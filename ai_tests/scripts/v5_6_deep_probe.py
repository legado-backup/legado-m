#!/usr/bin/env python3
r"""v5_6_deep_probe.py — 深度探测源站点，保存HTML原文供分析

安全规范：禁止输出源名称/URL/cookie，全部用代号。
"""
import json
import re
import sys
import urllib.request
import urllib.error
import ssl
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Linux; Android 12; SM-G9910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"

OUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_targets')


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        return resp.getcode(), resp.read().decode('utf-8', errors='ignore'), resp.geturl(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', errors='ignore')
        except Exception:
            body = ''
        return e.code, body, url, {}
    except Exception as e:
        return -1, '', url, {'error': str(e)}


def save_html(alias, label, url, code, html, final_url, headers):
    fname = f'src_{alias}_{label}.html'
    path = OUT_DIR / fname
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'<!-- url: {url} -->\n')
        f.write(f'<!-- code: {code} final: {final_url} -->\n')
        f.write(f'<!-- headers: {dict(headers)} -->\n')
        f.write(html)
    print(f"  saved: {path} (len={len(html)})")


# === 源[A] list_empty ===
print("\n" + "=" * 80)
print("[A] list_empty source deep probe")
print("=" * 80)
with open(OUT_DIR / 'src_1_list_empty.json', 'r', encoding='utf-8') as f:
    src_a = json.load(f)
url_a = src_a['sourceUrl']
code, html, final_url, headers = fetch(url_a)
print(f"source_url: code={code} html_len={len(html)} final_host={final_url.split('//')[1].split('/')[0] if '//' in final_url else 'N/A'}")
save_html('A', 'source_url', url_a, code, html, final_url, headers)
# 输出关键技术字段（脱敏）
print(f"  has_redirect_meta={bool(re.search(r'<meta[^>]*http-equiv=.refresh', html, re.I))}")
print(f"  has_js_redirect={bool(re.search(r'location\.href|window\.location|location\.replace', html))}")
print(f"  has_cf_challenge={'Just a moment' in html or 'cf-challenge' in html}")
# 提取跳转URL（如果有）
redirect_patterns = [
    r'location\.href\s*=\s*["\']([^"\']+)["\']',
    r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
    r'<meta[^>]*url=([^"\'>\s]+)',
    r'document\.location\s*=\s*["\']([^"\']+)["\']',
]
for pat in redirect_patterns:
    m = re.search(pat, html)
    if m:
        target = m.group(1)
        # 只输出host不输出完整url
        host = target.split('//')[1].split('/')[0] if '//' in target else target[:30]
        print(f"  redirect_target_host={host}")
        # 跟随跳转
        if target.startswith('http'):
            print(f"  [FOLLOW] redirect target")
            code2, html2, final_url2, headers2 = fetch(target)
            print(f"    redirect_code={code2} html_len={len(html2)}")
            save_html('A', 'redirect_target', target, code2, html2, final_url2, headers2)
            # 看真实HTML的列表容器
            li_count = len(re.findall(r'<li\b', html2))
            container_match = re.search(r'<(?:div|ul|section)[^>]*class="[^"]*container[^"]*"', html2)
            print(f"    li_count={li_count} has_container_div={bool(container_match)}")
            if container_match:
                print(f"    container_sample={container_match.group(0)[:100]}")
        break

# === 源[B] content_parse_failed ===
print("\n" + "=" * 80)
print("[B] content_parse_failed source deep probe")
print("=" * 80)
with open(OUT_DIR / 'src_2_content_parse_failed.json', 'r', encoding='utf-8') as f:
    src_b = json.load(f)
url_b = src_b['sourceUrl']
code, html, final_url, headers = fetch(url_b)
print(f"source_url: code={code} html_len={len(html)} final_host={final_url.split('//')[1].split('/')[0] if '//' in final_url else 'N/A'}")
save_html('B', 'source_url', url_b, code, html, final_url, headers)
# 输出关键技术字段（脱敏）
print(f"  has_cf_challenge={'Just a moment' in html or 'cf-challenge' in html or 'cf-mitigated' in html.lower()}")
_login_pat = re.compile(r'<input[^>]*type=["\']password')
print(f"  has_login_form={bool(_login_pat.search(html))}")
print(f"  has_robot_check={'captcha' in html.lower() or 'robot' in html.lower()}")
print(f"  has_js_rendered={'<noscript' in html and len(html) < 5000}")
# 看是否有真实分类URL在HTML中
sort_url_patterns = re.findall(r'href=["\']([^"\']*(?:thread|forum|fid)=\d+[^"\']*)["\']', html)
print(f"  sort_url_candidates={len(sort_url_patterns)}")
if sort_url_candidates := sort_url_patterns[:3]:
    for u in sort_url_candidates:
        host = u.split('//')[1].split('/')[0] if '//' in u else u[:50]
        print(f"    candidate_host_path={host}")

# 用 sortUrl 第一个URL继续探测
sort_url_raw = src_b.get('sortUrl', '')
print(f"\n  sortUrl_raw_len={len(sort_url_raw)} sortUrl_starts={sort_url_raw[:50]!r}")
if sort_url_raw and not sort_url_raw.startswith('@'):
    lines = [l for l in sort_url_raw.split('\n') if '::' in l]
    if lines:
        first_line = lines[0]
        sort_path = first_line.split('::', 1)[1].strip()
        # 拼接host
        host_match = re.match(r'(https?://[^/]+)', url_b)
        if host_match and sort_path.startswith('/'):
            full_sort_url = host_match.group(1) + sort_path
            print(f"  sort_first_url_host={full_sort_url.split('//')[1].split('/')[0]}")
            code2, html2, final_url2, headers2 = fetch(full_sort_url)
            print(f"  sort_url_fetch: code={code2} html_len={len(html2)}")
            save_html('B', 'sort_first', full_sort_url, code2, html2, final_url2, headers2)
            # 分析 sort_url 的 HTML
            tr3_count = len(re.findall(r'<tr[^>]*class="[^"]*tr3', html2))
            a_count = len(re.findall(r'<a\b[^>]*href=', html2))
            print(f"    tr3_count={tr3_count} a_count={a_count}")
            # 找出真正的列表项容器
            for pat_name, pat in [
                ('tr3', r'<tr[^>]*class="[^"]*tr3[^"]*"'),
                ('topic', r'class="[^"]*topic'),
                ('post', r'class="[^"]*post'),
                ('t_one', r'class="[^"]*t_one'),
                ('list_item', r'class="[^"]*list-item'),
            ]:
                m = re.search(pat, html2)
                if m:
                    print(f"    found: {pat_name} -> {m.group(0)[:80]}")

# === 源[C] search_malformed_url ===
print("\n" + "=" * 80)
print("[C] search_malformed_url source deep probe")
print("=" * 80)
with open(OUT_DIR / 'src_3_search_malformed_url.json', 'r', encoding='utf-8') as f:
    src_c = json.load(f)
url_c = src_c['sourceUrl']
print(f"  sourceUrl_raw={url_c!r}")
# 先尝试 http
if url_c.startswith('https'):
    url_c_http = 'http' + url_c[5:]
    print(f"  try_http_first")
    code, html, final_url, headers = fetch(url_c_http)
    print(f"  http_code={code} html_len={len(html)}")
    if code == 200:
        save_html('C', 'source_url_http', url_c_http, code, html, final_url, headers)
        # 检测是否是SSL提示页/HTTPS跳转
        if 'https' in html.lower() and len(html) < 3000:
            # 用 https 重试
            code2, html2, final_url2, headers2 = fetch(url_c)
            print(f"  https_retry_code={code2} html_len={len(html2)}")
            save_html('C', 'source_url_https', url_c, code2, html2, final_url2, headers2)

# 解析 sortUrl（可能是 JS）
sort_url_raw = src_c.get('sortUrl', '') or ''
print(f"\n  sortUrl_raw_len={len(sort_url_raw)} sortUrl_starts={sort_url_raw[:80]!r}")
# 提取URL（更鲁棒：所有 https?:// 字符串）
all_urls = re.findall(r'https?://[^\s\'"\\<>]+', sort_url_raw)
print(f"  sortUrl_url_count={len(all_urls)}")
for i, u in enumerate(all_urls[:5]):
    host = u.split('//')[1].split('/')[0] if '//' in u else u
    print(f"    sort_url[{i}] host={host} path_starts=/{'/'.join(u.split('/')[3:5])}")

# 解析 searchUrl
search_url_raw = src_c.get('searchUrl', '') or ''
print(f"\n  searchUrl_raw_len={len(search_url_raw)} searchUrl_starts={search_url_raw[:80]!r}")
all_search_urls = re.findall(r'https?://[^\s\'"\\<>]+', search_url_raw)
print(f"  searchUrl_url_count={len(all_search_urls)}")
for i, u in enumerate(all_search_urls[:5]):
    host = u.split('//')[1].split('/')[0] if '//' in u else u
    print(f"    search_url[{i}] host={host} path_starts=/{'/'.join(u.split('/')[3:5])}")

print("\n[DONE]")
