# 完整书源 JSON 示例

> ⚠️ **所有输出必须是 `[...]` 数组格式**，Legado 导入时始终期望数组，单个对象 `{...}` 会导致导入失败。

## 示例一：标准小说网站（CSS 选择器）

```json
[
  {
    "bookSourceUrl": "https://www.biquge.example.com",
    "bookSourceName": "笔趣阁示例(中文)",
    "bookSourceGroup": "小说",
    "bookSourceType": 0,
    "bookSourceComment": "示例书源，CSS选择器实现",
    "enabled": true,
    "enabledExplore": true,
    "enabledCookieJar": false,
    "header": "{\"User-Agent\":\"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36\"}",
    "concurrentRate": "",
    "loginUrl": "",
    "ruleSearch": {
      "searchUrl": "/search.php?keyword={{key}},{\"method\":\"POST\",\"body\":\"searchkey={{key}}\",\"charset\":\"gbk\"}",
      "bookList": "div.result-list > div.result-item",
      "name": "div.result-game-item-detail > h3 > a@text",
      "author": "div.result-game-item-detail > p:nth-child(2)@text##作者：(.*)",
      "kind": "div.result-game-item-detail > p:nth-child(3)@text##分类：(.*)",
      "wordCount": "",
      "lastChapter": "div.result-game-item-detail > p:nth-child(4)@text##最新：(.*)",
      "intro": "p.result-game-item-desc@text",
      "coverUrl": "img.result-game-item-pic@src",
      "bookUrl": "div.result-game-item-detail > h3 > a@href"
    },
    "ruleExplore": {
      "exploreUrl": "/sort/{{type}}/{{page}}.html",
      "bookList": "div.l > div.item",
      "name": "h2 > a@text",
      "author": "p.bt > span:nth-child(1)@text",
      "kind": "",
      "wordCount": "",
      "lastChapter": "p.bt > a@text",
      "intro": "",
      "coverUrl": "a > img@src",
      "bookUrl": "h2 > a@href"
    },
    "ruleBookInfo": {
      "init": "",
      "name": "h1@text",
      "author": "div.sinfo > p:nth-child(2)@text##作.*者：(.*)",
      "kind": "div.sinfo > p:nth-child(3)@text",
      "wordCount": "",
      "lastChapter": "div.sinfo > p:nth-child(5) > a@text",
      "intro": "div.intro@html",
      "coverUrl": "div.img > img@src",
      "tocUrl": "a.mulu@href||#list"
    },
    "ruleToc": {
      "chapterList": "div#list dd",
      "chapterName": "a@text",
      "chapterUrl": "a@href",
      "isVolume": "",
      "isVip": "",
      "isPay": "",
      "updateTime": "",
      "nextTocUrl": ""
    },
    "ruleContent": {
      "content": "div#content@html",
      "nextContentUrl": "a.next:contains(下一章)@href",
      "webJs": "",
      "sourceRegex": "",
      "replaceRegex": "##\\s*本书首发.*|##\\s*请记住本站.*|##\\s*一秒记住.*",
      "imageStyle": "FULL",
      "titleRule": "",
      "customProcessor": ""
    }
  }
]
```

---

## 示例二：JSON API 网站（JSONPath）

```json
[
  {
    "bookSourceUrl": "https://api.novel.example.com",
    "bookSourceName": "JSON API示例(中文)",
    "bookSourceGroup": "API",
    "bookSourceType": 0,
    "enabled": true,
    "enabledExplore": false,
    "ruleSearch": {
      "searchUrl": "/api/v1/search?keyword={{key}}",
      "bookList": "$.data[*]",
      "name": "$.title",
      "author": "$.author",
      "kind": "$.category",
      "wordCount": "$.wordCount",
      "lastChapter": "$.lastChapterTitle",
      "intro": "$.description",
      "coverUrl": "$.cover",
      "bookUrl": "$.bookId"
    },
    "ruleBookInfo": {
      "init": "",
      "name": "$.data.title",
      "author": "$.data.author",
      "kind": "$.data.category&&$.data.status",
      "wordCount": "$.data.wordCount",
      "lastChapter": "$.data.lastChapterTitle",
      "intro": "$.data.description",
      "coverUrl": "$.data.cover",
      "tocUrl": "$.data.bookId"
    },
    "ruleToc": {
      "chapterList": "$.data.chapters[*]",
      "chapterName": "$.title",
      "chapterUrl": "$.chapterId",
      "isVolume": "",
      "isVip": "$.isVip",
      "isPay": "",
      "updateTime": "$.updateTime",
      "nextTocUrl": ""
    },
    "ruleContent": {
      "content": "$.data.content",
      "nextContentUrl": "",
      "webJs": "",
      "replaceRegex": "",
      "imageStyle": "FULL"
    }
  }
]
```

---

## 示例三：带登录的书源（JS + 加密）

```json
[
  {
    "bookSourceUrl": "https://www.vip-novel.example.com",
    "bookSourceName": "会员小说站(中文)",
    "bookSourceGroup": "VIP",
    "bookSourceType": 0,
    "enabled": true,
    "enabledCookieJar": true,
    "loginUrl": "https://www.vip-novel.example.com/login.php",
    "loginUi": "[{\"name\":\"username\",\"type\":\"text\"},{\"name\":\"password\",\"type\":\"password\"}]",
    "loginCheckJs": "<js>\nvar loginUrl = 'https://www.vip-novel.example.com/login.php';\nvar username = java.get('username');\nvar password = java.get('password');\nvar md5pass = java.md5Encode(password + 'salt_key_2024');\nvar body = 'action=login&username=' + java.encodeURI(username) + '&password=' + md5pass;\nvar result = ajax(loginUrl, {method: 'POST', body: body});\nif (result.includes('登录成功')) {\n    java.setCookie(source.getKey(), result.match(/Set-Cookie: ([^;]+)/)[1]);\n    'ok';\n} else {\n    'no';\n}\n</js>",
    "ruleSearch": {
      "searchUrl": "/search.html?keyword={{key}}",
      "bookList": "ul.list > li",
      "name": "a@text",
      "author": "span.author@text",
      "kind": "",
      "wordCount": "",
      "lastChapter": "span.update@text",
      "intro": "",
      "coverUrl": "img@src",
      "bookUrl": "a@href"
    },
    "ruleBookInfo": {
      "init": "java.setCookie(source.getKey(), java.getCache('login_cookie'));",
      "name": "h1@text",
      "author": "p.author@text",
      "kind": "span.tag@text",
      "wordCount": "span.count@text",
      "lastChapter": "p.update@text",
      "intro": "div.desc@html",
      "coverUrl": "img.cover@src",
      "tocUrl": "a#read@href"
    },
    "ruleToc": {
      "chapterList": "ul.chapterlist > li",
      "chapterName": "a@text",
      "chapterUrl": "a@href",
      "isVolume": "",
      "isVip": "span.lock@text",
      "isPay": "span.lock@text",
      "updateTime": "",
      "nextTocUrl": ""
    },
    "ruleContent": {
      "content": "<js>\nvar html = ajax(baseUrl);\nif (html.includes('请登录')) {\n    var loginCookie = java.getCache('login_cookie');\n    java.setCookie(source.getKey(), loginCookie);\n    html = ajax(baseUrl);\n}\nvar doc = org.jsoup.Jsoup.parse(html);\nresult = doc.select('div#content').html();\n</js>",
      "nextContentUrl": "a.next@href",
      "webJs": "",
      "sourceRegex": "",
      "replaceRegex": "##本章未完.*|##\\s*手机用户请浏览.*",
      "imageStyle": "FULL"
    }
  }
]
```

---

## 示例四：漫画/图片站（bookSourceType=2）

```json
[
  {
    "bookSourceUrl": "https://www.comic.example.com",
    "bookSourceName": "示例漫画(中文)",
    "bookSourceGroup": "漫画",
    "bookSourceType": 2,
    "enabled": true,
    "coverDecodeJs": "",
    "ruleSearch": {
      "searchUrl": "/search?q={{key}}",
      "bookList": "div.comic-item",
      "name": "h3@text",
      "author": "p.author@text",
      "kind": "span.type@text",
      "wordCount": "",
      "lastChapter": "p.new@text",
      "intro": "p.desc@text",
      "coverUrl": "img@src",
      "bookUrl": "a@href"
    },
    "ruleBookInfo": {
      "init": "",
      "name": "h1@text",
      "author": "p.author@text",
      "kind": "span.tags@text",
      "wordCount": "",
      "lastChapter": "p.latest@text",
      "intro": "div.desc@html",
      "coverUrl": "img.cover@src",
      "tocUrl": "a.chapter@href"
    },
    "ruleToc": {
      "chapterList": "ul.chapter-list > li",
      "chapterName": "a@text",
      "chapterUrl": "a@href",
      "isVolume": "",
      "isVip": "",
      "isPay": "",
      "updateTime": "span.time@text",
      "nextTocUrl": ""
    },
    "ruleContent": {
      "content": "img.comic-page@src",
      "nextContentUrl": "a.next@href",
      "webJs": "",
      "sourceRegex": "",
      "replaceRegex": "",
      "imageStyle": "FULL"
    }
  }
]
```

---

## 示例五：RSS 订阅源

```json
[
  {
    "sourceUrl": "https://www.example-blog.com/feed.xml",
    "sourceName": "示例博客",
    "sourceIcon": "https://www.example-blog.com/favicon.ico",
    "sourceGroup": "技术博客",
    "enabled": true,
    "singleUrl": false,
    "type": 0
  }
]
```

### RSS 规则解析型订阅源

```json
[
  {
    "sourceUrl": "https://www.example-news.com/latest",
    "sourceName": "示例新闻网",
    "sourceIcon": "https://www.example-news.com/favicon.ico",
    "sourceGroup": "新闻",
    "enabled": true,
    "singleUrl": false,
    "type": 0,
    "ruleArticles": "div.news-item",
    "ruleTitle": "h2@text",
    "ruleLink": "h2 > a@href",
    "rulePubDate": "span.date@text",
    "ruleAuthor": "span.author@text",
    "ruleContent": "div.content@html##<script[\\s\\S]*?</script>",
    "ruleImage": "img@src",
    "ruleNextPage": "a.next-page@href"
  }
]
```

---

## 示例六：视频网站（bookSourceType=3 + AES加密搜索）

> **实战案例**：搜索关键词经 AES-128-CBC + ZeroPadding 加密，视频地址在自定义属性 `playdata` 中

```json
[
  {
    "bookSourceUrl": "https://example-video.com",
    "bookSourceName": "示例视频站(中文)",
    "bookSourceGroup": "视频",
    "bookSourceType": 3,
    "bookSourceComment": "视频书源|搜索关键词AES-128-CBC加密|正文直接提取m3u8播放地址|ZeroPadding",
    "enabled": true,
    "enabledExplore": true,
    "enabledCookieJar": false,
    "header": "{\"User-Agent\":\"Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36\"}",
    "concurrentRate": "",
    "loginUrl": "",
    "loginUi": "",
    "loginCheckJs": "",
    "ruleSearch": {
      "searchUrl": "@js:var base64=java.createSymmetricCrypto('AES/CBC/NoPadding','your-aes-key-16ch','your-aes-iv-16ch!!').encryptBase64(key);var encoded=encodeURIComponent(base64);var url='/search-0-1-'+encoded+'.html';if(page>1){url='/search-0-1-'+encoded+'-'+page+'.html'}url;",
      "bookList": "ul.ucontent > li",
      "name": "div.ctitle > p@text",
      "author": "",
      "kind": "",
      "wordCount": "span.vodtime@text",
      "lastChapter": "",
      "intro": "",
      "coverUrl": "input.h_d_pic@value",
      "bookUrl": "a@href"
    },
    "ruleExplore": {
      "exploreUrl": "今日热播::/toplist.html\n今日更新::/newlist.html",
      "bookList": "ul.ucontent > li",
      "name": "div.ctitle > p@text",
      "author": "",
      "kind": "",
      "wordCount": "span.vodtime@text",
      "lastChapter": "",
      "intro": "",
      "coverUrl": "input.h_d_pic@value",
      "bookUrl": "a@href"
    },
    "ruleBookInfo": {
      "init": "",
      "name": ".single-strong@text",
      "author": "",
      "kind": "",
      "wordCount": "",
      "lastChapter": "",
      "intro": "",
      "coverUrl": "#my-video@poster",
      "tocUrl": "",
      "canReName": ""
    },
    "ruleToc": {
      "chapterList": "-",
      "chapterName": ".single-strong@text",
      "chapterUrl": ""
    },
    "ruleContent": {
      "content": ".playsource a@playdata",
      "nextContentUrl": "",
      "webJs": "",
      "sourceRegex": "",
      "replaceRegex": "",
      "imageStyle": "",
      "titleRule": "",
      "customProcessor": ""
    }
  }
]
```

### 关键设计说明

| 规则 | 设计思路 |
|------|----------|
| `searchUrl` 用 `@js:` | 搜索关键词需 AES 加密，无法用模板语法，必须用 JS 计算 |
| `bookList` = `ul.ucontent > li` | 列表容器 class 为 `ucontent`，非直觉的 `list` |
| `coverUrl` = `input.h_d_pic@value` | 封面 URL 在 hidden input 中，而非 `<img src="">` |
| `wordCount` = `span.vodtime@text` | 视频时长放在 wordCount 字段（视频站无字数） |
| `chapterList` = `"-"` | 视频无章节目录，用 `"-"` 表示单章 |
| `content` = `.playsource a@playdata` | m3u8 地址在自定义属性 `playdata` 中，非 `<video src="">` |
| AES 用 `NoPadding` + 手动填充 | Java Crypto 不支持 ZeroPadding，需手动补零 |
| `searchUrl` 加密 | 使用 `java.createSymmetricCrypto()` 一行调用，而非手动 `javax.crypto.*`（500+字符且踩 Rhino 陷阱） |

---

## 关键提示

1. **⚠️ 输出必须是 `[...]` 数组格式**：Legado 导入时始终期望数组，单个对象 `{...}` 会导致导入失败
2. **bookSourceUrl 必须唯一**：这是书源的主键，重复会导致覆盖
3. **先测搜索再测正文**：搜索是最常用的入口，先确保搜索规则正确
4. **正文用 `html` 而非 `text`**：`html` 保留段落格式，`text` 会丢失换行
5. **replaceRegex 过滤广告**：这是书源质量的体现，多写几条替换规则
6. **charset 很重要**：很多中文网站用 GBK，不指定会导致乱码
7. **使用 `||` 做容错**：网站结构可能微调，多写几个备选规则

## 社区源模式分析

> 基于 yckceo.com 2561个社区订阅源的分析结果

### 最常见 ruleContent 模式

| 排名 | 规则 | 使用次数 | 适用场景 |
|------|------|----------|----------|
| 1 | `<!DOCTYPE html>\n\n<html>\n\n\n\n<head>\n\n    <meta name="viewport"` | 31 | 获取完整HTML内容 |
| 2 | `<js>page=Number({{@@class.pagination.0@tag.a.-2@textNodes}})` | 21 | 图片/视频地址 |
| 3 | `//ul/li` | 15 | 通用文章内容 |
| 4 | `<video src="{{$.data.httpurl}}{{$.data.httpurl_preview}}" au` | 14 | 通用文章内容 |
| 5 | `all## <script type="text/javascript">var cnzz_protocol = [\s` | 12 | 通用文章内容 |
| 6 | `<js>\n\nhtml = result\n\n//总页数-1(最后一页没有图\n\npage = parseInt(java.g` | 12 | 获取完整HTML内容 |
| 7 | `script@all` | 11 | 通用文章内容 |
| 8 | `class.s-tab-main@html` | 11 | 获取完整HTML内容 |
| 9 | `id.allbtn@text##展开全图\(1/|\)\n<js>\nn=Number(result)+1\nu='{{@@i` | 11 | 图片/视频地址 |
| 10 | `<js>\n\nfunction getNext(){\n\n//下一页url，链接不全请补全\nnextUrl = java.g` | 11 | 图片/视频地址 |

### 最常见 ruleArticles 模式

| 排名 | 规则 | 使用次数 | 适用场景 |
|------|------|----------|----------|
| 1 | `<js>\njson=[];\nif(baseUrl.match(/ /)){\nlist=baseUrl.replace(/` | 52 | CSS选择器 |
| 2 | `class.update_area_lists@tag.li` | 48 | CSS选择器 |
| 3 | `<js>\njson=[];\nif(baseUrl.match(/★/)){\nlist=baseUrl.replace(/` | 41 | CSS选择器 |
| 4 | `article` | 34 | CSS选择器 |
| 5 | `$.list` | 34 | CSS选择器 |
| 6 | `$.model.data` | 31 | CSS选择器 |
| 7 | `id.content@h3` | 28 | CSS选择器 |
| 8 | `$.data.vodrows` | 26 | CSS选择器 |
| 9 | `ul@li` | 23 | CSS选择器 |
| 10 | `class.item` | 21 | CSS选择器 |

### 社区源常见问题与修复

| 问题 | 影响源数 | 修复方案 |
|------|----------|----------|
| missing_ruleContent | 1509个源缺失 | 见修复模式 |
| missing_ruleArticles | 1026个源缺失列表规则 | 见修复模式 |
| missing_ruleTitle | 1026个源缺失标题规则 | 见修复模式 |
| missing_ruleLink | 1041个源缺失链接规则 | 见修复模式 |
| missing_sourceIcon | 100个源缺失图标 | 见修复模式 |
| rsshub_dependency | 5个源依赖rsshub.app | 见修复模式 |

### 社区源最佳实践

1. 几乎所有可用源都设置了enableJs:true和loadWithBaseUrl:true，这是订阅源的标准配置
2. ruleContent使用@html获取完整HTML内容是最常见的模式
3. ruleArticles使用CSS选择器定位列表容器是最可靠的方式
4. ruleLink使用'a@href'是最通用的链接提取规则
5. ruleTitle使用'a@text'或'a@textNodes'是最通用的标题提取规则
6. sortUrl使用'名称::URL\n名称::URL'格式，支持@js:动态生成
7. enabledCookieJar:true对于需要登录/Cookie的源是必需的
8. singleUrl:true适用于列表即内容的源（如发布页、导航页）
9. articleStyle:1更适合图片源，0适合文本源
10. header中设置合适的User-Agent可以避免被网站拦截


## 书源社区模式分析

> 基于 yckceo.com 社区书源的分析（11535个去重可用源）

### BookSource 类型分布

| 类型 | 数量 | 说明 |
|------|------|------|
| type_ | 754 | |
| 小说(0) | 21517 | |
| 音频(1) | 413 | |
| 图片(2) | 676 | |
| 文件/下载站(3) | 186 | 社区源标注可能有误，旧版为视频 |
| type_4 | 15 | |
| type_AUDIO | 38 | |
| type_TEXT | 282 | |

### BookSource 常见问题 TOP10

| 问题 | 数量 | 修复方案 |
|------|------|----------|
| missing_bookSourceIcon | 23881 | 从网站favicon获取 |
| missing_exploreRule | 9270 | 添加exploreUrl分类发现 |
| missing_bookInfoRule | 6614 | 分析详情页，添加ruleBookInfo字段 |
| missing_contentRule | 3017 | 分析正文页HTML，添加ruleContent.content |
| missing_searchRule | 2896 | 分析搜索页，添加ruleSearch.bookList或searchUrl |
| missing_tocRule | 2797 | 分析目录页，添加ruleToc.chapterList |
| missing_bookSourceName | 3 | 设置书源名称 |
| missing_bookSourceUrl | 1 | 设置书源基础URL |

### BookSource 规则字段使用频率


#### ruleSearch

| 字段 | 使用次数 |
|------|----------|
| name | 20926 |
| bookUrl | 20895 |
| bookList | 20818 |
| author | 19362 |
| coverUrl | 16190 |
| kind | 14855 |
| lastChapter | 12859 |
| intro | 10520 |

#### ruleContent

| 字段 | 使用次数 |
|------|----------|
| content | 20864 |
| nextContentUrl | 6491 |
| replaceRegex | 5363 |
| imageStyle | 1393 |
| sourceRegex | 122 |
| title | 68 |
| payAction | 51 |
| webJs | 17 |

#### ruleToc

| 字段 | 使用次数 |
|------|----------|
| chapterList | 20931 |
| chapterName | 20752 |
| chapterUrl | 20419 |
| nextTocUrl | 4191 |
| updateTime | 1825 |
| isVip | 1062 |
| isVolume | 401 |
| preUpdateJs | 133 |

#### ruleBookInfo

| 字段 | 使用次数 |
|------|----------|
| intro | 18569 |
| name | 17093 |
| author | 16883 |
| coverUrl | 16274 |
| kind | 16036 |
| lastChapter | 16006 |
| tocUrl | 9051 |
| wordCount | 6123 |