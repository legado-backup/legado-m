# RSS 订阅源基础处理

> 标准 RSS 2.0、非标准网页→RSS 规则解析、单URL源、RSS 搜索功能、视频订阅源的完整方案。

## 7.1 标准 RSS 2.0

```json
{
  "sourceUrl": "https://example.com/feed.xml",
  "sourceName": "示例RSS",
  "sourceIcon": "https://example.com/favicon.ico",
  "type": 0
}
```

## 7.2 非标准网页→RSS（规则解析）

```json
{
  "sourceUrl": "https://example.com/news",
  "ruleArticles": "div.article-item",
  "ruleTitle": "h2@text",
  "ruleLink": "a@href",
  "rulePubDate": "span.date@text",
  "ruleContent": "div.content@html",
  "ruleImage": "img@src",
  "ruleNextPage": "a.next@href"
}
```

## 7.3 单URL源（`singleUrl: true`）

```json
{
  "singleUrl": true
}
```
勾选后，`sourceUrl` 同时作为源URL和内容获取URL，适用于无需分页的简单源。

## 7.4 RSS 订阅源搜索功能

> ⚠️ **RssSource 支持搜索！** 通过 `searchUrl` 字段配置，搜索关键字通过 `{{key}}` 模板变量传递。

```json
{
  "sourceUrl": "https://example.com",
  "sourceName": "示例视频源",
  "type": 2,
  "sortUrl": "热播::/toplist.html\n最新::/newlist.html",
  "searchUrl": "/search?q={{key}}&page={{page}}",
  "ruleArticles": "ul.list > li",
  "ruleTitle": "h3@text",
  "ruleLink": "a@href",
  "ruleImage": "img@src",
  "ruleContent": ".video-url@data-src"
}
```

**搜索触发条件**：`searchUrl` 不为空且 `isNotBlank()` 时，RSS 分类页面自动显示搜索按钮。

**搜索 URL 支持与 BookSource 相同的语法**：
- URL 模板：`{{key}}`、`{{page}}`、`{{host}}`
- JS 规则：`@js:...`
- UrlOption 参数：`,{"method":"POST","body":"..."}`
- 加密搜索：与 BookSource 的 searchUrl 完全一致

## 7.5 视频订阅源（type=2）

```json
{
  "sourceUrl": "https://video.example.com",
  "sourceName": "示例视频站",
  "sourceGroup": "视频",
  "type": 2,
  "sortUrl": "热播::/top\n最新::/new",
  "searchUrl": "/search?q={{key}}",
  "ruleArticles": "ul.ucontent > li",
  "ruleTitle": "div.ctitle > p@text",
  "ruleImage": "input.h_d_pic@value",
  "ruleLink": "a@href",
  "rulePubDate": "span.vodtime@text",
  "ruleContent": ".playsource a@playdata"
}
```

**type 字段说明**：
- `0` — 网页（默认）
- `1` — 图片
- `2` — 视频

**⚠️ 实战教训**：当需要自定义播放器界面（如 HLS.js 播放器）时，必须用 `type: 0`，不能用 `type: 2`。详见 `../troubleshooting/source-type-traps.md` §4.2.1。

## 7.6 搜索关键词作为分类（实战技巧）

> searchUrl 可以用于 sortUrl 分类，让用户直接进入感兴趣的内容。

**示例**：
```json
{
  "sortUrl": "大神::/search?wd=大神\n学生::/search?wd=学生\n91::/search?wd=91\n偷情::/search?wd=偷情\n推特::/search?wd=推特\n少女::/search?wd=少女"
}
```

**好处**：
- 用户可以直接进入感兴趣的内容分类
- 不需要手动搜索
- 分类数量可以很丰富（20+）
- 适用于有搜索功能的网站

**注意**：
- 搜索关键词分类的 URL 格式与 searchUrl 相同
- 关键词需要 URL 编码（中文关键词）
- 可以与普通分类混合使用
