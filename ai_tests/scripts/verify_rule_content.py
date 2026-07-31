#!/usr/bin/env python3
"""
验证站点D的ruleContent JS逻辑
模拟JS执行：详情页URL → 提取videoId → 构造播放页URL → 获取HTML → 提取player_data JSON → 返回url字段
"""
import re
import json
import urllib.request
import ssl

# 关闭SSL验证（模拟器环境）
ssl._create_default_https_context = ssl._create_unverified_context

# 已知实际域名（从logcat获知）
REAL_DOMAIN = "alj.18jtoday7m6.buzz"
VIDEO_ID = "1777913"

def java_ajax(url):
    """模拟java.ajax"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [java.ajax ERROR] {type(e).__name__}: {e}")
        return ""

def extract_player_data(play_html):
    """模拟ruleContent JS的平衡括号算法"""
    start_idx = play_html.find("var player_data")
    if start_idx < 0:
        return None, f"ERR:no_player_data,htmlLen={len(play_html)}"

    json_start = play_html.find("{", start_idx)
    if json_start < 0:
        return None, "ERR:no_jsonStart"

    depth = 0
    end_idx = -1
    for i in range(json_start, len(play_html)):
        c = play_html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if end_idx < 0:
        return None, f"ERR:no_endIdx,depth={depth}"

    json_str = play_html[json_start:end_idx+1]
    return json_str, None

def main():
    print("=" * 70)
    print("站点D ruleContent JS 逻辑验证")
    print("=" * 70)

    # Step 1: 模拟baseUrl（详情页URL）
    detail_url = f"https://{REAL_DOMAIN}/index.php/voddetail/{VIDEO_ID}/"
    print(f"\n[Step 1] baseUrl (详情页URL): len={len(detail_url)}")
    print(f"  路径模式: /index.php/voddetail/{{id}}/")

    # Step 2: 提取baseUrlStr
    base_url_match = re.match(r"^(https?://[^/]+)", detail_url)
    if not base_url_match:
        print("[Step 2] ERR:no_baseUrlMatch")
        return
    base_url_str = base_url_match.group(1)
    print(f"\n[Step 2] baseUrlStr: {base_url_str}")

    # Step 3: 提取videoId
    id_match = re.search(r"/voddetail/(\d+)/", detail_url)
    if not id_match:
        print(f"[Step 3] ERR:no_idMatch:{detail_url}")
        return
    video_id = id_match.group(1)
    print(f"\n[Step 3] videoId: {video_id}")

    # Step 4: 构造播放页URL
    play_url = f"{base_url_str}/vodplay/{video_id}-1-1/"
    print(f"\n[Step 4] playUrl: {play_url}")

    # Step 5: 获取播放页HTML
    play_html = java_ajax(play_url)
    if not play_html:
        print(f"[Step 5] ERR:no_playHtml:{play_url}")
        return
    print(f"\n[Step 5] playHtml.length = {len(play_html)}")

    # Step 6: 提取player_data
    json_str, err = extract_player_data(play_html)
    if err:
        print(f"\n[Step 6] {err}")
        return
    print(f"\n[Step 6] player_data JSON 提取成功: len={len(json_str)}")

    # Step 7: JSON.parse
    try:
        pd = json.loads(json_str)
        print(f"\n[Step 7] JSON.parse 成功")
        print(f"  字段列表: {list(pd.keys())}")
        print(f"  字段数量: {len(pd)}")

        # 输出各字段的值（脱敏）
        for k, v in pd.items():
            if isinstance(v, str) and len(v) > 100:
                print(f"  {k}: <str len={len(v)}> {v[:60]}...")
            else:
                print(f"  {k}: {repr(v)[:100]}")
    except Exception as e:
        print(f"\n[Step 7] ERR:json_parse,{e}")
        print(f"  JSON前100字符: {json_str[:100]}")
        return

    # Step 8: 检查url字段
    if "url" in pd:
        m3u8_url = pd["url"]
        print(f"\n[Step 8] ✅ 成功提取 m3u8 URL")
        print(f"  url长度: {len(m3u8_url)}")
        print(f"  url前80字符: {m3u8_url[:80]}")
        # 判断是否以http开头
        if m3u8_url.startswith("http://") or m3u8_url.startswith("https://"):
            print(f"  ✅ 以http(s)://开头, isValidVideoContentUrl=True")
        else:
            print(f"  ❌ 不以http(s)://开头, isValidVideoContentUrl=False")
            print(f"  这就是21字符返回值被判定为非视频URL的原因！")
    else:
        err_msg = f"ERR:no_url,fields={','.join(pd.keys())}"
        print(f"\n[Step 8] ❌ {err_msg}")
        print(f"  错误信息长度: {len(err_msg)}")
        print(f"  这就是21字符返回值的内容！")

    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
