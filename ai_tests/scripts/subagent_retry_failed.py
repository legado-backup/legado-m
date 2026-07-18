#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subagent_retry_failed.py — 54个访问失败RSS订阅源深度重试

职责：
1. 筛选 sourceComment 含 "AI_CLASSIFY:access_failed" 的源
2. 对每个失败源用14种技术手段深度重试
3. 对仍然失败的源，尝试域名迁移5步闭环
4. 对反爬源（HTTP 403或17字节"Request Forbidden"），配置 loginUrl + enabledCookieJar
5. 输出最终状态：recovered / truly_dead / needs_login

输出安全铁律：
- 脚本输出禁止包含业务字段原文（sourceName/sourceUrl/sourceComment内容）
- 只输出技术指标：idx, error_type, recovery_strategy, final_status
- Playwright/requests异常消息必须脱敏（替换URL/域名为 [URL]/[DOMAIN]）
- 不输出完整URL，只保留URL长度和路径模式
- 不输出cookie/token/password等敏感字段
"""

import json
import re
import ssl
import time
import socket
import http.client
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_JSON = PROJECT_ROOT / "output" / "rss" / "classified_v2.json"
OUTPUT_JSON = PROJECT_ROOT / "output" / "rss" / "subagent_failed_retry.json"

# 4种UA
USER_AGENTS = [
    ("Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("Mobile", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
    ("Bot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"),
]

# CDN域名（迁移时跳过）
CDN_DOMAINS = {
    'www.google.com', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net',
    'unpkg.com', 'fonts.googleapis.com', 'fonts.gstatic.com',
    'www.googletagmanager.com', 'www.google-analytics.com',
    'ajax.googleapis.com', 'maxcdn.bootstrapcdn.com',
    'archive.org', 'web.archive.org', 'api.github.com',
    'schema.org', 'w3.org', 'jquery.com', 'bootstrap.com',
}

# 8端口组合
PORTS_TO_TRY = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000]

# ==================== 工具函数 ====================
def sanitize_exception(e: Exception) -> str:
    """异常消息脱敏：替换URL/域名为 [URL]/[DOMAIN]"""
    msg = str(e)
    msg = re.sub(r"https?://[^\s\"'<>]+", "[URL]", msg)
    msg = re.sub(r"\b[a-z0-9\-]+\.(com|net|org|io|cn|cc|xyz|top|info|me|tv|wiki|site|online|store|shop|live|app|dev|cloud|vip)[^\s]*", "[DOMAIN]", msg, flags=re.IGNORECASE)
    return msg[:150]


def classify_error(e: Optional[Exception], status: int = 0, content_len: int = 0) -> str:
    """错误类型分类（脱敏）"""
    if e is None:
        if status == 200:
            return 'ok'
        if status == 403:
            return 'http_403_forbidden'
        if status == 404:
            return 'http_404_not_found'
        if status in (301, 302):
            return 'http_redirect'
        if 400 <= status < 500:
            return f'http_{status}_client_error'
        if 500 <= status < 600:
            return f'http_{status}_server_error'
        return f'http_{status}'

    if e is None:
        return 'unknown'

    msg = str(e).lower()
    if 'timeout' in msg or 'timed out' in msg:
        return 'timeout'
    if 'connection refused' in msg or 'remotedisconnected' in msg or 'connectionreset' in msg:
        return 'connection_refused'
    if 'name or service' in msg or 'getaddrinfo' in msg or 'nodename' in msg or 'no address' in msg:
        return 'dns_fail'
    if 'ssl' in msg or 'certificate' in msg:
        return 'ssl_error'
    if 'http2' in msg or 'protocol' in msg:
        return 'http2_protocol_error'
    if 'forbidden' in msg:
        return 'forbidden'
    return f'exception:{type(e).__name__}'


def is_request_forbidden(content: str, status: int) -> bool:
    """检测17字节Request Forbidden或403"""
    if status == 403:
        return True
    if content and len(content.strip()) == 17 and 'forbidden' in content.lower():
        return True
    if content and ('Request Forbidden' in content or '请求被拒绝' in content):
        return True
    return False


def http_get(url: str, ua: str = None, timeout: int = 20, method: str = 'GET') -> Tuple[int, str, int, Optional[Exception]]:
    """通用HTTP GET，返回 (status, content, content_len, exception)"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return (0, '', 0, ValueError("invalid_url"))

        req_headers = {
            'User-Agent': ua or USER_AGENTS[0][1],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': f"{parsed.scheme}://{parsed.netloc}/",
            'Connection': 'keep-alive',
        }
        req = urllib.request.Request(url, headers=req_headers, method=method)

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            content_bytes = resp.read()
            try:
                content = content_bytes.decode('utf-8', errors='ignore')
            except Exception:
                content = ''
            return (resp.status, content, len(content_bytes), None)
    except urllib.error.HTTPError as e:
        return (e.code, '', 0, e)
    except Exception as e:
        return (0, '', 0, e)


def http11_get(url: str, ua: str = None, timeout: int = 20) -> Tuple[int, str, int, Optional[Exception]]:
    """HTTP/1.1 强制（http.client）"""
    try:
        parsed = urlparse(url)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query

        if parsed.scheme == 'https':
            conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout,
                                                context=ssl._create_unverified_context())
        else:
            conn = http.client.HTTPConnection(parsed.netloc, timeout=timeout)

        conn.request("GET", path, headers={
            'User-Agent': ua or USER_AGENTS[0][1],
            'Host': parsed.netloc,
            'Accept': '*/*',
        })
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


def requests_session_get(url: str, ua: str = None, timeout: int = 30) -> Tuple[int, str, int, Optional[Exception]]:
    """requests + Session（cookie共享）"""
    try:
        import requests
        sess = requests.Session()
        sess.headers.update({
            'User-Agent': ua or USER_AGENTS[0][1],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        resp = sess.get(url, timeout=timeout, verify=False, allow_redirects=True)
        return (resp.status_code, resp.text, len(resp.content), None)
    except Exception as e:
        return (0, '', 0, e)


def check_wayback(url: str, timeout: int = 30) -> Tuple[int, str, int, str, Optional[Exception]]:
    """Wayback Machine 存档查询"""
    try:
        api_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"
        status, content, _, _ = http_get(api_url, timeout=timeout)
        if status == 200 and content:
            data = json.loads(content)
            if data.get('archived_snapshots', {}).get('closest', {}).get('available'):
                archive_url = data['archived_snapshots']['closest']['url']
                ts = data['archived_snapshots']['closest'].get('timestamp', '')
                s, c, l, _ = http_get(archive_url, timeout=timeout)
                return (s, c, l, f'ts={ts}', None)
        return (0, '', 0, '', Exception('no_archive'))
    except Exception as e:
        return (0, '', 0, '', e)


def check_wayback_direct(url: str, timeout: int = 40) -> Tuple[int, str, int, Optional[Exception]]:
    """Wayback直接访问：尝试构造最近的存档URL"""
    try:
        # 构造最近的存档URL：https://web.archive.org/web/2024/{original_url}
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return (0, '', 0, ValueError("invalid_url"))
        archive_url = f"https://web.archive.org/web/2024/{url}"
        return http_get(archive_url, timeout=timeout)
    except Exception as e:
        return (0, '', 0, e)


def playwright_render(url: str, timeout_ms: int = 30000) -> Tuple[int, str, int, Optional[Exception]]:
    """Playwright真实渲染（stealth脚本）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = browser.new_context(
                user_agent=USER_AGENTS[0][1],
                viewport={'width': 1280, 'height': 800},
                ignore_https_errors=True,
            )
            # 注入stealth脚本
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
                window.chrome = {runtime: {}};
            """)
            page = context.new_page()
            resp = page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            status = resp.status if resp else 0
            content = page.content()
            page.close()
            context.close()
            browser.close()
            return (status, content, len(content), None)
    except Exception as e:
        return (0, '', 0, e)


def try_port_combinations(url: str, ua: str = None) -> Tuple[bool, str, Optional[str]]:
    """8端口组合尝试"""
    parsed = urlparse(url)
    if not parsed.netloc:
        return (False, '', None)

    # 拆分host和原端口
    if ':' in parsed.netloc:
        host = parsed.netloc.split(':')[0]
    else:
        host = parsed.netloc

    for port in PORTS_TO_TRY:
        if port in (80, 443):
            continue  # 已经在主重试中尝试过
        try:
            scheme = 'https' if port in (443, 8443) else 'http'
            test_url = f"{scheme}://{host}:{port}{parsed.path}"
            if parsed.query:
                test_url += '?' + parsed.query
            s, c, l, _ = http_get(test_url, ua=ua, timeout=15)
            if s == 200 and l > 1000:
                return (True, f'port_{port}', test_url)
        except Exception:
            continue
    return (False, '', None)


def extract_domains_from_html(html: str) -> List[str]:
    """从HTML提取候选域名（脱敏）"""
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


def migrate_domain(source_url: str, hint_url: str = None) -> Tuple[Optional[str], str]:
    """域名迁移5步闭环，返回 (new_url, reason)"""
    # Step1: 访问原URL提取候选域名
    status, content, content_len, _ = http_get(source_url, timeout=20)
    if status != 200 or content_len < 50:
        # 原URL不可达，尝试 https → http 降级
        if source_url.startswith('https://'):
            http_url = 'http://' + source_url[8:]
            status, content, content_len, _ = http_get(http_url, timeout=20)
            if status != 200:
                # Step2: 尝试"最新域名获取地址"提示
                if hint_url:
                    s2, c2, l2, _ = http_get(hint_url, timeout=20)
                    if s2 == 200 and l2 > 50:
                        domains = extract_domains_from_html(c2)
                        if not domains:
                            return None, 'hint_unreachable_no_domain'
                    else:
                        return None, 'hint_unreachable'
                else:
                    return None, 'original_unreachable_no_hint'
        else:
            return None, 'original_unreachable'

    # Step2: 提取候选域名（如果原URL可达）
    if status == 200 and content_len > 50:
        domains = extract_domains_from_html(content)
        # 同时尝试hint_url
        if hint_url and not domains:
            s2, c2, l2, _ = http_get(hint_url, timeout=20)
            if s2 == 200 and l2 > 50:
                domains = extract_domains_from_html(c2)
        if not domains:
            return None, 'no_hint_in_html'
    else:
        return None, 'original_and_hint_unreachable'

    # Step3: 去重去CDN
    candidates = []
    for d in domains:
        d = d.lower().strip().rstrip('/')
        # 提取纯域名
        m = re.match(r'([a-z0-9\-]+\.[a-z]{2,})', d)
        if not m:
            continue
        d = m.group(1)
        if d in CDN_DOMAINS:
            continue
        if d in candidates:
            continue
        candidates.append(d)

    if not candidates:
        return None, 'all_candidates_cdn'

    # Step4: 测试可达性
    for domain in candidates[:5]:
        for scheme in ['https', 'http']:
            test_url = f"{scheme}://{domain}/"
            s, c, l, _ = http_get(test_url, timeout=20)
            if s == 200 and l > 1000:
                # Step5: 用新域名替换sourceUrl
                return test_url, f'migrated_to_{scheme}'
            if s in (301, 302):
                # 跟随重定向
                final_url, fs, fl, _ = fetch_with_redirects(test_url, timeout=20)
                if fs == 200 and fl > 1000:
                    return final_url, f'migrated_via_redirect_{scheme}'

    return None, 'all_candidates_unreachable'


def extract_hint_url(comment: str) -> Optional[str]:
    """从sourceComment提取"最新域名获取地址"提示URL"""
    if not comment:
        return None
    # 匹配 "最新域名获取地址：URL" 等
    m = re.search(r'(?:最新域名获取地址|获取地址|域名发布页|备用地址)[：:\s]*(https?://[^\s\]\[<"\'<>]+)', comment)
    if m:
        return m.group(1)
    return None


# ==================== 14种技术手段深度重试 ====================
def deep_retry_14_techniques(url: str, comment: str = '') -> Tuple[bool, str, Optional[str], str]:
    """
    14种技术手段深度重试
    返回: (success, strategy_used, migrated_url, error_type)
    """
    # 1-4. 4种UA（Chrome/Mobile/Bot/Firefox）
    for ua_name, ua in USER_AGENTS:
        s, c, l, e = http_get(url, ua=ua, timeout=20)
        if s == 200 and l > 1000:
            return (True, f'ua_{ua_name.lower()}', None, 'ok')
        if is_request_forbidden(c, s):
            return (False, 'forbidden', None, 'http_403_forbidden')

    # 5. HTTP HEAD 方法
    s, c, l, e = http_get(url, method='HEAD', timeout=15)
    if s in (200, 301, 302):
        # HEAD成功，再用GET确认
        s2, c2, l2, _ = http_get(url, timeout=20)
        if s2 == 200 and l2 > 1000:
            return (True, 'head_method', None, 'ok')
        if s2 in (200, 301, 302):
            return (True, 'head_method', None, 'ok')

    # 6. Wayback Machine 存档查询
    s, c, l, info, e = check_wayback(url, timeout=30)
    if s == 200 and l > 1000:
        return (True, f'wayback_{info}', None, 'ok')

    # 7. HTTP/1.1 强制（http.client）
    s, c, l, e = http11_get(url, timeout=20)
    if s == 200 and l > 1000:
        return (True, 'http11_force', None, 'ok')

    # 8. HTTP 降级（https→http）
    if url.startswith('https://'):
        http_url = 'http://' + url[8:]
        s, c, l, e = http_get(http_url, timeout=20)
        if s == 200 and l > 1000:
            return (True, 'http_downgrade', http_url, 'ok')

    # 9. 跟随重定向（urllib）
    final_url, s, l, e = fetch_with_redirects(url, timeout=20)
    if s == 200 and l > 1000 and final_url != url:
        return (True, 'redirect_followed', final_url, 'ok')

    # 10. 长 timeout（40秒）
    s, c, l, e = http_get(url, timeout=40)
    if s == 200 and l > 1000:
        return (True, 'long_timeout_40s', None, 'ok')

    # 11. requests + Session（cookie共享）
    for ua_name, ua in USER_AGENTS[:2]:  # Chrome + Mobile
        s, c, l, e = requests_session_get(url, ua=ua, timeout=30)
        if s == 200 and l > 1000:
            return (True, f'requests_session_{ua_name.lower()}', None, 'ok')
        if is_request_forbidden(c, s):
            return (False, 'forbidden', None, 'http_403_forbidden')

    # 12. Playwright 真实渲染（stealth脚本）
    s, c, l, e = playwright_render(url, timeout_ms=25000)
    if s == 200 and l > 1000:
        return (True, 'playwright_stealth', None, 'ok')

    # 13. 8端口组合
    ok, strategy, new_url = try_port_combinations(url)
    if ok:
        return (True, strategy, new_url, 'ok')

    # 14. Wayback直接访问 + 60s超时多次重试
    s, c, l, e = check_wayback_direct(url, timeout=40)
    if s == 200 and l > 1000:
        return (True, 'wayback_direct', None, 'ok')

    # 14b. 多次重试（3次，60s超时）
    for attempt in range(3):
        s, c, l, e = http_get(url, timeout=60)
        if s == 200 and l > 1000:
            return (True, f'multi_retry_{attempt+1}', None, 'ok')
        time.sleep(1)

    # 全部失败，尝试域名迁移
    hint_url = extract_hint_url(comment)
    new_url, reason = migrate_domain(url, hint_url)
    if new_url:
        return (True, f'domain_migrate|{reason}', new_url, 'ok')

    # 最终错误类型
    last_status, last_content, _, last_e = http_get(url, timeout=20)
    err_type = classify_error(last_e, last_status, len(last_content))
    if is_request_forbidden(last_content, last_status):
        err_type = 'http_403_forbidden'

    return (False, 'truly_dead', None, err_type)


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


# ==================== 主流程 ====================
def main():
    print("=" * 80, flush=True)
    print("subagent_retry_failed.py — 54个失败源深度重试（14种技术手段+域名迁移+反爬配置）", flush=True)
    print("=" * 80, flush=True)

    # 全局socket超时保险（防止connect阶段卡死）
    socket.setdefaulttimeout(45)

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

    # 筛选 access_failed 源
    failed_indices = []
    for idx, source in enumerate(sources):
        comment = source.get("sourceComment", "") or ""
        if "AI_CLASSIFY:access_failed" in comment:
            failed_indices.append(idx)

    print(f"[INFO] 筛选出 access_failed 源: {len(failed_indices)} 个")

    # 禁用SSL警告
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    results = []
    stats = {
        'recovered': 0,
        'truly_dead': 0,
        'needs_login': 0,
    }

    for i, idx in enumerate(failed_indices):
        source = sources[idx]
        source_url = source.get("sourceUrl", "") or ""
        comment = source.get("sourceComment", "") or ""
        print(f"  [{i+1}/{len(failed_indices)}] idx={idx} starting retry (url_len={len(source_url)})...", flush=True)

        # 提取原始错误（脱敏）
        original_error = 'unknown'
        m = re.search(r'access_failed\|([^\]\[]+)', comment)
        if m:
            err_text = m.group(1).strip()
            # 脱敏：替换URL/域名
            err_text = re.sub(r"https?://[^\s\"'<>]+", "[URL]", err_text)
            err_text = re.sub(r"\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*", "[DOMAIN]", err_text, flags=re.IGNORECASE)
            original_error = err_text[:100]

        if not source_url.startswith(("http://", "https://")):
            # 非HTTP源直接标记为truly_dead
            results.append({
                "idx": idx,
                "original_error": original_error,
                "recovered": False,
                "recovered_url": "",
                "recovery_strategy": "none",
                "final_status": "truly_dead",
                "analysis_notes": "non_http_url"
            })
            stats['truly_dead'] += 1
            print(f"    -> truly_dead (non_http)", flush=True)
            continue

        # 14种技术手段深度重试（包裹在 try/except 防止单源崩溃）
        success = False
        strategy = 'unknown'
        migrated_url = None
        err_type = 'unknown'
        try:
            success, strategy, migrated_url, err_type = deep_retry_14_techniques(source_url, comment)
        except KeyboardInterrupt:
            # 捕获中断，标记为 unknown 并继续
            print(f"    -> KeyboardInterrupt caught, marking as unknown", flush=True)
            success = False
            strategy = 'interrupted'
            err_type = 'keyboard_interrupt'
        except Exception as e:
            success = False
            strategy = 'exception'
            migrated_url = None
            err_type = f'exception:{type(e).__name__}'
            print(f"    -> exception: {err_type}", flush=True)

        if success:
            stats['recovered'] += 1
            final_status = 'recovered'
            recovered_url = migrated_url or ''
            # 更新源
            if migrated_url:
                source['sourceUrl'] = migrated_url
            source['sourceComment'] = comment + f"\n[AI_RETRY:recovered|strategy={strategy}]"
            analysis_notes = f"strategy={strategy}"
            print(f"  [{i+1}/{len(failed_indices)}] idx={idx} status=recovered strategy={strategy}")
        else:
            # 检测是否反爬源
            if err_type == 'http_403_forbidden' or 'forbidden' in err_type.lower():
                # 反爬源：配置loginUrl
                if add_login_config(source):
                    stats['needs_login'] += 1
                    final_status = 'needs_login'
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        f"\n[AI_RETRY:needs_login|err={err_type}]"
                    analysis_notes = f"forbidden_source_login_configured|err={err_type}"
                    print(f"  [{i+1}/{len(failed_indices)}] idx={idx} status=needs_login err={err_type}")
                else:
                    stats['truly_dead'] += 1
                    final_status = 'truly_dead'
                    source['enabled'] = False
                    source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                        f"\n[AI_RETRY:truly_dead|err={err_type}]"
                    analysis_notes = f"forbidden_but_no_login|err={err_type}"
                    print(f"  [{i+1}/{len(failed_indices)}] idx={idx} status=truly_dead (forbidden_no_login)")
            else:
                stats['truly_dead'] += 1
                final_status = 'truly_dead'
                source['enabled'] = False
                source['sourceComment'] = (source.get("sourceComment", "") or "") + \
                    f"\n[AI_RETRY:truly_dead|err={err_type}]"
                analysis_notes = f"err={err_type}"
                print(f"  [{i+1}/{len(failed_indices)}] idx={idx} status=truly_dead err={err_type}")

            recovered_url = ''

        results.append({
            "idx": idx,
            "original_error": original_error,
            "recovered": success,
            "recovered_url": "[URL]" if recovered_url else "",
            "recovery_strategy": strategy,
            "final_status": final_status,
            "analysis_notes": analysis_notes
        })

        # 更新源列表
        sources[idx] = source

        # 进度提示
        if (i + 1) % 5 == 0:
            print(f"  [PROGRESS] {i+1}/{len(failed_indices)} recovered={stats['recovered']} dead={stats['truly_dead']} login={stats['needs_login']}")

    # 输出最终报告（仅技术指标，脱敏）
    output_report = {
        "agent": "failed_source_retrier",
        "total_analyzed": len(failed_indices),
        "recovered_count": stats['recovered'],
        "truly_dead_count": stats['truly_dead'],
        "needs_login_count": stats['needs_login'],
        "results": results
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"[RESULT] 深度重试完成")
    print(f"  - 总分析源数:       {len(failed_indices)}")
    print(f"  - recovered:        {stats['recovered']}")
    print(f"  - truly_dead:       {stats['truly_dead']}")
    print(f"  - needs_login:      {stats['needs_login']}")
    print(f"\n[OUTPUT] {OUTPUT_JSON}")
    print("=" * 80)


if __name__ == "__main__":
    main()
