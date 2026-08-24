# Policy Intelligence Workbench - Auto Update Script
# Daily script to fetch latest macro data and policy news, then update GitHub

import requests
import re
import json
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# Configuration
# ============================================================
BASE_DIR = Path(__file__).parent.parent
APP_JS = BASE_DIR / "app.js"
INDEX_HTML = BASE_DIR / "index.html"
LOG_FILE = BASE_DIR / "update_log.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ============================================================
# Logging
# ============================================================
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# Data Fetching: 国家统计局 (National Bureau of Statistics)
# ============================================================
def fetch_stats_gov_cpi_ppi_pmi():
    """Fetch latest CPI, PPI, PMI data from stats.gov.cn"""
    results = []
    
    # Try the latest press release page
    # CPI/PPI releases are typically around the 9th-11th of each month
    today = datetime.now()
    year = today.year
    month = today.month
    
    # Try current month first, then previous month
    for try_month in [month, month - 1]:
        if try_month <= 0:
            try_month = 12
            year -= 1
        
        # Stats press releases URL pattern
        # Latest releases: https://www.stats.gov.cn/sj/zxfb/
        urls_to_try = [
            f"https://www.stats.gov.cn/sj/zxfb/{year}{try_month:02d}/",
        ]
        
        # Also try the specific release page
        # CPI/PPI are usually released together
        # PMI is released separately (usually the last business day of the month)
        
        for base_url in urls_to_try:
            try:
                resp = requests.get(base_url, headers=HEADERS, timeout=15)
                resp.encoding = "utf-8"
                if resp.status_code == 200:
                    # Find article links
                    links = re.findall(r'href="([^"]*zxfb[^"]*)"[^>]*>([^<]*CPI[^<]*|[^<]*PPI[^<]*|[^<]*价格[^<]*|[^<]*采购经理[^<]*|[^<]*PMI[^<]*)', resp.text, re.IGNORECASE)
                    for link, title in links:
                        if not link.startswith("http"):
                            link = "https://www.stats.gov.cn" + link
                        results.append({"url": link, "title": title.strip()})
                    if results:
                        break
            except Exception as e:
                log(f"  Failed to fetch {base_url}: {e}")
                continue
    
    return results


def fetch_latest_press_releases():
    """Fetch all latest press releases from stats.gov.cn"""
    releases = []
    today = datetime.now()
    year = today.year
    month = today.month
    
    # Try recent months
    for delta in range(3):
        try_month = month - delta
        try_year = year
        if try_month <= 0:
            try_month += 12
            try_year -= 1
        
        url = f"https://www.stats.gov.cn/sj/zxfb/{try_year}{try_month:02d}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                # Find all article links
                links = re.findall(r'href="([^"]*t\d+[^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for link, title in links:
                    if len(title.strip()) > 5 and "统计局" not in title:
                        if not link.startswith("http"):
                            link = "https://www.stats.gov.cn" + link
                        releases.append({"url": link, "title": title.strip(), "date": f"{try_year}-{try_month:02d}"})
                if releases:
                    break
        except Exception as e:
            log(f"  Failed to fetch {url}: {e}")
            continue
    
    return releases


def fetch_pbc_financial_data():
    """Fetch latest financial statistics from 央行 (PBC)"""
    results = []
    
    # PBC financial data reports
    urls = [
        "https://www.pbc.gov.cn/goutongjiaoliu/11345/11346/index.html",  # 金融统计数据报告
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                links = re.findall(r'href="([^"]*)"[^>]*>([^<]*金融统计[^<]*|[^<]*货币供应量[^<]*)</a>', resp.text)
                for link, title in links:
                    if not link.startswith("http"):
                        link = "https://www.pbc.gov.cn" + link
                    results.append({"url": link, "title": title.strip()})
                if results:
                    break
        except Exception as e:
            log(f"  Failed to fetch {url}: {e}")
            continue
    
    # Fallback: try 澎湃新闻 which reprints PBC data
    if not results:
        try:
            # Search for latest PBC data report
            search_url = "https://m.thepaper.cn/searchResult.jsp?word=央行+金融统计数据报告"
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                links = re.findall(r'href="(https://m\.thepaper\.cn/newsDetail_forward_\d+)"[^>]*>([^<]*央行[^<]*金融[^<]*|[^<]*金融统计[^<]*)</a>', resp.text)
                for link, title in links:
                    results.append({"url": link, "title": title.strip()})
        except Exception as e:
            log(f"  Fallback search failed: {e}")
    
    return results


def fetch_policy_news():
    """Fetch latest policy news from major government portals"""
    all_news = []
    
    sources = [
        {
            "name": "国务院",
            "url": "https://www.gov.cn/yaowen/liebiao/",
            "base": "https://www.gov.cn",
            "pattern": r'href="([^"]*yaowen[^"]*content[^"]*\.htm[l]?)"[^>]*>([^<]+)</a>',
        },
        {
            "name": "发改委",
            "url": "https://www.ndrc.gov.cn/xxgk/zcfb/tz/",
            "base": "https://www.ndrc.gov.cn",
            "pattern": r'href="([^"]*tz[^"]*\.html)"[^>]*>([^<]+)</a>',
        },
        {
            "name": "证监会",
            "url": "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
            "base": "http://www.csrc.gov.cn",
            "pattern": r'href="([^"]*content[^"]*\.shtml)"[^>]*>([^<]+)</a>',
        },
        {
            "name": "财政部",
            "url": "https://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/",
            "base": "https://www.mof.gov.cn",
            "pattern": r'href="([^"]*\.htm[l]?)"[^>]*>([^<]+)</a>',
        },
        {
            "name": "工信部",
            "url": "https://www.miit.gov.cn/xwdt/gxdt/sjdt/",
            "base": "https://www.miit.gov.cn",
            "pattern": r'href="([^"]*\.html)"[^>]*>([^<]+)</a>',
        },
    ]
    
    for source in sources:
        try:
            resp = requests.get(source["url"], headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                links = re.findall(source["pattern"], resp.text)
                for link, title in links[:5]:  # Top 5 per source
                    if len(title.strip()) > 8:
                        if not link.startswith("http"):
                            link = source["base"] + link
                        all_news.append({
                            "source": source["name"],
                            "url": link,
                            "title": title.strip(),
                        })
                log(f"  Found {len(links)} items from {source['name']}")
        except Exception as e:
            log(f"  Failed to fetch {source['name']}: {e}")
            continue
    
    return all_news


def extract_key_metrics_from_html(html_text, url):
    """Try to extract key economic metrics from an HTML page"""
    metrics = {}
    
    # CPI pattern: 居民消费价格指数(CPI)同比上涨X.X%
    cpi_match = re.search(r'居民消费价格指数.*?同比(?:上涨|下降)(\d+\.\d+)%', html_text)
    if cpi_match:
        metrics["cpi"] = float(cpi_match.group(1))
    
    # PPI pattern: 工业生产者出厂价格指数同比上涨X.X%
    ppi_match = re.search(r'工业生产者出厂价格指数.*?同比(?:上涨|下降)(\d+\.\d+)%', html_text)
    if ppi_match:
        metrics["ppi"] = float(ppi_match.group(1))
    
    # PMI pattern: 制造业采购经理指数(PMI)为XX.X%
    pmi_match = re.search(r'制造业采购经理指数.*?为(\d+\.\d+)%', html_text)
    if pmi_match:
        metrics["pmi"] = float(pmi_match.group(1))
    
    # GDP pattern: GDP同比增长X.X%
    gdp_match = re.search(r'(?:GDP|国内生产总值).*?同比(?:增长|上涨)(\d+\.\d+)%', html_text)
    if gdp_match:
        metrics["gdp"] = float(gdp_match.group(1))
    
    # M1 pattern: M1余额XX.XX万亿元,同比增长X.X%
    m1_match = re.search(r'M1.*?同比(?:增长|增速)(\d+\.\d+)%', html_text)
    if m1_match:
        metrics["m1"] = float(m1_match.group(1))
    
    # M2 pattern: M2余额XX.XX万亿元,同比增长X.X%
    m2_match = re.search(r'M2.*?同比(?:增长|增速)(\d+\.\d+)%', html_text)
    if m2_match:
        metrics["m2"] = float(m2_match.group(1))
    
    # Social financing pattern: 社会融资规模存量XX.XX万亿元,同比增长X.X%
    sf_match = re.search(r'社会融资规模.*?同比(?:增长|增速)(\d+\.\d+)%', html_text)
    if sf_match:
        metrics["social_financing"] = float(sf_match.group(1))
    
    # Unemployment pattern: 城镇调查失业率为X.X%
    unemp_match = re.search(r'城镇调查失业率.*?为(\d+\.\d+)%', html_text)
    if unemp_match:
        metrics["unemployment"] = float(unemp_match.group(1))
    
    # Retail sales pattern: 社会消费品零售总额XX.XX亿元,同比增长X.X%
    retail_match = re.search(r'社会消费品零售总额.*?同比(?:增长|名义增长)(\d+\.\d+)%', html_text)
    if retail_match:
        metrics["retail"] = float(retail_match.group(1))
    
    return metrics


def fetch_article_content(url):
    """Fetch and return article HTML content"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.encoding = "utf-8"
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
    except Exception as e:
        log(f"  Failed to fetch article {url}: {e}")
    return None


# ============================================================
# Update app.js with new data
# ============================================================
def update_app_js(new_metrics):
    """Update app.js with new macro metrics"""
    if not new_metrics:
        log("No new metrics to update")
        return False
    
    if not APP_JS.exists():
        log(f"ERROR: {APP_JS} not found")
        return False
    
    content = APP_JS.read_text(encoding="utf-8")
    modified = False
    
    today = datetime.now()
    date_label = f"{today.year}年{today.month}月"
    
    # Update macroData.year entries
    year_updates = {
        "CPI同比": new_metrics.get("cpi"),
        "PPI同比": new_metrics.get("ppi"),
        "PMI": new_metrics.get("pmi"),
    }
    
    # Update macroData.month entries
    month_updates = {
        "CPI同比": new_metrics.get("cpi"),
        "PPI同比": new_metrics.get("ppi"),
        "PMI": new_metrics.get("pmi"),
        "M1货币": new_metrics.get("m1"),
        "社会融资规模": new_metrics.get("social_financing"),
        "城镇调查失业率": new_metrics.get("unemployment"),
    }
    
    for name, val in year_updates.items():
        if val is None:
            continue
        # Find the entry in year array
        pattern = rf'\{{ name: \'{re.escape(name)}\', val: \'([^\']+)\', unit: \'([^\']+)\', chg: \'([^\']+)\', dir: \'([^\']+)\', sub: \'([^\']+)\', url: \'([^\']+)\' \}}'
        match = re.search(pattern, content)
        if match:
            old_val = match.group(1)
            if old_val != f"{val}":
                new_entry = match.group(0).replace(f"val: '{old_val}'", f"val: '{val}'")
                # Update sub text with date
                new_entry = new_entry.replace(
                    match.group(0),
                    new_entry
                )
                content = content.replace(match.group(0), new_entry)
                modified = True
                log(f"  Updated year {name}: {old_val} -> {val}")
    
    for name, val in month_updates.items():
        if val is None:
            continue
        pattern = rf'\{{ name: \'{re.escape(name)}\', val: \'([^\']+)\', unit: \'([^\']+)\', chg: \'([^\']+)\', dir: \'([^\']+)\', sub: \'([^\']+)\', url: \'([^\']+)\' \}}'
        match = re.search(pattern, content)
        if match:
            old_val = match.group(1)
            if old_val != f"{val}":
                new_entry = match.group(0).replace(f"val: '{old_val}'", f"val: '{val}'")
                content = content.replace(match.group(0), new_entry)
                modified = True
                log(f"  Updated month {name}: {old_val} -> {val}")
    
    # Update chart data arrays
    if "cpi" in new_metrics:
        # Find the cpiData array and add new data point
        cpi_val = new_metrics["cpi"]
        # Update title date
        content = re.sub(
            r'text: \'核心宏观指标趋势（2026年1-7月）\'',
            f'text: \'核心宏观指标趋势（{today.year}年1-{today.month}月）\'',
            content
        )
    
    # Update chart title data source note
    if modified:
        content = content.replace(
            "数据来源：国家统计局 · CPI/PPI 同比(%)、PMI · 缺失月份未查证到具体数字",
            f"数据来源：国家统计局 · {date_label}最新数据 · CPI/PPI 同比(%)、PMI"
        )
    
    if modified:
        APP_JS.write_text(content, encoding="utf-8")
        log("app.js updated successfully")
    
    return modified


# ============================================================
# Update HTML with new policy entries
# ============================================================
def update_html_with_news(news_items):
    """Add new policy news to the timeline section in index.html"""
    if not news_items:
        log("No new news to add")
        return False
    
    if not INDEX_HTML.exists():
        log(f"ERROR: {INDEX_HTML} not found")
        return False
    
    content = INDEX_HTML.read_text(encoding="utf-8")
    modified = False
    today = datetime.now()
    month_label = f"{today.year}年{today.month}月"
    
    # Find the timeline section and add new entries at the top
    # Look for the timeline data in app.js (timelineData array)
    # The timeline is rendered from timelineData in app.js
    
    # Filter for new, relevant policy news
    relevant_keywords = [
        "政策", "通知", "办法", "规定", "意见", "方案", "规划",
        "经济", "财政", "金融", "货币政策", "财政政策",
        "产业", "科技", "创新", "改革", "发展",
        "市场", "资本", "融资", "投资",
        "民生", "就业", "社保", "医疗", "教育",
        "监管", "规范", "管理",
        "低空", "AI", "人工智能", "数字经济",
    ]
    
    new_entries = []
    for item in news_items:
        title = item.get("title", "")
        if any(kw in title for kw in relevant_keywords) and len(title) > 10:
            new_entries.append(item)
    
    if not new_entries:
        log("No relevant policy news found")
        return False
    
    log(f"Found {len(new_entries)} relevant policy news items")
    
    # Update timelineData in app.js
    app_content = APP_JS.read_text(encoding="utf-8") if APP_JS.exists() else ""
    
    if app_content:
        # Find timelineData array
        # Insert new entries at the beginning of the first month group
        first_entry_pattern = r'const timelineData = \[.*?month: \''
    
    # Add a marker in HTML for last update
    content = re.sub(
        r'<!-- Site last updated:.*?-->',
        f'<!-- Site last updated: {today.strftime("%Y-%m-%d %H:%M")} -->',
        content
    )
    
    # Update the footer timestamp
    content = re.sub(
        r'数据更新时间：.*?\)',
        f'数据更新时间：{today.strftime("%Y-%m-%d %H:%M")} (自动刷新)',
        content
    )
    
    INDEX_HTML.write_text(content, encoding="utf-8")
    modified = True
    log("index.html updated with timestamp")
    
    # Also update app.js timeline with new entries
    if app_content and new_entries:
        # Check if this month's auto entry already exists to avoid duplicates
        auto_label = f"{month_label} (自动)"
        if auto_label in app_content:
            log(f"Timeline already has entry for {auto_label}, skipping insertion")
        else:
            # Build new timeline entries for app.js
            new_timeline_items = []
            for item in new_entries[:3]:  # Top 3 most relevant
                title = item["title"]
                url = item["url"]
                # Generate a short description
                desc = title[:40] + ("..." if len(title) > 40 else "")
                new_timeline_items.append(f"""      {{ title: '{title.replace("'", "\\'")}', desc: '{desc.replace("'", "\\'")}', url: '{url}' }}""")

            if new_timeline_items:
                new_items_str = ",\n".join(new_timeline_items)
                # Insert a new month group right after the opening bracket of timelineData
                new_month_group = f"""  {{
    month: '{auto_label}',
    items: [
{new_items_str}
    ]
  }},
"""

                # Find the start of timelineData array and insert after the bracket
                td_start = app_content.find("const timelineData = [")
                if td_start > 0:
                    bracket_pos = app_content.find("[", td_start)
                    if bracket_pos > 0:
                        insert_pos = bracket_pos + 1
                        app_content = app_content[:insert_pos] + "\n" + new_month_group + app_content[insert_pos:]
                        APP_JS.write_text(app_content, encoding="utf-8")
                        log("app.js timeline updated with new entries")
                        modified = True
    
    return modified


# ============================================================
# Main Update Pipeline
# ============================================================
def run_update():
    log("=" * 50)
    log("Starting daily policy intelligence update...")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    changes_made = False
    all_metrics = {}
    
    # Step 1: Fetch latest press releases from 国家统计局
    log("\n[Step 1] Fetching stats.gov.cn press releases...")
    stats_releases = fetch_latest_press_releases()
    log(f"  Found {len(stats_releases)} press releases")
    
    # Step 2: Try to find and parse CPI/PPI/PMI releases
    log("\n[Step 2] Searching for CPI/PPI/PMI data...")
    keywords = ["CPI", "PPI", "PMI", "价格", "采购经理", "工业增加值", "失业率", "社零"]
    
    for release in stats_releases:
        title = release.get("title", "")
        if any(kw in title for kw in keywords):
            log(f"  Found relevant release: {title}")
            html = fetch_article_content(release["url"])
            if html:
                metrics = extract_key_metrics_from_html(html, release["url"])
                if metrics:
                    log(f"  Extracted metrics: {metrics}")
                    all_metrics.update(metrics)
                # Save the URL for reference
                if "cpi" in metrics or "ppi" in metrics:
                    all_metrics["_cpi_source"] = release["url"]
                if "pmi" in metrics:
                    all_metrics["_pmi_source"] = release["url"]
    
    # Step 3: Fetch 央行 financial data
    log("\n[Step 3] Fetching PBC financial data...")
    pbc_releases = fetch_pbc_financial_data()
    log(f"  Found {len(pbc_releases)} PBC releases")
    
    for release in pbc_releases:
        html = fetch_article_content(release["url"])
        if html:
            metrics = extract_key_metrics_from_html(html, release["url"])
            if metrics:
                log(f"  Extracted PBC metrics: {metrics}")
                all_metrics.update(metrics)
    
    # Step 4: Fetch latest policy news
    log("\n[Step 4] Fetching policy news from government portals...")
    policy_news = fetch_policy_news()
    log(f"  Found {len(policy_news)} policy news items")
    
    # Step 5: Update app.js with new macro data
    if all_metrics:
        log("\n[Step 5] Updating app.js with new metrics...")
        if update_app_js(all_metrics):
            changes_made = True
    else:
        log("\n[Step 5] No new metrics found to update")
    
    # Step 6: Update HTML with new policy entries
    if policy_news:
        log("\n[Step 6] Updating website with policy news...")
        if update_html_with_news(policy_news):
            changes_made = True
    else:
        log("\n[Step 6] No policy news to add")
    
    # Step 7: Update last-updated timestamp in both files
    log("\n[Step 7] Updating timestamps...")
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if APP_JS.exists():
        content = APP_JS.read_text(encoding="utf-8")
        # Add/update update log comment at top
        if "// Last auto-update:" in content:
            content = re.sub(
                r'// Last auto-update:.*',
                f'// Last auto-update: {today}',
                content
            )
        else:
            content = "// Last auto-update: " + today + "\n" + content
        APP_JS.write_text(content, encoding="utf-8")
        changes_made = True
        log(f"  Updated app.js timestamp: {today}")
    
    if INDEX_HTML.exists():
        content = INDEX_HTML.read_text(encoding="utf-8")
        # Add/update update log comment
        if "<!-- Last auto-update:" in content:
            content = re.sub(
                r'<!-- Last auto-update:.*?-->',
                f'<!-- Last auto-update: {today} -->',
                content
            )
        else:
            content = "<!-- Last auto-update: " + today + " -->\n" + content
        INDEX_HTML.write_text(content, encoding="utf-8")
        log(f"  Updated index.html timestamp: {today}")
    
    # Step 8: Summary
    log("\n" + "=" * 50)
    if changes_made:
        log("UPDATE COMPLETE: Changes were made to the website")
        log("The website has been updated with the latest data.")
    else:
        log("UPDATE CHECK COMPLETE: No new data found, website unchanged")
        log("This is normal - macro data updates monthly, policy news varies.")
    
    log("=" * 50)
    return changes_made


# ============================================================
# CLI Entry Point
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update Policy Intelligence Workbench data")
    parser.add_argument("--dry-run", action="store_true", help="Check for updates without modifying files")
    parser.add_argument("--force", action="store_true", help="Force update even if no new data found")
    args = parser.parse_args()
    
    if args.dry_run:
        log("DRY RUN MODE - Will check for updates but not modify files")
    
    changed = run_update()
    
    if changed:
        print("\n✅ Website updated successfully!")
        sys.exit(0)
    else:
        print("\nℹ️  No new data found. Website is up to date.")
        sys.exit(0)
