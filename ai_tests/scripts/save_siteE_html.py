#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速保存站点E页面HTML（用于URL提取）"""
import sys
from playwright.sync_api import sync_playwright

SITE_E_URL = "https://av.avav2.lol/"

def main():
    print("=== 快速保存站点E HTML ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        try:
            print("[1] 访问站点E...")
            page.goto(SITE_E_URL, timeout=30000, wait_until="domcontentloaded")
            print("[2] 等待JS跳转（15秒）...")
            page.wait_for_timeout(15000)
            print("[3] 滚动触发懒加载...")
            for i in range(5):
                page.evaluate(f"window.scrollTo(0, {i * 600})")
                page.wait_for_timeout(500)
            page.wait_for_timeout(2000)
            print("[4] 保存HTML...")
            html = page.content()
            with open("output/siteE_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  HTML已保存: output/siteE_page.html (长度: {len(html)})")
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
        finally:
            browser.close()
    print("=== 完成 ===")

if __name__ == "__main__":
    main()
