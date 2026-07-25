"""
html_fetcher.py - Legado 书源/订阅源 Skill 的 HTML 获取回退链模块

5步回退链：direct → Wayback Machine → CMS样本库 → Google Cache → Playwright

用法:
    python tools/html_fetcher.py --url URL --output output.html
    python tools/html_fetcher.py --url URL --json
    python tools/html_fetcher.py --url URL --cms-type maccms-v10
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    requests = None


# ---------------------------------------------------------------------------
# FetchResult
# ---------------------------------------------------------------------------

class FetchResult:
    """HTML 获取结果"""

    def __init__(self, html, source, cms_type=None, snapshot_date=None, log=None):
        self.html = html                # str | None
        self.source = source            # str: direct/wayback/cms_sample/google_cache/playwright/failed
        self.cms_type = cms_type        # str | None
        self.snapshot_date = snapshot_date  # str | None
        self.log = log or []            # list[str]

    @property
    def ok(self):
        return self.html is not None

    def to_dict(self):
        return {
            "ok": self.ok,
            "source": self.source,
            "cms_type": self.cms_type,
            "snapshot_date": self.snapshot_date,
            "html_length": len(self.html) if self.html else 0,
            "log": self.log,
        }

    def to_json(self, ensure_ascii=False, indent=2):
        d = self.to_dict()
        d["html"] = self.html
        return json.dumps(d, ensure_ascii=ensure_ascii, indent=indent)


# ---------------------------------------------------------------------------
# HtmlFetcher
# ---------------------------------------------------------------------------

class HtmlFetcher:
    """HTML 获取回退链"""

    # 缓存有效期（秒）
    CACHE_TTL = {
        "direct": 5 * 60,
        "wayback": 24 * 60 * 60,
        "cms_sample": float("inf"),
        "google_cache": 60 * 60,
        "playwright": 5 * 60,
    }

    DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    def __init__(self, ua=None, headers=None, timeout=15):
        if requests is None:
            raise ImportError("requests 库未安装，请运行: pip install requests")

        self.ua = ua or self.DEFAULT_UA
        self.timeout = timeout
        self._headers = headers or {}
        self._cache = {}  # key -> (html, source, timestamp)

    # -- 公开接口 --------------------------------------------------------

    def fetch(self, url, cms_type=None):
        """执行 5 步回退链，返回 FetchResult"""
        log = []

        # Step 1: 直接获取
        result = self._step_direct(url, log)
        if result.ok:
            return result

        # Step 2: Wayback Machine
        result = self._step_wayback(url, log)
        if result.ok:
            return result

        # Step 3: CMS 样本库
        result = self._step_cms_sample(url, log, cms_type=cms_type)
        if result.ok:
            return result

        # Step 4: Google Cache
        result = self._step_google_cache(url, log)
        if result.ok:
            return result

        # Step 5: Playwright
        result = self._step_playwright(url, log)
        if result.ok:
            return result

        return FetchResult(html=None, source="failed", log=log)

    # -- Step 1: 直接获取 ------------------------------------------------

    def _step_direct(self, url, log):
        """curl/requests 直接获取，含 CF 检测"""
        cached = self._get_cache(url, "direct")
        if cached is not None:
            log.append("[direct] 命中内存缓存")
            return FetchResult(html=cached, source="direct", log=log)

        headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        headers.update(self._headers)

        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True, verify=False)
            resp.raise_for_status()
            html = resp.text

            if self._is_cf_challenge(html):
                log.append("[direct] 检测到 Cloudflare 挑战页，跳过")
                return FetchResult(html=None, source="direct", log=log)

            self._set_cache(url, "direct", html)
            log.append(f"[direct] 成功获取，长度={len(html)}")
            return FetchResult(html=html, source="direct", log=log)

        except requests.RequestException as e:
            log.append(f"[direct] 请求失败: {e}")
            return FetchResult(html=None, source="direct", log=log)

    # -- Step 2: Wayback Machine -----------------------------------------

    def _step_wayback(self, url, log):
        """Wayback Machine CDX API 查询 + 快照获取 + 工具栏清理"""
        cached = self._get_cache(url, "wayback")
        if cached is not None:
            log.append("[wayback] 命中内存缓存")
            return FetchResult(html=cached, source="wayback", log=log)

        # CDX API 查询
        cdx_url = "https://web.archive.org/cdx/search/cdx"
        params = {
            "url": url,
            "output": "json",
            "limit": 3,
            "fl": "timestamp,original,statuscode",
            "filter": "statuscode:200",
        }

        try:
            resp = requests.get(cdx_url, params=params, timeout=10, verify=False)
            resp.raise_for_status()
            cdx_data = resp.json()
        except (requests.RequestException, ValueError) as e:
            log.append(f"[wayback] CDX API 超时或失败: {e}")
            return FetchResult(html=None, source="wayback", log=log)

        if len(cdx_data) <= 1:
            log.append("[wayback] 无可用快照")
            return FetchResult(html=None, source="wayback", log=log)

        # 尝试最多 3 个快照
        snapshots = cdx_data[1:]  # 跳过表头
        for row in snapshots:
            timestamp = row[0]
            snapshot_url = f"https://web.archive.org/web/{timestamp}/{url}"

            try:
                resp = requests.get(
                    snapshot_url,
                    headers={"User-Agent": self.ua},
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=False,
                )
                resp.raise_for_status()
                html = resp.text

                if not html or len(html) < 200:
                    log.append(f"[wayback] 快照 {timestamp} 内容过短，尝试下一个")
                    continue

                if self._is_cf_challenge(html):
                    log.append(f"[wayback] 快照 {timestamp} 是 CF 挑战页，尝试下一个")
                    continue

                html = self._clean_wayback_toolbar(html)
                snapshot_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                self._set_cache(url, "wayback", html)
                log.append(f"[wayback] 成功获取快照 {timestamp}，长度={len(html)}")
                return FetchResult(
                    html=html, source="wayback",
                    snapshot_date=snapshot_date, log=log,
                )

            except requests.RequestException as e:
                log.append(f"[wayback] 快照 {timestamp} 获取失败: {e}")
                continue

        log.append("[wayback] 所有快照均不可用")
        return FetchResult(html=None, source="wayback", log=log)

    # -- Step 3: CMS 样本库 -----------------------------------------------

    def _step_cms_sample(self, url, log, cms_type=None):
        """检测 CMS 类型 + 读取本地样本 HTML"""
        cached = self._get_cache(url, "cms_sample")
        if cached is not None:
            log.append("[cms_sample] 命中内存缓存")
            return FetchResult(html=cached, source="cms_sample", log=log)

        if cms_type is None:
            cms_type = self._detect_cms(url, log)

        if cms_type is None:
            log.append("[cms_sample] 无法检测 CMS 类型，跳过")
            return FetchResult(html=None, source="cms_sample", log=log)

        # 样本路径：references/cms-samples/{cms_type}/list.html
        sample_path = self._resolve_cms_sample_path(cms_type)
        if sample_path is None:
            log.append(f"[cms_sample] CMS 类型 {cms_type} 无样本路径")
            return FetchResult(html=None, source="cms_sample", log=log)

        if not os.path.isfile(sample_path):
            log.append(f"[cms_sample] 样本文件不存在: {sample_path}")
            return FetchResult(html=None, source="cms_sample", log=log)

        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                html = f.read()
            if not html or len(html) < 50:
                log.append(f"[cms_sample] 样本文件内容过短: {sample_path}")
                return FetchResult(html=None, source="cms_sample", log=log)

            self._set_cache(url, "cms_sample", html)
            log.append(f"[cms_sample] 使用 {cms_type} 样本，长度={len(html)}")
            return FetchResult(html=html, source="cms_sample", cms_type=cms_type, log=log)

        except (OSError, UnicodeDecodeError) as e:
            log.append(f"[cms_sample] 读取样本文件失败: {e}")
            return FetchResult(html=None, source="cms_sample", log=log)

    # -- Step 4: Google Cache --------------------------------------------

    def _step_google_cache(self, url, log):
        """Google Cache 缓存页面获取"""
        cached = self._get_cache(url, "google_cache")
        if cached is not None:
            log.append("[google_cache] 命中内存缓存")
            return FetchResult(html=cached, source="google_cache", log=log)

        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{urllib.parse.quote(url, safe='')}"
        headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            resp = requests.get(cache_url, headers=headers, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 403:
                log.append("[google_cache] 403 Forbidden，跳到 Step 5")
                return FetchResult(html=None, source="google_cache", log=log)

            resp.raise_for_status()
            html = resp.text

            if not html or len(html) < 200:
                log.append("[google_cache] 缓存页面内容过短")
                return FetchResult(html=None, source="google_cache", log=log)

            # 清理 Google Cache 注入的头部提示
            html = self._clean_google_cache_header(html)

            self._set_cache(url, "google_cache", html)
            log.append(f"[google_cache] 成功获取，长度={len(html)}")
            return FetchResult(html=html, source="google_cache", log=log)

        except requests.RequestException as e:
            log.append(f"[google_cache] 获取失败: {e}")
            return FetchResult(html=None, source="google_cache", log=log)

    # -- Step 5: Playwright -----------------------------------------------

    def _step_playwright(self, url, log):
        """Playwright 回退（检测可用性 + 调用 fetch_html.py）"""
        cached = self._get_cache(url, "playwright")
        if cached is not None:
            log.append("[playwright] 命中内存缓存")
            return FetchResult(html=cached, source="playwright", log=log)

        # 方式1: 尝试调用同目录下的 fetch_html.py
        fetch_html_path = os.path.join(os.path.dirname(__file__), "fetch_html.py")
        if os.path.isfile(fetch_html_path):
            log.append("[playwright] 发现 fetch_html.py，尝试调用")
            html = self._call_fetch_html_script(fetch_html_path, url, log)
            if html is not None:
                self._set_cache(url, "playwright", html)
                log.append(f"[playwright] 通过 fetch_html.py 成功获取，长度={len(html)}")
                return FetchResult(html=html, source="playwright", log=log)

        # 方式2: 尝试直接 import playwright
        html = self._try_playwright_direct(url, log)
        if html is not None:
            self._set_cache(url, "playwright", html)
            log.append(f"[playwright] 通过 playwright 直接调用成功，长度={len(html)}")
            return FetchResult(html=html, source="playwright", log=log)

        log.append("[playwright] Playwright 不可用，标记为 failed")
        return FetchResult(html=None, source="playwright", log=log)

    # -- 辅助方法 --------------------------------------------------------

    @staticmethod
    def _is_cf_challenge(html):
        """检测 Cloudflare 挑战页（15种特征）"""
        if not html:
            return False
        cf_signatures = [
            # 原有5种
            "Just a moment",
            "cf_chl_opt",
            "_cf_chl_rt_tk",
            "challenge-platform",
            "Checking your browser",
            # 新增10种 CF 特征关键词
            "cf-browser-verification",
            "cf_mitigated",
            "__cf_bm",
            "cdn-cgi/challenge",
            "cf-challenge",
            "Ray ID",
            "Performance & security by Cloudflare",
            "cf-error",
            "cf-spinner",
            "cf-please-wait",
        ]
        return any(sig in html for sig in cf_signatures)

    @staticmethod
    def _clean_wayback_toolbar(html):
        """清理 Wayback Machine 注入的工具栏代码"""
        if not html:
            return html

        # 1. 清理 <!-- BEGIN WAYBACK TOOLBAR INSERT -->...<!-- END WAYBACK TOOLBAR INSERT -->
        html = re.sub(
            r"<!--\s*BEGIN WAYBACK TOOLBAR INSERT\s*-->.*?<!--\s*END WAYBACK TOOLBAR INSERT\s*-->",
            "", html, flags=re.DOTALL | re.IGNORECASE,
        )

        # 2. 清理 /web/_static/ 路径的 JS/CSS
        html = re.sub(
            r'<(?:script|link)\s[^>]*(?:src|href)=["\'][^"\']*/web/_static/[^"\']*["\'][^>]*/?>',
            "", html, flags=re.IGNORECASE,
        )

        # 3. 清理 Wayback 时间戳前缀 /web/TIMESTAMP/...
        html = re.sub(
            r"/web/\d{14}/",
            "/", html,
        )

        return html

    @staticmethod
    def _clean_google_cache_header(html):
        """清理 Google Cache 注入的顶部提示"""
        if not html:
            return html
        # 清理 Google Cache 顶部提示 div
        html = re.sub(
            r"<div[^>]*class=\"[^\"]*cache\-header[^\"]*\"[^>]*>.*?</div>",
            "", html, flags=re.DOTALL | re.IGNORECASE,
        )
        return html

    def _detect_cms(self, url, log=None):
        """通过 URL 路径特征检测 CMS 类型"""
        # 先尝试直接请求，从响应内容中检测
        cms_patterns = {
            "maccms-v10": [
                "/api.php/provide/vod/",
                "/index.php/vod/",
                "/vod/type/",
                "/vod/detail/",
                "/vod/play/",
                "player_aaaa",
            ],
            "wordpress": [
                "/wp-content/",
                "/wp-includes/",
            ],
            "discuz": [
                "/forum.php",
                "/misc.php",
            ],
            "dedecms": [
                "/plus/",
                "/templets/",
            ],
        }

        # 先检查 URL 路径
        parsed = urllib.parse.urlparse(url)
        path = parsed.path

        for cms_type, patterns in cms_patterns.items():
            for pattern in patterns:
                if pattern.startswith("/"):
                    if pattern in path:
                        if log:
                            log.append(f"[cms_detect] URL路径匹配 {cms_type}: {pattern}")
                        return cms_type

        # 尝试请求首页检测内容特征
        try:
            headers = {"User-Agent": self.ua}
            resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True, verify=False)
            if resp.ok:
                text = resp.text
                for cms_type, patterns in cms_patterns.items():
                    for pattern in patterns:
                        if not pattern.startswith("/") and pattern in text:
                            if log:
                                log.append(f"[cms_detect] 页面内容匹配 {cms_type}: {pattern}")
                            return cms_type
        except requests.RequestException:
            pass

        # URL路径是根路径时，尝试请求常见CMS路径来检测
        if path == "/" or path == "":
            cms_probe_paths = {
                "maccms-v10": ["/index.php/vod/type/id/1.html", "/api.php/provide/vod/"],
                "wordpress": ["/wp-content/", "/wp-includes/"],
                "discuz": ["/forum.php"],
                "dedecms": ["/plus/"],
            }
            for cms_type, probe_paths in cms_probe_paths.items():
                for probe_path in probe_paths:
                    probe_url = f"{parsed.scheme}://{parsed.netloc}{probe_path}"
                    try:
                        resp = requests.get(probe_url, headers=headers, timeout=5, allow_redirects=True, verify=False)
                        if resp.ok:
                            if log:
                                log.append(f"[cms_detect] 探测路径匹配 {cms_type}: {probe_path} (HTTP {resp.status_code})")
                            return cms_type
                    except requests.RequestException:
                        continue

        return None

    @staticmethod
    def _resolve_cms_sample_path(cms_type):
        """解析 CMS 样本文件路径"""
        # references/cms-samples/{cms_type}/list.html，相对于 skill 根目录
        # 文件已迁移至 scripts/legado_client/utils/，需向上3级到 skill 根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        skill_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sample_path = os.path.join(skill_dir, "references", "cms-samples", cms_type, "list.html")
        return sample_path

    @staticmethod
    def _call_fetch_html_script(script_path, url, log):
        """调用 fetch_html.py 脚本获取 HTML"""
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, script_path, "--url", url],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                html = result.stdout.strip()
                return html
            else:
                log.append(f"[playwright] fetch_html.py 返回非零: {result.stderr[:200]}")
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            log.append(f"[playwright] fetch_html.py 调用失败: {e}")
            return None

    @staticmethod
    def _try_playwright_direct(url, log):
        """尝试直接使用 playwright 获取页面"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.append("[playwright] playwright 库未安装")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            log.append(f"[playwright] 浏览器执行失败: {e}")
            return None

    # -- 缓存 -------------------------------------------------------------

    def _get_cache(self, url, source):
        """获取缓存"""
        key = (url, source)
        entry = self._cache.get(key)
        if entry is None:
            return None
        html, ts = entry
        ttl = self.CACHE_TTL.get(source, 0)
        if ttl == float("inf"):
            return html
        if time.time() - ts > ttl:
            del self._cache[key]
            return None
        return html

    def _set_cache(self, url, source, html):
        """设置缓存"""
        key = (url, source)
        self._cache[key] = (html, time.time())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Legado 书源/订阅源 HTML 获取回退链工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
回退链顺序:
  1. direct      - curl/requests 直接获取（含 CF 检测）
  2. wayback     - Wayback Machine CDX API 快照
  3. cms_sample  - CMS 样本库匹配
  4. google_cache- Google Cache 缓存页面
  5. playwright  - Playwright 浏览器渲染

示例:
  python tools/html_fetcher.py --url https://example.com --json
  python tools/html_fetcher.py --url https://example.com --output page.html
  python tools/html_fetcher.py --url https://example.com --cms-type maccms-v10
""",
    )
    parser.add_argument("--url", required=True, help="目标 URL")
    parser.add_argument("--output", "-o", help="输出 HTML 文件路径")
    parser.add_argument("--json", action="store_true", dest="json_output", help="以 JSON 格式输出结果")
    parser.add_argument("--cms-type", help="指定 CMS 类型（跳过自动检测）")
    parser.add_argument("--ua", help="自定义 User-Agent")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP 请求超时（秒），默认 15")
    parser.add_argument("--header", action="append", help="自定义请求头，格式: Key:Value，可多次使用")

    args = parser.parse_args()

    # 解析自定义请求头
    custom_headers = {}
    if args.header:
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                custom_headers[k.strip()] = v.strip()

    fetcher = HtmlFetcher(ua=args.ua, headers=custom_headers, timeout=args.timeout)
    result = fetcher.fetch(args.url, cms_type=args.cms_type)

    if args.json_output:
        print(result.to_json())
    else:
        if result.ok:
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result.html)
                print(f"已保存到 {args.output} (source={result.source}, length={len(result.html)})")
            else:
                print(result.html)
        else:
            print(f"获取失败！回退日志:", file=sys.stderr)
            for line in result.log:
                print(f"  {line}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
