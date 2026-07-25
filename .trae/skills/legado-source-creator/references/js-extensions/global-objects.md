# JS 全局对象 API 参考

> Legado Rhino JS 环境中可直接访问的全局对象及其方法/属性。
> 验证日期：2026-06-03

---

## book 对象

> 类型：`Book`（继承自 `BaseBook` → `RuleDataInterface`）
> 源码：`app/src/main/java/io/legado/app/data/entities/Book.kt`、`BaseBook.kt`

### 方法

| 方法 | 返回值 | 说明 | 源码行号 |
|------|--------|------|----------|
| `putVariable(key, value)` | `Boolean` | 存储变量到 book.variable | BaseBook.kt L19-24 |
| `getVariable(key)` | `String` | 从 book.variable 读取变量 | RuleDataInterface.kt L32-34 |

### 完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `bookUrl` | String | 书籍URL（主键之一） |
| `tocUrl` | String | 目录页URL |
| `origin` | String | 书源URL |
| `originName` | String | 书源名称 |
| `name` | String | 书名 |
| `author` | String | 作者 |
| `kind` | String | 分类 |
| `customTag` | String | 自定义标签 |
| `coverUrl` | String | 封面URL |
| `customCoverUrl` | String | 自定义封面URL |
| `intro` | String | 简介 |
| `customIntro` | String | 自定义简介 |
| `charset` | String | 编码 |
| `type` | Int | 类型（0:文字 1:音频 3:图片） |
| `group` | Long | 分组 |
| `latestChapterTitle` | String | 最新章节标题 |
| `latestChapterTime` | Long | 最新章节时间 |
| `lastCheckTime` | Long | 最后检查时间 |
| `lastCheckCount` | Int | 最后检查新章数 |
| `totalChapterNum` | Int | 总章节数 |
| `durChapterTitle` | String | 当前阅读章节标题 |
| `durChapterIndex` | Int | 当前阅读章节索引 |
| `durChapterPos` | Int | 当前阅读位置 |
| `durChapterTime` | Long | 当前阅读章节时间 |
| `canUpdate` | Boolean | 是否可更新 |
| `order` | Int | 排序 |
| `originOrder` | Int | 书源排序 |
| `variable` | String | 变量JSON字符串 |

---

## chapter 对象

> 类型：`BookChapter`（继承自 `BaseBook` → `RuleDataInterface`）
> 源码：`app/src/main/java/io/legado/app/data/entities/BookChapter.kt`

### 方法

| 方法 | 返回值 | 说明 | 源码行号 |
|------|--------|------|----------|
| `putVariable(key, value)` | `Boolean` | 存储变量（重写） | L96-101 |
| `getVariable(key)` | `String` | 读取变量（继承自 RuleDataInterface） | RuleDataInterface.kt L32-34 |
| `putLyric(value)` | Unit | 存储歌词 | L74-79 |
| `putImgUrl(value)` | Unit | 存储图片URL | L69-72 |
| `putDanmaku(value)` | Unit | 存储弹幕 | L81-86 |
| `update()` | Unit | 更新章节到数据库 | L88-90 |

### 完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `url` | String | 章节URL（复合主键之一） |
| `title` | String | 章节标题 |
| `baseUrl` | String | 基础URL |
| `bookUrl` | String | 所属书籍URL（复合主键之一） |
| `index` | Int | 章节索引 |
| `resourceUrl` | String | 资源URL（音频/视频） |
| `tag` | String | 标签 |
| `start` | Long | 起始位置 |
| `end` | Long | 结束位置 |
| `variable` | String | 变量JSON字符串 |

---

## source 对象

> 类型：`BaseSource`（BookSource 和 RssSource 的基类）
> 源码：`app/src/main/java/io/legado/app/data/entities/BaseSource.kt`

### 方法

| 方法 | 返回值 | 说明 | 源码行号 |
|------|--------|------|----------|
| `put(key, value)` | `String` | 存储变量到 source.variable | L275-278 |
| `get(key)` | `String` | 从 source.variable 读取变量 | L284-286 |
| `getLoginHeader()` | `String?` | 获取登录Header | L139-141 |
| `putLoginHeader(header)` | Unit | 存储登录Header | L151-158 |
| `removeLoginHeader()` | Unit | 删除登录Header | L160-163 |
| `getLoginInfo()` | `String?` | 获取登录信息 | L170-179 |
| `putLoginInfo(info)` | `Boolean` | 存储登录信息 | L221-231 |
| `removeLoginInfo()` | Unit | 删除登录信息 | L234-236 |
| `refreshExplore()` | Unit | 刷新发现页配置 | L291-300 |
| `refreshJSLib()` | Unit | 刷新JS库 | L305-312 |
| `getKey()` | `String` | 获取书源URL（唯一标识） | — |

---

## cookie 对象

> 类型：`CookieStore`（注意：不是 CookieManager.kt）
> 源码：`app/src/main/java/io/legado/app/data/entities/CookieStore.kt`

### 方法

| 方法 | 返回值 | 说明 | 源码行号 |
|------|--------|------|----------|
| `getKey(url, key)` | `String` | 获取指定URL下指定key的Cookie值 | L87-92 |
| `replaceCookie(url, cookie)` | Unit | 替换指定URL的Cookie | L51-64 |
| `setWebCookie(url, cookie)` | Unit | 设置WebView Cookie | L37-49 |
| `removeCookie(url)` | Unit | 删除指定URL的Cookie | CookieStore.kt L94-100 |

---

## cache 对象

> 类型：`CacheManager`（注意：不是 WebCacheManager）
> 源码：`app/src/main/java/io/legado/app/help/CacheManager.kt`
> JS 绑定位置：BaseSource.kt L331、AnalyzeUrl.kt L369、AnalyzeRule.kt L832，三处均为 `bindings["cache"] = CacheManager`

> ⚠️ **重要**：`WebCacheManager`（CacheManager.kt L158-196）是给 WebView 的 `@JavascriptInterface` 使用的，并非 Rhino JS 引擎中的 `cache` 对象。JS 环境中的 `cache` 绑定的是 `CacheManager`。

### 方法

| 方法 | 返回值 | 说明 | 源码行号 |
|------|--------|------|----------|
| `put(key, value, saveTime)` | Unit | 存储缓存，saveTime 单位：秒，默认 0（永久） | L58-70 |
| `get(key)` | `String?` | 读取缓存 | L85-96 |
| `putFile(key, value, saveTime)` | Unit | 存储文件缓存 | L141-143 |
| `getFile(key)` | `String?` | 读取文件缓存 | L145-147 |
| `putMemory(key, value)` | Unit | 存储内存缓存（不持久化） | L72-74 |
| `getFromMemory(key)` | `Any?` | 读取内存缓存 | L77-79 |
| `deleteMemory(key)` | Unit | 删除内存缓存 | L81-83 |
| `delete(key)` | Unit | 删除缓存（含文件） | L149-153 |

---

## 全局变量

> 在 JS 规则执行环境中可直接访问的全局变量。
> 源码：AnalyzeRule.kt evalJS() 方法中的绑定

| 变量 | 类型 | 说明 | 可用阶段 |
|------|------|------|----------|
| `result` | String | 当前规则执行结果 | 所有阶段 |
| `src` | String | 请求返回的源码 | 所有阶段 |
| `baseUrl` | String | 当前页面URL | 所有阶段 |
| `key` | String | 搜索关键词 | 搜索 |
| `page` | String/Int | 当前页码 | 搜索、发现、目录 |
| `title` | String | 章节当前标题 | 正文 |
| `book` | Book | Book 对象 | 详情、目录、正文 |
| `chapter` | BookChapter | BookChapter 对象 | 正文 |
| `source` | BaseSource | BaseSource 对象 | 所有阶段 |
| `cookie` | CookieStore | CookieStore 对象 | 所有阶段 |
| `cache` | WebCacheManager | WebCacheManager 对象 | 所有阶段 |
| `java` | JsExtensions | JsExtensions 实例 | 所有阶段 |
| `nextChapterUrl` | String | 下一章节URL | 正文 |

### 注意事项

- `java` 变量是 JsExtensions 实例，**会遮蔽 Rhino 的 Java 包命名空间**。如需访问 Java 类，使用 `Packages.java.xxx` 前缀
- `page` 在不同上下文中类型可能不同，建议用 `Number(page)` 确保数值类型
- `result` 可被 JS 代码重写（`result = 新值`），重写后的值作为当前规则的输出
