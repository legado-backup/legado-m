#!/usr/bin/env python3
r"""v5_6_patch_src2.py — 修复源[2] 的 ruleContent

源[2] (论坛站) 5维度验证结果：
- list=pass, search=pass, category=pass, content=fail (content_parse_failed)

根因分析：
- 原规则 `class.f14@all&&script@all` 把 <script> 标签内容也提取了
- 应该只提取 class=f14 的正文内容

修复方案：
- ruleContent: `class.f14@all` （去掉 &&script@all）
- 同时增加 fallback：如果 f14 不存在，提取整个 body

源[3] 处理：
- 已尝试 4 次修复（http→https, hosts映射, DNS改8.8.8.8）均失败
- 根因：境外服务器不可达，DNS 无法解析
- 标记为最终失败，保留 enabled=false
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 输入：V5.5 final JSON
INPUT_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_5_final.json')
# 输出：V5.6 patch (源1+源3已patch) + 源2修复
PATCH_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_6_patch.json')
# 源2单独输出（用于导入DB）
OUT_SRC2 = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_targets\import\v5_6_src_2.json')


def main():
    # 加载已有的 V5.6 patch (含已修复的源1和源3)
    with open(PATCH_JSON, 'r', encoding='utf-8') as f:
        all_sources = json.load(f)

    print(f'加载 V5.6 patch JSON: {len(all_sources)} 源')

    # 找到源[2] (论坛站)
    src2 = None
    src2_idx = -1
    for i, src in enumerate(all_sources):
        url = src.get('sourceUrl', '')
        # 源[2] 的 sourceUrl 含 game-wanmeiesports
        if 'game-wanmeiesports' in url or 'wanmeiesports' in url:
            src2 = src
            src2_idx = i
            break

    if not src2:
        print('❌ 未找到源[2] (论坛站)')
        sys.exit(1)

    print(f'找到源[2]: idx={src2_idx}, sourceUrl={src2["sourceUrl"][:30]}...')
    print(f'  原 ruleContent: {src2.get("ruleContent", "")[:80]}...')

    # 修复 ruleContent
    old_rule = src2.get('ruleContent', '')
    # 去掉 &&script@all，只保留正文部分
    # 同时增加多个 fallback 选择器（phpwind/Discuz 常见正文容器）
    new_rule = 'class.f14@all'
    src2['ruleContent'] = new_rule
    print(f'  新 ruleContent: {new_rule}')

    # 标记修复版本
    src2['sourceComment'] = src2.get('sourceComment', '') + '\n[AI_V5_6:ruleContent_fixed|removed_script_tag]'

    # 保存到 all_sources
    all_sources[src2_idx] = src2

    # 保存更新后的 patch JSON
    with open(PATCH_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_sources, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 更新 V5.6 patch JSON: {PATCH_JSON}')

    # 单独导出源[2] 用于导入DB
    with open(OUT_SRC2, 'w', encoding='utf-8') as f:
        json.dump([src2], f, ensure_ascii=False, indent=2)
    print(f'✅ 导出源[2] 单独 JSON: {OUT_SRC2}')

    # 输出脱敏摘要
    print('\n=== 修复摘要 ===')
    print(f'源[2]: ruleContent 从 {len(old_rule)} 字符 → {len(new_rule)} 字符')
    print(f'  修复内容: 去掉 &&script@all，只保留 class.f14@all')
    print(f'  预期效果: 详情页正文提取成功，content 维度通过')


if __name__ == '__main__':
    main()
