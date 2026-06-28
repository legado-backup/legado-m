# Legado（开源阅读）项目深度分析文档

> 基于对 `temp/legado` 项目源码的逐行级深度分析整理
> 目标：提供足够支撑 **Python 后端 + Vue3 前端 + SQLite 数据库** 完整重构的设计文档
>
> 项目版本：3.x | 包名：`io.legado.app` | 数据库版本：89

## 文档目录

> 所有详细技术文档已整合至 [project-flow/](./project-flow/) 目录，按架构/模块/数据库分类组织。

| 分类 | 目录 | 说明 |
|------|------|------|
| 架构文档 | [project-flow/architecture/](./project-flow/architecture/) | 规则引擎、前端架构、网络层、UI体系、启动流程等 |
| 模块文档 | [project-flow/modules/](./project-flow/modules/) | WebBook、阅读引擎、内容处理、服务层、本地书籍等 |
| 数据库文档 | [project-flow/database/](./project-flow/database/) | 数据库总览、实体定义、表结构DDL |
| 快速参考 | [project-flow/quick-reference.md](./project-flow/quick-reference.md) | 构建命令/关键文件/版本锁定速查 |
| 任务导航 | [project-flow/task-navigation.md](./project-flow/task-navigation.md) | 14个任务导航表（按任务类型索引代码锚点） |
| 关键词索引 | [project-flow/INDEX.md](./project-flow/INDEX.md) | A-Z 关键词索引 |
| 完整索引 | [INDEX.md](./INDEX.md) | 项目所有文档统一入口 |

## 阅读建议

- **首次阅读**：[project-flow/architecture/overview.md](./project-flow/architecture/overview.md) → [project-flow/architecture/rule-engine.md](./project-flow/architecture/rule-engine.md) → [project-flow/modules/webbook-search.md](./project-flow/modules/webbook-search.md) → [project-flow/modules/web-service.md](./project-flow/modules/web-service.md) → [project-flow/architecture/frontend.md](./project-flow/architecture/frontend.md)
- **规则引擎**：[rule-engine.md](./project-flow/architecture/rule-engine.md) 是核心难点，建议配合 [rule-engine-algorithms.md](./project-flow/architecture/rule-engine-algorithms.md) 和 [rule-engine-js-env.md](./project-flow/architecture/rule-engine-js-env.md) 一起阅读
- **重构实施**：聚焦 [project-rules/architecture_rules.md](./project-rules/architecture_rules.md) 的重构注意事项 + [rule-engine.md](./project-flow/architecture/rule-engine.md) 规则引擎 + [web-service.md](./project-flow/modules/web-service.md) API 规范 + [frontend.md](./project-flow/architecture/frontend.md) 前端架构

## 核心架构速览

```
前端 (Vue3 + TS)       →  API层 (FastAPI)     →  业务逻辑层 (Python)
  ├─ Web管理页面        ├─ 书籍API              ├─ WebBook 网书处理
  ├─ 书架页面           ├─ 书源API              ├─ LocalBook 本地处理
  ├─ 阅读器页面         ├─ RSS API              ├─ ReadBook 阅读引擎
  ├─ 搜索页面           ├─ 替换规则API           ├─ CacheBook 缓存下载
  ├─ 书源管理页面       ├─ WebSocket(搜索/调试)  ├─ ExportBook 导出
  └─ 配置页面           └─ 封面/图片代理         └─ RSS 处理
                         ↓                      ↓
                   规则引擎层 (Python)     数据层 (SQLite + 文件缓存)
                   ├─ AnalyzeRule 主引擎     ├─ 数据库 (SQLAlchemy)
                   ├─ Jsoup/XPath/JSONPath   ├─ 章节缓存 (.nb 文件)
                   ├─ JS 沙箱执行器           └─ 封面缓存
                   └─ AnalyzeUrl 构建器
```
