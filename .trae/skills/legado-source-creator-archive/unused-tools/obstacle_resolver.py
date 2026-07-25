#!/usr/bin/env python3
"""
obstacle_resolver.py - 障碍场景辅助模块

合并 7.1 登录辅助 + 7.2 CF破盾 + 7.3 验证码辅助。
当 debug-source.py 检测到登录需求/CF盾/验证码时，主动尝试辅助，
辅助失败再标记 unverifiable。

可选依赖（未安装时自动降级到手动模式，不报错）:
    - requests      : HTTP 请求
    - cloudscraper  : CF Challenge 自动求解
    - ddddocr       : 图形验证码 OCR

用法:
    from obstacle_resolver import resolve_obstacle
    result = resolve_obstacle(url, html, "cf")
    if result.success:
        cookie_store = result.cookie_store
"""

import json
import os
import re
import sys
import time
import urllib.parse

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 可选依赖：requests
try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None

# 可选依赖：cloudscraper（CF破盾）
try:
    import cloudscraper
except ImportError:
    cloudscraper = None

# 可选依赖：ddddocr（验证码OCR）
try:
    import ddddocr
except ImportError:
    ddddocr = None


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 路径常量（迁移自 tools/，通过相对路径回到 tools/ 目录以保持缓存位置不变）
_TOOLS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools')
)
COOKIE_CACHE_DIR = os.path.join(_TOOLS_DIR, ".cookie-cache")
CAPTCHA_CACHE_DIR = os.path.join(_TOOLS_DIR, ".captcha-cache")

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# ResolveResult
# ---------------------------------------------------------------------------

class ResolveResult:
    """障碍解决结果"""

    def __init__(self, success=False, method=None, cookie_store=None,
                 html=None, message="", log=None):
        self.success = success
        self.method = method        # cookie_import/form_login/oauth_mark/auto_cf/manual_cf/ocr/export_image
        self.cookie_store = cookie_store or {}
        self.html = html            # 破盾后的新HTML（CF场景）
        self.message = message
        self.log = log or []

    def to_dict(self):
        return {
            "success": self.success,
            "method": self.method,
            "message": self.message,
            "html_length": len(self.html) if self.html else 0,
            "log": self.log,
        }


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def _get_domain(url):
    """从URL提取域名（netloc）"""
    return urllib.parse.urlparse(url).netloc


def _safe_filename(name):
    """将字符串转为安全文件名"""
    return re.sub(r'[^\w.-]', '_', name)


def _parse_cookie_str(cookie_str):
    """将 'k1=v1; k2=v2' 解析为 dict"""
    cookies = {}
    if not cookie_str:
        return cookies
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def _cookie_dict_to_str(cookie_dict):
    """dict 转 'k1=v1; k2=v2'"""
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items())


# ===========================================================================
# 7.1 登录辅助
# ===========================================================================

def analyze_login_form(html):
    """解析HTML中的登录表单，返回表单字段清单。

    Returns:
        dict | None: {action, method, inputs:[{name,type,value}], has_password}
    """
    if not html:
        return None

    form_pattern = re.compile(r'<form[^>]*>(.*?)</form>', re.DOTALL | re.IGNORECASE)
    input_pattern = re.compile(r'<input[^>]*>', re.IGNORECASE)

    for form_match in form_pattern.finditer(html):
        # 提取 form 标签属性（action/method）
        form_tag = html[form_match.start():form_match.start() + 200]
        action = ""
        method = "get"
        action_m = re.search(r'action=["\']([^"\']*)["\']', form_tag, re.IGNORECASE)
        method_m = re.search(r'method=["\']([^"\']*)["\']', form_tag, re.IGNORECASE)
        if action_m:
            action = action_m.group(1)
        if method_m:
            method = method_m.group(1).lower()

        # 解析所有 input
        form_html = form_match.group(1)
        inputs = []
        has_password = False
        for inp in input_pattern.finditer(form_html):
            inp_html = inp.group(0)
            name_m = re.search(r'name=["\']([^"\']*)["\']', inp_html, re.IGNORECASE)
            type_m = re.search(r'type=["\']([^"\']*)["\']', inp_html, re.IGNORECASE)
            value_m = re.search(r'value=["\']([^"\']*)["\']', inp_html, re.IGNORECASE)
            name = name_m.group(1) if name_m else ""
            inp_type = type_m.group(1).lower() if type_m else "text"
            value = value_m.group(1) if value_m else ""
            if inp_type == "password":
                has_password = True
            if name:
                inputs.append({"name": name, "type": inp_type, "value": value})

        if has_password:
            return {
                "action": action,
                "method": method,
                "inputs": inputs,
                "has_password": True,
            }
    return None


def prompt_user_for_cookie(url):
    """交互式引导用户提供浏览器Cookie（提示F12->Network->复制Cookie）"""
    domain = _get_domain(url)
    print(f"\n{'=' * 60}")
    print(f"登录辅助 - 需要提供 Cookie")
    print(f"{'=' * 60}")
    print(f"目标站点: {domain}")
    print(f"\n请按以下步骤获取 Cookie:")
    print(f"  1. 在浏览器中打开: {url}")
    print(f"  2. 登录你的账号")
    print(f"  3. 按 F12 打开开发者工具")
    print(f"  4. 切换到 Network 标签页")
    print(f"  5. 刷新页面，点击任意请求")
    print(f"  6. 在 Request Headers 中找到 Cookie 字段")
    print(f"  7. 复制完整的 Cookie 值")
    print(f"\n请粘贴 Cookie（直接回车跳过）:")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def detect_login_failure(response):
    """检测登录态失效：重定向到登录页/401/登录JSON。

    Args:
        response: requests.Response 对象

    Returns:
        bool: True 表示登录态失效
    """
    # 401 状态码
    if response.status_code == 401:
        return True
    # 3xx 重定向到登录页
    if 300 <= response.status_code < 400:
        location = response.headers.get("Location", "")
        if re.search(r'login|signin|auth', location, re.IGNORECASE):
            return True
    # 最终 URL 含 login
    final_url = getattr(response, "url", "") or ""
    if final_url and re.search(r'login|signin|auth', final_url, re.IGNORECASE):
        return True
    # 响应体是登录JSON或含登录表单
    try:
        body = response.text[:500]
    except Exception:
        body = ""
    if body:
        if re.search(r'"code"\s*:\s*401', body) and \
           re.search(r'login|未登录|unauthorized', body, re.IGNORECASE):
            return True
        if re.search(r'<form[^>]*login', body, re.IGNORECASE):
            return True
    return False


def verify_login_success(url, cookie_store):
    """请求登录态页面，检测是否重定向到登录页/返回401/返回登录JSON。

    Args:
        url: 登录态页面URL
        cookie_store: dict[domain] = cookie_str

    Returns:
        bool: True 表示登录态正常
    """
    if requests is None:
        return False
    domain = _get_domain(url)
    cookie_str = (cookie_store or {}).get(domain, "")
    if not cookie_str:
        return False
    headers = {"User-Agent": DEFAULT_UA, "Cookie": cookie_str}
    try:
        resp = requests.get(url, headers=headers, timeout=15,
                            allow_redirects=False, verify=False)
    except requests.RequestException:
        return False
    return not detect_login_failure(resp)


def persist_cookie(url, cookie_str):
    """Cookie持久化到 tools/.cookie-cache/{domain}.json。

    Returns:
        str | None: 保存的文件路径，失败返回 None
    """
    _ensure_dir(COOKIE_CACHE_DIR)
    domain = _get_domain(url)
    cache_file = os.path.join(COOKIE_CACHE_DIR, f"{_safe_filename(domain)}.json")
    data = {
        "domain": domain,
        "cookie": cookie_str,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return cache_file
    except OSError:
        return None


def assist_login(url, html, cookie_store=None):
    """登录主函数：三层策略（Cookie导入->表单登录->OAuth标记）。

    Args:
        url: 目标URL
        html: 页面HTML
        cookie_store: dict[domain] = cookie_str

    Returns:
        ResolveResult
    """
    log = []
    cs = dict(cookie_store) if cookie_store else {}
    domain = _get_domain(url)

    # 第一层：Cookie 缓存导入
    cache_file = os.path.join(COOKIE_CACHE_DIR, f"{_safe_filename(domain)}.json")
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_cookie = data.get("cookie", "")
            if cached_cookie:
                cs[domain] = cached_cookie
                log.append("[login] 命中Cookie缓存，验证登录态")
                if verify_login_success(url, cs):
                    log.append("[login] 缓存Cookie有效，登录态正常")
                    return ResolveResult(True, "cookie_import", cs,
                                         message="Cookie缓存导入成功", log=log)
                log.append("[login] 缓存Cookie已失效")
        except (OSError, ValueError):
            pass

    # 第二层：表单登录（解析表单 + 引导用户导入Cookie）
    form = analyze_login_form(html)
    if form:
        log.append(f"[login] 检测到登录表单: action={form['action']}, method={form['method']}")
        log.append(f"[login] 表单字段: {[i['name'] for i in form['inputs']]}")
        # 简化说明：CLI 无法安全代用户提交凭据，引导用户在浏览器登录后导入 Cookie
        cookie_str = prompt_user_for_cookie(url)
        if cookie_str:
            cs[domain] = cookie_str
            persist_cookie(url, cookie_str)
            if verify_login_success(url, cs):
                log.append("[login] 用户导入Cookie验证成功")
                return ResolveResult(True, "cookie_import", cs,
                                     message="用户Cookie导入成功", log=log)
            log.append("[login] 用户导入Cookie验证失败")
            return ResolveResult(False, "cookie_import", cs,
                                 message="Cookie导入但验证失败", log=log)
        log.append("[login] 用户未提供Cookie")
    else:
        log.append("[login] 未检测到登录表单")

    # 第三层：OAuth 标记（无表单，可能是OAuth站点）
    log.append("[login] 标记为OAuth/需手工登录站点")
    return ResolveResult(False, "oauth_mark", cs,
                         message="需OAuth或手工登录，无法自动辅助", log=log)


# ===========================================================================
# 7.2 CF破盾辅助
# ===========================================================================

def is_cf_challenge(html):
    """检测CF Challenge页面特征（cf-browser-verification/jschl_vc/__cf_chl_jschl_tk__等）。

    Returns:
        bool: True 表示是CF挑战页
    """
    if not html:
        return False
    signatures = [
        "cf-browser-verification",
        "jschl_vc",
        "__cf_chl_jschl_tk__",
        "cf_chl_opt",
        "_cf_chl_rt_tk",
        "challenge-platform",
        "Just a moment",
        "Checking your browser",
        "cdn-cgi/challenge",
        "cf-challenge",
        "Performance & security by Cloudflare",
    ]
    return any(sig in html for sig in signatures)


def bypass_cf_auto(url):
    """集成cloudscraper自动求解简单CF Challenge（5秒等待类）。

    cloudscraper 是可选依赖，未安装时返回 None。

    Returns:
        requests.Response | None: 破盾成功的响应，失败返回 None
    """
    if cloudscraper is None:
        return None
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        resp = scraper.get(url, timeout=30)
        if resp.status_code == 200 and not is_cf_challenge(resp.text):
            return resp
    except Exception:
        pass
    return None


def extract_cf_cookie(response):
    """从破盾成功的响应中提取cf_clearance/cf_chl_ Cookie。

    Returns:
        dict: {cookie_name: cookie_value}
    """
    cookies = {}
    try:
        for name, value in response.cookies.items():
            if name.startswith("cf_") or "clearance" in name or "chl" in name:
                cookies[name] = value
    except Exception:
        pass
    set_cookie = response.headers.get("Set-Cookie", "")
    if set_cookie:
        for pair in set_cookie.split(","):
            m = re.match(r'\s*(cf_\w+|__cf_\w+)=([^;]+)', pair)
            if m:
                cookies[m.group(1)] = m.group(2)
    return cookies


def bypass_cf_manual(url, cookie_store=None):
    """交互式引导用户手动破盾并导入Cookie。

    Returns:
        ResolveResult
    """
    domain = _get_domain(url)
    print(f"\n{'=' * 60}")
    print(f"CF破盾辅助 - 需要手动破盾")
    print(f"{'=' * 60}")
    print(f"目标站点: {domain}")
    print(f"\nCloudflare 防护无法自动绕过，请手动破盾:")
    print(f"  1. 在浏览器中打开: {url}")
    print(f"  2. 等待 5 秒挑战自动完成")
    print(f"  3. 页面正常显示后，按 F12 -> Network")
    print(f"  4. 刷新页面，点击主文档请求")
    print(f"  5. 在 Request Headers 中复制完整 Cookie")
    print(f"     （重点找 cf_clearance 字段）")
    print(f"\n请粘贴 Cookie（直接回车跳过）:")
    try:
        cookie_str = input().strip()
    except (EOFError, KeyboardInterrupt):
        return ResolveResult(False, "manual_cf", cookie_store or {},
                             message="用户取消", log=[])
    if not cookie_str:
        return ResolveResult(False, "manual_cf", cookie_store or {},
                             message="用户未提供Cookie", log=[])
    cs = dict(cookie_store) if cookie_store else {}
    cs[domain] = cookie_str
    persist_cookie(url, cookie_str)
    return ResolveResult(True, "manual_cf", cs,
                         message="手动破盾Cookie导入成功",
                         log=["[cf] 手动破盾Cookie已导入并持久化"])


def bypass_cf(url, html, cookie_store=None):
    """CF破盾主函数：自动求解优先，失败降级到手动导入。

    Args:
        url: 目标URL
        html: 页面HTML（用于确认是CF挑战页）
        cookie_store: dict[domain] = cookie_str

    Returns:
        ResolveResult
    """
    log = []
    cs = dict(cookie_store) if cookie_store else {}
    domain = _get_domain(url)

    # 优先检查Cookie缓存（含cf_clearance）
    cache_file = os.path.join(COOKIE_CACHE_DIR, f"{_safe_filename(domain)}.json")
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached = data.get("cookie", "")
            if cached and "cf_clearance" in cached:
                cs[domain] = cached
                log.append("[cf] 命中含cf_clearance的Cookie缓存")
                return ResolveResult(True, "cookie_import", cs,
                                     message="CF Cookie缓存命中", log=log)
        except (OSError, ValueError):
            pass

    # 自动求解
    if cloudscraper is not None:
        log.append("[cf] 尝试 cloudscraper 自动破盾")
        resp = bypass_cf_auto(url)
        if resp is not None:
            cf_cookies = extract_cf_cookie(resp)
            if cf_cookies:
                existing = _parse_cookie_str(cs.get(domain, ""))
                existing.update(cf_cookies)
                cs[domain] = _cookie_dict_to_str(existing)
                persist_cookie(url, cs[domain])
                log.append(f"[cf] 自动破盾成功，提取Cookie: {list(cf_cookies.keys())}")
                return ResolveResult(True, "auto_cf", cs, html=resp.text,
                                     message="cloudscraper自动破盾成功", log=log)
            log.append("[cf] 自动破盾成功但未提取到cf Cookie")
            return ResolveResult(True, "auto_cf", cs, html=resp.text,
                                 message="自动破盾成功", log=log)
        log.append("[cf] cloudscraper 自动破盾失败")
    else:
        log.append("[cf] cloudscraper 未安装，跳过自动破盾")

    # 降级到手动
    result = bypass_cf_manual(url, cs)
    result.log = log + result.log
    return result


# ===========================================================================
# 7.3 验证码辅助
# ===========================================================================

def identify_captcha_type(html):
    """识别验证码类型：image/slider/click/behavior/unknown。

    Returns:
        str: 验证码类型
    """
    if not html:
        return "unknown"
    if re.search(r'<img[^>]*captcha|captcha\.(?:png|jpg|gif)|verifyCode|vcode', html, re.IGNORECASE):
        return "image"
    if re.search(r'slider|slide-block|nc_iconfont|geetest|极验|滑块', html, re.IGNORECASE):
        return "slider"
    if re.search(r'click.*captcha|captcha.*click|点选|文字点选', html, re.IGNORECASE):
        return "click"
    if re.search(r'behavior|fingerprint|指纹|无感验证', html, re.IGNORECASE):
        return "behavior"
    return "unknown"


def ocr_image_captcha(img_bytes):
    """集成ddddocr识别简单图形验证码（4-6位字母数字）。

    ddddocr 是可选依赖，未安装时返回 None。

    Returns:
        str | None: 识别结果，失败返回 None
    """
    if ddddocr is None:
        return None
    try:
        ocr = ddddocr.DdddOcr(show_ad=False)
        result = ocr.classification(img_bytes)
        result = re.sub(r'[^a-zA-Z0-9]', '', result)
        return result if result else None
    except Exception:
        return None


def export_captcha_image(img_bytes, timestamp=None):
    """导出验证码图片到 tools/.captcha-cache/{timestamp}.png。

    Returns:
        str | None: 保存的文件路径，失败返回 None
    """
    _ensure_dir(CAPTCHA_CACHE_DIR)
    if timestamp is None:
        timestamp = int(time.time())
    img_path = os.path.join(CAPTCHA_CACHE_DIR, f"{timestamp}.png")
    try:
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        return img_path
    except OSError:
        return None


def _extract_captcha_img_url(html):
    """从HTML中提取验证码图片URL"""
    m = re.search(
        r'<img[^>]*src=["\']([^"\']*(?:captcha|verifyCode|vcode|code)[^"\']*)["\']',
        html, re.IGNORECASE,
    )
    return m.group(1) if m else None


def _download_captcha_image(img_url, cookie_store, base_url):
    """下载验证码图片"""
    if requests is None:
        return None
    if not img_url.startswith("http"):
        img_url = urllib.parse.urljoin(base_url, img_url)
    domain = _get_domain(base_url)
    headers = {"User-Agent": DEFAULT_UA}
    cookie_str = (cookie_store or {}).get(domain, "")
    if cookie_str:
        headers["Cookie"] = cookie_str
    try:
        resp = requests.get(img_url, headers=headers, timeout=15, verify=False)
        if resp.ok:
            return resp.content
    except requests.RequestException:
        pass
    return None


def assist_captcha(url, html, cookie_store=None):
    """验证码主函数：OCR优先，失败降级到图片导出。

    Args:
        url: 目标URL
        html: 页面HTML
        cookie_store: dict[domain] = cookie_str

    Returns:
        ResolveResult
    """
    log = []
    cs = dict(cookie_store) if cookie_store else {}

    captcha_type = identify_captcha_type(html)
    log.append(f"[captcha] 识别验证码类型: {captcha_type}")

    if captcha_type != "image":
        log.append(f"[captcha] 非 图形验证码({captcha_type})，无法OCR，需手工处理")
        return ResolveResult(False, "export_image", cs,
                             message=f"验证码类型 {captcha_type} 无法自动识别", log=log)

    img_url = _extract_captcha_img_url(html)
    if not img_url:
        log.append("[captcha] 未找到验证码图片URL")
        return ResolveResult(False, "export_image", cs,
                             message="未找到验证码图片", log=log)

    img_bytes = _download_captcha_image(img_url, cs, url)
    if not img_bytes:
        log.append(f"[captcha] 验证码图片下载失败: {img_url}")
        return ResolveResult(False, "export_image", cs,
                             message="验证码图片下载失败", log=log)

    # OCR优先
    if ddddocr is not None:
        code = ocr_image_captcha(img_bytes)
        if code:
            log.append(f"[captcha] OCR识别结果: {code}")
            cs["_captcha_code"] = code
            return ResolveResult(True, "ocr", cs,
                                 message=f"OCR识别成功: {code}", log=log)
        log.append("[captcha] OCR识别失败")
    else:
        log.append("[captcha] ddddocr 未安装，跳过OCR")

    # 降级到图片导出
    ts = int(time.time())
    img_path = export_captcha_image(img_bytes, ts)
    if img_path:
        log.append(f"[captcha] 验证码图片已导出: {img_path}")
        print(f"\n验证码图片已保存: {img_path}")
        print(f"   请手动查看并输入验证码（直接回车跳过）:")
        try:
            code = input().strip()
            if code:
                cs["_captcha_code"] = code
                return ResolveResult(True, "export_image", cs,
                                     message=f"手工识别: {code}", log=log)
        except (EOFError, KeyboardInterrupt):
            pass
        return ResolveResult(False, "export_image", cs,
                             message="图片已导出但未输入验证码", log=log)

    return ResolveResult(False, "export_image", cs,
                         message="图片导出失败", log=log)


# ===========================================================================
# 统一入口
# ===========================================================================

def resolve_obstacle(url, html, obstacle_type, cookie_store=None):
    """统一障碍解决入口，根据obstacle_type调用对应辅助函数。

    Args:
        url: 目标URL
        html: 页面HTML
        obstacle_type: 障碍类型 login/cf/captcha
        cookie_store: dict[domain] = cookie_str

    Returns:
        ResolveResult
    """
    obstacle_type = (obstacle_type or "").lower()
    if obstacle_type == "login":
        return assist_login(url, html, cookie_store)
    if obstacle_type == "cf":
        return bypass_cf(url, html, cookie_store)
    if obstacle_type == "captcha":
        return assist_captcha(url, html, cookie_store)
    return ResolveResult(False, None, cookie_store or {},
                         message=f"未知障碍类型: {obstacle_type}", log=[])


# ===========================================================================
# 自检（纯逻辑函数，无需网络/交互）
# ===========================================================================

def _self_test():
    """最小自检：覆盖纯逻辑函数的正常+边界用例"""
    # 1. analyze_login_form - 正常用例
    html_with_form = (
        '<form action="/login" method="post">'
        '<input type="text" name="username" value="">'
        '<input type="password" name="password">'
        '<input type="hidden" name="csrf" value="abc">'
        '</form>'
    )
    form = analyze_login_form(html_with_form)
    assert form is not None, "应解析到登录表单"
    assert form["action"] == "/login"
    assert form["method"] == "post"
    assert form["has_password"] is True
    names = [i["name"] for i in form["inputs"]]
    assert "username" in names and "password" in names and "csrf" in names
    # 边界用例：无表单 / 表单无password
    assert analyze_login_form("<div>no form</div>") is None
    assert analyze_login_form('<form><input name="q"></form>') is None

    # 2. is_cf_challenge - 正常用例 + 边界
    assert is_cf_challenge("<html>Just a moment...</html>") is True
    assert is_cf_challenge('<div id="cf-browser-verification"></div>') is True
    assert is_cf_challenge("") is False
    assert is_cf_challenge(None) is False
    assert is_cf_challenge("<html>normal page</html>") is False

    # 3. identify_captcha_type - 正常用例 + 边界
    assert identify_captcha_type('<img src="/captcha.png">') == "image"
    assert identify_captcha_type('<div class="slider">slide</div>') == "slider"
    assert identify_captcha_type("") == "unknown"
    assert identify_captcha_type(None) == "unknown"
    assert identify_captcha_type("<div>no captcha</div>") == "unknown"

    # 4. _parse_cookie_str / _cookie_dict_to_str 互转 + 边界
    d = _parse_cookie_str("k1=v1; k2=v2")
    assert d == {"k1": "v1", "k2": "v2"}
    assert _cookie_dict_to_str(d) == "k1=v1; k2=v2"
    assert _parse_cookie_str("") == {}
    assert _parse_cookie_str(None) == {}
    assert _cookie_dict_to_str({}) == ""

    # 5. detect_login_failure - 模拟 response
    class _FakeResp:
        def __init__(self, status, headers=None, url="", text=""):
            self.status_code = status
            self.headers = headers or {}
            self.url = url
            self.text = text
    assert detect_login_failure(_FakeResp(401)) is True
    assert detect_login_failure(_FakeResp(302, headers={"Location": "/login"})) is True
    assert detect_login_failure(_FakeResp(200, url="/user/home")) is False
    assert detect_login_failure(_FakeResp(200, text='{"code":401,"msg":"未登录"}')) is True

    # 6. resolve_obstacle - 未知类型
    r = resolve_obstacle("http://x.com", "", "unknown_type")
    assert r.success is False
    assert "未知障碍类型" in r.message

    print("[self_test] 全部通过 (6 组用例)")


if __name__ == "__main__":
    _self_test()
