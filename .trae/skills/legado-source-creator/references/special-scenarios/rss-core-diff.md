# 订阅源核心差异（vs 书源）

> 本文档从 SKILL.md 拆分，包含 RssSource 与 BookSource 的核心差异要点。
> 完整订阅源规范详见：[rss-basic.md](./rss-basic.md) + [rss-advanced.md](./rss-advanced.md) + [source-analysis/rss-source-entity.md](../source-analysis/rss-source-entity.md)

---

## 核心差异速览

1. **字段扁平**：ruleArticles/ruleTitle/ruleLink/ruleImage/ruleDescription/rulePubDate/ruleContent 都是独立String?字段
2. **搜索复用列表规则**：searchUrl + 同一套ruleArticles/ruleTitle/ruleLink
3. **ruleContent也是扁平String?**：不是`{"content":"..."}`，直接写CSS/JS规则
   - 示例：`ruleContent: "class.article-content@html"` 或 `ruleContent: "<js>...</js>"`
4. **视频播放器**：用`templates/auto-video-player.html`模板，type=0（WebView渲染）
   - 用法：读取模板文件内容，替换 `${videoUrl}` 占位符为实际视频URL的CSS/JS规则，将结果作为 ruleContent 的值

---

## 字段对比

| 维度 | BookSource | RssSource |
|------|-----------|-----------|
| 规则结构 | 5组嵌套（Search/BookInfo/Toc/Content/Explore） | **扁平独立字段**（ruleArticles/ruleTitle/ruleLink等） |
| 典型网站 | 笔趣阁、起点 | 视频站、图集站、新闻站 |
| type 含义 | bookSourceType 决定内容类型（0小说/1音频/2漫画/3文件） | type 决定渲染方式（0=拼HTML显示, 1=图片列表, 2=视频直链播放） |
| 搜索 | searchUrl + ruleSearch | searchUrl + ruleArticles/ruleTitle/ruleLink（复用列表规则） |
| 正文 | ruleContent（嵌套对象） | ruleContent（扁平String?） |

---

## 构建顺序

- **BookSource**：searchUrl → ruleSearch → ruleBookInfo → ruleToc → ruleContent
- **RssSource**：sourceUrl → ruleArticles → ruleTitle/ruleLink/ruleImage → ruleContent

---

## 相关陷阱

| # | 陷阱 | ✅ 正确做法 |
|---|------|-----------|
| 14 | RssSource字段扁平 | ruleArticles/ruleTitle等是独立String?，非嵌套对象 |
| 15 | type选择 | 拼HTML→type:0；纯视频URL→type:2 |
| 17 | enableJs≠webView | `{"webView":true}`才触发WebView加载 |
| 74 | loginCheckJs中result是StrResponse | RssSource的loginCheckJs在AnalyzeUrl.evalJS中执行，`result`绑定的是StrResponse对象（非HTML字符串）。必须用`result.body+''`获取HTML内容再检测关键词 |
