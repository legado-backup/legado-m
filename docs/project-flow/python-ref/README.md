# Python 重构参考（外迁区）

> 本目录为 Python 重构参考外迁区：从 Kotlin 源码提取的跨语言移植参考实现（本 README+6 份参考件），供 Python 重构对照使用；权威业务文档仍在 `docs/project-flow/modules/` 与 `docs/project-flow/architecture/`。

| 参考件 | 对应模块 |
|--------|----------|
| [reading-engine.md](./reading-engine.md) | 阅读引擎（ReadBook 状态机/三章缓存/翻页跳章/预下载） |
| [web-service.md](./web-service.md) | Web 服务（REST API/数据模型/响应辅助） |
| [local-book.md](./local-book.md) | 本地书籍解析（TXT 编码/EPUB） |
| [service-layer.md](./service-layer.md) | 服务层（WebDAV/TTS/RSS） |
| [webbook-search.md](./webbook-search.md) | WebBook 搜索（并发调度/四分类聚合） |
| [config-system.md](./config-system.md) | 配置系统（AppConfig/ReadBookConfig/SSE 推送适配） |

> **权威源声明**：本目录仅为重构参考件，接口签名/行为语义以 Kotlin 源码及 `modules/` 正式文档为准；两者冲突时以后者为准。
