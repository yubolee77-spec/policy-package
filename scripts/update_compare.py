# -*- coding: utf-8 -*-
"""
历年政策对比数据抓取（L3 层，自动更新）
========================================

用户方法论：
  找过去两年「同一部门 + 同一主题」的文件，对比表述差异，重点看三类关键词变化：
    - 定调词（力度递增）：持续用力 → 着力 → 大力 → 坚决
    - 动词（性质判断）：推动/鼓励 = 扶持；严控/压减 = 限制
    - 程度词（推进节奏）：有序/稳步 → 持续 → 进一步 → 加速

实现：
  1. 数据源：国务院政策文件库 API（sousuo.www.gov.cn，t=zhengcelibrary）
     —— 覆盖国务院公文 + 各部委文件，url 均为 gov.cn 体系原文页
  2. 按 35+ 产业主题**逐词全库标题检索**（searchfield=title，翻页取尽），
     再按 `match` 词二次过滤 + 年份分组 —— 计数即「全库标题命中该主题的文件数」
  3. 按 主题 × 部门 × 年份 分组，选代表文件（部门权威度 + 是否带文号）
  4. 每条提取 定调词/动词/程度词（复用 update_data.KEYWORD_RULES），
     代表文件额外抓原文取关键语句
  5. 自动生成「差异说明」：力度变化 / 性质方向 / 节奏变化 / 发文密度变化
  6. 输出 data/compare.json，前端 L3 优先读取，硬编码数据降级为兜底

运行：由 scripts/update_data.py 末尾自动调用（try/except 隔离，失败不影响主数据）

── 踩坑记录（2026-09-19 改口径，勿回退）─────────────────────────
A. `searchfield=title` 不能省。不带它时服务端**忽略 q**，返回的是「综合排序的政策池」
   （约 300 条/页、可翻很多页），表现为：32 个主题各查 4 页拿到的是**同一批数据**，
   再靠标题正则在里面挑 —— 于是各年计数只反映「该主题文件在池子里残留多少」，
   而不是真实发文量。池子的年份分布极不均衡（实测 2026:1124 / 2025:654 / 2024:119），
   导致 2024 年数字系统性偏低，三年对比失真。
B. 加了 searchfield=title 之后，检索范围变成**全库标题命中**，翻页到空为止即可取尽
   （`searchVO.totalCount` 恒为 0，不能用它判总量，只能靠「本页 0 条新增」收手）。
C. 时间范围参数（publishStart/pubtimeStart/startTime/beginDate/timeStart…）实测**全部无效**，
   加与不加返回完全一致 —— 所以「逐年检索」只能在本地按 pubtimeStr 分组，别去试参数。
D. 单主题要靠多个检索词才够：如「房地产」标题命中仅 59 条且 2026 年为零，
   而「住房」有 405 条（2026:28 条）。故检索词取 kws + match 的并集。
E. 接口每页上限 300 条（n 参数只在 <300 时起作用）。
F. **接口有反爬，会临时封 IP**：8 并发 × 143 词（约 180 次请求、~10 req/s）后，所有请求（含不带
   关键词的）连续返 **403 Forbidden，实测锁了约 7 分钟**。⇒ 打这个接口一律低并发（本文件 2）+ 页间延时
   + 失败退避重试；任一检索词重试耗尽即 `SearchError` 中止本轮、**不覆盖** compare.json。
G. **`searchVO=null` 要分两种**：`msg='抱歉，没有找到相关结果'`（code 1001）= 真零命中（如「半导体」
   在政策库标题里就是没有，别当故障）；其余（含限流期的空响应）= 失败，必须重试。
   把零命中当失败会让这些词白等退避、最后把整轮拖中止；把限流当零命中则会静默少算 —— 两头都要防。
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

# 复用主脚本的关键词体系与正文抓取
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_data import (  # noqa: E402
    extract_keywords, fetch_article_digest, pick_key_sentence, safe_fetch_json,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "compare.json")

API_BASE = "https://sousuo.www.gov.cn/search-gov/data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sousuo.www.gov.cn/",
}

# ── 年份窗口：当前年 + 前两年 ──────────────────────────────────
TODAY = date.today()
YEARS = [TODAY.year - 2, TODAY.year - 1, TODAY.year]      # e.g. [2024, 2025, 2026]
AS_OF = "%d年%d月" % (TODAY.year, TODAY.month)

# ── 产业主题库（track 与前端 compareCategories 对齐 + 扩展） ────
# kws: 检索词（第一个为主检索词）；match: 标题/摘要二次过滤的关联词
# code: 国民经济行业分类代码（仅展示用）
TOPICS = [
    # ── 战略性新兴产业 emerging ──
    dict(key="ic",       label="集成电路/半导体",  track="emerging", code="C39",
         kws=["集成电路"],       match=["集成电路", "半导体", "芯片", "晶圆", "EDA"]),
    dict(key="ai",       label="人工智能",         track="emerging", code="I65",
         kws=["人工智能"],       match=["人工智能", "AI", "大模型", "智能体", "生成式"]),
    dict(key="biomed",   label="生物医药",         track="emerging", code="C27",
         kws=["生物医药"],       match=["生物医药", "创新药", "药品", "医疗器械", "中医药"]),
    dict(key="lowalt",   label="低空经济",         track="emerging", code="G56",
         kws=["低空经济"],       match=["低空经济", "无人机", "通用航空", "eVTOL"]),
    dict(key="storage",  label="新型储能",         track="emerging", code="D44",
         kws=["新型储能"],       match=["储能", "抽水蓄能", "电化学储能"]),
    dict(key="robot",    label="机器人/智能制造",  track="emerging", code="C34",
         kws=["机器人"],         match=["机器人", "智能制造", "人形机器人", "工业互联网", "智能工厂"]),
    dict(key="aerospace",label="商业航天/卫星",    track="emerging", code="C37",
         kws=["商业航天"],       match=["商业航天", "卫星", "航天", "空天信息"]),
    dict(key="material", label="新材料",           track="emerging", code="C26",
         kws=["新材料"],         match=["新材料", "原材料", "首批次", "石墨烯", "碳纤维"]),
    dict(key="nev",      label="新能源汽车",       track="emerging", code="C36",
         kws=["新能源汽车"],     match=["新能源汽车", "动力电池", "充电", "智能网联汽车", "以旧换新"]),
    dict(key="hydrogen", label="氢能",             track="emerging", code="D44",
         kws=["氢能"],           match=["氢能", "氢燃料", "制氢", "加氢"]),
    dict(key="quantum",  label="量子科技",         track="emerging", code="I65",
         kws=["量子"],           match=["量子", "量子计算", "量子通信", "量子测量"]),
    dict(key="future6g", label="6G/未来通信",      track="emerging", code="I63",
         kws=["6G"],             match=["6G", "第六代移动", "未来网络", "未来通信", "卫星互联网"]),
    # ── 传统支柱产业 traditional ──
    dict(key="steel",    label="钢铁",             track="traditional", code="C31",
         kws=["钢铁"],           match=["钢铁", "产能置换", "粗钢"]),
    dict(key="chem",     label="石化化工",         track="traditional", code="C25",
         kws=["石化"],           match=["石化", "化工", "老旧装置", "乙烯"]),
    dict(key="nonfer",   label="有色金属",         track="traditional", code="C32",
         kws=["有色金属"],       match=["有色金属", "铜", "铝", "锂", "稀土"]),
    dict(key="cement",   label="建材/水泥",        track="traditional", code="C30",
         kws=["建材"],           match=["建材", "水泥", "平板玻璃", "陶瓷"]),
    dict(key="coal",     label="煤炭/煤电",        track="traditional", code="B06",
         kws=["煤炭"],           match=["煤炭", "煤电", "煤矿", "智能化改造"]),
    dict(key="realest",  label="房地产",           track="traditional", code="K70",
         kws=["房地产"],         match=["房地产", "住房", "城中村", "保障性住房", "止跌回稳"]),
    dict(key="construct",label="建筑业/基建",      track="traditional", code="E48",
         kws=["建筑业"],         match=["建筑业", "基建", "基础设施", "重大工程", "老旧小区"]),
    # ── 数字经济与要素 digital ──
    dict(key="digital",  label="数字经济",         track="digital", code="I",
         kws=["数字经济"],       match=["数字经济", "数字中国", "数字化转型"]),
    dict(key="data",     label="数据要素/数据局",  track="digital", code="I65",
         kws=["数据要素"],       match=["数据要素", "数据资产", "公共数据", "数据流通", "数据局"]),
    dict(key="compute",  label="算力/数据中心",    track="digital", code="I65",
         kws=["算力"],           match=["算力", "数据中心", "东数西算", "智算"]),
    dict(key="platform", label="平台经济",         track="digital", code="I64",
         kws=["平台经济"],       match=["平台经济", "平台企业", "常态化监管"]),
    # ── 绿色低碳与能源 green ──
    dict(key="carbon",   label="节能降碳/双碳",    track="green", code="N77",
         kws=["节能降碳"],       match=["节能降碳", "碳达峰", "碳中和", "双碳", "碳排放"]),
    dict(key="power",    label="新型电力系统",     track="green", code="D44",
         kws=["新型电力系统"],   match=["新型电力系统", "电力市场", "电网", "绿电", "新能源消纳"]),
    dict(key="greennew", label="绿色转型/环保",    track="green", code="N77",
         kws=["绿色转型"],       match=["绿色转型", "绿色低碳", "环保", "污染治理", "循环经济"]),
    # ── 现代服务业与民生 service ──
    dict(key="reits",    label="REITs/基础设施基金", track="service", code="J67",
         kws=["REITs"],          match=["REITs", "不动产投资信托", "基础设施基金"]),
    dict(key="eldercare",label="养老/银发经济",    track="service", code="Q85",
         kws=["养老服务"],       match=["养老", "银发经济", "老年", "适老化"]),
    dict(key="health",   label="医疗卫生",         track="service", code="Q84",
         kws=["医疗卫生"],       match=["医疗", "卫生", "医院", "医保", "药品安全"]),
    dict(key="edu",      label="教育",             track="service", code="P83",
         kws=["教育"],           match=["教育", "学校", "职业教育", "产教融合"]),
    dict(key="culture",  label="文旅/消费",        track="service", code="R88",
         kws=["文旅"],           match=["文旅", "旅游", "文化", "消费", "冰雪"]),
    dict(key="trade",    label="外贸/跨境",        track="service", code="G58",
         kws=["外贸"],           match=["外贸", "进出口", "跨境", "关税", "自贸"]),
    # ── 农业农村与经营主体 agri/enterprise ──
    dict(key="agri",     label="乡村振兴/农业",    track="agri", code="A01",
         kws=["乡村振兴"],       match=["乡村振兴", "农业", "农村", "种业", "粮食"]),
    dict(key="private",  label="民营经济",         track="enterprise", code="—",
         kws=["民营经济"],       match=["民营经济", "民营企业", "民营企业家的"]),
    dict(key="sme",      label="中小企业/专精特新", track="enterprise", code="—",
         kws=["中小企业"],       match=["中小企业", "专精特新", "小微企业", "减负"]),
]

# ── 部门权威度（选代表文件时优先国务院 / 综合部门） ──────────────
DEPT_RANK = [
    ("国务院", 100), ("中共中央", 98), ("国务院办公厅", 95),
    ("国家发展改革委", 80), ("工业和信息化部", 78), ("财政部", 76),
    ("中国人民银行", 74), ("国家能源局", 72), ("住房城乡建设部", 70),
    ("商务部", 68), ("中国证券监督管理委员会", 66), ("国家数据局", 64),
    ("交通运输部", 62), ("农业农村部", 60), ("科学技术部", 58),
    ("人力资源和社会保障部", 56), ("文化和旅游部", 54), ("生态环境部", 52),
    ("国家卫生健康委", 50), ("教育部", 48), ("国务院国资委", 46),
]

# ── 力度词分级（用于「力度递增/回落」的自动判断） ────────────────
DING_STRENGTH = {
    "毫不动摇": 5, "坚定不移": 5, "坚决": 5,
    "大力": 4, "全力": 4, "加力": 4,
    "着力": 3, "加大": 3, "加强": 3, "加快": 3, "强化": 3, "有力": 3, "抓紧": 3,
    "严格": 2,
}

# 每年每主题最多取几个代表文件、每部门几条
MAX_DOCS_PER_YEAR = 3
MAX_DEPTS_PER_TOPIC = 3

# ── 全库标题检索参数 ────────────────────────────────────────────
# 翻页上限只取 5：实测「教育」全库 1309 条命中里，2024–2026 窗口内的条目**全在第 1–2 页**
# （p1 含 2024:78/2025:89/2026:37，p2 含 2024:35，p3 及以后 0 条在窗口内，全是 2024 年之前），
# 深翻对本层的三年对比没有增量。每页上限 300 条。
MAX_PAGES_PER_KEY = 5
# 并发必须压到很低：gov.cn 检索接口有反爬，实测 8 并发 × 143 词（~10 req/s）后**整段 IP 被封**：
# 所有请求（连不带关键词的普通请求）连续 403 Forbidden，**锁约 7 分钟**才恢复。
# 压到 2 并发 + 页间延时后，同样的量能安全跑完（旧版 L3 用 ~4 req/s 也没被封过）。
SEARCH_WORKERS = 2
PAGE_DELAY = 0.5               # 同词翻页之间的间隔
RETRY_BACKOFF = (2, 5, 12)     # 单页失败后的退避秒数，用完仍失败即中止本轮


class SearchError(Exception):
    """检索失败（多为被 gov.cn 限流）。触发时**不覆盖** compare.json，保留上一版。"""


def _bj_now(fmt="%Y-%m-%d %H:%M"):
    """北京时间字符串（Actions 环境为 UTC，需 +8）"""
    from datetime import datetime as _d, timezone as _tz, timedelta as _td
    return (_d.now(_tz.utc) + _td(hours=8)).strftime(fmt)


def _rank_dept(puborg):
    """按部门权威度打分；多部门联合发文取最高分。无署名的（gov.cn 新闻/解读）最低。"""
    org = puborg or ""
    best = 5 if not org.strip() else 10
    for name, sc in DEPT_RANK:
        if name in org:
            best = max(best, sc)
    return best


# 标题相关性加分/减分：真政策文件优先，解读/答问类二手内容降权
_TITLE_POLICY_HINTS = ("关于印发", "条例", "办法", "意见", "方案", "行动计划",
                       "通知", "规定", "决定", "公告", "指引", "实施细则", "规划")
_TITLE_NOISE_HINTS = ("解读", "答记者问", "问答", "新闻发布会", "一图", "速览",
                      "报道", "图文", "实录", "摘编", "新闻发布会")


def _title_relevance(title):
    sc = 0
    if any(k in title for k in _TITLE_POLICY_HINTS):
        sc += 2
    if any(k in title for k in _TITLE_NOISE_HINTS):
        sc -= 3
    return sc


def _short_dept(puborg):
    """把 '工业和信息化部办公厅' 这类长名压短成 '工信部'。无署名标为 gov.cn 发布。"""
    org = (puborg or "").strip()
    if not org:
        return "gov.cn发布"
    if "国务院办公厅" in org:
        return "国务院办公厅"
    if org.startswith("国务院"):
        return "国务院"
    for long, short in [
        ("国家发展和改革委员会", "发改委"), ("国家发展改革委", "发改委"),
        ("工业和信息化部", "工信部"), ("财政部", "财政部"),
        ("中国人民银行", "央行"), ("中国证券监督管理委员会", "证监会"),
        ("住房和城乡建设部", "住建部"), ("国家能源局", "能源局"),
        ("商务部", "商务部"), ("交通运输部", "交通运输部"),
        ("农业农村部", "农业农村部"), ("科学技术部", "科技部"),
        ("人力资源和社会保障部", "人社部"), ("文化和旅游部", "文旅部"),
        ("生态环境部", "生态环境部"), ("国家卫生健康委", "卫健委"),
        ("国家市场监督管理总局", "市场监管总局"), ("国务院国资委", "国资委"),
        ("国家数据局", "数据局"), ("教育部", "教育部"),
    ]:
        if long in org:
            return short
    # 截断超长联合发文
    return org if len(org) <= 14 else org[:13] + "…"


def search_keys(topic):
    """一个主题要用哪些词去全库标题检索：`kws` + `match` 全量，保序去重。

    两条约束（改这张表前先看）：
      ① **必须带上 match 里的词**，而不只是 kws[0]：「房地产」标题命中仅 59 条、2026 年为零，
         只靠它会把一个活跃主题算成「今年没发文」；补上「住房」才有 405 条。
      ② **不要挑肥拣瘦地排除「太宽的词」**。曾试过把 消费/文化/医疗/药品/学校/铜铝锂/AI 踢出检索词，
         结果主题标签与计数口径当场不一致 —— 「文旅/消费」只剩文旅，「医疗卫生」少了医药，
         数字对不上标题。既然 match 已声明该主题涵盖这些词，检索就必须一视同仁。
    """
    keys = []
    for w in list(topic["kws"]) + list(topic["match"]):
        if w not in keys:
            keys.append(w)
    return keys


def _title_page(kw, p):
    """取一页标题检索结果。返回 (status, payload)：

      ("ok",     [item, ...])  正常
      ("empty",  [])           服务端明确说「没有找到相关结果」—— 该词真无命中
      ("retry",  "原因")       被限流/请求失败，应当重试
    """
    url = (f"{API_BASE}?t=zhengcelibrary&q={urllib.parse.quote(kw)}"
           f"&searchfield=title&sort=pubtime&sortType=1&p={p}&n=100")
    data = safe_fetch_json(url, timeout=20)
    if data is None:
        return "retry", "请求失败（403 / 超时）"
    sv = data.get("searchVO")
    if sv is None:
        # 200 但 searchVO 为空有两种来源，必须分开（实测）：
        #   ① msg='抱歉，没有找到相关结果' code=1001 → **真的零命中**（如「半导体」在政策库标题里就没有），
        #      当失败处理会让这些词反复重试、最后把整轮 L3 拖到中止；
        #   ② 其它（含被限流时的空响应）→ 一律重试，避免把「被限流」写成「该主题没文件」而静默少算。
        if "没有找到" in (data.get("msg") or "") or data.get("code") == 1001:
            return "empty", []
        return "retry", f"searchVO 为空（msg={data.get('msg')!r}）"
    cat_map = sv.get("catMap") or {}
    items = []
    # 只取这三类，**不取 gongbao**：catMap 里还有「国务院公报」一类，但公报是对国发/国办发
    # 文件的**再发布**（同文不同 URL），合并进来会把同一份政策算两遍、把年度计数灌水。
    # L2/L6 也是这三类，保持一致。
    for cat in ("gongwen", "bumenfile", "otherfile"):
        items.extend((cat_map.get(cat) or {}).get("listVO") or [])
    return "ok", items


def fetch_key_hits(kw, pages=MAX_PAGES_PER_KEY):
    """单个关键词做**标题**检索，翻页到「本页无新增」为止。

    searchfield=title 是关键：省掉它服务端会忽略 q（详见文件头踩坑记录 A）。
    searchVO.totalCount 恒为 0，无法用它算总量，只能靠空页收手。
    任一分页重试耗尽即抛 SearchError —— 宁可本轮不更新，也不要写进被少算的数字。

    返回 {"items", "pages", "capped"}。`capped` 表示翻到上限时末页仍有新增，
    只用于日志告警（实测窗口内条目集中在第 1–2 页，深翻拿到的都是 2024 年之前的，
    对本层的三年窗口没有增量，所以上限才敢设这么低）。
    """
    items, seen, capped, used = [], set(), False, 0
    for p in range(1, pages + 1):
        payload, reason, empty = None, "", False
        for attempt in range(len(RETRY_BACKOFF) + 1):
            status, data = _title_page(kw, p)
            if status == "ok":
                payload = data
                break
            if status == "empty":
                empty = True
                break
            reason = data
            if attempt == len(RETRY_BACKOFF):
                raise SearchError(f"「{kw}」第 {p} 页：{reason}")
            time.sleep(RETRY_BACKOFF[attempt])
        if empty:
            break                      # 服务端明确无结果，不必再翻页
        used = p
        got = 0
        for it in payload:
            key = it.get("url") or it.get("id")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(it)
            got += 1
        if got == 0:
            break                      # 没有更多页，提前收手
        if p == pages:
            capped = True
        time.sleep(PAGE_DELAY)
    return {"items": items, "pages": used, "capped": capped}


def build_hit_index(keys):
    """把所有主题的检索词去重后抓一次，供各主题共用。

    主题之间检索词大量重叠（人工智能/半导体/储能…），逐主题各抓一遍会成倍放大请求数。
    低并发 + 全量失败中止：任一检索词抓不到就整体放弃，防止把残缺数据写进 compare.json。
    """
    index, errors, done, capped = {}, [], 0, []
    requests = 0
    with ThreadPoolExecutor(max_workers=SEARCH_WORKERS) as pool:
        futs = {pool.submit(fetch_key_hits, k): k for k in keys}
        for fut in as_completed(futs):
            kw = futs[fut]
            try:
                r = fut.result()
                index[kw] = r["items"]
                requests += r["pages"]
                if r["capped"]:
                    capped.append("%s(%d条)" % (kw, len(r["items"])))
            except Exception as e:                          # noqa: BLE001
                index[kw] = []
                errors.append(str(e)[:140])
            done += 1
            if done % 20 == 0:
                print(f"    ... 检索词 {done}/{len(keys)}（累计失败 {len(errors)}）")
    print(f"  共 {requests} 次分页请求（{len(keys)} 词）")
    # 命中量 top5：便于日后判断「还要不要调翻页上限」
    top = sorted(index.items(), key=lambda kv: -len(kv[1]))[:5]
    print("  命中 top5：" + " / ".join("%s %d" % (k, len(v)) for k, v in top))
    zero = [k for k, v in index.items() if not v]
    if zero:
        print(f"  零命中检索词 {len(zero)} 个（服务端明确无结果，如 " + "、".join(zero[:5]) + "）")
    if capped:
        print(f"  ! 触及 {MAX_PAGES_PER_KEY} 页上限的检索词（末页仍有新增）：" + "、".join(capped))
    if errors:
        raise SearchError(
            f"{len(errors)}/{len(keys)} 个检索词抓取失败（疑似被 gov.cn 限流）：\n      "
            + "\n      ".join(errors[:6]))
    return index


def fetch_topic_items(topic, index):
    """把该主题所有检索词的全库命中并起来（按 url 去重）。"""
    items, seen = [], set()
    for kw in search_keys(topic):
        for it in index.get(kw, []):
            key = it.get("url") or it.get("id")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(it)
    return items


def filter_year_and_topic(items, topic, years):
    """年份窗口 + 标题关键词过滤。

    检索侧已是「标题命中」，这里再按 `match` 词过一遍，是为了兜住两种情况：
      ① 检索词比 match 更宽（如以「储能」捞回的文件 title 只出现「抽水蓄能」——
         这其实也在 match 里，但换个词表就不一定）；
      ② 接口可能把标题匹配降级到摘要（观察到过），不能假设它严格只看标题。
    只有标题命中主题词的文件才是真正的「该主题政策」，保证对比对象准确可查证。
    """
    out = []
    kwset = topic["match"]
    for it in items:
        t = (it.get("pubtimeStr") or "")
        m = re.match(r"(\d{4})\.", t)
        if not m:
            continue
        year = int(m.group(1))
        if year not in years:
            continue
        title = re.sub(r"<[^>]+>", "", it.get("title") or "")
        if not any(k in title for k in kwset):
            continue
        out.append({
            "year": year,
            "date": t.replace(".", "-"),
            "title": title,
            "summary": re.sub(r"<[^>]+>", "", it.get("summary") or "")[:300],
            "puborg": it.get("puborg") or "",
            "docno": it.get("pcode") or it.get("wenhao") or "",
            "url": it.get("url") or "",
        })
    return out


def pick_representatives(docs, max_n=MAX_DOCS_PER_YEAR):
    """选代表文件：部门权威度 + 标题相关性（真文件 > 解读）> 带文号 > 时间新。"""
    scored = sorted(
        docs,
        key=lambda d: (-(_rank_dept(d["puborg"]) + _title_relevance(d["title"])),
                       0 if d["docno"] else 1,
                       d["date"]),
    )
    picked, depts = [], []
    for d in scored:
        short = _short_dept(d["puborg"])
        if short in depts and len(picked) < max_n:
            continue                      # 同部门只取最强一条（除非名额没满）
        picked.append(d)
        depts.append(short)
        if len(picked) >= max_n:
            break
    # 名额没满就放开部门限制
    for d in scored:
        if len(picked) >= max_n:
            break
        if d not in picked:
            picked.append(d)
    return picked


def kw_of(text):
    return [(k["type"], k["text"]) for k in extract_keywords(text)]


def _ding_score(kws):
    return max([DING_STRENGTH.get(w, 1) for t, w in kws if t == "ding"] or [0])


def _direction(kws):
    has_restrict = any(t == "restrict" for t, _ in kws)
    has_support = any(t in ("verb", "ding") for t, _ in kws)
    if has_restrict and has_support:
        return "有保有压"
    if has_restrict:
        return "限制收紧"
    if has_support:
        return "扶持导向"
    return "中性"


def _pace(kws):
    words = [w for t, w in kws if t == "deg"]
    if any(w in ("加快", "提速", "加速") for w in words):
        return "节奏加快"
    if any(w in ("进一步", "深化", "深入") for w in words):
        return "深化推进"
    if any(w in ("持续", "不断") for w in words):
        return "延续加码"
    if any(w in ("稳步", "有序", "逐步") for w in words):
        return "稳步推进"
    return "常规节奏"


def build_diff(year_docs):
    """给定 {year: [代表文件]}，生成逐年的差异说明。

    关注点与用户方法论对齐：
      1. 力度变化（定调词分级对比：持续用力 → 着力 → 大力 → 坚决）
      2. 性质方向（扶持 / 限制 / 有保有压）
      3. 节奏变化（稳步 / 持续 / 进一步 / 加速）
      4. 发文密度（年度条数对比，密度本身就是政策信号）
    """
    ys = sorted(y for y in year_docs if year_docs[y])
    if len(ys) < 2:
        return ""
    parts = []
    # ① 力度
    seq = []
    for y in ys:
        kws = kw_of(" ".join(d["title"] + d["summary"] for d in year_docs[y]))
        ding_words = [w for t, w in kws if t == "ding"]
        seq.append((y, _ding_score(kws), ding_words))
    for i in range(1, len(seq)):
        y0, s0, w0 = seq[i - 1]
        y1, s1, w1 = seq[i]
        if s1 > s0:
            parts.append(f"{y0}「{'、'.join(w0) or '—'}」→ {y1}「{'、'.join(w1) or '—'}」力度递增")
        elif s1 < s0:
            parts.append(f"{y0}「{'、'.join(w0) or '—'}」→ {y1}「{'、'.join(w1) or '—'}」力度回落")
        elif w1 and set(w1) != set(w0):
            parts.append(f"{y0}→{y1} 定调延续（{'、'.join(w1)}）")
    # ② 性质
    dirs = {y: _direction(kw_of(" ".join(d["title"] + d["summary"] for d in year_docs[y]))) for y in ys}
    dvals = list(dirs.values())
    if len(set(dvals)) > 1 or dvals[0] != "扶持导向":
        parts.append(" / ".join(f"{y}{dirs[y]}" for y in ys))
    # ③ 节奏
    paces = {y: _pace(kw_of(" ".join(d["title"] + d["summary"] for d in year_docs[y]))) for y in ys}
    if len(set(paces.values())) > 1:
        parts.append("节奏：" + " → ".join(paces[y] for y in ys))
    return "；".join(parts)


def main():
    print("== L3 历年政策对比抓取 ==")
    print(f"  年份窗口: {YEARS[0]}–{YEARS[-1]}（{YEARS[-1]} 年数据截至 {AS_OF}）")

    # ── ① 全库标题检索：所有主题的检索词去重后并发抓一次 ──────────
    all_keys = []
    for topic in TOPICS:
        for k in search_keys(topic):
            if k not in all_keys:
                all_keys.append(k)
    print(f"  标题检索词 {len(all_keys)} 个（全库，翻页取尽，并发 {SEARCH_WORKERS}）...")
    try:
        index = build_hit_index(all_keys)
    except SearchError as e:
        print(f"  !! 检索失败，**不覆盖** compare.json（保留上一版 {YEARS[0]}–{YEARS[-1]} 数据）")
        print(f"     {e}")
        return 1
    hit_total = sum(len(v) for v in index.values())
    print(f"  检索完成：命中合计 {hit_total} 条（去重前）")

    # ── ② 逐主题合并命中 → 过滤 → 分组 ─────────────────────────
    topics_out = []
    for topic in TOPICS:
        raw = fetch_topic_items(topic, index)
        docs = filter_year_and_topic(raw, topic, YEARS)
        if not docs:
            print(f"  [{topic['label']:12s}] 0 条，跳过")
            continue

        # 年度计数（密度信号）：全库标题命中数，同一文件只计一次
        counts = {str(y): sum(1 for d in docs if d["year"] == y) for y in YEARS}

        # 每年代表文件
        year_picks = {y: pick_representatives([d for d in docs if d["year"] == y])
                      for y in YEARS}

        # 按部门组织 children（取代表性最强的前几个部门）
        dept_map = {}
        for y in YEARS:
            for d in year_picks[y]:
                short = _short_dept(d["puborg"])
                dept_map.setdefault(short, {"years": {}})
                if str(y) not in dept_map[short]["years"]:
                    kws = kw_of(d["title"] + " " + d["summary"])
                    dept_map[short]["years"][str(y)] = {
                        "text": d["title"][:40],
                        "docno": d["docno"],
                        "date": d["date"],
                        "kw": [{"type": t, "text": w} for t, w in kws],
                        "url": d["url"],
                    }
        # 每部门差异说明 + 部门排序（覆盖年份多的在前）
        children = []
        for short, info in dept_map.items():
            ydocs = {}
            for d in docs:
                if _short_dept(d["puborg"]) == short:
                    ydocs.setdefault(d["year"], []).append(d)
            children.append({
                "dept": short,
                "years": info["years"],
                "diff": build_diff({k: v for k, v in ydocs.items() if v}),
            })
        children.sort(key=lambda c: (-len(c["years"]), c["dept"]))
        children = children[:MAX_DEPTS_PER_TOPIC * 2]

        topics_out.append({
            "key": topic["key"],
            "label": topic["label"],
            "track": topic["track"],
            "code": topic["code"],
            "counts": counts,
            "total": len(docs),
            "searched": search_keys(topic),
            "diff": build_diff({y: year_picks[y] for y in YEARS if year_picks[y]}),
            "children": children,
        })
        print(f"  [{topic['label']:12s}] 总{len(docs):4d}条  "
              + " ".join(f"{y}年{counts[str(y)]:4d}" for y in YEARS)
              + f"  部门{len(children)}")

    # ── 代表文件抓正文取关键语句（每主题每年第一条，并发） ──────
    print("  抓取代表文件正文（关键语句）...")
    tasks = []
    for t in topics_out:
        for c in t["children"]:
            for y, cell in c["years"].items():
                tasks.append((c, y, cell))
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(fetch_article_digest, cell["url"], cell["text"]): (c, y, cell)
                for c, y, cell in tasks}
        done = 0
        for fut in as_completed(futs):
            c, y, cell = futs[fut]
            try:
                summary, body = fut.result()
                if body:
                    kws = extract_keywords(cell["text"], summary)
                    ks = pick_key_sentence(body, kws, title=cell["text"], summary=summary)
                    if ks:
                        cell["keySentence"] = ks[:110]
            except Exception:
                pass
            done += 1
            if done % 40 == 0:
                print(f"    ... {done}/{len(tasks)}")

    year_tot = {str(y): sum(t["counts"].get(str(y), 0) for t in topics_out) for y in YEARS}
    result = {
        "generatedAt": _bj_now(),
        "asOf": AS_OF,
        "years": YEARS,
        "countMode": "title-full-library",
        "searchKeys": len(all_keys),
        "countNote": (
            "计数口径：国务院政策文件库**全库**标题命中「该主题任一关键词」的文件数，同一文件只计一次，"
            "与每行标注的「发文密度」同义；2026-09-19 起由「按时间取最新池再筛」改为「逐主题全库标题检索」"
            "（旧口径是抽样，各年数字不可比，2024 年被系统性压低）。"
        ),
        "topics": topics_out,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\nUpdated {OUTPUT_FILE}")
    print(f"  Topics: {len(topics_out)}")
    print(f"  Window: {YEARS[0]}–{YEARS[-1]} (as of {AS_OF})")
    print(f"  年度合计: " + " / ".join(f"{y}年{year_tot[str(y)]}条" for y in YEARS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
