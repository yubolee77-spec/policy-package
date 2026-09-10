#!/usr/bin/env python3
"""
Policy Intelligence Workbench - Daily Auto Update
Only writes to data/latest.json. NEVER touches app.js or index.html.
If any source fails, skip it and continue. The script must never crash.

修复记录 (2026-09-10):
  1. 去重 bug：所有源抓取后统一去重（原来统计局数据未去重导致重复）
  2. 过滤垃圾链接：ICP备案号、beian.miit.gov.cn、过短标题
  3. 修复 URL 构造 bug：去掉 link 前缀的 ./ 和 ../ 避免出现 .gov.cn./ 错误 URL
  4. 修复 gov.cn 抓取正则：放宽匹配条件，适配官网改版
  5. 新增证监会动态抓取源 (csrc.gov.cn)
  6. 新增工信部抓取源 (miit.gov.cn)
"""

import json
import os
import re
from datetime import date
from urllib.request import urlopen, Request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "latest.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MONTH_LABEL = f"{date.today().year}年{date.today().month}月"

# ── 垃圾标题/URL 过滤关键词 ──────────────────────────────────────
JUNK_KEYWORDS = [
    'icp备', 'icp证', '京icp', '沪icp', '粤icp', '备案',
    'beian.miit', '网站标识码', '公安备',
    '版权所有', '联系我们', '网站地图', '无障碍',
]


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


def clean_link(link, base_domain):
    """构造完整 URL，去掉 link 前缀的 ./ ../ 避免出现 .gov.cn./ 错误。"""
    if not link:
        return ""
    # 去掉前缀的 ./ 或 ../
    link = re.sub(r'^(\./)+', '', link)
    link = re.sub(r'^(\.\./)+', '', link)
    if link.startswith("http"):
        return link
    if link.startswith("/"):
        return base_domain + link
    return base_domain + "/" + link


def is_junk(title, url):
    """过滤备案号、版权声明等垃圾链接。"""
    combined = (title + url).lower()
    for kw in JUNK_KEYWORDS:
        if kw in combined:
            return True
    # 标题过短
    if len(title.strip()) < 8:
        return True
    # URL 指向备案站
    if 'beian' in url.lower():
        return True
    return False


# ── 政策新闻源 ──────────────────────────────────────────────────

def fetch_gov_cn_policies():
    """国务院最新政策文件 (www.gov.cn/zhengce/)。

    实际链接格式：
      - https://www.gov.cn/zhengce/content/202609/content_7080627.htm
      - ./202609/content_7080188.htm
    统一匹配 content_数字.htm
    """
    url = "https://www.gov.cn/zhengce/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    seen_urls = set()
    pattern = r'<a[^>]*href="([^"]*content_\d+\.htm)"[^>]*>([^<]{6,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        full_url = clean_link(link, "https://www.gov.cn/zhengce")
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        items.append({
            "title": title,
            "desc": "国务院最新政策文件",
            "url": full_url,
        })
    return items[:8]


def fetch_ndrc_news():
    """发改委最新动态 (www.ndrc.gov.cn)。"""
    url = "https://www.ndrc.gov.cn/xwdt/xwfb/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        full_url = clean_link(link, "https://www.ndrc.gov.cn")
        items.append({
            "title": title,
            "desc": "发改委最新动态",
            "url": full_url,
        })
    return items[:8]


def fetch_pbc_news():
    """央行最新动态 (www.pbc.gov.cn 首页)。

    /goutongjiaoliu/113456/113469/ 子路径返回 403，但首页 200 可访问。
    新闻链接格式：/goutongjiaoliu/113456/113469/2026090909080511735/index.html
    """
    url = "https://www.pbc.gov.cn/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    seen_urls = set()
    # 匹配 /goutongjiaoliu/113456/113469/数字/index.html 格式
    pattern = r'<a[^>]*href="(/goutongjiaoliu/113456/113469/\d+/index\.html)"[^>]*>([^<]{6,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        full_url = clean_link(link, "https://www.pbc.gov.cn")
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        items.append({
            "title": title,
            "desc": "央行最新动态",
            "url": full_url,
        })
    return items[:8]


def fetch_csrc_news():
    """证监会最新动态 (www.csrc.gov.cn/csrc/xwfb/index.shtml)。

    实际链接格式：/csrc/c106311/c7657131/content.shtml
    """
    url = "https://www.csrc.gov.cn/csrc/xwfb/index.shtml"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    seen_urls = set()
    pattern = r'<a[^>]*href="(/csrc/c\d+/c\d+/content\.shtml)"[^>]*>([^<]{6,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        full_url = clean_link(link, "https://www.csrc.gov.cn")
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        items.append({
            "title": title,
            "desc": "证监会最新动态",
            "url": full_url,
        })
    return items[:8]


def fetch_miit_news():
    """工信部最新动态 (www.miit.gov.cn 首页)。

    实际链接格式：https://www.miit.gov.cn/xwfb/szyw/art/2026/art_XXX.html
    """
    url = "https://www.miit.gov.cn/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    seen_urls = set()
    pattern = r'<a[^>]*href="(https?://[^"]*art_\w+\.html)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        # 统一 https
        full_url = link.replace("http://", "https://")
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        items.append({
            "title": title,
            "desc": "工信部最新动态",
            "url": full_url,
        })
    return items[:8]


# ── 宏观数据源 ──────────────────────────────────────────────────

def fetch_stats_gov_data():
    """国家统计局最新数据发布 (www.stats.gov.cn)。"""
    url = "https://www.stats.gov.cn/sj/zxfb/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1).strip()
        title = m.group(2).strip()
        if is_junk(title, link):
            continue
        full_url = clean_link(link, "https://www.stats.gov.cn")
        items.append({
            "title": title,
            "desc": "国家统计局最新数据发布",
            "url": full_url,
        })
    return items[:8]


# ── 主函数 ──────────────────────────────────────────────────────

def main():
    today_str = date.today().strftime("%Y-%m-%d")
    result = {
        "lastUpdated": today_str,
        "monthLabel": MONTH_LABEL,
        "timeline": [],
    }

    # 1. 抓取所有源的原始数据
    all_raw = []
    sources = [
        ("国务院政策", fetch_gov_cn_policies),
        ("发改委", fetch_ndrc_news),
        ("央行", fetch_pbc_news),
        ("证监会", fetch_csrc_news),
        ("工信部", fetch_miit_news),
        ("国家统计局", fetch_stats_gov_data),
    ]

    for name, fetcher in sources:
        print(f"Fetching {name}...")
        try:
            items = fetcher()
            all_raw.extend(items)
            print(f"  Found {len(items)} items")
        except Exception as e:
            print(f"  Error: {e} (skipped)")

    # 2. 统一去重（按 title 和 url 双重去重，保留首次出现的）
    seen_titles = set()
    seen_urls = set()
    unique = []
    for item in all_raw:
        title = item["title"]
        url = item["url"]
        if title in seen_titles or url in seen_urls:
            continue
        seen_titles.add(title)
        seen_urls.add(url)
        unique.append(item)

    result["timeline"] = unique
    print(f"\nTotal after dedup: {len(unique)} items")

    # 3. 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {OUTPUT_FILE}")
    print(f"  Date: {today_str}")
    print(f"  Timeline entries: {len(result['timeline'])}")


if __name__ == "__main__":
    main()
