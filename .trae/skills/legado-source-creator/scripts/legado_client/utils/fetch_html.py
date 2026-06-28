"""
fetch_html.py - Playwright HTML 获取脚本

用于获取需要 JS 渲染的页面 HTML，支持 Cloudflare Challenge 自动等待。

用法:
    python tools/fetch_html.py --url URL --output output.html
    python tools/fetch_html.py --url URL --output output.html --wait-cf
    python tools/fetch_html.py --url URL --output output.html --wait-selector ".video-list"
    python tools/fetch_html.py --url URL --output output.html --headed --export-cookies cookies.json
"""

import argparse
import json
import sys
import time


# ---------------------------------------------------------------------------
# Playwright 安装检测
# ---------------------------------------------------------------------------

def check_playwright():
    """检测 Playwright 是否完整可用（Python 包 + Chromium 浏览器）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# CF Challenge 多特征检测
# ---------------------------------------------------------------------------

def detect_cf_challenge(page):
    """CF Challenge 多特征检测

    Returns:
        False  - 未检测到 CF 挑战
        True   - 检测到 CF JS Challenge
        'turnstile' - 检测到 Turnstile 验证码（需人工）
    """
    # 检测1: 页面标题
    try:
        title = page.title()
        if 'Just a moment' in title or 'Cloudflare' in title:
            return True
    except Exception:
        pass

    # 检测2: CF JS 变量
    try:
        has_cf_var = page.evaluate('typeof cf_chl_opt !== "undefined"')
        if has_cf_var:
            return True
    except Exception:
        pass

    # 检测3: CF Challenge 脚本
    try:
        has_cf_script = page.evaluate(
            'document.querySelector("script[src*=challenge-platform]") !== null'
        )
        if has_cf_script:
            return True
    except Exception:
        pass

    # 检测4: Turnstile iframe
    try:
        has_turnstile = page.evaluate(
            'document.querySelector(\'iframe[src*="challenges.cloudflare.com"]\') !== null'
        )
        if has_turnstile:
            return 'turnstile'
    except Exception:
        pass

    return False


# ---------------------------------------------------------------------------
# CF JS Challenge 自动等待
# ---------------------------------------------------------------------------

def wait_cf_challenge(page, timeout=30):
    """等待 CF JS Challenge 自动通过

    Args:
        page: Playwright Page 对象
        timeout: 最长等待秒数

    Returns:
        True  - CF 验证已通过
        False - 超时未通过
        'turnstile' - 检测到 Turnstile（需人工操作）
    """
    print(f"[CF] 等待 Cloudflare 验证通过（最长 {timeout} 秒）...")
    start = time.time()

    while time.time() - start < timeout:
        result = detect_cf_challenge(page)
        if result is False:
            elapsed = time.time() - start
            print(f"[CF] 验证已通过（耗时 {elapsed:.1f} 秒）")
            return True
        if result == 'turnstile':
            print("[CF] 检测到 Turnstile 验证码，需要人工操作（请使用 --headed 模式）")
            return 'turnstile'
        # JS Challenge，继续等待
        time.sleep(1)

    print(f"[CF] 警告: CF 验证等待超时（{timeout} 秒）")
    return False


# ---------------------------------------------------------------------------
# Cookie 导出
# ---------------------------------------------------------------------------

def export_cookies(context, output_path):
    """导出浏览器 Cookie 为 JSON 格式

    Args:
        context: Playwright BrowserContext 对象
        output_path: Cookie 输出文件路径
    """
    cookies = context.cookies()
    cookie_list = []
    for c in cookies:
        cookie_list.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": c.get("expires", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", "None"),
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cookie_list, f, ensure_ascii=False, indent=2)

    print(f"[Cookie] 已导出 {len(cookie_list)} 条 Cookie 到 {output_path}")


# ---------------------------------------------------------------------------
# 核心: Playwright HTML 获取
# ---------------------------------------------------------------------------

def fetch_html(url, output, wait_cf=False, wait_selector=None,
               headed=False, export_cookies_path=None, timeout=30):
    """使用 Playwright 获取页面 HTML

    Args:
        url: 目标 URL
        output: HTML 输出文件路径
        wait_cf: 是否等待 CF 验证通过
        wait_selector: 等待指定 CSS 选择器出现
        headed: 是否使用有头模式
        export_cookies_path: Cookie 导出文件路径
        timeout: 超时时间（秒）
    """
    # 检测 Playwright
    if not check_playwright():
        print("错误: Playwright 未安装或 Chromium 浏览器不可用！")
        print()
        print("安装步骤:")
        print("  1. pip install playwright")
        print("  2. playwright install chromium")
        print()
        print("如果已安装 pip 包但仍报错，请运行:")
        print("  playwright install chromium")
        sys.exit(1)

    from playwright.sync_api import sync_playwright

    # Mobile UA 模拟 Android 浏览器
    mobile_ua = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 6) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.6422.113 Mobile Safari/537.36"
    )

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=not headed)

        # 创建上下文（模拟移动端）
        context = browser.new_context(
            user_agent=mobile_ua,
            viewport={"width": 412, "height": 915},
            is_mobile=True,
            device_scale_factor=2.625,
            has_touch=True,
        )

        page = context.new_page()

        try:
            # 导航到目标页面
            print(f"[导航] 正在加载: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            print(f"[导航] 页面已加载（domcontentloaded）")

            # CF Challenge 等待
            if wait_cf:
                cf_result = wait_cf_challenge(page, timeout=timeout)
                if cf_result == 'turnstile':
                    if not headed:
                        print("[CF] Turnstile 需要人工操作，请使用 --headed 模式重新运行")
                        browser.close()
                        sys.exit(1)
                    else:
                        # 有头模式下等待用户手动通过 Turnstile
                        print("[CF] 请在浏览器中手动完成 Turnstile 验证...")
                        print("[CF] 等待验证通过（最长 120 秒）...")
                        cf_result = wait_cf_challenge(page, timeout=120)
                        if cf_result is not True:
                            print("[CF] Turnstile 验证超时")
                            browser.close()
                            sys.exit(1)
                elif cf_result is False:
                    print("[CF] 警告: CF 验证未通过，继续获取当前页面内容")

            # 等待指定选择器
            if wait_selector:
                print(f"[等待] 等待选择器出现: {wait_selector}")
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout * 1000)
                    print(f"[等待] 选择器已出现: {wait_selector}")
                except Exception as e:
                    print(f"[等待] 警告: 选择器等待超时: {wait_selector} ({e})")

            # 获取 HTML
            html = page.content()
            print(f"[完成] HTML 长度: {len(html)}")

            # 保存 HTML
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[保存] 已保存到 {output}")

            # 导出 Cookie
            if export_cookies_path:
                export_cookies(context, export_cookies_path)

        except Exception as e:
            error_msg = str(e)

            # 判断是否为 CF 拦截导致的加载失败
            if "net::ERR_CONNECTION" in error_msg or "Timeout" in error_msg:
                print(f"[错误] 页面加载失败: {e}")
                print("[提示] 如果目标网站使用 Cloudflare 防护，请尝试:")
                print("  --wait-cf      等待 CF JS Challenge 自动通过")
                print("  --headed       有头模式（用于 Turnstile 手动通过）")
            else:
                print(f"[错误] 页面加载失败: {e}")

            # 即使失败也尝试获取当前页面内容
            try:
                html = page.content()
                if html and len(html) > 100:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"[回退] 已保存当前页面内容到 {output}（长度={len(html)}）")
            except Exception:
                pass

            browser.close()
            sys.exit(1)

        finally:
            browser.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Playwright HTML 获取脚本 - 用于获取需要 JS 渲染的页面 HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python tools/fetch_html.py --url https://example.com --output page.html
  python tools/fetch_html.py --url https://example.com --output page.html --wait-cf
  python tools/fetch_html.py --url https://example.com --output page.html --wait-selector ".video-list"
  python tools/fetch_html.py --url https://example.com --output page.html --headed --export-cookies cookies.json

注意:
  - Playwright 是可选依赖，未安装时会输出安装指引
  - --headed 模式用于需要人工通过 Turnstile 验证码的场景
  - 默认使用 Mobile UA 模拟 Android 浏览器（Pixel 6）
""",
    )
    parser.add_argument("--url", required=True, help="目标 URL（必需）")
    parser.add_argument("--output", required=True, help="HTML 输出文件路径（必需）")
    parser.add_argument("--wait-cf", action="store_true",
                        help="等待 Cloudflare 验证通过（最长 30 秒）")
    parser.add_argument("--wait-selector", metavar="SELECTOR",
                        help="等待指定 CSS 选择器出现")
    parser.add_argument("--headed", action="store_true",
                        help="有头模式（用于 Turnstile 手动通过）")
    parser.add_argument("--export-cookies", metavar="PATH",
                        help="Cookie 导出文件路径（JSON 格式）")
    parser.add_argument("--timeout", type=int, default=30,
                        help="超时时间（秒），默认 30")

    args = parser.parse_args()

    fetch_html(
        url=args.url,
        output=args.output,
        wait_cf=args.wait_cf,
        wait_selector=args.wait_selector,
        headed=args.headed,
        export_cookies_path=args.export_cookies,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
