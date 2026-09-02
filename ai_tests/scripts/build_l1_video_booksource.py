# -*- coding: utf-8 -*-
"""video-booksource-multiroute 4.7 硬用例：从 @js 版书源派生 L1 零 JS 对照版
L1 写法：chapterList=$.chapters[*] / chapterName=$.title / chapterUrl=$.url / isVolume=$.isVolume
ruleContent 留空（既有机制：正文规则空 -> chapter.url 直链直出）
"""
import json

SRC = r"F:\myself\github\WeAgentChat\temp\legado\docs\analysis\archive-video-booksource.json"
OUT = r"F:\myself\github\WeAgentChat\temp\legado\output\ai_source\video_booksource_l1_nojs.json"

body = open(SRC, encoding="utf-8").read()
s = json.loads(body)[0] if body.lstrip().startswith("[") else json.loads(body)

l1 = json.loads(json.dumps(s))
toc = l1.setdefault("ruleToc", {})
# L1 四条 JSONPath（消费 App 侧 MacCmsNormalizer 注入的 chapters 扁平卷章结构）
toc["chapterList"] = "$.chapters[*]"
toc["chapterName"] = "$.title"
toc["chapterUrl"] = "$.url"
toc["isVolume"] = "$.isVolume"
# 正文留空 -> chapter.url 直链直出；播放页 URL 由三层嗅探兜底
content = l1.setdefault("ruleContent", {})
content["content"] = ""

with open(OUT, "w", encoding="utf-8") as f:
    json.dump([l1], f, ensure_ascii=False, indent=2)

print("L1 booksource written")
print("bookSourceUrl=", l1.get("bookSourceUrl", "")[:30])
print("tocUrl=", l1.get("searchUrl", "")[:40])
print("bookSourceType=", l1.get("bookSourceType"))
