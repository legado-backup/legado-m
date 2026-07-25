#!/usr/bin/env python3
"""
smart_http_client.py - Legado 书源/订阅源 Skill 的网络请求增强模块（7.9）

提供自适应请求频率、代理池、UA池、自动重试、Referer自动携带、请求日志的 HTTP 客户端。

特性:
    - 请求重试：超时重试3次 / DNS错误切换代理 / 连接拒绝等待5秒重试
    - 频率自适应：429/503 降速，正常响应加速
    - UA池：内置5个常见浏览器UA，随机选择，支持指定
    - Referer自动携带：自动携带上一页URL作为Referer
    - 请求日志：记录完整请求/响应日志

用法:
    from smart_http_client import SmartHttpClient

    client = SmartHttpClient()
    client.set_rate_limit(2)  # 每秒2个请求
    client.add_proxy("http://127.0.0.1:8080")
    resp = client.get("https://example.com")
    print(client.get_request_log())
"""

import random
import sys
import time
from datetime import datetime

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 内置 UA 池（5个常见浏览器）
# ---------------------------------------------------------------------------

DEFAULT_UA_POOL = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 重试策略常量
MAX_TIMEOUT_RETRIES = 3       # 超时最大重试次数
CONN_REFUSED_WAIT = 5         # 连接拒绝等待秒数
RATE_BACKOFF_FACTOR = 1.5     # 降速倍数
RATE_SPEEDUP_FACTOR = 0.9     # 加速倍数
MIN_INTERVAL = 0.1            # 最小请求间隔（秒）


class SmartHttpClient:
    """自适应 HTTP 客户端：频率限制 + 代理池 + UA池 + 自动重试。

    Attributes:
        _proxy_pool: 代理URL列表
        _ua_pool: User-Agent列表
        _min_interval: 最小请求间隔（秒），由频率限制推导
        _current_interval: 当前请求间隔（自适应调整）
        _last_url: 上次请求的URL（用于Referer）
        _request_log: 请求日志列表
    """

    def __init__(self, proxy=None, ua=None):
        """初始化客户端。

        Args:
            proxy: 可选，初始代理URL（如 "http://127.0.0.1:8080"）
            ua: 可选，指定固定UA（不指定则从UA池随机选择）
        """
        if requests is None:
            raise ImportError("requests 库未安装，请运行: pip install requests")

        # 代理池
        self._proxy_pool = []
        if proxy:
            self._proxy_pool.append(proxy)

        # UA池
        self._ua_pool = list(DEFAULT_UA_POOL)
        self._fixed_ua = ua  # 指定固定UA时优先使用

        # 频率限制（默认每秒10个请求）
        self._min_interval = 0.1
        self._current_interval = 0.1
        self._last_request_time = 0.0

        # Referer 自动携带
        self._last_url = None

        # 请求日志
        self._request_log = []

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def set_rate_limit(self, requests_per_second):
        """设置请求频率限制。

        Args:
            requests_per_second: 每秒最大请求数（如 2 表示每秒最多2个请求）
        """
        if requests_per_second <= 0:
            return
        self._min_interval = 1.0 / requests_per_second
        # 重置当前间隔为最小值（用户显式设置频率时重置自适应状态）
        self._current_interval = self._min_interval

    def add_proxy(self, proxy_url):
        """添加代理到代理池。

        Args:
            proxy_url: 代理URL（如 "http://127.0.0.1:8080" 或 "socks5://127.0.0.1:1080"）
        """
        if proxy_url and proxy_url not in self._proxy_pool:
            self._proxy_pool.append(proxy_url)

    def add_ua(self, ua):
        """添加 UA 到 UA池。

        Args:
            ua: User-Agent 字符串
        """
        if ua and ua not in self._ua_pool:
            self._ua_pool.append(ua)

    def get_request_log(self):
        """获取请求日志副本。

        Returns:
            list[dict]: 请求日志列表，每条包含 timestamp/method/url/status_code/
                        duration_ms/retries/error
        """
        return list(self._request_log)

    def get(self, url, **kwargs):
        """GET 请求，自动重试。

        Args:
            url: 请求URL
            **kwargs: 传递给 requests.get 的额外参数（headers/params/data 等）

        Returns:
            requests.Response 或 None（全部重试失败时）
        """
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        """POST 请求，自动重试。

        Args:
            url: 请求URL
            **kwargs: 传递给 requests.post 的额外参数

        Returns:
            requests.Response 或 None（全部重试失败时）
        """
        return self._request("POST", url, **kwargs)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _pick_ua(self):
        """选择 UA：固定UA优先，否则从UA池随机选择。"""
        if self._fixed_ua:
            return self._fixed_ua
        return random.choice(self._ua_pool) if self._ua_pool else DEFAULT_UA_POOL[0]

    def _pick_proxy(self):
        """从代理池随机选择代理（无代理时返回None）。"""
        if not self._proxy_pool:
            return None
        return random.choice(self._proxy_pool)

    def _wait_rate_limit(self):
        """频率限制：确保两次请求间隔不小于当前间隔。"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._current_interval:
            time.sleep(self._current_interval - elapsed)
        self._last_request_time = time.time()

    def _adjust_rate_up(self):
        """降速：检测到429/503时增加请求间隔。"""
        self._current_interval = min(
            self._current_interval * RATE_BACKOFF_FACTOR, 30.0  # 上限30秒
        )

    def _adjust_rate_down(self):
        """加速：正常响应时减少请求间隔（不低于最小值）。"""
        self._current_interval = max(
            self._current_interval * RATE_SPEEDUP_FACTOR, self._min_interval
        )

    def _request(self, method, url, **kwargs):
        """核心请求逻辑：频率限制 + UA选择 + Referer + 重试 + 日志。

        重试策略:
            - 超时(Timeout): 重试最多3次
            - DNS错误(gaierror): 切换代理重试
            - 连接拒绝(ConnectionError非DNS): 等待5秒重试
            - 429/503: 降速后重试（最多3次）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status_code": None,
            "duration_ms": 0,
            "retries": 0,
            "error": None,
        }
        start_time = time.time()
        retries = 0
        max_retries = MAX_TIMEOUT_RETRIES

        # 准备 headers：合并 UA 和 Referer
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("User-Agent", self._pick_ua())
        # Referer 自动携带（用户未显式设置时）
        if self._last_url and "Referer" not in headers:
            headers["Referer"] = self._last_url

        # 代理
        proxies = kwargs.pop("proxies", None)
        if proxies is None:
            proxy = self._pick_proxy()
            if proxy:
                proxies = {"http": proxy, "https": proxy}

        # 默认超时
        kwargs.setdefault("timeout", 15)
        kwargs.setdefault("verify", False)
        kwargs.setdefault("allow_redirects", True)

        response = None
        last_error = None

        while retries <= max_retries:
            try:
                self._wait_rate_limit()
                if method == "GET":
                    response = requests.get(url, headers=headers, proxies=proxies, **kwargs)
                else:
                    response = requests.post(url, headers=headers, proxies=proxies, **kwargs)

                # 频率自适应：429/503 降速并重试
                if response.status_code in (429, 503):
                    self._adjust_rate_up()
                    last_error = f"HTTP {response.status_code}"
                    retries += 1
                    log_entry["retries"] = retries
                    if retries <= max_retries:
                        time.sleep(self._current_interval)
                        continue
                    break  # 重试耗尽，返回最后响应

                # 正常响应：加速
                self._adjust_rate_down()
                log_entry["status_code"] = response.status_code
                break

            except requests.exceptions.Timeout as e:
                last_error = f"Timeout: {e}"
                retries += 1
                log_entry["retries"] = retries
                if retries <= max_retries:
                    continue
                break

            except requests.exceptions.ConnectionError as e:
                # 区分 DNS 错误和连接拒绝
                err_str = str(e).lower()
                if "gaierror" in err_str or "name or service not known" in err_str:
                    # DNS 错误：切换代理
                    last_error = f"DNS Error: {e}"
                    if self._proxy_pool:
                        proxy = self._pick_proxy()
                        if proxy:
                            proxies = {"http": proxy, "https": proxy}
                    retries += 1
                    log_entry["retries"] = retries
                    if retries <= max_retries:
                        continue
                else:
                    # 连接拒绝：等待5秒重试
                    last_error = f"ConnectionError: {e}"
                    retries += 1
                    log_entry["retries"] = retries
                    if retries <= max_retries:
                        time.sleep(CONN_REFUSED_WAIT)
                        continue
                break

            except requests.exceptions.RequestException as e:
                last_error = f"RequestException: {e}"
                retries += 1
                log_entry["retries"] = retries
                if retries <= max_retries:
                    continue
                break

        # 记录日志
        log_entry["duration_ms"] = int((time.time() - start_time) * 1000)
        if response is not None:
            log_entry["status_code"] = response.status_code
        log_entry["error"] = last_error
        self._request_log.append(log_entry)

        # 更新 Referer（成功响应时记录URL）
        if response is not None and response.status_code < 400:
            self._last_url = url

        return response


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== smart_http_client.py 自检 ===")

    # 边界用例1：实例化
    print("\n[1] 实例化自检:")
    c = SmartHttpClient()
    assert c._proxy_pool == [], "初始代理池应为空"
    assert len(c._ua_pool) == 5, f"内置UA池应有5个UA，实际{len(c._ua_pool)}"
    print("   OK - 实例化成功，UA池5个")

    # 边界用例2：频率限制设置
    print("\n[2] set_rate_limit 自检:")
    c.set_rate_limit(2)  # 每秒2个请求
    assert abs(c._min_interval - 0.5) < 0.001, "2 req/s 应得 0.5s 间隔"
    print(f"   OK - 2 req/s -> interval={c._min_interval}s")

    # 边界用例3：代理池和UA池
    print("\n[3] add_proxy / add_ua 自检:")
    c.add_proxy("http://127.0.0.1:8080")
    c.add_proxy("http://127.0.0.1:8080")  # 重复添加应忽略
    assert len(c._proxy_pool) == 1, "重复代理不应重复添加"
    c.add_ua("TestBot/1.0")
    assert "TestBot/1.0" in c._ua_pool
    print("   OK - 代理池去重，UA池添加成功")

    # 边界用例4：UA选择（固定UA优先）
    print("\n[4] UA 选择自检:")
    c2 = SmartHttpClient(ua="FixedUA/1.0")
    assert c2._pick_ua() == "FixedUA/1.0", "固定UA应优先"
    c2._fixed_ua = None
    ua = c2._pick_ua()
    assert ua in DEFAULT_UA_POOL, "非固定时应从池中选择"
    print("   OK - 固定UA优先，否则随机选择")

    # 边界用例5：频率自适应
    print("\n[5] 频率自适应自检:")
    c3 = SmartHttpClient()
    c3.set_rate_limit(10)  # interval=0.1
    base = c3._current_interval
    c3._adjust_rate_up()  # 降速
    assert c3._current_interval > base, "降速应增加间隔"
    c3._adjust_rate_down()  # 加速
    assert c3._current_interval >= c3._min_interval, "加速不应低于最小间隔"
    print(f"   OK - 降速后={c3._current_interval:.3f}s，加速后不低于{c3._min_interval}s")

    # 边界用例6：日志结构
    print("\n[6] 请求日志结构自检:")
    log = c.get_request_log()
    assert isinstance(log, list), "日志应为列表"
    print(f"   OK - 日志类型正确，当前{len(log)}条")

    print("\n=== 自检完成 ===")
