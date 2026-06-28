#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
user_interaction.py - 用户交互场景处理器

AI遇到需用户介入场景时输出标准化交互请求。
方向15核心模块：用户交互场景设计。

用法:
    from legado_client.client.user_interaction import create_interaction_request
    request = create_interaction_request(source, "site_down", "网站不可达")
"""
from __future__ import annotations

from typing import Optional

# ==================== 3.15: Web 模式降级 ====================
_web_mode: bool = False
_ws_callback = None


def set_web_mode(enabled: bool = True, ws_callback=None) -> None:
    """设置 Web 模式。Web 模式下用户交互降级为日志输出。"""
    global _web_mode, _ws_callback
    _web_mode = enabled
    _ws_callback = ws_callback


def is_web_mode() -> bool:
    """是否处于 Web 模式。"""
    return _web_mode


class UserInteractionHandler:
    """处理AI使用skill时的用户交互场景

    当debug-source.py检测到需要用户介入的场景时，
    调用对应方法生成标准化交互请求。
    """

    def handle_url_unreachable(self, source: dict, error: Optional[str] = None) -> dict:
        """URL不可达：向用户报告并请求新URL

        Args:
            source: 书源/订阅源JSON字典
            error: 错误信息（可选）

        Returns:
            标准化交互请求字典
        """
        url = source.get("bookSourceUrl") or source.get("sourceUrl") or ""
        return {
            "type": "url_unreachable",
            "message": f"网站 {url} 不可达",
            "suggestion": "请确认网站是否已迁移，或提供新的URL",
            "current_url": url,
            "needs_user_input": "new_url",
        }

    def handle_login_required(self, source: dict, html_analysis: Optional[dict] = None) -> dict:
        """需登录：向用户请求Cookie

        Args:
            source: 书源/订阅源JSON字典
            html_analysis: HTML分析结果（可选）

        Returns:
            标准化交互请求字典
        """
        url = source.get("bookSourceUrl") or source.get("sourceUrl") or ""
        return {
            "type": "login_required",
            "message": f"网站 {url} 需要登录",
            "suggestion": "请在浏览器中登录该网站，然后提供Cookie值",
            "cookie_guide": "F12→Network→任意请求→Request Headers→Cookie",
            "needs_user_input": "cookie",
        }

    def handle_captcha(self, source: dict, html_analysis: Optional[dict] = None) -> dict:
        """验证码：请求用户手动处理

        Args:
            source: 书源/订阅源JSON字典
            html_analysis: HTML分析结果（可选）

        Returns:
            标准化交互请求字典
        """
        url = source.get("bookSourceUrl") or source.get("sourceUrl") or ""
        return {
            "type": "captcha_detected",
            "message": f"网站 {url} 需要验证码",
            "suggestion": "请在浏览器中手动访问该网站并完成验证码",
            "needs_user_input": "manual_captcha_resolution",
        }

    def handle_cf_protection(self, source: dict, html_analysis: Optional[dict] = None) -> dict:
        """Cloudflare保护：请求用户手动处理

        Args:
            source: 书源/订阅源JSON字典
            html_analysis: HTML分析结果（可选）

        Returns:
            标准化交互请求字典
        """
        url = source.get("bookSourceUrl") or source.get("sourceUrl") or ""
        return {
            "type": "cf_protection",
            "message": f"网站 {url} 受Cloudflare保护",
            "suggestion": "请在浏览器中手动访问该网站通过CF验证，然后提供Cookie值",
            "cookie_guide": "F12→Network→任意请求→Request Headers→Cookie",
            "needs_user_input": "cookie",
        }

    def detect_and_handle(self, source: dict, error_type: str,
                          error_msg: str = "") -> Optional[dict]:
        """根据错误类型自动选择处理方法。

        Web 模式下返回交互请求但不等待用户响应（降级为日志输出）。

        Args:
            source: 书源/订阅源JSON字典
            error_type: 错误类型（来自ErrorDiagnoser）
            error_msg: 错误消息

        Returns:
            交互请求字典，无需用户介入时返回None
        """
        if _web_mode:
            # Web 模式：生成请求但通过 WebSocket 推送，不阻塞
            result = None
            if error_type == "site_down":
                result = self.handle_url_unreachable(source, error_msg)
            elif error_type == "site_redesign":
                result = self.handle_url_unreachable(source, error_msg)
            if result and _ws_callback:
                try:
                    _ws_callback({"type": "user_interaction", **result})
                except Exception:
                    pass
            return result

        if error_type == "site_down":
            return self.handle_url_unreachable(source, error_msg)
        if error_type == "site_redesign":
            return self.handle_url_unreachable(source, error_msg)
        # 登录/验证码/CF保护需要从HTML分析中检测
        # 简化说明：当前仅基于error_type判断 | 已知上限：需HTML分析才能确认登录/验证码 | 升级路径：集成site_type_detector
        return None


# 模块级便捷函数
def create_interaction_request(source: dict, error_type: str,
                               error_msg: str = "") -> Optional[dict]:
    """创建用户交互请求（模块级便捷函数）"""
    return UserInteractionHandler().detect_and_handle(source, error_type, error_msg)


if __name__ == "__main__":
    # 自检：1正常用例 + 1边界用例
    handler = UserInteractionHandler()

    # 正常用例：URL不可达
    source = {"bookSourceName": "测试源", "bookSourceUrl": "https://www.test.com"}
    request = handler.handle_url_unreachable(source)
    assert request["type"] == "url_unreachable"
    assert request["needs_user_input"] == "new_url"
    print(f"✅ 正常用例: {request['type']} → {request['needs_user_input']}")

    # 边界用例：无需用户介入的错误类型
    request = handler.detect_and_handle(source, "rule_empty")
    assert request is None, f"rule_empty无需用户介入: {request}"
    print(f"✅ 边界用例: rule_empty → None")

    print("\n所有自检通过 (2/2)")
