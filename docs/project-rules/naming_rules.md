# 命名规范

> 基于 Legado 项目源码深度分析提取的项目特有命名约定，AI Agent 必须遵循。

---

## 类命名 — PascalCase + 语义后缀

| 后缀 | 用途 | 示例 |
|------|------|------|
| (无后缀) | 核心业务 object 单例 | `ReadBook`, `WebBook`, `Debug`, `CacheBook`, `AudioPlay` |
| Model | 并发调度/聚合模型 | `SearchModel` |
| Helper | 工具/辅助类 | `HttpHelper`, `SSLHelper`, `BookHelp`, `ContentHelp` |
| Config | 配置管理 object | `AppConfig`, `ReadBookConfig`, `ThemeConfig`, `SourceConfig` |
| Extensions | 扩展函数文件 | `BookExtensions`, `BookSourceExtensions` |
| Controller | Web API 控制器 | `BookController`, `BookSourceController` |
| Service | Android Service | `AudioPlayService`, `CacheBookService` |
| Activity | UI Activity | `ReadBookActivity`, `SearchActivity` |
| Dao | Room DAO 接口 | `BookDao`, `BookSourceDao` |
| Rule | 规则数据类 | `SearchRule`, `ContentRule`, `ExploreRule` |
| Processor | 处理管线 | `ContentProcessor` |
| Manager | 管理器 | `CookieManager`, `CacheManager` |
| Interceptor | OkHttp 拦截器 | `OkHttpExceptionInterceptor`, `DecompressInterceptor` |

## 方法命名 — 项目特有缩写

| 前缀/后缀 | 含义 | 示例 |
|-----------|------|------|
| `up` | update 的缩写（项目历史约定） | `upContent()`, `upData()`, `upMenuView()`, `upReadTime()` |
| `Await` 后缀 | 挂起函数版本 | `searchBookAwait()`, `getContentAwait()`, `loadContentAwait()` |
| `get` | 获取数据 | `getBook()`, `getBookInfo()`, `getChapterList()` |
| `is` | 布尔属性 | `isRun`, `isLocal`, `isAudio`, `isImage` |
| `has` | 存在性检查 | `has()`, `hasGroup()`, `hasVariable()` |
| `add/remove` | 集合操作 | `addType()`, `removeType()`, `addGroup()` |
| `on` | 回调/事件 | `onSuccess`, `onError`, `onFinally`, `onCancel` |

## 变量命名 — 项目特有缩写

| 模式 | 含义 | 示例 |
|------|------|------|
| `dur` 前缀 | "当前"(current/duration) | `durChapterIndex`, `durChapterPos`, `durChapterTitle` |
| `prev/cur/next` | 三章缓存 | `prevTextChapter`, `curTextChapter`, `nextTextChapter` |
| `appDb` | 全局数据库引用 | 顶级 lazy 属性 |
| `appCtx` | 全局 Context | 来自 splitties 库 |

## 常量命名 — 混合风格（项目约定）

项目常量命名存在两派风格，这是历史遗留约定：

| 风格 | 使用位置 | 示例 |
|------|----------|------|
| UPPER_SNAKE_CASE | `Status`, `EventBus`, `AppConst` 部分 | `STOP`, `PLAY`, `RECREATE`, `APP_TAG` |
| camelCase + @Suppress | `BookType`, `AppConst` 部分 | `video`, `text`, `audio`, `channelIdDownload` |

**规则**：新增常量优先使用 UPPER_SNAKE_CASE。如需使用 camelCase 常量（如位标志组），必须添加 `@Suppress("ConstPropertyName")`。

## 扩展函数组织

按目标实体组织到独立文件：

| 文件 | 目标实体 |
|------|----------|
| `help/book/BookExtensions.kt` | Book |
| `help/book/BookChapterExtensions.kt` | BookChapter |
| `help/source/BookSourceExtensions.kt` | BookSource |
| `help/source/BaseSourceExtensions.kt` | BaseSource |
| `help/source/RssSourceExtensions.kt` | RssSource |

## 包结构

```
io.legado.app/
├── api/controller/        # Web API 控制器
├── base/adapter/          # 基类 + RecyclerView 适配器
├── constant/              # 常量 (AppConst, Status, EventBus, BookType)
├── data/dao/              # Room DAO
├── data/entities/rule/    # 规则数据类
├── exception/             # 自定义异常
├── help/book/             # 书籍扩展+帮助
├── help/config/           # 配置管理
├── help/coroutine/        # 自定义协程封装
├── help/crypto/           # 加密
├── help/http/             # HTTP 相关
├── help/source/           # 书源扩展
├── help/storage/          # 备份恢复
├── lib/mobi/              # MOBI 解析（独立库级）
├── lib/webdav/            # WebDAV 客户端（独立库级）
├── lib/theme/             # 主题引擎（独立库级）
├── model/analyzeRule/     # 规则引擎
├── model/localBook/       # 本地书解析
├── model/webBook/         # 网络书
├── model/rss/             # RSS
├── service/               # Android Service
├── ui/                    # UI 层
└── web/                   # NanoHTTPD Web 服务器
```

**help/ vs lib/ 区分**：`help/` 是项目业务辅助代码，`lib/` 是相对独立的库级代码。
