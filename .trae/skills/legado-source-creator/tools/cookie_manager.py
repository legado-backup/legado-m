#!/usr/bin/env python3
"""
cookie_manager.py - Cookie/Session 管理增强

obstacle_resolver.py 的 persist_cookie 提供基础 Cookie 持久化（仅存字符串），
本模块在其基础上增强：结构化存储、过期检测、跨子域共享、浏览器导入、JVM 导出。

存储格式（tools/.cookie-cache/{domain}.json）:
    {
        "domain": "example.com",
        "cookies": {
            "sid": {"value": "abc", "expires": 1234567890, "path": "/"}
        },
        "saved_at": "2026-06-19 12:00:00"
    }

跨子域共享：a.example.com 与 b.example.com 归一化为 example.com（取最后两段），
与 JVM MockCookieStore.getSubDomain 算法一致。

用法:
    from cookie_manager import PersistentCookieStore
    store = PersistentCookieStore()
    store.save("example.com", "sid=abc; token=xyz")
    cookie = store.get_cookie_for_url("https://a.example.com/page")
"""

import json
import os
import re
import time
import urllib.parse

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CACHE_DIR = os.path.join(_TOOLS_DIR, ".cookie-cache")


def _safe_filename(name):
    """将字符串转为安全文件名"""
    return re.sub(r'[^\w.-]', '_', name)


def _normalize_domain(domain):
    """归一化域名为二级域名（最后两段），与 JVM MockCookieStore.getSubDomain 一致。

    简化说明: 取最后两段 | 已知上限: 对 .co.uk 等多段TLD不准确 | 升级路径: 引入 tldextract
    """
    if not domain:
        return domain
    domain = domain.split(":")[0]  # 去端口
    if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain) or ":" in domain:
        return domain  # IP 地址原样返回
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    return ".".join(parts[-2:])


def _parse_cookie_str(cookie_str):
    """将 'k1=v1; k2=v2' 解析为 dict {name: value}"""
    cookies = {}
    if not cookie_str:
        return cookies
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            name, _, value = pair.partition("=")
            cookies[name.strip()] = value.strip()
    return cookies


class PersistentCookieStore:
    """文件持久化 Cookie 管理器。

    每个二级域名一个 JSON 文件，支持过期检测与跨子域共享。
    """

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def _file_for(self, domain):
        return os.path.join(self.cache_dir, f"{_safe_filename(_normalize_domain(domain))}.json")

    def save(self, domain, cookies):
        """保存 Cookie。

        Args:
            domain: 域名（自动归一化为二级域名）
            cookies: 字符串 'k1=v1; k2=v2' 或 dict {name: value} 或
                     list[{name, value, expires, path}]（浏览器导出格式）

        Returns:
            str | None: 保存路径，失败返回 None
        """
        norm = _normalize_domain(domain)
        cookie_map = self._coerce_cookies(cookies)
        # 合并已有 Cookie（同域名增量更新）
        existing = self._load_raw(norm)
        existing.get("cookies", {}).update(cookie_map)
        existing["domain"] = norm
        existing["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._file_for(norm), "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            return self._file_for(norm)
        except OSError:
            return None

    @staticmethod
    def _coerce_cookies(cookies):
        """将多种输入统一为 {name: {value, expires, path}} 结构"""
        result = {}
        if not cookies:
            return result
        if isinstance(cookies, str):
            for name, value in _parse_cookie_str(cookies).items():
                result[name] = {"value": value, "expires": None, "path": "/"}
        elif isinstance(cookies, dict):
            for name, val in cookies.items():
                if isinstance(val, dict):
                    item = dict(val)
                    item.setdefault("value", "")
                    item.setdefault("expires", None)
                    item.setdefault("path", "/")
                    result[name] = item
                else:
                    result[name] = {"value": str(val), "expires": None, "path": "/"}
        elif isinstance(cookies, list):
            for item in cookies:
                name = item.get("name") if isinstance(item, dict) else None
                if not name:
                    continue
                result[name] = {
                    "value": item.get("value", ""),
                    "expires": item.get("expires") or item.get("expirationDate"),
                    "path": item.get("path", "/"),
                }
        return result

    def _load_raw(self, domain):
        """读取原始 JSON dict（不存在/损坏返回空骨架）"""
        path = self._file_for(_normalize_domain(domain))
        if not os.path.isfile(path):
            return {"domain": _normalize_domain(domain), "cookies": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 兼容 obstacle_resolver.persist_cookie 的旧格式（cookie 字符串）
            if "cookie" in data and "cookies" not in data:
                cookies = _parse_cookie_str(data.get("cookie", ""))
                data["cookies"] = {
                    n: {"value": v, "expires": None, "path": "/"}
                    for n, v in cookies.items()
                }
            data.setdefault("cookies", {})
            return data
        except (OSError, ValueError):
            return {"domain": _normalize_domain(domain), "cookies": {}}

    def load(self, domain):
        """加载 Cookie，返回 {name: {value, expires, path}}，无则空 dict"""
        return self._load_raw(domain).get("cookies", {})

    def load_all(self):
        """启动时加载所有持久化 Cookie。

        Returns:
            dict[domain] = {name: {value, expires, path}}
        """
        result = {}
        for name in self.list_all():
            result[name] = self.load(name)
        return result

    def delete(self, domain):
        """删除 Cookie 文件，返回是否删除成功"""
        path = self._file_for(domain)
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
        except OSError:
            pass
        return False

    def list_all(self):
        """列出所有已存储的 Cookie 域名（去 .json 后缀）"""
        if not os.path.isdir(self.cache_dir):
            return []
        names = []
        for fn in os.listdir(self.cache_dir):
            if fn.endswith(".json"):
                names.append(fn[:-5])
        return sorted(names)

    def get_cookie_for_url(self, url):
        """根据 URL 获取对应域名的 Cookie（跨子域共享）。

        Returns:
            str: 'k1=v1; k2=v2' 格式，无则空串
        """
        domain = urllib.parse.urlparse(url).netloc
        if not domain:
            return ""
        cookies = self.load(domain)
        # 过滤过期项
        pairs = [
            f"{n}={c['value']}"
            for n, c in cookies.items()
            if not self.is_expired(c)
        ]
        return "; ".join(pairs)

    @staticmethod
    def is_expired(cookie):
        """检测单个 Cookie 是否过期。

        Args:
            cookie: {value, expires, path} 结构

        Returns:
            bool: expires 为 None/0 视为会话 Cookie（未过期）；
                  expires < 当前时间戳视为已过期
        """
        if not isinstance(cookie, dict):
            return False
        expires = cookie.get("expires")
        if not expires:
            return False
        try:
            exp = float(expires)
        except (TypeError, ValueError):
            return False
        if exp <= 0:
            return False
        return exp < time.time()

    def clean_expired(self):
        """清理所有过期 Cookie，返回被清理的条目数"""
        removed = 0
        for name in self.list_all():
            data = self._load_raw(name)
            cookies = data.get("cookies", {})
            before = len(cookies)
            data["cookies"] = {
                n: c for n, c in cookies.items() if not self.is_expired(c)
            }
            removed += before - len(data["cookies"])
            path = self._file_for(name)
            if data["cookies"]:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except OSError:
                    pass
            else:
                self.delete(name)
        return removed

    def export_to_jvm(self, domain):
        """导出 Cookie 为 JVM 可用格式（'k1=v1; k2=v2' 字符串）。

        与 MockCookieStore.setCookie(url, cookie) 的入参格式一致。
        """
        cookies = self.load(domain)
        pairs = [
            f"{n}={c['value']}"
            for n, c in cookies.items()
            if not self.is_expired(c)
        ]
        return "; ".join(pairs)


def import_from_browser(file_path):
    """从浏览器导出文件导入 Cookie。

    支持两种格式：
        - Netscape cookies.txt：每行 tab 分隔
          domain \\t flag \\t path \\t secure \\t expiration \\t name \\t value
        - JSON：浏览器扩展导出，元素为
          {domain, name, value, expirationDate, path, secure}

    Args:
        file_path: Cookie 文件路径

    Returns:
        dict[domain] = {name: {value, expires, path}}；解析失败返回空 dict
    """
    result = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return result

    # JSON 格式
    stripped = content.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(content)
        except ValueError:
            data = None
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name:
                    continue
                domain = _normalize_domain(item.get("domain", "").lstrip("."))
                if not domain:
                    continue
                result.setdefault(domain, {})[name] = {
                    "value": item.get("value", ""),
                    "expires": item.get("expirationDate") or item.get("expires"),
                    "path": item.get("path", "/"),
                }
            return result

    # Netscape 格式
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, _secure, expiration, name, value = parts[:7]
        domain = _normalize_domain(domain.lstrip("."))
        if not domain:
            continue
        try:
            exp = float(expiration) if expiration else None
        except ValueError:
            exp = None
        result.setdefault(domain, {})[name] = {
            "value": value,
            "expires": exp,
            "path": path,
        }
    return result


if __name__ == "__main__":
    # 简化自检：正常用例 + 边界用例
    import tempfile

    tmp = tempfile.mkdtemp()
    s = PersistentCookieStore(cache_dir=tmp)
    # 正常用例：保存字符串并跨子域读取
    s.save("a.example.com", "sid=abc; token=xyz")
    assert s.get_cookie_for_url("https://b.example.com/page") == "sid=abc; token=xyz"
    # 过期检测：会话 Cookie（expires=None）未过期
    assert s.is_expired({"value": "v", "expires": None, "path": "/"}) is False
    # 过期检测：已过期
    assert s.is_expired({"value": "v", "expires": 1, "path": "/"}) is True
    # 边界用例：空输入
    assert s.get_cookie_for_url("https://no-such-domain.test/") == ""
    assert s.save("empty.test", "") is not None
    assert s.get_cookie_for_url("https://empty.test/") == ""
    print("cookie_manager self-check OK")
