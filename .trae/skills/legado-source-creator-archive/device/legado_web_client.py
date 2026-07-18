#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legado Web 客户端：封装 Legado App 的 26 个 HTTP API + 3 个 WebSocket API。

源码参考：io.legado.app.web.controller.*

HTTP 默认端口 1122，WebSocket 端口 = HTTP + 1（源码硬编码）。
HTTP 响应格式：ReturnData {isSuccess, errorMsg, data}，需提取 data 字段。
特殊端点：/cover 和 /image 返回 image/png（非 JSON）。
/addLocalBook 使用 multipart form-data。
WebSocket 调试返回纯文本日志（非 JSON），通过关闭帧结束。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger(__name__)


class LegadoWebClient:
    """Legado Web 服务客户端，封装 HTTP + WebSocket API。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 1122, auth_token: str = ""):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self._base_url = f"http://{host}:{port}"
        self._ws_url = f"ws://{host}:{port + 1}"  # WebSocket 端口 = HTTP + 1
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))

    # ==================== 内部方法 ====================

    def _headers(self) -> dict[str, str]:
        """构建请求头。"""
        h = {"Content-Type": "application/json"}
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    async def _get(self, path: str, params: dict | None = None) -> Any:
        """GET 请求，提取 ReturnData.data。"""
        resp = await self._client.get(
            f"{self._base_url}{path}",
            params=params,
            headers=self._headers(),
        )
        return self._parse_response(resp, path)

    async def _post(self, path: str, json_data: Any = None) -> Any:
        """POST JSON 请求，提取 ReturnData.data。"""
        resp = await self._client.post(
            f"{self._base_url}{path}",
            json=json_data,
            headers=self._headers(),
        )
        return self._parse_response(resp, path)

    async def _post_raw(self, path: str, data: bytes, content_type: str) -> Any:
        """POST 原始数据请求。"""
        h = self._headers()
        h["Content-Type"] = content_type
        resp = await self._client.post(
            f"{self._base_url}{path}",
            content=data,
            headers=h,
        )
        return self._parse_response(resp, path)

    async def _get_binary(self, path: str, params: dict | None = None) -> bytes | None:
        """GET 请求，返回二进制内容（用于 /cover 和 /image）。"""
        resp = await self._client.get(
            f"{self._base_url}{path}",
            params=params,
            headers=self._headers(),
        )
        if resp.status_code == 200:
            return resp.content
        logger.warning("二进制请求失败: %s status=%d", path, resp.status_code)
        return None

    def _parse_response(self, resp: httpx.Response, path: str) -> Any:
        """解析 HTTP 响应，提取 ReturnData.data。"""
        if resp.status_code != 200:
            logger.error("HTTP %d: %s", resp.status_code, path)
            return None
        try:
            data = resp.json()
            # ReturnData 格式：{isSuccess, errorMsg, data}
            if isinstance(data, dict):
                if not data.get("isSuccess", True):
                    logger.warning("Legado API 失败: %s error=%s", path, data.get("errorMsg", ""))
                    return None
                return data.get("data", data)
            return data
        except (json.JSONDecodeError, ValueError):
            # 非JSON响应（如纯文本），返回原始文本
            return resp.text

    # ==================== HTTP API（书源管理） ====================

    async def get_book_sources(self) -> list[dict]:
        """获取所有书源列表。"""
        result = await self._get("/getBookSources")
        return result if isinstance(result, list) else []

    async def save_book_source(self, source: dict) -> bool:
        """保存单个书源。"""
        result = await self._post("/saveBookSource", json_data=source)
        return result is not None

    async def save_book_sources(self, sources: list[dict]) -> bool:
        """批量保存书源。"""
        result = await self._post("/saveBookSources", json_data=sources)
        return result is not None

    async def delete_book_sources(self, sources: list[dict]) -> bool:
        """删除书源。"""
        result = await self._post("/deleteBookSources", json_data=sources)
        return result is not None

    # ==================== HTTP API（订阅源管理） ====================

    async def get_rss_sources(self) -> list[dict]:
        """获取所有订阅源列表。"""
        result = await self._get("/getRssSources")
        return result if isinstance(result, list) else []

    async def save_rss_source(self, source: dict) -> bool:
        """保存单个订阅源。"""
        result = await self._post("/saveRssSource", json_data=source)
        return result is not None

    async def save_rss_sources(self, sources: list[dict]) -> bool:
        """批量保存订阅源。"""
        result = await self._post("/saveRssSources", json_data=sources)
        return result is not None

    async def delete_rss_sources(self, sources: list[dict]) -> bool:
        """删除订阅源。"""
        result = await self._post("/deleteRssSources", json_data=sources)
        return result is not None

    # ==================== HTTP API（书籍管理） ====================

    async def get_books(self) -> list[dict]:
        """获取所有书籍列表。"""
        result = await self._get("/getBookshelf")
        return result if isinstance(result, list) else []

    async def save_book(self, book: dict) -> bool:
        """保存书籍。"""
        result = await self._post("/saveBook", json_data=book)
        return result is not None

    async def delete_book(self, book: dict) -> bool:
        """删除书籍。"""
        result = await self._post("/deleteBook", json_data=book)
        return result is not None

    async def save_book_progress(self, book: dict) -> bool:
        """保存阅读进度。"""
        result = await self._post("/saveBookProgress", json_data=book)
        return result is not None

    # ==================== HTTP API（本地书导入） ====================

    async def add_local_book(self, parameters: dict, files: dict) -> bool:
        """添加本地书籍（multipart form-data）。

        Args:
            parameters: 表单参数
            files: 文件数据，如 {"file": ("book.epub", b"...", "application/epub+zip")}
        """
        try:
            # 使用 httpx 的 multipart 上传
            resp = await self._client.post(
                f"{self._base_url}/addLocalBook",
                data=parameters,
                files=files,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("addLocalBook 失败: %s", e)
            return False

    # ==================== HTTP API（阅读配置） ====================

    async def save_read_config(self, config: dict) -> bool:
        """保存阅读配置。"""
        result = await self._post("/saveReadConfig", json_data=config)
        return result is not None

    async def get_read_config(self) -> dict:
        """获取阅读配置。"""
        result = await self._get("/getReadConfig")
        return result if isinstance(result, dict) else {}

    # ==================== HTTP API（刷新 & 图片） ====================

    async def refresh_toc(self, url: str) -> dict:
        """刷新目录。

        Args:
            url: 书籍 URL
        """
        result = await self._post("/refreshToc", json_data={"url": url})
        return result if isinstance(result, dict) else {}

    async def get_cover(self, url: str) -> bytes | None:
        """获取封面图片（返回 image/png 二进制数据）。"""
        return await self._get_binary("/cover", params={"url": url})

    async def get_image(self, url: str) -> bytes | None:
        """获取正文图片（返回 image/png 二进制数据）。"""
        return await self._get_binary("/image", params={"url": url})

    # ==================== HTTP API（V2 接口） ====================

    async def get_source_list(self) -> list:
        """获取源列表（V2 接口）。"""
        result = await self._get("/getSourceList")
        return result if isinstance(result, list) else []

    async def get_book_source(self, url: str) -> dict:
        """获取单个书源（V2 接口）。

        Args:
            url: 书源 URL
        """
        result = await self._get("/getBookSource", params={"url": url})
        return result if isinstance(result, dict) else {}

    async def save_book_source_v2(self, source: dict) -> bool:
        """保存书源（V2 接口，支持单条和批量）。"""
        result = await self._post("/saveBookSource", json_data=source)
        return result is not None

    # ==================== HTTP API（测试） ====================

    async def test_book_source(self, source: dict) -> dict:
        """测试书源（HTTP 模式，非 WebSocket）。

        Args:
            source: 书源 JSON
        """
        result = await self._post("/testBookSource", json_data=source)
        return result if isinstance(result, dict) else {}

    async def test_replace_rule(self, rule: dict) -> dict:
        """测试替换规则。

        Args:
            rule: 替换规则 JSON
        """
        result = await self._post("/testReplaceRule", json_data=rule)
        return result if isinstance(result, dict) else {}

    # ==================== WebSocket API ====================

    async def ws_search_book(
        self,
        key: str,
        callback: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """WebSocket 搜索书籍。

        通信协议（参考 BookSearchWebSocket.kt）：
        1. 连接 ws://host:1123/searchBook
        2. 发送 JSON: {"key": "搜索关键词"}
        3. 服务端搜索所有启用的书源
        4. 返回搜索结果 JSON（SearchBook 列表）

        Args:
            key: 搜索关键词
            callback: 逐行回调（可选）

        Returns:
            搜索结果列表
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets 库未安装，请 pip install websockets")
            return []

        results: list[dict] = []
        payload = json.dumps({"key": key}, ensure_ascii=False)

        try:
            async with websockets.connect(
                f"{self._ws_url}/searchBook",
                additional_headers=self._headers(),
            ) as ws:
                await ws.send(payload)
                async for message in ws:
                    text = message if isinstance(message, str) else message.decode("utf-8")
                    if callback:
                        callback(text)
                    # 尝试解析为 JSON（搜索结果可能是 JSON 数组）
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            results.extend(parsed)
                        elif isinstance(parsed, dict):
                            results.append(parsed)
                    except (json.JSONDecodeError, ValueError):
                        # 纯文本日志行，跳过
                        pass
        except Exception as e:
            logger.error("ws_search_book 失败: %s", e)

        return results

    async def ws_debug_book_source(
        self,
        source: dict,
        key: str,
        callback: Callable[[str], None] | None = None,
    ) -> list[str]:
        """WebSocket 调试书源。

        通信协议（参考 BookSourceDebugWebSocket.kt）：
        1. 连接 ws://host:1123/bookSourceDebug
        2. 发送 JSON: {"tag": "书源URL(bookSourceUrl)", "key": "搜索关键词"}
        3. 服务端从数据库查找书源并执行调试
        4. 逐行返回调试日志，state=-1 或 1000 时关闭

        Args:
            source: 书源 JSON（用于提取 bookSourceUrl）
            key: 搜索关键词
            callback: 逐行回调（可选）

        Returns:
            调试日志行列表
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets 库未安装")
            return []

        logs: list[str] = []
        # 提取 tag = bookSourceUrl
        tag = source.get("bookSourceUrl", "")
        if not tag:
            logs.append("[ERROR] 书源缺少 bookSourceUrl 字段")
            return logs

        payload = json.dumps({"tag": tag, "key": key}, ensure_ascii=False)

        try:
            async with websockets.connect(
                f"{self._ws_url}/bookSourceDebug",
                additional_headers=self._headers(),
            ) as ws:
                await ws.send(payload)
                async for message in ws:
                    text = message if isinstance(message, str) else message.decode("utf-8")
                    logs.append(text)
                    if callback:
                        callback(text)
        except Exception as e:
            logger.error("ws_debug_book_source 失败: %s", e)
            logs.append(f"[ERROR] {e}")

        return logs

    async def ws_debug_rss_source(
        self,
        source: dict,
        callback: Callable[[str], None] | None = None,
    ) -> list[str]:
        """WebSocket 调试订阅源。

        通信协议（参考 RssSourceDebugWebSocket.kt）：
        1. 连接 ws://host:1123/rssSourceDebug
        2. 发送 JSON: {"tag": "源URL(sourceUrl)"}
        3. 服务端从数据库查找订阅源并执行调试
        4. 逐行返回调试日志，state=-1 或 1000 时关闭

        Args:
            source: 订阅源 JSON（用于提取 sourceUrl）
            callback: 逐行回调（可选）

        Returns:
            调试日志行列表
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets 库未安装")
            return []

        logs: list[str] = []
        # 提取 tag = sourceUrl
        tag = source.get("sourceUrl", "")
        if not tag:
            logs.append("[ERROR] 订阅源缺少 sourceUrl 字段")
            return logs

        payload = json.dumps({"tag": tag}, ensure_ascii=False)

        try:
            async with websockets.connect(
                f"{self._ws_url}/rssSourceDebug",
                additional_headers=self._headers(),
            ) as ws:
                await ws.send(payload)
                async for message in ws:
                    text = message if isinstance(message, str) else message.decode("utf-8")
                    logs.append(text)
                    if callback:
                        callback(text)
        except Exception as e:
            logger.error("ws_debug_rss_source 失败: %s", e)
            logs.append(f"[ERROR] {e}")

        return logs

    # ==================== 连接测试 ====================

    async def test_connection(self) -> dict:
        """测试与 Legado 设备的连接状态。

        使用轻量级请求避免拉取大量数据超时。
        """
        try:
            # 轻量级检测：请求根路径或任意 API
            resp = await self._client.get(
                f"{self._base_url}/",
                headers=self._headers(),
                timeout=10.0,
            )
            connected = resp.status_code == 200
            book_count = 0
            if connected:
                # 尝试快速获取书源数量（仅请求前1条）
                try:
                    sources = await self._client.get(
                        f"{self._base_url}/getBookSources",
                        params={"page": 1, "size": 1},
                        headers=self._headers(),
                        timeout=5.0,
                    )
                    if sources.status_code == 200:
                        data = sources.json()
                        if isinstance(data, list):
                            book_count = len(data)
                except Exception:
                    pass
            return {
                "connected": connected,
                "host": self.host,
                "port": self.port,
                "book_source_count": book_count,
                "error": None,
            }
        except Exception as e:
            return {
                "connected": False,
                "host": self.host,
                "port": self.port,
                "book_source_count": 0,
                "error": str(e),
            }

    # ==================== 生命周期 ====================

    async def close(self) -> None:
        """关闭 HTTP 客户端。"""
        await self._client.aclose()

    async def __aenter__(self) -> "LegadoWebClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


if __name__ == "__main__":
    import asyncio

    # 自检：1正常 + 1边界 + 1异常
    # 正常用例：创建客户端
    client = LegadoWebClient(host="127.0.0.1", port=1122)
    assert client._base_url == "http://127.0.0.1:1122"
    assert client._ws_url == "ws://127.0.0.1:1123"
    print("✅ 正常用例：客户端创建正确")

    # 边界用例：自定义端口
    client2 = LegadoWebClient(host="192.168.1.100", port=9999, auth_token="test")
    assert client2._base_url == "http://192.168.1.100:9999"
    assert client2._ws_url == "ws://192.168.1.100:10000"
    assert client2.auth_token == "test"
    print("✅ 边界用例：自定义端口和Token")

    # 异常用例：连接不可达设备
    async def _test_unreachable():
        result = await client.test_connection()
        assert result["connected"] is False
        assert result["error"] is not None
        await client.close()
        print("✅ 异常用例：不可达设备返回 connected=False")

    asyncio.run(_test_unreachable())
