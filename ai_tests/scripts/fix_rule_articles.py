#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改订阅源JSON的ruleArticles和ruleLink
- ruleArticles: $.list -> @js动态解析(JSON用JSONPath, HTML用Jsoup提取.video-card)
- ruleLink: result.id -> JSON.parse(result).id (因为元素现在是JSON字符串)
"""
import json
import io

JSON_PATH = r"f:\myself\github\WeAgentChat\temp\legado\output\ai_source\rss\rss_avav2_subsites_20260729.json"

# 新的ruleArticles规则(@js动态解析JSON/HTML)
NEW_RULE_ARTICLES = (
    "@js:(function(){"
    "var c=result;"
    "try{var j=JSON.parse(c);if(j&&j.list)return j.list.map(function(item){return JSON.stringify(item);});}catch(e){}"
    "var d=org.jsoup.Jsoup.parse(c);"
    "var cards=d.select('.video-card');"
    "var list=[];"
    "for(var i=0;i<cards.size();i++){"
    "var card=cards.get(i);"
    "var link=card.attr('href');"
    "var m=link.match(/k=(\\d+)/);"
    "var id=m?m[1]:'';"
    "var img=card.select('.thumb-img').attr('src');"
    "var title=card.select('.video-title').text();"
    "list.push(JSON.stringify({id:id,title:title,img:img}));"
    "}"
    "return list;"
    "})()"
)

# 新的ruleLink规则(先JSON.parse(result)再访问id)
NEW_RULE_LINK = (
    "@js:var r=JSON.parse(result);"
    "var u=baseUrl.split('//')[1].split('/')[0];"
    "'https://'+u+'/?m=play&u=sh&k='+r.id+'&mod=jump'"
)

# 读取JSON文件(用utf-8无BOM)
with open(JSON_PATH, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

print(f"[SOURCE COUNT] {len(data)}")
modified = 0
for i, source in enumerate(data):
    # 强制设置新值(不判断旧值)
    source["ruleArticles"] = NEW_RULE_ARTICLES
    source["ruleLink"] = NEW_RULE_LINK
    print(f"[{i}] ruleArticles + ruleLink 已设置")
    modified += 1

print(f"[MODIFIED] {modified} sources")

# 写回JSON文件(无BOM, ensure_ascii=False保持中文可读)
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"[SAVED] {JSON_PATH}")
print(f"[DONE] 修改完成")
