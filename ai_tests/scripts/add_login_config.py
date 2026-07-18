#!/usr/bin/env python3
"""add_login_config.py — 为反爬/失败源添加loginUrl配置（脱敏）

为7个失败源添加登录配置，让用户在App中通过WebView登录获取Cookie：
- loginUrl: 设为sourceUrl（用户在主页登录）
- enabledCookieJar: true（默认值，显式设置）
- 标记为needs_user_login

7个源：idx=21/24/30/36/39/55/58
"""
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v5.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'

# 7个需要登录配置的源
LOGIN_SOURCES = [21, 24, 30, 36, 39, 55, 58]


def main():
    print('=' * 70)
    print('为7个失败源添加loginUrl配置（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    configured = 0
    for idx in LOGIN_SOURCES:
        if idx >= len(sources):
            continue
        s = sources[idx]
        source_url = s.get('sourceUrl', '')
        if not source_url.startswith('http'):
            print(f'  [idx={idx}] 跳过: sourceUrl非http')
            continue

        # 设置loginUrl=sourceUrl（用户在App中点击登录按钮会打开WebView访问这个URL）
        old_login_url = s.get('loginUrl', '') or ''
        # 强制覆盖：如果loginUrl为空或长度小于5（无效值），用sourceUrl覆盖
        if len(old_login_url) < 5:
            s['loginUrl'] = source_url
            print(f'  [idx={idx}] 设置loginUrl=sourceUrl (len={len(source_url)}, 覆盖旧值len={len(old_login_url)})')
        else:
            print(f'  [idx={idx}] loginUrl已存在且有效 (len={len(old_login_url)})')

        # 显式启用CookieJar（默认就是true，但显式设置避免被覆盖）
        s['enabledCookieJar'] = True
        print(f'  [idx={idx}] enabledCookieJar=True')

        # 更新sourceComment标记为needs_user_login
        comment = s.get('sourceComment', '') or ''
        # 清除旧的AI_FINAL_DIAG标记
        comment_clean = re.sub(r'\[AI_FINAL_DIAG:[^\]]+\]', '', comment).strip()
        comment_clean = re.sub(r'\[AI_DIAGNOSIS:[^\]]+\]', '', comment_clean).strip()

        new_diag = '[AI_CONFIG:needs_user_login|配置loginUrl+CookieJar-用户在App内登录后可用]'
        new_comment = (comment_clean + '\n' + new_diag) if comment_clean else new_diag
        s['sourceComment'] = new_comment
        print(f'  [idx={idx}] 更新sourceComment: needs_user_login')

        configured += 1
        print()

    print(f'\n共配置: {configured} 个源')

    # 保存
    print('\n--- 保存最终JSON ---')
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'  路径: {OUTPUT_JSON}')
    print(f'  源数: {len(sources)}')

    # 验证loginUrl是否生效
    print('\n--- 验证loginUrl配置 ---')
    for idx in LOGIN_SOURCES:
        if idx >= len(sources):
            continue
        s = sources[idx]
        login_url = s.get('loginUrl', '') or ''
        cookie_jar = s.get('enabledCookieJar', False)
        has_needs_login = 'needs_user_login' in (s.get('sourceComment', '') or '')
        print(f'  [idx={idx}] loginUrl_len={len(login_url)} cookieJar={cookie_jar} needs_login_marker={has_needs_login}')

    # 统计最终诊断分布
    print('\n--- 最终诊断分布 ---')
    diag_counter = Counter()
    for s in sources:
        comment = s.get('sourceComment', '') or ''
        if 'needs_user_login' in comment:
            diag_counter['needs_user_login'] += 1
        elif 'truly_dead' in comment:
            diag_counter['truly_dead'] += 1
        elif 'unstable_http_downgrade' in comment:
            diag_counter['unstable_http_downgrade'] += 1
        elif 'already_optimized' in comment:
            diag_counter['already_optimized'] += 1
        else:
            diag_counter['normal'] += 1

    for k, v in diag_counter.most_common():
        print(f'  {k}: {v}')

    # 生成精简版（去掉truly_dead，保留needs_user_login）
    print('\n--- 生成精简版JSON ---')
    lite_sources = []
    removed_idx = []
    for i, s in enumerate(sources):
        comment = s.get('sourceComment', '') or ''
        if 'truly_dead' in comment:
            removed_idx.append(i)
        else:
            # 清除所有诊断标记
            cleaned = re.sub(r'\[AI_[A-Z_]+:[^\]]+\]', '', comment).strip()
            s['sourceComment'] = cleaned
            lite_sources.append(s)

    lite_path = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_lite_v2.json'
    with open(lite_path, 'w', encoding='utf-8') as f:
        json.dump(lite_sources, f, ensure_ascii=False, indent=2)
    print(f'  精简版路径: {lite_path}')
    print(f'  精简版源数: {len(lite_sources)} (移除{len(removed_idx)}个truly_dead)')
    print(f'  移除idx: {removed_idx}')


if __name__ == '__main__':
    main()
