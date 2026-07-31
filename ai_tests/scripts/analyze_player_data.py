#!/usr/bin/env python3
"""分析站点D播放页HTML的player_data格式（输出安全：只输出技术结构）"""
import re
import sys
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8')

# 步骤1: 获取入口域名HTML，解析实际域名
ENTRY_URL = "https://qd.18j12m.xyz/rise/"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("=== 步骤1: 获取入口域名HTML ===")
try:
    req = urllib.request.Request(ENTRY_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        entry_html = resp.read().decode('utf-8', errors='ignore')
    print(f"入口HTML长度: {len(entry_html)}")
except Exception as e:
    print(f"获取入口HTML失败: {e}")
    sys.exit(1)

# 步骤2: 解析域名基础
print("\n=== 步骤2: 解析域名基础 ===")
domain_match = re.search(r'getRandomWord\(\)\s*\+\s*"\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', entry_html)
if not domain_match:
    print("未匹配到getRandomWord域名模式")
    # 尝试其他模式
    alt_match = re.search(r'getRandomWord\(\)\s*\+\s*\'\.([a-zA-Z0-9.-]+)', entry_html)
    if alt_match:
        print(f"匹配到单引号模式，域名基础: {alt_match.group(1)}")
    else:
        # 输出含getRandomWord的上下文（只输出技术结构）
        for m in re.finditer(r'.{0,80}getRandomWord.{0,80}', entry_html):
            print(f"getRandomWord上下文: {m.group(0)[:160]}")
        sys.exit(1)
else:
    domain_base = domain_match.group(1)
    print(f"域名基础: {domain_base}")

# 步骤3: 生成今日候选域名（复现JS算法）
import math
import datetime

def seeded_random(seed):
    x = math.sin(seed) * 10000
    return x - math.floor(x)

d = datetime.datetime.now()
seed = d.year * 10000 + d.month * 100 + d.day
letters = 'abcdefgijlmnoqrstwz'

def generate_word(s, length):
    word = ''
    for i in range(length):
        idx = int(seeded_random(s + i) * len(letters))
        word += letters[idx]
    return word

words = []
i = 0
while len(words) < 2:
    length = 3 + int(seeded_random(seed + i) * 3)
    w = generate_word(seed + i * 10, length)
    if w not in words:
        words.append(w)
    i += 1

print(f"\n=== 步骤3: 今日候选域名词 ===")
print(f"候选词: {words}")
print(f"候选域名: {[w + '.' + domain_base for w in words]}")

# 步骤4: 测试候选域名可用性
print(f"\n=== 步骤4: 测试候选域名可用性 ===")
real_domain = None
for w in words:
    candidate = w + '.' + domain_base
    test_url = f'https://{candidate}/vodtype/1/'
    try:
        req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            test_html = resp.read().decode('utf-8', errors='ignore')
        if len(test_html) > 1000:
            print(f"候选域名可用: 域名#{words.index(w)+1} (HTML长度={len(test_html)})")
            real_domain = candidate
            break
        else:
            print(f"候选域名HTML过短: 域名#{words.index(w)+1} (HTML长度={len(test_html)})")
    except Exception as e:
        print(f"候选域名不可用: 域名#{words.index(w)+1} (错误: {type(e).__name__})")

if not real_domain:
    real_domain = words[0] + '.' + domain_base
    print(f"使用第一个候选域名作为fallback")

# 步骤5: 获取详情页HTML，提取视频ID
print(f"\n=== 步骤5: 获取详情页HTML ===")
detail_url = f'https://{real_domain}/voddetail/1777913/'
try:
    req = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        detail_html = resp.read().decode('utf-8', errors='ignore')
    print(f"详情页HTML长度: {len(detail_html)}")
    # 检查详情页是否含player_data
    if 'player_data' in detail_html:
        print("详情页含player_data（直接在详情页）")
    else:
        print("详情页不含player_data（需要请求播放页）")
except Exception as e:
    print(f"获取详情页失败: {e}")

# 步骤6: 获取播放页HTML，分析player_data格式
print(f"\n=== 步骤6: 获取播放页HTML ===")
play_url = f'https://{real_domain}/vodplay/1777913-1-1/'
try:
    req = urllib.request.Request(play_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        play_html = resp.read().decode('utf-8', errors='ignore')
    print(f"播放页HTML长度: {len(play_html)}")
except Exception as e:
    print(f"获取播放页失败: {e}")
    sys.exit(1)

# 步骤7: 分析player_data格式
print(f"\n=== 步骤7: 分析player_data格式 ===")
# 尝试多种正则模式
patterns = [
    (r'var\s+player_data\s*=\s*(\{[\s\S]*?\})\s*;</script>', 'var player_data = {...};</script>'),
    (r'var\s+player_data\s*=\s*(\{[\s\S]*?\})\s*;', 'var player_data = {...};'),
    (r'player_data\s*=\s*(\{[\s\S]*?\})\s*</script>', 'player_data = {...}</script>'),
    (r'player_data\s*=\s*(\{[^}]+\})', 'player_data = {...}'),
    (r'player_aaaa\s*=\s*(\{[\s\S]*?\})', 'player_aaaa = {...}（maccms常见变量名）'),
]

for pattern, desc in patterns:
    m = re.search(pattern, play_html)
    if m:
        print(f"\n✅ 匹配成功! 模式: {desc}")
        raw = m.group(1)
        print(f"player_data原始长度: {len(raw)}")
        print(f"player_data前200字符: {raw[:200]}")
        # 尝试JSON解析
        try:
            import json
            pd = json.loads(raw)
            print(f"\nJSON解析成功! 字段列表:")
            for k, v in pd.items():
                v_str = str(v)
                if len(v_str) > 100:
                    v_str = v_str[:100] + '...'
                print(f"  {k}: {v_str}")
            # 检查url字段
            if 'url' in pd:
                url_val = pd['url']
                if '.m3u8' in url_val:
                    print(f"\n✅ url字段含m3u8: 长度={len(url_val)}")
                else:
                    print(f"\n⚠️ url字段不含m3u8: {url_val[:50]}")
            else:
                print(f"\n❌ 无url字段")
                # 检查其他可能含视频地址的字段
                for k in ['url', 'play_url', 'video_url', 'src', 'source']:
                    if k in pd:
                        print(f"  发现替代字段: {k}={str(pd[k])[:50]}")
        except Exception as e:
            print(f"JSON解析失败: {e}")
            print(f"原始内容前500字符: {raw[:500]}")
        break
    else:
        print(f"❌ 模式不匹配: {desc}")

# 如果所有模式都不匹配，输出含player的上下文
if not any(re.search(p[0], play_html) for p in patterns):
    print(f"\n=== 所有模式都不匹配，搜索含player的上下文 ===")
    for m in re.finditer(r'.{0,100}player.{0,100}', play_html, re.IGNORECASE):
        ctx_text = m.group(0)
        if len(ctx_text) > 200:
            ctx_text = ctx_text[:200] + '...'
        print(f"player上下文: {ctx_text}")
        print('---')
