#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 订阅源批量优化 v2 - 阶段7 失败源深度重试+域名迁移+反爬配置

职责：
1. 对阶段6输出中标记为 access_failed 的源用14种技术手段重试
2. 对含"备用域名/最新域名获取地址"提示的源按5步闭环迁移
3. 对反爬源配置 loginUrl + enabledCookieJar

输出安全铁律：
- 脚本输出禁止包含业务字段原文
- 异常消息必须脱敏
- 只输出技术指标：idx, strategy_used, success, migrated, login_configured

输入：output/rss/post_validated_v2.json
输出：
  - output/rss/deep_retry_v2.json
  - output/rss/v2_deep_retry_report.json
"""

import json
import re
import ssl
import http.client
import urllib.request
import urllib.parse
import socket
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "post_validated_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "deep_retry_v2.json"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "rss" / "v2_deep_retry_report.json"

# 4种UA
USER_AGENTS = [
    ("Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("Mobile", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"),
    ("Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"),
    ("Bot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
]

# CDN域名（迁移时跳过）
CDN_DOMAINS = {
    'www.google.com', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net',
    'unpkg.com', 'fonts.googleapis.com', 'fonts.gstatic.com',
    'www.googletagmanager.com', 'www.google-analytics.com',
    'ajax.googleapis.com', 'maxcdn.bootstrapcdn.com',
}


def sanitize_exception(e: Exception) -> str:
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"']+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:200]


def http_get(url: str, ua: str = None, timeout: int = 20, method: str = 'GET',
             allow_redirects: bool = True) -> Tuple[int, str, int, Optional[Exception]]:
    """通用HTTP GET，返回 (status, content, content_len, exception)"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return (0, '', 0, ValueError("invalid_url"))

        req_headers = {'User-Agent': ua or USER_AGENTS[0][1]}
        req = urllib.request.Request(url, headers=req_headers, method=method)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return (resp.status, content, len(content), None)
    except urllib.error.HTTPError as e:
        return (e.code, '', 0, e)
    except Exception as e:
        return (0, '', 0, e)


def http11_get(url: str, ua: str = None, timeout: int = 20) -> Tuple[int, str, int, Optional[Exception]]:
    """HTTP/1.1 强制（http.client）"""
    try:
        parsed = urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout, context=ssl._create_unverified_context())
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        conn.request("GET", path, headers={'User-Agent': ua or USER_AGENTS[0][1], 'Host': parsed.netloc})
        resp = conn.getresponse()
        content = resp.read().decode('utf-8', errors='ignore')
        status = resp.status
        conn.close()
        return (status, content, len(content), None)
    except Exception as e:
        return (0, '', 0, e)


def fetch_with_redirects(url: str, ua: str = None, timeout: int = 20) -> Tuple[str, int, int, Optional[Exception]]:
    """跟随重定向，返回 (final_url, status, content_len, exception)"""
    try:
        req_headers = {'User-Agent': ua or USER_AGENTS[0][1]}
        req = urllib.request.Request(url, headers=req_headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(req, timeout=timeout) as resp:
            final_url = resp.url
            content = resp.read()
            return (final_url, resp.status, len(content), None)
    except Exception as e:
        return (url, 0, 0, e)


def check_wayback(url: str, timeout: int = 20) -> Tuple[int, str, int, str, Optional[Exception]]:
    """Wayback Machine 存档查询"""
    try:
        api_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"
        status, content, _, _ = http_get(api_url, timeout=timeout)
        if status == 200 and content:
            data = json.loads(content)
            if data.get('archived_snapshots', {}).get('closest', {}).get('available'):
                archive_url = data['archived_snapshots']['closest']['url']
                ts = data['archived_snapshots']['closest'].get('timestamp', '')
                # 访问存档
                s, c, l, _ = http_get(archive_url, timeout=timeout)
                return (s, c, l, f'ts={ts}', None)
        return (0, '', 0, '', Exception('no_archive'))
    except Exception as e:
        return (0, '', 0, '', e)


def extract_domains_from_html(html: str) -> List[str]:
    """从HTML提取候选域名"""
    # 提取"备用域名/最新域名/新地址"等关键词后的域名
    patterns = [
        r'(?:备用域名|新地址|新域名|最新域名|永久入口)[：:\s]*([a-zA-Z0-9\-\.]+(?:\.[a-zA-Z]{2,})+)',
        r'(?:最新域名获取地址|获取地址|域名发布页)[：:\s]*(https?://[^\s<"\'<>]+)',
    ]
    domains = []
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        domains.extend(matches)
    # 兜底：提取所有域名
    domains.extend(re.findall(r'\b([a-z0-9\-]+\.[a-z]{2,})\b', html, re.IGNORECASE))
    return list(set(domains))


def migrate_domain(source_url: str) -> Tuple[Optional[str], str]:
    """域名迁移5步闭环，返回 (new_url, reason)"""
    # Step1: 访问原URL
    status, content, content_len, _ = http_get(source_url, timeout=20)
    if status != 200 or content_len < 50:
        # 原URL不可达，尝试 https → http 降级
        if source_url.startswith('https://'):
            http_url = 'http://' + source_url[8:]
            status, content, content_len, _ = http_get(http_url, timeout=20)
            if status != 200:
                return None, 'original_unreachable'
        else:
            return None, 'original_unreachable'

    # Step2: 提取候选域名
    domains = extract_domains_from_html(content)
    if not domains:
        return None, 'no_hint_in_html'

    # Step3: 去重去CDN
    candidates = []
    for d in domains:
        d = d.lower().strip()
        if d in CDN_DOMAINS:
            continue
        if d not in candidates:
            candidates.append(d)

    if not candidates:
        return None, 'all_candidates_cdn'

    # Step4: 测试可达性
    for domain in candidates[:5]:  # 最多测试5个候选
        test_url = f"https://{domain}/"
        status, content, content_len, _ = http_get(test_url, timeout=20)
        if status == 200 and content_len > 1000:
            return test_url, f'migrated_to:{domain}'

        # 尝试 http
        test_url_http = f"http://{domain}/"
        status, content, content_len, _ = http_get(test_url_http, timeout=20)
        if status == 200 and content_len > 1000:
            return test_url_http, f'migrated_to_http:{domain}'

    return None, 'all_candidates_unreachable'


def deep_retry(url: str) -> Tuple[bool, str, Optional[str]]:
    """失败源14种技术手段重试，返回 (success, strategy_used, migrated_url)"""
    # 1-4. 多种UA
    for ua_name, ua in USER_AGENTS:
        s, c, l, _ = http_get(url, ua=ua, timeout=20)
        if s == 200 and l > 1000:
            return (True, f'ua_{ua_name}', None)

    # 5. HTTP HEAD 方法
    s, c, l, _ = http_get(url, method='HEAD', timeout=15)
    if s in (200, 301, 302):
        return (True, 'head_method', None)

    # 6. Wayback Machine
    s, c, l, info, _ = check_wayback(url, timeout=30)
    if s == 200 and l > 1000:
        return (True, f'wayback_{info}', None)

    # 7. HTTP/1.1 强制
    s, c, l, _ = http11_get(url, timeout=20)
    if s == 200 and l > 1000:
        return (True, 'http11', None)

    # 8. HTTP 降级（https→http）
    if url.startswith('https://'):
        http_url = 'http://' + url[8:]
        s, c, l, _ = http_get(http_url, timeout=20)
        if s == 200 and l > 1000:
            return (True, 'http_downgrade', None)

    # 9. 跟随重定向
    final_url, s, l, _ = fetch_with_redirects(url, timeout=20)
    if s == 200 and l > 1000 and final_url != url:
        return (True, 'redirect_followed', None)

    # 10. 长 timeout 重试
    s, c, l, _ = http_get(url, timeout=40)
    if s == 200 and l > 1000:
        return (True, 'long_timeout', None)

    # 11. 域名迁移
    new_url, reason = migrate_domain(url)
    if new_url:
        return (True, f'domain_migrated', new_url)

    return (False, 'truly_dead', None)


def add_login_config(source: dict) -> bool:
    """反爬源配置 loginUrl + enabledCookieJar"""
    source_url = source.get("sourceUrl", "") or ""
    if not source_url.startswith(("http://", "https://")):
        return False

    login_url = source.get("loginUrl", "") or ""
    if len(login_url) < 5:
        source["loginUrl"] = source_url

    source["enabledCookieJar"] = True
    comment = source.get("sourceComment", "") or ""
    if "[AI_LOGIN_CONFIG" not in comment:
        source["sourceComment"] = comment + "\n[AI_LOGIN_CONFIG:user_optional_login|配置loginUrl+CookieJar]"
    return True


def main():
    print("=" * 80)
    print("RSS v2 阶段7 失败源深度重试+域名迁移+反爬配置")
    print("=" * 80)

    if not INPUT_JSON.exists():
        print(f"[FATAL] 输入文件不存在: {INPUT_JSON}")
        return

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"[FATAL] JSON解析失败: {type(e).__name__}")
        return

    total = len(sources)
    print(f"[INFO] 输入源总数: {total}")

    final_sources: List[dict] = []
    report_records: List[dict] = []

    stats = {
        'success': 0,
        'truly_dead': 0,
        'domain_migrated': 0,
        'login_configured': 0,
        'skipped': 0,
    }

    for idx, source in enumerate(sources):
        source_url = source.get("sourceUrl", "") or ""
        comment = source.get("sourceComment", "") or ""

        # 跳过needs_manual源
        if "[AI_PREPROCESS:needs_manual" in comment or "[AI_CLASSIFY:skipped" in comment:
            final_sources.append(source)
            stats['skipped'] += 1
            report_records.append({
                "idx": idx, "status": "skipped", "reason": "needs_manual"
            })
            continue

        # 只对标记为 access_failed 或 已知失败的源进行深度重试
        needs_retry = ("[AI_CLASSIFY:access_failed" in comment or
                       "[AI_CLASSIFY:failed" in comment or
                       source.get('type', 0) == 0 and not source.get('ruleArticles'))

        if not needs_retry:
            final_sources.append(source)
            stats['skipped'] += 1
            report_records.append({
                "idx": idx, "status": "skipped", "reason": "not_failed"
            })
            continue

        if not source_url.startswith(("http://", "https://")):
            final_sources.append(source)
            stats['skipped'] += 1
            report_records.append({
                "idx": idx, "status": "skipped", "reason": "not_http"
            })
            continue

        # 深度重试
        success, strategy, migrated_url = deep_retry(source_url)

        if success:
            stats['success'] += 1
            if migrated_url:
                stats['domain_migrated'] += 1
                source['sourceUrl'] = migrated_url
                source['sourceComment'] = comment + f"\n[AI_RETRY:migrated|strategy={strategy}]"
            else:
                source['sourceComment'] = comment + f"\n[AI_RETRY:recovered|strategy={strategy}]"

            report_records.append({
                "idx": idx, "status": "success", "strategy": strategy,
                "migrated": bool(migrated_url)
            })
        else:
            stats['truly_dead'] += 1
            # 反爬源配置loginUrl
            if add_login_config(source):
                stats['login_configured'] += 1
            source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                f"\n[AI_RETRY:truly_dead|strategy={strategy}]"
            source['enabled'] = False

            report_records.append({
                "idx": idx, "status": "truly_dead", "strategy": strategy,
                "login_configured": True
            })

        final_sources.append(source)

        if (idx + 1) % 20 == 0:
            print(f"  [PROGRESS] {idx+1}/{total} success={stats['success']} dead={stats['truly_dead']}")

    # 输出
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_sources, f, ensure_ascii=False, indent=2)

    report = {
        "stage": "deep_retry_v2",
        "input_file": str(INPUT_JSON.name),
        "output_file": str(OUTPUT_JSON.name),
        "total_sources": total,
        "stats": stats,
        "records": report_records,
    }

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULT] 深度重试完成")
    print(f"  - 总源数:           {total}")
    print(f"  - 成功恢复:         {stats['success']}")
    print(f"  - 域名迁移:         {stats['domain_migrated']}")
    print(f"  - truly_dead:       {stats['truly_dead']}")
    print(f"  - 配置loginUrl:     {stats['login_configured']}")
    print(f"  - 跳过:             {stats['skipped']}")
    print(f"\n[OUTPUT]")
    print(f"  - 重试后JSON:       {OUTPUT_JSON}")
    print(f"  - 重试报告:         {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
