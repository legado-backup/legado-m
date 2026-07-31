#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 Microsoft Sway 文档 API 结构，提取子站链接。
输出安全：不输出真实域名/URL/业务数据，只输出技术字段。
"""
import re
import json
import sys
import time
from urllib.parse import urlparse

import requests

# ===== 配置 =====
SWAY_DOC_ID = "9fNLFiE39CvqVsBq"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15

URLS = {
    "main": f"https://sway.cloud.microsoft/{SWAY_DOC_ID}",
    "embed": f"https://sway.cloud.microsoft/embed/{SWAY_DOC_ID}",
    "print": f"https://sway.cloud.microsoft/print/{SWAY_DOC_ID}",
    "oembed_v1": f"https://sway.cloud.microsoft/api/v1/oembed/{SWAY_DOC_ID}?format=json",
    "oembed_v1_0": f"https://sway.cloud.microsoft/api/v1.0/oembed?url=https%3a%2f%2fsway.cloud.microsoft%2f{SWAY_DOC_ID}&format=json",
}

# 微软/Sway 相关域名后缀，用于过滤（含 MS 基础设施域名）
MS_DOMAINS = (
    "microsoft.com", "microsoftonline.com", "microsoft.net",
    "microsoft365.com", "microsoft-ppe.com",
    "office.com", "office365.com", "office-int.com", "office-int.net",
    "office.net", "officeppe.com", "officeppe.net",
    "live.com", "live.net", "live-int.com",
    "msn.com", "msn.net", "bing.com", "bing.net", "bingapis.com",
    "sway.cloud.microsoft", "sway.com", "sway.office.com",
    "sway-cdn.com", "sway-edog.com", "sway-int.com",
    "azure.com", "azure.net", "azureedge.net", "azurefd.net",
    "azure-api.net", "azurewebsites.net", "cloudapp.net",
    "trafficmanager.net", "windows-ppe.net",
    "akamai.net", "akamaized.net",  # CDN
    "skype.com", "xbox.com", "windows.net",
    "onmicrosoft.com", "sharepoint.com",
    "msecnd.net", "msftauth.net", "msauth.net",
    "trouter.io", "trouter.skype.com",
    "cloud.microsoft", "cloud-dev.microsoft",  # Sway 当前主域
    "1drv.ms", "onedrive.com",
    "aka.ms", "gfx.ms",  # MS 短链/静态资源
    "docs.com", "int-docs.com", "contentvalidation.com",  # MS Sway 关联
    "static.microsoft",  # MS 静态资源（无.com后缀）
    "onenote.com",
    "linkedin.com",
    "google.com", "googleapis.com", "gstatic.com", "google-analytics.com",
    "facebook.com", "facebook.net",
    "twitter.com", "x.com", "twimg.com", "ads-twitter.com",
    "youtube.com", "youtu.be", "ytimg.com",
    "jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
    "w3.org", "schema.org",
    "vimeo.com", "soundcloud.com", "sketchfab.com", "pickit.com",  # Sway 内嵌第三方服务
)

# 子站判定时排除上面域名的URL
def is_ms_or_tracker(host):
    host = host.lower().lstrip(".")
    for d in MS_DOMAINS:
        if host == d or host.endswith("." + d):
            return True
    return False


# 安全化URL：只保留 host后缀 + path模式
def safe_url(raw_url):
    try:
        p = urlparse(raw_url)
    except Exception:
        return None
    host = p.netloc.lower()
    if not host:
        return None
    # 域名后缀
    parts = host.split(".")
    suffix = "." + ".".join(parts[-2:]) if len(parts) >= 2 else host
    # 路径模式化：把数字/长hash替换为{id}
    path = p.path or "/"
    path = re.sub(r"/\d{3,}", "/{id}", path)
    path = re.sub(r"/[a-f0-9]{8,}", "/{hash}", path)
    path = re.sub(r"/[A-Z0-9]{10,}", "/{id}", path)
    # 查询参数键列表
    qkeys = ""
    if p.query:
        ks = [kv.split("=")[0] for kv in p.query.split("&") if kv]
        qkeys = "?" + ",".join(sorted(set(ks))) if ks else ""
    return f"{suffix}{path}{qkeys}"


def fetch(url, headers=None, allow_redirects=True):
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    try:
        r = requests.get(url, headers=h, timeout=TIMEOUT,
                         allow_redirects=allow_redirects)
        return r, None
    except Exception as e:
        return None, str(e)


def scan_html(html):
    """扫描HTML，提取技术信息。返回 dict。"""
    info = {
        "size": len(html) if html else 0,
        "api_endpoints": [],          # API 端点路径模式
        "tokens": [],                 # token来源描述（不输出token值）
        "preloaded_vars": [],         # 预加载数据变量名
        "json_ld_blocks": 0,          # JSON-LD 块数量
        "json_ld_types": [],          # JSON-LD @type
        "all_urls": [],               # 所有 http(s) URL
        "non_ms_urls_safe": [],       # 非微软域名的安全化URL
        "meta_keys": [],              # meta 标签 name/property
        "script_src_safe": [],        # script src 路径模式
    }
    if not html:
        return info

    # API 端点模式
    api_patterns = [
        r'["\']/api/v\d+/[^"\'\s]+["\']',
        r'["\']/api/documents?/[^"\'\s]+["\']',
        r'["\']/api/[^"\'\s]+["\']',
        r'["\']/contents?/[^"\'\s]+["\']',
        r'api\.sway[^"\'\s]*',
        r'contentEndpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'["\']https://sway\.cloud\.microsoft/api/[^"\']+["\']',
    ]
    for pat in api_patterns:
        for m in re.findall(pat, html, flags=re.IGNORECASE):
            # 模式化
            s = m if isinstance(m, str) else (m[0] if m else "")
            s = re.sub(r'\d{6,}', '{id}', s)
            info["api_endpoints"].append(s.strip("'\""))
    info["api_endpoints"] = sorted(set(info["api_endpoints"]))[:30]

    # token / auth 相关
    token_patterns = [
        (r'Bearer\s+([A-Za-z0-9_\-\.]+)', "Bearer in JS"),
        (r'authorization["\']?\s*[:=]\s*["\']([^"\']+)["\']', "authorization header"),
        (r'<meta[^>]+name=["\']bearer[^"\']*["\'][^>]*>', "meta bearer"),
        (r'<meta[^>]+http-equiv=["\']authorization[^"\']*["\'][^>]*>', "meta http-equiv authorization"),
        (r'accessToken["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', "accessToken var"),
        (r'token["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']', "token var"),
        (r'_csrf["\']?\s*[:=]\s*["\']([^"\']+)["\']', "csrf token"),
    ]
    for pat, src in token_patterns:
        if re.search(pat, html, flags=re.IGNORECASE):
            # 只记录来源，不记录 token 值
            info["tokens"].append(src)
    info["tokens"] = sorted(set(info["tokens"]))

    # 预加载数据变量
    preload_patterns = [
        r'window\.(__PRELOADED_STATE__|__INITIAL_STATE__|__INITIAL_DATA__|initialData|__DATA__|__APP_CONFIG__|preloadedData|window\.__swayData__)\s*=',
        r'window\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{[^}]{50,}',  # 大对象赋值
    ]
    for pat in preload_patterns:
        for m in re.findall(pat, html):
            if isinstance(m, tuple):
                m = m[0]
            info["preloaded_vars"].append(m)
    info["preloaded_vars"] = sorted(set(info["preloaded_vars"]))[:20]

    # JSON-LD
    ld_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, flags=re.DOTALL)
    info["json_ld_blocks"] = len(ld_blocks)
    for b in ld_blocks:
        try:
            d = json.loads(b.strip())
            if isinstance(d, dict):
                t = d.get("@type")
                if t:
                    info["json_ld_types"].append(str(t))
        except Exception:
            pass
    info["json_ld_types"] = sorted(set(info["json_ld_types"]))

    # 所有 http(s) URL
    all_urls = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', html)
    info["all_urls"] = all_urls

    # 非微软/非追踪器域名
    non_ms = []
    for u in all_urls:
        try:
            p = urlparse(u)
        except Exception:
            continue
        host = p.netloc.lower().lstrip(".")
        if not host:
            continue
        if is_ms_or_tracker(host):
            continue
        s = safe_url(u)
        if s:
            non_ms.append(s)
    info["non_ms_urls_safe"] = sorted(set(non_ms))

    # meta 标签
    for m in re.findall(r'<meta[^>]+(?:name|property)=["\']([^"\']+)["\']', html):
        info["meta_keys"].append(m)
    info["meta_keys"] = sorted(set(info["meta_keys"]))[:30]

    # script src
    for m in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html):
        s = safe_url(m) if m.startswith("http") else None
        if s:
            info["script_src_safe"].append(s)
        else:
            # 相对路径直接保留模式化
            mm = re.sub(r'\d{6,}', '{id}', m)
            info["script_src_safe"].append(mm)
    info["script_src_safe"] = sorted(set(info["script_src_safe"]))[:30]

    return info


def try_content_apis(main_html, embed_html):
    """尝试从HTML中提取的API端点，直接调用。"""
    results = []
    candidate_apis = set()
    # 从HTML中提取 /api/ 开头的路径
    for html in [main_html, embed_html]:
        if not html:
            continue
        for m in re.findall(r'["\']([^"\']*/api/[^"\']+)[ "\']*', html):
            # 把 {id} 占位
            url = m if m.startswith("http") else f"https://sway.cloud.microsoft{m if m.startswith('/') else '/' + m}"
            url = url.replace("{id}", SWAY_DOC_ID).replace("{docId}", SWAY_DOC_ID)
            candidate_apis.add(url)

    # 常见猜测（含 v1.0/v2.0 版本）
    guesses = [
        f"https://sway.cloud.microsoft/api/v1/contents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1/documents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1/contents/{SWAY_DOC_ID}/content",
        f"https://sway.cloud.microsoft/api/v1/contents/{SWAY_DOC_ID}/pages",
        f"https://sway.cloud.microsoft/api/documents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/contents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1.0/documents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{SWAY_DOC_ID}/content",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{SWAY_DOC_ID}/pages",
        f"https://sway.cloud.microsoft/api/v2.0/contents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v2/contents/{SWAY_DOC_ID}",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{SWAY_DOC_ID}?locale=en-us",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{SWAY_DOC_ID}/publish",
        f"https://sway.cloud.microsoft/api/v1.0/documents/{SWAY_DOC_ID}/content",
    ]
    for g in guesses:
        candidate_apis.add(g)

    # 不带认证调用
    for url in sorted(candidate_apis)[:15]:
        r, err = fetch(url, headers={"Accept": "application/json"})
        if err:
            results.append({"url_safe": safe_url(url) or url, "auth": "none",
                            "status": "ERR", "err": err[:80], "size": 0,
                            "content_type": "", "has_substation": False})
            continue
        ct = r.headers.get("Content-Type", "")
        body = r.text or ""
        # 检测子站链接（非微软域名的URL）
        has_sub = False
        sub_safe = []
        urls_found = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', body)
        for u in urls_found:
            try:
                p = urlparse(u)
            except Exception:
                continue
            if not p.netloc:
                continue
            if is_ms_or_tracker(p.netloc.lower().lstrip(".")):
                continue
            has_sub = True
            s = safe_url(u)
            if s:
                sub_safe.append(s)
        results.append({
            "url_safe": safe_url(url) or url,
            "auth": "none",
            "status": r.status_code,
            "size": len(body),
            "content_type": ct.split(";")[0].strip(),
            "has_substation": has_sub,
            "sub_safe": sorted(set(sub_safe))[:10],
        })
        time.sleep(0.3)
    return results


def main():
    print("=== Sway 文档抓取 ===")
    htmls = {}
    for key, url in URLS.items():
        r, err = fetch(url)
        if err:
            print(f"[{key}] ERROR: {err[:100]}")
            htmls[key] = (None, None, 0)
            continue
        ct = r.headers.get("Content-Type", "")
        body = r.text or ""
        htmls[key] = (body, r.status_code, len(body))
        print(f"[{key}] status={r.status_code} size={len(body)} ct={ct.split(';')[0]}")

    main_html = htmls["main"][0]
    embed_html = htmls["embed"][0]
    print_html = htmls["print"][0]

    print("\n=== HTML源码扫描 ===")
    scan_main = scan_html(main_html)
    scan_embed = scan_html(embed_html)
    scan_print = scan_html(print_html)

    print(f"主视图大小: {scan_main['size']} 字节")
    print(f"embed视图大小: {scan_embed['size']} 字节")
    print(f"print视图大小: {scan_print['size']} 字节")

    print(f"\n[主视图] API端点候选: {scan_main['api_endpoints']}")
    print(f"[主视图] token来源: {scan_main['tokens']}")
    print(f"[主视图] 预加载数据变量: {scan_main['preloaded_vars']}")
    print(f"[主视图] JSON-LD块数: {scan_main['json_ld_blocks']} types={scan_main['json_ld_types']}")
    print(f"[主视图] meta键: {scan_main['meta_keys']}")
    print(f"[主视图] script src模式: {scan_main['script_src_safe']}")

    print(f"\n[embed视图] API端点候选: {scan_embed['api_endpoints']}")
    print(f"[embed视图] token来源: {scan_embed['tokens']}")
    print(f"[embed视图] 预加载数据变量: {scan_embed['preloaded_vars']}")
    print(f"[embed视图] JSON-LD块数: {scan_embed['json_ld_blocks']} types={scan_embed['json_ld_types']}")
    print(f"[embed视图] meta键: {scan_embed['meta_keys']}")
    print(f"[embed视图] script src模式: {scan_embed['script_src_safe']}")

    print(f"\n[print视图] API端点候选: {scan_print['api_endpoints']}")
    print(f"[print视图] token来源: {scan_print['tokens']}")
    print(f"[print视图] 预加载数据变量: {scan_print['preloaded_vars']}")
    print(f"[print视图] JSON-LD块数: {scan_print['json_ld_blocks']} types={scan_print['json_ld_types']}")
    print(f"[print视图] meta键: {scan_print['meta_keys']}")
    print(f"[print视图] script src模式: {scan_print['script_src_safe']}")

    # oembed 响应字段（两个版本）
    print("\n=== oembed API响应 ===")
    for ok in ["oembed_v1", "oembed_v1_0"]:
        url = URLS[ok]
        print(f"\n--- {ok}: {safe_url(url)} ---")
        r, err = fetch(url, headers={"Accept": "application/json"})
        if err:
            print(f"  ERROR: {err[:100]}")
            continue
        body = r.text or ""
        print(f"  status={r.status_code} size={len(body)} ct={r.headers.get('Content-Type','').split(';')[0]}")
        if r.status_code == 200 and body.strip().startswith(("{", "[")):
            try:
                oj = r.json()
                if isinstance(oj, dict):
                    print(f"  字段: {list(oj.keys())}")
                    # 安全化输出每个字段值（不输出原始业务数据）
                    for k, v in oj.items():
                        if isinstance(v, str):
                            # 只输出长度和是否含URL
                            has_url = bool(re.search(r'https?://', v))
                            print(f"  {k}: 类型=str 长度={len(v)} 含URL={has_url}")
                            # 如果含URL，提取并安全化
                            if has_url:
                                urls_in_v = re.findall(r'https?://[^\s"\'<>\)\\\]+]+', v)
                                safe_urls = []
                                for u in urls_in_v:
                                    try:
                                        p = urlparse(u)
                                    except Exception:
                                        continue
                                    if not p.netloc:
                                        continue
                                    if is_ms_or_tracker(p.netloc.lower().lstrip(".")):
                                        continue
                                    s = safe_url(u)
                                    if s:
                                        safe_urls.append(s)
                                if safe_urls:
                                    print(f"    非微软URL(安全化): {sorted(set(safe_urls))}")
                        elif isinstance(v, (int, float, bool)):
                            print(f"  {k}: {type(v).__name__}={v}")
                        elif v is None:
                            print(f"  {k}: null")
                        else:
                            print(f"  {k}: 类型={type(v).__name__}")
                else:
                    print(f"  顶层类型: {type(oj).__name__}")
            except Exception as e:
                print(f"  非JSON: {e}")

    # 尝试内容API
    print("\n=== 内容API调用尝试 ===")
    results = try_content_apis(main_html, embed_html)
    for r_ in results:
        print(f"  [{r_['auth']}] {r_['url_safe']} -> status={r_['status']} "
              f"size={r_['size']} ct={r_.get('content_type','')} "
              f"has_substation={r_['has_substation']}")
        if r_["has_substation"] and r_.get("sub_safe"):
            print(f"      子站安全URL: {r_['sub_safe']}")

    # 总结：HTML中所有非微软URL（正则搜索）
    print("\n=== HTML中URL正则搜索（替代方案）===")
    for label, scan in [("main", scan_main), ("embed", scan_embed), ("print", scan_print)]:
        total = len(scan["all_urls"])
        ms_count = total - len([u for u in scan["all_urls"]
                                if not is_ms_or_tracker(
                                    urlparse(u).netloc.lower().lstrip("."))])
        non_ms_count = len(scan["non_ms_urls_safe"])
        print(f"[{label}] URL总数={total} 微软/追踪器={ms_count} 其他={non_ms_count}")
        if scan["non_ms_urls_safe"]:
            print(f"[{label}] 非微软URL(安全化): {scan['non_ms_urls_safe']}")

    # 合并所有非微软URL作为子站候选
    all_sub_candidates = sorted(set(
        scan_main["non_ms_urls_safe"] +
        scan_embed["non_ms_urls_safe"] +
        scan_print["non_ms_urls_safe"]
    ))
    print(f"\n=== 子站链接候选清单（去重后）===")
    print(f"子站候选数量: {len(all_sub_candidates)}")
    for i, s in enumerate(all_sub_candidates, 1):
        print(f"  子站候选E{i}: {s}")

    # 深度分析主视图HTML：寻找内联JSON/SPA配置
    print("\n=== 主视图HTML深度分析 ===")
    if main_html:
        # 保存到文件用于检查
        try:
            out_path = "ai_tests/output/sway_main.html"
            import os
            os.makedirs("ai_tests/output", exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(main_html)
            print(f"主视图HTML已保存: {out_path}")
        except Exception as e:
            print(f"保存失败: {e}")

        # 提取所有 <script> 标签内容（内联JS）
        scripts_inline = re.findall(
            r'<script(?![^>]+src=)[^>]*>(.*?)</script>',
            main_html, flags=re.DOTALL)
        print(f"内联script块数: {len(scripts_inline)}")
        for i, s in enumerate(scripts_inline[:10]):
            s_strip = s.strip()
            if not s_strip:
                continue
            print(f"  [inline#{i}] 长度={len(s_strip)} 预览={s_strip[:120]!r}")

        # 提取所有 data-* 属性
        data_attrs = re.findall(r'data-([a-z0-9\-]+)=["\']([^"\']*)["\']',
                                main_html, flags=re.IGNORECASE)
        if data_attrs:
            print(f"data-* 属性数: {len(data_attrs)}")
            for k, v in data_attrs[:20]:
                vv = v if len(v) < 80 else v[:80] + "..."
                print(f"  data-{k}={vv!r}")

        # 寻找 SPA 启动配置
        spa_patterns = [
            (r'window\.([A-Za-z_][A-Za-z0-9_]*)\s*=', "window.X="),
            (r'__([A-Z_][A-Z0-9_]*)__', "double_underscore_var"),
            (r'(?:bootConfig|appConfig|swayConfig|preloadConfig|runtimeConfig)',
             "config_var"),
            (r'(?:contentsEndpoint|contentEndpoint|apiEndpoint|graphqlEndpoint)',
             "endpoint_var"),
            (r'JSON\.parse\(([^)]{20,})\)', "JSON.parse"),
            (r'"(https://[^"]*sway[^"]*)"', "sway_url_in_string"),
        ]
        for pat, label in spa_patterns:
            matches = re.findall(pat, main_html)
            if matches:
                uniq = sorted(set(matches))[:10]
                # 安全化URL
                safe = []
                for m in uniq:
                    if isinstance(m, str) and m.startswith("http"):
                        s = safe_url(m)
                        safe.append(s if s else m[:60])
                    else:
                        safe.append(m if len(m) < 60 else m[:60] + "...")
                print(f"  [{label}] {safe}")

        # 搜索 main HTML 中所有非微软URL（已用扩展域名表过滤）
        print(f"  主视图非微软URL数(扩展过滤后): {len(scan_main['non_ms_urls_safe'])}")
    else:
        print("  主视图HTML为空")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
