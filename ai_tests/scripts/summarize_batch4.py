"""读取batch4输出文件，生成技术摘要（脱敏）"""
import json
from pathlib import Path

OUT = Path(r"f:\myself\github\WeAgentChat\temp\legado\output\rss\subagent_web4_analysis.json")

with open(OUT, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 60)
print("Batch4 分析结果摘要")
print("=" * 60)
print(f"agent: {data['agent']}")
print(f"batch_range: {data['batch_range']}")
print(f"total_analyzed: {data['total_analyzed']}")

print(f"\n[参考源]")
for r in data["ref_sources"]:
    print(f"  idx={r['idx']}: 字段数={r['field_count']}, enableJs={r['enableJs']}, has_login={r['has_login']}")

print(f"\n[静态字段分布]")
for f, c in sorted(data["field_distribution"].items(), key=lambda x: -x[1]):
    print(f"  {f}: {c}/{data['total_analyzed']}")

print(f"\n[Playwright状态分布]")
for s, c in data["status_distribution"].items():
    print(f"  {s}: {c}")

print(f"\n[摘要]")
for k, v in data["summary"].items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")

# 详细结果统计
print(f"\n[详细结果技术指标统计]")
results = data["results"]
analyzed_status = [r for r in results if r.get("dynamic", {}).get("status") == "analyzed"]
print(f"  动态分析成功: {len(analyzed_status)}/{len(results)}")

# 统计技术指标
login_form_count = 0
captcha_count = 0
rss_link_count = 0
feed_detected_count = 0
iframe_count = 0
total_link_count = 0
total_img_count = 0
total_article_count = 0
status_code_dist = {}

for r in analyzed_status:
    tech = r["dynamic"].get("tech_indicators", {})
    if tech.get("has_login_form"):
        login_form_count += 1
    if tech.get("has_captcha"):
        captcha_count += 1
    if tech.get("rss_link"):
        rss_link_count += 1
    if tech.get("detected_feeds"):
        feed_detected_count += 1
    if tech.get("has_iframe", 0) > 0:
        iframe_count += 1
    total_link_count += tech.get("link_count", 0)
    total_img_count += tech.get("img_count", 0)
    total_article_count += tech.get("article_count", 0)
    sc = tech.get("status_code")
    if sc:
        status_code_dist[sc] = status_code_dist.get(sc, 0) + 1

n = len(analyzed_status)
print(f"  含登录表单: {login_form_count}/{n}")
print(f"  含验证码: {captcha_count}/{n}")
print(f"  含RSS link标签: {rss_link_count}/{n}")
print(f"  探测到RSS路径: {feed_detected_count}/{n}")
print(f"  含iframe: {iframe_count}/{n}")
print(f"  平均链接数: {total_link_count/max(1,n):.1f}")
print(f"  平均图片数: {total_img_count/max(1,n):.1f}")
print(f"  平均article数: {total_article_count/max(1,n):.1f}")
print(f"  状态码分布: {status_code_dist}")

# 字段补全建议
print(f"\n[字段补全建议]")
print(f"  searchUrl: 0/{n} - 需要为{n}个源全部补全")
print(f"  jsRule: 0/{n} - 需要为{n}个源全部补全")
print(f"  sourceIcon: {data['field_distribution'].get('sourceIcon',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('sourceIcon',0)}个")
print(f"  ruleArticles: {data['field_distribution'].get('ruleArticles',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleArticles',0)}个")
print(f"  ruleNextPage: {data['field_distribution'].get('ruleNextPage',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleNextPage',0)}个")
print(f"  sortUrl: {data['field_distribution'].get('sortUrl',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('sortUrl',0)}个")
print(f"  ruleTitle: {data['field_distribution'].get('ruleTitle',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleTitle',0)}个")
print(f"  ruleImage: {data['field_distribution'].get('ruleImage',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleImage',0)}个")
print(f"  rulePubDate: {data['field_distribution'].get('rulePubDate',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('rulePubDate',0)}个")
print(f"  ruleLink: {data['field_distribution'].get('ruleLink',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleLink',0)}个")
print(f"  ruleContent: {data['field_distribution'].get('ruleContent',0)}/{data['total_analyzed']} - 缺失{n - data['field_distribution'].get('ruleContent',0)}个")
