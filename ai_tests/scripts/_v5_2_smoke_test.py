"""Smoke test: 用前 3 个源快速验证脚本逻辑"""
import sys
sys.path.insert(0, r"f:\myself\github\WeAgentChat\temp\legado\ai_tests\scripts")
import json
from pathlib import Path
from v5_2_rule_verify import load_sources, parse_rule_to_css_list, convert_single_segment, apply_css_list, find_common_selector
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# 1) 测试规则转换
test_rules = [
    "ul[!0]",
    "div.pic.vodst>ul>li",
    "class.tr3[!0:3]",
    "class.video-item",
    "id.content@li",
    "div.cell_box",
    "class.text-card-foreground",
    "$.model.data",
    "//div[@class='vodContainer-list']/div",
    ".vod-item",
    "article",
    "ul li.list-item",
]
print("=== 规则转换测试 ===")
for r in test_rules:
    css_list, rt = parse_rule_to_css_list(r)
    print(f"  {r!r:60} -> type={rt:8}  css={css_list}")

# 2) 用前3个源做真实访问
sources = load_sources()
print(f"\n=== 前 3 个源 smoke test ===")
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(
        viewport={"width": 375, "height": 667},
        user_agent="Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Mobile",
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    for i in range(3):
        s = sources[i]
        url = s.get("sourceUrl", "")
        rule = s.get("ruleArticles", "")
        print(f"\n[idx={i}] ruleArticles={rule!r}")
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)
            html = page.content()
            print(f"  status={resp.status if resp else None}  html_len={len(html)}")
            soup = BeautifulSoup(html, "lxml")
            css_list, rt = parse_rule_to_css_list(rule)
            print(f"  rule_type={rt}  css={css_list}")
            if rt == "css" and css_list:
                elements = apply_css_list(soup, css_list)
                print(f"  matched_count={len(elements)}")
            else:
                print(f"  skip apply (rule_type={rt})")
            # 通用选择器
            common = find_common_selector(soup)
            print(f"  common_selectors_top3={common[:3]}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {str(e)[:200]}")
    browser.close()
print("\n=== smoke test 完成 ===")
