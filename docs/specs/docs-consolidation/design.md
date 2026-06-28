# Design: 文档整合技术方案

## Technical Approach

### 整体流程

```
Phase 1: 差异分析 → Phase 2: 并行合并 → Phase 3: 源码验证 → Phase 4: 导航同步 → Phase 5: 清理
```

### Phase 1: 差异分析（逐文件对比）

对每个旧文档 vs project-flow/ 对应文档进行逐节对比，标记：
- **UNIQUE_OLD**: 旧文档独有内容（必须迁移）
- **OVERLAP**: 两套文档重叠内容（以project-flow版为准，补充旧文档独有细节）
- **UNIQUE_NEW**: project-flow/ 独有内容（保留）
- **GAP**: 两套文档都缺失的内容（需源码验证补充）

### Phase 2: 并行合并（按模块分组）

将15个旧文档按目标位置分组，每组启动一个子代理并行合并：

| 分组 | 旧文档 | 目标文件 | 预估行数 |
|------|--------|---------|---------|
| G1: 架构总览 | 01-项目概述 | architecture/overview.md | ~350 |
| G2: 规则引擎 | 03-规则引擎 | architecture/rule-engine.md | ~2500 |
| G3: 网络层 | 04-网络请求 | architecture/network-layer.md | ~1200 |
| G4: 前端 | 11-Vue3前端 | architecture/frontend.md | ~2500 |
| G5: 数据库 | 02-数据库设计 | database/overview.md + entities.md | ~1500 |
| G6: 搜索+并发 | 05-WebBook + 07-搜索并发 | modules/webbook-search.md | ~2000 |
| G7: 内容处理 | 06-内容处理 | modules/content-pipeline.md | ~1100 |
| G8: 本地书 | 08-本地书籍 | modules/local-book.md | ~1500 |
| G9: 阅读引擎 | 09-阅读引擎 | modules/reading-engine.md | ~2500 |
| G10: API+Web服务 | 10-API规范 | modules/web-service.md + architecture/api-dataflow.md | ~1800 |
| G11: 服务层 | 12-服务层 | modules/service-layer.md + modules/android-services.md | ~2200 |
| G12: 配置 | 13-配置与重构 | modules/config-system.md | ~800 |
| G13: 补遗分散 | 14-遗漏补充 + 15-深层补遗 | 分散到对应模块 | 各模块增加 |

### Phase 3: 源码验证

对合并后的关键文档启动子代理对照源码验证：
- 规则引擎（analyzeRule/ 目录）
- 网络请求（model/analyzeRule/AnalyzeUrl.kt）
- 阅读引擎（model/ReadBook.kt）
- 数据库（data/entities/）
- JS扩展（model/webBook/JsExtensions.kt）

### Phase 4: 导航同步

更新所有索引文件：
- docs/INDEX.md
- docs/README.md
- project-flow/INDEX.md
- project-flow/quick-reference.md
- project-flow/task-navigation.md

### Phase 5: 清理

- 删除 docs/01-15 文档
- 验证所有内部链接有效性

## Architecture Decisions

### ADR-1: 合并方向 — 以 project-flow/ 为骨架

**Context**: 两套文档各有优势，旧文档深度高但结构差，project-flow/ 结构好但深度不足。

**Decision**: 以 project-flow/ 为骨架，将旧文档独有内容补充进去。

**Rationale**: project-flow/ 的目录结构更合理（architecture/modules/database 三级分离），索引体系更完善。旧文档的编号式命名不利于维护和扩展。

**Consequences**: 需要大量内容迁移工作，但最终产物更易维护。

### ADR-2: 超长文档处理 — 拆分为子文档

**Context**: 合并后部分文档可能超过 2000 行（规则引擎、阅读引擎、前端）。

**Decision**: 超过 1500 行的文档拆分为主文档+子文档，主文档保留概览和核心流程，子文档存放详细实现。

**Rationale**: 单文档过长不利于阅读和 AI 上下文加载。

**Consequences**: 需要维护主文档↔子文档的交叉引用。

拆分方案：

| 文档 | 拆分策略 |
|------|---------|
| architecture/rule-engine.md | 主文档(概览+状态机+5种解析器概要) + rule-engine-algorithms.md(算法详解) + rule-engine-js-env.md(JS环境+变量机制) |
| modules/reading-engine.md | 主文档(状态机+缓存+预下载) + reading-engine-pagination.md(分页算法) + reading-engine-media.md(漫画+音频) |
| architecture/frontend.md | 主文档(MPA架构+路由+组件树) + frontend-components.md(组件实现) + frontend-stores.md(Store实现) |

### ADR-3: Python 伪代码保留策略

**Context**: 旧文档包含大量 Python 伪代码实现，project-flow/ 以架构描述为主。

**Decision**: 保留 Python 伪代码，但移至文档末尾的"Python 重构参考"章节，与架构描述分离。

**Rationale**: Python 伪代码对重构有参考价值，但不应与架构描述混合影响阅读。

### ADR-4: database/ 目录扩展

**Context**: 当前 database/ 仅 123 行，远不如旧文档 02-数据库设计.md(1305行) 详细。

**Decision**: 扩展 database/ 为完整数据库文档目录：
- overview.md: 数据库概览+ER图+迁移策略
- entities.md: 完整实体字段定义（从 architecture/entity-fields.md 迁移）
- tables.md: 21张表完整DDL+字段详解+索引

**Rationale**: 数据库是项目核心，需要独立完整的文档。当前 architecture/entity-fields.md 应归入 database/。

## Data Flow

```
旧文档(01-15) ──读取──→ 差异分析 ──标记──→ 合并引擎 ──写入──→ project-flow/
                                                          ↑
Legado源码 ──子代理验证──→ 补充内容 ──────────────────────┘
                                                          ↓
                                              导航更新(INDEX/README/quick-ref)
                                                          ↓
                                                  删除旧文档(01-15)
```

## File Changes

### 新增文件
| 文件 | 说明 |
|------|------|
| project-flow/architecture/rule-engine-algorithms.md | 规则引擎算法详解（从03拆分） |
| project-flow/architecture/rule-engine-js-env.md | JS环境+变量机制（从03拆分） |
| project-flow/modules/reading-engine-pagination.md | 分页算法详解（从09拆分） |
| project-flow/modules/reading-engine-media.md | 漫画+音频播放（从09拆分） |
| project-flow/architecture/frontend-components.md | 前端组件实现（从11拆分） |
| project-flow/architecture/frontend-stores.md | 前端Store实现（从11拆分） |
| project-flow/database/tables.md | 21张表完整DDL（从02迁移） |

### 修改文件
| 文件 | 变更说明 |
|------|---------|
| project-flow/architecture/overview.md | 补充01项目概述完整内容 |
| project-flow/architecture/rule-engine.md | 补充03独有内容，拆分超长部分 |
| project-flow/architecture/network-layer.md | 补充04 AnalyzeUrl管线+并发控制 |
| project-flow/architecture/frontend.md | 补充11独有内容，拆分超长部分 |
| project-flow/architecture/api-dataflow.md | 补充10 API端点+WebSocket协议 |
| project-flow/architecture/entity-fields.md | 迁移至 database/entities.md |
| project-flow/database/overview.md | 扩展为完整数据库概览 |
| project-flow/database/entities.md | 扩展为完整实体字段定义 |
| project-flow/modules/webbook-search.md | 合并05+07，补充正文管线+并发模型 |
| project-flow/modules/content-pipeline.md | 补充06 8步管线+ReplaceRule引擎 |
| project-flow/modules/local-book.md | 补充08 5种格式解析+编码检测 |
| project-flow/modules/reading-engine.md | 补充09分页+预下载，拆分超长部分 |
| project-flow/modules/web-service.md | 补充10 REST+WebSocket完整规范 |
| project-flow/modules/service-layer.md | 补充12服务Python伪代码 |
| project-flow/modules/android-services.md | 补充12 Android服务详解 |
| project-flow/modules/config-system.md | 补充13 17条Python重构建议 |
| project-flow/modules/js-extensions.md | 补充14 70+ JS扩展函数清单 |
| project-flow/modules/rss-subsystem.md | 补充14 RSS双解析器详解 |
| project-flow/modules/tools-infrastructure.md | 补充14+15 工具类详解 |
| project-flow/modules/model-layer.md | 补充15 BookHelp/Debug等详解 |
| project-flow/quick-reference.md | 填充空表 |
| project-flow/INDEX.md | 更新关键词索引 |
| project-flow/task-navigation.md | 更新代码锚点 |
| docs/INDEX.md | 更新文档索引，移除旧文档引用 |
| docs/README.md | 更新文档列表 |

### 删除文件
| 文件 | 说明 |
|------|------|
| docs/01-项目概述.md | 内容已合并至 project-flow/ |
| docs/02-数据库设计.md | 内容已合并至 project-flow/database/ |
| docs/03-规则引擎.md | 内容已合并至 project-flow/architecture/ |
| docs/04-网络请求.md | 内容已合并至 project-flow/architecture/ |
| docs/05-WebBook业务.md | 内容已合并至 project-flow/modules/ |
| docs/06-内容处理.md | 内容已合并至 project-flow/modules/ |
| docs/07-搜索并发模型.md | 内容已合并至 project-flow/modules/ |
| docs/08-本地书籍解析.md | 内容已合并至 project-flow/modules/ |
| docs/09-阅读引擎.md | 内容已合并至 project-flow/modules/ |
| docs/10-API规范.md | 内容已合并至 project-flow/modules/ |
| docs/11-Vue3前端架构.md | 内容已合并至 project-flow/architecture/ |
| docs/12-服务层.md | 内容已合并至 project-flow/modules/ |
| docs/13-配置与重构.md | 内容已合并至 project-flow/modules/ |
| docs/14-遗漏补充.md | 内容已分散至对应模块文档 |
| docs/15-深层补遗.md | 内容已分散至对应模块文档 |
