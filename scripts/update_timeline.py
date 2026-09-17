# -*- coding: utf-8 -*-
"""L1「年度政策时间线」自动生成。

背景（为什么要自动生成）：
  该板块由 app.js 的 annualTimelineNodes 硬编码驱动，节点 status 写死在代码里，
  结果 2026-09 打开页面，1-2月 还标着「🔥 当前阶段」，9-10月 反而标成「⏳ 预期窗口」；
  节点内容也停在 8 月，之后发生的事永远不会出现。

本脚本做两件事：
  1. 按**北京时间的月**重新判定 8 个政策节点的 hot / pass / future；
  2. 按每个节点覆盖的月份窗口，从 data/latest.json（政策 timeline + 党媒评论）
     自动收录真实条目，前端把它们追加到节点正文的「原文链接」区。

输出 data/timeline.json，结构：
{
  "generatedAt": "2026-09-17 16:10",
  "month": 9,
  "hotPeriod": "9-10月",
  "nodes": {
    "9-10月": {"status": "hot", "docs": [{"label","url","date","source"}]},
    ...
  }
}
前端拿不到本文件时回退到内置文案与 status，页面不会空白。
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LATEST_FILE = os.path.join(PROJECT_DIR, "data", "latest.json")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "timeline.json")

BJ = timezone(timedelta(hours=8))
MAX_DOCS_PER_NODE = 6
# 会晤/人事/执纪类条目不是「政策节奏」事件，优先排在后面（不足时才回填）
NOISE_RE = re.compile(r"会见|会谈|致辞|演讲|贺信|纪念|座谈|纪律审查|监察调查|"
                      r"任免|任前公示|被查|双开|简历|讣告")

# 政策节点 → 覆盖月份（与 app.js 的 annualTimelineNodes 的 period 一一对应）
# 「7月」节点含 8 月：7 月底政治局会议定调后，8 月是配套解读与新政策密集期
NODE_WINDOWS = [
    ("1-2月", [1, 2]),
    ("3月", [3]),
    ("4月", [4]),
    ("5-6月", [5, 6]),
    ("7月", [7, 8]),
    ("9-10月", [9, 10]),
    ("11月", [11]),
    ("12月", [12]),
]
# 1~2 月时，上一年 11/12 月的会议刚刚开完，应显示为「已发生」
YEAR_END_NODES = ("11月", "12月")


def bj_now(fmt="%Y-%m-%d %H:%M"):
    return datetime.now(BJ).strftime(fmt)


def node_status(period, months, cur_month):
    """按北京时间当月判定节点状态：

    · 当前月落在节点窗口内 → hot（进行中）
    · 节点已在今年走完（窗口末尾早于当前月）→ pass（已发生）
    · 否则 → future（预期窗口）
    另外 1~2 月时，上一年的 11/12 月节点刚开完，按 pass 处理。
    """
    if cur_month in months:
        return "hot"
    if max(months) < cur_month:
        return "pass"
    if cur_month <= 2 and period in YEAR_END_NODES:
        return "pass"
    return "future"


def _date_ok(d):
    return bool(re.match(r"20\d{2}-\d{2}-\d{2}$", d or ""))


def _months_for_node(period, months, cur_month, cur_year):
    """节点窗口对应的 (年, 月) 集合。1~2 月时把 11/12 月节点算到上一年。"""
    if cur_month <= 2 and period in YEAR_END_NODES:
        return (cur_year - 1, months)
    return (cur_year, months)


def collect_docs(node_months, year):
    """从 latest.json 里挑出落在 (year, node_months) 窗口内的条目。"""
    docs, seen = [], set()
    for it, src in SOURCES_CACHE:
        d = it.get("date") or ""
        if not _date_ok(d):
            continue
        try:
            y, m = int(d[:4]), int(d[5:7])
        except ValueError:
            continue
        if y != year or m not in node_months:
            continue
        url = it.get("url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        title = (it.get("title") or "").strip()
        docs.append({
            "label": "%s · %s%s" % (d, title[:60], ("（%s）" % src) if src else ""),
            "title": title,
            "url": url,
            "date": d,
            "source": src or "",
            "noise": bool(NOISE_RE.search(title)),
        })
    docs.sort(key=lambda x: x["date"], reverse=True)
    keep = [x for x in docs if not x["noise"]]
    rest = [x for x in docs if x["noise"]]
    # 政策类优先；政策类不足时才用会晤/人事类补齐
    return (keep + rest)[:MAX_DOCS_PER_NODE]


SOURCES_CACHE = []


def load_items():
    """政策条目与党媒评论合并成一个候选池（政策优先，同为政策来源更权威）"""
    global SOURCES_CACHE
    SOURCES_CACHE = []
    if not os.path.exists(LATEST_FILE):
        return 0
    with open(LATEST_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for it in data.get("timeline") or []:
        # desc 是来源标签（国务院/发改委/央行…）
        SOURCES_CACHE.append((it, it.get("desc") or ""))
    for it in data.get("commentary") or []:
        SOURCES_CACHE.append((it, it.get("media") or "党媒"))
    return len(SOURCES_CACHE)


def main():
    n = load_items()
    now = datetime.now(BJ)
    cur_month, cur_year = now.month, now.year

    nodes = {}
    hot_period = ""
    for period, months in NODE_WINDOWS:
        status = node_status(period, months, cur_month)
        year, mset = _months_for_node(period, months, cur_month, cur_year)
        docs = collect_docs(mset, year)
        nodes[period] = {"status": status, "docs": docs,
                         "window": "%d年%s" % (year, period)}
        if status == "hot":
            hot_period = period

    result = {
        "generatedAt": bj_now(),
        "month": cur_month,
        "hotPeriod": hot_period,
        "candidateCount": n,
        "nodes": nodes,
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print("  年度时间线: 当前 %d月 → 当前阶段 %s，候选 %d 条" % (cur_month, hot_period, n))
    for period, _ in NODE_WINDOWS:
        nd = nodes[period]
        print("    %-7s %-6s 自动收录 %d 条" % (period, nd["status"], len(nd["docs"])))
    print("  已写入 %s" % OUTPUT_FILE)
    return result


if __name__ == "__main__":
    main()
