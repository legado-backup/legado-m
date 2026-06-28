# Design: Skill HTML 获取能力增强

---

## 1. Technical Approach（技术方法）

### 1.0 CF JS Challenge 自动绕过（L0，新增关键方案）

**源码验证结论**（已通过 Legado 源码深度分析确认）：

| 组件 | 行为 | 源码依据 |
|------|------|---------|
| `java.webView(null, url, null, false)` | 在后台WebView中加载URL，自动执行JS，返回渲染后HTML（String?） | JsExtensions.kt L203-229 |
| `BackstageWebView.onPageFinished` | 自动从WebView CookieManager读取Cookie，写入OkHttp CookieStore | BackstageWebView.kt L183-189 |
| `CookieStore` | OkHttp的Cookie持久化存储，后续OkHttp请求自动携带 | CookieStore.kt |
| `loginCheckJs` | 必须返回StrResponse对象，每次请求前执行 | Rss.kt L53-77 |
| `loginUrl` | JS代码（非URL），在SourceLoginDialog用户点击"登录"时执行，不会自动重新请求 | SourceLoginDialog.kt |

**CF 验证类型与绕过策略**：

| CF 验证类型 | 特征 | 自动绕过 | 降级方案 | 原理 |
|------------|------|---------|---------|------|
| JS Challenge（5秒盾） | "Just a moment..." + 自动执行JS | ✅ `webView()` 自动通过 | - | WebView是真实浏览器引擎，执行CF JS→设置cf_clearance Cookie→onPageFinished自动同步到CookieStore |
| Managed Challenge (Turnstile) | 需要用户交互（点击/滑块） | ❌ 无法自动通过 | `startBrowserAwait()` 手动通过 | Turnstile检测自动化工具，需要真实用户交互 |
| Interactive Challenge | 需要输入验证码 | ❌ 无法自动通过 | `startBrowserAwait()` 手动通过 | 需要人工识别验证码 |

**为什么纯Rhino JS无法破除CF盾？**

1. CF JS Challenge的验证JS是高度混淆的，且动态变化，无法在Rhino中模拟
2. CF验证JS依赖浏览器环境（DOM、BOM、Canvas、WebGL等），Rhino不具备这些API
3. CF验证JS可能检测浏览器指纹（navigator、screen、canvas hash等），Rhino环境无法伪造
4. 即使能模拟JS计算，也无法设置Cookie到OkHttp的CookieStore（Rhino没有Cookie操作API）

**结论：CF JS Challenge只能通过webView()自动通过，纯Rhino JS无法破除CF盾。**

**推荐源配置**：

```json
{
    "loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);",
    "loginCheckJs": "var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;"
}
```

**执行流程**：

```
用户首次打开源
    ↓
Legado请求文章列表 → CF拦截 → 返回"Just a moment..."
    ↓
loginCheckJs执行 → 检测到CF特征
    ↓
弹出SourceLoginDialog → 用户点击"登录"
    ↓
执行loginUrl → webView()加载页面
    ↓
WebView自动执行CF JS Challenge → CF验证通过
    ↓
cf_clearance Cookie → CookieManager → CookieStore（自动同步）
    ↓
webView()返回渲染后HTML（被忽略，仅用于触发Cookie同步）
    ↓
后续OkHttp请求自动携带cf_clearance Cookie → 无需再次验证
    ↓
loginCheckJs再次执行 → 不含CF特征 → 返回result → 正常加载
```

**Cookie 生命周期管理**：

| 阶段 | 行为 | 说明 |
|------|------|------|
| 首次通过CF | webView() → CookieManager → CookieStore | Cookie自动持久化 |
| 后续请求 | OkHttp自动从CookieStore读取Cookie | 无需手动设置Header |
| Cookie过期 | loginCheckJs检测到CF → 弹startBrowserAwait() | 用户需再次手动触发 |
| Cookie跨源 | 不共享（CookieStore按域名隔离） | 每个源独立管理 |

**⚠️ 关键注意事项**：

1. **loginUrl不会自动执行**：需要用户在SourceLoginDialog中手动点击"登录"按钮。这是Legado的设计，无法改变。
2. **webView()是同步阻塞的**：执行时间约5-10秒（CF JS Challenge耗时），在IO线程执行不会ANR。
3. **loginCheckJs必须返回StrResponse**：不能返回String，否则Legado会崩溃。`result`就是StrResponse对象，直接返回即可。
4. **startBrowserAwait()是最终降级**：当webView()无法通过CF（Turnstile/Interactive）时，让用户手动操作。

### 1.1 HTML 获取回退链

**核心模块**：`tools/html_fetcher.py`

```python
class FetchResult:
    """HTML 获取结果"""
    def __init__(self, html, source, cms_type=None, snapshot_date=None, log=None):
        self.html = html           # str | None: 获取到的 HTML
        self.source = source       # str: 获取方式
        self.cms_type = cms_type   # str | None: 检测到的 CMS 类型
        self.snapshot_date = snapshot_date  # str | None: Wayback 快照日期
        self.log = log or []       # list: 每步尝试记录


class HtmlFetcher:
    """HTML 获取回退链"""

    DEFAULT_UA = "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

    def __init__(self, timeout=15, user_agent=None, headers=None):
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_UA
        self.headers = headers or {}
        self.log = []  # 回退链日志

    def fetch(self, url, cms_type=None):
        """
        获取 HTML，按回退链逐级尝试

        回退链顺序（按可靠性排序）：
        1. curl/requests 直接获取（最可靠，如果网站无CF）
        2. Wayback Machine 历史快照（CF保护网站首选）
        3. CMS 样本库匹配（同CMS不同站，结构大概率一致）
        4. Google Cache 缓存页面（Google 2024年后已缩减Cache服务，可靠性下降）
        5. Playwright 获取（需要安装，但最完整）

        Returns:
            FetchResult
        """
        # Step 1: 直接获取
        result = self._fetch_direct(url)
        if result:
            return result

        # Step 2: Wayback Machine
        result = self._fetch_wayback(url)
        if result:
            return result

        # Step 3: CMS 样本库
        if not cms_type:
            cms_type = self._detect_cms(url)
        if cms_type:
            result = self._fetch_cms_sample(cms_type)
            if result:
                return result

        # Step 4: Google Cache
        result = self._fetch_google_cache(url)
        if result:
            return result

        # Step 5: Playwright（如果可用）
        result = self._fetch_playwright(url)
        if result:
            return result

        # 全部失败
        return FetchResult(html=None, source='failed', log=self.log)
```

**Step 1: 直接获取**：

```python
def _fetch_direct(self, url):
    """Step 1: curl/requests 直接获取"""
    import requests

    self.log.append({"step": 1, "method": "direct", "status": "trying"})

    try:
        resp = requests.get(url, headers={
            "User-Agent": self.user_agent,
            **self.headers
        }, timeout=self.timeout, allow_redirects=True)

        if resp.status_code == 200:
            html = resp.text
            # 检测 CF 保护
            if self._is_cf_challenge(html):
                self.log.append({"step": 1, "method": "direct", "status": "cf_blocked"})
                return None
            self.log.append({"step": 1, "method": "direct", "status": "success"})
            return FetchResult(html=html, source='direct', log=self.log)
        else:
            self.log.append({"step": 1, "method": "direct", "status": "http_error", "code": resp.status_code})
            return None
    except Exception as e:
        self.log.append({"step": 1, "method": "direct", "status": "error", "message": str(e)})
        return None
```

**Step 2: Wayback Machine**：

```python
def _fetch_wayback(self, url):
    """Step 2: Wayback Machine CDX API 查询 + 快照获取 + 工具栏清理"""
    import requests
    import re

    self.log.append({"step": 2, "method": "wayback", "status": "trying"})

    try:
        # CDX API 查询最近快照
        cdx_url = 'https://web.archive.org/cdx/search/cdx'
        params = {
            'url': url,
            'output': 'json',
            'limit': 3,  # 取最近3个快照，防止某个快照损坏
            'fl': 'timestamp,original,statuscode,mimetype',
            'filter': 'statuscode:200',
        }
        resp = requests.get(cdx_url, params=params, timeout=10)
        data = resp.json()

        if len(data) <= 1:  # 只有表头，无快照
            self.log.append({"step": 2, "method": "wayback", "status": "no_snapshot"})
            return None

        # 尝试每个快照
        for row in data[1:]:  # 跳过表头
            timestamp, original, statuscode, mimetype = row
            snapshot_url = f'https://web.archive.org/web/{timestamp}/{original}'

            try:
                snap_resp = requests.get(snapshot_url, timeout=15)
                if snap_resp.status_code == 200:
                    html = self._clean_wayback_toolbar(snap_resp.text)
                    snapshot_date = f'{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}'
                    self.log.append({
                        "step": 2, "method": "wayback", "status": "success",
                        "snapshot_date": snapshot_date
                    })
                    return FetchResult(
                        html=html, source='wayback',
                        snapshot_date=snapshot_date, log=self.log
                    )
            except Exception:
                continue

        self.log.append({"step": 2, "method": "wayback", "status": "all_snapshots_failed"})
        return None
    except Exception as e:
        self.log.append({"step": 2, "method": "wayback", "status": "error", "message": str(e)})
        return None

def _clean_wayback_toolbar(self, html):
    """清理 Wayback Machine 注入的工具栏和资源引用"""
    import re

    # 1. 清理 Wayback 工具栏注释块
    html = re.sub(
        r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->',
        '', html, flags=re.DOTALL
    )

    # 2. 清理 Wayback 注入的 JS/CSS（/web/_static/ 路径）
    html = re.sub(
        r'<script[^>]*src=["\'][^"\']*/web/_static/[^"\']*["\'][^>]*></script>',
        '', html, flags=re.IGNORECASE
    )
    html = re.sub(
        r'<link[^>]*href=["\'][^"\']*/web/_static/[^"\']*["\'][^>]*/?>',
        '', html, flags=re.IGNORECASE
    )

    # 3. 清理 Wayback 重写标记（如 src="/web/TIMESTAMP/... → src="..."）
    # 注意：不清理所有/web/前缀，因为有些可能是原始URL的一部分
    # 只清理 Wayback 特有的时间戳前缀
    html = re.sub(
        r'(src|href)=["\']/web/\d{14}/([^"\']*)["\']',
        r'\1="\2"', html
    )

    return html
```

**Step 3: CMS 样本库**：

```python
def _detect_cms(self, url):
    """检测 CMS 类型（复用 analyze-site.py 的检测逻辑）"""
    # 1. 尝试获取 robots.txt / favicon / 特征路径
    # 2. 匹配 CMS 特征指纹
    # 3. 返回 CMS 类型或 None
    # 苹果CMS特征: /api.php/provide/vod/, player_aaaa JS变量
    # WordPress特征: /wp-content/, /wp-includes/
    # Discuz特征: /forum.php, /member.php
    # DedeCMS特征: /plus/, /templets/
    pass

def _fetch_cms_sample(self, cms_type):
    """Step 3: 从 CMS 样本库获取标准 HTML"""
    import os
    import json

    self.log.append({"step": 3, "method": "cms_sample", "cms_type": cms_type, "status": "trying"})

    sample_dir = os.path.join(os.path.dirname(__file__), '..', 'references', 'cms-samples', cms_type)
    list_html_path = os.path.join(sample_dir, 'list.html')

    if os.path.exists(list_html_path):
        with open(list_html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        self.log.append({"step": 3, "method": "cms_sample", "cms_type": cms_type, "status": "success"})
        return FetchResult(html=html, source='cms_sample', cms_type=cms_type, log=self.log)

    self.log.append({"step": 3, "method": "cms_sample", "cms_type": cms_type, "status": "no_sample"})
    return None
```

**Step 4: Google Cache**：

```python
def _fetch_google_cache(self, url):
    """Step 4: Google Cache 缓存页面获取"""
    import requests

    self.log.append({"step": 4, "method": "google_cache", "status": "trying"})

    try:
        # Google Cache URL 格式
        cache_url = f'https://webcache.googleusercontent.com/search?q=cache:{url}'
        resp = requests.get(cache_url, headers={
            "User-Agent": self.user_agent,
        }, timeout=self.timeout)

        if resp.status_code == 200:
            html = resp.text
            # Google Cache 可能在页面顶部添加导航栏，需清理
            self.log.append({"step": 4, "method": "google_cache", "status": "success"})
            return FetchResult(html=html, source='google_cache', log=self.log)
        else:
            self.log.append({"step": 4, "method": "google_cache", "status": "http_error", "code": resp.status_code})
            return None
    except Exception as e:
        self.log.append({"step": 4, "method": "google_cache", "status": "error", "message": str(e)})
        return None
```

**CF 检测**：

```python
def _is_cf_challenge(self, html):
    """检测页面是否为 CF Challenge 页面"""
    cf_indicators = [
        'Just a moment',           # CF JS Challenge 标题
        'cf_chl_opt',             # CF Challenge 选项变量
        '_cf_chl_rt_tk',          # CF Challenge Token 参数
        'challenge-platform',      # CF Challenge 脚本标识
        'Checking your browser',   # CF 检测文案
    ]
    for indicator in cf_indicators:
        if indicator in html:
            return True
    return False
```

**html_fetcher.py CLI 接口**：

```bash
# AI 在 Phase 2 中用 RunCommand 调用
python tools/html_fetcher.py --url URL --output output.html

# 指定 CMS 类型（跳过检测）
python tools/html_fetcher.py --url URL --output output.html --cms-type maccms-v10

# 仅输出 JSON 结果（不写文件）
python tools/html_fetcher.py --url URL --json

# 输出 FetchResult JSON 示例
{
    "html": "<html>...</html>",
    "source": "wayback",
    "cms_type": null,
    "snapshot_date": "2024-08-15",
    "log": [
        {"step": 1, "method": "direct", "status": "cf_blocked"},
        {"step": 2, "method": "wayback", "status": "success", "snapshot_date": "2024-08-15"}
    ]
}
```

### 1.2 CMS 样本库

**目录结构**：

```
references/cms-samples/
├── _INDEX.md                          # 样本库索引
├── maccms-v10/
│   ├── list.html                      # 列表页样本（脱敏）
│   ├── detail.html                    # 详情页样本（脱敏）
│   ├── search.html                    # 搜索页样本（脱敏）
│   ├── play.html                      # 播放页样本（脱敏）
│   └── selectors.json                 # 标准选择器映射
├── maccms-x10/
│   ├── list.html
│   ├── detail.html
│   └── selectors.json
├── wordpress/
│   ├── list.html
│   ├── detail.html
│   └── selectors.json
├── discuz/
│   ├── list.html
│   ├── detail.html
│   └── selectors.json
└── dedecms/
    ├── list.html
    ├── detail.html
    └── selectors.json
```

**样本来源**：GitHub 开源 CMS 仓库的默认模板 HTML

| CMS | GitHub 仓库 | 模板路径 | 获取方式 |
|-----|-----------|---------|---------|
| 苹果CMS V10 | magicblack/maccms10 | template/default/html/ | WebFetch GitHub Raw |
| 苹果CMS X10 | magetop/maccms-x10 | resources/template/ | WebFetch GitHub Raw |
| WordPress | WordPress/WordPress | wp-content/themes/twentytwentyfour/ | WebFetch GitHub Raw |
| Discuz | Discuz/DiscuzX | template/default/ | WebFetch GitHub Raw |
| DedeCMS | dedecms/dedecms | templets/default/ | WebFetch GitHub Raw |

**selectors.json 格式**：

```json
{
  "cms_type": "maccms-v10",
  "version": "1.0",
  "verified_date": "2026-06-14",
  "verified_source": "1080zyk.com",
  "pages": {
    "list": {
      "description": "视频列表页（首页/分类页）",
      "selectors": {
        "articleList": {
          "primary": ".stui-vodlist li",
          "fallbacks": [".module-items .module-item", ".vodlist li"],
          "note": "视频列表项容器"
        },
        "title": {
          "primary": "tag.a.0@title",
          "fallbacks": ["tag.a.0@text", "tag.a@title"],
          "note": "视频标题"
        },
        "link": {
          "primary": "tag.a.0@href",
          "fallbacks": ["tag.a@href"],
          "note": "详情页链接"
        },
        "image": {
          "primary": "tag.img.0@data-original",
          "fallbacks": ["tag.img.0@data-src", "tag.img.0@src"],
          "note": "封面图片（懒加载属性优先）"
        },
        "description": {
          "primary": ".pic-text@text",
          "fallbacks": [".module-item-note@text"],
          "note": "备注/集数信息"
        },
        "nextPage": {
          "primary": ".page-next a@href",
          "fallbacks": [".stui-page a.next@href", ".module-page a.next@href"],
          "note": "下一页链接"
        }
      }
    },
    "detail": {
      "description": "视频详情页",
      "selectors": {
        "playList": {
          "primary": ".stui-content__playlist a",
          "fallbacks": [".module-play-list a", ".playlist a"],
          "note": "播放列表链接"
        },
        "playerVar": {
          "primary": "player_aaaa",
          "fallbacks": [],
          "note": "苹果CMS播放页JS变量名"
        }
      }
    },
    "sortUrl": {
      "description": "分类URL模板",
      "templates": {
        "电影": "/index.php/vod/type/id/1.html",
        "连续剧": "/index.php/vod/type/id/2.html",
        "动漫": "/index.php/vod/type/id/3.html",
        "综艺": "/index.php/vod/type/id/4.html"
      },
      "note": "苹果CMS标准分类URL格式，id可能因站而异"
    }
  }
}
```

**样本 HTML 脱敏规范**：

1. 去除所有用户数据（用户名、头像、评论内容）→ 替换为占位符 `{{USERNAME}}`
2. 去除广告和追踪代码（`<script>` 中的第三方统计/广告）
3. 去除敏感 URL 参数（token/session）
4. 保留完整的 HTML 结构（标签、class、id、data-* 属性）
5. 保留足够的列表项（至少 5 个）以验证选择器
6. 文件头 HTML 注释标注来源和脱敏日期：
   ```html
   <!-- CMS Sample: maccms-v10 | Source: GitHub magicblack/maccms10 | Desensitized: 2026-06-14 -->
   ```

### 1.3 Playwright 集成

**脚本**：`tools/fetch_html.py`

```python
#!/usr/bin/env python3
"""
Playwright HTML 获取工具
用法:
  python tools/fetch_html.py --url URL --output output.html
  python tools/fetch_html.py --url URL --output output.html --wait-cf
  python tools/fetch_html.py --url URL --output output.html --wait-selector ".video-list"
  python tools/fetch_html.py --url URL --output output.html --headed --export-cookies cookies.json
"""

import argparse
import json
import sys


def check_playwright():
    """检测 Playwright 是否完整可用（Python 包 + Chromium 浏览器）"""
    try:
        from playwright.sync_api import sync_playwright
        # 检测 Chromium 浏览器是否已安装
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except ImportError:
        return False


def detect_cf_challenge(page):
    """CF Challenge 多特征检测"""
    # 检测1: 页面标题
    title = page.title()
    if 'Just a moment' in title or 'Cloudflare' in title:
        return True

    # 检测2: CF JS 变量
    has_cf_var = page.evaluate('typeof cf_chl_opt !== "undefined"')
    if has_cf_var:
        return True

    # 检测3: CF Challenge 脚本
    has_cf_script = page.evaluate(
        'document.querySelector("script[src*=challenge-platform]") !== null'
    )
    if has_cf_script:
        return True

    # 检测4: Turnstile iframe
    has_turnstile = page.evaluate(
        'document.querySelector(\'iframe[src*="challenges.cloudflare.com"]\') !== null'
    )
    if has_turnstile:
        return 'turnstile'

    return False


def fetch_html(url, output, wait_cf=False, wait_selector=None,
               headed=False, export_cookies=None, timeout=30):
    """使用 Playwright 获取渲染后 HTML"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            viewport={'width': 412, 'height': 915},
            is_mobile=True,
        )
        page = context.new_page()

        # 导航到目标页面
        page.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)

        # 等待 CF 验证
        if wait_cf:
            max_wait = 30
            for i in range(max_wait):
                cf_result = detect_cf_challenge(page)
                if cf_result == 'turnstile':
                    print('WARNING: Turnstile detected, cannot auto-bypass. Use --headed mode.')
                    if not headed:
                        break
                elif not cf_result:
                    break
                page.wait_for_timeout(1000)

        # 等待指定选择器
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout*1000)

        # 获取渲染后 HTML
        html = page.content()

        # 导出 Cookie
        if export_cookies:
            cookies = context.cookies()
            with open(export_cookies, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)

        browser.close()

    # 输出 HTML
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'HTML saved to {output}')
    if export_cookies:
        print(f'Cookies saved to {export_cookies}')


if __name__ == '__main__':
    if not check_playwright():
        print('ERROR: Playwright not installed or Chromium browser not available.')
        print('Install: pip install playwright && playwright install chromium')
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--wait-cf', action='store_true')
    parser.add_argument('--wait-selector', type=str)
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--export-cookies', type=str)
    parser.add_argument('--timeout', type=int, default=30)
    args = parser.parse_args()

    fetch_html(args.url, args.output, args.wait_cf, args.wait_selector,
               args.headed, args.export_cookies, args.timeout)
```

### 1.4 JVM Cookie 注入

**Cookie 格式转换**：

Playwright 导出的 Cookie 格式与 OkHttp CookieStore 需要的格式不同，需要转换：

```python
# Playwright 导出格式
playwright_cookie = {
    "name": "cf_clearance",
    "value": "xxx",
    "domain": ".1080zyk.com",
    "path": "/",
    "expires": 1719000000,
    "httpOnly": False,
    "secure": True,
    "sameSite": "None"
}

# OkHttp CookieStore 需要的格式（通过 JVM 命令传入）
okhttp_cookie = {
    "name": "cf_clearance",
    "value": "xxx",
    "domain": ".1080zyk.com",
    "path": "/",
    "expiresAt": 1719000000,       # 注意：字段名不同
    "secure": True,
    "httpOnly": False,
    "hostOnly": False              # Playwright 没有此字段，需推断
}
```

**转换函数**（在 `rule_engine_client.py` 中实现）：

```python
def convert_playwright_cookies_to_okhttp(playwright_cookies):
    """将 Playwright Cookie 格式转换为 OkHttp CookieStore 格式"""
    okhttp_cookies = []
    for pc in playwright_cookies:
        okhttp_cookie = {
            "name": pc["name"],
            "value": pc["value"],
            "domain": pc.get("domain", ""),
            "path": pc.get("path", "/"),
            "expiresAt": pc.get("expires", -1),
            "secure": pc.get("secure", False),
            "httpOnly": pc.get("httpOnly", False),
            "hostOnly": not pc.get("domain", "").startswith("."),
        }
        okhttp_cookies.append(okhttp_cookie)
    return okhttp_cookies
```

**RuleEngineServer 新增命令**：

```json
// 请求
{"command": "set_cookies", "cookies": [{"name": "cf_clearance", "value": "xxx", "domain": ".1080zyk.com", "path": "/", "expiresAt": 1719000000, "secure": true, "httpOnly": false, "hostOnly": false}]}

// 响应
{"status": "ok", "cookie_count": 1}
```

**RuleEngineClient 新增方法**：

```python
def set_cookies(self, cookies):
    """注入 Cookie 到 JVM 仿真器"""
    okhttp_cookies = self.convert_playwright_cookies_to_okhttp(cookies)
    return self._send_command("set_cookies", {"cookies": okhttp_cookies})
```

**MockJsExtensions.ajax() 修改**：

```kotlin
// MinimalMockJsExtensions.kt
fun ajax(url: String): String {
    val request = Request.Builder().url(url)

    // 从 CookieStore 读取 Cookie
    val cookies = cookieStore.get(url)
    if (cookies.isNotEmpty()) {
        val cookieHeader = cookies.joinToString("; ") { "${it.name}=${it.value}" }
        request.addHeader("Cookie", cookieHeader)
    }

    // ... 其余逻辑不变
}
```

### 1.5 SKILL.md 5阶段工作流精确修改设计

#### Phase 1（经验优先）修改

**新增步骤**：
1. 搜索CF绕过经验：`search_notes(query="CF绕过 Cloudflare", search_type="hybrid", project="legado")`
2. 搜索CMS类型经验：`search_notes(query="{CMS类型} 选择器", search_type="hybrid", project="legado")`
3. 查cms-samples/目录：检查 `references/cms-samples/{cms_type}/` 是否存在

**完成检查清单新增**：
- [ ] 搜索CF绕过经验（如网站有CF保护）
- [ ] 搜索CMS类型经验（如检测到CMS类型）
- [ ] 查cms-samples/目录（如检测到CMS类型）

#### Phase 2（构建规则）修改

**步骤1"分析网站"修改**：
- 原：curl获取HTML → 判断类型
- 新：curl获取HTML → CF拦截？→ 调用html_fetcher.py回退链 → 判断类型
- 调用方式：`python tools/html_fetcher.py --url URL --json`
- AI解析FetchResult JSON → 获取HTML和来源信息

**步骤3"构建详情+目录+正文规则"修改**：
- 新增：如果检测到CMS类型，优先使用 `references/cms-samples/{cms_type}/selectors.json` 中的选择器
- AI读取selectors.json → 使用primary选择器 → 构建规则字段

**步骤4"处理特殊场景"修改**：
- 原：CF反爬 → `references/special-scenarios/anti-crawl.md`
- 新：CF反爬 → CF绕过三级策略：
  - JS Challenge → loginUrl: `@js:java.webView(null, source.sourceUrl, null, false);`
  - Turnstile → loginCheckJs: `java.startBrowserAwait(source.sourceUrl, '通过Cloudflare验证');`
  - Interactive → loginCheckJs: `java.startBrowserAwait(source.sourceUrl, '通过验证');`

#### Phase 3（测试驱动）修改

**可信度分层表格修改**：

| 可信度 | 适用 | 提示 |
|--------|------|------|
| 高 | CSS/纯逻辑JS/加密/AnalyzeRule + HTML直接获取验证通过 / Wayback(1年内)验证通过 | "已通过本地验证" |
| 中 | 依赖ajax()但无Cookie / Wayback(1年以上) / CMS样本库 / Google Cache | "Cookie差异可能影响" 或 "CMS样本验证通过" |
| 低 | 依赖ajax()+Cookie / 无HTML（猜测） | "需真机验证" |
| 不可验证 | WebView规则 | "必须在Legado中测试" |

**测试脚本执行优先级修改**：
- 新增：`html_fetcher.py`（HTML获取，Phase 2 中使用）
- 修改：`verify-selector.py` 新增 `--sample` 参数

#### Phase 4（源码深挖）修改

**源码深挖表格新增**：

| 核实场景 | 源码位置 |
|----------|----------|
| CF JS Challenge 绕过 | `app/.../help/JsExtensions.kt` (webView方法) |
| Cookie 同步机制 | `app/.../help/http/CookieStore.kt` + `app/.../web/BackstageWebView.kt` |
| loginCheckJs 执行 | `app/.../model/rss/Rss.kt` (L53-77) |
| loginUrl 执行 | `app/.../ui/dialog/SourceLoginDialog.kt` |

#### Phase 5（经验反哺）修改

**反哺写入目标新增**：
- `references/special-scenarios/anti-crawl.md`：CF绕过方案
- `references/cms-samples/{cms_type}/`：CMS样本和选择器
- `references/troubleshooting/html-fetch-traps.md`：HTML获取方案
- basic-memory：CF绕过经验 + CMS样本经验 + HTML获取经验

### 1.6 6大参考目录修改设计

| 目录 | 修改文件 | 修改内容 | 优先级 |
|------|---------|---------|--------|
| js-extensions/ | webview.md | 补充webView()用于CF绕过的用法：loginUrl中调用、Cookie自动同步、注意事项 | P0 |
| js-extensions/ | cookie-cache.md | 补充Cookie双向共享机制：WebView→CookieStore自动(onPageFinished) / OkHttp→WebView需applyToWebView() | P0 |
| js-patterns/ | url-js-patterns.md | 补充loginUrl CF绕过模式：webView()自动通过 + startBrowserAwait()降级 | P1 |
| js-patterns/ | rule-js-patterns.md | 补充loginCheckJs CF检测模式：检测"Just a moment" → 降级处理 | P1 |
| troubleshooting/ | html-fetch-traps.md | 补充CF保护网站获取方案：Wayback/CMS样本/Playwright回退链 | P0 |
| troubleshooting/ | source-type-traps.md | 补充loginCheckJs必须返回StrResponse的陷阱：末尾加`;result` | P0 |
| source-analysis/ | cf-bypass-source.md（新增） | CF绕过源码分析：JsExtensions.webView + BackstageWebView + CookieStore | P1 |
| references/ | _INDEX.md | 新增cms-samples/目录索引 + 自进化指引新增CMS样本条目 | P0 |

### 1.7 验证脚本修改设计

| 脚本 | 修改内容 | 优先级 |
|------|---------|--------|
| quick-verify.py | 增加CF检测：检测HTTP响应是否为CF Challenge页面（检查"Just a moment"/"cf_chl_opt"等特征） | P1 |
| deep-verify.py | 增加HTML来源维度：可信度标注包含html_source字段（direct/wayback/cms_sample/google_cache/failed） | P0 |
| deep-verify.py | 增加CMS样本验证：支持`--sample`参数指定CMS样本HTML | P1 |
| classify-and-fix.py | 增加CMS样本匹配分类：问题分类包含"cms_sample_available"字段 | P1 |
| verify-source.py | 增加CF绕过配置验证：检查loginUrl/loginCheckJs格式，CF保护网站缺少loginUrl时报错 | P0 |

### 1.8 html_fetcher.py 缓存和错误处理设计

**缓存机制**：

```python
class HtmlFetcher:
    def __init__(self, ...):
        self._cache = {}  # 内存缓存：{(url,): FetchResult}
        self._cache_timestamps = {}  # 缓存时间戳

    def _get_cache(self, url):
        """获取缓存，检查有效期"""
        key = (url,)
        if key not in self._cache:
            return None
        ts = self._cache_timestamps.get(key, 0)
        source = self._cache[key].source
        # 缓存有效期：direct 5分钟 / wayback 24小时 / cms_sample 永久 / google_cache 1小时
        ttl = {
            'direct': 300, 'wayback': 86400,
            'cms_sample': float('inf'), 'google_cache': 3600,
            'playwright': 300
        }.get(source, 300)
        if time.time() - ts > ttl:
            del self._cache[key]
            del self._cache_timestamps[key]
            return None
        return self._cache[key]

    def _set_cache(self, url, result):
        """设置缓存"""
        self._cache[(url,)] = result
        self._cache_timestamps[(url,)] = time.time()
```

**错误处理边界**：

| 错误场景 | 处理方式 | 影响 |
|---------|---------|------|
| Wayback API 超时（10s） | 记录日志，跳到Step 3 | 不影响后续步骤 |
| Wayback快照损坏（HTML解析失败） | 尝试下一个快照（取3个快照） | 容错 |
| CMS样本文件不存在 | 记录日志，跳到Step 4 | 不影响后续步骤 |
| CMS样本文件损坏（HTML格式错误） | try-except捕获，跳到Step 4 | 不影响后续步骤 |
| Playwright进程崩溃 | try-except捕获，标记为failed | 不影响其他功能 |
| Google Cache 403 | 记录日志，跳到Step 5 | 不影响后续步骤 |
| 所有步骤失败 | 返回FetchResult(source='failed') | AI标记为"需真机验证" |

**CF绕过边界情况**：

| 边界情况 | 处理方式 |
|---------|---------|
| webView()返回null（网络错误/超时） | loginCheckJs检测到CF → 弹startBrowserAwait()让用户手动通过 |
| Cookie同步失败（极端情况） | loginCheckJs检测到CF → 弹startBrowserAwait()让用户手动通过 |
| CF Cookie过期 | loginCheckJs检测到CF → 用户需再次点击"登录"触发webView() |
| 多个源共享同一域名 | CookieStore按域名隔离，不会冲突 |
| loginUrl不会自动执行 | 用户首次使用需手动点击"登录"按钮（Legado设计限制） |

### 1.9 回测验证设计（强制闭环）

> **不经过实际验证的优化=虚假优化。本节定义用"优质资源(1080zyk)"订阅源回测验证的完整闭环。**

#### 1.9.1 优化前后对比

**当前"优质资源-优化.json"存在的问题**：

| 问题 | 当前值 | 优化后值 | 影响 |
|------|--------|---------|------|
| loginUrl 使用 startBrowserAwait() | `@js:java.startBrowserAwait('https://1080zyk.com/','通过Cloudflare验证');` | `@js:java.webView(null, source.sourceUrl, null, false);` | 从"需用户手动操作"变为"自动通过CF JS Challenge" |
| loginCheckJs 降级方案 | 仅 startBrowserAwait() | 检测CF → Turnstile则startBrowserAwait() | 增加CF类型检测，避免不必要的弹窗 |
| 5个低可信字段 | 无HTML验证 | CMS样本库/Wayback验证 | 从"猜测"变为"验证通过" |

**可信度变化矩阵**：

| 字段 | 当前选择器 | 当前可信度 | 验证方式 | 优化后预期可信度 |
|------|-----------|-----------|---------|----------------|
| ruleArticles | `.stui-vodlist li\|\|.module-items .module-item\|\|.vodlist li` | 低 | CMS样本验证 | 高 |
| ruleNextPage | `.page-next a@href\|\|.stui-page a.next@href\|\|.module-page a.next@href` | 低 | CMS样本验证 | 高 |
| ruleLink | `tag.a.0@href\|\|tag.a@href` | 低 | CMS样本验证 | 高 |
| ruleTitle | `tag.a.0@title\|\|tag.a.0@text\|\|tag.a@title` | 低 | CMS样本验证 | 高 |
| ruleImage | `tag.img.0@data-original\|\|tag.img.0@data-src\|\|tag.img.0@src` | 低 | CMS样本验证 | 高 |
| ruleDescription | `.pic-text@text\|\|.module-item-note@text` | 中 | CMS样本验证 | 高 |
| ruleContent | `<js>...player_aaaa...</js>` | 中 | 需ajax()+Cookie | 中 |
| header | `@js:JSON.stringify({...})` | 高 | 纯JS逻辑 | 高 |
| loginUrl/loginCheckJs | startBrowserAwait() | 低 | webView()自动通过 | 高 |

#### 1.9.2 验证流程

```
Step 1: 更新源配置
    ↓  loginUrl: startBrowserAwait() → webView()
    ↓  loginCheckJs: 增加CF类型检测
    ↓
Step 2: HTML获取验证
    ↓  python tools/html_fetcher.py --url https://1080zyk.com/ --json
    ↓  记录: FetchResult { source, cms_type, snapshot_date }
    ↓
Step 3: CMS样本验证
    ↓  python scripts/verify-selector.py --sample references/cms-samples/maccms-v10/list.html \
    ↓      --selector ".stui-vodlist li" --selector ".page-next a" --selector "tag.a.0@title"
    ↓  记录: 每个选择器的验证结果（命中数量/0=未命中）
    ↓
Step 4: JVM MVP2深度验证
    ↓  python scripts/deep-verify.py --source output/rss/优质资源-优化.json
    ↓  记录: 每个字段的可信度 + HTML来源
    ↓
Step 5: CF绕过配置验证
    ↓  检查loginUrl格式: @js:java.webView(null, source.sourceUrl, null, false);
    ↓  检查loginCheckJs格式: var s=result.body();if(s.indexOf('Just a moment')!=-1){...}result;
    ↓  记录: 配置是否正确
    ↓
Step 6: 输出验证报告
    ↓  对比优化前后可信度
    ↓  确认低可信项从5个降到≤2个
    ↓  如果未达标 → 分析原因 → 修复 → 重新验证
```

#### 1.9.3 验证报告格式

```json
{
  "source_name": "优质资源",
  "source_url": "https://1080zyk.com/",
  "verification_date": "2026-06-14",
  "html_fetch_result": {
    "source": "wayback",
    "cms_type": "maccms-v10",
    "snapshot_date": "2024-08-15"
  },
  "confidence_comparison": {
    "before": {
      "high": 1,
      "medium": 2,
      "low": 5,
      "unverifiable": 0
    },
    "after": {
      "high": 7,
      "medium": 1,
      "low": 0,
      "unverifiable": 0
    },
    "improvement": "低可信项从5个降到0个"
  },
  "selector_verification": {
    "ruleArticles": {"selector": ".stui-vodlist li", "result": "命中5项", "confidence": "高"},
    "ruleNextPage": {"selector": ".page-next a", "result": "命中1项", "confidence": "高"},
    "ruleLink": {"selector": "tag.a.0@href", "result": "命中5项", "confidence": "高"},
    "ruleTitle": {"selector": "tag.a.0@title", "result": "命中5项", "confidence": "高"},
    "ruleImage": {"selector": "tag.img.0@data-original", "result": "命中5项", "confidence": "高"},
    "ruleDescription": {"selector": ".pic-text@text", "result": "命中5项", "confidence": "高"}
  },
  "cf_bypass_verification": {
    "loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);",
    "loginCheckJs": "var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;",
    "status": "配置正确"
  },
  "conclusion": "优化效果达标"
}
```

#### 1.9.4 未达标处理

如果验证结果未达标（低可信项>2个），按以下流程处理：

1. **分析原因**：哪些字段未通过验证？为什么？
2. **修复方案**：
   - CMS样本不匹配 → 尝试fallbacks选择器 → 或从Wayback HTML提取新选择器
   - Wayback HTML过旧 → 检查是否有更新的快照
   - 选择器语法错误 → 修正选择器
3. **重新验证**：修复后重新执行Step 3-6
4. **记录经验**：将修复经验写入basic-memory和references/

---

## 2. Architecture Decisions（架构决策）

### AD1: 回退链设计为独立模块而非嵌入 SKILL.md

**决策**：创建 `tools/html_fetcher.py` 独立模块，而非在 SKILL.md 中描述流程让 AI 手动执行。

**理由**：
- AI 手动执行回退链容易遗漏步骤（5步回退，AI 可能跳过中间步骤）
- 独立模块可被多个脚本复用（analyze-site.py、verify-selector.py、deep-verify.py）
- 回退链日志自动记录，写入 basic-memory 执行证据
- 测试更方便（单元测试 vs AI 行为测试）

### AD2: CMS 样本存 HTML 文件而非 JSON

**决策**：样本以 `.html` 文件存储，而非嵌入 JSON。

**理由**：
- HTML 文件可直接用于 jsoup 验证，无需解析
- AI 可直接 Read() 查看样本结构
- JVM MVP2 的 `eval_css(html, selector)` 需要 HTML 字符串输入
- JSON 格式需要额外的序列化/反序列化步骤

### AD3: Playwright 为可选依赖

**决策**：Playwright 不作为 skill 的必需依赖，未安装时降级到其他获取方式。

**理由**：
- Playwright + Chromium 约 200MB，安装成本高
- 部分用户环境可能无法安装（企业网络限制等）
- Wayback Machine + CMS 样本库已覆盖 85%+ 场景
- Playwright 是"锦上添花"而非"必需品"

### AD4: selectors.json 使用 primary+fallbacks 结构

**决策**：选择器映射使用 `primary` + `fallbacks` 数组结构，而非单一选择器。

**理由**：
- 同一 CMS 不同模板的选择器可能不同（如苹果CMS的"首涂模板"vs"模板M3"）
- `||` 操作符在 Legado 中已有回退语义，selectors.json 应与之对应
- AI 构建规则时可直接使用 primary，失败时尝试 fallbacks
- verify-selector.py 可逐个验证 primary 和 fallbacks

### AD5: 可信度分级增加"来源"维度

**决策**：Phase 3 可信度标注增加 HTML 来源维度。

| HTML 来源 | 选择器可信度 | 说明 |
|-----------|------------|------|
| 直接获取 | 高 | 实际网站 HTML，当前有效 |
| Wayback Machine（1年内） | 高 | 快照较新，结构大概率一致 |
| Wayback Machine（1年以上） | 中 | 快照过旧，可能已改版 |
| CMS 样本库 | 中 | 同 CMS 但版本/模板可能不同 |
| Google Cache | 中 | 缓存可能不是最新版 |
| 无 HTML（猜测） | 低 | 未验证 |

### AD6: CF 绕过方案选择——loginUrl 而非 loginCheckJs

**决策**：CF 绕过逻辑放在 `loginUrl` 中（`webView()`），而非 `loginCheckJs` 中。

**理由**：
- `webView()` 是同步阻塞操作（5-10秒），不适合放在每次请求都执行的 `loginCheckJs` 中
- `loginUrl` 只在用户手动触发时执行一次，性能影响可控
- `loginCheckJs` 仅做检测（轻量级字符串匹配），不做耗时操作
- CF Cookie 有效期长（数天到数周），不需要每次请求都重新获取

**代价**：用户首次使用需手动点击"登录"按钮触发 `webView()`。但这是 Legado 的设计限制，无法绕过。

### AD7: 回退链顺序——CMS 样本库优先于 Google Cache

**决策**：回退链中 CMS 样本库（Step 3）优先于 Google Cache（Step 4）。

**理由**：
- Google 2024年后已大幅缩减 Cache 服务，可靠性显著下降
- CMS 样本库基于开源模板，结构标准化，可靠性更高
- CMS 样本库是本地资源，无网络延迟和失败风险
- Google Cache 依赖第三方服务，可能随时不可用

---

## 3. Data Flow（数据流）

### 3.0 CF JS Challenge 自动绕过数据流

```
用户打开源 → Legado请求文章列表
       ↓
CF拦截 → 返回"Just a moment..."
       ↓
loginCheckJs执行 → 检测到CF特征
       ↓
弹出SourceLoginDialog → 用户点击"登录"
       ↓
执行loginUrl: java.webView(null, source.sourceUrl, null, false)
       ↓
BackstageWebView加载页面 → 自动执行CF JS Challenge
       ↓
CF验证通过 → cf_clearance Cookie设置到CookieManager
       ↓
onPageFinished → CookieManager → CookieStore（自动同步）
       ↓
webView()返回HTML（被忽略）
       ↓
后续OkHttp请求 → 自动从CookieStore读取cf_clearance → 请求成功
       ↓
loginCheckJs再次执行 → 不含CF特征 → 返回result → 正常加载文章列表
```

### 3.1 HTML 获取回退链数据流

```
Phase 2: AI 调用 html_fetcher.fetch(url)
       ↓
  ┌─────────────────────────────────────────┐
  │ Step 1: curl/requests 直接获取           │
  │   → 成功: 返回 HTML (source=direct)      │
  │   → CF拦截: 记录日志，继续 Step 2        │
  ├─────────────────────────────────────────┤
  │ Step 2: Wayback Machine CDX API 查询     │
  │   → 成功: 清理工具栏 → 返回HTML(wayback) │
  │   → 失败: 记录日志，继续 Step 3          │
  ├─────────────────────────────────────────┤
  │ Step 3: CMS 样本库匹配                   │
  │   → 成功: 返回样本 HTML (source=cms)     │
  │   → 失败: 记录日志，继续 Step 4          │
  ├─────────────────────────────────────────┤
  │ Step 4: Google Cache 查询                │
  │   → 成功: 返回缓存 HTML (source=cache)   │
  │   → 失败: 记录日志，继续 Step 5          │
  ├─────────────────────────────────────────┤
  │ Step 5: Playwright 获取（如可用）         │
  │   → 成功: 返回渲染HTML (source=playwright)│
  │   → 失败: 全部失败 (source=failed)       │
  └─────────────────────────────────────────┘
       ↓
FetchResult { html, source, cms_type, snapshot_date, log }
       ↓
AI 基于 HTML 构建规则
       ↓
Phase 3: JVM MVP2 验证选择器
       ↓
可信度标注（含 HTML 来源维度）
```

### 3.2 CMS 样本库数据流

```
analyze-site.py 检测 CMS 类型
       ↓
html_fetcher 查找 references/cms-samples/{cms_type}/
       ↓
读取 selectors.json → 获取标准选择器映射
       ↓
读取对应页面样本 HTML (list.html/detail.html)
       ↓
JVM MVP2 eval_css(sample_html, selector) → 验证选择器
       ↓
验证通过 → 使用 primary 选择器
验证失败 → 尝试 fallbacks 选择器
全部失败 → 标记为"中可信-CMS样本不匹配"
```

### 3.3 Playwright + JVM Cookie 注入数据流

```
fetch_html.py --url URL --export-cookies cookies.json
       ↓
Playwright 获取渲染后 HTML + CF Cookie
       ↓
HTML → AI 分析结构 / JVM MVP2 验证选择器
       ↓
Cookie → convert_playwright_cookies_to_okhttp()
       ↓
RuleEngineClient.set_cookies(okhttp_cookies)
       ↓
JVM MockJsExtensions.ajax() 携带 Cookie
       ↓
CF 保护网站的 ajax() 请求成功
       ↓
可信度从"低"提升到"中"
```

---

## 4. File Changes（文件变更）

### 新增文件

| 文件 | 说明 | 优先级 |
|------|------|--------|
| `references/anti-crawl/cf-bypass.md` | CF绕过方案文档（含源码验证结论） | P0 |
| `tools/html_fetcher.py` | HTML 获取回退链模块 | P0 |
| `tools/fetch_html.py` | Playwright HTML 获取脚本 | P1 |
| `references/cms-samples/_INDEX.md` | CMS 样本库索引 | P0 |
| `references/cms-samples/maccms-v10/list.html` | 苹果CMS V10 列表页样本 | P0 |
| `references/cms-samples/maccms-v10/detail.html` | 苹果CMS V10 详情页样本 | P0 |
| `references/cms-samples/maccms-v10/search.html` | 苹果CMS V10 搜索页样本 | P0 |
| `references/cms-samples/maccms-v10/play.html` | 苹果CMS V10 播放页样本 | P0 |
| `references/cms-samples/maccms-v10/selectors.json` | 苹果CMS V10 选择器映射 | P0 |
| `references/cms-samples/maccms-x10/list.html` | 苹果CMS X10 列表页样本 | P1 |
| `references/cms-samples/maccms-x10/detail.html` | 苹果CMS X10 详情页样本 | P1 |
| `references/cms-samples/maccms-x10/selectors.json` | 苹果CMS X10 选择器映射 | P1 |
| `references/cms-samples/wordpress/list.html` | WordPress 列表页样本 | P1 |
| `references/cms-samples/wordpress/detail.html` | WordPress 详情页样本 | P1 |
| `references/cms-samples/wordpress/selectors.json` | WordPress 选择器映射 | P1 |
| `references/cms-samples/discuz/list.html` | Discuz 列表页样本 | P2 |
| `references/cms-samples/discuz/detail.html` | Discuz 详情页样本 | P2 |
| `references/cms-samples/discuz/selectors.json` | Discuz 选择器映射 | P2 |
| `references/cms-samples/dedecms/list.html` | DedeCMS 列表页样本 | P2 |
| `references/cms-samples/dedecms/detail.html` | DedeCMS 详情页样本 | P2 |
| `references/cms-samples/dedecms/selectors.json` | DedeCMS 选择器映射 | P2 |

### 修改文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `SKILL.md` | Phase 1-5 每阶段精确修改 + 陷阱速查表新增CF条目 + 参考文档索引更新 + 测试脚本表格更新 | P0 |
| `references/special-scenarios/anti-crawl.md` | 新增 CF 绕过三级策略（webView()自动通过 + startBrowserAwait()降级） | P0 |
| `references/js-extensions/webview.md` | 补充 webView() 用于 CF 绕过的用法说明 | P0 |
| `references/js-extensions/cookie-cache.md` | 补充 Cookie 双向共享机制说明 | P0 |
| `references/js-patterns/url-js-patterns.md` | 补充 loginUrl CF 绕过模式 | P1 |
| `references/js-patterns/rule-js-patterns.md` | 补充 loginCheckJs CF 检测模式 | P1 |
| `references/troubleshooting/html-fetch-traps.md` | 补充 CF 保护网站获取方案 | P0 |
| `references/troubleshooting/source-type-traps.md` | 补充 loginCheckJs 返回值陷阱 | P0 |
| `references/source-analysis/cf-bypass-source.md` | 新增 CF 绕过源码分析文档 | P1 |
| `references/_INDEX.md` | 新增 cms-samples/ 目录索引 + 自进化指引更新 | P0 |
| `scripts/verify-selector.py` | 新增 `--sample` 参数支持 CMS 样本 HTML 输入 | P0 |
| `scripts/analyze-site.py` | 集成 html_fetcher.py 回退链 + Wayback Machine 回退 | P0 |
| `scripts/quick-verify.py` | 增加 CF 检测 | P1 |
| `scripts/deep-verify.py` | 增加 HTML 来源维度 + CMS 样本验证 | P0 |
| `scripts/classify-and-fix.py` | 增加 CMS 样本匹配分类 | P1 |
| `scripts/verify-source.py` | 增加 CF 绕过配置验证 | P0 |
| `tools/rule_engine_client.py` | 新增 `set_cookies()` 方法 + Cookie 格式转换 | P2 |
| `tools/jvm_helpers.py` | 新增 `fetch_html()` 辅助函数 + `assess_confidence()` 增加 HTML 来源维度 | P0 |
| `references/_INDEX.md` | 新增 cms-samples/ 目录索引 | P0 |
| `AGENTS.md` | 更新 skill 描述（新增 HTML 获取能力 + CF 自动绕过） | P0 |

### JVM 源码修改（P2）

| 文件 | 修改内容 |
|------|---------|
| `tools/mvp1-build/src/main/kotlin/.../RuleEngineServer.kt` | 新增 `set_cookies` 命令 |
| `tools/mvp1-build/src/main/kotlin/.../MinimalMockJsExtensions.kt` | ajax() 从 CookieStore 读取 Cookie |
