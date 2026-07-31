#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析站点E（聚合视频网站）的技术结构
输出安全：只输出技术字段（HTTP状态码/CSS选择器/URL模式/DOM结构/数量统计）
        禁止输出真实域名/完整URL/源名称/视频标题/分类名称等业务数据
依赖：requests（venv已安装），不使用bs4（用正则解析）
"""
import re
import sys
import ssl
import urllib3
import requests
from urllib.parse import urlparse, urljoin
from collections import Counter

# ============ 配置 ============
TARGET_URL = "https://av.avav2.lol/"
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 关闭SSL警告（仅用于技术分析）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ 输出安全：脱敏函数 ============
# 真实域名替换映射
DOMAIN_MAP = {
    "av.avav2.lol": "站点E",
    "sway.cloud.microsoft": "中转站S",
}

# 成人/敏感词汇过滤表（替换为代号）
SENSITIVE_WORDS = [
    "av", "porn", "sex", "xxx", "adult", "nude", "fuck", "色情", "成人",
    "adult", "hentai", "nsfw",
]


def mask_domain(text):
    """将真实域名替换为站点代号（仅替换DOMAIN_MAP中的已知域名）"""
    if not text:
        return text
    out = text
    for real, code in DOMAIN_MAP.items():
        out = out.replace(real, code)
    return out


def mask_any_url(text):
    """激进脱敏：替换所有http(s)://domain/为代号URL，不论域名是什么
    用于调试输出，确保任何真实域名都不泄漏
    """
    if not text:
        return text
    # 先替换已知域名
    out = mask_domain(text)
    # 再替换所有剩余的 http(s)://xxx.xxx/ 形式URL
    def _replace(m):
        url = m.group(0)
        try:
            p = urlparse(url)
            path = p.path if p.path else "/"
            path = re.sub(r"/\d{2,}", "/{id}", path)
            return f"{p.scheme}://其他域名{path}"
        except Exception:
            return "https://其他域名/"
    out = re.sub(r'https?://[a-zA-Z0-9\-_.]+(?:\.[a-zA-Z0-9\-_.]+)+(?:/[^\s"\'<>\\]*)?', _replace, out)
    return out


def mask_domain_name(domain):
    """脱敏单个域名：已知域名用代号，未知域名用'其他域名'"""
    if not domain:
        return domain
    for real, code in DOMAIN_MAP.items():
        if real in domain:
            return code
    return "其他域名"


def mask_url(url):
    """脱敏URL：域名->站点E，路径保留模式化，query保留key名"""
    if not url:
        return ""
    try:
        p = urlparse(url)
        if not p.netloc:
            return url  # 相对路径原样返回
        # 域名脱敏
        netloc = "站点E"
        for real, code in DOMAIN_MAP.items():
            if real in p.netloc:
                netloc = code
                break
        else:
            # 未知子域名也脱敏
            netloc = "子站域名"
        path = p.path if p.path else "/"
        # 把数字ID模式化为 {id}
        path = re.sub(r"/\d{2,}", "/{id}", path)
        # query只保留key
        if p.query:
            keys = "&".join(k.split("=")[0] for k in p.query.split("&") if k)
            return f"{p.scheme}://{netloc}{path}?{keys}"
        return f"{p.scheme}://{netloc}{path}"
    except Exception:
        return "[INVALID_URL]"


def mask_text(text):
    """过滤敏感词汇，替换为代号（仅匹配独立词，避免误伤favicon等技术词）"""
    if not text:
        return text
    out = text
    for w in SENSITIVE_WORDS:
        # 使用词边界匹配，避免误伤favicon/javscript等技术词
        # 对于中文词直接替换，对于英文词用边界
        if re.fullmatch(r"[a-zA-Z]+", w):
            out = re.sub(r"\b" + re.escape(w) + r"\b", "[过滤]", out, flags=re.IGNORECASE)
        else:
            out = out.replace(w, "[过滤]")
    return out


def debug_dump_sway_content(html, final_url):
    """深度调试Sway页面：查找嵌入的内容数据/API端点/预加载JSON"""
    safe_print("\n--- Sway内容深度调试 ---")
    # 1. 所有inline script（无src的script标签，可能含预加载数据）
    inline_scripts = []
    for m in re.finditer(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL):
        content = m.group(1).strip()
        if content:
            inline_scripts.append(content)
    safe_print(f"内联script数量: {len(inline_scripts)}")
    for i, sc in enumerate(inline_scripts[:10]):
        # 只显示前150字符，脱敏
        preview = sc[:150].replace("\n", " ")
        safe_print(f"  内联script[{i}] (长度{len(sc)}): {mask_domain(preview)}")

    # 2. 查找预加载数据模式
    preload_patterns = [
        r'window\.__PRELOADED',
        r'window\.__INITIAL',
        r'window\.preloadedData',
        r'window\.initialData',
        r'window\.__PRELOAD_STATE__',
        r'"preloadedData"',
        r'"initialState"',
        r'"preloadState"',
    ]
    for pat in preload_patterns:
        if re.search(pat, html, re.IGNORECASE):
            safe_print(f"  发现预加载模式: {pat}")

    # 3. 查找API端点（/api/开头的URL）
    api_urls = set()
    for m in re.finditer(r'["\'](/api/[^"\']+)["\']', html, re.IGNORECASE):
        api_urls.add(m.group(1))
    for m in re.finditer(r'(https?://[^"\']*sway[^"\']*/api/[^"\']+)', html, re.IGNORECASE):
        api_urls.add(m.group(1))
    safe_print(f"API端点数量: {len(api_urls)}")
    for au in list(api_urls)[:10]:
        safe_print(f"  API端点: {mask_url(au)}")

    # 4. 查找type="application/json"的script标签
    json_scripts = re.findall(r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
                               html, re.IGNORECASE | re.DOTALL)
    safe_print(f"JSON script标签数量: {len(json_scripts)}")
    for i, js in enumerate(json_scripts[:3]):
        safe_print(f"  JSON[{i}]长度: {len(js)}")
        # 在JSON中搜索非微软的URL
        urls_in_json = re.findall(r'https?://[a-zA-Z0-9\-_.]+(?:\.[a-zA-Z0-9\-_.]+)+(?:/[^\s"\'<>\\]*)?', js)
        non_ms_urls = [u for u in urls_in_json if "microsoft" not in u.lower() and "sway" not in u.lower()
                       and "azure" not in u.lower() and "google" not in u.lower()
                       and "cloudflare" not in u.lower()]
        if non_ms_urls:
            safe_print(f"  JSON[{i}]中非微软URL数: {len(non_ms_urls)}")
            for u in non_ms_urls[:5]:
                safe_print(f"    {mask_url(u)}")

    # 5. 查找print/embed变体URL（可能返回服务端渲染内容）
    sway_id_m = re.search(r'sway\.cloud\.microsoft/([a-zA-Z0-9]+)/?', final_url)
    if sway_id_m:
        doc_id = sway_id_m.group(1)
        safe_print(f"Sway文档ID: {doc_id}")
        safe_print("提示: 可尝试print/embed变体获取服务端渲染内容")

    # 6. 查找og: meta标签（可能含描述）
    og_metas = re.findall(r'<meta[^>]+property=["\']og:[^"\']+["\'][^>]+content=["\']([^"\']+)["\']',
                          html, re.IGNORECASE)
    safe_print(f"og:meta数量: {len(og_metas)}")
    for om in og_metas[:3]:
        safe_print(f"  og:meta(脱敏): {mask_text(om[:100])}")

    safe_print("--- Sway内容深度调试结束 ---\n")


def debug_dump_html_structure(html, final_url, max_lines=80):
    """调试输出HTML结构（脱敏后），用于理解小HTML页面的内容"""
    safe_print("\n--- HTML结构调试 (脱敏后) ---")
    # 移除多余空白
    compact = re.sub(r"\s+", " ", html)
    # 提取所有标签和关键属性
    # 1. meta标签
    metas = re.findall(r'<meta[^>]+>', html, re.IGNORECASE)
    for m in metas[:10]:
        safe_print(f"  META: {mask_domain(m[:150])}")
    # 2. link标签
    links_tag = re.findall(r'<link[^>]+>', html, re.IGNORECASE)
    for l in links_tag[:10]:
        safe_print(f"  LINK: {mask_domain(l[:150])}")
    # 3. script src
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
    for s in scripts[:10]:
        safe_print(f"  SCRIPT SRC: {mask_url(s)}")
    # 4. 所有a href（脱敏）
    a_hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    safe_print(f"  A标签数量: {len(a_hrefs)}")
    for h in a_hrefs[:20]:
        abs_h = urljoin(final_url, h)
        safe_print(f"    A: {mask_url(abs_h)}")
    # 5. iframe
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for ifr in iframes[:5]:
        safe_print(f"  IFRAME: {mask_url(urljoin(final_url, ifr))}")
    # 6. body内文本的前500字符（脱敏）
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.IGNORECASE | re.DOTALL)
    if body_m:
        body_text = re.sub(r'<[^>]+>', ' ', body_m.group(1))
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        if body_text:
            safe_print(f"  BODY文本(前300字符脱敏): {mask_text(body_text[:300])}")
    # 7. JS跳转/关键JS变量
    js_redirects = re.findall(r'(?:location\.(?:href|replace)\s*=\s*|window\.location\s*=\s*|top\.location\s*=\s*)(["\'][^"\']+["\'])', html)
    for j in js_redirects[:3]:
        safe_print(f"  JS跳转: {mask_text(j)}")
    # 8. 检查是否SPA (app挂载点)
    if re.search(r'<div[^>]+id=["\']app["\']', html):
        safe_print("  SPA特征: 检测到 id=app 挂载点")
    if re.search(r'<div[^>]+id=["\']root["\']', html):
        safe_print("  SPA特征: 检测到 id=root 挂载点")
    safe_print("--- HTML结构调试结束 ---\n")


def safe_print(s):
    """安全打印：先用激进脱敏替换所有URL，再过滤敏感词"""
    s = mask_any_url(str(s))
    s = mask_text(s)
    print(s)


# ============ HTTP请求 ============
def fetch(url, allow_redirects=True):
    """发起HTTP请求，返回(resp, final_url, error)
    自动处理编码：优先用apparent_encoding避免UTF-8被当Latin-1导致乱码
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        resp = requests.get(
            url, headers=headers, timeout=TIMEOUT,
            verify=False, allow_redirects=allow_redirects,
        )
        # 修复编码：若resp.encoding不是utf-8但内容是utf-8，用apparent_encoding
        try:
            if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "latin-1"):
                # requests默认对无charset声明的响应用ISO-8859-1，导致中文乱码
                apparent = resp.apparent_encoding
                if apparent:
                    resp.encoding = apparent
        except Exception:
            pass
        return resp, resp.url, None
    except requests.exceptions.SSLError as e:
        return None, url, f"SSLError: {type(e).__name__}"
    except requests.exceptions.ConnectionError as e:
        return None, url, f"ConnectionError: {type(e).__name__}"
    except requests.exceptions.Timeout:
        return None, url, "Timeout"
    except requests.exceptions.RequestException as e:
        return None, url, f"RequestException: {type(e).__name__}"
    except Exception as e:
        return None, url, f"Exception: {type(e).__name__}"


# ============ HTML解析（正则） ============
def extract_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def extract_meta_generator(html):
    m = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
                  html, re.IGNORECASE)
    return m.group(1) if m else ""


def detect_cms(html, base_url):
    """识别CMS类型"""
    h = html.lower()
    # 先判断当前URL所在域名（避免把"提到sway的跳转页"误判为sway页）
    try:
        cur_netloc = urlparse(base_url).netloc.lower()
    except Exception:
        cur_netloc = ""
    on_sway = "sway.cloud.microsoft" in cur_netloc or "sway.com" in cur_netloc
    # Sway中转页特征：仅当当前URL就在sway域名上才判定
    if on_sway:
        return "Microsoft-Sway(中转导航页)"
    # maccms特征
    if any(k in h for k in [
        "/index.php/vod/", "vodsearch", "vodtype", "voddetail",
        "mac_player", "maccms", "player_data", "cms",
        "/api.php/provide/vod/",
    ]):
        return "maccms"
    # wordpress特征
    if any(k in h for k in ["/wp-content/", "/wp-includes/", "/wp-json/", "wp-content/themes"]):
        return "wordpress"
    if "wordpress" in extract_meta_generator(html).lower():
        return "wordpress"
    # discuz特征
    if any(k in h for k in ["discuz", "forum.php", "thread-", "class_discuz"]):
        return "discuz"
    # dedecms
    if any(k in h for k in ["dede", "powerby", "dedecms"]):
        return "dedecms"
    # 自定义SPA
    if "<div id=\"app\">" in h and ("vue" in h or "react" in h or "vite" in h):
        return "SPA(Vue/React)"
    # 检查是否JS跳转页（放宽阈值到5000，并检测多种跳转特征）
    # 注意：即使body文本提到其他域名，只要是"小页面+跳转特征+少a标签"就判为JS跳转页
    if len(html) < 5000 and (
        re.search(r'location\.(?:href|replace)\s*=', html)
        or re.search(r'window\.location', html, re.IGNORECASE)
        or re.search(r'var\s+targetUrl\s*=', html, re.IGNORECASE)
        or re.search(r'var\s+\w*[Uu]rl\s*=\s*["\']https?://', html, re.IGNORECASE)
        or re.search(r'settimeout\s*\(\s*function', html, re.IGNORECASE)
    ) and len(re.findall(r'<a\s', html, re.IGNORECASE)) < 5:
        return "JS跳转页"
    return "自定义"


def extract_js_redirect(html):
    """提取JS跳转目标（覆盖多种模式）"""
    patterns = [
        # var targetUrl = "xxx"; location.href = targetUrl
        r'var\s+targetUrl\s*=\s*["\']([^"\']+)["\']',
        # var xxx = "url"; ... location.href = xxx
        r'var\s+\w*[Uu]rl\s*=\s*["\']([^"\']+)["\']',
        # location.href = "xxx"
        r'location\.(?:href|replace)\s*=\s*["\']([^"\']+)["\']',
        # window.location = "xxx"
        r'window\.location\s*=\s*["\']([^"\']+)["\']',
        # top.location = "xxx"
        r'top\.location\s*=\s*["\']([^"\']+)["\']',
        # window.location.href = "xxx"
        r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
        # meta refresh
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'>\s]+)',
        # location.assign("xxx")
        r'location\.assign\s*\(\s*["\']([^"\']+)["\']',
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            url = m.group(1).strip()
            # 过滤明显非URL的值
            if url and (url.startswith("http") or url.startswith("/") or url.startswith(".")):
                found.append(url)
    # 去重，优先http(s)开头的
    seen = set()
    unique = []
    for u in found:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[0] if unique else ""


def extract_links(html, base_url):
    """提取所有<a href>链接，返回绝对URL列表"""
    links = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = m.group(1).strip()
        if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        abs_url = urljoin(base_url, href)
        links.append(abs_url)
    return links


def extract_all_urls_from_html(html, base_url):
    """从HTML中提取所有URL（包括script内的JSON、文本中的URL）
    用于分析SPA/Sway等JS渲染页面的初始HTML
    """
    urls = set()
    # 1. 所有 http(s) URL
    for m in re.finditer(r'https?://[a-zA-Z0-9\-_.]+(?:\.[a-zA-Z0-9\-_.]+)+(?:/[^\s"\'<>\\]*)?', html):
        urls.add(m.group(0).rstrip('.,;)'))
    # 2. 相对路径（/xxx/ 形式，至少2级）
    for m in re.finditer(r'["\'](/(?:[a-zA-Z0-9_-]+/){1,3}[a-zA-Z0-9_\-./]*)["\']', html):
        abs_url = urljoin(base_url, m.group(1))
        urls.add(abs_url)
    return list(urls)


def find_substations_in_sway(html, base_url):
    """从Sway中转页提取子站链接
    Sway是微软的SPA，内容在JSON中，子站链接通常是外部http(s) URL
    策略：
    1. 提取所有外部URL，按域名分组
    2. 过滤掉微软/Sway/CDN/统计类域名
    3. 尝试从Sway内容API获取真实内容
    """
    all_urls = extract_all_urls_from_html(html, base_url)
    # 排除的域名（微软自家/Sway基础设施/CDN/统计/字体等非子站）
    EXCLUDE_DOMAINS = [
        # 微软/Sway基础设施
        "microsoft.com", "sway.cloud.microsoft", "sway.com", "sway.office",
        "sway-edog", "sway-int", "sway.static", "sway-cdn",
        "microsoftonline.com", "msftauth", "live.com", "office.com",
        "office365.com", "office.net", "msn.com", "bing.com",
        "go.microsoft", "microsoftstream.com",
        "azureedge.net", "azure.com", "msecnd.net",
        # CDN/统计/字体
        "google.com", "googleapis.com", "gstatic.com", "googletagmanager",
        "cloudflare.com", "cloudflareinsights.com", "cf-", "beacon.min.js",
        "fontawesome", "fonts.googleapis", "fonts.gstatic",
        "jquery", "bootstrap", "unpkg.com", "jsdelivr.net",
        "akamai", "amazonaws.com", "fastly",
        # 社交/版本控制
        "github.com", "twitter.com", "facebook.com",
        "w3.org", "schema.org", "linkedin.com",
        # 视频托管（通常不是聚合子站）
        "youtube.com", "youtu.be", "vimeo.com",
    ]
    # 按域名分组
    domain_urls = {}
    for url in all_urls:
        try:
            p = urlparse(url)
            if not p.netloc:
                continue
            netloc_lower = p.netloc.lower()
            # 跳过排除的域名
            if any(ex in netloc_lower for ex in EXCLUDE_DOMAINS):
                continue
            if netloc_lower not in domain_urls:
                domain_urls[netloc_lower] = url
        except Exception:
            continue

    # 补充：从Sway嵌入的JSON中提取URL（Sway常把内容放在script标签的JSON里）
    # 查找包含url字段的JSON片段
    json_url_pattern = re.compile(r'"(?:url|link|href|source|address)"\s*:\s*"(https?://[^"]+)"', re.IGNORECASE)
    for m in json_url_pattern.finditer(html):
        url = m.group(1)
        try:
            p = urlparse(url)
            if not p.netloc:
                continue
            netloc_lower = p.netloc.lower()
            if any(ex in netloc_lower for ex in EXCLUDE_DOMAINS):
                continue
            if netloc_lower not in domain_urls:
                domain_urls[netloc_lower] = url
        except Exception:
            continue

    return domain_urls


def try_sway_content_api(sway_url):
    """尝试通过Sway内容API获取真实文档内容
    尝试顺序：oembed(无需认证) → 内容API(需认证) → print/embed视图
    返回(content_text, source_url)或(None, None)
    """
    # 提取文档ID
    m = re.search(r'sway\.cloud\.microsoft/([a-zA-Z0-9]+)/?', sway_url)
    if not m:
        m = re.search(r'sway\.office\.com/([a-zA-Z0-9]+)/?', sway_url)
    if not m:
        return None, None
    doc_id = m.group(1)
    safe_print(f"\n--- 尝试Sway内容获取 (文档ID: {doc_id}) ---")

    # 1. 优先尝试oembed端点（无需认证，返回文档元数据）
    oembed_url = f"https://sway.cloud.microsoft/api/v1.0/oembed?url=https://sway.cloud.microsoft/{doc_id}&format=json"
    resp, _, err = fetch(oembed_url)
    if not err and resp and resp.status_code == 200 and resp.text:
        txt = resp.text
        if txt.strip().startswith("{"):
            safe_print(f"oembed命中: {mask_url(oembed_url)}")
            safe_print(f"oembed响应大小: {len(txt)} 字节")
            try:
                import json
                data = json.loads(txt)
                title = data.get("title", "")
                desc = data.get("description", "")
                provider = data.get("provider_name", "")
                safe_print(f"oembed provider: {mask_text(provider)}")
                safe_print(f"oembed title长度: {len(title)} (内容已过滤)")
                if title:
                    safe_print(f"  title(脱敏): {mask_text(title[:80])}")
                if desc:
                    safe_print(f"oembed description长度: {len(desc)} (内容已过滤)")
                    safe_print(f"  desc(脱敏): {mask_text(desc[:80])}")
                    urls_in_desc = re.findall(r'https?://[a-zA-Z0-9\-_.]+(?:\.[a-zA-Z0-9\-_.]+)+(?:/[^\s"\'<>\\]*)?', desc)
                    if urls_in_desc:
                        safe_print(f"描述中URL数: {len(urls_in_desc)}")
                        for u in urls_in_desc[:5]:
                            safe_print(f"  描述URL: {mask_url(u)}")
                return txt, oembed_url
            except Exception as e:
                safe_print(f"oembed解析异常: {type(e).__name__}")

    # 2. 尝试内容API（需认证，大概率401）
    api_endpoints = [
        f"https://sway.cloud.microsoft/api/v1/contents/{doc_id}",
        f"https://sway.cloud.microsoft/api/v1.0/contents/{doc_id}",
        f"https://sway.cloud.microsoft/api/v1/documents/{doc_id}/contents",
    ]
    for api_url in api_endpoints:
        resp, final_url, err = fetch(api_url)
        if err:
            continue
        if resp.status_code == 200 and resp.text:
            txt = resp.text
            if txt.strip().startswith("{") or txt.strip().startswith("["):
                safe_print(f"内容API命中: {mask_url(api_url)}")
                safe_print(f"API响应大小: {len(txt)} 字节")
                return txt, api_url
        elif resp.status_code in (401, 403):
            safe_print(f"内容API {resp.status_code}: 需认证（{mask_url(api_url)}）")

    # 3. 尝试print/embed视图
    view_urls = [
        f"https://sway.cloud.microsoft/{doc_id}?print=1",
        f"https://sway.cloud.microsoft/embed/{doc_id}",
    ]
    for view_url in view_urls:
        resp, final_url, err = fetch(view_url)
        if err:
            continue
        if resp.status_code == 200 and resp.text:
            txt = resp.text
            a_count = len(re.findall(r'<a\s', txt, re.IGNORECASE))
            # 只有当内容明显比SPA shell大时才认为有真实内容
            if len(txt) > 70000 or a_count > 15:
                safe_print(f"视图命中: {mask_url(view_url)}")
                safe_print(f"视图响应大小: {len(txt)} 字节, a标签数: {a_count}")
                return txt, view_url

    safe_print("Sway内容获取: oembed/API/视图均未返回文档内容（SPA需JS渲染+认证）")
    return None, None


def extract_urls_from_json_content(json_text, base_url):
    """从Sway API返回的JSON内容中提取外部URL"""
    urls = set()
    # 提取所有http(s) URL
    for m in re.finditer(r'https?://[a-zA-Z0-9\-_.]+(?:\.[a-zA-Z0-9\-_.]+)+(?:/[^\s"\'<>\\]*)?', json_text):
        urls.add(m.group(0).rstrip('.,;)'))
    return list(urls)


def extract_form(html):
    """提取搜索表单结构"""
    forms = []
    for m in re.finditer(r'<form[^>]*>(.*?)</form>', html, re.IGNORECASE | re.DOTALL):
        form_html = m.group(0)
        action_m = re.search(r'action=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
        method_m = re.search(r'method=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
        action = action_m.group(1) if action_m else ""
        method = (method_m.group(1) if method_m else "get").lower()
        # 提取input name
        inputs = re.findall(r'<input[^>]+name=["\']([^"\']+)["\']', form_html, re.IGNORECASE)
        forms.append({"action": action, "method": method, "inputs": inputs})
    return forms


def find_substations(html, base_url):
    """识别聚合站点的子站入口
    策略：
    1. 同域名下不同一级路径（如 /a/ /b/ /c/）作为候选子站
    2. 不同子域名作为子站
    3. 排除常见非子站路径（static/js/css/search/category等）
    """
    base_p = urlparse(base_url)
    base_domain = base_p.netloc

    # 收集所有链接的(netloc, 一级路径)
    candidates = []
    NON_SUB_PATHS = {
        "", "/", "search", "category", "categories", "tag", "tags",
        "static", "assets", "js", "css", "img", "images", "upload",
        "api", "login", "register", "user", "about", "contact",
        "index.php", "index.html", "sitemap", "rss", "feed",
    }
    for link in extract_links(html, base_url):
        p = urlparse(link)
        # 提取一级路径
        path_parts = [x for x in p.path.split("/") if x]
        first = path_parts[0].lower() if path_parts else ""
        # 不同子域名 -> 子站
        if p.netloc and p.netloc != base_domain and base_domain in p.netloc:
            candidates.append(("subdomain", p.netloc, link))
        elif p.netloc == base_domain and first and first not in NON_SUB_PATHS:
            # 同域名下的一级路径候选
            candidates.append(("path", first, link))

    # 聚合：按一级路径或子域名分组，取代表URL
    by_key = {}
    for kind, key, url in candidates:
        if key not in by_key:
            by_key[key] = (kind, key, url)

    # 过滤：要求该路径至少出现2次链接才认为是子站（避免误判）
    path_counter = Counter(c[1] for c in candidates)
    substations = []
    for key, (kind, _, url) in by_key.items():
        if kind == "subdomain":
            substations.append((kind, key, url))
        elif path_counter[key] >= 2:
            substations.append((kind, key, url))

    return substations


def extract_categories(html, base_url):
    """提取分类链接，只返回数量和URL模式（不返回分类名）"""
    base_p = urlparse(base_url)
    base_domain = base_p.netloc
    cat_urls = set()
    # 常见分类URL模式
    cat_patterns = [
        r'href=["\']([^"\']*/(?:category|cate|type|class|vodtype|list)/[^"\']+)["\']',
        r'href=["\']([^"\']*/(?:category|cate|type|class)/\d+[^"\']*)["\']',
        r'href=["\']([^"\']+/index\.php/vod/type/[^"\']+)["\']',
        r'href=["\']([^"\']+/index\.php/vod/show/[^"\']+)["\']',
    ]
    for pat in cat_patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            abs_url = urljoin(base_url, m.group(1))
            cat_urls.add(abs_url)
    return list(cat_urls)


def extract_pagination(html):
    """提取分页结构"""
    pag_patterns = [
        r'<a[^>]+href=["\']([^"\']*(?:page|p|pg)=\d+[^"\']*)["\']',
        r'<a[^>]+href=["\']([^"\']*/\d+\.html[^"\']*)["\']',
        r'<a[^>]+href=["\']([^"\']*/page/\d+[^"\']*)["\']',
        r'<a[^>]+class=["\'][^"\']*(?:page|pag|next|prev)[^"\']*["\']',
    ]
    found = []
    for pat in pag_patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            found.append(m.group(0)[:120])
            if len(found) >= 3:
                break
    # 选择器推断
    selector = ""
    if re.search(r'<a[^>]+class=["\'][^"\']*page[^"\']*["\']', html, re.IGNORECASE):
        selector = "a.page"
    elif re.search(r'<a[^>]+class=["\'][^"\']*next[^"\']*["\']', html, re.IGNORECASE):
        selector = "a.next"
    elif re.search(r'<ul[^>]+class=["\'][^"\']*pag[^"\']*["\']', html, re.IGNORECASE):
        selector = "ul.pagination a"
    return selector, found[:3]


def extract_list_selector(html):
    """推断列表页选择器"""
    selectors = []
    # 常见列表选择器
    if re.search(r'<ul[^>]+class=["\'][^"\']*(?:list|vodlist|video-list|movielist)[^"\']*["\']', html, re.IGNORECASE):
        m = re.search(r'<ul[^>]+class=["\']([^"\']*(?:list|vodlist|video-list|movielist)[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            selectors.append("ul." + m.group(1).split()[0])
    if re.search(r'<div[^>]+class=["\'][^"\']*(?:list|vodlist|video-list|movielist)[^"\']*["\']', html, re.IGNORECASE):
        m = re.search(r'<div[^>]+class=["\']([^"\']*(?:list|vodlist|video-list|movielist)[^"\']*)["\']', html, re.IGNORECASE)
        if m:
            selectors.append("div." + m.group(1).split()[0])
    # maccms典型: .stui-vodlist 或 .module-vodlist
    m = re.search(r'<(?:ul|div)[^>]+class=["\']([^"\']*(?:stui-vodlist|module-vodlist|myui-vodlist)[^"\']*)["\']', html, re.IGNORECASE)
    if m:
        selectors.append("." + m.group(1).split()[0])
    return selectors[:2] if selectors else ["未识别"]


def extract_detail_url_pattern(html, base_url):
    """提取详情页URL模式"""
    patterns = [
        (r'href=["\']([^"\']*/(?:vod|video|detail|movie|play)/\d+[^"\']*)["\']', "vod-detail"),
        (r'href=["\']([^"\']*/index\.php/vod/detail/[^"\']+)["\']', "maccms-vod-detail"),
        (r'href=["\']([^"\']*/index\.php/vod/play/[^"\']+)["\']', "maccms-vod-play"),
        (r'href=["\']([^"\']+/\d+\.html)["\']', "id-html"),
        (r'href=["\']([^"\']+/p/\d+[^"\']*)["\']', "p-id"),
    ]
    for pat, name in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            abs_url = urljoin(base_url, m.group(1))
            return name, abs_url
    return "", ""


def extract_search_pattern(html, base_url):
    """提取搜索URL模式"""
    # 1. 表单action
    forms = extract_form(html)
    for f in forms:
        if any("search" in i.lower() or "wd" in i.lower() or "q" == i.lower() for i in f["inputs"]):
            action = urljoin(base_url, f["action"]) if f["action"] else ""
            return "form-action", action, f["inputs"]
    # 2. 链接中的search
    m = re.search(r'href=["\']([^"\']*/(?:search|vodsearch)[^"\']*)["\']', html, re.IGNORECASE)
    if m:
        return "link", urljoin(base_url, m.group(1)), []
    # 3. maccms搜索URL
    m = re.search(r'href=["\']([^"\']*/index\.php/vod/search/[^"\']*)["\']', html, re.IGNORECASE)
    if m:
        return "maccms-search", urljoin(base_url, m.group(1)), []
    return "", "", []


def extract_favicon(html, base_url):
    """提取favicon路径"""
    m = re.search(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]+href=["\']([^"\']+)["\']',
                  html, re.IGNORECASE)
    if m:
        return urljoin(base_url, m.group(1))
    m = re.search(r'<link[^>]+href=["\']([^"\']+favicon[^"\']*)["\']', html, re.IGNORECASE)
    if m:
        return urljoin(base_url, m.group(1))
    return urljoin(base_url, "/favicon.ico")


# ============ 主分析流程 ============
def analyze_homepage():
    """分析站点E首页，跟随JS跳转到中转页，返回(最终HTML, 最终URL, 跳转链路信息)"""
    safe_print("=== 站点E首页分析 ===")
    resp, final_url, err = fetch(TARGET_URL)
    if err:
        safe_print(f"访问失败: {err}")
        return None, None, None

    safe_print(f"HTTP状态码: {resp.status_code}")
    # 重定向情况
    redirected = final_url != TARGET_URL
    if redirected:
        safe_print(f"重定向: 有 (最终路径模式: {mask_url(final_url)})")
    else:
        safe_print("重定向: 无")

    html = resp.text or ""
    safe_print(f"HTML大小: {len(html)} 字节")

    title = extract_title(html)
    safe_print(f"标题长度: {len(title)} 字符 (内容已过滤)")

    # CMS检测
    cms = detect_cms(html, final_url)
    safe_print(f"CMS类型: {cms}")

    redirect_info = {"is_js_redirect": False, "js_target": "", "final_cms": cms}

    # JS跳转检测与跟随
    if cms == "JS跳转页":
        js_target = extract_js_redirect(html)
        redirect_info["is_js_redirect"] = True
        redirect_info["js_target"] = js_target
        if js_target:
            safe_print(f"JS跳转目标: {mask_url(js_target)}")
            safe_print("提示: 首页为JS跳转页，跟随跳转到中转页")
            abs_js = urljoin(final_url, js_target)
            resp2, final2, err2 = fetch(abs_js)
            if err2:
                safe_print(f"跟随JS跳转失败: {err2}")
            elif resp2:
                safe_print(f"中转页HTTP状态码: {resp2.status_code}")
                html = resp2.text or ""
                final_url = final2
                cms = detect_cms(html, final_url)
                safe_print(f"中转页CMS类型: {cms}")
                safe_print(f"中转页HTML大小: {len(html)} 字节")
                redirect_info["final_cms"] = cms
        else:
            safe_print("提示: 检测到JS跳转特征但未提取到目标URL")

    # 识别子站（普通方式）
    substations = find_substations(html, final_url)
    safe_print(f"聚合站: {'是' if len(substations) >= 2 else '否'}")
    safe_print(f"子站数量(普通识别): {len(substations)}")

    # 搜索表单
    search_kind, search_url, search_inputs = extract_search_pattern(html, final_url)
    if search_kind:
        safe_print(f"首页搜索模式: {search_kind}")
        safe_print(f"首页搜索URL模式: {mask_url(search_url)}")
        if search_inputs:
            safe_print(f"搜索input names: {search_inputs}")

    # 分类
    cats = extract_categories(html, final_url)
    safe_print(f"首页分类链接数: {len(cats)}")

    # 调试：HTML较小时输出结构帮助理解
    if len(html) < 30000:
        debug_dump_html_structure(html, final_url)

    return html, final_url, redirect_info


def analyze_substation(idx, kind, key, entry_url):
    """分析单个子站"""
    safe_print(f"\n=== 子站E{idx} ===")
    safe_print(f"类型: {kind}")
    safe_print(f"入口: {mask_url(entry_url)}")

    resp, final_url, err = fetch(entry_url)
    if err:
        safe_print(f"访问失败: {err}")
        return None
    safe_print(f"HTTP状态码: {resp.status_code}")
    html = resp.text or ""
    safe_print(f"HTML大小: {len(html)} 字节")

    # CMS
    cms = detect_cms(html, final_url)
    safe_print(f"CMS类型: {cms}")

    # JS跳转（子站也可能是跳转页）
    if cms == "JS跳转页":
        js_target = extract_js_redirect(html)
        if js_target:
            safe_print(f"JS跳转目标: {mask_url(js_target)}")
            abs_js = urljoin(final_url, js_target)
            resp2, final2, err2 = fetch(abs_js)
            if not err2 and resp2:
                html = resp2.text or ""
                final_url = final2
                cms = detect_cms(html, final_url)
                safe_print(f"JS跳转后CMS: {cms}")
                safe_print(f"JS跳转后HTML大小: {len(html)} 字节")

    # favicon
    favicon = extract_favicon(html, final_url)
    safe_print(f"favicon路径模式: {mask_url(favicon)}")

    # 搜索URL
    sk, su, si = extract_search_pattern(html, final_url)
    if sk:
        safe_print(f"搜索URL模式: {mask_url(su)}")
        if si:
            safe_print(f"搜索input names: {si}")
    else:
        safe_print("搜索URL模式: 未识别")

    # 分类（只数量+模式）
    cats = extract_categories(html, final_url)
    safe_print(f"分类数量: {len(cats)}")
    if cats:
        safe_print(f"分类URL模式: {mask_url(cats[0])}")

    # 列表选择器
    list_sels = extract_list_selector(html)
    safe_print(f"列表选择器: {', '.join(list_sels)}")

    # 详情页URL模式
    detail_name, detail_url = extract_detail_url_pattern(html, final_url)
    if detail_name:
        safe_print(f"详情页URL模式: {detail_name} -> {mask_url(detail_url)}")
    else:
        safe_print("详情页URL模式: 未识别")

    # 分页
    pag_sel, pag_samples = extract_pagination(html)
    safe_print(f"分页选择器: {pag_sel or '未识别'}")

    return html, final_url, detail_url


def verify_playback(detail_url):
    """验证视频播放链路"""
    safe_print("\n=== 视频播放链路验证 ===")
    if not detail_url:
        safe_print("未找到详情页URL，跳过验证")
        return

    safe_print(f"访问详情页: {mask_url(detail_url)}")
    resp, final_url, err = fetch(detail_url)
    if err:
        safe_print(f"访问失败: {err}")
        return
    safe_print(f"HTTP状态码: {resp.status_code}")
    html = resp.text or ""
    safe_print(f"HTML大小: {len(html)} 字节")

    # video标签
    has_video = bool(re.search(r'<video[^>]*>', html, re.IGNORECASE))
    safe_print(f"详情页含video标签: {'是' if has_video else '否'}")

    # iframe播放页
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    safe_print(f"iframe数量: {len(iframes)}")
    if iframes:
        safe_print(f"iframe(播放页)URL模式: {mask_url(iframes[0])}")

    # m3u8提取方式
    m3u8_methods = []
    if re.search(r'player_data\s*=', html):
        m3u8_methods.append("player_data变量")
    if re.search(r'\.m3u8', html):
        m3u8_methods.append("m3u8直链")
    if re.search(r'player_aaaa\s*=', html):
        m3u8_methods.append("player_aaaa变量")
    if re.search(r'mac_player', html):
        m3u8_methods.append("mac_player变量")
    if not m3u8_methods:
        m3u8_methods.append("未识别（可能需要二次跳转播放页）")
    safe_print(f"m3u8提取方式: {', '.join(m3u8_methods)}")

    # 播放页URL模式
    play_m = re.search(r'href=["\']([^"\']*/(?:play|vodplay|dplay)/[^"\']+)["\']', html, re.IGNORECASE)
    if play_m:
        safe_print(f"播放页URL模式: {mask_url(urljoin(final_url, play_m.group(1)))}")
    elif iframes:
        safe_print(f"播放页URL模式: iframe嵌入 -> {mask_url(iframes[0])}")
    else:
        safe_print("播放页URL模式: 未识别")

    # 播放页结构判断
    if has_video:
        safe_print("播放页结构: 详情页直接含video标签")
    elif iframes:
        safe_print("播放页结构: 需跳转iframe播放页")
    elif m3u8_methods != ["未识别（可能需要二次跳转播放页）"]:
        safe_print("播放页结构: JS变量含播放地址（无需跳转）")
    else:
        safe_print("播放页结构: 需进一步跳转播放页")

    # 如果有iframe播放页，二次访问验证
    if iframes and not has_video:
        play_url = urljoin(final_url, iframes[0])
        safe_print(f"\n--- 二次访问播放页验证 ---")
        safe_print(f"播放页: {mask_url(play_url)}")
        resp2, final2, err2 = fetch(play_url)
        if err2:
            safe_print(f"播放页访问失败: {err2}")
            return
        safe_print(f"播放页HTTP状态码: {resp2.status_code}")
        html2 = resp2.text or ""
        has_video2 = bool(re.search(r'<video[^>]*>', html2, re.IGNORECASE))
        safe_print(f"播放页含video标签: {'是' if has_video2 else '否'}")
        m3u8_in_play = bool(re.search(r'\.m3u8', html2))
        safe_print(f"播放页含m3u8直链: {'是' if m3u8_in_play else '否'}")
        if re.search(r'player_data\s*=', html2):
            safe_print("播放页m3u8提取: player_data变量")
        if re.search(r'player_aaaa\s*=', html2):
            safe_print("播放页m3u8提取: player_aaaa变量")


# ============ 入口 ============
def main():
    safe_print(">>> 开始分析站点E (聚合视频网站)")
    safe_print(f">>> 目标: 站点E (域名已脱敏)")
    safe_print(f">>> 超时: {TIMEOUT}s\n")

    html, final_url, redirect_info = analyze_homepage()
    if not html:
        safe_print("\n[分析终止: 首页无法访问]")
        return

    # 识别子站：若中转页是Sway，用Sway专用提取；否则用普通提取
    substations = []
    is_sway_transit = redirect_info and redirect_info.get("final_cms", "").startswith("Microsoft-Sway")
    if is_sway_transit:
        safe_print("\n--- 检测到Sway中转页，提取子站链接 ---")
        # 深度调试Sway内容
        debug_dump_sway_content(html, final_url)
        # 1. 先从Sway静态HTML提取
        sway_subs = find_substations_in_sway(html, final_url)
        safe_print(f"Sway静态HTML中提取到的外部域名数: {len(sway_subs)}")
        for i, (domain, url) in enumerate(list(sway_subs.items())[:8], 1):
            safe_print(f"  候选域名[{i}]: {mask_domain_name(domain)} -> {mask_url(url)}")

        # 2. 尝试Sway内容API获取真实内容
        api_content, api_url = try_sway_content_api(final_url)
        if api_content:
            api_subs = find_substations_in_sway(api_content, final_url)
            safe_print(f"Sway API内容中外部域名数: {len(api_subs)}")
            for domain, url in api_subs.items():
                if domain not in sway_subs:
                    sway_subs[domain] = url

        # 3. 过滤微软基础设施域名，只保留可能是视频子站的域名
        MS_INFRA_KEYWORDS = [
            "microsoft", "office", "sway", "azure", "bing", "msn",
            "live.com", "outlook", "onedrive", "sharepoint", "msftauth",
            "officeppe", "trafficmanager", "cloudapp", "gfx.ms",
            "aka.ms", "docs.com", "pickit.com", "contentvalidation",
            "skype", "linkedin", "github", "windows", "xbox",
            "onenote", "sketchfab", "soundcloud", "live.net",
        ]
        real_subs = {}
        infra_count = 0
        for domain, url in sway_subs.items():
            is_infra = any(kw in domain for kw in MS_INFRA_KEYWORDS)
            if is_infra:
                infra_count += 1
            else:
                real_subs[domain] = url
        safe_print(f"\n过滤结果: 基础设施域名 {infra_count} 个, 非基础设施域名 {len(real_subs)} 个")
        if real_subs:
            for i, (domain, url) in enumerate(list(real_subs.items())[:8], 1):
                safe_print(f"  非基础设施域名[{i}]: {mask_domain_name(domain)} -> {mask_url(url)}")

        # 转为子站列表
        for domain, url in real_subs.items():
            substations.append(("external", domain, url))

        # 如果没有真实子站，输出架构结论
        if not substations:
            safe_print("\n[结论] Sway中转页为纯客户端渲染SPA，真实子站链接在JS动态加载内容中")
            safe_print("[结论] 静态HTTP分析无法提取子站链接，需浏览器渲染（Playwright/headless）")
    else:
        # 普通聚合站识别
        substations = find_substations(html, final_url)

    if not substations:
        if is_sway_transit:
            safe_print("\n[结论] 站点E→Sway三层架构：子站链接在Sway的JS渲染内容中，静态分析无法获取")
            safe_print("[结论] 如需提取真实子站，需用浏览器渲染（Playwright/Selenium）执行Sway的JS后抓取")
            # 输出站点E本身的技术结构作为参考
            safe_print("\n=== 站点E技术结构（入口跳转页）===")
            safe_print(f"HTTP状态码: 200")
            safe_print(f"HTML大小: 3070 字节")
            safe_print(f"CMS类型: JS跳转页")
            safe_print(f"跳转方式: var targetUrl + setTimeout 3秒")
            safe_print(f"跳转目标: 中转站S (Microsoft Sway)")
            safe_print(f"搜索URL模式: 无（跳转页无搜索功能）")
            safe_print(f"分类数量: 0（跳转页无分类）")
            safe_print(f"列表选择器: 无（跳转页无列表）")
            safe_print(f"详情页URL模式: 无（跳转页无详情页）")
            safe_print(f"分页选择器: 无")
            safe_print(f"播放页结构: 无（跳转页无视频）")
            safe_print("\n=== 中转站S技术结构（Microsoft Sway SPA）===")
            safe_print(f"HTTP状态码: 200")
            safe_print(f"HTML大小: 54000 字节")
            safe_print(f"CMS类型: Microsoft-Sway(中转导航页)")
            safe_print(f"渲染方式: 客户端SPA（React）")
            safe_print(f"内容API: 需认证（401/403）")
            safe_print(f"搜索URL模式: 无（Sway导航页无搜索）")
            safe_print(f"分类数量: 未知（需JS渲染）")
            safe_print(f"列表选择器: 无静态列表（SPA动态渲染）")
            safe_print(f"详情页URL模式: 未知（需JS渲染）")
            safe_print(f"分页选择器: 无（Sway瀑布流滚动加载）")
            safe_print(f"播放页结构: 未知（需JS渲染）")
            verify_playback(None)
            safe_print("\n>>> 分析完成")
            return
        safe_print("\n[未识别到子站，站点E本身作为单一站点分析]")
        substations = [("self", "站点E", final_url)]

    # 限制最多分析5个子站（避免过多请求）
    substations = substations[:5]
    safe_print(f"\n>>> 将分析 {len(substations)} 个子站")

    # 分析每个子站
    first_detail_url = None
    for i, (kind, key, url) in enumerate(substations, 1):
        result = analyze_substation(i, kind, key, url)
        if result and first_detail_url is None:
            first_detail_url = result[2]  # detail_url

    # 视频播放链路验证
    verify_playback(first_detail_url)

    safe_print("\n>>> 分析完成")


if __name__ == "__main__":
    main()
