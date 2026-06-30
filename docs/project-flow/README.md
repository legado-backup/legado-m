# 项目文档导航

> Legado（阅读Sigma）项目 Wiki 文档体系。按任务类型或模块快速定位到对应文档。

---

## 快速路径

| 我要做什么 | 看哪个文档 |
|-----------|-----------|
| 了解整体架构 | [architecture/overview.md](./architecture/overview.md) |
| 了解前端页面布局 | [architecture/frontend.md](./architecture/frontend.md) |
| 理解前后端数据流 | [architecture/api-dataflow.md](./architecture/api-dataflow.md) |
| 查看核心实体字段 | [database/entities.md](./database/entities.md) |
| 新增/修改书源规则 | [architecture/rule-engine.md](./architecture/rule-engine.md) |
| 理解搜索并发逻辑 | [modules/webbook-search.md](./modules/webbook-search.md) |
| 修改正文后处理 | [modules/content-pipeline.md](./modules/content-pipeline.md) |
| 新增阅读功能 | [modules/reading-engine.md](./modules/reading-engine.md) |
| 新增数据库表/字段 | [modules/data-layer.md](./modules/data-layer.md) |
| 新增 Web API | [modules/web-service.md](./modules/web-service.md) |
| 优化 TXT/EPUB 解析 | [modules/local-book.md](./modules/local-book.md) |
| 了解 WebDAV/TTS/RSS | [modules/service-layer.md](./modules/service-layer.md) |
| 修改 UI/Activity | [architecture/android-ui.md](./architecture/android-ui.md) |
| 了解 Android 页面布局交互 | [architecture/android-ui.md](./architecture/android-ui.md) §9-10 |
| 修改网络层/SSL | [architecture/network-layer.md](./architecture/network-layer.md) |
| 修改配置项 | [modules/config-system.md](./modules/config-system.md) |
| 新增后台 Service | [modules/android-services.md](./modules/android-services.md) |
| 修改备份/恢复 | [modules/backup-restore.md](./modules/backup-restore.md) |
| 集成第三方库 | [modules/remote-third-party.md](./modules/remote-third-party.md) |
| 速查命令/版本/文件 | [quick-reference.md](./quick-reference.md) |
| 了解启动流程 | [architecture/app-init.md](./architecture/app-init.md) |
| 了解 Model 单例 | [modules/model-layer.md](./modules/model-layer.md) |
| 编写书源 JS 规则 | [modules/js-extensions.md](./modules/js-extensions.md) |
| 管理书源/导入导出 | [modules/source-management.md](./modules/source-management.md) |
| 了解 MVVM/Base | [architecture/base-layer.md](./architecture/base-layer.md) |
| 开发 RSS 订阅 | [modules/rss-subsystem.md](./modules/rss-subsystem.md) |
| 修改工具类/协程/加密 | [modules/tools-infrastructure.md](./modules/tools-infrastructure.md) |
| 了解 help/ 辅助工具层 | [modules/help-layer.md](./modules/help-layer.md) |
| 开发MOBI/WebDAV/主题 | [modules/custom-libraries.md](./modules/custom-libraries.md) |

---

## 文档结构

``` 
docs/project-flow/
├── README.md                          ← 你在这里
├── INDEX.md                           ← 全局关键词索引（170+条目）
├── quick-reference.md                 ← 命令/文件/版本锁定速查
├── architecture/
│   ├── overview.md                    ← 四层架构+数据流+设计模式
│   ├── multi-agent-analysis-spec.md    ← 🔴 AI方法论（强制遵循：五阶段流水线+单代理≤12文件）
│   ├── rule-engine.md                 ← 规则引擎（SourceRule状态机+五种解析+JS环境+WebJs模式+ruleType常量）
│   ├── rule-engine-js-env.md          ← JS环境绑定（AnalyzeRule+AnalyzeUrl绑定+Rhino缓存+@put/@get变量）
│   ├── rule-engine-algorithms.md      ← 规则引擎算法（SourceRule初始化+RuleAnalyzer完整算法+前缀检测）
│   ├── frontend.md                    ← Vue3 MPA架构（config/types等9模块+路由+组件树+功能）
│   ├── frontend-components.md         ← 前端组件（路由设计+阅读器核心+通用组件）
│   ├── frontend-stores.md             ← 前端状态管理（Pinia Stores+数据流）
│   ├── api-dataflow.md                ← 接口数据流（HTTP/WS/Beacon完整链路+API表）
│   ├── android-ui.md                  ← Android UI层（MainActivity+ReadBookActivity三层继承+RSS+Activity体系+Widget+Theme+核心页面布局与交互）
│   ├── network-layer.md               ← 网络层（OkHttp拦截器链+SSL+Cookie+Cronet+代理）
│   ├── app-init.md                    ← App初始化（50步启动+常量+EventBus+异常+监控）
│   ├── base-layer.md                  ← ⭐ Base类与MVVM（BaseActivity/VM/Service+RecyclerAdapter+Diff）
│   └── skill-architecture.md          ← Skill体系架构（陷阱体系+JVM仿真器+Python客户端）
├── database/
│   ├── overview.md                    ← 数据库概览（AppDatabase定义+版本+迁移清单）
│   ├── entities.md                    ← 实体与字段详解（BookSource+Book+5组规则字段）
│   └── tables.md                      ← 表结构DDL（全部21张表DDL+索引+约束）
└── modules/
    ├── webbook-search.md              ← WebBook双版本+搜索调度+四分类去重
    ├── content-pipeline.md            ← ContentProcessor七步管线+替换规则引擎
    ├── reading-engine.md              ← ReadBook状态机+三章缓存+预下载
    ├── reading-engine-media.md        ← 阅读引擎媒体层（BookType位标志+ReadManga+AudioPlay）
    ├── reading-engine-pagination.md   ← 阅读引擎排版层（durChapterPos+TextChapter+翻页动画）
    ├── data-layer.md                  ← 21实体+21DAO+1视图+AutoMigration
    ├── web-service.md                 ← NanoHTTPD路由+14POST+12GET+4控制器+WebSocket
    ├── local-book.md                  ← TXT编码检测+目录规则+EPUB
    ├── service-layer.md               ← WebDAV+TTS+RSS+JS扩展
    ├── config-system.md               ← 配置系统（AppConfig+ReadBookConfig+ThemeConfig+字段类型修正）
    ├── android-services.md            ← Service层（11个Service+WebSocketServer+CustomExporter+ExoPlayer+朗读状态机+WakeLock）
    ├── backup-restore.md              ← 备份恢复（21数据源JSON导出+AES+WebDAV同步）
    ├── remote-third-party.md          ← 远程书+第三方库（Glide/GSYVideo/ExoPlayer+更新）
    ├── model-layer.md                 ← ⭐ Model层单例（ReadAloud/VideoPlay/BookCover/CheckSource等）
    ├── js-extensions.md               ← ⭐ JS扩展函数（30+方法：ajax/webView/cache/file/encode）
    ├── source-management.md           ← 书源管理（导入/导出/校验/调试/登录/18+全链路）
    ├── rss-subsystem.md               ← ⭐ RSS子系统（Rss调度+规则解析+标准解析+文章流UI）
    ├── tools-infrastructure.md         ← ⭐ 工具与辅助层（utils+协程+加密+广播接收器）
    ├── help-layer.md                   ← ⭐ Help辅助层（监控三件套+数据传递+渲染优化+规则辅助+缓存系统+默认数据）
    └── custom-libraries.md             ← ⭐ 自定义库层（MOBI解析引擎+WebDAV+主题引擎+阿里云TTS+Cronet+权限+对话框+偏好控件）
```

---

## 文档设计原则

1. **任务导向** — 每个文档对应一个开发任务领域
2. **深度 + 行号** — 算法伪代码+数据模型+状态机+精确代码锚点
3. **模块独立** — 可独立阅读，减少交叉引用
4. **大小控制** — 单文档 ≤ 400行，AI Agent 一次性加载不压缩
5. **可迭代扩展** — 新增文档无需重构现有结构

---

## 关联文件

| 文件 | 说明 |
|------|------|
| [AGENTS.md](../../AGENTS.md) | 项目根 AI Agent 指南（任务导航表） |
| docs/README.md | 项目文档总入口（索引与导航） |