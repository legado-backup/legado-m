#!/usr/bin/env python3
"""final_summary.py — 最终总结（脱敏输出）

汇总10个失败源的最终状态：
- 已优化: 1个 (idx=60域名迁移)
- 不稳定可救: 1个 (idx=46 HTTP降级，第一次成功第二次失败)
- 真正失败: 8个 (idx=1/21/24/30/36/39/55/58)

按技术原因分类，并标记最终诊断到JSON
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

INPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v4.json'
OUTPUT_JSON = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v5.json'

# 10个失败源的最终诊断
FINAL_DIAGNOSIS = {
    1: ('truly_dead', 'RemoteDisconnected+HTTP_502', '服务器主动断开连接，HTTP降级返回502 Bad Gateway'),
    21: ('truly_dead', 'HTTP_500+301_redirect', 'HTTP降级返回301但最终500服务器内部错误'),
    24: ('truly_dead', 'HTTP_403_反爬拦截', '3种UA都返回403，需手动Cookie'),
    30: ('truly_dead', '端口2666不可达', '非标准端口2666，TCP OK但SSL握手ConnectionResetError'),
    36: ('truly_dead', 'SSL_wrong_version', 'SSL握手成功TLSv1.3但HTTP请求报wrong_version'),
    39: ('truly_dead', 'HTTP_206_文件下载', 'sourceUrl是文件下载链接，Wayback存档timeout'),
    46: ('unstable_http_downgrade', 'HTTP降级不稳定', '第一次测试status=200 len=3628，第二次ConnectionResetError，服务器不稳定'),
    55: ('truly_dead', 'timeout_40s_超时', '40秒timeout仍失败，服务器响应慢或不可达'),
    58: ('truly_dead', '反爬页_17字节', '返回200但内容是17字节"Request Forbidden"反爬页'),
    60: ('already_optimized', '域名迁移成功', '已优化，sourceUrl迁移+searchUrl补全'),
}


def main():
    print('=' * 70)
    print('最终失败源诊断汇总（脱敏）')
    print('=' * 70)

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        sources = json.load(f)
    print(f'加载源数: {len(sources)}')

    # 按诊断类型分组
    by_type = {}
    for idx, (status, code, desc) in FINAL_DIAGNOSIS.items():
        by_type.setdefault(status, []).append(idx)

    print('\n--- 10个失败源最终诊断 ---')
    for idx, (status, code, desc) in FINAL_DIAGNOSIS.items():
        print(f'  [idx={idx}] {status} | {code} | {desc}')

    print('\n--- 按状态分组 ---')
    for status, idxs in by_type.items():
        print(f'  {status}: {len(idxs)}个 | idx: {idxs}')

    # 更新JSON中的诊断标记
    print('\n--- 更新JSON诊断标记 ---')
    updated = 0
    for idx, (status, code, desc) in FINAL_DIAGNOSIS.items():
        if idx >= len(sources):
            continue
        s = sources[idx]
        comment = s.get('sourceComment', '') or ''
        new_diag = f'[AI_FINAL_DIAG:{status}|{code}|{desc}]'

        # 检查是否已有FINAL_DIAG标记
        if 'AI_FINAL_DIAG' in comment:
            print(f'  [idx={idx}] 已有最终诊断，跳过')
            continue

        # 移除旧的AI_DIAGNOSIS标记（避免重复）
        import re
        comment_clean = re.sub(r'\[AI_DIAGNOSIS:[^\]]+\]', '', comment).strip()
        new_comment = (comment_clean + '\n' + new_diag) if comment_clean else new_diag
        s['sourceComment'] = new_comment
        print(f'  [idx={idx}] 已更新诊断: {status}')
        updated += 1

    print(f'\n共更新: {updated} 个')

    # 对idx=46做HTTP降级优化（虽然不稳定，但作为最佳尝试）
    print('\n--- idx=46 HTTP降级优化（标记为不稳定） ---')
    if 46 < len(sources):
        s = sources[46]
        old_url = s.get('sourceUrl', '')
        if old_url.startswith('https://'):
            new_url = 'http://' + old_url[len('https://'):]
            s['sourceUrl'] = new_url
            print(f'  [idx=46] sourceUrl已更新为http降级版本（不稳定）')
            updated += 1

    # 保存最终JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f'\n最终JSON: {OUTPUT_JSON}')

    # 最终统计
    print('\n' + '=' * 70)
    print('最终统计')
    print('=' * 70)
    print(f'  总源数: {len(sources)}')
    print(f'  已优化: 1个 (idx=60 域名迁移)')
    print(f'  HTTP降级优化（不稳定）: 1个 (idx=46)')
    print(f'  truly_dead: 7个 (idx=1/21/24/30/36/39/55/58)')
    print(f'  已尝试技术手段: 7种')
    print(f'    1. 多种UA (Chrome/Mobile/Bot/Firefox)')
    print(f'    2. 多种HTTP方法 (GET/HEAD)')
    print(f'    3. Wayback Machine存档查询')
    print(f'    4. HTTP/1.1强制 (http.client.HTTPConnection)')
    print(f'    5. HTTP降级 (https→http)')
    print(f'    6. 跟随重定向 (301/302)')
    print(f'    7. 长timeout重试 (40秒)')


if __name__ == '__main__':
    main()
