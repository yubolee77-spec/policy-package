#!/usr/bin/env python3
"""
Policy Intelligence Workbench - Daily Auto Update
Only writes to data/latest.json. NEVER touches app.js or index.html.
If any source fails, skip it and continue. The script must never crash.

更新记录 (2026-09-14):
  1. 每条记录新增 date 字段（YYYY-MM-DD），输出统一按日期降序排序
     —— 修复"页面第一眼看到的不是最新政策"的问题
  2. 发改委改抓政策发布栏目 xxgk/zcfb/tz + xxgk/zcfb/ghxwj（原文详情页），
     不再抓 xwdt/xwfb 新闻列表页 —— 修复"跳转到列表页而非原文"的问题
  3. 新增 blocks 模块（证监会/交易所动态、宏观数据发布），供前端自动渲染
  4. 抓取结果同时输出各来源最新日期，便于核对时效
  5. 每条记录自动生成 summary（摘要）+ keywords（政策定调词）+ keySentence（关键语句）
     —— 让 L1「最新政策动态」不再只有标题，与 L4「本月文件」展示效果对齐
     —— 全部由脚本从 API / 原文详情页自动提取，零手工维护
  6. 摘要通过并发抓取原文详情页生成（ThreadPoolExecutor，8 线程）

更新记录 (2026-09-11):
  切换到国务院政策文件库 API (sousuo.www.gov.cn/search-gov/data)
  - 国务院政策：API gongwen 分类
  - 各部委政策：API bumenfile 分类 + Python 按 puborg 过滤
  - API 返回的 URL 已是最终原文 URL，无需二次解析
  - 保留 HTML 爬虫作为 fallback
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from html import unescape
from urllib.parse import quote, urlparse
from urllib.request import urlopen, Request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "latest.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sousuo.www.gov.cn/",
}

MONTH_LABEL = f"{date.today().year}年{date.today().month}月"

# ── 垃圾标题/URL 过滤关键词 ──────────────────────────────────────
JUNK_KEYWORDS = [
    'icp备', 'icp证', '京icp', '沪icp', '粤icp', '备案',
    'beian.miit', '网站标识码', '公安备',
    '版权所有', '联系我们', '网站地图', '无障碍',
]

# ── API 配置 ─────────────────────────────────────────────────────
API_BASE = "https://sousuo.www.gov.cn/search-gov/data"

# ── 来源标签常量（必须与前端 app.js 的 srcIcons 保持一致）──────────
SRC_GOV = "国务院最新政策文件"
SRC_NDRC = "发改委最新政策文件"
SRC_PBC = "央行最新动态"
SRC_CSRC = "证监会最新动态"
SRC_MIIT = "工信部最新政策文件"
SRC_STATS = "国家统计局最新数据发布"
SRC_EXCHANGE = "交易所最新公告"

# 各部委在 API 返回 puborg 字段中的匹配关键词
# 注意：必须按"发布文件名 + 空格"匹配，避免把它委牵头的联合发文误归到本部门
MINISTRY_MAP = {
    "工业和信息化部": SRC_MIIT,
    "国家发展改革委": SRC_NDRC,
    "国家发展和改革委员会": SRC_NDRC,
    "中国人民银行": SRC_PBC,
    "中国证监会": SRC_CSRC,
    "中国证券监督管理委员会": SRC_CSRC,
    "国家统计局": SRC_STATS,
}


# ── 政策定调词表 ─────────────────────────────────────────────────
# 中国政策文本有一套稳定的"定调词"体系，读文件时先看这些词就能判断力度与节奏。
#   ding = 力度定调（红）：着力 / 大力 / 加力 / 坚决 ...
#   deg  = 程度节奏（黄）：持续 / 进一步 / 深化 / 稳步 ...
#   verb = 动作指向（绿）：推动 / 优化 / 培育 / 落实 ...
# 顺序即优先级：越靠前越有信号意义，提取时优先命中。
KEYWORD_RULES = [
    ("毫不动摇", "ding"), ("坚定不移", "ding"), ("坚决", "ding"),
    ("大力", "ding"), ("着力", "ding"), ("加力", "ding"), ("全力", "ding"),
    ("加大", "ding"), ("加强", "ding"), ("加快", "ding"), ("强化", "ding"),
    ("有力", "ding"), ("抓紧", "ding"), ("严格", "ding"),
    ("持续", "deg"), ("进一步", "deg"), ("深入", "deg"), ("深化", "deg"),
    ("不断", "deg"), ("逐步", "deg"), ("稳步", "deg"), ("有序", "deg"),
    ("统筹", "deg"), ("协同", "deg"), ("常态化", "deg"), ("长效", "deg"),
    ("精准", "deg"), ("系统", "deg"), ("分类", "deg"),
    ("推动", "verb"), ("推进", "verb"), ("促进", "verb"), ("支持", "verb"),
    ("优化", "verb"), ("完善", "verb"), ("健全", "verb"), ("落实", "verb"),
    ("实施", "verb"), ("开展", "verb"), ("建设", "verb"), ("培育", "verb"),
    ("壮大", "verb"), ("拓展", "verb"), ("扩大", "verb"), ("提升", "verb"),
    ("提高", "verb"), ("增强", "verb"), ("规范", "verb"), ("引导", "verb"),
    ("激发", "verb"), ("鼓励", "verb"), ("保障", "verb"), ("监管", "verb"),
    # restrict = 限制性动作（判断这条政策是在"扶持"还是"限制"）
    #   扶持：推动 / 鼓励 / 支持 / 培育 …
    #   限制：严禁 / 严控 / 遏制 / 压减 / 淘汰 …
    ("严格限制", "restrict"), ("严禁", "restrict"), ("严控", "restrict"),
    ("遏制", "restrict"), ("压减", "restrict"), ("淘汰", "restrict"),
    ("禁止", "restrict"), ("打击", "restrict"), ("整治", "restrict"),
    ("严查", "restrict"), ("查处", "restrict"), ("清理", "restrict"),
    ("防范", "restrict"), ("化解", "restrict"), ("收紧", "restrict"),
    ("限制", "restrict"), ("叫停", "restrict"),
]

# 每个类型最多标注几个、总计最多几个 —— 控制在 3 个以内，避免满屏标签
KEYWORD_PER_TYPE = 2
KEYWORD_TOTAL = 4


def extract_keywords(*texts):
    """从标题/摘要/正文中提取政策定调词，返回 [{"type","text"}, ...]。

    按词长降序匹配，命中后把该词从文本中抹掉，
    避免"加大力度"里"加大"和"力度"之类的位置重叠重复计数。
    """
    blob = " ".join(t for t in texts if t)
    if not blob:
        return []
    blob = re.sub(r'\s+', '', blob)

    ordered = sorted(KEYWORD_RULES, key=lambda kv: -len(kv[0]))
    hits = []
    for word, kind in ordered:
        if word in blob:
            hits.append((word, kind))
            blob = blob.replace(word, "\u3000")   # 抹掉，防重叠

    # 按原始优先级排序，再按类型配额截断
    prio = {w: i for i, (w, _) in enumerate(KEYWORD_RULES)}
    hits.sort(key=lambda h: prio.get(h[0], 999))

    per_type = {}
    out = []
    for word, kind in hits:
        if per_type.get(kind, 0) >= KEYWORD_PER_TYPE:
            continue
        if len(out) >= KEYWORD_TOTAL:
            break
        per_type[kind] = per_type.get(kind, 0) + 1
        out.append({"type": kind, "text": word})
    return out


# ── 正文摘要提取 ─────────────────────────────────────────────────

# 正文可能所在的容器（不同站点结构不同，按命中率排序尝试）
CONTENT_PATTERNS = [
    # 人民日报 / 经济日报数字报：正文在 <div id=ozoom>
    # 注意引号可能被省略（经济日报写作 id=ozoom），所以用 ["\']? 兼容
    r'<div[^>]*id=["\']?ozoom["\']?[^>]*>(.*?)</div>',
    r'<founder-content[^>]*>(.*?)</founder-content>',
    r'<div[^>]*id=["\']?articleContent["\']?[^>]*>(.*?)</div>',
    r'<div[^>]*class="[^"]*(?:TRS_Editor|article-content|articleContent|content_body|detail-content|view|zoom)[^"]*"[^>]*>(.*?)</div>\s*(?:</div>|<script)',
    r'<div[^>]*id="(?:UCAP-CONTENT|content|zoom|detail|post_content)"[^>]*>(.*?)</div>',
    r'<article[^>]*>(.*?)</article>',
]

# 从正文里剔除的噪声片段
NOISE_PATTERNS = [
    r'<script.*?</script>', r'<style.*?</style>', r'<!--.*?-->',
    r'<div[^>]*class="[^"]*(?:share|print|editor|prev|next|related|footer|nav)[^"]*".*?</div>',
]

SENTENCE_SPLIT = re.compile(r'[。；！？!?；;]|\n')


def html_to_text(html):
    """HTML 片段 → 干净纯文本。"""
    if not html:
        return ""
    text = html
    for pat in NOISE_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.S | re.I)
    text = re.sub(r'<(?:br|/p|/div|/li|/h\d)[^>]*>', "\n", text, flags=re.I)
    text = re.sub(r'<[^>]+>', "", text)
    text = unescape(text)
    text = text.replace('\u3000', ' ').replace('\xa0', ' ')
    text = re.sub(r'[ \t]+', " ", text)
    text = re.sub(r'\n\s*\n+', "\n", text)
    return text.strip()


def extract_article_body(html):
    """从详情页 HTML 里定位正文文本（命中不了就退化为全文去标签）。"""
    if not html:
        return ""
    for pat in CONTENT_PATTERNS:
        m = re.search(pat, html, re.S | re.I)
        if m:
            body = html_to_text(m.group(1))
            if len(body) >= 60:
                return body
    # 兜底：去掉 head / nav / footer 后整体去标签
    stripped = re.sub(r'<head.*?</head>', " ", html, flags=re.S | re.I)
    stripped = re.sub(r'<(?:nav|footer|header).*?</(?:nav|footer|header)>', " ", stripped, flags=re.S | re.I)
    return html_to_text(stripped)


# 做标题/正文比对时需要忽略的排版字符
_STRIP_CHARS = '《》“”"（）()【】[]{}\u3000 \t\r\n'

# 判断"标题后面跟的是不是元信息/过渡语"，用于决定要不要去掉重复的标题开头
# 只列明确的开场词：正文以"为/根据/现将"开头说明前面那段是重复的标题；
# 而《××条例》已经……这类标题是正文主语，不在此列，必须保留。
_META_START = re.compile(
    r'^(?:日期|发布时间|发布日期|文章来源|来源|时间)[:：]'
    r'|^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}'
    r'|^\d{4}年\d{1,2}月\d{1,2}日'
    r'|^〔'
    r'|^(?:为|根据|按照|现将|经|近日|日前|自)'
    r'|^(?:证监会|我会|央行|人民银行|统计局|工信部|发改委|银保监|商务部|财政部|国务院)'
)

# 出现的"日期：xxx来源：证监会"里的来源名，删掉后残留会显得啰嗦
_SOURCE_NAMES = [
    '中国证券监督管理委员会', '中国证监会', '证监会',
    '中国人民银行', '人民银行', '央行',
    '国家统计局', '统计局',
    '国家发展和改革委员会', '国家发展改革委', '发展改革委', '发改委',
    '工业和信息化部', '工信部',
    '中华人民共和国国务院', '国务院',
]


def _strip_source_name(body):
    """去掉残留的来源名开头（"证监会为贯彻……" → "为贯彻……"）。"""
    for name in _SOURCE_NAMES:
        if body.startswith(name):
            rest = body[len(name):].lstrip()
            if len(rest) >= 20:
                return rest
            break
    return body


def _dedup_title_prefix(body, title):
    """正文开头常把标题原样印一遍，去掉这段重复，避免摘要以标题开场。

    只在"标题后面紧跟的是元信息"时才删。像《市场监督管理所条例》已经……这种，
    标题是正文主语，删掉会让摘要失去主语，所以保留。
    """
    if not body or not title or len(title) < 8:
        return body
    core = title
    flat = body
    for ch in _STRIP_CHARS:
        core = core.replace(ch, '')
        flat = flat.replace(ch, '')
    if len(core) < 8 or not flat.startswith(core):
        return body
    # 逐字扫描原串，数够 core 的长度后切掉（保持原始下标）
    cnt = 0
    i = 0
    while i < len(body) and cnt < len(core):
        if body[i] not in _STRIP_CHARS:
            cnt += 1
        i += 1
    rest = body[i:].lstrip(_STRIP_CHARS)
    # 标题带书名号时会留下孤立的 "》"，lstrip 已清掉；再看后面是不是元信息
    return rest if _META_START.match(rest) else body


def strip_leading_noise(body, title=""):
    """去掉公文正文开头的元信息：页面时间戳、日期来源行、文号+主送机关。"""
    if not body:
        return ""
    # 1) 页面时间戳：2026/09/1409:30
    body = re.sub(r'^\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}\s*\d{0,2}:?\d{0,2}', '', body)
    # 2) 与标题重复的开场（仅当后面是元信息时才删）
    body = _dedup_title_prefix(body, title)
    # 3) 日期 / 来源标签
    #    注意不要贪婪匹配来源名：早期写法 {2,10} 会把"证监会为贯彻党的二十届四中"
    #    当成来源名一起吃掉，导致摘要从句子中间开始。
    body = re.sub(r'日期[:：][\d\-/.]{4,14}来源[:：]', '', body)
    body = re.sub(r'^(?:文章来源|来源)[:：][\u4e00-\u9fa5A-Za-z]{2,8}', '', body)
    body = re.sub(r'^(?:发布时间|发布日期|日期)[:：][\d\-/. :]{4,20}', '', body)
    body = _strip_source_name(body)
    # 只清空白，不要清《》：否则《××条例》开头的摘要会被剃掉左书名号
    body = body.lstrip('\u3000 \t\r\n')
    # 4) 文号 + 主送机关（"……〔2026〕305号各省、自治区……："）
    #    只有确实识别出主送机关才跳过；否则保留原样，
    #    否则会留下"）部署要求……"这种从括号中间开始的残句。
    m = re.search(r'〔\s*\d{4}\s*〕\s*\d+\s*号', body[:200])
    if m:
        rest = body[m.end():]
        m2 = re.match(r'[^：:。]{0,120}[：:]', rest)
        if (m2 and len(rest) >= 40
                and re.search(r'(省|市|区|县|部门|兵团|委|局|单位)', m2.group(0))):
            body = rest[m2.end():]
    return body.strip()


def clean_summary(text, limit=150, title=""):
    """把正文整理成一条摘要：合并换行、去头部噪声、在句号处收尾。"""
    if not text:
        return ""
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) >= 12]
    body = re.sub(r'\s+', '', " ".join(lines))
    body = strip_leading_noise(body, title)
    # 公文落款的"附件：xxx"不是内容本身，截掉
    body = re.split(r'附件[:：]', body)[0].strip()
    if not body:
        return ""
    if len(body) <= limit:
        return body
    cut = body[:limit]
    # 尽量在句号处断开，避免摘要以半句话结束
    for sep in ("。", "；", "，"):
        idx = cut.rfind(sep)
        if idx >= limit * 0.6:
            return cut[:idx + 1]
    return cut + "…"


# 关键语句里要排除的公文噪声
_NOISE_SENTENCE = re.compile(
    r'(附件[:：]|总理|委员长|主席令|国务院令|年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|'
    r'扫一扫|二维码|责任编辑|来源[:：]|点击查看|下载|'
    r'主管部门[:：]|^各省|^各市|^各地|^各有关部门)'   # 主送机关抬头
)


def _collect_sentences(text, limit, title=""):
    """切句并过滤掉公文落款、页码、标题复读等噪声句。"""
    core_title = re.sub(r'[《》“”"（）()【】\[\]{}\u3000\s]', '', title or '')
    out = []
    for raw in SENTENCE_SPLIT.split(text):
        s = re.sub(r'\s+', '', raw.strip())
        if not (18 <= len(s) <= limit):
            continue
        if _NOISE_SENTENCE.search(s):
            continue
        # 与标题高度重合的句子（公文常把标题印在正文第一行）不算关键语句
        if core_title and len(core_title) >= 8 and core_title[:10] in s:
            continue
        out.append(s)
    return out


def _find_summary_end(text, summary):
    """在正文里定位摘要结束的位置，让关键语句从摘要之后开始，避免重复。"""
    if not text or not summary or len(summary) < 40:
        return 0
    tail = summary[-16:]
    # 正文里可能夹着换行，用 \s* 连接每个字符来容忍空白差异
    pat = r'\s*'.join(re.escape(c) for c in tail)
    m = re.search(pat, text)
    if m:
        return m.end()
    return len(summary)


def pick_key_sentence(text, keywords, limit=110, title="", summary=""):
    """挑一句能代表文件主旨的关键语句。

    只在"摘要之后"的正文里找，这样关键语句是摘要的补充而非复述。
    若该文件除摘要外没有其他可摘句子（如只有一页通知），返回空串。
    """
    if not text:
        return ""
    skip = _find_summary_end(text, summary)
    # 剩余内容太少就不硬凑，宁可不显示
    if len(text) - skip < 60:
        return ""
    sents = _collect_sentences(text[skip:], limit, title)
    if not sents:
        return ""
    # keywords 已按优先级排序，先命中先返回
    for k in (keywords or []):
        for s in sents:
            if k["text"] in s:
                return s + "。"
    return sents[0] + "。"


def fetch_article_digest(url, title=""):
    """抓取原文详情页，返回 (摘要, 正文文本)。失败返回 ("", "")。"""
    html = safe_fetch(url, timeout=12)
    if not html or len(html) < 400:
        return "", ""
    body = extract_article_body(html)
    # 正文太短说明没定位到，可能抓到列表页/错误页
    if len(body) < 60:
        return "", ""
    return clean_summary(body, title=title), body


# ── HTTP 工具 ─────────────────────────────────────────────────────
# 注意：上面 fetch_article_digest 依赖下面的 safe_fetch / safe_fetch_json，
# Python 在函数调用时才解析名字，所以定义顺序不影响运行。

def safe_fetch(url, timeout=15):
    """Fetch URL content, return None on any error."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def safe_fetch_json(url, timeout=15):
    """Fetch URL and parse JSON, return None on any error."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def is_junk(title, url):
    """过滤备案号、版权声明等垃圾链接。"""
    combined = (title + url).lower()
    for kw in JUNK_KEYWORDS:
        if kw in combined:
            return True
    if len(title.strip()) < 8:
        return True
    if 'beian' in url.lower():
        return True
    return False


def normalize_date(raw):
    """把各类日期写法统一成 YYYY-MM-DD，无法识别时返回空串。"""
    if not raw:
        return ""
    if isinstance(raw, str):
        s = raw.strip()
        # 2026.09.12 / 2026-09-12 / 2026/09/12
        m = re.match(r'^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', s)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        # 20260912
        m = re.match(r'^(\d{4})(\d{2})(\d{2})$', s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return ""
    return ""


def date_from_url(url):
    """从 URL 路径里的 /202609/t20260912_xxx.html 推断日期。

    只认 tYYYYMMDD_ 这一种明确写法，并且要求月份 01-12、日期 01-31 合法。
    不要放宽成"任意 8 位数字"——央行 URL 里的 /2026091115515046822/ 会被误判成 1134 年。
    """
    if not url:
        return ""
    m = re.search(r'/t(\d{4})(\d{2})(\d{2})_', url)
    if not m:
        # 央行 URL 形如 /goutongjiaoliu/113456/113469/2026091115515046822/index.html
        # 前 8 位是发布日期 YYYYMMDD，后面才是时间戳
        m = re.search(r'/(\d{4})(\d{2})(\d{2})\d{9,}/', url)
    if not m:
        return ""
    y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return ""
    return f"{y}-{mo:02d}-{d:02d}"


def date_from_md(md):
    """把列表页的 "09-11" 补成 YYYY-MM-DD（证监会等站点只给月日）。

    只接受"距今 45 天内"的月日，否则返回空串。
    列表页底部往往混有往年旧闻（如 2021 年的发布会），
    如果不做这个约束，那些旧条目的"09-24"会被当成今年的日期，把排序彻底带偏。
    """
    m = re.match(r'^(\d{1,2})[-/.](\d{1,2})$', (md or '').strip())
    if not m:
        return ""
    mo, d = int(m.group(1)), int(m.group(2))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return ""
    today = date.today()
    for y in (today.year, today.year - 1):
        try:
            cand = date(y, mo, d)
        except ValueError:
            continue
        delta = (today - cand).days
        if 0 <= delta <= 45:
            return cand.strftime("%Y-%m-%d")
    return ""


def clean_link(link, base_url):
    """构造完整 URL，支持相对路径拼接，避免双斜杠。"""
    if not link:
        return ""
    if link.startswith("http"):
        return link
    parsed = urlparse(base_url if base_url.startswith("http") else "https://" + base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    page_path = parsed.path.strip("/")
    if link.startswith("/"):
        return domain + link
    link = re.sub(r'^(\./)+', '', link)
    link = re.sub(r'^(\.\./)+', '', link)
    link = link.lstrip("/")
    if page_path:
        return f"{domain}/{page_path}/{link}"
    return f"{domain}/{link}"


def make_item(title, url, src, dt="", summary=""):
    """统一构造条目。

    summary 只做基础清洗（去标签、压空白），真正的摘要生成与关键词提取
    在主流程最后统一进行，确保所有来源口径一致。
    """
    title = re.sub(r'<[^>]+>', ' ', title or '')
    title = re.sub(r'\s+', ' ', unescape(title)).strip()
    summ = re.sub(r'<[^>]+>', ' ', summary or '')
    summ = re.sub(r'\s+', '', unescape(summ)).strip()
    return {
        "title": title,
        "desc": src,
        "url": url,
        "date": dt or date_from_url(url),
        "summary": summ,
    }


# ── API 数据源（主要）────────────────────────────────────────────

def fetch_gov_api():
    """通过国务院政策文件库 API 获取数据。

    该 API 覆盖国务院公文 + 各部委文件，且 url 已是 gov.cn 原文详情页。
    n=100（API 单页上限），一次请求即可拿到全部 100 条，再按 puborg 分派来源。
    排序按 pubtime 倒序，配合每条记录的 date 字段，前端可稳定降序展示。
    """
    all_items = []
    url = f"{API_BASE}?t=zhengcelibrary&q=&sort=pubtime&sortType=1&p=1&n=100"
    data = safe_fetch_json(url)
    if not data or "searchVO" not in data:
        return all_items

    cat_map = data["searchVO"].get("catMap", {}) or {}

    # 1. 国务院公文
    for item in (cat_map.get("gongwen", {}) or {}).get("listVO", []) or []:
        title = item.get("title", "").strip()
        link = item.get("url", "")
        if is_junk(title, link):
            continue
        dt = normalize_date(item.get("pubtimeStr")) or date_from_url(link)
        all_items.append(make_item(title, link, SRC_GOV, dt, item.get("summary", "")))

    # 2. 部门文件：按 puborg 首个发布单位分派到对应来源
    quota = {}   # 每个来源最多保留 8 条
    for item in (cat_map.get("bumenfile", {}) or {}).get("listVO", []) or []:
        puborg = (item.get("puborg") or "").strip()
        if not puborg:
            continue
        # 取第一个发布单位（空格分隔），避免联合发文里非牵头部门抢占
        lead = re.split(r'[\s　]+', puborg)[0]
        src = MINISTRY_MAP.get(lead)
        if not src and lead.endswith("办公厅"):
            src = MINISTRY_MAP.get(lead[:-3])
        if not src:
            continue
        if quota.get(src, 0) >= 8:
            continue
        title = item.get("title", "").strip()
        link = item.get("url", "")
        if is_junk(title, link):
            continue
        dt = normalize_date(item.get("pubtimeStr")) or date_from_url(link)
        all_items.append(make_item(title, link, src, dt, item.get("summary", "")))
        quota[src] = quota.get(src, 0) + 1

    return all_items


# ── HTML 爬虫（fallback）─────────────────────────────────────────

def fetch_gov_cn_html():
    """HTML fallback: 国务院政策。"""
    url = "https://www.gov.cn/zhengce/zhengceku/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="([^"]*content_\d+\.htm[l]?)"[^>]*>([^<]{6,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, "https://www.gov.cn/zhengce/zhengceku")
        if full in seen:
            continue
        seen.add(full)
        items.append(make_item(title, full, SRC_GOV))
    return items[:8]


def fetch_ndrc_html():
    """HTML fallback: 发改委政策发布（原文详情页，非新闻列表页）。

    原实现抓的是 /xwdt/xwfb/（发改委新闻发布），那是"会见/会议通稿"列表，
    点进去往往是栏目页而非政策原文——这正是用户反馈的问题。
    正确入口是 /xxgk/zcfb/ 下的 tz（通知）与 ghxwj（规范性文件）栏目。
    """
    items = []
    seen = set()
    for page in ("https://www.ndrc.gov.cn/xxgk/zcfb/tz/",
                 "https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/"):
        html = safe_fetch(page)
        if not html:
            continue
        for m in re.finditer(
                r'<a[^>]*href="(\./\d{6}/t\d{8}_\d+\.html)"[^>]*>\s*([^<]{8,})</a>', html):
            link, title = m.group(1).strip(), m.group(2).strip()
            if is_junk(title, link):
                continue
            full = clean_link(link, page)
            if full in seen:
                continue
            seen.add(full)
            items.append(make_item(title, full, SRC_NDRC))
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:8]


def fetch_pbc_html():
    """HTML fallback: 央行。"""
    url = "https://www.pbc.gov.cn/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="(/goutongjiaoliu/113456/113469/\d+/index\.html)"[^>]*>([^<]{6,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, "https://www.pbc.gov.cn")
        if full in seen:
            continue
        seen.add(full)
        items.append(make_item(title, full, SRC_PBC))
    return items[:8]


def fetch_csrc_html():
    """HTML fallback: 证监会。

    证监会列表项的结构是 <a href="...">标题</a> ... <span class="time">09-11</span>，
    日期只给"月-日"，需要向后找最近的 time span 补全年份。
    """
    url = "https://www.csrc.gov.cn/csrc/xwfb/index.shtml"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    pattern = (r'<a[^>]*href="(/csrc/c\d+/c\d+/content\.shtml)"[^>]*>([^<]{6,})</a>'
               r'(?P<tail>.{0,300}?)</li>')
    for m in re.finditer(pattern, html, re.S):
        link, title, tail = m.group(1).strip(), m.group(2).strip(), m.group(3)
        if is_junk(title, link):
            continue
        full = clean_link(link, "https://www.csrc.gov.cn")
        if full in seen:
            continue
        seen.add(full)
        tm = re.search(r'<span[^>]*class="time"[^>]*>\s*([\d\-/.]+)\s*</span>', tail)
        dt = date_from_md(tm.group(1)) if tm else ""
        items.append(make_item(title, full, SRC_CSRC, dt))
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:8]


def fetch_miit_html():
    """HTML fallback: 工信部政策文件。"""
    url = "https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/index.html"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="([^"]*art_\w+\.html)"[^>]*>([^<]{8,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, url).replace("http://", "https://")
        if full in seen:
            continue
        seen.add(full)
        items.append(make_item(title, full, SRC_MIIT, date_from_url(full)))
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:8]


def fetch_stats_html():
    """HTML fallback: 国家统计局。"""
    url = "https://www.stats.gov.cn/sj/zxfb/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="([^"]*t\d{8}_\d+\.html?)"[^>]*>\s*([^<]{8,})', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, url)
        if full in seen:
            continue
        seen.add(full)
        items.append(make_item(title, full, SRC_STATS, date_from_url(full)))
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:8]


def fetch_exchange_html():
    """交易所规则页面。

    说明：上交所/深交所的规则列表页是 JS 动态渲染的，静态 HTML 里拿不到条目，
    因此这里不做"猜链接"，而是返回列表页入口本身作为固定入口项（不参与时间线排序）。
    前端会把它们展示在「官网入口」区域。若日后找到稳定接口，可在此处替换实现。
    """
    entries = [
        ("上海证券交易所 · 业务规则", "https://www.sse.com.cn/lawandrules/sselawsrules/"),
        ("上海证券交易所 · 公募REITs信息", "https://www.sse.com.cn/reits/announcements/info/"),
        ("深圳证券交易所 · 业务规则", "https://www.szse.cn/lawrules/rule/allrules/bussiness/"),
    ]
    return [make_item(t, u, SRC_EXCHANGE, "") for t, u in entries]


# ── 摘要 / 关键词 生成配置 ───────────────────────────────────────
SUMMARY_MIN_LEN = 40      # 摘要短于这个长度就认为"需要补抓原文"
SUMMARY_LIMIT = 150       # 摘要展示长度上限
DIGEST_LIMIT = 250        # 每轮最多抓多少条原文（覆盖全部条目，留余量）
DIGEST_WORKERS = 8        # 并发线程数
BLOCK_SIZE = 10           # 每个来源在 blocks 里保留多少条


def worker_digest(item):
    """线程池工作单元：抓一条原文，返回 (item, 摘要, 正文)。"""
    try:
        summ, body = fetch_article_digest(item["url"], item.get("title", ""))
        return item, summ, body
    except Exception:
        return item, "", ""


# ════════════════════════════════════════════════════════════════
#  政策层级判定 —— "从上往下看"：中央定方向 → 部委细化路径 → 地方落实执行
# ════════════════════════════════════════════════════════════════

TIER_LABEL = {"central": "中央", "dept": "部委", "local": "地方"}

# 中央级域名（国务院 / 党中央 / 全国人大等）
_CENTRAL_HOSTS = ("www.gov.cn", "gov.cn/zhengce", "www.12371.cn", "www.npc.gov.cn",
                  "www.cppcc.gov.cn", "www.ccdi.gov.cn")
# 部委级域名
_DEPT_HOSTS = ("ndrc.gov.cn", "miit.gov.cn", "pbc.gov.cn", "csrc.gov.cn",
               "stats.gov.cn", "mof.gov.cn", "mofcom.gov.cn", "samr.gov.cn",
               "mot.gov.cn", "mohurd.gov.cn", "most.gov.cn", "nea.gov.cn",
               "cnsa.gov.cn", "miit", "customs.gov.cn", "chinatax.gov.cn")


def classify_tier(src, url=""):
    """判断条目的政策层级：central（中央）/ dept（部委）/ local（地方）。"""
    if src == SRC_GOV:
        return "central"
    if src in (SRC_NDRC, SRC_PBC, SRC_CSRC, SRC_MIIT, SRC_STATS):
        return "dept"
    host = ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        pass
    if any(host.endswith(h) or h in (url or "") for h in _CENTRAL_HOSTS):
        return "central"
    if any(h in host for h in _DEPT_HOSTS):
        return "dept"
    return "local"


# ════════════════════════════════════════════════════════════════
#  党媒评论采集 —— 人民日报 / 求是网 / 经济日报 头版评论员文章
# ════════════════════════════════════════════════════════════════
#  用户的核心工作流：按 年/月/周/日 追踪三家党媒的评论员文章，
#  特别关注「化名」文章 —— 党媒重要评论历来以固定笔名发布，
#  署名本身就是政策信号强度的标志：
#    任仲平 = 人民日报重要评论（最重）   钟才文/钟才平 = 财经口径
#    金轩   = 经济形势系列述评           金观平 = 经济日报评论
#    仲音   = 人民日报评论员             秋石   = 求是杂志重要评论
COMMENTARY_FILE = os.path.join(PROJECT_DIR, "data", "commentary_archive.json")
# 种子库：初版页面里手工维护的历史评论，一次性迁移过来打底
COMMENTARY_SEED_FILE = os.path.join(PROJECT_DIR, "data", "commentary_seed.json")

# 化名 → 所属媒体。命中即视为「重点文章」，前端高亮。
# 对照关系（用户长期关注的一组）：
#   任仲平 = 人民日报重要评论（分量最重）   钟才文 / 钟才平 = 中央财经委口径
#   金轩   = 发改委经济宣传系列             金观平 / 钟经文 = 经济日报重要评论
#   仲音   = 人民日报评论员                 秋石 = 求是杂志重要评论
BYLINE_MAP = {
    "钟才文": "人民日报", "钟才平": "人民日报", "任仲平": "人民日报",
    "金轩": "人民日报", "仲音": "人民日报", "任平": "人民日报",
    "国纪平": "人民日报", "金社平": "人民日报", "柯教平": "人民日报",
    "钟声": "人民日报", "仲祖文": "人民日报", "吴哲": "人民日报",
    "秋石": "求是", "石平": "求是",
    "金观平": "经济日报", "钟经文": "经济日报",
}

# 党媒电子版（数字报）配置。人民日报与经济日报用的是同一套数字报系统：
# 版面页列文章链接，详情页带 <author> / <date> 结构化署名 —— 可以精确识别化名。
PAPER_SITES = [
    {
        "media": "人民日报",
        "layout": "http://paper.people.com.cn/rmrb/pc/layout/{ym}/{dd}/node_{node}.html",
        "article": "http://paper.people.com.cn/rmrb/pc/content/{ym}/{dd}/content_{cid}.html",
        # 要闻(01-06) / 评论(05) / 理论(09)：化名文章的主要版面
        "nodes": ["01", "02", "03", "04", "05", "06", "09"],
    },
    {
        "media": "经济日报",
        "layout": "http://paper.ce.cn/pc/layout/{ym}/{dd}/node_{node}.html",
        "article": "http://paper.ce.cn/pc/content/{ym}/{dd}/content_{cid}.html",
        # 要闻(01-03) / 时评(05) / 综合(11)
        "nodes": ["01", "02", "03", "05", "11"],
    },
]

COMMENTARY_LOOKBACK_DAYS = 12     # 常规运行回溯天数
COMMENTARY_BOOTSTRAP_DAYS = 45    # 累积库为空时首次回溯天数（把历史一次性补齐）
COMMENTARY_WORKERS = 10           # 并发线程数

_CID_RE = re.compile(r'content_(\d+)\.html')
_TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
_BY_AUTHOR = re.compile(r'<author>(.*?)</author>')
_BY_DATE = re.compile(r'<date>(.*?)</date>')
_TITLE_NOISE = re.compile(r'[\u200b-\u200f\ufeff\u3000]+')


def _paper_day_cids(site, day):
    """抓某一天的版面页，返回当天的文章 cid 列表（去重）。

    两种链接都要认：要闻版是 <a href="...content_XXX.html">，
    评论版等图片版是 <Area href="...content_XXX.html">。
    """
    ym, dd = day.strftime("%Y%m"), day.strftime("%d")
    cids, seen = [], set()
    for node in site["nodes"]:
        html = safe_fetch(site["layout"].format(ym=ym, dd=dd, node=node), timeout=12)
        if not html:
            continue
        for m in _CID_RE.finditer(html):
            cid = m.group(1)
            if cid not in seen:
                seen.add(cid)
                cids.append(cid)
    return cids


def _paper_probe(args):
    """抓一篇数字报文章的详情页，解析标题/署名/日期/正文。"""
    site, ym, dd, cid = args
    url = site["article"].format(ym=ym, dd=dd, cid=cid)
    html = safe_fetch(url, timeout=12)
    if not html:
        return None
    m_t = _TITLE_RE.search(html)
    title = re.sub(r'<[^>]+>', '', m_t.group(1)) if m_t else ""
    title = _TITLE_NOISE.sub('', title)
    title = re.sub(r'\s+', ' ', title).strip()
    m_au = _BY_AUTHOR.search(html)
    author = re.sub(r'\s+', ' ', m_au.group(1)).strip() if m_au else ""
    m_dt = _BY_DATE.search(html)
    pub = (m_dt.group(1).strip()[:10] if m_dt else "")
    if not re.match(r'\d{4}-\d{2}-\d{2}', pub):
        pub = f"{ym[:4]}-{ym[4:6]}-{dd}"
    return {"url": url, "title": title, "author": author, "date": pub,
            "media": site["media"], "body": extract_article_body(html)}


def fetch_paper_comments(days, known=None):
    """回溯 N 天抓两家党媒数字报，返回署名命中化名表的条目。

    known 为已入库 URL 集合，用于跳过抓过的文章，避免每天重复请求。
    """
    known = known or set()
    jobs = []
    for site in PAPER_SITES:
        for i in range(days):
            day = date.today() - timedelta(days=i)
            ym, dd = day.strftime("%Y%m"), day.strftime("%d")
            for cid in _paper_day_cids(site, day):
                url = site["article"].format(ym=ym, dd=dd, cid=cid)
                if url in known:
                    continue
                jobs.append((site, ym, dd, cid))
    if not jobs:
        return []
    print(f"  党媒数字报: 待查 {len(jobs)} 篇（回溯 {days} 天），并发核验署名...")
    out, seen_titles = [], set()
    try:
        with ThreadPoolExecutor(max_workers=COMMENTARY_WORKERS) as pool:
            for art in pool.map(_paper_probe, jobs):
                if not art or not art["title"]:
                    continue
                hit = next((b for b in BYLINE_MAP if b in art["author"]), "")
                if not hit:
                    continue
                # 同一篇文章常在要闻版与评论版各登一次（版面 ID 不同），按标题去重
                key = re.sub(r'\s+', '', art["title"])
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                art["byline"] = hit
                out.append(art)
    except Exception as e:
        print(f"  数字报并发抓取异常: {e}")
    return out


def fetch_qstheory_comments():
    """求是网「社论评论」栏目（定期更新，非每日）。"""
    url = "https://www.qstheory.cn/v9zhuanqu/zhuanqu/slpl/index.htm"
    html = safe_fetch(url, timeout=15)
    if not html:
        return []
    out, seen = [], set()
    link_re = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
    for m in link_re.finditer(html):
        href = m.group(1).strip()
        title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(2))).strip()
        if "qstheory" not in href or len(title) < 8:
            continue
        dm = re.search(r'/(20\d{2})(\d{2})(\d{2})/', href)
        pub = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""
        if href in seen:
            continue
        seen.add(href)
        out.append({"url": href, "title": title, "author": "求是网评论员",
                    "byline": "求是网评论员", "date": pub, "body": ""})
    return out[:20]


def fetch_ce_comments():
    """经济日报：观点频道列表 + 电子版，筛「金观平 / 评论员」署名。"""
    pages = ["http://views.ce.cn/", "http://www.ce.cn/xwzx/gnsz/gdxw/",
             "http://views.ce.cn/view/ent/index.shtml"]
    out, seen = [], set()
    link_re = re.compile(r'<a[^>]+href=["\']([^"\']+\.shtml)["\'][^>]*>(.*?)</a>', re.S)
    for page in pages:
        html = safe_fetch(page, timeout=15)
        if not html:
            continue
        for m in link_re.finditer(html):
            href, title = m.group(1).strip(), \
                re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(2))).strip()
            if len(title) < 8 or href in seen:
                continue
            byline = ""
            for b in BYLINE_MAP:
                if b in title:
                    byline = b
                    break
            if not byline and "评论员" in title:
                byline = "评论员"
            if not byline:
                continue
            seen.add(href)
            if href.startswith("./"):
                href = "http://www.ce.cn/xwzx/gnsz/gdxw/" + href[2:]
            out.append({"url": href, "title": title, "author": byline,
                        "byline": byline, "date": date_from_url(href), "body": ""})
    return out[:20]


def enrich_commentary(items):
    """给评论条目补齐摘要 / 关键词 / 关键语句（与政策条目同一套口径）。"""
    need = [x for x in items if not x.get("body")]
    if need:
        try:
            with ThreadPoolExecutor(max_workers=COMMENTARY_WORKERS) as pool:
                for it, body in pool.map(_fetch_body_only, need):
                    if body:
                        it["body"] = body
        except Exception:
            pass
    for x in items:
        body = x.get("body", "")
        if not x.get("summary"):
            x["summary"] = clean_summary(body or x["title"], SUMMARY_LIMIT,
                                         x.get("title", ""))
        x["keywords"] = extract_keywords(x.get("title", ""), x.get("summary", ""),
                                         body[:800])
        x["keySentence"] = (
            pick_key_sentence(body, x["keywords"], title=x.get("title", ""),
                              summary=x.get("summary", "")) if body else "")
        x["tier"] = "central" if x.get("byline") in ("任仲平", "钟才文", "钟才平",
                                                     "秋石") else ""
        x.pop("body", None)
    return items


def _fetch_body_only(item):
    """线程池单元：只取正文。"""
    html = safe_fetch(item["url"], timeout=12)
    return item, (extract_article_body(html) if html else "")


def fetch_commentary(existing=None, bootstrap=False):
    """汇总党媒来源，并与历史累积库合并去重。"""
    existing = existing if isinstance(existing, list) else []
    known = {x.get("url") for x in existing if x.get("url")}

    days = COMMENTARY_LOOKBACK_DAYS
    if bootstrap:
        days = COMMENTARY_BOOTSTRAP_DAYS
        print(f"  首次运行，回溯 {days} 天初始化评论库")

    fresh = []
    for name, fn in (("党媒数字报", lambda: fetch_paper_comments(days, known)),
                     ("求是网", fetch_qstheory_comments),
                     ("经济日报网", fetch_ce_comments)):
        try:
            got = fn()
            got = [g for g in got if g.get("url") and g["url"] not in known]
            print(f"  {name}: 新增 {len(got)} 条")
            fresh.extend(got)
        except Exception as e:
            print(f"  {name} 抓取失败（不影响主流程）: {e}")

    if not fresh:
        return existing

    enrich_commentary(fresh)

    merged = existing + fresh
    seen, out = set(), []
    for x in merged:
        u = x.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(x)
    out.sort(key=lambda x: (x.get("date") or "0000-00-00"), reverse=True)
    return out


# ── 主函数 ──────────────────────────────────────────────────────

ALL_SOURCES = [SRC_GOV, SRC_NDRC, SRC_PBC, SRC_CSRC, SRC_MIIT, SRC_STATS]

HTML_FETCHERS = {
    SRC_GOV: fetch_gov_cn_html,
    SRC_NDRC: fetch_ndrc_html,
    SRC_PBC: fetch_pbc_html,
    SRC_CSRC: fetch_csrc_html,
    SRC_MIIT: fetch_miit_html,
    SRC_STATS: fetch_stats_html,
}


def main():
    today_str = date.today().strftime("%Y-%m-%d")
    result = {
        "lastUpdated": today_str,
        "monthLabel": MONTH_LABEL,
        "timeline": [],
        "commentary": [],
        "blocks": {},
    }

    collected = []

    # 1. 优先使用 API
    print("Fetching via gov.cn API...")
    api_items = []
    try:
        api_items = fetch_gov_api()
        print(f"  API returned {len(api_items)} items")
    except Exception as e:
        print(f"  API error: {e}")
    collected.extend(api_items)

    # 2. 对 API 未覆盖的来源，用 HTML 爬虫 fallback
    api_sources = set(item["desc"] for item in api_items)
    missing = [s for s in ALL_SOURCES if s not in api_sources]
    if missing:
        print(f"  API missing sources: {missing}")
        for src in missing:
            fetcher = HTML_FETCHERS.get(src)
            if not fetcher:
                continue
            print(f"  Fetching {src} via HTML...")
            try:
                items = fetcher()
                print(f"    Found {len(items)} items")
                collected.extend(items)
            except Exception as e:
                print(f"    Error: {e}")

    # 2b. 交易所规则入口（列表页为 JS 渲染，仅作为固定官网入口）
    #     这类不是"政策动态"，只进 blocks 供板块展示，不污染时间线
    exchange_items = []
    try:
        exchange_items = fetch_exchange_html()
        print(f"  Exchange entries: {len(exchange_items)}")
    except Exception as e:
        print(f"  Exchange error: {e}")

    # 3. 统一去重（按 title 和 url 双重去重）
    seen_titles = set()
    seen_urls = set()
    unique = []
    for item in collected:
        title = item["title"]
        url = item["url"]
        if not title or not url:
            continue
        key_t = re.sub(r'\s+', '', title)
        if key_t in seen_titles or url in seen_urls:
            continue
        seen_titles.add(key_t)
        seen_urls.add(url)
        unique.append({
            "title": title,
            "desc": item["desc"],
            "url": url,
            "date": item.get("date", ""),
            "summary": item.get("summary", ""),
            "tier": classify_tier(item["desc"], url),
        })

    # 4. 按日期降序排序 —— 保证页面第一屏就是最新政策
    #    无日期的条目统一排在末尾（官网入口类噪声不该抢占首屏）
    unique.sort(key=lambda x: (x["date"] or "0000-00-00"), reverse=True)

    # 5. 抓原文详情页生成摘要 —— API 返回的 summary 是搜索片段，质量不稳定
    #    （常出现"联规函〔2026〕305号各省、自治区……"这种文号+主送机关的残句），
    #    所以统一以正文摘要为准，抓不到才退回 API 片段。
    need = [x for x in unique if len(x.get("summary", "")) < 400][:DIGEST_LIMIT]
    if need:
        print(f"\n抓取原文生成摘要: {len(need)} 条（并发 {DIGEST_WORKERS} 线程）")
        done = got = 0
        try:
            with ThreadPoolExecutor(max_workers=DIGEST_WORKERS) as pool:
                for item, summ, body in pool.map(worker_digest, need):
                    done += 1
                    if summ and len(summ) >= SUMMARY_MIN_LEN:
                        item["summary"] = summ      # 正文摘要优先
                        got += 1
                    if body:
                        item["_body"] = body
            print(f"  完成 {done} 条，{got} 条拿到正文摘要")
        except Exception as e:
            print(f"  并发抓取异常（不影响主流程）: {e}")

    # 6. 统一生成关键词与关键语句（全部自动，无手工维护）
    #    API 片段式的摘要常有省略号，清掉避免显示成"……xxx..."这种半截话
    for x in unique:
        body = x.pop("_body", "")
        summ = re.sub(r'\.{3,}|…+', '', x.get("summary", ""))
        x["summary"] = clean_summary(summ, SUMMARY_LIMIT, x["title"])
        x["keywords"] = extract_keywords(x["title"], x["summary"], body[:600])
        # 关键语句只在拿到正文时生成，且必须来自摘要之后（否则只是复述摘要）
        x["keySentence"] = (
            pick_key_sentence(body, x["keywords"], title=x["title"], summary=x["summary"])
            if body else ""
        )

    result["timeline"] = [
        x for x in unique if x["desc"] != SRC_EXCHANGE
    ]

    # 7. blocks：按来源分组，供前端「证监会动态」等板块自动渲染
    for src in ALL_SOURCES:
        group = [x for x in unique if x["desc"] == src]
        if group:
            result["blocks"][src] = group[:BLOCK_SIZE]
    if exchange_items:
        result["blocks"][SRC_EXCHANGE] = exchange_items

    # 7b. 党媒评论 —— 人民日报 / 求是网 / 经济日报 头版评论员文章
    #     与历史累积库合并（评论按年/月/周/日检索，需要长期积累）
    print("\nFetching commentary (人民日报 / 求是网 / 经济日报)...")
    existing_commentary = []
    first_run = not os.path.exists(COMMENTARY_FILE)
    if not first_run:
        try:
            with open(COMMENTARY_FILE, encoding="utf-8") as f:
                prev = json.load(f)
            existing_commentary = prev.get("items", []) if isinstance(prev, dict) else prev
        except Exception as e:
            print(f"  读取历史评论库失败（按空库处理）: {e}")
            first_run = True
    # 首次运行：用初版页面手工维护的历史数据打底，
    # 保证「年 / 月」视图一上来就有内容，之后每天增量累积
    if first_run and os.path.exists(COMMENTARY_SEED_FILE):
        try:
            with open(COMMENTARY_SEED_FILE, encoding="utf-8") as f:
                seed = json.load(f)
            seed_items = seed.get("items", []) if isinstance(seed, dict) else seed
            existing_commentary = seed_items + existing_commentary
            print(f"  载入历史种子 {len(seed_items)} 条")
        except Exception as e:
            print(f"  读取种子库失败: {e}")
    try:
        commentary = fetch_commentary(existing_commentary, bootstrap=first_run)
        result["commentary"] = commentary
        os.makedirs(os.path.dirname(COMMENTARY_FILE), exist_ok=True)
        with open(COMMENTARY_FILE, "w", encoding="utf-8") as f:
            json.dump({"updated": today_str, "items": commentary}, f,
                      ensure_ascii=False, indent=2)
        bylines = sum(1 for c in commentary if c.get("byline") in BYLINE_MAP)
        print(f"  评论库合计 {len(commentary)} 条（其中化名文章 {bylines} 条）")
    except Exception as e:
        print(f"  评论抓取整体失败（不影响政策数据）: {e}")
        result["commentary"] = existing_commentary

    # 8. 输出各来源最新日期，便于在 Actions 日志里核对时效
    print(f"\nTotal after dedup: {len(unique)} items")
    for src in ALL_SOURCES:
        group = [x for x in unique if x["desc"] == src]
        if group:
            withsum = sum(1 for x in group if x.get("summary"))
            withks = sum(1 for x in group if x.get("keySentence"))
            withkw = sum(1 for x in group if x.get("keywords"))
            print(f"  {src}: {len(group)} 条, 最新 {group[0]['date'] or '未知'}, "
                  f"摘要 {withsum} / 关键词 {withkw} / 关键句 {withks}")
        else:
            print(f"  {src}: 0 条 (本次未抓到)")
    print(f"  {SRC_EXCHANGE}: {len(exchange_items)} 条入口（仅 blocks）")
    if result["timeline"]:
        top = result["timeline"][0]
        print(f"  >>> 全站最新一条: {top['date']} {top['title'][:30]}")

    # 9. 写入 JSON（抓取完全失败时保留旧数据，避免把页面清空）
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if not result["timeline"] and os.path.exists(OUTPUT_FILE):
        print("\n!! 本次未抓到任何数据，保留原有 latest.json 不覆盖")
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {OUTPUT_FILE}")
    print(f"  Date: {today_str}")
    print(f"  Timeline entries: {len(result['timeline'])}")

    # 10. L0 宏观指标（独立数据源，失败不影响政策数据）
    try:
        import update_macro
        update_macro.update_macro()
    except Exception as e:
        print(f"  宏观指标更新失败（不影响政策数据）: {e}")

    # 11. L5 证监会动态（负面清单/正面试点/审核进度/官媒定调，失败不影响政策数据）
    try:
        import update_csrc
        update_csrc.build()
    except Exception as e:
        print(f"  证监会动态更新失败（不影响政策数据）: {e}")


if __name__ == "__main__":
    main()
