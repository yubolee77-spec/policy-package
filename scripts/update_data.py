#!/usr/bin/env python3
"""
Policy Intelligence Workbench - Daily Auto Update
Only writes to data/latest.json. NEVER touches app.js or index.html.
If any source fails, skip it and continue. The script must never crash.
"""

import json
import os
import re
import sys
from datetime import datetime, date
from urllib.request import urlopen, Request
from html.parser import HTMLParser

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "latest.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MONTH_LABEL = f"{date.today().year}年{date.today().month}月"


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


# ── Policy news sources ──────────────────────────────────────

def fetch_gov_cn_policies():
    """Fetch latest policies from www.gov.cn."""
    url = "https://www.gov.cn/zhengce/latest/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    # Try to extract policy titles and URLs
    pattern = r'<a[^>]*href="(/zhengce/[^"]*)"[^>]*>([^<]+)</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1)
        title = m.group(2).strip()
        if title and len(title) > 5:
            full_url = "https://www.gov.cn" + link if link.startswith("/") else link
            items.append({
                "title": title,
                "desc": "国务院最新政策文件",
                "url": full_url,
            })
    return items[:5]


def fetch_ndrc_news():
    """Fetch latest news from National Development and Reform Commission."""
    url = "https://www.ndrc.gov.cn/xwdt/xwfb/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1)
        title = m.group(2).strip()
        if title and len(title) > 5:
            full_url = link if link.startswith("http") else "https://www.ndrc.gov.cn" + link
            items.append({
                "title": title,
                "desc": "发改委最新动态",
                "url": full_url,
            })
    return items[:5]


def fetch_pbc_news():
    """Fetch latest news from People's Bank of China."""
    url = "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1)
        title = m.group(2).strip()
        if title and len(title) > 5 and "index" not in link:
            full_url = link if link.startswith("http") else "https://www.pbc.gov.cn" + link
            items.append({
                "title": title,
                "desc": "央行最新动态",
                "url": full_url,
            })
    return items[:5]


def fetch_policy_news():
    """Fetch policy news from all sources, deduplicate."""
    all_news = []
    all_news.extend(fetch_gov_cn_policies())
    all_news.extend(fetch_ndrc_news())
    all_news.extend(fetch_pbc_news())

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_news:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return unique


# ── Macro data sources ───────────────────────────────────────

def fetch_stats_gov_data():
    """Fetch latest macro data from National Bureau of Statistics."""
    url = "https://www.stats.gov.cn/sj/zxfb/"
    html = safe_fetch(url)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]*href="([^"]*t\d+_\d+\.html?)"[^>]*>([^<]{8,})</a>'
    for m in re.finditer(pattern, html):
        link = m.group(1)
        title = m.group(2).strip()
        if title and len(title) > 5:
            full_url = link if link.startswith("http") else "https://www.stats.gov.cn" + link
            items.append({
                "title": title,
                "desc": "国家统计局最新数据发布",
                "url": full_url,
            })
    return items[:5]


# ── Main ─────────────────────────────────────────────────────

def main():
    today_str = date.today().strftime("%Y-%m-%d")
    result = {
        "lastUpdated": today_str,
        "monthLabel": MONTH_LABEL,
        "timeline": [],
    }

    # Fetch policy news
    print("Fetching policy news...")
    news = fetch_policy_news()
    if news:
        result["timeline"] = news
        print(f"  Found {len(news)} news items")
    else:
        print("  No new news found (sources may be unavailable)")

    # Fetch stats data
    print("Fetching macro data...")
    stats = fetch_stats_gov_data()
    if stats:
        result["timeline"].extend(stats)
        print(f"  Found {len(stats)} data items")
    else:
        print("  No new stats found (sources may be unavailable)")

    # Ensure data directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Write JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {OUTPUT_FILE}")
    print(f"  Date: {today_str}")
    print(f"  Timeline entries: {len(result['timeline'])}")


if __name__ == "__main__":
    main()
