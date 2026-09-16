# -*- coding: utf-8 -*-
"""L0 核心宏观指标自动更新

数据源：东方财富数据中心（datacenter-web.eastmoney.com）
  - 境外可访问（GitHub Actions 可直接抓），结构化 JSON，字段稳定
  - 底层数据即国家统计局/央行月度发布

生成 data/macro.json：
  - cards  : L0 卡片（最新值 + 较上期变化），前端渲染；抓不到的指标由前端用内置兜底
  - series : CPI/PPI/PMI 近 13 个月序列，用于趋势图

抓取失败时不动旧文件；本脚本由 update_data.py 在每次运行末尾调用。
"""

import json
import os
import re
import urllib.request
from datetime import date

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "macro.json")

# ── 北京时间工具（Actions 环境是 UTC，统一转北京时间输出，避免前端显示困惑）──
def bj_now(fmt="%Y-%m-%d %H:%M"):
    import datetime as _dt
    return (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).strftime(fmt)



_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
_API = ("https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?columns=ALL&pageSize={size}&sortColumns=TIME&sortTypes=-1&reportName={name}")
_PAGE_URL = {
    "cpi": "https://data.eastmoney.com/cjsj/cpi.html",
    "ppi": "https://data.eastmoney.com/cjsj/ppi.html",
    "pmi": "https://data.eastmoney.com/cjsj/pmi.html",
    "gdp": "https://data.eastmoney.com/cjsj/gdp.html",
    "money": "https://data.eastmoney.com/cjsj/hbgyl.html",
    "indus": "https://data.eastmoney.com/cjsj/gyzjz.html",
    "retail": "https://data.eastmoney.com/cjsj/qgsssr.html",
}

_REPORTS = {
    "cpi": "RPT_ECONOMY_CPI",
    "ppi": "RPT_ECONOMY_PPI",
    "pmi": "RPT_ECONOMY_PMI",
    "gdp": "RPT_ECONOMY_GDP",
    "money": "RPT_ECONOMY_CURRENCY_SUPPLY",
    "indus": "RPT_ECONOMY_INDUS_GROW",
    "retail": "RPT_ECONOMY_TOTAL_RETAIL",
}


def _fetch_report(name, size=30):
    """拉取单个报告，返回按时间升序的行列表"""
    url = _API.format(size=size, name=name)
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Referer": "https://data.eastmoney.com/cjsj/",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d or not d.get("result"):
        return []
    return d["result"]["data"]


def _month_key(t):
    """'2026年08月份' -> '2026-08'；其余返回 ''"""
    m = re.match(r"(\d{4})年(\d{1,2})月份", t or "")
    return "%s-%02d" % (m.group(1), int(m.group(2))) if m else ""


def _quarter_key(t):
    """'2026年第1-2季度' -> (2026, 2, '上半年')；非季度返回 (0,0,'')"""
    m = re.match(r"(\d{4})年第(\d+)(?:-(\d+))?季度", t or "")
    if not m:
        return (0, 0, "")
    end = int(m.group(3) or m.group(2))
    label = {1: "一季度", 2: "上半年", 3: "前三季度", 4: "全年"}.get(end, "第%d季度" % end)
    return (int(m.group(1)), end, label)


def _sort_rows(rows, monthly=True):
    """按解析出的时间键升序（旧→新），无法解析的丢弃"""
    out = []
    for r in rows:
        t = r.get("TIME") or ""
        if monthly:
            k = _month_key(t)
            sk = k
        else:
            y, q, label = _quarter_key(t)
            k, sk = (label, "%04d-%d" % (y, q))
        if not sk:
            continue
        out.append((sk, k, r))
    out.sort(key=lambda x: x[0])
    return out


def _f1(x):
    """保留 1 位小数的字符串"""
    try:
        return "%.1f" % float(x)
    except (TypeError, ValueError):
        return ""


def _mlabel(mk):
    """'2026-08' -> '2026年8月'"""
    if not mk or "-" not in mk:
        return mk or ""
    y, m = mk.split("-")
    return "%s年%d月" % (y, int(m))


def _delta(cur, prev):
    """环比变化字符串，如 '+0.3pct' / '持平'"""
    try:
        d = round(float(cur) - float(prev), 1)
    except (TypeError, ValueError):
        return ""
    if d > 0:
        return "较上月+%.1fpct" % d
    if d < 0:
        return "较上月-%.1fpct" % abs(d)
    return "与上月持平"


def _dir_rise(cur, prev):
    """数值上升=pos（配 chg 文案表达好坏），下降=neg，持平=flat"""
    try:
        c, p = float(cur), float(prev)
    except (TypeError, ValueError):
        return "flat"
    if c > p:
        return "pos"
    if c < p:
        return "neg"
    return "flat"


def _mk_card(name, val, unit, chg, dirn, sub, key):
    return {
        "name": name, "val": _f1(val), "unit": unit, "chg": chg,
        "dir": dirn, "sub": sub, "url": _PAGE_URL[key],
    }


def build_macro():
    """返回 macro dict；单个指标抓取失败不阻塞整体"""
    data = {}
    for key, report in _REPORTS.items():
        try:
            rows = _fetch_report(report)
            data[key] = _sort_rows(rows, monthly=(key != "gdp"))
            print(f"  macro[{key}]: {len(data[key])} rows")
        except Exception as e:
            print(f"  macro[{key}] fetch error: {e}")

    cards = []

    # ---- GDP（季度累计，最新行） ----
    gdp = data.get("gdp") or []
    if gdp:
        (_, label, r), prev = gdp[-1], (gdp[-2] if len(gdp) > 1 else None)
        base = r.get("DOMESTICL_PRODUCT_BASE")
        sub = "%s·GDP %s亿元" % (label, format(int(base), ",") if base else "—")
        if prev:
            sub += "·" + _delta(r.get("SUM_SAME"), prev[2].get("SUM_SAME")).replace("上月", "上期")
        cards.append(_mk_card("GDP", r.get("SUM_SAME"), "%", "%s同比" % label,
                              _dir_rise(r.get("SUM_SAME"), prev[2].get("SUM_SAME")) if prev else "flat",
                              sub, "gdp"))

    # ---- M1 / M2 / 剪刀差 ----
    money = data.get("money") or []
    if money:
        (_, mk, r), prev = money[-1], (money[-2] if len(money) > 1 else None)
        plabel = _mlabel(mk) + "末"
        # 字段对照（已与站上 2026-07 手工值核对）：
        #   BASIC_CURRENCY  = M2（货币和准货币）  BASIC_CURRENCY_SAME = M2同比
        #   CURRENCY        = M1（货币）          CURRENCY_SAME       = M1同比
        #   FREE_CASH       = M0（流通中货币）
        m1, m2 = r.get("CURRENCY_SAME"), r.get("BASIC_CURRENCY_SAME")
        m1b, m2b = r.get("CURRENCY"), r.get("BASIC_CURRENCY")
        cards.append(_mk_card(
            "M1货币", m1, "%", "%s同比" % plabel,
            _dir_rise(m1, prev[2].get("CURRENCY_SAME")) if prev else "flat",
            "%s·M1余额 %.2f万亿元" % (plabel, float(m1b) / 1e4) if m1b else "%s·M1同比" % plabel,
            "money"))
        cards.append(_mk_card(
            "M2货币", m2, "%", "%s同比" % plabel,
            _dir_rise(m2, prev[2].get("FREE_CASH_SAME")) if prev else "flat",
            "%s·M2余额 %.2f万亿元" % (plabel, float(m2b) / 1e4) if m2b else "%s·M2同比" % plabel,
            "money"))
        if m1 is not None and m2 is not None:
            gap = round(float(m2) - float(m1), 1)
            gap_prev = None
            if prev:
                p1, p2 = prev[2].get("CURRENCY_SAME"), prev[2].get("BASIC_CURRENCY_SAME")
                if p1 is not None and p2 is not None:
                    gap_prev = round(float(p2) - float(p1), 1)
            cards.append(_mk_card(
                "M2-M1剪刀差", gap, "pct",
                ("收窄" if gap_prev is not None and gap < gap_prev else
                 "走阔" if gap_prev is not None and gap > gap_prev else "持平"),
                ("pos" if gap_prev is not None and gap < gap_prev else
                 "neg" if gap_prev is not None and gap > gap_prev else "flat"),
                "M2 %s%% - M1 %s%% = %spct" % (_f1(m2), _f1(m1), _f1(gap)),
                "money"))

    # ---- CPI / PPI / PMI / 工业增加值 / 社零 ----
    def _latest(key):
        rows = data.get(key) or []
        return (rows[-1], rows[-2] if len(rows) > 1 else None) if rows else (None, None)

    (cur, prev) = _latest("cpi")
    if cur:
        mk = cur[1]
        plabel = _mlabel(mk)
        cards.append(_mk_card(
            "CPI同比", cur[2].get("NATIONAL_SAME"), "%", "%s同比" % plabel,
            _dir_rise(cur[2].get("NATIONAL_SAME"), prev[2].get("NATIONAL_SAME")) if prev else "flat",
            "%s·全国居民消费价格·%s" % (plabel, _delta(cur[2].get("NATIONAL_SAME"), prev[2].get("NATIONAL_SAME")) if prev else "同比"),
            "cpi"))
    (cur, prev) = _latest("ppi")
    if cur:
        plabel = _mlabel(cur[1])
        cards.append(_mk_card(
            "PPI同比", cur[2].get("BASE_SAME"), "%", "%s同比" % plabel,
            _dir_rise(cur[2].get("BASE_SAME"), prev[2].get("BASE_SAME")) if prev else "flat",
            "%s·工业生产者出厂价格·%s" % (plabel, _delta(cur[2].get("BASE_SAME"), prev[2].get("BASE_SAME")) if prev else "同比"),
            "ppi"))
    (cur, prev) = _latest("pmi")
    if cur:
        plabel = _mlabel(cur[1])
        v = cur[2].get("MAKE_INDEX")
        cards.append(_mk_card(
            "PMI", v, "%", "%s·制造业" % plabel,
            "pos" if v is not None and float(v) >= 50 else "neg",
            "%s·制造业PMI·荣枯线%s" % (plabel, "上" if v is not None and float(v) >= 50 else "下"),
            "pmi"))
    (cur, prev) = _latest("indus")
    if cur:
        plabel = _mlabel(cur[1])
        acc = cur[2].get("BASE_ACCUMULATE")
        sub = "%s·规上工业增加值" % plabel
        if acc is not None:
            sub += "·1-%s累计%s%%" % (plabel.split("年")[1].lstrip("0"), _f1(acc))
        cards.append(_mk_card(
            "工业增加值", cur[2].get("BASE_SAME"), "%", "%s同比" % plabel,
            _dir_rise(cur[2].get("BASE_SAME"), prev[2].get("BASE_SAME")) if prev else "flat",
            sub, "indus"))
    (cur, prev) = _latest("retail")
    if cur:
        plabel = _mlabel(cur[1])
        acc = cur[2].get("RETAIL_ACCUMULATE_SAME")
        sub = "%s·社会消费品零售总额" % plabel
        if acc is not None:
            sub += "·1-%s累计同比%s%%" % (plabel.split("年")[1].lstrip("0"), _f1(acc))
        cards.append(_mk_card(
            "社会消费品零售总额", cur[2].get("RETAIL_TOTAL_SAME"), "%", "%s同比" % plabel,
            _dir_rise(cur[2].get("RETAIL_TOTAL_SAME"), prev[2].get("RETAIL_TOTAL_SAME")) if prev else "flat",
            sub, "retail"))

    # ---- 趋势序列：CPI/PPI/PMI 近 13 个月 ----
    series = {"dates": [], "cpi": [], "ppi": [], "pmi": []}
    if data.get("pmi"):
        months = [k for k, _, _ in data["pmi"]][-13:]
        series["dates"] = months
        for key, field in (("cpi", "NATIONAL_SAME"), ("ppi", "BASE_SAME"), ("pmi", "MAKE_INDEX")):
            m = {k: r.get(field) for k, _, r in (data.get(key) or [])}
            series[key] = [m.get(d) for d in months]

    period_label = (series["dates"][-1] if series["dates"] else
                    (money[-1][1] if money else ""))
    return {
        "lastUpdated": bj_now("%Y-%m-%d"),
    "generatedAt": bj_now(),
        "periodLabel": period_label,
        "cards": cards,
        "series": series,
    }


def update_macro():
    """抓取并写 data/macro.json；任何异常向上抛，由调用方兜底"""
    print("Updating macro indicators (L0)...")
    macro = build_macro()
    if not macro["cards"]:
        print("  !! 未抓到任何宏观指标，保留原 macro.json")
        return
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(macro, f, ensure_ascii=False, indent=2)
    print("  macro.json: %d cards, series 至 %s" % (len(macro["cards"]), macro["periodLabel"]))


if __name__ == "__main__":
    update_macro()
