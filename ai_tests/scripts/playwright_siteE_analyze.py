#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点E深度结构分析脚本（脱敏输出）
分析页面中的图片/按钮/文本/可点击元素，定位子站入口
"""
import sys
import re
import json
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

SITE_E_URL = "https://av.avav2.lol/"

# 需要过滤的微软/通用服务域名
MS_DOMAINS = {
    "microsoft.com", "microsoftonline.com", "live.com", "office.com",
    "office365.com", "sway.cloud.microsoft", "sway.office.com",
    "azureedge.net", "msftauth.net", "sharepoint.com", "docs.com",
    "skype.com", "bing.com", "msn.com", "windows.net", "xbox.com",
    "github.com", "linkedin.com", "twitter.com", "facebook.com",
    "youtube.com", "youtu.be", "vimeo.com", "soundcloud.com",
    "sketchfab.com", "pickit.com", "google.com", "googleapis.com",
    "gstatic.com", "cloudflare.com", "jsdelivr.net", "unpkg.com",
    "w3.org", "schema.org",
}


def sanitize_url(url):
    """URL脱敏：域名→站点代号，路径模式化"""
    if not url:
        return "[空]"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # 判断域名类型
        is_ms = any(domain == ms or domain.endswith("." + ms) for ms in MS_DOMAINS)
        if is_ms:
            return f"[微软域名]/{parsed.path[:30]}"
        if "avav" in domain or "av" in domain:
            return f"[站点E]/{parsed.path[:30]}"
        # 其他域名用代号
        return f"[域名:{domain.split('.')[-1]}]/{parsed.path[:30]}"
    except Exception:
        return "[解析失败]"


def sanitize_text(text, max_len=80):
    """文本脱敏：截断+替换敏感内容"""
    if not text:
        return "[空]"
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def main():
    print("=== 站点E深度结构分析（脱敏）===")
    print(f"Python: {sys.executable}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            # 步骤1：访问站点E
            print("[步骤1] 访问站点E首页...")
            page.goto(SITE_E_URL, timeout=30000, wait_until="domcontentloaded")
            print(f"  当前URL: {sanitize_url(page.url)}")
            print(f"  页面标题: {sanitize_text(page.title(), 50)}")

            # 步骤2：等待JS跳转（等更久，15秒）
            print("[步骤2] 等待JS跳转（15秒）...")
            page.wait_for_timeout(15000)
            print(f"  跳转后URL: {sanitize_url(page.url)}")

            # 步骤3：等待页面渲染
            print("[步骤3] 等待页面渲染...")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

            # 步骤4：滚动页面触发懒加载
            print("[步骤4] 滚动页面...")
            for i in range(8):
                page.evaluate(f"window.scrollTo(0, {i * 600})")
                page.wait_for_timeout(800)
            # 滚回顶部
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)

            # 步骤5：提取所有链接（含相对链接）
            print("[步骤5] 提取所有链接...")
            all_links = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.map(a => ({
                    href: a.href,
                    text: a.textContent.trim().substring(0, 60),
                    target: a.target,
                    rel: a.rel
                }));
            }""")
            print(f"  总链接数: {len(all_links)}")
            for i, link in enumerate(all_links):
                print(f"  链接[{i}]: {sanitize_url(link['href'])} | 文本: {sanitize_text(link['text'], 40)} | target: {link.get('target','')}")

            # 步骤6：提取所有图片
            print("[步骤6] 提取所有图片...")
            all_images = page.evaluate("""() => {
                const imgs = Array.from(document.querySelectorAll('img'));
                return imgs.map(img => ({
                    src: img.src || img.getAttribute('data-src') || '',
                    alt: img.alt || '',
                    cls: img.className,
                    parentTag: img.parentElement ? img.parentElement.tagName : '',
                    parentHref: img.parentElement && img.parentElement.tagName === 'A' ? img.parentElement.href : ''
                }));
            }""")
            print(f"  总图片数: {len(all_images)}")
            for i, img in enumerate(all_images):
                print(f"  图片[{i}]: src={sanitize_url(img['src'])} | alt={sanitize_text(img['alt'], 30)} | 父元素: {img['parentTag']}" + (f" | 父链接: {sanitize_url(img['parentHref'])}" if img['parentHref'] else ""))

            # 步骤7：提取所有按钮和可点击元素
            print("[步骤7] 提取按钮/可点击元素...")
            clickables = page.evaluate("""() => {
                const results = [];
                // button元素
                document.querySelectorAll('button, [role="button"], [onclick]').forEach(el => {
                    results.push({
                        tag: el.tagName,
                        cls: el.className.substring(0, 50),
                        text: el.textContent.trim().substring(0, 60),
                        onclick: el.getAttribute('onclick') ? '有onclick' : '',
                        href: el.getAttribute('href') || ''
                    });
                });
                return results;
            }""")
            print(f"  可点击元素数: {len(clickables)}")
            for i, el in enumerate(clickables[:20]):
                print(f"  点击元素[{i}]: tag={el['tag']} | cls={sanitize_text(el['cls'], 30)} | 文本: {sanitize_text(el['text'], 40)} | href: {sanitize_url(el['href'])}")

            # 步骤8：提取页面文本内容（前2000字符）
            print("[步骤8] 提取页面文本内容（脱敏，前2000字符）...")
            body_text = page.evaluate("() => document.body.innerText || ''")
            print(f"  文本总长度: {len(body_text)}")
            # 脱敏：替换URL
            body_text_sanitized = re.sub(r'https?://[^\s<>"\']+', '[URL]', body_text)
            print(f"  文本前2000字符:")
            print(body_text_sanitized[:2000])

            # 步骤9：提取所有iframe
            print("[步骤9] 提取iframe...")
            iframes = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('iframe')).map(f => ({
                    src: f.src,
                    cls: f.className
                }));
            }""")
            print(f"  iframe数量: {len(iframes)}")
            for i, f in enumerate(iframes):
                print(f"  iframe[{i}]: src={sanitize_url(f['src'])}")

            # 步骤10：提取卡片/区块结构（可能是子站入口）
            print("[步骤10] 提取卡片/区块结构...")
            cards = page.evaluate("""() => {
                const selectors = [
                    '.card', '.item', '.box', '.tile', '.module',
                    '[class*="card"]', '[class*="item"]', '[class*="box"]',
                    '[class*="link"]', '[class*="site"]', '[class*="nav"]'
                ];
                const seen = new Set();
                const results = [];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        const key = el.outerHTML.substring(0, 100);
                        if (!seen.has(key) && results.length < 30) {
                            seen.add(key);
                            const a = el.querySelector('a[href]');
                            const img = el.querySelector('img');
                            results.push({
                                tag: el.tagName,
                                cls: el.className.substring(0, 60),
                                text: el.textContent.trim().substring(0, 80),
                                hasLink: !!a,
                                linkHref: a ? a.href : '',
                                hasImg: !!img,
                                imgSrc: img ? (img.src || img.getAttribute('data-src') || '') : ''
                            });
                        }
                    });
                });
                return results;
            }""")
            print(f"  卡片/区块数: {len(cards)}")
            for i, card in enumerate(cards[:30]):
                print(f"  区块[{i}]: tag={card['tag']} | cls={sanitize_text(card['cls'], 40)} | 文本: {sanitize_text(card['text'], 50)} | 有链接: {card['hasLink']} | 链接: {sanitize_url(card['linkHref'])} | 有图: {card['hasImg']}")

            # 步骤11：保存完整HTML用于分析（优先，避免截图超时影响）
            print("[步骤11] 保存HTML...")
            html = page.content()
            with open("output/siteE_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  HTML已保存: output/siteE_page.html (长度: {len(html)})")

            # 步骤12：截图保存（可能超时，不影响HTML）
            print("[步骤12] 截图保存...")
            try:
                page.screenshot(path="output/siteE_screenshot.png", full_page=True)
                print("  截图已保存: output/siteE_screenshot.png")
            except Exception as e:
                print(f"  [WARN] 截图失败: {type(e).__name__}")

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

    print("\n=== 分析完成 ===")


if __name__ == "__main__":
    main()
