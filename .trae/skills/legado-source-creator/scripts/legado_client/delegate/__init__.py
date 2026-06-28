#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""委托模块：WebView 渲染委托 + OCR 识别委托。

将平台相关能力（Selenium WebView 渲染、OCR 图片识别）从核心流程中解耦，
通过 delegate 模式委托给具体实现，便于独立测试和按需启用。
"""
from legado_client.delegate.webview_delegate import WebViewDelegate
from legado_client.delegate.ocr_delegate import OcrDelegate

__all__ = ["WebViewDelegate", "OcrDelegate"]
