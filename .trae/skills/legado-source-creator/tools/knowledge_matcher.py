#!/usr/bin/env python3
"""
knowledge_matcher.py - 知识库匹配器

根据网站特征（CMS/加密方式/反爬策略/URL结构）匹配 references/site-features/
知识库中的相似案例，并在书源生成成功后自动沉淀新案例。

特征提取复用 scripts/analyze_site.py 的 identify_cms 与 identify_anti_crawl
（未安装时降级为内置正则，不报错）。

知识库（references/site-features/cases.json）格式:
    [
        {
            "url": "https://example.com",
            "domain": "example.com",
            "features": { ... extract_features 输出 ... },
            "solution": "书源规则摘要或解决方案",
            "created_at": "2026-06-19 12:00:00"
        }
    ]

用法:
    from knowledge_matcher import match_site_features, update_knowledge_base
    hit = match_site_features(url, html)
    if hit:
        print(hit["solution"])
"""

import json
import os
import re
import sys
import time
import urllib.parse

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SITE_FEATURES_DIR = os.path.join(_SKILL_DIR, "references", "site-features")
_CASES_FILE = os.path.join(_SITE_FEATURES_DIR, "cases.json")

# 加密/混淆特征关键词（小写匹配）
_ENC_PATTERNS = {
    "cryptojs": r"crypto-js|cryptojs|crypto\.js",
    "aes": r"\baes\b|cryptojs\.aes",
    "des": r"\bdes\b|tripledes",
    "rsa": r"\brsa\b|jsencrypt|s_rsa",
    "rc4": r"\brc4\b",
    "base64": r"\batob\b|\bbtoa\b|base64\.decode",
    "packer": r"eval\(function\(p,a,c,k,e,d",
    "unescape": r"unescape\(",
    "hex": r"fromCharCode|hex2bin|\\\\x[0-9a-f]{2}",
}


def _import_analyze_site():
    """尝试导入 scripts/analyze_site.py 的 identify_cms / identify_anti_crawl。

    Returns:
        (identify_cms, identify_anti_crawl) 或 (None, None)
    """
    scripts_dir = os.path.join(_SKILL_DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from analyze_site import identify_cms, identify_anti_crawl
        return identify_cms, identify_anti_crawl
    except Exception:
        return None, None


def _detect_encryption_hints(html):
    """从 HTML 检测加密/混淆特征"""
    lower = html.lower() if html else ""
    hints = []
    for name, pattern in _ENC_PATTERNS.items():
        if re.search(pattern, lower):
            hints.append(name)
    return hints


def _url_structure(url):
    """分析 URL 结构：path / query / fragment / plain"""
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        return "query"
    if parsed.fragment:
        return "fragment"
    if parsed.path and parsed.path != "/":
        return "path"
    return "plain"


def extract_features(url, html):
    """提取网站特征。

    Args:
        url: 目标 URL
        html: 页面 HTML 文本

    Returns:
        dict: {
            url, domain, cms, cms_confidence,
            anti_crawl(list), has_anti_crawl,
            is_https, url_structure,
            has_login_form, encryption_hints(list)
        }
    """
    html = html or ""
    domain = urllib.parse.urlparse(url).netloc
    parsed = urllib.parse.urlparse(url)

    identify_cms, identify_anti_crawl = _import_analyze_site()

    # CMS 识别（优先 analyze_site，降级为内置正则）
    cms = "Unknown"
    cms_confidence = "none"
    if identify_cms is not None:
        try:
            r = identify_cms(html)
            cms = r.get("cms", "Unknown")
            cms_confidence = r.get("confidence", "none")
        except Exception:
            pass
    if cms == "Unknown":
        m = re.search(
            r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.I,
        )
        if m:
            cms = m.group(1).split()[0]
            cms_confidence = "low"

    # 反爬识别
    anti_crawl = []
    has_anti_crawl = False
    if identify_anti_crawl is not None:
        try:
            r = identify_anti_crawl(html)
            anti_crawl = r.get("strategies", [])
            has_anti_crawl = r.get("has_anti_crawl", False)
        except Exception:
            pass
    if not anti_crawl:
        lower = html.lower()
        if re.search(r'cf-browser-verification|__cf_bm|cf-challenge|just a moment', lower):
            anti_crawl.append("cloudflare")
        if re.search(r'captcha|验证码|geetest|recaptcha|hcaptcha', lower):
            anti_crawl.append("captcha")

    return {
        "url": url,
        "domain": domain,
        "cms": cms,
        "cms_confidence": cms_confidence,
        "anti_crawl": anti_crawl,
        "has_anti_crawl": has_anti_crawl,
        "is_https": parsed.scheme == "https",
        "url_structure": _url_structure(url),
        "has_login_form": bool(
            html and re.search(r'<input[^>]+type=["\']password["\']', html)
        ),
        "encryption_hints": _detect_encryption_hints(html),
    }


def _features_to_set(features):
    """将特征 dict 展平为可比较的字符串集合"""
    tags = set()
    if features.get("cms") and features["cms"] != "Unknown":
        tags.add(f"cms:{features['cms'].lower()}")
    for s in features.get("anti_crawl", []):
        tags.add(f"anti:{s}")
    for h in features.get("encryption_hints", []):
        tags.add(f"enc:{h}")
    tags.add(f"url:{features.get('url_structure', 'plain')}")
    tags.add("https" if features.get("is_https") else "http")
    if features.get("has_login_form"):
        tags.add("login_form")
    return tags


def calculate_similarity(features1, features2):
    """计算两组特征的 Jaccard 相似度（0-1）。

    简化说明: Jaccard 集合相似度 | 已知上限: 不考虑特征权重 | 升级路径: 加权余弦相似度
    """
    s1 = _features_to_set(features1 or {})
    s2 = _features_to_set(features2 or {})
    if not s1 and not s2:
        return 1.0
    union = s1 | s2
    if not union:
        return 0.0
    return len(s1 & s2) / len(union)


def _load_cases():
    """读取知识库案例列表，文件不存在/损坏返回 []"""
    if not os.path.isfile(_CASES_FILE):
        return []
    try:
        with open(_CASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_cases(cases):
    os.makedirs(_SITE_FEATURES_DIR, exist_ok=True)
    with open(_CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


def match_site_features(url, html, threshold=0.3):
    """主函数：匹配知识库中的相似案例。

    Args:
        url: 目标 URL
        html: 页面 HTML
        threshold: 最低相似度阈值，低于则视为无匹配

    Returns:
        dict | None: 最相似案例（含 similarity 字段），无匹配返回 None
    """
    features = extract_features(url, html)
    cases = _load_cases()
    best = None
    best_score = 0.0
    for case in cases:
        score = calculate_similarity(features, case.get("features", {}))
        if score > best_score:
            best_score = score
            best = case
    if best is None or best_score < threshold:
        return None
    best = dict(best)
    best["similarity"] = round(best_score, 3)
    return best


def update_knowledge_base(url, html, solution):
    """成功生成书源后自动更新知识库。

    Args:
        url: 目标 URL
        html: 页面 HTML
        solution: 书源规则摘要或解决方案文本

    Returns:
        str | None: 写入的案例标识（domain），失败返回 None
    """
    features = extract_features(url, html)
    domain = features.get("domain") or urllib.parse.urlparse(url).netloc
    if not domain:
        return None
    cases = _load_cases()
    # 同域名去重：覆盖已有案例
    cases = [c for c in cases if c.get("domain") != domain]
    cases.append({
        "url": url,
        "domain": domain,
        "features": features,
        "solution": solution,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    try:
        _save_cases(cases)
        return domain
    except OSError:
        return None


if __name__ == "__main__":
    # 简化自检：正常用例 + 边界用例
    html_wp = '<meta name="generator" content="WordPress 6.0"><input type="password" name="pwd">'
    html_cf = '<html>just a moment... cf-challenge</html>'
    f1 = extract_features("https://a.example.com/list", html_wp)
    f2 = extract_features("https://b.example.com/list", html_wp)
    # 正常用例：同 CMS+登录表单，相似度应较高
    assert calculate_similarity(f1, f2) >= 0.8, f1
    # 正常用例：CF 盾特征应被识别
    f3 = extract_features("https://c.example.com/", html_cf)
    assert "cloudflare" in f3["anti_crawl"]
    # 边界用例：空输入
    f_empty = extract_features("", "")
    assert calculate_similarity(f_empty, f_empty) == 1.0
    assert match_site_features("", "") is None
    print("knowledge_matcher self-check OK")
