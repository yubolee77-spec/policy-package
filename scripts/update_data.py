#!/usr/bin/env python3
"""
Policy Intelligence Workbench - Daily Auto Update
Only writes to data/latest.json. NEVER touches app.js or index.html.
If any source fails, skip it and continue. The script must never crash.

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
from datetime import date
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

# 各部委在 API 返回 puborg 字段中的匹配关键词
MINISTRY_MAP = {
    "国家发展和改革委员会": "发改委最新动态",
    "中国人民银行": "央行最新动态",
    "中国证券监督管理委员会": "证监会最新动态",
    "工业和信息化部": "工信部最新动态",
    "国家统计局": "国家统计局最新数据发布",
}


# ── HTTP 工具 ─────────────────────────────────────────────────────

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


# ── API 数据源（主要）────────────────────────────────────────────

def fetch_gov_api():
    """通过国务院政策文件库 API 获取数据。

    API 只用于获取国务院公文（gongwen）和工信部文件（bumenfile 中 puborg 以"工业和信息化部"开头）。
    央行/证监会/统计局等部委的 HTML 页面数据质量更好，由 HTML fallback 处理。
    """
    all_items = []

    # 1. 获取国务院公文（gongwen 分类）
    url = f"{API_BASE}?t=zhengcelibrary&q=&sort=pubtime&sortType=1&p=1&n=8"
    data = safe_fetch_json(url)
    if data and "searchVO" in data:
        cat_map = data["searchVO"].get("catMap", {})
        gongwen = cat_map.get("gongwen", {})
        for item in gongwen.get("listVO", []):
            title = item.get("title", "").strip()
            url = item.get("url", "")
            if is_junk(title, url):
                continue
            all_items.append({
                "title": title,
                "desc": "国务院最新政策文件",
                "url": url,
            })

    # 2. 获取部门文件，只取工信部（puborg 以"工业和信息化部"开头）
    for p in range(1, 4):
        url = f"{API_BASE}?t=zhengcelibrary&q=&sort=pubtime&sortType=1&p={p}&n=40"
        data = safe_fetch_json(url)
        if not data or "searchVO" not in data:
            break
        cat_map = data["searchVO"].get("catMap", {})
        bumen = cat_map.get("bumenfile", {})
        items = bumen.get("listVO", [])
        if not items:
            break
        miit_count = sum(1 for i in all_items if i["desc"] == "工信部最新动态")
        for item in items:
            if miit_count >= 8:
                break
            puborg = item.get("puborg", "")
            # 精确匹配：puborg 以"工业和信息化部"开头（排除联合发文里不是牵头部门的）
            if puborg.startswith("工业和信息化部"):
                title = item.get("title", "").strip()
                url = item.get("url", "")
                if is_junk(title, url):
                    continue
                all_items.append({
                    "title": title,
                    "desc": "工信部最新动态",
                    "url": url,
                })
                miit_count += 1
        if miit_count >= 8:
            break

    return all_items


# ── HTML 爬虫（fallback）─────────────────────────────────────────

def fetch_gov_cn_html():
    """HTML fallback: 国务院政策。"""
    url = "https://www.gov.cn/zhengce/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="([^"]*content_\d+\.htm)"[^>]*>([^<]{6,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, "https://www.gov.cn/zhengce")
        if full in seen:
            continue
        seen.add(full)
        items.append({"title": title, "desc": "国务院最新政策文件", "url": full})
    return items[:8]


def fetch_ndrc_html():
    """HTML fallback: 发改委。"""
    url = "https://www.ndrc.gov.cn/xwdt/xwfb/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    for m in re.finditer(r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        items.append({"title": title, "desc": "发改委最新动态", "url": clean_link(link, url)})
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
        items.append({"title": title, "desc": "央行最新动态", "url": full})
    return items[:8]


def fetch_csrc_html():
    """HTML fallback: 证监会。"""
    url = "https://www.csrc.gov.cn/csrc/xwfb/index.shtml"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="(/csrc/c\d+/c\d+/content\.shtml)"[^>]*>([^<]{6,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = clean_link(link, "https://www.csrc.gov.cn")
        if full in seen:
            continue
        seen.add(full)
        items.append({"title": title, "desc": "证监会最新动态", "url": full})
    return items[:8]


def fetch_miit_html():
    """HTML fallback: 工信部。"""
    url = "https://www.miit.gov.cn/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    seen = set()
    for m in re.finditer(r'<a[^>]*href="(https?://[^"]*art_\w+\.html)"[^>]*>([^<]{8,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        full = link.replace("http://", "https://")
        if full in seen:
            continue
        seen.add(full)
        items.append({"title": title, "desc": "工信部最新动态", "url": full})
    return items[:8]


def fetch_stats_html():
    """HTML fallback: 国家统计局。"""
    url = "https://www.stats.gov.cn/sj/zxfb/"
    html = safe_fetch(url)
    if not html:
        return []
    items = []
    for m in re.finditer(r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>', html):
        link, title = m.group(1).strip(), m.group(2).strip()
        if is_junk(title, link):
            continue
        items.append({"title": title, "desc": "国家统计局最新数据发布", "url": clean_link(link, url)})
    return items[:8]


# ── 主函数 ──────────────────────────────────────────────────────

def main():
    today_str = date.today().strftime("%Y-%m-%d")
    result = {
        "lastUpdated": today_str,
        "monthLabel": MONTH_LABEL,
        "timeline": [],
    }

    # 1. 优先使用 API
    print("Fetching via gov.cn API...")
    api_items = []
    try:
        api_items = fetch_gov_api()
        print(f"  API returned {len(api_items)} items")
    except Exception as e:
        print(f"  API error: {e}")

    # 2. 检查 API 是否覆盖了所有来源
    api_sources = set(item["desc"] for item in api_items)
    all_sources = {"国务院最新政策文件", "发改委最新动态", "央行最新动态",
                   "证监会最新动态", "工信部最新动态", "国家统计局最新数据发布"}
    missing = all_sources - api_sources

    # 3. 对 API 未覆盖的来源，用 HTML 爬虫 fallback
    if missing:
        print(f"  API missing sources: {missing}")
        print("  Falling back to HTML scraping...")
        html_fetchers = {
            "国务院最新政策文件": fetch_gov_cn_html,
            "发改委最新动态": fetch_ndrc_html,
            "央行最新动态": fetch_pbc_html,
            "证监会最新动态": fetch_csrc_html,
            "工信部最新动态": fetch_miit_html,
            "国家统计局最新数据发布": fetch_stats_html,
        }
        for src in missing:
            fetcher = html_fetchers.get(src)
            if not fetcher:
                continue
            print(f"  Fetching {src} via HTML...")
            try:
                items = fetcher()
                print(f"    Found {len(items)} items")
                api_items.extend(items)
            except Exception as e:
                print(f"    Error: {e}")

    # 4. 统一去重（按 title 和 url 双重去重）
    seen_titles = set()
    seen_urls = set()
    unique = []
    for item in api_items:
        title = item["title"]
        url = item["url"]
        if title in seen_titles or url in seen_urls:
            continue
        seen_titles.add(title)
        seen_urls.add(url)
        # 清理内部字段
        clean_item = {"title": title, "desc": item["desc"], "url": url}
        unique.append(clean_item)

    result["timeline"] = unique
    print(f"\nTotal after dedup: {len(unique)} items")

    # 5. 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {OUTPUT_FILE}")
    print(f"  Date: {today_str}")
    print(f"  Timeline entries: {len(result['timeline'])}")


if __name__ == "__main__":
    main()
