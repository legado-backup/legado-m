"""异步 HTTP 客户端：频率控制、User-Agent、超时、重试。

所有 fetcher 模块共享此客户端实例，确保请求间隔 ≥ fetch_delay 秒。
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from legado_client.utils.config import config
from legado_client.utils.logger import get_logger

logger = get_logger("legado_client.http_client")

# 默认 User-Agent
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class RateLimitedClient:
    """带频率限制的异步 HTTP 客户端。

    - 请求间隔 ≥ config.fetch_delay 秒（默认 1.0s）
    - 超时 = config.fetch_timeout 秒（默认 30s）
    - 自动重试（最多 max_retries 次，仅对可重试状态码）
    """

    # 可重试的 HTTP 状态码
    _RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        delay: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        user_agent: str = _DEFAULT_UA,
    ) -> None:
        self._delay = delay if delay is not None else config.fetch_delay
        self._timeout = timeout if timeout is not None else config.fetch_timeout
        self._max_retries = max_retries
        self._ua = user_agent
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """懒初始化 httpx 客户端。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self._ua},
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                follow_redirects=True,
                verify=False,  # 简化说明：Windows 环境下 Python 常见 SSL 证书链不全 | 已知上限：中间人攻击风险 | 升级路径：使用 certifi 或系统证书
            )
        return self._client

    async def _throttle(self) -> None:
        """确保请求间隔 ≥ delay 秒。"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._delay:
                wait = self._delay - elapsed
                logger.debug("频率控制: 等待 %.2fs", wait)
                await asyncio.sleep(wait)
            self._last_request_time = time.monotonic()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """发送 GET 请求（带频率控制和重试）。"""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """发送 POST 请求（带频率控制和重试）。"""
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """通用请求方法：频率控制 + 重试。"""
        client = await self._ensure_client()
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            await self._throttle()
            try:
                resp = await client.request(method, url, **kwargs)
                if resp.status_code in self._RETRYABLE_STATUS:
                    logger.warning(
                        "请求 %s 返回 %d，重试 %d/%d",
                        url, resp.status_code, attempt, self._max_retries,
                    )
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    continue
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
                last_exc = exc
                logger.warning(
                    "请求 %s 异常: %s，重试 %d/%d",
                    url, exc, attempt, self._max_retries,
                )

        raise last_exc or httpx.HTTPError(f"请求 {url} 失败，已重试 {self._max_retries} 次")

    async def get_text(self, url: str, **kwargs) -> str:
        """GET 请求并返回文本内容。"""
        resp = await self.get(url, **kwargs)
        resp.raise_for_status()
        return resp.text

    async def get_bytes(self, url: str, **kwargs) -> bytes:
        """GET 请求并返回字节内容。"""
        resp = await self.get(url, **kwargs)
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        """关闭客户端。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# 模块级共享实例
shared_client = RateLimitedClient()
