#!/usr/bin/env python3
r"""v5_6_probe_source.py — PC 端探测单个源的站点可达性 + HTML 结构

安全规范：禁止输出源名称/URL/cookie内容，全部用代号(源[idx]/站点[X])。
仅输出：状态码、HTML长度、关键技术字段（选择器/容器名）。
"""
import json
import re
import sys
import urllib.request
import urllib.error
import ssl
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 关闭SSL验证（仅探测）
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Linux; Android 12; SM-G9910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"


def probe_url(url, label, timeout=15):
    """探测单个URL，返回技术摘要（脱敏）"""
    print(f"\n[PROBE] label={label}")
    print(f"  url_len={len(url)} url_host={url.split('//')[1].split('/')[0] if '//' in url else 'N/A'}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        code = resp.getcode()
        final_url = resp.geturl()
        body = resp.read()
        body_text = body.decode('utf-8', errors='ignore')
        # 重定向检测
        redirected = final_url != url
        redir_host = final_url.split('//')[1].split('/')[0] if '//' in final_url else ''
        print(f"  status={code} html_len={len(body)} redirected={redirected} final_host={redir_host}")
        return {'ok': True, 'code': code, 'html': body_text, 'final_url': final_url, 'redirected': redirected}
    except urllib.error.HTTPError as e:
        print(f"  HTTPError={e.code} reason={e.reason}")
        try:
            body = e.read().decode('utf-8', errors='ignore')
            return {'ok': False, 'code': e.code, 'html': body, 'final_url': url, 'redirected': False}
        except Exception:
            return {'ok': False, 'code': e.code, 'html': '', 'final_url': url, 'redirected': False}
    except Exception as e:
        print(f"  Exception={type(e).__name__}: {e}")
        return {'ok': False, 'code': -1, 'html': '', 'final_url': url, 'redirected': False}


def analyze_html_structure(html, label):
    """分析HTML结构，输出技术摘要（脱敏）"""
    if not html:
        print(f"  [ANALYZE] {label}: empty html")
        return
    print(f"  [ANALYZE] {label}: html_len={len(html)}")
    # 检测常见特征
    has_cf = 'Just a moment' in html or 'cf-challenge' in html or 'challenges.cloudflare.com' in html
    has_login_form = bool(re.search(r'<input[^>]*type=["\']password', html))
    has_container_li = bool(re.search(r'<div[^>]*class="[^"]*container', html)) and '<li' in html
    has_stui_vodlist = 'stui-vodlist' in html
    has_myui_vodlist = 'myui-vodlist' in html
    has_mac_plus = 'MacPlayer' in html or 'player_aaaa' in html
    has_cms_pattern = 'vod-detail' in html or 'vodinfo' in html or 'module-vod' in html
    title_match = re.search(r'<title>([^<]+)</title>', html)
    title_text = title_match.group(1).strip()[:60] if title_match else ''
    print(f"    cf_shield={has_cf} login_form={has_login_form} container_li={has_container_li}")
    print(f"    stui_vodlist={has_stui_vodlist} myui_vodlist={has_myui_vodlist} mac_player={has_mac_plus} cms_pattern={has_cms_pattern}")
    print(f"    title_text_len={len(title_text)} title_preview={title_text[:30]}")
    # 检测列表项容器（常见CMS模板）
    patterns = [
        (r'class="[^"]*stui-vodlist__item', 'stui_vodlist_item'),
        (r'class="[^"]*myui-vodlist__item', 'myui_vodlist_item'),
        (r'class="[^"]*module-vodlist[^"]*"', 'module_vodlist'),
        (r'class="[^"]*vodlist[^"]*"', 'vodlist'),
        (r'class="[^"]*list-item[^"]*"', 'list_item'),
        (r'class="[^"]*movie-item[^"]*"', 'movie_item'),
        (r'class="[^"]*video-item[^"]*"', 'video_item'),
        (r'<ul[^>]*class="[^"]*stui-vodlist', 'ul_stui_vodlist'),
        (r'<ul[^>]*class="[^"]*myui-vodlist', 'ul_myui_vodlist'),
    ]
    found_patterns = []
    for pat, name in patterns:
        m = re.search(pat, html)
        if m:
            found_patterns.append(name)
            print(f"    matched_pattern: {name} (sample: {m.group(0)[:80]})")
    if not found_patterns:
        print(f"    no_cms_pattern_matched")
    # 检测 <li> 数量
    li_count = len(re.findall(r'<li\b', html))
    a_count = len(re.findall(r'<a\b[^>]*href=', html))
    img_count = len(re.findall(r'<img\b', html))
    print(f"    li_count={li_count} a_count={a_count} img_count={img_count}")


# === 主流程 ===
print("=" * 80)
print("[TASK] 探测3个失败源站点可达性")
print("=" * 80)

# 加载3个源配置（不输出敏感内容）
targets_dir = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_targets')
results_summary = []

for fname, alias, fail_type in [
    ('src_1_list_empty.json', 'A', 'list_empty'),
    ('src_2_content_parse_failed.json', 'B', 'content_parse_failed'),
    ('src_3_search_malformed_url.json', 'C', 'search_malformed_url'),
]:
    src_path = targets_dir / fname
    if not src_path.exists():
        print(f"\n[SKIP] {alias}: {src_path} not found")
        continue
    with open(src_path, 'r', encoding='utf-8') as f:
        src = json.load(f)

    print("\n" + "=" * 80)
    print(f"[SOURCE] alias=源[{alias}] fail_type={fail_type}")
    print(f"  type={src.get('type')} enabled={src.get('enabled')} lastHost={src.get('lastHost')}")
    print(f"  ruleArticles={src.get('ruleArticles')!r}")
    print(f"  ruleTitle={src.get('ruleTitle')!r}")
    print(f"  ruleImage={src.get('ruleImage')!r}")
    print(f"  rulePubDate={src.get('rulePubDate')!r}")

    source_url = src.get('sourceUrl', '')
    sort_url = src.get('sortUrl', '') or ''
    search_url = src.get('searchUrl', '') or ''

    # 探测 sourceUrl
    r1 = probe_url(source_url, f'src_{alias}_source_url')

    # 如果 sortUrl 是 JS（@js:开头），尝试解析出第一个分类URL
    sort_url_sample = ''
    if sort_url.startswith('@js:'):
        # 提取 https://xxx.html 这种URL
        urls = re.findall(r'https?://[^\s\'"\\]+\.html', sort_url)
        if urls:
            sort_url_sample = urls[0]
    elif sort_url and not sort_url.startswith('@'):
        # 解析第一个分类URL
        lines = sort_url.split('\n')
        for line in lines:
            if '::' in line:
                sort_url_sample = line.split('::', 1)[1].strip()
                # 如果是相对路径，拼接source_url域名
                if sort_url_sample.startswith('/'):
                    host_match = re.match(r'(https?://[^/]+)', source_url)
                    if host_match:
                        sort_url_sample = host_match.group(1) + sort_url_sample
                break

    if sort_url_sample:
        r2 = probe_url(sort_url_sample, f'src_{alias}_sort_url_sample')
        if r2['ok']:
            analyze_html_structure(r2['html'], f'src_{alias}_sort_html')

    # 如果 searchUrl 是模板（含 {{key}}），替换为测试关键词
    search_url_sample = ''
    if search_url and not search_url.startswith('@'):
        if '{{key}}' in search_url:
            search_url_sample = search_url.replace('{{key}}', 'test').replace('{{page}}', '1')
    elif search_url.startswith('@js:'):
        urls = re.findall(r'https?://[^\s\'"\\]+\.html', search_url)
        if urls:
            search_url_sample = urls[0].replace('{{key}}', 'test').replace('{{page}}', '1')

    if search_url_sample:
        r3 = probe_url(search_url_sample, f'src_{alias}_search_url_sample')

    results_summary.append({
        'alias': alias,
        'fail_type': fail_type,
        'source_url_ok': r1['ok'],
        'source_url_code': r1['code'],
        'sort_url_sample': sort_url_sample[:80] if sort_url_sample else '',
        'sort_url_ok': r2['ok'] if sort_url_sample else None,
        'sort_url_code': r2['code'] if sort_url_sample else None,
        'search_url_sample': search_url_sample[:80] if search_url_sample else '',
        'search_url_ok': r3['ok'] if search_url_sample else None,
        'search_url_code': r3['code'] if search_url_sample else None,
    })

# 保存技术摘要
out = targets_dir / 'probe_summary.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(results_summary, f, ensure_ascii=False, indent=2)
print(f"\n[DONE] summary saved: {out}")
print("\n[SUMMARY]")
for r in results_summary:
    print(f"  源[{r['alias']}] ({r['fail_type']}): "
          f"src_url={r['source_url_code']} sort_url={r['sort_url_code']} search_url={r['search_url_code']}")
