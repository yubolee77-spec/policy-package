#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L5「证监会动态」数据抓取
=========================================================================
把原先硬编码在 index.html 里的四张静态卡片，换成每天自动抓取的四块数据：

  1) 负面清单（谁被罚了）—— 证监会官网「按日盯市 / 监管动态」的实际内容
     数据源：www.csrc.gov.cn 的 searchList 栏目接口
        · 行政处罚决定 · 监管措施 · 市场禁入决定 · 辖区监管动态
  2) 正面试点（谁被放行了）
     数据源：同上
        · 结果公示（IPO / REITs 注册批复）· 政策解读 · 许可审核进度
  3) 发行上市审核进度（实时「试点进度条」）
     数据源：东方财富数据中心 RPT_IPO_INFOALLNEW
        在审状态快照 / 上市板块 / 证监会行业 / 受理→注册生效周期（按月趋势）
  4) 官媒定调（首例 / 首单 / 首个 / 首批）
     数据源：东方财富新闻搜索，仅保留官方媒体

输出：data/csrc.json
"""

import datetime
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(ROOT, "data", "csrc.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 证监会站点证书链在本机/CI 上偶有问题，统一放宽校验（只读公开数据）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

CSRC_HOST = "https://www.csrc.gov.cn"


# ---------------------------------------------------------------------------
# 通用 HTTP
# ---------------------------------------------------------------------------
def http_get(url, referer="", timeout=25, tries=3, accept="*/*"):
    """带重试的 GET，返回解码后的文本；全部失败则抛出最后一个异常。"""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": accept,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": referer or url,
            })
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:            # noqa: BLE001 - 网络抖动统一重试
            last = e
            if i < tries - 1:
                time.sleep(1.5 * (i + 1))
    raise last


def _strip_tags(s):
    return re.sub(r"<[^>]*>", "", s or "").strip()


def _parse_day(v):
    if not v:
        return None
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _days_ago(date_str):
    d = _parse_day(date_str)
    return None if d is None else (datetime.date.today() - d).days


# ---------------------------------------------------------------------------
# 一、证监会官网栏目（负面清单 + 正面试点）
# ---------------------------------------------------------------------------
# 栏目 channelId 从 www.csrc.gov.cn 首页侧栏提取，是站点 CMS 的稳定内部 ID。
# 「行政处罚决定 / 监管措施 / 市场禁入决定 / 辖区监管动态」= 负面清单；
# 「结果公示 / 政策解读 / 许可审核进度」= 正面（试点）清单。
CSRC_COLUMNS = [
    ("监管措施",     "212665889d144f0392445f47661ca98e", "penalty"),
    ("辖区监管动态", "625e0ed8a45842c28751458bfcacb422", "penalty"),
    ("行政处罚决定", "17d5ff2fe43e488dba825807ae40d63f", "penalty"),
    ("市场禁入决定", "3795869930ca4b70bf55469270a6e641", "penalty"),
    ("结果公示",     "d5483bfd719e4e8d95ffbe975b2f73ff", "approval"),
    ("政策解读",     "cb16a6a50e134294a3e59df17fa960e3", "approval"),
    ("许可审核进度", "940e56fc158746b98c10bb7dcdd11012", "approval"),
]

CSRC_PAGE_SIZE = 60
CSRC_PAGES = 3          # 每栏目抓 3 页 ≈ 180 条，足够覆盖「年」视图

# 负面清单类型标签（按标题关键词判定，顺序即优先级）
PENALTY_TAGS = [
    (("市场禁入",),                         "市场禁入"),
    (("行政处罚", "处罚决定书"),             "行政处罚"),
    (("警示函",),                           "警示函"),
    (("监管谈话",),                         "监管谈话"),
    (("责令改正", "责令公开说明"),            "责令改正"),
    (("公开谴责", "通报批评"),               "公开谴责"),
    (("立案", "调查", "稽查"),               "立案调查"),
]

# 正面清单类型标签（「谁被放行了」的通行证类型）
APPROVAL_TAGS = [
    (("商业不动产证券投资基金", "商业不动产投资信托基金"), "REITs·商业不动产"),
    (("基础设施证券投资基金",),              "REITs·基础设施"),
    (("首次公开发行股票注册", "公开发行股票注册的批复"), "IPO注册"),
    (("并购重组",),                         "并购重组"),
    (("基金注册的批复", "基金注册"),          "基金注册"),
    (("合格境外投资者", "合格境外机构投资者"), "境外投资者资格"),
    (("做市交易业务资格", "做市"),            "做市资格"),
    (("托管资格",),                         "托管资格"),
    (("吸收合并", "合并"),                   "机构合并"),
    (("业务资格", "资格的批复"),              "业务资格"),
]

# 栏目兜底标签：决定「其他」落到哪个筐
APPROVAL_COLUMN_FALLBACK = {
    "政策解读": "政策法规",
    "许可审核进度": "审核进度公示",
    "结果公示": "核准批复",
}


def _enrich_penalty_title(title, content):
    """行政处罚决定书 / 市场禁入决定书的标题是通用名称（几十条一模一样），
    从正文开头补出「文号 + 当事人」，否则列表里全是无意义的重复标题。

    正文形如：〔2026〕42号当事人:元道通信股份有限公司(以下简称元道通信),住所:...
    返回 (文号, 当事人)，两项都可能为空。
    """
    text = _strip_tags(content)
    doc_no, party = "", ""

    m = re.match(r"^\s*[〔\[（(]\s*(\d{4})\s*[〕\]）)]\s*第?\s*(\d+)\s*号", text)
    if m:
        doc_no = "〔%s〕%s号" % (m.group(1), m.group(2))

    m2 = re.search(r"当事人[:：]\s*([^,，。；;、（(]{2,32})", text)
    if m2:
        party = m2.group(1).strip()
    if not party:                      # 「市场禁入决定书（高松）」这类标题自带人名
        m3 = re.search(r"[（(]([^）)]{2,20})[）)]\s*$", title)
        if m3:
            party = m3.group(1).strip()
    return doc_no, party


def _classify(title, table, fallback):
    for keys, tag in table:
        for k in keys:
            if k in title:
                return tag
    return fallback


def fetch_csrc_column(name, guid, bucket):
    """抓单个栏目若干页，返回标准化条目列表。"""
    items, seen = [], set()
    for page in range(1, CSRC_PAGES + 1):
        url = ("%s/searchList/%s?_isAgg=true&_isJson=true&_pageSize=%d"
               "&_template=index&_rangeTimeGte=&_channelName=&page=%d"
               % (CSRC_HOST, guid, CSRC_PAGE_SIZE, page))
        try:
            data = json.loads(http_get(url, referer=CSRC_HOST + "/"))
        except Exception as e:                       # noqa: BLE001
            print("    ! %s 第%d页失败: %s" % (name, page, str(e)[:60]))
            break

        results = ((data.get("data") or {}).get("results")) or []
        if not results:
            break

        for r in results:
            raw_title = _strip_tags(r.get("title") or "")
            if not raw_title:
                continue
            raw_url = r.get("url") or ""
            if raw_url.startswith("//"):
                full = "https:" + raw_url
            elif raw_url.startswith("/"):
                full = CSRC_HOST + raw_url
            else:
                full = raw_url
            date = str(r.get("publishedTimeStr") or "")[:10]
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                continue
            if full in seen:
                continue
            seen.add(full)

            title, doc_no, party = raw_title, "", ""
            if bucket == "penalty":
                # 分类必须用原始标题（补充后的标题会丢掉「行政处罚/市场禁入」等关键词）
                tag = _classify(raw_title, PENALTY_TAGS, "监管措施")
                doc_no, party = _enrich_penalty_title(
                    raw_title, r.get("content") or "")
                suffix = doc_no + (" · " + party if party else "")
                if suffix:
                    # 通用标题 → 换成「类型 + 文号 + 当事人」，避免一屏重复
                    title = ("%s %s" % (tag, suffix)).strip() \
                        if "决定书" in raw_title else raw_title
                elif "决定书" in raw_title:
                    tail = re.search(r"/(c\d+)\.shtml", full) or \
                        re.search(r"/(\d+)\.shtml", full)
                    if tail:
                        title = "%s · %s" % (raw_title, tail.group(1))
            else:
                tag = _classify(title, APPROVAL_TAGS,
                                APPROVAL_COLUMN_FALLBACK.get(name, "其他"))

            items.append({
                "date": date,
                "channel": r.get("channelName") or name,
                "column": name,
                "tag": tag,
                "title": title,
                "docNo": doc_no,
                "party": party,
                "url": full,
            })
        time.sleep(0.2)

    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def fetch_csrc_all():
    """并发抓取全部栏目，返回 (penalty, approval)。

    注意：同一份决定书可能同时挂在「监管措施」和各地「辖区监管动态」下，
    因此再按标题做一次去重，保留最新的一条。
    """
    penalty, approval = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_csrc_column, n, g, b): (n, b)
                   for n, g, b in CSRC_COLUMNS}
        for fut in as_completed(futures):
            name, bucket = futures[fut]
            try:
                rows = fut.result()
            except Exception as e:                    # noqa: BLE001
                print("    ! %s 抓取异常: %s" % (name, str(e)[:70]))
                continue
            (penalty if bucket == "penalty" else approval).extend(rows)
            print("    · %-12s %4d 条" % (name, len(rows)))

    def _dedupe_by_title(rows):
        rows.sort(key=lambda x: x["date"], reverse=True)
        out, seen = [], set()
        for r in rows:
            key = re.sub(r"\s+", "", r["title"])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    return _dedupe_by_title(penalty), _dedupe_by_title(approval)


# ---------------------------------------------------------------------------
# 二、发行上市审核进度（东财数据中心）
# ---------------------------------------------------------------------------
EM_HOST = "https://datacenter-web.eastmoney.com"
EM_REFERER = "https://data.eastmoney.com/"

# 各审核状态的归类：active=在审管道 / success=已放行 / fail=已出局
STATE_KIND = {
    "已受理": "active",
    "已问询": "active",
    "上市委会议通过": "active",
    "上市委会议暂缓": "active",
    "提交注册": "active",
    "已收到注册申请材料": "active",
    "注册生效": "success",
    "终止": "fail",
    "撤回": "fail",
    "终止注册": "fail",
    "不予注册": "fail",
}
STAGE_ORDER = ["已受理", "已问询", "上市委会议通过", "提交注册", "注册生效"]


def fetch_ipo_review():
    """抓 IPO 审核进度，统计在审快照 / 板块 / 行业 / 审批周期趋势。"""
    rows, page, page_size = [], 1, 500
    while True:
        url = ("%s/api/data/v1/get?columns=ALL&pageSize=%d&pageNumber=%d"
               "&sortColumns=UPDATE_DATE&sortTypes=-1&reportName=RPT_IPO_INFOALLNEW"
               % (EM_HOST, page_size, page))
        try:
            data = json.loads(http_get(url, referer=EM_REFERER))
        except Exception as e:                        # noqa: BLE001
            print("    ! IPO 第%d页失败: %s" % (page, str(e)[:60]))
            break
        result = data.get("result") or {}
        batch = result.get("data") or []
        if not batch:
            break
        rows.extend(batch)
        total = result.get("count") or 0
        if len(rows) >= total or page >= 12:
            break
        page += 1

    if not rows:
        return None

    today = datetime.date.today()

    # 只保留近两年内仍有状态更新的记录 → 代表「当前在审管道」
    pipeline = []
    for r in rows:
        upd = _parse_day(r.get("UPDATE_DATE"))
        if upd and (today - upd).days <= 730:
            pipeline.append(r)

    stage_counts, market_counter, industry_counter = {}, {}, {}
    for r in pipeline:
        st = (r.get("STATE") or "").strip()
        if st:
            stage_counts[st] = stage_counts.get(st, 0) + 1
        mk = (r.get("PREDICT_LISTING_MARKET") or "其他").strip()
        market_counter[mk] = market_counter.get(mk, 0) + 1
        ind = (r.get("CSRC_INDUSTRY") or "未分类").strip()
        industry_counter[ind] = industry_counter.get(ind, 0) + 1

    stages = []
    for s in STAGE_ORDER:
        stages.append({"name": s, "count": stage_counts.get(s, 0),
                       "kind": STATE_KIND.get(s, "active")})
    fail_count = sum(v for k, v in stage_counts.items()
                     if STATE_KIND.get(k) == "fail")
    if fail_count:
        stages.append({"name": "已终止 / 撤回", "count": fail_count, "kind": "fail"})

    def _top(counter, n):
        return [{"name": k, "count": v}
                for k, v in sorted(counter.items(), key=lambda x: -x[1])[:n] if k]

    # —— 审批周期：受理 → 注册生效 的天数 ——
    approved = []
    for r in rows:
        if (r.get("STATE") or "").strip() != "注册生效":
            continue
        a, u = _parse_day(r.get("ACCEPT_DATE")), _parse_day(r.get("UPDATE_DATE"))
        if not a or not u or (u - a).days <= 0:
            continue
        approved.append({
            "date": u,
            "days": (u - a).days,
            "company": (r.get("DECLARE_ORG") or "").strip(),
            "market": (r.get("PREDICT_LISTING_MARKET") or "").strip(),
            "industry": (r.get("CSRC_INDUSTRY") or "").strip(),
        })
    approved.sort(key=lambda x: x["date"], reverse=True)

    def _avg(seq):
        return round(sum(x["days"] for x in seq) / len(seq)) if seq else None

    recent90 = [x for x in approved if (today - x["date"]).days <= 90]
    prev90 = [x for x in approved if 90 < (today - x["date"]).days <= 180]

    # 按月的周期趋势（近 12 个自然月）
    by_month = []
    for back in range(11, -1, -1):
        first = (today.replace(day=1) - datetime.timedelta(days=back * 30)).replace(day=1)
        ym = first.strftime("%Y-%m")
        bucket = [x for x in approved if x["date"].strftime("%Y-%m") == ym]
        if bucket:
            by_month.append({"month": ym[2:], "avg": _avg(bucket), "n": len(bucket)})

    ra, pa = _avg(recent90), _avg(prev90)
    if ra is not None and pa:
        delta = round((ra - pa) / pa * 100)
        verdict = ("加快 %d%%" % abs(delta)) if delta < -5 else \
                  ("放缓 %d%%" % delta) if delta > 5 else "基本持平"
    else:
        delta, verdict = None, "样本不足"

    cycle = {
        "recentAvg": ra, "recentN": len(recent90),
        "prevAvg": pa, "prevN": len(prev90),
        "deltaPct": delta, "verdict": verdict,
        "byMonth": by_month,
        "fastest": [{"company": x["company"], "days": x["days"],
                     "date": x["date"].isoformat(), "market": x["market"]}
                    for x in sorted(recent90 or approved,
                                    key=lambda x: x["days"])[:5]],
    }

    def _row(r, with_days=False):
        a, u = _parse_day(r.get("ACCEPT_DATE")), _parse_day(r.get("UPDATE_DATE"))
        d = {
            "date": u.isoformat() if u else "",
            "acceptDate": a.isoformat() if a else "",
            "company": (r.get("DECLARE_ORG") or "").strip(),
            "market": (r.get("PREDICT_LISTING_MARKET") or "").strip(),
            "industry": (r.get("CSRC_INDUSTRY") or "").strip(),
            "state": (r.get("STATE") or "").strip(),
            "region": (r.get("REG_ADDRESS") or "").strip(),
            "sponsor": (r.get("RECOMMEND_ORG") or "").strip(),
        }
        if with_days:
            d["days"] = (u - a).days if (a and u) else None
        return d

    by_update_desc = sorted(pipeline,
                            key=lambda r: str(r.get("UPDATE_DATE") or ""),
                            reverse=True)

    return {
        "asOf": max((r.get("UPDATE_DATE") or "")[:10] for r in rows),
        "total": len(rows),
        "pipelineTotal": len(pipeline),
        "activeTotal": sum(v for k, v in stage_counts.items()
                           if STATE_KIND.get(k) == "active"),
        "successTotal": sum(v for k, v in stage_counts.items()
                            if STATE_KIND.get(k) == "success"),
        "failTotal": fail_count,
        "stages": stages,
        "markets": _top(market_counter, 6),
        "industries": _top(industry_counter, 10),
        "cycle": cycle,
        # 最近放行（注册生效）
        "recentApproved": [
            {"date": x["date"].isoformat(), "company": x["company"],
             "market": x["market"], "industry": x["industry"], "days": x["days"]}
            for x in approved[:25]],
        # 最近在审动态
        "recentActive": [_row(r) for r in by_update_desc
                         if STATE_KIND.get((r.get("STATE") or "").strip()) == "active"][:40],
    }


# ---------------------------------------------------------------------------
# 三、官媒定调（首例 / 首单 / 首个 / 首批）
# ---------------------------------------------------------------------------
# 官方媒体白名单：定调性报道主要出自这几家
MEDIA_WHITELIST = (
    "财联社", "证券时报", "上海证券报", "中国证券网", "中国证券报", "证券日报",
    "新华社", "新华财经", "人民日报", "经济日报", "央视", "央广", "光明日报",
    "21世纪经济报道", "第一财经", "科创板日报", "澎湃新闻", "中国新闻网",
    "每日经济新闻", "界面新闻", "中证", "上证报",
)

# 定调关键词：都是「首创性」表述。
# 刻意不含「首次」「首发」——实测噪音极大（首次回购、产品首发），会把信号淹掉。
MEDIA_KEYWORDS = ["首例", "首单", "首个", "首批", "首家", "首张", "首条"]

# 试点方向：命中则归类，说明报道落在国家重点推进的赛道上
TOPIC_HINTS = [
    ("REITs",     ("reits", "不动产投资信托", "商业不动产", "基础设施基金")),
    ("低空经济",   ("低空", "evtol", "无人机", "通航", "飞行汽车")),
    ("算力/AI",   ("算力", "智算", "人工智能", "大模型")),
    ("数据要素",   ("数据要素", "数据资产", "可信数据", "数据交易所")),
    ("集成电路",   ("集成电路", "芯片", "半导体", "光刻")),
    ("新能源",     ("光伏", "储能", "新能源", "电网", "氢能")),
    ("生物医药",   ("创新药", "生物医药", "医疗器械", "细胞治疗")),
    ("绿色通道",   ("绿色通道", "简易程序", "即报即审", "快速通道", "预审")),
    ("商业航天",   ("商业航天", "卫星", "可回收火箭")),
    ("消费/文旅",  ("消费基础设施", "免税", "文旅", "首发经济")),
]


def fetch_media_signals(max_per_kw=50):
    """搜索「首例/首单/…」，只保留官媒 + 标题命中关键词的报道。"""
    out, seen = [], set()
    for kw in MEDIA_KEYWORDS:
        param = {
            "uid": "", "keyword": kw, "type": ["cmsArticleWebOld"],
            "client": "web", "clientType": "web", "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {
                "searchScope": "default", "sort": "time",
                "pageIndex": 1, "pageSize": max_per_kw,
                "preTag": "", "postTag": "",
            }},
        }
        url = ("https://search-api-web.eastmoney.com/search/jsonp?cb=cb&param="
               + urllib.parse.quote(json.dumps(param, ensure_ascii=False)))
        try:
            text = http_get(url, referer="https://so.eastmoney.com/")
            payload = json.loads(text[text.find("(") + 1: text.rfind(")")])
            rows = payload["result"]["cmsArticleWebOld"]
        except Exception as e:                        # noqa: BLE001
            print("    ! 搜索「%s」失败: %s" % (kw, str(e)[:60]))
            continue

        kept = 0
        for r in rows:
            title = _strip_tags(r.get("title") or "")
            media = _strip_tags(r.get("mediaName") or "")
            if kw not in title:                       # 搜索是模糊匹配，必须标题命中
                continue
            if not any(m in media for m in MEDIA_WHITELIST):
                continue
            link = r.get("url") or ""
            if not link or link in seen:
                continue
            seen.add(link)

            low = (title + " " + (r.get("content") or "")).lower()
            topics = [name for name, keys in TOPIC_HINTS
                      if any(k in low for k in keys)]

            out.append({
                "date": str(r.get("date") or "")[:10],
                "media": media,
                "title": title,
                "url": link,
                "keyword": kw,
                "topics": topics[:3],
                # 首例/首单/首个 = 首创性最强的表述，定调力度更高
                "strong": kw in ("首例", "首单", "首个") or bool(topics),
            })
            kept += 1
        print("    · 「%s」命中官媒 %d 条" % (kw, kept))

    out.sort(key=lambda x: (x["date"], x["strong"]), reverse=True)
    return out


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build():
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print("[csrc] 开始抓取 …")

    print("  [1/3] 证监会官网栏目（负面清单 / 正面试点）")
    try:
        penalty, approval = fetch_csrc_all()
    except Exception as e:                            # noqa: BLE001
        print("    ! 证监会栏目整体失败: %s" % str(e)[:100])
        penalty, approval = [], []

    print("  [2/3] 发行上市审核进度（东财）")
    try:
        review = fetch_ipo_review()
    except Exception as e:                            # noqa: BLE001
        print("    ! IPO 审核进度失败: %s" % str(e)[:100])
        review = None

    print("  [3/3] 官媒定调（首例 / 首单 / 首个 / 首批）")
    try:
        media = fetch_media_signals()
    except Exception as e:                            # noqa: BLE001
        print("    ! 官媒搜索失败: %s" % str(e)[:100])
        media = []

    # —— 监管 KPI：从上面数据自动汇总 ——
    ym = datetime.date.today().strftime("%Y-%m")
    month = lambda rows: sum(1 for r in rows if str(r.get("date") or "").startswith(ym))  # noqa: E731

    kpi = {
        "penaltyTotal": len(penalty),
        "penaltyMonth": month(penalty),
        "approvalTotal": len(approval),
        "approvalMonth": month(approval),
        "reitsApproved30d": sum(
            1 for r in approval if r["tag"].startswith("REITs")
            and (_days_ago(r["date"]) or 999) <= 30),
        "ipoApproved30d": sum(
            1 for r in approval if r["tag"] == "IPO注册"
            and (_days_ago(r["date"]) or 999) <= 30),
        "mediaTotal": len(media),
        "mediaStrong": sum(1 for m in media if m.get("strong")),
    }
    if review:
        kpi["activeTotal"] = review["activeTotal"]
        kpi["successTotal"] = review["successTotal"]
        kpi["cycleRecentAvg"] = review["cycle"]["recentAvg"]
        kpi["cyclePrevAvg"] = review["cycle"]["prevAvg"]
        kpi["cycleVerdict"] = review["cycle"]["verdict"]

    result = {
        "generatedAt": generated,
        "kpi": kpi,
        "penalty": penalty[:400],
        "approval": approval[:300],
        "media": media[:80],
        "review": review,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print("\n[csrc] 完成 → %s" % OUTPUT_FILE)
    print("  负面清单 %d 条（本月新增 %d）" % (len(result["penalty"]), kpi["penaltyMonth"]))
    print("  正面试点 %d 条（本月新增 %d · 30天内 REITs 批复 %d / IPO 批复 %d）"
          % (len(result["approval"]), kpi["approvalMonth"],
             kpi["reitsApproved30d"], kpi["ipoApproved30d"]))
    print("  官媒定调 %d 条（强定调 %d）" % (kpi["mediaTotal"], kpi["mediaStrong"]))
    if review:
        print("  在审 %d 家 · 已放行 %d · 已出局 %d"
              % (review["activeTotal"], review["successTotal"], review["failTotal"]))
        print("  审批周期 近90天 %s 天 vs 前90天 %s 天 → %s"
              % (review["cycle"]["recentAvg"], review["cycle"]["prevAvg"],
                 review["cycle"]["verdict"]))
    return result


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:                          # noqa: BLE001
        print("[csrc] 抓取失败: %s" % exc, file=sys.stderr)
        sys.exit(1)
