#!/usr/bin/env python3
"""
error_translator.py - 8.5 用户体验增强：错误翻译

将技术性错误信息翻译为用户可理解的语言，并给出修复建议。
支持错误分级（致命/严重/警告/提示四级），便于 UI 着色展示。

用法:
    from error_translator import translate_error, classify_error_level
    msg = translate_error("ConnectionError: Failed to establish a connection")
    level = classify_error_level("SSL: CERTIFICATE_VERIFY_FAILED")
"""

import sys

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 错误分级
# ---------------------------------------------------------------------------

# 四级错误：致命(红)/严重(橙)/警告(黄)/提示(蓝)
LEVEL_FATAL = "fatal"      # 致命：流程无法继续
LEVEL_SEVERE = "severe"    # 严重：当前步骤失败，可降级
LEVEL_WARNING = "warning"  # 警告：部分功能受影响
LEVEL_INFO = "info"        # 提示：不影响主流程

LEVEL_LABELS = {
    LEVEL_FATAL: "致命",
    LEVEL_SEVERE: "严重",
    LEVEL_WARNING: "警告",
    LEVEL_INFO: "提示",
}


# ---------------------------------------------------------------------------
# 错误翻译表（技术错误关键词 -> 用户友好描述 + 修复建议 + 默认级别）
# ---------------------------------------------------------------------------

# 每条：{friendly: 用户友好描述, suggestion: 修复建议, level: 默认级别}
ERROR_TRANSLATIONS = {
    # --- 网络连接类 ---
    "ConnectionError": {
        "friendly": "无法连接到目标网站",
        "suggestion": "请检查网络连接是否正常，或目标网站是否可访问",
        "level": LEVEL_SEVERE,
    },
    "连接被拒绝": {
        "friendly": "目标网站拒绝了连接请求",
        "suggestion": "网站可能暂时不可用或封禁了当前 IP，稍后重试或更换网络环境",
        "level": LEVEL_SEVERE,
    },
    "Timeout": {
        "friendly": "请求超时，网站响应过慢",
        "suggestion": "增加请求超时时间，或检查网络连接质量",
        "level": LEVEL_WARNING,
    },
    "超时": {
        "friendly": "操作超时",
        "suggestion": "目标站点响应过慢，建议增加超时时间或稍后重试",
        "level": LEVEL_WARNING,
    },
    "MaxRetryError": {
        "friendly": "多次重试后仍无法连接",
        "suggestion": "网站可能不可达，检查 URL 是否正确或网络是否通畅",
        "level": LEVEL_SEVERE,
    },
    "TooManyRedirects": {
        "friendly": "页面重定向次数过多",
        "suggestion": "网站可能存在重定向循环，检查 URL 或提供正确的 Cookie",
        "level": LEVEL_WARNING,
    },
    "DNS": {
        "friendly": "域名解析失败",
        "suggestion": "检查 URL 域名是否拼写正确，或本机 DNS 配置是否正常",
        "level": LEVEL_SEVERE,
    },
    "Network unreachable": {
        "friendly": "网络不可达",
        "suggestion": "本机网络未连接，请检查网络后重试",
        "level": LEVEL_FATAL,
    },

    # --- HTTP 状态码类 ---
    "404": {
        "friendly": "目标页面不存在（404）",
        "suggestion": "URL 已失效或书源配置的地址有误，请核实书源 URL",
        "level": LEVEL_WARNING,
    },
    "403": {
        "friendly": "访问被拒绝（403）",
        "suggestion": "网站需要登录或限制了访问，请提供 Cookie 或更换 User-Agent",
        "level": LEVEL_SEVERE,
    },
    "401": {
        "friendly": "未授权访问（401）",
        "suggestion": "需要登录后才能访问，请导入登录 Cookie",
        "level": LEVEL_SEVERE,
    },
    "500": {
        "friendly": "网站服务器内部错误（500）",
        "suggestion": "目标网站服务异常，稍后重试",
        "level": LEVEL_WARNING,
    },
    "502": {
        "friendly": "网关错误（502）",
        "suggestion": "网站网关异常，稍后重试",
        "level": LEVEL_WARNING,
    },
    "503": {
        "friendly": "服务暂时不可用（503）",
        "suggestion": "网站维护中或过载，稍后重试",
        "level": LEVEL_WARNING,
    },

    # --- SSL/证书类 ---
    "SSL": {
        "friendly": "SSL 证书验证失败",
        "suggestion": "网站证书有问题，可在请求中关闭 SSL 验证（verify=False）",
        "level": LEVEL_WARNING,
    },
    "CERTIFICATE_VERIFY_FAILED": {
        "friendly": "SSL 证书验证失败",
        "suggestion": "网站证书过期或不被信任，可关闭 SSL 验证后重试",
        "level": LEVEL_WARNING,
    },

    # --- 解析类 ---
    "JSONDecodeError": {
        "friendly": "JSON 数据解析失败",
        "suggestion": "返回内容不是合法 JSON，检查接口是否返回了 HTML 错误页",
        "level": LEVEL_SEVERE,
    },
    "UnicodeDecodeError": {
        "friendly": "文本编码解析失败",
        "suggestion": "页面编码可能不是 UTF-8，尝试指定 encoding（如 GBK）",
        "level": LEVEL_WARNING,
    },
    "No matching": {
        "friendly": "规则未匹配到任何内容",
        "suggestion": "CSS/XPath 选择器可能已失效，请到网站核实页面结构后更新规则",
        "level": LEVEL_SEVERE,
    },
    "空": {
        "friendly": "解析结果为空",
        "suggestion": "规则未匹配到内容，或目标页面无数据，请检查规则与页面结构",
        "level": LEVEL_WARNING,
    },

    # --- 障碍场景类 ---
    "Cloudflare": {
        "friendly": "遇到 Cloudflare 防护",
        "suggestion": "网站启用了 CF 防护，请手动破盾后导入 cf_clearance Cookie",
        "level": LEVEL_SEVERE,
    },
    "cf_clearance": {
        "friendly": "Cloudflare 验证 Cookie 缺失",
        "suggestion": "请手动破盾并导入含 cf_clearance 的 Cookie",
        "level": LEVEL_SEVERE,
    },
    "captcha": {
        "friendly": "遇到验证码",
        "suggestion": "需识别验证码，安装 ddddocr 可自动识别，或手动输入",
        "level": LEVEL_WARNING,
    },
    "验证码": {
        "friendly": "遇到验证码",
        "suggestion": "需识别验证码，安装 ddddocr 可自动识别，或手动输入",
        "level": LEVEL_WARNING,
    },
    "Cookie": {
        "friendly": "Cookie 缺失或已过期",
        "suggestion": "请重新登录并导入最新的浏览器 Cookie",
        "level": LEVEL_SEVERE,
    },
    "登录": {
        "friendly": "需要登录才能访问",
        "suggestion": "请登录后导入 Cookie，或检查 Cookie 是否已过期",
        "level": LEVEL_SEVERE,
    },

    # --- 规则引擎类 ---
    "SyntaxError": {
        "friendly": "规则语法错误",
        "suggestion": "检查书源规则语法（CSS/XPath/正则）是否正确",
        "level": LEVEL_FATAL,
    },
    "规则": {
        "friendly": "规则执行出错",
        "suggestion": "检查书源规则配置，参考 Legado 规则语法文档",
        "level": LEVEL_SEVERE,
    },
    "字段缺失": {
        "friendly": "必要字段缺失",
        "suggestion": "书源配置缺少必要字段（如 bookUrl/bookName），请补全",
        "level": LEVEL_FATAL,
    },
    "jsoup": {
        "friendly": "HTML 解析失败",
        "suggestion": "页面 HTML 结构异常，检查 CSS 选择器或页面是否被篡改",
        "level": LEVEL_SEVERE,
    },
    # --- JS 执行类 ---
    "TypeError": {
        "friendly": "JS 执行类型错误，调用了不存在的函数",
        "suggestion": "1. 检查函数名拼写是否正确；2. 该函数可能在真机有但仿真端未实现，标记为 unverifiable；3. 建议在手机端实际测试验证",
        "level": LEVEL_WARNING,
    },
    "is not a function": {
        "friendly": "调用了不存在的 JS 函数",
        "suggestion": "检查函数名拼写，或该函数可能在仿真端未实现，标记为 unverifiable 并在手机端验证",
        "level": LEVEL_WARNING,
    },
    "java.ajax is not a function": {
        "friendly": "java.ajax 函数不可用",
        "suggestion": "仿真端可能未实现该 ajax 变体，标记为 unverifiable 并在手机端验证",
        "level": LEVEL_WARNING,
    },
}


# ---------------------------------------------------------------------------
# 翻译与分级
# ---------------------------------------------------------------------------

def translate_error(technical_error, context=None):
    """将技术错误翻译为用户可理解的语言，并给出修复建议。

    遍历 ERROR_TRANSLATIONS，返回首个匹配关键词的翻译；
    无匹配时返回通用兜底描述。

    Args:
        technical_error: 技术错误信息字符串
        context: 上下文 dict（可选，如 {"url": "...", "phase": "..."}）

    Returns:
        dict: {friendly, suggestion, level, original, context}
    """
    err = technical_error or ""
    matched = None
    for keyword, trans in ERROR_TRANSLATIONS.items():
        if keyword.lower() in err.lower():
            matched = trans
            break
    if matched is None:
        matched = {
            "friendly": "发生未知错误",
            "suggestion": "请查看详细错误信息，或重试操作",
            "level": LEVEL_WARNING,
        }
    return {
        "friendly": matched["friendly"],
        "suggestion": matched["suggestion"],
        "level": matched["level"],
        "original": err,
        "context": context or {},
    }


def classify_error_level(error):
    """错误分级：致命(红)/严重(橙)/警告(黄)/提示(蓝)。

    Args:
        error: 错误信息字符串

    Returns:
        str: 级别标识 fatal/severe/warning/info
    """
    result = translate_error(error)
    return result["level"]


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def _self_test():
    """最小自检：覆盖正常+边界用例"""
    # 1. translate_error - 正常用例（匹配关键词）
    r = translate_error("ConnectionError: Failed to establish connection")
    assert r["level"] == LEVEL_SEVERE
    assert "无法连接" in r["friendly"]
    assert r["original"] == "ConnectionError: Failed to establish connection"

    # 2. translate_error - 中文关键词匹配（大小写不敏感）
    r = translate_error("遇到 Cloudflare 防护页面")
    assert r["level"] == LEVEL_SEVERE
    assert "Cloudflare" in r["friendly"]

    # 3. translate_error - 边界用例：无匹配
    r = translate_error("some unknown weird error xyz123")
    assert r["level"] == LEVEL_WARNING
    assert "未知" in r["friendly"]

    # 4. translate_error - 边界用例：空输入
    r = translate_error("")
    assert r["level"] == LEVEL_WARNING
    assert r["original"] == ""

    # 5. translate_error - context 透传
    r = translate_error("404 Not Found", context={"url": "http://x.com/a"})
    assert r["context"]["url"] == "http://x.com/a"

    # 6. classify_error_level - 各级别
    assert classify_error_level("字段缺失: bookUrl") == LEVEL_FATAL
    assert classify_error_level("ConnectionError") == LEVEL_SEVERE
    assert classify_error_level("Timeout") == LEVEL_WARNING

    # 7. ERROR_TRANSLATIONS 至少 20 条
    assert len(ERROR_TRANSLATIONS) >= 20

    print(f"[self_test] error_translator 全部通过 (7 组用例, {len(ERROR_TRANSLATIONS)} 条翻译)")


if __name__ == "__main__":
    _self_test()
