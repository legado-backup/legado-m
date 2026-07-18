#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebView 委托模块：薄壳包装 WebViewHandler，提供统一的 delegate 接口。

委托路径：debug_runner → WebViewDelegate → WebViewHandler → Selenium/Chrome

源码参照: io.legado.app.help.http.BackstageWebView (Android WebView)
"""
from __future__ import annotations

from typing import Optional

from legado_client.client.webview_handler import WebViewHandler


class WebViewDelegate:
    """WebView 渲染委托器，包装 WebViewHandler 提供 delegate 模式接口。

    当 JAR 仿真服务端检测到 webView 需求时（BackstageWebView/JsExtensions.webView()），
    抛出 WebViewRequiredException，Python 客户端捕获后通过本委托器用 Selenium 渲染页面，
    再将渲染后的 HTML 传回 JAR 用 AnalyzeRule 解析。
    """

    def __init__(self, headless: bool = True, chrome_path: Optional[str] = None,
                 chromedriver_path: Optional[str] = None):
        """初始化 WebView 委托器。

        Args:
            headless: 是否无头模式
            chrome_path: Chrome 可执行文件路径（自动检测时传 None）
            chromedriver_path: chromedriver 路径（自动检测时传 None）
        """
        self._handler = WebViewHandler(
            headless=headless,
            chrome_path=chrome_path,
            chromedriver_path=chromedriver_path
        )

    def is_available(self) -> bool:
        """检测 Selenium + Chrome 是否可用"""
        return self._handler.is_available()

    def handle_webview_request(self, request: dict) -> dict:
        """处理 WebView 渲染请求。

        Args:
            request: WebView 请求字典，含 url/js/timer 等字段

        Returns:
            dict: {success: bool, html: str, error: str}
        """
        return self._handler.handle_webview_request(request)

    def close(self) -> None:
        """关闭 WebDriver 释放资源"""
        if self._handler.driver is not None:
            try:
                self._handler.driver.quit()
            except Exception:
                pass
            self._handler.driver = None

    def __enter__(self) -> "WebViewDelegate":
        return self

    def __exit__(self, *args) -> None:
        self.close()


if __name__ == "__main__":
    # 最小自检
    delegate = WebViewDelegate()
    print(f"WebViewDelegate 可用性: {delegate.is_available()}")
    print("✅ 导入自检通过")
