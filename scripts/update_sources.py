# -*- coding: utf-8 -*-
"""L2「政策信息源」四张卡片的最新文件自动更新。

背景（为什么要自动生成）：
  L2 的四张卡片原本是 index.html 里的静态 HTML —— 卡片上写的「最新文件」是
  2025 年第四季度国债发行安排、国办发〔2024〕52 号这类**手工贴死的链接**，
  页面再跑一年它们也不会变。而且「国债汇总 / 地方债汇总」在抓取管线里
  **根本没有数据源**（财政部 mof.gov.cn 不在 ALL_SOURCES 里），所以永远不会更新。

本脚本给每张卡片配一个数据来源，输出 data/sources.json：
  · 政策汇总库 → 主抓取产物 data/latest.json 的「国务院最新政策文件」
  · 国债汇总   → 财政部预算司·国债发行通知（bgt.mof.gov.cn，逐笔发行/续发行通知）
  · 地方债汇总 → 财政部预算司·地方政府债券发行和债务余额情况（月度系列）+ 专项债政策法规
  · 官方解读汇总 → 主抓取产物 data/latest.json 的党媒评论

抓取零命中时沿用上一版并标 stale（与 L5 官媒定调同一套兜底思路：
CI 在境外，国内源随时可能被挡，绝不能把板块清空）。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LATEST_FILE = os.path.join(PROJECT_DIR, "data", "latest.json")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "sources.json")

BJ = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# gov.cn 政策文件库检索（与 update_compare.py 同一接口，实测 CI 可用）
SEARCH_API = "https://sousuo.www.gov.cn/search-gov/data"

# 卡片配置：indexUrl 是栏目的常驻入口（抓不到具体文件时的兜底指向）
CARDS = [
    {
        "key": "policy",
        "title": "政策汇总库",
        "indexUrl": "https://www.gov.cn/zhengce/zuixin.htm",
        "indexLabel": "gov.cn/zhengce 最新政策",
        "from": "gov",
    },
    {
        "key": "bond",
        "title": "国债汇总",
        "indexUrl": "https://bgt.mof.gov.cn/zhuantilanmu/rdwyh/czyw/",
        "indexLabel": "财政部预算司·国债发行",
        "lists": ["https://bgt.mof.gov.cn/zhuantilanmu/rdwyh/czyw/"],
        "include": r"国债",
        "exclude": r"会见|会谈|座谈|巡视|招聘|任免|公示|考试|培训",
        # 逐笔发行通知之外，再检索一次「超长期特别国债」等重大安排
        "search": {"kw": "超长期特别国债",
                   "titleMatch": r"国债"},
    },
    {
        "key": "localbond",
        "title": "地方债汇总",
        "indexUrl": "https://yss.mof.gov.cn/zhuantilanmu/dfzgl/sjtj/",
        "indexLabel": "财政部预算司·地方债数据",
        "lists": ["https://yss.mof.gov.cn/zhuantilanmu/dfzgl/sjtj/",
                  "https://yss.mof.gov.cn/zhuantilanmu/dfzgl/zcfg/"],
        "include": r"地方政府债券|专项债|地方债|一般债券|债务余额",
        "exclude": r"会见|会谈|座谈|巡视|招聘|任免",
        # 该栏目的月度数据停在 2025-09（栏目已停更），补一路政策文件库检索
        "search": {"kw": "专项债券",
                   "titleMatch": r"地方政府债券|专项债|地方债|债务余额|债务限额"},
    },
    {
        "key": "media",
        "title": "官方解读汇总",
        "indexUrl": "http://www.people.com.cn",
        "indexLabel": "people.com.cn",
        "from": "commentary",
    },
]


def bj_now(fmt="%Y-%m-%d %H:%M"):
    return datetime.now(BJ).strftime(fmt)


def _age_days(d):
    """最新文件距今天数（北京时间为准）；日期只到月份时按当月 1 日估。"""
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", d or "")
    if not m:
        return None
    try:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1),
                      tzinfo=BJ)
    except ValueError:
        return None
    return (datetime.now(BJ) - dt).days


def fetch(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except Exception as e:
        print("    · 抓取失败 %s: %s" % (url[:56], str(e)[:50]))
        return ""


def url_date(u):
    """从链接里取日期：优先 t20260915_ 这种 8 位日期，否则取 /202609/ 月份。"""
    m = re.search(r"t(20\d{2})(\d{2})(\d{2})_", u)
    if m:
        return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
    m = re.search(r"/(20\d{2})(\d{2})/", u)
    if m:
        return "%s-%s" % (m.group(1), m.group(2))
    return ""


def latest_from_mof(card):
    """从财政部栏目列表页挑出最新且命中关键词的文件。"""
    found = []
    for page in card.get("lists", []):
        html = fetch(page)
        if not html:
            continue
        for href, raw in re.findall(
                r'<a[^>]+href=["\']([^"\']+\.s?html?)["\'][^>]*>(.*?)</a>', html, re.S):
            title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()
            if len(title) < 8:
                continue
            if not re.search(card["include"], title):
                continue
            if card.get("exclude") and re.search(card["exclude"], title):
                continue
            full = urllib.parse.urljoin(page, href.strip())
            if not full.startswith("http"):
                continue
            found.append({"title": title, "url": full,
                          "date": url_date(full), "source": "财政部"})
    return found


def latest_from_search(card):
    """gov.cn 政策文件库检索（全文检索，必须按标题二次过滤，否则混入答记者问之类）。

    与 update_compare.py 同一接口：真实路径是 searchVO.catMap.{gongwen,bumenfile,otherfile}.listVO。
    """
    cfg = card.get("search")
    if not cfg:
        return []
    u = ("%s?t=zhengcelibrary&q=%s&sort=pubtime&sortType=1&p=1&n=100"
         % (SEARCH_API, urllib.parse.quote(cfg["kw"])))
    try:
        req = urllib.request.Request(u, headers=UA)
        data = json.loads(urllib.request.urlopen(req, timeout=25).read())
    except Exception as e:
        print("    · 文件库检索失败 %s: %s" % (cfg["kw"], str(e)[:50]))
        return []
    cat_map = (data.get("searchVO") or {}).get("catMap", {}) or {}
    rows = []
    for cat in ("gongwen", "bumenfile", "otherfile"):
        rows += (cat_map.get(cat, {}) or {}).get("listVO", []) or []
    out = []
    for it in rows:
        title = re.sub(r"<[^>]+>", "", it.get("title") or "").strip()
        url = it.get("url") or ""
        # pubtimeStr 形如 2026.09.16
        m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", it.get("pubtimeStr") or "")
        if not title or not url or not m:
            continue
        if not re.search(cfg["titleMatch"], title):
            continue
        org = re.sub(r"\s+", " ", it.get("puborg") or "").strip()
        out.append({"title": title, "url": url,
                    "date": "%s-%s-%s" % m.groups(),
                    "source": org or "gov.cn 文件库"})
    return out


def latest_from_local(card, latest):
    """从主抓取产物里挑：gov=国务院政策库，commentary=党媒评论。"""
    if card.get("from") == "gov":
        pool = [(it, it.get("desc") or "") for it in latest.get("timeline") or []
                if (it.get("desc") or "") == "国务院最新政策文件"]
    else:
        pool = [(it, it.get("media") or "党媒") for it in latest.get("commentary") or []]
    out = []
    for it, src in pool:
        if not it.get("title") or not it.get("url"):
            continue
        out.append({"title": it["title"], "url": it["url"],
                    "date": it.get("date") or "", "source": src})
    return out


def remote_candidates(card):
    """卡片的外部来源候选：栏目列表页 + 政策文件库检索。"""
    return latest_from_mof(card) + latest_from_search(card)


def main():
    now = bj_now()
    latest = {}
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, encoding="utf-8") as f:
            latest = json.load(f)

    prev = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                for c in json.load(f).get("cards") or []:
                    prev[c.get("key")] = c
        except Exception:
            prev = {}

    # 外部来源（财政部栏目 + 政策文件库检索）并发抓，减少串行等待
    remote_cards = [c for c in CARDS if c.get("lists") or c.get("search")]
    remote_result = {}
    if remote_cards:
        with ThreadPoolExecutor(max_workers=len(remote_cards)) as pool:
            for card, items in pool.map(lambda c: (c, remote_candidates(c)), remote_cards):
                remote_result[card["key"]] = items

    out, stale_keys = [], []
    for card in CARDS:
        candidates = (latest_from_local(card, latest) if card.get("from")
                      else remote_result.get(card["key"], []))
        candidates = [c for c in candidates if c.get("date")]
        candidates.sort(key=lambda x: x["date"], reverse=True)
        newest = candidates[0] if candidates else None

        if newest:
            entry = dict(card)
            entry.pop("lists", None)
            entry.pop("search", None)
            entry.update({
                "href": newest["url"],
                "latest": newest,
                "stale": False,
                "total": len(candidates),
                "fetchedAt": now,
                "ageDays": _age_days(newest.get("date")),
            })
        elif prev.get(card["key"], {}).get("latest"):
            # 零命中：沿用上一版，如实标注（境外网络受限时不让卡片变空）
            old = prev[card["key"]]
            entry = dict(card)
            entry.pop("lists", None)
            entry.pop("search", None)
            entry.update({
                "href": old.get("href") or card["indexUrl"],
                "latest": old["latest"],
                "stale": True,
                "total": old.get("total", 0),
                "fetchedAt": old.get("fetchedAt") or "",
                "ageDays": _age_days((old.get("latest") or {}).get("date")),
            })
            stale_keys.append(card["key"])
        else:
            entry = dict(card)
            entry.pop("lists", None)
            entry.pop("search", None)
            entry.update({"href": card["indexUrl"], "latest": None,
                          "stale": False, "total": 0, "fetchedAt": now,
                          "ageDays": None})
        out.append(entry)
        lt = entry.get("latest") or {}
        print("    %-8s %s  %s %s" % (
            card["key"], "沿用上一版" if entry["stale"] else "命中 %d 条" % entry["total"],
            lt.get("date", "(无)"), (lt.get("title") or "(无最新文件)")[:44]))

    result = {"generatedAt": now, "cards": out,
              "stale": bool(stale_keys), "staleKeys": stale_keys}
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("  已写入 %s" % OUTPUT_FILE)
    return result


if __name__ == "__main__":
    main()
