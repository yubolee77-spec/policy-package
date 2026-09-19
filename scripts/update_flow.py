#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L6 资金流向：官方「钱投向哪」文件的月 / 季 / 年节奏与行业分布。

设计要点（与 L0~L5 的边界，避免重复展示）：
  · L3 历年政策对比 = 政策「表述」对比（文本 + 定调词，3 年窗口）
  · L4 本月文件     = 党媒评论原文
  · L5 证监会动态   = 监管口径（罚单 / 发行上市审核 / 官媒定调）
  · L2 政策信息源   = 各栏目最新文件入口卡片
  · L6（本脚本）    = 资金「去向」口径：部委专项资金 / 专项债与特别国债 /
                      试点示范先行区 / 一级市场融资，按行业聚合，按月·季·年与上周期比。

可溯源原则：每条都带官方原文 URL；节奏指标用「官方发布文件条数」，
标题或摘要中出现金额（亿元 / 万元）时一并抽取展示，抽不到不编造。

数据通道（全部为境内可抓、且 GitHub Actions 已验证可达的来源）：
  1) gov.cn 政策库检索接口 sousuo.www.gov.cn/search-gov/data
     —— update_compare.py / update_sources.py / update_data.py 共用，CI 稳定可达
  2) 财政部官网栏目（政策发布 / 财政新闻）
     —— 专项资金、补助资金、预算下达类文件的第一发布渠道
  3) data/csrc.json（L5 已抓的发行上市审核台账）
     —— 一级市场融资节奏，零新增请求，直接复用

累积库：data/flow_archive.json（按 URL 去重，逐日累积，月度 / 季度序列随天数自然变厚）
输出：  data/flow.json（只保留今年 + 去年，供前端渲染）
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "flow.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "flow_archive.json")
LATEST_FILE = os.path.join(DATA_DIR, "latest.json")
CSRC_FILE = os.path.join(DATA_DIR, "csrc.json")

API_BASE = "https://sousuo.www.gov.cn/search-gov/data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sousuo.www.gov.cn/",
}
HTML_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "text/html,application/xhtml+xml,*/*",
}

BJ = timezone(timedelta(hours=8))          # CI runner 是 UTC，一律换算北京时间

LOOKBACK_MONTHS = 14        # 首次打底回溯月数（累积库为空时）
MAX_PAGES = 5               # 单关键词最多翻页数（每页最多 300 条）
ARCHIVE_MAX = 6000          # 累积库条目上限
OUT_KEEP_DAYS = 800         # flow.json 只保留近 N 天条目（够覆盖今年 + 去年对比）
WORKERS = 8

# ── 四个资金通道 ─────────────────────────────────────────────
# must  : 标题必须命中的强过滤词（gov.cn 是全文检索，标题命中才算「该主题文件」）
# noise : 标题命中即剔除（答记者问 / 解读 / 吹风会 / 监管局工作动态等非资金文件）
# dim   : 该通道的归类维度标签（前三个按行业，融资按「审核类型」）
NEWS_NOISE = (r"答记者问|解读|一图|政策问答|新闻发布会|征求意见|吹风会|看点|详解|聚焦|"
              r"如何|透视|盘点|侧记|综述|观察|回顾|探访|访谈|评论|述评|专访")
CHANNELS = [
    dict(
        key="special_fund", label="专项资金 / 预算下达", icon="💰", dim="行业",
        desc="部委下达的专项资金、补助资金、中央预算内投资与转移支付文件",
        sources="财政部·政策发布 / gov.cn 政策库",
        # 必须是「资金类文件」本身，不能只是提到"投资"
        must=r"专项资金|补助资金|预算下达|转移支付|以奖代补|贴息|中央预算内投资|"
             r"资金管理办法|资金分配|拨款",
        noise=NEWS_NOISE + r"|监管局|绩效评价|工作动态|抽查|复核|自评",
        # 只取「政策发布」栏目：财政新闻栏目多为监管局动态，不属于资金文件。
        # index_1.htm 起为历史分页（列表页按时间倒序），翻 4 页可覆盖约一年。
        mof_pages=["https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/"],
        mof_indexes=["", "index_1.htm", "index_2.htm", "index_3.htm", "index_4.htm"],
    ),
    dict(
        key="bond", label="专项债 / 特别国债", icon="🏗", dim="行业",
        desc="地方政府专项债券、超长期特别国债、债务限额类文件（官方月度统计已停更，见页脚口径说明）",
        sources="gov.cn 政策库",
        must=r"专项债|地方政府债券|特别国债|债务限额|债券资金|债券发行",
        noise=NEWS_NOISE,
        mof_pages=[],
    ),
    dict(
        key="pilot", label="试点 / 示范 / 先行区", icon="🧪", dim="行业",
        desc="新公布的试点城市、示范工程、先行区与试验区名单",
        sources="gov.cn 政策库",
        must=r"试点|示范|先行|试验区",
        noise=NEWS_NOISE + r"|经验|案例|成效|进展",
        mof_pages=[],
    ),
    dict(
        key="capital", label="一级市场融资", icon="📈", dim="类型",
        desc="REITs、首发上市、并购重组与再融资的放行节奏（不含二级市场行情）",
        sources="证监会审核台账（L5 复用） / gov.cn 政策库",
        must=r"REITs|上市|融资|并购|重组|基金|证券",
        noise=NEWS_NOISE + r"|风险提示|投教|投资者",
        mof_pages=[],
    ),
]

# 一级市场融资按「审核类型」归类（公司名无法判断行业，硬套行业会全是"综合"）
_CAPITAL_RULES = [
    ("首发上市（IPO）", r"首次公开发行|首发|上市委|IPO"),
    ("REITs 注册", r"REITs|不动产投资信托|基础设施证券投资基金|封闭式.*基金"),
    ("并购重组", r"并购|重组|重大资产"),
    ("再融资", r"再融资|向特定对象发行|可转债|配股|增发"),
    ("机构资格", r"合格境内机构投资者|基金销售|经营证券|业务资格|核准.*公司"),
]

# ── 行业归类（按国民经济行业分类门类归并，首个命中即采用）──────
INDUSTRY_RULES = [
    ("交通基础设施", r"公路|铁路|机场|港口|航道|轨道交通|交通|收费公路"),
    ("水利",         r"水利|水库|灌区|防洪|排涝|供水"),
    ("能源电力",     r"电网|电力|能源|光伏|风电|储能|氢能|核电|煤炭|油气|充电"),
    ("新兴产业",     r"低空|人工智能|算力|集成电路|半导体|新材料|生物制造|生物医药|"
                     r"机器人|商业航天|量子|6G|智能网联|无人机|北斗"),
    ("制造业升级",   r"制造业|中试|技术改造|设备更新|专精特新|工业|智能制造|以旧换新"),
    ("城市更新与住房", r"城中村|老旧小区|城市更新|保障性|安居|房地产|住房|棚户|危旧房"),
    ("市政与园区",   r"市政|产业园区|开发区|管网|管廊|基础设施|停车"),
    ("农业农村",     r"农业|农村|乡村振兴|种业|农田|粮食|乡村"),
    ("生态环保",     r"生态|环境|污染|节能降碳|碳达峰|碳中和|绿色|循环|废弃"),
    ("教科文卫",     r"教育|学校|医疗|卫生|养老|文化|旅游|体育|科普|托育|医院"),
    ("消费与流通",   r"消费|商贸|流通|物流|电商|零售|批发|供销"),
    ("对外开放",     r"自贸|开放|跨境|口岸|保税|外资|出海|签证"),
    ("数据与信息",   r"数据|数字经济|政务|通信|网络|信息化|人工智能应用|数字"),
    ("金融与资本",   r"金融|资本市场|基金|REITs|上市|并购|重组|银行|保险|债券|私募|证券"),
]
INDUSTRY_OTHER = "综合与其他"

MONEY_RE = re.compile(r"(\d[\d,，]*(?:\.\d+)?)\s*(亿元|万元)")

_CAT_KEYS = ("gongwen", "bumenfile", "otherfile")


# ── 时间工具（一律北京时间）───────────────────────────────────
def bj_now(fmt="%Y-%m-%d %H:%M"):
    return datetime.now(BJ).strftime(fmt)


def bj_today():
    return datetime.now(BJ).date()


def month_key(d):
    return "%04d-%02d" % (d.year, d.month)


def month_key_shift(key, delta):
    y, m = int(key[:4]), int(key[5:7])
    m += delta
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return "%04d-%02d" % (y, m)


def quarter_key(d):
    return "%dQ%d" % (d.year, (d.month - 1) // 3 + 1)


def quarter_key_shift(key, delta):
    y, q = int(key[:4]), int(key[-1])
    q += delta
    while q < 1:
        q += 4
        y -= 1
    while q > 4:
        q -= 4
        y += 1
    return "%dQ%d" % (y, q)


def year_key(d):
    return "%d" % d.year


def month_label(key):
    return "%d年%d月" % (int(key[:4]), int(key[5:7]))


def quarter_label(key):
    return "%s年第%d季度" % (key[:4], int(key[-1]))


def period_keys(kind, today):
    """返回（本周期 key 列表，含上周期对照的完整序列）。"""
    if kind == "month":
        keys = [month_key(date(today.year, m, 1)) for m in range(1, 13)]
        return keys
    if kind == "quarter":
        return ["%dQ%d" % (today.year, q) for q in range(1, 5)]
    return ["%d" % y for y in (today.year - 1, today.year)]


def key_of(kind, d):
    if kind == "month":
        return month_key(d)
    if kind == "quarter":
        return quarter_key(d)
    return year_key(d)


def prev_key(kind, key):
    if kind == "month":
        return month_key_shift(key, -1)
    if kind == "quarter":
        return quarter_key_shift(key, -1)
    return "%d" % (int(key) - 1)


def label_of(kind, key):
    if kind == "month":
        return month_label(key)
    if kind == "quarter":
        return quarter_label(key)
    return "%s年" % key


# ── HTTP / 解析工具 ──────────────────────────────────────────
def safe_json(url, timeout=25, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            raw = urllib.request.urlopen(req, timeout=timeout).read()
            if raw[:2] == b"\x1f\x8b":
                import gzip
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            if i + 1 < tries:
                time.sleep(1.0)
    return None


def safe_html(url, timeout=20, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HTML_HEADERS)
            raw = urllib.request.urlopen(req, timeout=timeout).read()
            if raw[:2] == b"\x1f\x8b":
                import gzip
                raw = gzip.decompress(raw)
            for enc in ("utf-8", "gbk", "gb18030"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("utf-8", "ignore")
        except Exception:
            if i + 1 < tries:
                time.sleep(1.0)
    return ""


def norm_title(s):
    """去 <em> 高亮标签、零宽字符与多余空白。"""
    s = re.sub(r"</?em>", "", s or "")
    s = re.sub(r"[\u200b-\u200f\ufeff\u3000]+", "", s)
    return re.sub(r"\s+", "", s).strip()


def parse_date(raw):
    """把 2026.09.18 / 2026-09-18 / 20260918 解析为 date；失败返回 None。"""
    s = (raw or "").strip()
    m = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.match(r"(\d{4})(\d{2})(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def date_from_url(u):
    m = re.search(r"/t(\d{8})_", u or "") or re.search(r"/(\d{6})/", u or "")
    if not m:
        return None
    g = m.group(1)
    if len(g) == 6:                                   # /202609/ 形式 → 只到月，取 1 号
        return date(int(g[:4]), int(g[4:6]), 1)
    return parse_date(g)


def short_org(org):
    org = (org or "").strip()
    if not org:
        return "gov.cn"
    for long, short in [
        ("国家发展和改革委员会", "发改委"), ("国家发展改革委", "发改委"),
        ("工业和信息化部", "工信部"), ("财政部", "财政部"),
        ("中国人民银行", "央行"), ("中国证券监督管理委员会", "证监会"),
        ("住房和城乡建设部", "住建部"), ("国家能源局", "能源局"),
        ("交通运输部", "交通运输部"), ("农业农村部", "农业农村部"),
        ("科学技术部", "科技部"), ("生态环境部", "生态环境部"),
        ("商务部", "商务部"), ("水利部", "水利部"),
        ("国家市场监督管理总局", "市场监管总局"), ("国家数据局", "数据局"),
        ("国务院办公厅", "国务院办公厅"), ("国务院", "国务院"),
    ]:
        if long in org:
            return short
    return org if len(org) <= 12 else org[:11] + "…"


def classify_industry(text):
    for name, pat in INDUSTRY_RULES:
        if re.search(pat, text):
            return name
    return INDUSTRY_OTHER


def classify_dim(ch, text):
    """按通道的归类维度打标：融资通道归到「审核类型」，其余归到行业。"""
    if ch.get("dim") == "类型":
        for name, pat in _CAPITAL_RULES:
            if re.search(pat, text):
                return name
        return "其他审核"
    return classify_industry(text)


def extract_amount_yi(text):
    """从文本抽金额并折算为亿元；抽不到返回 None。"""
    best = None
    for num, unit in MONEY_RE.findall(text or ""):
        try:
            v = float(num.replace(",", "").replace("，", ""))
        except ValueError:
            continue
        yi = v if unit == "亿元" else v / 10000.0
        if yi <= 0 or yi > 200000:          # 过滤明显异常值
            continue
        if best is None or yi > best:
            best = yi
    return round(best, 2) if best else None


# ── 通道 1~4 的 gov.cn 政策文件库通道 ────────────────────────
def search_api(q="", pages=MAX_PAGES):
    """gov.cn 政策文件库翻页取文件列表（按发布时间倒序，新版在前）。

    ⚠ 不要试图给这个接口传关键词（踩过两次，记录下来免得再改回去）：
      ① 只给 q、不给 searchfield 时服务端**直接忽略 q**，返回的是最新列表，
         不同关键词拿到的是同一批数据；
      ② 加上 searchfield=title 后 q 才生效，但那个标题索引明显滞后——
         「专项资金」只检索到 64 条、最新一条到 2025-12，2026 年整年查不到；
         同一关键词走 ① 的列表能拿到 14 个月内 886 条。
    所以本层的做法是：拿 ① 的列表当「近期政策文件池」（约 1500 条，正好覆盖
    LOOKBACK_MONTHS 窗口），各通道再用标题正则（CHANNELS[*]["must"]）在池里
    挑自己的主题；更早的历史由 flow_archive.json 累积。
    """
    items, seen = [], set()
    for p in range(1, pages + 1):
        url = ("%s?t=zhengcelibrary&q=%s&sort=pubtime&sortType=1&p=%d&n=100"
               % (API_BASE, urllib.parse.quote(q), p))
        data = safe_json(url)
        sv = (data or {}).get("searchVO")
        if sv is None:
            # 请求失败、或 200 但 searchVO 为空（实测多为**被限流**，见 MEMORY 陷阱 A4）。
            # 停止翻页即可：本层各周期数字都从累积库算，拿不到新条目只是本轮少收录，
            # 不会把已有数据写成 0。别在这里改成「当作 0 条」。
            break
        cat = sv.get("catMap") or {}
        got = 0
        for c in _CAT_KEYS:
            for it in ((cat.get(c) or {}).get("listVO") or []):
                key = it.get("url") or it.get("id")
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(it)
                got += 1
        if got == 0:
            break
        time.sleep(0.25)
    return items


def collect_from_search(ch, cutoff, pool):
    """在「近期政策文件池」里按通道的标题正则筛出该主题的文件。

    池子只取一次（见 search_api 的说明），四个通道共用：
    原先每个通道各发 5 个关键词 × 5 页 = 25 次请求，拿到的是同一批数据。
    """
    out = []
    for it in pool:
        title = norm_title(it.get("title"))
        if not title or re.search(ch["noise"], title):
            continue
        if not re.search(ch["must"], title):
            continue
        d = parse_date(it.get("pubtimeStr")) or date_from_url(it.get("url", ""))
        if not d or d < cutoff or d > bj_today():
            continue
        url = it.get("url") or ""
        if not url.startswith("http"):
            continue
        summary = norm_title(it.get("summary"))[:180]
        out.append({
            "url": url,
            "title": title,
            "date": d.isoformat(),
            "org": short_org(it.get("puborg")),
            "channel": ch["key"],
            "industry": classify_dim(ch, title + summary),
            "amountYi": extract_amount_yi(title + " " + summary),
            "src": "gov.cn 政策库",
        })
    return out


# ── 财政部栏目（政策发布 / 财政新闻）─────────────────────────
_LINK_RE = re.compile(r'<a[^>]+href="([^"]+\.htm[l]?)"[^>]*>(.*?)</a>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_MONEY_SKIP = re.compile(r"答记者问|解读|问答|一图|视频|图片")


def collect_from_mof(ch, cutoff):
    """财政部栏目列表页：标题命中「资金 / 预算 / 补助」等词的文件。"""
    out = []
    for page in ch["mof_pages"]:
        for idx in (ch.get("mof_indexes") or [""]):
            html = safe_html(urllib.parse.urljoin(page, idx))
            if not html:
                continue
            for href, label in _LINK_RE.findall(html):
                title = norm_title(_TAG_RE.sub("", label))
                if len(title) < 8 or _MONEY_SKIP.search(title):
                    continue
                if not re.search(ch["must"], title):
                    continue
                url = urllib.parse.urljoin(page, href)
                d = date_from_url(url)
                if not d or d < cutoff or d > bj_today():
                    continue
                # 列表页标题往往就是文件标题；摘要留给前端点击原文核验
                out.append({
                    "url": url,
                    "title": title,
                    "date": d.isoformat(),
                    "org": "财政部",
                    "channel": ch["key"],
                    "industry": classify_dim(ch, title),
                    "amountYi": extract_amount_yi(title),
                    "src": "财政部官网栏目",
                })
            time.sleep(0.2)
    return out


# ── 复用 L1 已抓到的政策文件（零新增请求）────────────────────
def collect_from_latest(cutoff):
    """latest.json 的 timeline 已由 update_data 抓好，这里只做资金类筛选。"""
    try:
        with open(LATEST_FILE, encoding="utf-8") as f:
            latest = json.load(f) or {}
    except Exception:
        return []
    out = []
    for it in latest.get("timeline") or []:
        title = norm_title(it.get("title"))
        if not title:
            continue
        hit = None
        for ch in CHANNELS:
            if re.search(ch["noise"], title):
                continue
            if re.search(ch["must"], title):
                hit = ch
                break
        if not hit:
            continue
        d = parse_date(it.get("date"))
        if not d or d < cutoff or d > bj_today():
            continue
        summary = (it.get("summary") or "")[:180]
        out.append({
            "url": it.get("url") or "",
            "title": title,
            "date": d.isoformat(),
            "org": short_org((it.get("desc") or "").replace("最新政策文件", "")
                             .replace("最新动态", "").replace("最新数据发布", "")),
            "channel": hit["key"],
            "industry": classify_dim(hit, title + summary),
            "amountYi": extract_amount_yi(title + " " + summary),
            "src": "L1 政策速览",
        })
    return [x for x in out if x["url"].startswith("http")]


# ── 复用 L5 的发行上市审核台账（一级市场融资节奏）───────────
def collect_from_csrc(cutoff):
    try:
        with open(CSRC_FILE, encoding="utf-8") as f:
            csrc = json.load(f) or {}
    except Exception:
        return []
    out = []
    for row in csrc.get("approval") or []:
        title = norm_title(row.get("title"))
        d = parse_date(row.get("date"))
        if not title or not d or d < cutoff or d > bj_today():
            continue
        url = row.get("url") or ""
        if not url.startswith("http"):
            continue
        out.append({
            "url": url,
            "title": title,
            "date": d.isoformat(),
            "org": short_org(row.get("party") or "证监会"),
            "channel": "capital",
            "industry": classify_dim(CHANNELS[-1], title),
            "amountYi": None,
            "src": "证监会审核台账",
        })
    return out


# ── 累积库 ──────────────────────────────────────────────────
def load_archive():
    try:
        with open(ARCHIVE_FILE, encoding="utf-8") as f:
            arc = json.load(f) or {}
        items = arc.get("items") or []
        if isinstance(items, list):
            return items
    except Exception:
        pass
    return []


def merge_archive(old, new):
    """按 URL 去重合并，保留最早的归类（人工/首轮归类更可信）。"""
    seen, merged = {}, []
    for it in old:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen[u] = it
        merged.append(it)
    added = 0
    for it in new:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen[u] = it
        merged.append(it)
        added += 1
    merged.sort(key=lambda x: x.get("date") or "", reverse=True)
    return merged[:ARCHIVE_MAX], added


def save_archive(items):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated": bj_now(), "items": items}, f,
                  ensure_ascii=False, indent=2)


# ── 聚合 ────────────────────────────────────────────────────
def period_stat(rows, kind, key):
    """统计某周期：条数 / 金额合计 / 行业分布。"""
    n, amt, ind = 0, 0.0, defaultdict(int)
    has_amt = 0
    for r in rows:
        if r["_k"][kind] != key:
            continue
        n += 1
        ind[r["industry"]] += 1
        if r.get("amountYi"):
            amt += r["amountYi"]
            has_amt += 1
    return {"n": n, "amountYi": round(amt, 2), "amountCount": has_amt,
            "industries": dict(ind)}


def delta_pct(cur, prev):
    if prev in (0, None):
        return None if not cur else 100.0
    return round((cur - prev) * 100.0 / prev, 1)


def build_channel(ch, rows, today):
    """产出单通道的三档周期数据 + 行业明细。"""
    res = {"key": ch["key"], "label": ch["label"], "icon": ch["icon"],
           "dim": ch.get("dim", "行业"),
           "desc": ch["desc"], "sources": ch["sources"], "unit": "件",
           "period": {}, "series": {}, "industries": {}}
    for kind in ("month", "quarter", "year"):
        keys = period_keys(kind, today)
        cur_key = key_of(kind, today)
        pk = prev_key(kind, cur_key)
        cur = period_stat(rows, kind, cur_key)
        prev = period_stat(rows, kind, pk)
        # 序列（只输出已过去的周期，未来周期给 0 便于画图）
        series = []
        for k in keys:
            st = period_stat(rows, kind, k)
            series.append({"key": k, "label": label_of(kind, k), "n": st["n"],
                           "amountYi": st["amountYi"]})
        res["series"][kind] = series
        res["period"][kind] = {
            "cur": {"key": cur_key, "label": label_of(kind, cur_key), **cur},
            "prev": {"key": pk, "label": label_of(kind, pk), **prev},
            "deltaPct": delta_pct(cur["n"], prev["n"]),
            "deltaAmountPct": delta_pct(cur["amountYi"], prev["amountYi"]),
        }
        # 行业明细（本周期 vs 上周期）
        names = set(cur["industries"]) | set(prev["industries"])
        inds = []
        for name in names:
            c = cur["industries"].get(name, 0)
            p = prev["industries"].get(name, 0)
            items = [{"title": r["title"], "url": r["url"], "date": r["date"],
                      "org": r["org"], "amountYi": r.get("amountYi"),
                      "src": r.get("src", "")}
                     for r in rows if r["_k"][kind] == cur_key and r["industry"] == name]
            items.sort(key=lambda x: x["date"], reverse=True)
            inds.append({"name": name, "cur": c, "prev": p,
                         "deltaPct": delta_pct(c, p), "items": items[:6],
                         "totalItems": len(items)})
        inds.sort(key=lambda x: (-x["cur"], x["name"]))
        res["industries"][kind] = inds
    return res


def build_industry_movers(channels, kind):
    """跨通道行业榜：本周期新增最多 / 减少最多的行业（只统计行业维度通道）。"""
    cur_agg, prev_agg = defaultdict(int), defaultdict(int)
    first_url = {}
    for ch in channels:
        if ch.get("dim") != "行业":
            continue
        for row in ch["industries"].get(kind) or []:
            name = row["name"]
            cur_agg[name] += row["cur"]
            prev_agg[name] += row["prev"]
            if row["items"] and name not in first_url:
                first_url[name] = row["items"][0]["url"]
    rows = []
    for name in set(cur_agg) | set(prev_agg):
        c, p = cur_agg[name], prev_agg[name]
        rows.append({"name": name, "cur": c, "prev": p,
                     "delta": c - p, "deltaPct": delta_pct(c, p),
                     "url": first_url.get(name, "")})
    up = sorted([r for r in rows if r["delta"] > 0],
                key=lambda x: (-x["delta"], -x["cur"]))[:6]
    down = sorted([r for r in rows if r["delta"] < 0],
                  key=lambda x: (x["delta"], -x["cur"]))[:6]
    flat = sorted([r for r in rows if r["delta"] == 0],
                  key=lambda x: -x["cur"])[:4]
    return {"up": up, "down": down, "flat": flat}


# ── 主流程 ──────────────────────────────────────────────────
def build():
    today = bj_today()
    generated = bj_now()
    print("L6 资金流向更新：%s（北京时间）" % generated)

    old_archive = load_archive()
    cutoff = today - timedelta(days=int(LOOKBACK_MONTHS * 30.5))
    if not old_archive:
        print("  累积库为空，按 %d 个月回溯打底（%s 起）" % (LOOKBACK_MONTHS, cutoff.isoformat()))

    fresh = []
    pool = search_api()
    print("  [政策文件池] 近期 %d 条（各通道共用，标题正则筛选）" % len(pool))
    for ch in CHANNELS:
        got = collect_from_search(ch, cutoff, pool)
        print("  [标题筛选] %-14s %d 条" % (ch["label"], len(got)))
        fresh.extend(got)
        if ch["mof_pages"]:
            mof = collect_from_mof(ch, cutoff)
            print("  [财政部栏目] %-10s %d 条" % (ch["label"], len(mof)))
            fresh.extend(mof)
    extra = collect_from_latest(cutoff)
    print("  [复用 L1 政策速览] %d 条" % len(extra))
    fresh.extend(extra)
    csrc = collect_from_csrc(cutoff)
    print("  [复用 L5 审核台账] %d 条" % len(csrc))
    fresh.extend(csrc)

    archive, added = merge_archive(old_archive, fresh)
    if added == 0 and old_archive:
        print("  本次无新增条目（沿用累积库 %d 条）" % len(archive))

    if not archive:
        print("  !! 未获得任何资金类文件，保留原有 flow.json 不覆盖")
        return

    # 计算各周期 key（只用累积库里近两年数据，够月度/季度/年度对比）
    years = (str(today.year - 1), str(today.year))
    ch_by_key = {c["key"]: c for c in CHANNELS}
    rows = []
    for it in archive:
        d = parse_date(it.get("date"))
        if not d or d.year < today.year - 1:
            continue
        it = dict(it)
        it["_k"] = {"month": month_key(d), "quarter": quarter_key(d), "year": year_key(d)}
        if not it.get("industry"):
            ch = ch_by_key.get(it.get("channel"))
            it["industry"] = classify_dim(ch, it.get("title", "")) if ch else INDUSTRY_OTHER
        rows.append(it)

    channels = []
    for ch in CHANNELS:
        sub = [r for r in rows if r["channel"] == ch["key"]]
        built = build_channel(ch, sub, today)
        cur_m = built["period"]["month"]["cur"]
        print("  %-14s 本月 %d 件（上月 %d，环比 %s%%）｜本季 %d 件｜今年 %d 件"
              % (ch["label"], cur_m["n"], built["period"]["month"]["prev"]["n"],
                 built["period"]["month"]["deltaPct"],
                 built["period"]["quarter"]["cur"]["n"],
                 built["period"]["year"]["cur"]["n"]))
        channels.append(built)

    movers = {k: build_industry_movers(channels, k)
              for k in ("month", "quarter", "year")}

    # 近期条目（供前端展开原文，最多 120 条）
    recent = sorted(rows, key=lambda x: x["date"], reverse=True)[:120]
    recent = [{k: v for k, v in r.items() if k != "_k"} for r in recent]

    out = {
        "generatedAt": generated,
        "asOf": month_key(today),
        "asOfLabel": "%d年%d月" % (today.year, today.month),
        "archiveTotal": len(archive),
        "archiveAdded": added,
        "channels": channels,
        "movers": movers,
        "recent": recent,
        "note": ("口径：以官方发布的资金类文件条数作为资金节奏指标（每项均附原文可核验）；"
                 "标题或摘要中出现金额时抽取为亿元一并展示，未抽取到的不做估算。"
                 "行业归类按国民经济行业分类门类归并。"),
    }
    save_archive(archive)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("更新 %s（累积 %d 条，本次新增 %d 条）" % (OUTPUT_FILE, len(archive), added))


def main():
    build()


if __name__ == "__main__":
    main()
