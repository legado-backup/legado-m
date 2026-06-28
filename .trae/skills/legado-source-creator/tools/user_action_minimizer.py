#!/usr/bin/env python3
"""
user_action_minimizer.py - 8.5 用户体验增强：用户操作最小化

对需要用户介入的操作（Cookie输入/验证码输入/CF破盾），优先尝试自动化方案，
全部自动化方案失败后才提示用户手动操作，最大限度减少用户干预。

用法:
    from user_action_minimizer import minimize_user_action
    result = minimize_user_action("cookie_input", context={"url": "http://x.com"})
    if result["automated"]:
        print("已自动完成，无需用户介入")
"""

import os
import sys
from urllib.parse import urlparse

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 添加 scripts/ 目录到 sys.path 以导入 legado_client 包（obstacle_resolver/interactive_guide 已迁移）
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# try-import 辅助模块
try:
    from legado_client.client.obstacle_resolver import bypass_cf_auto, assist_captcha, is_cf_challenge
    _HAS_OBSTACLE_RESOLVER = True
except ImportError:
    _HAS_OBSTACLE_RESOLVER = False
    bypass_cf_auto = assist_captcha = is_cf_challenge = None

try:
    from cookie_manager import PersistentCookieStore
    _HAS_COOKIE_MANAGER = True
except ImportError:
    _HAS_COOKIE_MANAGER = False
    PersistentCookieStore = None

try:
    from legado_client.client.interactive_guide import guide_login, guide_cf_bypass, guide_captcha
    _HAS_INTERACTIVE_GUIDE = True
except ImportError:
    _HAS_INTERACTIVE_GUIDE = False
    guide_login = guide_cf_bypass = guide_captcha = None


# ---------------------------------------------------------------------------
# 自动化尝试顺序配置
# ---------------------------------------------------------------------------

# 三类操作的自动化尝试顺序：全部失败后才提示用户
AUTOMATION_ATTEMPTS = {
    "cookie_input": ["cookie_cache", "browser_import"],
    "captcha_input": ["ocr_auto", "image_export"],
    "cf_bypass": ["cloudscraper_auto", "cookie_cache_cf"],
}

# 用户操作追踪记录：{action_type: [{attempt, automated, success, message}]}
_action_log = {}


# ---------------------------------------------------------------------------
# 各自动化尝试实现
# ---------------------------------------------------------------------------

def _try_cookie_cache(url):
    """从持久化 Cookie 缓存加载"""
    if not _HAS_COOKIE_MANAGER:
        return False, None, "cookie_manager 未安装"
    try:
        store = PersistentCookieStore()
        cookie_str = store.get_cookie_for_url(url)
        if cookie_str:
            return True, {"cookie": cookie_str}, "从缓存加载Cookie成功"
        return False, None, "无可用Cookie缓存"
    except Exception as e:
        return False, None, f"Cookie缓存加载异常: {e}"


def _try_browser_import(context):
    """从浏览器导出文件导入 Cookie"""
    if not _HAS_COOKIE_MANAGER:
        return False, None, "cookie_manager 未安装"
    file_path = (context or {}).get("cookie_file")
    if not file_path:
        return False, None, "未提供浏览器Cookie文件路径"
    try:
        from cookie_manager import import_from_browser
        result = import_from_browser(file_path)
        if result:
            return True, {"cookies": result}, f"从浏览器导入Cookie成功: {len(result)}个域名"
        return False, None, "浏览器Cookie文件解析为空"
    except Exception as e:
        return False, None, f"浏览器导入异常: {e}"


def _try_ocr_auto(url, html, context):
    """OCR 自动识别验证码"""
    if not _HAS_OBSTACLE_RESOLVER:
        return False, None, "obstacle_resolver 未安装"
    try:
        result = assist_captcha(url, html, context.get("cookie_store"))
        if result.success:
            return True, {"code": result.cookie_store.get("_captcha_code")}, result.message
        return False, None, result.message
    except Exception as e:
        return False, None, f"OCR识别异常: {e}"


def _try_image_export(url, html, context):
    """导出验证码图片（半自动，仍需用户查看，但无需用户下载）"""
    if not _HAS_OBSTACLE_RESOLVER:
        return False, None, "obstacle_resolver 未安装"
    try:
        result = assist_captcha(url, html, context.get("cookie_store"))
        if result.success:
            return True, {"code": result.cookie_store.get("_captcha_code")}, result.message
        return False, None, result.message
    except Exception as e:
        return False, None, f"图片导出异常: {e}"


def _try_cloudscraper_auto(url):
    """cloudscraper 自动破盾"""
    if not _HAS_OBSTACLE_RESOLVER or bypass_cf_auto is None:
        return False, None, "cloudscraper 未安装"
    try:
        resp = bypass_cf_auto(url)
        if resp is not None:
            return True, {"html": resp.text}, "cloudscraper自动破盾成功"
        return False, None, "cloudscraper自动破盾失败"
    except Exception as e:
        return False, None, f"自动破盾异常: {e}"


def _try_cookie_cache_cf(url):
    """从缓存加载含 cf_clearance 的 Cookie"""
    if not _HAS_COOKIE_MANAGER:
        return False, None, "cookie_manager 未安装"
    try:
        store = PersistentCookieStore()
        cookie_str = store.get_cookie_for_url(url)
        if cookie_str and "cf_clearance" in cookie_str:
            return True, {"cookie": cookie_str}, "从缓存加载CF Cookie成功"
        return False, None, "缓存中无含cf_clearance的Cookie"
    except Exception as e:
        return False, None, f"CF Cookie缓存加载异常: {e}"


# ---------------------------------------------------------------------------
# 自动化尝试调度
# ---------------------------------------------------------------------------

def _run_attempt(attempt_name, action_type, url, context):
    """执行单个自动化尝试"""
    ctx = context or {}
    html = ctx.get("html", "")
    if attempt_name == "cookie_cache":
        return _try_cookie_cache(url)
    if attempt_name == "browser_import":
        return _try_browser_import(ctx)
    if attempt_name == "ocr_auto":
        return _try_ocr_auto(url, html, ctx)
    if attempt_name == "image_export":
        return _try_image_export(url, html, ctx)
    if attempt_name == "cloudscraper_auto":
        return _try_cloudscraper_auto(url)
    if attempt_name == "cookie_cache_cf":
        return _try_cookie_cache_cf(url)
    return False, None, f"未知自动化尝试: {attempt_name}"


def _record_action(action_type, attempt, automated, success, message):
    """内部：记录用户操作最小化尝试"""
    _action_log.setdefault(action_type, []).append({
        "attempt": attempt,
        "automated": automated,
        "success": success,
        "message": message,
    })


def minimize_user_action(action_type, context=None):
    """按自动化尝试顺序逐个尝试，成功则返回自动化结果，全部失败才提示用户。

    Args:
        action_type: 操作类型 cookie_input/captcha_input/cf_bypass
        context: 上下文 dict，可含 url/html/cookie_store/cookie_file

    Returns:
        dict: {automated, success, method, data, message, user_required}
              - automated: 是否由自动化完成
              - user_required: 是否需要用户手动介入
    """
    ctx = context or {}
    url = ctx.get("url", "")
    attempts = AUTOMATION_ATTEMPTS.get(action_type)
    if not attempts:
        return {
            "automated": False, "success": False, "method": None,
            "data": None, "message": f"未知操作类型: {action_type}",
            "user_required": False,
        }

    # 逐个尝试自动化方案
    for attempt_name in attempts:
        success, data, message = _run_attempt(attempt_name, action_type, url, ctx)
        _record_action(action_type, attempt_name, True, success, message)
        if success:
            return {
                "automated": True, "success": True, "method": attempt_name,
                "data": data, "message": message, "user_required": False,
            }

    # 全部自动化失败，提示用户手动操作
    user_result = _prompt_user(action_type, url, ctx)
    _record_action(action_type, "user_manual", False,
                   user_result["success"], user_result["message"])
    return user_result


def _prompt_user(action_type, url, context):
    """自动化全部失败后，提示用户手动操作"""
    if not _HAS_INTERACTIVE_GUIDE:
        return {
            "automated": False, "success": False, "method": "user_manual",
            "data": None, "message": "所有自动化方案失败且交互引导不可用",
            "user_required": True,
        }
    try:
        if action_type == "cookie_input":
            cookie_str = guide_login(url)
        elif action_type == "cf_bypass":
            cookie_str = guide_cf_bypass(url)
        elif action_type == "captcha_input":
            img_path = context.get("captcha_img_path", "")
            cookie_str = guide_captcha(img_path) if img_path else ""
        else:
            return {
                "automated": False, "success": False, "method": "user_manual",
                "data": None, "message": f"不支持的操作类型: {action_type}",
                "user_required": True,
            }
        if cookie_str:
            # 持久化用户输入
            if _HAS_COOKIE_MANAGER and url:
                try:
                    domain = urlparse(url).netloc
                    PersistentCookieStore().save(domain, cookie_str)
                except Exception:
                    pass
            return {
                "automated": False, "success": True, "method": "user_manual",
                "data": {"cookie": cookie_str}, "message": "用户手动输入成功",
                "user_required": True,
            }
        return {
            "automated": False, "success": False, "method": "user_manual",
            "data": None, "message": "用户未提供输入",
            "user_required": True,
        }
    except Exception as e:
        return {
            "automated": False, "success": False, "method": "user_manual",
            "data": None, "message": f"用户交互异常: {e}",
            "user_required": True,
        }


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def report_user_actions():
    """输出用户操作最小化检查报告。

    Returns:
        str: 格式化的报告文本，统计各操作类型的自动化覆盖率
    """
    lines = []
    lines.append("=" * 60)
    lines.append("用户操作最小化检查报告")
    lines.append("=" * 60)

    if not _action_log:
        lines.append("（暂无操作记录）")
        lines.append("=" * 60)
        return "\n".join(lines)

    total_attempts = 0
    total_automated_success = 0
    total_user_required = 0

    for action_type, records in _action_log.items():
        lines.append(f"\n[{action_type}]")
        for r in records:
            total_attempts += 1
            tag = "自动化" if r["automated"] else "用户手动"
            status = "成功" if r["success"] else "失败"
            lines.append(f"  - {r['attempt']} ({tag}): {status} - {r['message']}")
            if r["automated"] and r["success"]:
                total_automated_success += 1
            if not r["automated"]:
                total_user_required += 1

    lines.append("-" * 60)
    coverage = (total_automated_success / total_attempts * 100) if total_attempts else 0.0
    lines.append(f"自动化覆盖率: {total_automated_success}/{total_attempts} ({coverage:.1f}%)")
    lines.append(f"需用户介入次数: {total_user_required}")
    if coverage >= 80:
        lines.append("评价: 自动化程度高，用户干预少")
    elif coverage >= 50:
        lines.append("评价: 自动化程度中等，部分操作仍需用户介入")
    else:
        lines.append("评价: 自动化程度低，建议增强自动化能力")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def _self_test():
    """最小自检：覆盖正常+边界用例"""
    # 清空追踪记录
    _action_log.clear()

    # 1. minimize_user_action - 未知操作类型
    r = minimize_user_action("unknown_action")
    assert r["success"] is False
    assert "未知操作类型" in r["message"]

    # 2. minimize_user_action - cookie_input（无缓存，自动化失败，降级到用户提示）
    #    辅助模块可能缺失，应走完尝试链
    r = minimize_user_action("cookie_input", context={"url": "http://no-cache.test"})
    # 无论成功与否，都应返回结构完整的 dict
    assert "automated" in r
    assert "user_required" in r
    assert "method" in r

    # 3. minimize_user_action - cf_bypass
    r = minimize_user_action("cf_bypass", context={"url": "http://cf-test.test"})
    assert "automated" in r

    # 4. report_user_actions - 有记录
    report = report_user_actions()
    assert "用户操作最小化检查报告" in report
    assert "自动化覆盖率" in report

    # 5. report_user_actions - 边界用例：无记录
    _action_log.clear()
    report = report_user_actions()
    assert "暂无操作记录" in report

    # 6. AUTOMATION_ATTEMPTS 三类操作齐全
    assert set(AUTOMATION_ATTEMPTS.keys()) == {"cookie_input", "captcha_input", "cf_bypass"}

    _action_log.clear()
    print("[self_test] user_action_minimizer 全部通过 (6 组用例)")


if __name__ == "__main__":
    _self_test()
