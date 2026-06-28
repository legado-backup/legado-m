#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR 委托模块：占位实现，提供统一的 delegate 接口。

委托路径：debug_runner → OcrDelegate → （未来）Tesseract/PaddleOCR

源码参照: io.legado.app.help.http.JsExtensions.getVerificationCode (Android OCR)
"""
from __future__ import annotations

from typing import Optional


class OcrDelegate:
    """OCR 识别委托器，占位实现。

    当书源/订阅源需要验证码识别时（JsExtensions.getVerificationCode），
    通过本委托器执行 OCR 识别。当前为占位实现，需用户手动处理验证码。

    升级路径：集成 Tesseract OCR 或 PaddleOCR，实现 recognize() 方法。
    """

    def __init__(self, engine: str = "tesseract"):
        """初始化 OCR 委托器。

        Args:
            engine: OCR 引擎名称（tesseract/paddle），当前未实现
        """
        self.engine = engine
        self._available = False  # 占位实现，始终不可用

    def is_available(self) -> bool:
        """检测 OCR 引擎是否可用"""
        return self._available

    def recognize(self, image_data: bytes, image_type: str = "png") -> str:
        """识别图片中的文字（验证码）。

        Args:
            image_data: 图片二进制数据
            image_type: 图片格式（png/jpg）

        Returns:
            str: 识别出的文字

        Raises:
            NotImplementedError: 当前为占位实现，始终抛出此异常
        """
        # 简化说明: OCR 识别未实现 | 已知上限: 验证码源需用户手动处理 | 升级路径: 集成 Tesseract OCR 或 PaddleOCR
        raise NotImplementedError(
            "OCR 识别未实现。"
            "升级路径：安装 tesseract-ocr 并 pip install pytesseract，"
            "或 pip install paddleocr，然后实现 recognize() 方法。"
            "当前需用户手动处理验证码。"
        )

    def recognize_from_url(self, image_url: str) -> str:
        """从 URL 下载图片并识别（占位实现）。

        Args:
            image_url: 图片 URL

        Returns:
            str: 识别出的文字

        Raises:
            NotImplementedError: 当前为占位实现
        """
        # 简化说明: URL 图片 OCR 未实现 | 已知上限: 验证码源需用户手动处理 | 升级路径: 同 recognize()
        raise NotImplementedError(
            "URL 图片 OCR 识别未实现。"
            "升级路径：实现图片下载 + recognize() 调用。"
            "当前需用户手动处理验证码。"
        )


if __name__ == "__main__":
    # 最小自检
    delegate = OcrDelegate()
    print(f"OcrDelegate 可用性: {delegate.is_available()}")
    # 验证 recognize() 抛出 NotImplementedError
    try:
        delegate.recognize(b"fake_image_data")
        assert False, "应抛出 NotImplementedError"
    except NotImplementedError as e:
        print(f"✅ recognize() 正确抛出 NotImplementedError: {str(e)[:50]}...")
    print("✅ 导入自检通过")
