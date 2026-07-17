#!/usr/bin/env python3
"""fix_login_url.py — 修复 loginUrl 为 URL 形式（不是 @js: 形式）

根因：cf-bypass.md陷阱#54建议 loginUrl=@js:java.webView(...) 是错误的
源码验证：WebViewLoginFragment.loadUrl() 直接把 loginUrl 当 URL 加载，不执行JS
        只有 SourceLoginDialog（需要 loginUi 非空）才用 getLoginJs() 执行JS

正确方案：loginUrl = sourceUrl，让 WebView 加载 sourceUrl 触发 CF JS Challenge
        自动通过，Cookie 通过 onPageStarted/onPageFinished 自动同步到 CookieStore

用法：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/fix_login_url.py
"""
import json
import sys
from pathlib import Path

# 输入文件
INPUT_JSON = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\rssSource_18AV-new_optimized.json"

def main():
    if not Path(INPUT_JSON).exists():
        print(f"ERROR: 文件不存在 {INPUT_JSON}")
        return 1

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    if not isinstance(sources, list):
        sources = [sources]

    print(f"加载 {len(sources)} 个源")
    for i, src in enumerate(sources):
        old_login = src.get('loginUrl', '')
        source_url = src.get('sourceUrl', '')
        # 不输出原始URL，只输出长度
        print(f"源[{i+1}] sourceUrl长度={len(source_url)} 当前loginUrl长度={len(old_login)}")

        # 关键修复：loginUrl = sourceUrl（URL形式，让WebView直接加载）
        # 不要用 @js: 形式（WebViewLoginFragment不执行JS）
        # 不要设置 loginUi（保持为空，让走WebViewLoginFragment分支）
        # 不要设置 loginCheckJs（避免无限循环，陷阱#57）
        src['loginUrl'] = source_url
        # 清空 loginUi 如果存在
        if 'loginUi' in src and src['loginUi']:
            print(f"  清空 loginUi（原长度={len(src['loginUi'])}）")
            src['loginUi'] = ""
        # 清空 loginCheckJs 如果存在
        if 'loginCheckJs' in src and src['loginCheckJs']:
            print(f"  清空 loginCheckJs（避免无限循环）")
            src['loginCheckJs'] = ""
        # 确保 enabledCookieJar=true（Cookie同步必需）
        src['enabledCookieJar'] = True
        # 确保 enableJs=true（WebView执行JS通过CF必需）
        src['enableJs'] = True

        new_login = src.get('loginUrl', '')
        print(f"  ✅ loginUrl 已修复（长度={len(new_login)}，URL形式）")

    with open(INPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 修复完成，已保存到 {INPUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
