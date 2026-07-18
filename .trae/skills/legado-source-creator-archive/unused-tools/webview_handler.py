#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebView 委托处理器 - 使用 Selenium 渲染页面

源码参照: io.legado.app.help.http.BackstageWebView (Android WebView + WebViewClient + WebChromeClient)

用途: 当 JAR 仿真服务端检测到 webView 需求时（BackstageWebView/JsExtensions.webView()），
抛出 WebViewRequiredException，Python 客户端捕获后用本模块的 Selenium 渲染页面，
再将渲染后的 HTML 传回 JAR 用 AnalyzeRule 解析。

简化说明: 仅模拟 BackstageWebView 的核心行为（加载URL+执行JS+返回HTML），不模拟 WebViewClient 的 onLoadResource/onPageFinished 回调 | 已知上限: 无法处理复杂的 WebViewClient 交互（如 JS Bridge） | 升级路径: 需要时用 CDP 协议监听更多事件
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ==================== 3.15: Web 模式降级 ====================
_web_mode: bool = False


def set_web_mode(enabled: bool = True) -> None:
    """设置 Web 模式。Web 模式下 WebView 渲染降级为日志输出。"""
    global _web_mode
    _web_mode = enabled


def is_web_mode() -> bool:
    """是否处于 Web 模式。"""
    return _web_mode


class WebViewHandler:
    """Selenium WebView 渲染器，模拟 Legado BackstageWebView 行为"""

    def __init__(self, headless: bool = True, chrome_path: Optional[str] = None,
                 chromedriver_path: Optional[str] = None):
        """
        Args:
            headless: 是否无头模式
            chrome_path: Chrome 可执行文件路径（自动检测时传 None）
            chromedriver_path: chromedriver 路径（自动检测时传 None）
        """
        self.headless: bool = headless
        self.chrome_path: Optional[str] = chrome_path
        self.chromedriver_path: Optional[str] = chromedriver_path
        self.driver = None
        self._available: Optional[bool] = None  # None=未检测, True/False=已检测

    def is_available(self) -> bool:
        """检测 Selenium + Chrome 是否可用"""
        if self._available is not None:
            return self._available
        try:
            from selenium import webdriver  # noqa: F401
            from selenium.webdriver.chrome.options import Options  # noqa: F401
            self._available = True
        except ImportError:
            logger.warning("selenium 未安装，WebView 渲染不可用。安装: pip install selenium")
            self._available = False
        return self._available

    def _ensure_driver(self) -> None:
        """确保 WebDriver 已启动"""
        if self.driver is not None:
            return
        if not self.is_available():
            raise RuntimeError("Selenium/Chrome 不可用，无法渲染 WebView")

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if self.chrome_path:
            options.binary_location = self.chrome_path

        if self.chromedriver_path:
            service = Service(executable_path=self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)

        # 设置默认超时
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)

    def render_url(self, url: str, js: Optional[str] = None,
                  timeout: int = 30) -> Optional[str]:
        """
        加载 URL 并执行 JS，返回渲染后 HTML

        模拟 BackstageWebView.getStrResponse(): 加载 URL → 等待页面加载 → 执行 JS → 返回 page_source

        Args:
            url: 目标 URL
            js: 需执行的 JavaScript 代码（对应 BackstageWebView 的 javaScript 参数）
            timeout: 页面加载超时（秒）

        Returns:
            渲染后的 HTML 字符串，失败返回 None
        """
        try:
            self._ensure_driver()
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)

            if js:
                result = self.driver.execute_script(js)
                # 如果 JS 返回了结果，直接返回（模拟 webView() 的 JS 返回值）
                if result is not None:
                    return str(result)

            return self.driver.page_source
        except Exception as e:
            logger.error(f"render_url 失败: url={url[:80]}, error={e}")
            return None

    def render_html(self, html: str, js: Optional[str] = None,
                    base_url: str = "about:blank", timeout: int = 30) -> Optional[str]:
        """
        加载 HTML 并执行 JS，返回结果

        模拟 BackstageWebView 加载本地 HTML → 执行 JS → 返回结果

        Args:
            html: HTML 内容
            js: 需执行的 JavaScript 代码
            base_url: 基础 URL（用于相对路径解析）
            timeout: 超时（秒）

        Returns:
            渲染后的 HTML 字符串，失败返回 None
        """
        try:
            self._ensure_driver()
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(base_url)
            # 用 document.write 写入 HTML
            self.driver.execute_script(
                "document.open(); document.write(arguments[0]); document.close();", html
            )

            if js:
                result = self.driver.execute_script(js)
                if result is not None:
                    return str(result)

            return self.driver.page_source
        except Exception as e:
            logger.error(f"render_html 失败: error={e}")
            return None

    def sniff_resource(self, url: str, source_regex: str,
                       js: Optional[str] = None, timeout: int = 30) -> Optional[str]:
        """
        嗅探资源 URL（视频/音频）

        模拟 BackstageWebView 的 sourceRegex 行为: 加载 URL → 监听网络请求 → 匹配正则

        Args:
            url: 目标页面 URL
            source_regex: 资源 URL 匹配正则
            js: 页面加载后执行的 JS
            timeout: 嗅探等待时间（秒）

        Returns:
            匹配到的资源 URL，未匹配返回 None
        """
        try:
            self._ensure_driver()

            # 启用性能日志以捕获网络请求
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities  # noqa: F401

            # 重新创建 driver 以启用性能日志
            if self.driver:
                self.driver.quit()
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            if self.chrome_path:
                options.binary_location = self.chrome_path
            options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

            if self.chromedriver_path:
                from selenium.webdriver.chrome.service import Service
                service = Service(executable_path=self.chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)

            if js:
                self.driver.execute_script(js)

            # 等待资源加载
            time.sleep(min(timeout, 10))

            # 从性能日志中提取网络请求 URL
            logs = self.driver.get_log("performance")
            pattern = re.compile(source_regex) if source_regex else None

            for entry in logs:
                try:
                    log_msg = json.loads(entry["message"])["message"]
                    if log_msg.get("method") == "Network.requestWillBeSent":
                        req_url = log_msg["params"]["request"]["url"]
                        if pattern is None or pattern.search(req_url):
                            return req_url
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            return None
        except Exception as e:
            logger.error(f"sniff_resource 失败: url={url[:80]}, error={e}")
            return None

    def handle_webview_request(self, request: dict) -> dict:
        """
        根据 WebViewRequest 类型分发处理

        Web 模式下降级为日志输出，不执行实际渲染。

        对应 JAR 中 WebViewRequest 的 type 字段:
        - "load": 加载 URL 并执行 JS
        - "sniff": 嗅探资源 URL
        - "overrideUrl": 拦截 URL 跳转（简化为加载 URL）
        - "login": 需要用户介入，返回提示信息

        Args:
            request: dict，包含 url/html/js/sourceRegex/type 字段

        Returns:
            dict: {"success": bool, "html": str|None, "error": str|None}
        """
        if _web_mode:
            # Web 模式下降级：记录日志但不执行渲染
            req_type = request.get("type", "load")
            url = request.get("url", "")
            logger.info("[Web模式] WebView请求降级: type=%s url=%s", req_type, url[:80])
            return {
                "success": False,
                "html": None,
                "error": f"Web模式下 WebView 渲染已降级（type={req_type}, url={url[:80]}）",
            }
        req_type = request.get("type", "load")

        if req_type == "login":
            return {
                "success": False,
                "html": None,
                "error": f"源需要登录/人工验证: url={request.get('url', '')}\n建议：在 Legado App 中手动登录后导出 Cookie"
            }

        if not self.is_available():
            return {
                "success": False,
                "html": None,
                "error": "Selenium/Chrome 不可用，无法渲染 WebView。安装: pip install selenium"
            }

        url = request.get("url")
        js = request.get("js")
        source_regex = request.get("sourceRegex")
        html = request.get("html")

        if req_type == "sniff":
            # 嗅探资源
            result = self.sniff_resource(url, source_regex, js)
            if result:
                return {"success": True, "html": result, "error": None}
            else:
                return {"success": False, "html": None, "error": f"未嗅探到匹配 {source_regex} 的资源"}
        else:
            # load / overrideUrl: 加载 URL 或 HTML
            if html and not url:
                result = self.render_html(html, js)
            elif url:
                result = self.render_url(url, js)
            else:
                return {"success": False, "html": None, "error": "WebViewRequest 缺少 url 和 html"}

            if result:
                return {"success": True, "html": result, "error": None}
            else:
                return {"success": False, "html": None, "error": f"渲染失败: url={url}"}

    def close(self) -> None:
        """关闭 WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


# ==================== 自检程序 ====================
# 简化说明: 验证 WebViewHandler 基本功能 | 已知上限: 依赖 Chrome 安装 | 升级路径: 添加更多浏览器支持

if __name__ == "__main__":
    handler = WebViewHandler(headless=True)

    # 边界用例: Selenium 未安装时的降级
    assert handler.is_available() in (True, False), "is_available 应返回布尔值"
    print(f"Selenium 可用: {handler.is_available()}")

    if handler.is_available():
        # 正常用例: 渲染一个简单页面
        html = handler.render_url("https://example.com", timeout=15)
        assert html is not None, "render_url 应返回 HTML"
        assert "Example Domain" in html, "渲染结果应包含页面内容"
        print(f"render_url 测试通过: HTML 长度={len(html)}")

        # 正常用例: handle_webview_request 分发
        result = handler.handle_webview_request({
            "url": "https://example.com",
            "js": None,
            "type": "load"
        })
        assert result["success"] is True, "load 类型应成功"
        print(f"handle_webview_request(load) 测试通过")

        # 边界用例: login 类型不需要渲染
        result = handler.handle_webview_request({
            "url": "https://example.com/login",
            "type": "login"
        })
        assert result["success"] is False, "login 类型应返回 success=False"
        assert "登录" in result["error"], "login 类型应包含登录提示"
        print(f"handle_webview_request(login) 测试通过")

        handler.close()
        print("所有自检通过")
    else:
        print("Selenium 不可用，跳过渲染测试")
        # 边界用例: Selenium 不可用时 handle_webview_request 应返回错误
        result = handler.handle_webview_request({
            "url": "https://example.com",
            "type": "load"
        })
        assert result["success"] is False, "Selenium 不可用时应返回 success=False"
        assert "不可用" in result["error"], "应包含不可用提示"
        print("降级测试通过")
