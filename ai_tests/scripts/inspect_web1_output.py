"""
检查输出文件中的几个典型记录，分析为何jsRule未生成。
同时查看popup_selectors检测结果。
不输出业务字段原文。
"""
import json
from pathlib import Path

INPUT = Path("output/rss/subagent_web1_analysis.json")

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print("jsRule 未生成原因分析")
print("=" * 70)

# 统计每个源的page_signals详细
for r in data["results"]:
    sig = r.get("page_signals", {}) or {}
    popup_sel = sig.get("popup_selectors", [])
    popup_cnt = sig.get("popup_count", 0)
    cf = sig.get("cloudflare", False)
    sf = sig.get("search_form_count", 0)
    print(f"idx={r['idx']:3d} acc={r['source_url_accessible']} popup_cnt={popup_cnt} popup_sel={popup_sel} cf={cf} sf={sf}")

# 看几个有accessible=True但popup=0的源，检查页面是否有其他弹框迹象
print("\n--- 抽样查看idx=0,9,30的完整page_signals ---")
for target_idx in [0, 9, 30, 40, 45]:
    for r in data["results"]:
        if r["idx"] == target_idx:
            sig = r.get("page_signals", {}) or {}
            print(f"\nidx={target_idx}:")
            for k, v in sig.items():
                # 截断长字符串
                if isinstance(v, str) and len(v) > 100:
                    print(f"  {k}: {v[:100]}...")
                elif isinstance(v, list):
                    print(f"  {k}: {v[:5]}")
                else:
                    print(f"  {k}: {v}")
            break

# 检查有多少源生成了searchUrl，看看格式是否正确
print("\n--- 抽样查看searchUrl生成结果 ---")
for target_idx in [9, 10, 11, 30, 36, 40, 45]:
    for r in data["results"]:
        if r["idx"] == target_idx:
            su = r["fields"].get("searchUrl", "")
            # 路径模式化
            print(f"idx={target_idx}: searchUrl={su[:150]}")
            break
