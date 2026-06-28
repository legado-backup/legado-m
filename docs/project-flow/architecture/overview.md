# 架构全景图

## 项目定位

**Legado（开源阅读）** 是一款面向 Android 平台的开源电子书阅读器，GitHub 仓库为 [gedoor/legado](https://github.com/gedoor/legado)。与市场上大多数阅读器不同，Legado 的核心设计理念是**用户驱动的书源规则引擎**——用户通过编写自定义规则，即可将任意网页转化为结构化的书籍资源。

### 核心特征

| 特征 | 说明 |
|------|------|
| **自定义书源规则引擎** | 核心差异化能力，支持 CSS 选择器、JSONPath、XPath、正则表达式、JavaScript 五种解析方式 |
| **多格式本地支持** | TXT / EPUB / MOBI / PDF / UMD 等本地书籍解析与阅读 |
| **多内容类型** | 文字阅读、漫画阅读、音频播放（TTS + 在线音频） |
| **RSS 订阅** | 内置 RSS 订阅源管理，支持自定义订阅规则 |
| **Web 管理界面** | Vue3 SPA，端口 1122，支持远程书架管理 |
| **WebDAV 同步** | 书架、配置、书源跨设备同步 |

### 技术栈

| 层次 | 技术 |
|------|------|
| 语言 | Kotlin 2.3.x / Java 17 |
| UI | Android Activity + Fragment + ViewModel |
| 规则引擎 | jsoup 1.16.2（CSS）/ JSONPath / JsoupXpath（XPath） / Rhino 1.8.1（JS） |
| 网络 | OkHttp 3.x + Cronet（可选） |
| 数据库 | Room v89（21 实体 + 21 DAO + 1 视图） |
| Web 服务 | NanoHTTPD + Vue3 |
| 加密 | hutool 5.8.22（书源加解密） |

### 一句话定位

> Legado = **规则引擎驱动**的 Android 电子书阅读器。用户编写规则 → 规则引擎解析网页 → 结构化书籍数据 → 多种阅读模式消费。

---

> Legado 四层架构：UI → 业务逻辑 → 规则引擎 → 数据/网络/服务层。

---

## 四层架构 Mermaid 图

```mermaid
%%{init: {'themeVariables': {'fontFamily': 'Microsoft YaHei, SimHei, sans-serif'}}}%%
flowchart TB
    subgraph UI["UI 层"]
        direction LR
        A1["MainActivity<br/>底部导航(书架/发现/我的/RSS)"]
        A2["ReadBookActivity<br/>阅读界面+翻页+设置"]
        A3["SearchActivity<br/>多书源并发搜索"]
        A4["BookSourceEditActivity<br/>书源编辑/调试"]
        A5["ConfigActivity<br/>全局配置管理"]
        A6["Web管理界面<br/>Vue3 SPA :1122"]
    end

    subgraph BIZ["业务逻辑层 (model/)"]
        direction LR
        B1["webBook/<br/>WebBook+SearchModel<br/>网络书搜索/发现/详情"]
        B2["localBook/<br/>LocalBook+TextFile<br/>TXT/EPUB/MOBI解析"]
        B3["ReadBook<br/>文字阅读核心<br/>全局单例"]
        B4["ReadManga<br/>漫画阅读<br/>全局单例"]
        B5["AudioPlay<br/>音频播放<br/>全局单例"]
        B6["rss/<br/>RSS订阅调度"]
        B7["remote/<br/>远程书/WebDAV"]
    end

    subgraph ENGINE["规则引擎层 (analyzeRule/)"]
        direction LR
        C1["AnalyzeRule<br/>统一入口 Mode分发"]
        C2["AnalyzeByJSoup<br/>CSS选择器"]
        C3["AnalyzeByJSonPath<br/>JSONPath"]
        C4["AnalyzeByXPath<br/>XPath"]
        C5["AnalyzeByRegex<br/>正则表达式"]
        C6["RhinoScriptEngine<br/>JS执行(rhino 1.8.1)"]
        C7["AnalyzeUrl<br/>URL模板引擎"]
    end

    subgraph INFRA["基础设施层"]
        direction LR
        D1["数据层<br/>Room v89<br/>21实体+21DAO+1视图"]
        D2["网络层<br/>OkHttp+Cronet<br/>SSL+Cookie"]
        D3["服务层<br/>NanoHTTPD+TTS<br/>WebDAV+Service"]
    end

    A1 --> B1 & B2 & B6
    A2 --> B3
    A2 --> B4 & B5
    A3 --> B1
    A4 --> C1
    B1 --> C1 & C7
    B2 --> C1
    B3 --> D1 & D2
    B1 --> D2
    C1 --> C2 & C3 & C4 & C5 & C6
    C7 --> D2
    C1 --> D1
    A5 --> D1 & D3
    A6 --> D3
```

---

## 分层架构

```
┌─────────────────────────────────────────────────────┐
│ UI 层 (Activity/Fragment/ViewModel)                  │
│  SearchActivity / ReadBookActivity / Web管理界面      │
├─────────────────────────────────────────────────────┤
│ 业务逻辑层 (model/)                                   │
│  ├── webBook/    (WebBook/SearchModel/BookList)      │
│  ├── localBook/  (LocalBook/TextFile/EpubFile)       │
│  ├── ReadBook    (阅读核心 全局单例)                  │
│  ├── ReadManga   (漫画阅读 全局单例)                  │
│  ├── AudioPlay   (音频播放 全局单例)                  │
│  ├── rss/        (RSS订阅管理)                        │
│  ├── remote/     (远程书/WebDAV)                      │
│  └── Download/CacheBook (下载/缓存)                   │
├─────────────────────────────────────────────────────┤
│ 规则引擎层 (analyzeRule/)                             │
│  ├── AnalyzeRule     (统一入口 Mode分发)              │
│  ├── AnalyzeByJSoup  (CSS选择器 jsoup 1.16.2)        │
│  ├── AnalyzeByJSonPath (JSONPath)                    │
│  ├── AnalyzeByXPath  (XPath JsoupXpath)              │
│  ├── AnalyzeByRegex  (正则表达式)                     │
│  ├── AnalyzeUrl      (URL模板引擎)                    │
│  └── RhinoScriptEngine (JS执行 rhino 1.8.1)         │
├─────────────────────────────────────────────────────┤
│ 基础设施层                                            │
│  ├── 数据层 (Room 21实体+21DAO+1视图 v89)            │
│  ├── 网络层 (OkHttp + Cronet)                        │
│  └── 服务层 (NanoHTTPD + WebDAV + TTS)               │
└─────────────────────────────────────────────────────┘
```

---

## 数据流

### 搜索数据流
```
UI 输入关键词
  → SearchModel.search(key)
    → Flow.mapParallelSafe(并发)
      → WebBook.searchBookAwait(bookSource)
        → AnalyzeUrl → HTTP 请求
        → BookList.analyzeBookList → 解析结果
      → 四分类聚合去重
    → UI 更新搜索结果
```

### 阅读数据流
```
用户点击书籍
  → ReadBook.resetData(book)
    → loadContent(三章)
      → WebBook.getContentAwait() / LocalBook.getContent()
        → ContentProcessor.getContent() 七步管线
    → TextChapter 创建 → UI 渲染
```

### 本地书导入数据流
```
用户选择文件
  → LocalBook.importFile(path)
    → 扩展名检测 → 分发到 TextFile/EpubFile/...
    → 编码检测 (TXT)
    → 目录规则自动选择 (TXT)
    → Book + Chapters 写入数据库
```

---

## 设计模式总结

| 模式 | 应用场景 |
|------|----------|
| **全局单例 (object)** | ReadBook, ReadManga, AudioPlay, WebBook, AppWebDav |
| **门面模式 (Facade)** | LocalBook (按文件类型分发) |
| **双版本方法** | WebBook.xxx() + xxxAwait() |
| **WeakReference 缓存** | ContentProcessor (防内存泄漏) |
| **状态机** | SourceRule (规则预处理), SearchModel (搜索调度) |
| **位标志 (Bit Flags)** | Book.type, Book.group |
| **模板引擎** | AnalyzeUrl ({{key}}/{{page}} 变量替换) |
| **管线模式** | ContentProcessor 七步处理管线 |
| **REPLACE 策略** | Room Entity 持久化（OnConflictStrategy.REPLACE） |

---

## 关键版本锁定

| 依赖 | 版本 | 原因 |
|------|------|------|
| jsoup | 1.16.2 | 新版 select() 破坏性变更 |
| rhino | 1.8.1 | Android 6 兼容性 |
| hutool | 5.8.22 | 书源加解密依赖 |
| Kotlin | 2.3.x | 项目语言 |
| Java | 17 | 编译目标 |

---

## 模块文档索引

### 架构文档

| 模块 | 文档 | 说明 |
|------|------|------|
| 🔴 **AI方法论** | [architecture/multi-agent-analysis-spec.md](architecture/multi-agent-analysis-spec.md) | **强制遵循**：五阶段流水线+单代理≤12文件+并行+交叉验证+导航同步 |
| 规则引擎 | [architecture/rule-engine.md](architecture/rule-engine.md) | SourceRule状态机+五种解析+JS环境+WebJs模式+变量系统+ruleType常量 |
| 前端架构 | [architecture/frontend.md](architecture/frontend.md) | Vue3 MPA架构+config/types等9模块+路由+组件树+技术栈 |
| API数据流 | [architecture/api-dataflow.md](architecture/api-dataflow.md) | HTTP/WebSocket/Beacon完整链路+API对照表 |
| 核心字段 | [database/entities.md](../database/entities.md) | BookSource/Book/SearchBook/BookChapter/5组规则字段详解 |
| Android UI层 | [architecture/android-ui.md](architecture/android-ui.md) | MainActivity导航+ReadBookActivity三层继承+RSS UI完整覆盖+Activity体系+Fragment+Widget+Theme |
| 网络层 | [architecture/network-layer.md](architecture/network-layer.md) | OkHttp拦截器链+SSL全信任+Cookie双层+Cronet加速+代理+AnalyzeUrl请求管线 |
| App初始化 | [architecture/app-init.md](architecture/app-init.md) | 50步启动流程+常量系统+EventBus+异常体系+监控 |
| Base类与MVVM | [architecture/base-layer.md](architecture/base-layer.md) | BaseActivity/VMBaseActivity/BaseViewModel/BaseService/RecyclerAdapter/Diff+动画 |

### 模块文档

| 模块 | 文档 | 说明 |
|------|------|------|
| 搜索/网络书 | [modules/webbook-search.md](../modules/webbook-search.md) | WebBook双版本+并发搜索+四分类去重 |
| 内容处理 | [modules/content-pipeline.md](../modules/content-pipeline.md) | ContentProcessor七步管线+替换规则引擎 |
| 阅读引擎 | [modules/reading-engine.md](../modules/reading-engine.md) | ReadBook状态机+三章缓存+预下载+漫画+音频 |
| 数据层 | [modules/data-layer.md](../modules/data-layer.md) | 21实体+21DAO+1视图+AutoMigration+位标志+TypeConverter |
| Web服务 | [modules/web-service.md](../modules/web-service.md) | NanoHTTPD路由+14POST+12GET+4控制器+WebSocket+静态服务 |
| 本地书籍 | [modules/local-book.md](../modules/local-book.md) | TXT编码检测+目录规则+EPUB+MOBI+PDF+UMD |
| 配置系统 | [modules/config-system.md](../modules/config-system.md) | AppConfig/ReadBookConfig/ThemeConfig/SourceConfig/LocalConfig+字段类型修正(textBold Int/pageAnim Int/paragraphIndent String) |
| Android Service | [modules/android-services.md](../modules/android-services.md) | 11个Service+WebSocketServer+CustomExporter+ExoPlayer+朗读状态机+音频焦点+WakeLock+通知 |
| 备份恢复 | [modules/backup-restore.md](../modules/backup-restore.md) | 21数据源JSON导出+AES加密+WebDAV同步+Mutex并发 |
| 远程书+第三方库 | [modules/remote-third-party.md](../modules/remote-third-party.md) | RemoteBook/WebDAV浏览+Glide/GSYVideo/ExoPlayer+更新系统 |
| Model层单例 | [modules/model-layer.md](../modules/model-layer.md) | ReadAloud/VideoPlay/BookCover/CheckSource/Debug/RuleUpdate/SharedJsScope |
| JS扩展函数 | [modules/js-extensions.md](../modules/js-extensions.md) | 30+ JS可调用方法：ajax/connect/webView/cache/file/encode/python |
| 书源管理 | [modules/source-management.md](../modules/source-management.md) | 导入/导出/校验/调试/登录/18+过滤+排序全链路 |
| RSS子系统 | [modules/rss-subsystem.md](../modules/rss-subsystem.md) | Rss调度+RssParserByRule规则解析+RssParserDefault标准解析+文章流UI |
| 工具与辅助层 | [modules/tools-infrastructure.md](../modules/tools-infrastructure.md) | utils工具类+协程封装+加密+广播接收器 |
| 自定义库层 | [modules/custom-libraries.md](../modules/custom-libraries.md) | MOBI解析引擎(KF6/KF8)+文件数量修正+语言映射+WebDAV客户端+主题引擎+阿里云TTS |

### 参考文档

| 模块 | 文档 | 说明 |
|------|------|------|
| 快速参考 | [../quick-reference.md](../quick-reference.md) | 命令/文件/版本锁定速查 |
| 全局索引 | [../INDEX.md](../INDEX.md) | 150+条目全局关键词索引 |
