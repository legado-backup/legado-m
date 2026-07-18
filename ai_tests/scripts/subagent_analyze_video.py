"""
subagent_analyze_video.py
深度分析type=2视频源,设计ruleContent适配VideoPlayerActivity
输出脱敏JSON,不包含业务字段原文
"""
import asyncio
import json
import re
import sys
import os
from pathlib import Path

# 输出安全: 导入Playwright时异常消息脱敏
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)


# ========== 脱敏工具 ==========
def mask_url(url: str) -> str:
    """URL脱敏: 只保留路径模式,域名替换为[DOMAIN]"""
    if not url or not isinstance(url, str):
        return ""
    # 替换域名为[DOMAIN]
    masked = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', url)
    # 替换长数字ID为{id}
    masked = re.sub(r'/\d{4,}', '/{id}', masked)
    # 替换可能的token参数
    masked = re.sub(r'(token|key|sign|auth|password|secret)=[^&\s"\'<>]+', r'\1=***', masked, flags=re.IGNORECASE)
    return masked


def mask_text(text: str, max_len: int = 80) -> str:
    """文本脱敏: 截断+替换敏感词"""
    if not text or not isinstance(text, str):
        return ""
    # 替换URL
    text = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', text)
    text = re.sub(r'(token|cookie|password|key|secret|auth)=[^&\s"\'<>]+', r'\1=***', text, flags=re.IGNORECASE)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def get_domain_code(idx: int) -> str:
    """根据idx分配站点代号"""
    return {48: "站点A", 69: "站点B", 70: "站点C"}.get(idx, f"站点{idx}")


# ========== Playwright 分析器 ==========
class VideoSourceAnalyzer:
    def __init__(self, source_data: dict, idx: int):
        self.data = source_data
        self.idx = idx
        self.domain_code = get_domain_code(idx)
        self.source_url = source_data.get("sourceUrl", "")
        self.search_url = source_data.get("searchUrl", "")
        self.sort_url = source_data.get("sortUrl", "")
        self.header = source_data.get("header", "")
        self.enable_js = source_data.get("enableJs", True)
        self.login_url = source_data.get("loginUrl", "")
        self.enabled_cookie_jar = source_data.get("enabledCookieJar", False)

        # 分析结果
        self.page_title = ""
        self.html_length = 0
        self.list_candidates = []  # 列表项候选
        self.script_video_urls = []  # script中的视频URL
        self.iframe_srcs = []  # iframe src
        self.video_tags = []  # <video>标签
        self.source_tags = []  # <source>标签
        self.m3u8_urls = []
        self.mp4_urls = []
        self.page_accessible = False
        self.error_msg = ""
        self.cf_challenge = False
        self.has_popup = False
        self.favicon_url = ""

    def _parse_header(self) -> dict:
        """解析header字段"""
        if not self.header:
            return {}
        try:
            h = json.loads(self.header)
            return h if isinstance(h, dict) else {}
        except Exception:
            return {}

    async def analyze(self) -> dict:
        """分析单个源"""
        if not self.source_url:
            return self._build_result(success=False, error="empty_source_url")

        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Linux; Android 12; SM-G9910) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
                    viewport={"width": 412, "height": 915},
                    locale="zh-CN",
                    extra_http_headers=self._parse_header(),
                )
                # 注入反检测
                await context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )

                page = await context.new_page()
                page.set_default_timeout(30000)
                page.set_default_navigation_timeout(45000)

                # 访问首页
                try:
                    resp = await page.goto(self.source_url, wait_until="domcontentloaded")
                    if resp and resp.status >= 400:
                        self.error_msg = f"http_{resp.status}"
                except Exception as e:
                    self.error_msg = mask_text(str(e), 120)
                    # 可能是Cloudflare或网络问题,尝试继续

                # 等待页面加载
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass

                # 检测Cloudflare
                content = await page.content()
                self.html_length = len(content)
                if "challenge-platform" in content or "cf-browser-verification" in content:
                    self.cf_challenge = True
                    # 等待challenge完成
                    try:
                        await page.wait_for_timeout(8000)
                        content = await page.content()
                        self.html_length = len(content)
                        if "challenge-platform" not in content:
                            self.cf_challenge = False
                            self.page_accessible = True
                    except Exception:
                        pass
                else:
                    self.page_accessible = True

                if self.page_accessible:
                    await self._extract_page_info(page, content)

                await context.close()

            except Exception as e:
                self.error_msg = mask_text(str(e), 150)
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

        return self._build_result(success=self.page_accessible)

    async def _extract_page_info(self, page, content: str):
        """提取页面信息"""
        try:
            self.page_title = mask_text(await page.title(), 60)
        except Exception:
            self.page_title = ""

        # favicon
        try:
            favicon = await page.evaluate("""() => {
                const link = document.querySelector('link[rel*="icon"]') || document.querySelector('link[rel="shortcut icon"]');
                return link ? link.href : '';
            }""")
            self.favicon_url = favicon or ""
        except Exception:
            self.favicon_url = ""

        # 列表项候选 (查找重复结构的容器)
        try:
            self.list_candidates = await page.evaluate("""() => {
                const candidates = [];
                // 查找重复子元素最多的容器
                const containers = document.querySelectorAll('ul, ol, div.list, div[class*="list"], div[class*="item"], section, main');
                let best = null;
                let maxCount = 0;
                containers.forEach(c => {
                    const children = c.children;
                    if (children.length >= 5) {
                        // 检查子元素是否相似(同一标签)
                        const tags = new Set();
                        for (let i = 0; i < Math.min(children.length, 10); i++) {
                            tags.add(children[i].tagName);
                        }
                        if (tags.size <= 2) {
                            if (children.length > maxCount) {
                                maxCount = children.length;
                                best = {
                                    tag: c.tagName,
                                    className: c.className || '',
                                    id: c.id || '',
                                    childCount: children.length,
                                    childTag: children[0] ? children[0].tagName : '',
                                    childClass: children[0] ? (children[0].className || '') : ''
                                };
                            }
                        }
                    }
                });
                if (best) candidates.push(best);
                return candidates;
            }""")
        except Exception:
            self.list_candidates = []

        # script中的视频URL
        try:
            urls = await page.evaluate("""() => {
                const urls = {m3u8: [], mp4: [], iframe: [], video: [], source: []};
                const scripts = document.querySelectorAll('script');
                for (const s of scripts) {
                    const text = s.textContent || '';
                    const m3u8 = text.match(/https?:\\/\\/[^\\s"'<>]+\\.m3u8[^\\s"'<>]*/g) || [];
                    const mp4 = text.match(/https?:\\/\\/[^\\s"'<>]+\\.mp4[^\\s"'<>]*/g) || [];
                    urls.m3u8.push(...m3u8);
                    urls.mp4.push(...mp4);
                }
                // iframe
                document.querySelectorAll('iframe').forEach(f => {
                    if (f.src) urls.iframe.push(f.src);
                });
                // video标签
                document.querySelectorAll('video').forEach(v => {
                    urls.video.push({src: v.src || '', currentSrc: v.currentSrc || ''});
                });
                // source标签
                document.querySelectorAll('source').forEach(s => {
                    if (s.src) urls.source.push(s.src);
                });
                return urls;
            }""")
            self.m3u8_urls = urls.get("m3u8", [])[:3]  # 最多保留3个
            self.mp4_urls = urls.get("mp4", [])[:3]
            self.iframe_srcs = urls.get("iframe", [])[:3]
            self.video_tags = urls.get("video", [])[:3]
            self.source_tags = urls.get("source", [])[:3]
        except Exception:
            pass

        # 检测弹框
        try:
            self.has_popup = await page.evaluate("""() => {
                return !!document.querySelector('.modal.show, .dialog[style*="block"], [class*="popup"][style*="block"]');
            }""")
        except Exception:
            self.has_popup = False

    def _design_rule_content(self) -> tuple:
        """设计ruleContent,返回(rule_content, strategy)"""
        # V1: script中有m3u8/mp4 URL
        if self.m3u8_urls or self.mp4_urls:
            strategy = "V1"
            rule = """<js>
(function(){
    var scripts = document.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent || '';
        var match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.m3u8[^\\s"'<>]*/);
        if (match) return match[0];
        match = text.match(/https?:\\/\\/[^\\s"'<>]+\\.mp4[^\\s"'<>]*/);
        if (match) return match[0];
    }
    return '';
})();
</js>"""
            return rule, strategy

        # V3: iframe src提取
        if self.iframe_srcs:
            strategy = "V3"
            rule = """<js>
(function(){
    var f = document.querySelector('iframe[src]');
    return f ? f.src : '';
})();
</js>"""
            return rule, strategy

        # video/source标签
        if self.video_tags or self.source_tags:
            strategy = "V1"
            rule = """<js>
(function(){
    var v = document.querySelector('video[src], video source[src]');
    if (v) return v.src || v.getAttribute('src') || '';
    return '';
})();
</js>"""
            return rule, strategy

        # sniffer: 留空让VideoPlayerActivity嗅探器处理
        strategy = "sniffer"
        return "", strategy

    def _design_rule_articles(self) -> str:
        """设计ruleArticles"""
        if self.list_candidates:
            c = self.list_candidates[0]
            if c.get("className"):
                return f"class.{c['className'].split()[0]}"
            elif c.get("id"):
                return f"id.{c['id']}"
            else:
                return c.get("tag", "div").lower()
        return ""

    def _design_rule_next_page(self) -> str:
        """设计ruleNextPage"""
        # 通用: 查找a标签含"下一页"或"next"
        return "text.下一页@href||text.next@href||class.next@href"

    def _build_js_rule(self) -> str:
        """设计jsRule(关闭弹框)"""
        if self.has_popup:
            return """// 自动关闭弹框
(function(){
    document.querySelectorAll('.modal.show, .dialog, [class*="popup"]').forEach(e => e.remove());
})();"""
        return ""

    def _build_result(self, success: bool, error: str = "") -> dict:
        """构建脱敏结果"""
        rule_content, strategy = self._design_rule_content() if success else ("", "sniffer")
        rule_articles = self._design_rule_articles() if success else ""

        result = {
            "idx": self.idx,
            "type": 2,
            "domain_code": self.domain_code,
            "source_url_accessible": success,
            "page_title_masked": self.page_title,
            "html_length": self.html_length,
            "fields": {
                "sourceIcon": mask_url(self.favicon_url) if self.favicon_url else mask_url(self.data.get("sourceIcon", "")),
                "searchUrl": self._mask_search_url(),
                "sortUrl": self._mask_sort_url(),
                "ruleArticles": rule_articles or self.data.get("ruleArticles", ""),
                "ruleTitle": self._infer_rule_title(),
                "ruleLink": self._infer_rule_link(),
                "ruleImage": self._infer_rule_image(),
                "ruleNextPage": self._design_rule_next_page(),
                "rulePubDate": "",
                "ruleContent": rule_content,
            },
            "special_config": {
                "loginUrl": "[LOGIN_URL]" if self.login_url else "",
                "enabledCookieJar": bool(self.enabled_cookie_jar),
                "enableJs": bool(self.enable_js),
                "loadWithBaseUrl": bool(self.data.get("loadWithBaseUrl", False)),
                "jsRule": self._build_js_rule(),
            },
            "rule_content_strategy": strategy,
            "page_signals": {
                "cf_challenge": self.cf_challenge,
                "has_popup": self.has_popup,
                "m3u8_count": len(self.m3u8_urls),
                "mp4_count": len(self.mp4_urls),
                "iframe_count": len(self.iframe_srcs),
                "video_tag_count": len(self.video_tags),
                "list_candidate_count": len(self.list_candidates),
            },
            "analysis_notes": self._build_notes(success, error, strategy),
        }
        if error:
            result["error"] = error
        return result

    def _mask_search_url(self) -> str:
        """脱敏searchUrl,保留结构"""
        s = self.search_url or self.data.get("searchUrl", "")
        if not s:
            return ""
        # 保留搜索占位符,域名替换
        masked = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', s)
        return masked

    def _mask_sort_url(self) -> str:
        """脱敏sortUrl,只保留分类数量和路径模式"""
        s = self.data.get("sortUrl", "")
        if not s:
            return ""
        # 统计分类数
        lines = [l for l in s.split("\n") if l.strip()]
        cat_count = len(lines)
        # 取第一行路径模式
        first = lines[0] if lines else ""
        masked_first = re.sub(r'https?://[^/\s"\'<>]+', '[DOMAIN]', first)
        masked_first = re.sub(r'/\d{4,}', '/{id}', masked_first)
        return f"[{cat_count}个分类] {masked_first}"

    def _infer_rule_title(self) -> str:
        """推断ruleTitle"""
        if self.list_candidates:
            return "tag.a.0@text||class.title@text"
        return self.data.get("ruleTitle", "")

    def _infer_rule_link(self) -> str:
        """推断ruleLink"""
        if self.list_candidates:
            return "tag.a.0@href"
        return self.data.get("ruleLink", "")

    def _infer_rule_image(self) -> str:
        """推断ruleImage"""
        if self.list_candidates:
            return "tag.img@src||class.img@html"
        return self.data.get("ruleImage", "")

    def _build_notes(self, success: bool, error: str, strategy: str) -> str:
        """构建分析备注"""
        notes = []
        if not success:
            notes.append(f"页面访问失败: {error or self.error_msg}")
            return "; ".join(notes)

        if self.cf_challenge:
            notes.append("检测到Cloudflare防护,已等待challenge完成")
        if self.has_popup:
            notes.append("检测到弹框,已配置jsRule自动关闭")
        if self.login_url:
            notes.append("登录源,已配置loginUrl+enabledCookieJar")
        if self.m3u8_urls:
            notes.append(f"script中发现{len(self.m3u8_urls)}个m3u8 URL,使用V1模板")
        elif self.mp4_urls:
            notes.append(f"script中发现{len(self.mp4_urls)}个mp4 URL,使用V1模板")
        elif self.iframe_srcs:
            notes.append(f"发现{len(self.iframe_srcs)}个iframe,使用V3模板")
        elif self.video_tags or self.source_tags:
            notes.append("发现video/source标签,使用V1变体")
        else:
            notes.append("未发现直接视频URL,使用嗅探器策略(sniffer),ruleContent留空")

        if self.list_candidates:
            c = self.list_candidates[0]
            notes.append(f"列表候选: tag={c.get('tag')}, class={c.get('className','')[:30]}, childCount={c.get('childCount')}")
        else:
            notes.append("未找到明显列表结构,可能需要人工调整ruleArticles")

        return "; ".join(notes)


# ========== 主流程 ==========
async def main():
    input_file = "output/rss/classified_v2.json"
    output_file = "output/rss/subagent_video_analysis.json"

    if not Path(input_file).exists():
        print(f"ERROR: input file not found: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 筛选type=2
    type2_sources = [(i, item) for i, item in enumerate(data) if item.get("type") == 2]
    print(f"[INFO] 找到 {len(type2_sources)} 个 type=2 视频源")
    print(f"[INFO] idx列表: {[idx for idx, _ in type2_sources]}")

    results = []
    success_count = 0
    failed_count = 0

    for idx, source in type2_sources:
        print(f"\n[ANALYZE] idx={idx} ({get_domain_code(idx)})")
        analyzer = VideoSourceAnalyzer(source, idx)
        try:
            result = await analyzer.analyze()
            results.append(result)
            if result.get("source_url_accessible"):
                success_count += 1
                print(f"  [OK] strategy={result.get('rule_content_strategy')}, html_len={result.get('html_length')}")
            else:
                failed_count += 1
                print(f"  [FAIL] error={result.get('error', result.get('analysis_notes',''))}")
        except Exception as e:
            failed_count += 1
            err = mask_text(str(e), 100)
            print(f"  [EXCEPTION] {err}")
            results.append({
                "idx": idx,
                "type": 2,
                "domain_code": get_domain_code(idx),
                "source_url_accessible": False,
                "error": err,
                "fields": {},
                "special_config": {},
                "rule_content_strategy": "sniffer",
                "analysis_notes": f"分析异常: {err}",
            })

    # 构建输出
    output = {
        "agent": "video_source_analyzer",
        "total_analyzed": len(type2_sources),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OUTPUT] 已保存到 {output_file}")
    print(f"[SUMMARY] 成功 {success_count}/{len(type2_sources)}, 失败 {failed_count}")


if __name__ == "__main__":
    asyncio.run(main())
