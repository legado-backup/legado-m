"""
用 Playwright 访问站点E -> 中转站S(Sway SPA)，渲染后提取子站链接。
输出安全：只输出技术字段，真实域名用代号替代，URL用路径模式替代。
"""
import sys
import re
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# 站点E入口URL
SITE_E_URL = "https://av.avav2.lol/"

# 微软/Sway 相关域名后缀（过滤用）
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


def mask_domain(url: str) -> str:
    """将URL中的域名替换为代号，路径保留模式化"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 移除www前缀
        if domain.startswith("www."):
            domain = domain[4:]
        # 获取域名后缀
        parts = domain.rsplit(".", 1)
        suffix = "." + parts[-1] if len(parts) > 1 else ""
        path = parsed.path
        return f"[域名后缀{suffix}]{path}"
    except Exception:
        return "[无效URL]"


def extract_links(page):
    """从渲染后的页面提取所有外部链接"""
    links = page.evaluate("""() => {
        const anchors = document.querySelectorAll('a[href]');
        return Array.from(anchors).map(a => ({
            href: a.href,
            text: a.textContent.trim().substring(0, 20),
            rect: a.getBoundingClientRect().width > 0
        }));
    }""")
    return links


def main():
    print("=== Playwright Sway 子站链接提取 ===")
    print(f"Python: {sys.executable}")
    print()

    with sync_playwright() as p:
        # 启动chromium，headless模式
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            # 步骤1：访问站点E首页
            print("[步骤1] 访问站点E首页...")
            page.goto(SITE_E_URL, timeout=30000, wait_until="domcontentloaded")
            print(f"  当前URL: [已脱敏]")
            print(f"  页面标题: {page.title()}")

            # 步骤2：等待JS跳转（最多等10秒）
            print("[步骤2] 等待JS跳转...")
            page.wait_for_timeout(5000)  # 等5秒让setTimeout执行

            current_url = page.url
            print(f"  跳转后URL: [已脱敏]")

            # 检查是否跳转到Sway
            if "sway" in current_url.lower() or "microsoft" in current_url.lower():
                print("  [OK] 已跳转到中转站S（Sway）")
            else:
                print(f"  [WARN] 未跳转到Sway，当前域名后缀: .{current_url.split('.')[-1].split('/')[0]}")

            # 步骤3：等待Sway页面渲染完成
            print("[步骤3] 等待Sway页面渲染...")
            # Sway是SPA，需要等待内容加载
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
                print("  [OK] networkidle完成")
            except Exception:
                print("  [WARN] networkidle超时，继续提取")

            # 额外等待确保内容渲染
            page.wait_for_timeout(3000)

            # 尝试滚动页面触发懒加载
            print("[步骤4] 滚动页面触发懒加载...")
            for i in range(5):
                page.evaluate(f"window.scrollTo(0, {i * 500})")
                page.wait_for_timeout(1000)
            # 滚回顶部
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)

            # 步骤5：提取所有链接
            print("[步骤5] 提取页面链接...")
            links = extract_links(page)
            print(f"  总链接数: {len(links)}")
            print(f"  可见链接数: {sum(1 for l in links if l['rect'])}")

            # 步骤6：过滤出子站链接（非微软域名）
            print("[步骤6] 过滤子站链接...")
            sub_sites = []
            ms_links = []
            other_links = []

            for link in links:
                href = link["href"]
                if not href or not href.startswith("http"):
                    continue

                try:
                    parsed = urlparse(href)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]

                    # 检查是否是微软/通用服务域名
                    is_ms = any(domain == ms or domain.endswith("." + ms) for ms in MS_DOMAINS)

                    if is_ms:
                        ms_links.append(link)
                    else:
                        # 可能是子站链接
                        sub_sites.append({
                            "domain": domain,
                            "suffix": "." + domain.rsplit(".", 1)[-1] if "." in domain else "",
                            "path": parsed.path,
                            "has_text": bool(link["text"]),
                            "is_visible": link["rect"]
                        })
                except Exception:
                    other_links.append(link)

            print(f"  微软/通用域名链接: {len(ms_links)}")
            print(f"  其他域名链接: {len(sub_sites)}")
            print()

            # 步骤7：输出子站清单（脱敏）
            print("=== 子站链接清单（脱敏）===")
            print(f"子站数量: {len(sub_sites)}")
            print()

            for i, site in enumerate(sub_sites, 1):
                print(f"=== 子站E{i} ===")
                print(f"  域名后缀: {site['suffix']}")
                print(f"  路径模式: {site['path']}")
                print(f"  有链接文本: {'是' if site['has_text'] else '否'}")
                print(f"  可见: {'是' if site['is_visible'] else '否'}")
                print()

            # 额外：输出页面中的所有文本内容（脱敏，只输出结构信息）
            print("=== 页面结构信息 ===")
            text_content = page.evaluate("""() => {
                const body = document.body;
                if (!body) return {textLen: 0, headings: [], paragraphs: 0, images: 0, iframes: 0};
                return {
                    textLen: body.innerText.length,
                    headings: Array.from(body.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => h.tagName).length,
                    paragraphs: body.querySelectorAll('p').length,
                    images: body.querySelectorAll('img').length,
                    iframes: body.querySelectorAll('iframe').length,
                    divs: body.querySelectorAll('div').length
                };
            }""")
            print(f"  文本长度: {text_content.get('textLen', 0)}")
            print(f"  标题数量: {text_content.get('headings', 0)}")
            print(f"  段落数量: {text_content.get('paragraphs', 0)}")
            print(f"  图片数量: {text_content.get('images', 0)}")
            print(f"  iframe数量: {text_content.get('iframes', 0)}")
            print(f"  div数量: {text_content.get('divs', 0)}")

            # 检查页面是否有实际内容（Sway渲染后应该有内容）
            if text_content.get("textLen", 0) > 100:
                print("  [OK] 页面有内容（Sway已渲染）")
            else:
                print("  [WARN] 页面内容很少（Sway可能未渲染完成）")

        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {str(e)[:200]}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
