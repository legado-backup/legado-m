"""
Legado Source Creator - deep-analyze-js
用途: 深度JS/HTML分析，自动检测网页重复结构、提取书籍列表元素、分析CSS选择器匹配
依赖: beautifulsoup4
使用: python scripts/deep-analyze-js.py
输入: 网站URL(硬编码在脚本中)
输出: temp/*.html(搜索页面快照), 控制台输出选择器匹配结果
注意: SSL证书验证已关闭
"""
import json
import ssl
import urllib.request
import urllib.parse
import time
import re
import sys

try:
    from bs4 import BeautifulSoup
except ImportError:
    from subprocess import check_call
    check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "-q"])
    from bs4 import BeautifulSoup

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"

def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace"), resp.status
    except Exception as e:
        return str(e), None

def deep_analyze_html(html, source_name, old_rules):
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "title": soup.title.string if soup.title else "N/A",
        "old_rules_test": {},
        "structure": {},
        "proposed_rules": {},
        "sample_books": [],
    }

    old_bookList = old_rules.get("bookList", "")
    if old_bookList:
        clean_selector = old_bookList.split("@")[0] if "@" in old_bookList else old_bookList
        clean_selector = clean_selector.replace("!0", "").strip()
        try:
            matched = soup.select(clean_selector)
            result["old_rules_test"]["bookList"] = {
                "selector": clean_selector,
                "match_count": len(matched),
                "works": len(matched) > 0
            }
        except Exception as e:
            result["old_rules_test"]["bookList"] = {"selector": clean_selector, "error": str(e)}

    body = soup.body
    if not body:
        return result

    def find_repeating_patterns(tag, depth=0, max_depth=5):
        if depth > max_depth:
            return []
        patterns = []
        children = tag.find_all(recursive=False)
        child_tags = {}
        for c in children:
            key = c.name + "|" + " ".join(c.get("class", []))
            if key not in child_tags:
                child_tags[key] = []
            child_tags[key].append(c)

        for key, elems in child_tags.items():
            if len(elems) >= 3:
                tag_name, classes = key.split("|", 1)
                patterns.append({
                    "selector": f"{tag_name}.{'.'.join(classes.split())}" if classes else tag_name,
                    "count": len(elems),
                    "depth": depth,
                    "parent": tag.name + "." + ".".join(tag.get("class", [])),
                })
            for e in elems:
                patterns.extend(find_repeating_patterns(e, depth + 1, max_depth))
        return patterns

    patterns = find_repeating_patterns(body)
    patterns.sort(key=lambda x: (-x["count"], x["depth"]))

    book_like_patterns = [p for p in patterns if any(
        kw in p["selector"].lower() or kw in p["parent"].lower()
        for kw in ["book", "list", "item", "novel", "result", "search", "grid", "row", "card", "li"]
    )]

    result["structure"]["repeating_patterns"] = (book_like_patterns or patterns)[:10]

    best_pattern = None
    if book_like_patterns:
        best_pattern = book_like_patterns[0]
    elif patterns:
        for p in patterns:
            if p["count"] >= 3 and p["depth"] <= 3:
                best_pattern = p
                break

    if best_pattern:
        selector = best_pattern["selector"]
        if best_pattern["depth"] > 0 and best_pattern["parent"]:
            parent_sel = best_pattern["parent"].replace(".", ".")
            full_selector = f"{parent_sel} > {selector}"
        else:
            full_selector = selector

        try:
            items = soup.select(full_selector)
        except:
            try:
                items = soup.select(selector)
                full_selector = selector
            except:
                items = []

        if not items:
            try:
                items = soup.select(selector)
                full_selector = selector
            except:
                items = []

        if items and len(items) >= 2:
            result["structure"]["best_selector"] = full_selector
            result["structure"]["best_count"] = len(items)

            for i, item in enumerate(items[:5]):
                book = {"index": i}

                links = item.find_all("a", recursive=True)
                book["all_links"] = []
                for a in links:
                    book["all_links"].append({
                        "text": a.get_text(strip=True)[:80],
                        "href": a.get("href", ""),
                        "title": a.get("title", ""),
                        "class": " ".join(a.get("class", [])),
                    })

                imgs = item.find_all("img", recursive=True)
                book["all_images"] = []
                for img in imgs:
                    book["all_images"].append({
                        "src": img.get("src", ""),
                        "data-src": img.get("data-src", ""),
                        "data-original": img.get("data-original", ""),
                        "alt": img.get("alt", ""),
                    })

                headings = item.find_all(["h1", "h2", "h3", "h4"], recursive=True)
                book["headings"] = []
                for h in headings:
                    book["headings"].append({
                        "tag": h.name,
                        "text": h.get_text(strip=True)[:80],
                        "class": " ".join(h.get("class", [])),
                    })

                spans = item.find_all(["span", "em", "b", "strong", "i"], recursive=True)
                book["spans"] = []
                for s in spans:
                    txt = s.get_text(strip=True)[:60]
                    if txt:
                        book["spans"].append({
                            "tag": s.name,
                            "text": txt,
                            "class": " ".join(s.get("class", [])),
                        })

                paras = item.find_all("p", recursive=True)
                book["paragraphs"] = []
                for p in paras:
                    txt = p.get_text(strip=True)[:100]
                    if txt:
                        book["paragraphs"].append({
                            "text": txt,
                            "class": " ".join(p.get("class", [])),
                        })

                book["html_snippet"] = str(item)[:800]
                book["text_content"] = item.get_text(strip=True, separator=" | ")[:300]

                result["sample_books"].append(book)

    return result

def analyze_ixdzs8():
    print("\n" + "="*60, flush=True)
    print("深度分析: 爱下电子系列 (ixdzs8.com)", flush=True)

    base_url = "https://ixdzs8.com"
    search_url = "https://ixdzs8.com/bsearch?q=" + urllib.parse.quote("斗罗大陆")

    html, status = fetch_url(search_url)
    if status is None:
        print(f"  ❌ 搜索请求失败: {html}", flush=True)
        return None

    print(f"  搜索响应: {status}, HTML长度: {len(html)}", flush=True)

    soup = BeautifulSoup(html, "html.parser")

    with open("temp/ixdzs8_search.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML已保存到 temp/ixdzs8_search.html", flush=True)

    for selector in [".u-list", ".u-list li", ".search", ".search li", "ul li", ".list", ".book-list"]:
        try:
            matched = soup.select(selector)
            print(f"  选择器 '{selector}': {len(matched)} 个匹配", flush=True)
        except:
            print(f"  选择器 '{selector}': 语法错误", flush=True)

    ul_tags = soup.find_all("ul")
    for ul in ul_tags:
        cls = " ".join(ul.get("class", []))
        li_count = len(ul.find_all("li", recursive=False))
        print(f"  <ul class='{cls}'> 含 {li_count} 个直接<li>", flush=True)
        if li_count > 0:
            first_li = ul.find("li", recursive=False)
            print(f"    第一个<li>: {str(first_li)[:300]}", flush=True)

    div_list_items = soup.find_all("div", class_=re.compile(r"list|item|book|result|search"))
    for div in div_list_items[:5]:
        cls = " ".join(div.get("class", []))
        children = div.find_all(recursive=False)
        print(f"  <div class='{cls}'> 含 {len(children)} 个直接子元素", flush=True)
        if children:
            print(f"    第一个子元素: {str(children[0])[:300]}", flush=True)

    return html

def analyze_kxwx():
    print("\n" + "="*60, flush=True)
    print("深度分析: 开心文学网 (kxwx.org)", flush=True)

    base_url = "https://www.kxwx.org"
    search_url = base_url + "/search/" + urllib.parse.quote("斗罗大陆") + ".html"

    html, status = fetch_url(search_url)
    if status is None:
        print(f"  ❌ 搜索请求失败: {html}", flush=True)
        return None

    print(f"  搜索响应: {status}, HTML长度: {len(html)}", flush=True)

    soup = BeautifulSoup(html, "html.parser")

    with open("temp/kxwx_search.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML已保存到 temp/kxwx_search.html", flush=True)

    for selector in [".grid", ".grid tr", "table tr", ".channel-nav-list", ".book-list", ".list", "ul li"]:
        try:
            matched = soup.select(selector)
            print(f"  选择器 '{selector}': {len(matched)} 个匹配", flush=True)
        except:
            print(f"  选择器 '{selector}': 语法错误", flush=True)

    tables = soup.find_all("table")
    for t in tables:
        cls = " ".join(t.get("class", []))
        rows = t.find_all("tr")
        print(f"  <table class='{cls}'> 含 {len(rows)} 行", flush=True)
        if rows:
            for i, row in enumerate(rows[:3]):
                tds = row.find_all(["td", "th"])
                texts = [td.get_text(strip=True)[:30] for td in tds]
                print(f"    行{i}: {texts}", flush=True)

    div_items = soup.find_all("div", class_=re.compile(r"list|item|book|result|grid|channel"))
    for div in div_items[:5]:
        cls = " ".join(div.get("class", []))
        children = div.find_all(recursive=False)
        print(f"  <div class='{cls}'> 含 {len(children)} 个直接子元素", flush=True)
        if children:
            print(f"    第一个子元素: {str(children[0])[:300]}", flush=True)

    return html

def analyze_shubl():
    print("\n" + "="*60, flush=True)
    print("深度分析: 书耽网站 (m.shubl.com)", flush=True)

    base_url = "http://m.shubl.com"
    search_url = base_url + "/index/search_book?key=" + urllib.parse.quote("斗罗大陆")

    html, status = fetch_url(search_url)
    if status is None:
        print(f"  ❌ 搜索请求失败: {html}", flush=True)
        return None

    print(f"  搜索响应: {status}, HTML长度: {len(html)}", flush=True)

    soup = BeautifulSoup(html, "html.parser")

    with open("temp/shubl_search.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML已保存到 temp/shubl_search.html", flush=True)

    for selector in [".book-list", ".book-list li", "ul li", ".list li", ".search-wrap", ".search-wrap li"]:
        try:
            matched = soup.select(selector)
            print(f"  选择器 '{selector}': {len(matched)} 个匹配", flush=True)
        except:
            print(f"  选择器 '{selector}': 语法错误", flush=True)

    ul_tags = soup.find_all("ul")
    for ul in ul_tags:
        cls = " ".join(ul.get("class", []))
        li_count = len(ul.find_all("li", recursive=False))
        print(f"  <ul class='{cls}'> 含 {li_count} 个直接<li>", flush=True)
        if li_count > 0:
            first_li = ul.find("li", recursive=False)
            print(f"    第一个<li>: {str(first_li)[:500]}", flush=True)

    return html

def analyze_bsxiaoshuo():
    print("\n" + "="*60, flush=True)
    print("深度分析: 笔尚小说 (bsxiaoshuo.com)", flush=True)

    base_url = "https://www.bsxiaoshuo.com"
    search_url = base_url + "/s.php?sid=3&k=" + urllib.parse.quote("斗罗大陆")

    html, status = fetch_url(search_url)
    if status is None:
        print(f"  ❌ 搜索请求失败: {html}", flush=True)
        return None

    print(f"  搜索响应: {status}, HTML长度: {len(html)}", flush=True)

    soup = BeautifulSoup(html, "html.parser")

    with open("temp/bsxiaoshuo_search.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML已保存到 temp/bsxiaoshuo_search.html", flush=True)

    for selector in ["#j", "#j li", ".search", ".search li", "ul li", ".list", ".book-list", ".result"]:
        try:
            matched = soup.select(selector)
            print(f"  选择器 '{selector}': {len(matched)} 个匹配", flush=True)
        except:
            print(f"  选择器 '{selector}': 语法错误", flush=True)

    ul_tags = soup.find_all("ul")
    for ul in ul_tags:
        cls = " ".join(ul.get("class", []))
        uid = ul.get("id", "")
        li_count = len(ul.find_all("li", recursive=False))
        print(f"  <ul class='{cls}' id='{uid}'> 含 {li_count} 个直接<li>", flush=True)
        if li_count > 0:
            first_li = ul.find("li", recursive=False)
            print(f"    第一个<li>: {str(first_li)[:500]}", flush=True)

    div_items = soup.find_all("div", class_=re.compile(r"list|item|book|result|search"))
    for div in div_items[:5]:
        cls = " ".join(div.get("class", []))
        children = div.find_all(recursive=False)
        print(f"  <div class='{cls}'> 含 {len(children)} 个直接子元素", flush=True)
        if children:
            print(f"    第一个子元素: {str(children[0])[:500]}", flush=True)

    return html

def analyze_url(url, source_name="custom"):
    """4.3.6: 通用分析函数 — 分析任意URL的HTML结构和选择器匹配。
    提取为 CLI 工具，而非硬编码4个网站。
    """
    html, status = fetch_url(url)
    if status is None:
        print(f"[错误] 无法获取 {url}: {html}")
        return
    print(f"[分析] {url} (HTTP {status}, {len(html)} bytes)")
    # 保存HTML快照
    safe_name = re.sub(r'[^\w]', '_', source_name)[:30]
    snapshot_path = f"temp/{safe_name}_snapshot.html"
    os.makedirs("temp", exist_ok=True)
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[快照] 已保存: {snapshot_path}")
    print(f"[建议] 用浏览器打开快照，F12分析HTML结构，更新CSS选择器")


def main():
    # 4.3.6: 支持命令行参数，不再硬编码4个网站
    import argparse
    parser = argparse.ArgumentParser(description='深度JS/HTML分析工具')
    parser.add_argument('--url', help='分析指定URL（通用模式）')
    parser.add_argument('--name', default='custom', help='源名称（用于快照文件名）')
    parser.add_argument('--all', action='store_true', help='运行所有硬编码分析（旧模式）')
    args = parser.parse_args()

    if args.url:
        analyze_url(args.url, args.name)
    elif args.all:
        analyze_ixdzs8()
        time.sleep(0.5)
        analyze_kxwx()
        time.sleep(0.5)
        analyze_shubl()
        time.sleep(0.5)
        analyze_bsxiaoshuo()
        print("\n\n深度分析完成！请查看保存的HTML文件进行精确修复。", flush=True)
    else:
        print("用法: deep-analyze-js.py --url <URL> [--name <名称>]")
        print("      deep-analyze-js.py --all  (运行硬编码分析)")
        print("\n4.3.6: 已从硬编码4个网站改为通用CLI工具")

if __name__ == "__main__":
    main()
