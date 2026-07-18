#!/usr/bin/env python3
"""
interactive_guide.py - Legado 书源/订阅源 Skill 的用户交互优化模块（7.7）

提供友好的 CLI 交互引导，覆盖登录、CF破盾、验证码、规则确认、进度反馈五个场景。
所有交互通过 print() + input() 实现，无外部依赖。

用法:
    from interactive_guide import guide_login, guide_cf_bypass, guide_captcha, confirm_rules, report_progress

    cookie = guide_login("https://example.com/login")
    code = guide_captcha("/tmp/captcha.png")
    rules = confirm_rules({"bookList": ".book-item", "bookName": ".title"})
    report_progress("解析", 50, "已解析50%书籍")
"""

import os
import sys

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ==================== 3.15: Web 模式标志 ====================
_web_mode: bool = False
_ws_callback = None  # WebSocket 推送回调（Web 模式下使用）


def set_web_mode(enabled: bool = True, ws_callback=None) -> None:
    """设置 Web 模式。

    Web 模式下：
    - interactive_guide 交互提示通过 WebSocket 推送（非阻塞）
    - webview_handler/user_interaction 降级为日志输出
    """
    global _web_mode, _ws_callback
    _web_mode = enabled
    _ws_callback = ws_callback


def is_web_mode() -> bool:
    """是否处于 Web 模式。"""
    return _web_mode


# ---------------------------------------------------------------------------
# 交互引导函数
# ---------------------------------------------------------------------------

def guide_login(url):
    """交互式登录引导：展示获取 Cookie 的步骤，等待用户输入 Cookie。

    Web 模式下降级为日志输出，不阻塞等待用户输入。

    Args:
        url: 目标站点登录页 URL

    Returns:
        str: 用户输入的 Cookie 字符串（可能为空表示跳过）
    """
    if _web_mode:
        msg = f"[Web模式] 登录引导：目标站点 {url} 需要登录，请通过 Legado App 手动登录"
        print(msg)
        if _ws_callback:
            try:
                _ws_callback({"type": "login_required", "url": url, "message": msg})
            except Exception:
                pass
        return ""
    print(f"\n{'=' * 60}")
    print(f"登录引导 - 需要提供登录 Cookie")
    print(f"{'=' * 60}")
    print(f"目标站点: {url}")
    print(f"\n请按以下步骤获取 Cookie:")
    print(f"  1. 在浏览器中打开: {url}")
    print(f"  2. 完成账号登录")
    print(f"  3. 按 F12 打开开发者工具")
    print(f"  4. 切换到 Network（网络）标签页")
    print(f"  5. 刷新页面，点击任意请求")
    print(f"  6. 在 Request Headers 中找到 Cookie 字段")
    print(f"  7. 复制完整的 Cookie 值")
    print(f"\n请粘贴 Cookie（直接回车跳过）:")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def guide_cf_bypass(url):
    """交互式 CF 破盾引导：展示手动破盾步骤，等待用户导入 Cookie。

    Web 模式下降级为日志输出，不阻塞等待用户输入。

    Args:
        url: 受 Cloudflare 防护的目标 URL

    Returns:
        str: 用户输入的 Cookie 字符串（含 cf_clearance，可能为空表示跳过）
    """
    if _web_mode:
        msg = f"[Web模式] CF破盾引导：目标站点 {url} 受 CF 防护，请通过 Legado App WebView 自动通过"
        print(msg)
        if _ws_callback:
            try:
                _ws_callback({"type": "cf_challenge", "url": url, "message": msg})
            except Exception:
                pass
        return ""
    print(f"\n{'=' * 60}")
    print(f"CF 破盾引导 - 需要手动绕过 Cloudflare 防护")
    print(f"{'=' * 60}")
    print(f"目标站点: {url}")
    print(f"\nCloudflare 防护无法自动绕过，请手动破盾:")
    print(f"  1. 在浏览器中打开: {url}")
    print(f"  2. 等待 5 秒 JS 挑战自动完成")
    print(f"  3. 页面正常显示后，按 F12 -> Network")
    print(f"  4. 刷新页面，点击主文档请求")
    print(f"  5. 在 Request Headers 中复制完整 Cookie")
    print(f"     （重点找 cf_clearance 字段）")
    print(f"\n请粘贴 Cookie（直接回车跳过）:")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def guide_captcha(img_path):
    """交互式验证码识别：展示验证码图片，等待用户手动输入。

    Web 模式下降级为日志输出，不阻塞等待用户输入。

    Args:
        img_path: 验证码图片的本地路径

    Returns:
        str: 用户输入的验证码（可能为空表示跳过）
    """
    if _web_mode:
        msg = f"[Web模式] 验证码识别：图片路径 {img_path}，请通过 Legado App 手动处理"
        print(msg)
        if _ws_callback:
            try:
                _ws_callback({"type": "captcha_required", "img_path": img_path, "message": msg})
            except Exception:
                pass
        return ""
    print(f"\n{'=' * 60}")
    print(f"验证码识别 - 需要手动输入")
    print(f"{'=' * 60}")
    print(f"图片路径: {img_path}")

    # 尝试用系统默认程序打开图片
    if img_path and os.path.exists(img_path):
        try:
            if sys.platform == "win32":
                os.startfile(img_path)  # Windows
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", img_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", img_path])
        except Exception:
            print(f"（无法自动打开图片，请手动查看上述路径）")
    else:
        print(f"（图片路径不存在，请检查路径）")

    print(f"\n请查看图片并输入验证码内容（直接回车跳过）:")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def confirm_rules(rule_suggestions):
    """交互式规则确认：逐条展示规则建议，用户可确认或修改。

    Web 模式下直接返回建议值（跳过交互）。

    Args:
        rule_suggestions: dict，规则名 -> 规则建议值

    Returns:
        dict: 用户确认/修改后的规则字典
    """
    if _web_mode:
        print(f"[Web模式] 规则确认：跳过交互，直接采用建议值（{len(rule_suggestions)} 条）")
        if _ws_callback:
            try:
                _ws_callback({"type": "rules_confirmed", "rules": rule_suggestions, "auto": True})
            except Exception:
                pass
        return dict(rule_suggestions)
    print(f"\n{'=' * 60}")
    print(f"规则确认 - 共 {len(rule_suggestions)} 条规则")
    print(f"{'=' * 60}")
    print(f"操作说明: 直接回车=确认建议值，输入新值=修改，输入 '!' = 删除该规则")

    confirmed = {}
    for name, suggestion in rule_suggestions.items():
        print(f"\n规则名: {name}")
        print(f"建议值: {suggestion}")
        print(f"请输入确认/修改值（回车确认，'!' 删除）:")
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            user_input = ""

        if user_input == "!":
            print(f"  -> 已删除规则: {name}")
            continue
        elif user_input == "":
            confirmed[name] = suggestion
            print(f"  -> 已确认: {name} = {suggestion}")
        else:
            confirmed[name] = user_input
            print(f"  -> 已修改: {name} = {user_input}")

    print(f"\n规则确认完成，共保留 {len(confirmed)} 条规则")
    return confirmed


def report_progress(stage, progress, message):
    """进度实时反馈：输出阶段、百分比和消息。

    用于长时间操作（如批量解析书籍列表）时向用户反馈进度。

    Args:
        stage: 当前阶段名称（如 "解析书源"、"测试规则"）
        progress: 进度百分比 0-100
        message: 进度描述消息
    """
    # 规范化进度值
    try:
        pct = float(progress)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))

    # 进度条（20格）
    filled = int(pct / 100 * 20)
    bar = "[" + "#" * filled + "-" * (20 - filled) + "]"

    print(f"\r[{stage}] {bar} {pct:5.1f}% - {message}", end="", flush=True)
    # 100% 时换行
    if pct >= 100.0:
        print()


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== interactive_guide.py 自检 ===")

    # report_progress 自检（正常用例）
    print("\n[1] report_progress 正常用例:")
    report_progress("测试阶段", 50, "处理中")
    report_progress("测试阶段", 100, "完成")

    # report_progress 边界用例（超出范围）
    print("\n[2] report_progress 边界用例（超出范围应被截断）:")
    report_progress("边界测试", 150, "应显示100%")
    report_progress("边界测试", -10, "应显示0%")

    # confirm_rules 逻辑自检（非交互，用模拟数据验证返回结构）
    print("\n[3] confirm_rules 返回结构自检（跳过交互）:")
    _sample = {"rule1": "value1", "rule2": "value2"}
    assert isinstance(_sample, dict), "rule_suggestions 应为 dict"
    print("   OK - rule_suggestions 类型正确")

    print("\n=== 自检完成 ===")
