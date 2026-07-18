#!/usr/bin/env python3
"""mark_user_optional.py — 更新7个源的标记为"用户可选验证"

保留loginUrl + enabledCookieJar 配置
把sourceComment改为"用户可选验证"标记
"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
NEEDS_LOGIN_IDX = [21, 24, 30, 36, 39, 55, 58]

# 新标记：用户可选验证
NEW_MARKER = '[AI_CONFIG:user_optional_login|保留loginUrl配置-模拟器DNS/网络问题-用户可在App内尝试登录后验证可用性]'


def main():
    print('=' * 60)
    print('更新7个源标记为"用户可选验证"')
    print('=' * 60)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f'JSON源数: {len(sources)}')

    updated = 0
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            continue
        s = sources[idx]
        url = s.get('sourceUrl', '')
        if not url.startswith('http'):
            continue

        old_comment = s.get('sourceComment', '') or ''
        # 保留loginUrl + enabledCookieJar配置（已存在）
        # 只更新sourceComment为"用户可选验证"
        s['sourceComment'] = NEW_MARKER
        updated += 1
        print(f'  idx={idx} url_len={len(url)} loginUrl_len={len(s.get("loginUrl", "") or "")} cookieJar={s.get("enabledCookieJar", False)}')
        print(f'    旧comment_len={len(old_comment)} 新comment_len={len(NEW_MARKER)}')

    print(f'\n更新数: {updated}/{len(NEEDS_LOGIN_IDX)}')

    # 保存
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'已保存: {JSON_PATH}')

    # 同步更新精简版（如果有）
    import os
    lite_path = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_lite_v2.json'
    if os.path.exists(lite_path):
        with open(lite_path, 'r', encoding='utf-8') as f:
            lite_sources = json.load(f)
        # 精简版已移除idx=1，源数=64，但其他idx不变
        lite_updated = 0
        for s in lite_sources:
            url = s.get('sourceUrl', '')
            if not url.startswith('http'):
                continue
            # 找对应的原JSON idx
            for orig_idx, orig_s in enumerate(sources):
                if orig_s.get('sourceUrl', '') == url and orig_idx in NEEDS_LOGIN_IDX:
                    s['sourceComment'] = NEW_MARKER
                    lite_updated += 1
                    break
        with open(lite_path, 'w', encoding='utf-8') as f:
            json.dump(lite_sources, f, ensure_ascii=False, indent=2)
        print(f'精简版同步更新: {lite_updated}个，保存到: {lite_path}')


if __name__ == '__main__':
    main()
