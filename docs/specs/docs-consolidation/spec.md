# Spec: 文档整合 — 消除双套文档，统一至 project-flow/

## Intent

当前 `docs/` 目录下存在两套文档体系：
1. **旧文档** (01-15)：~23,000行，深度分析+Python伪代码，但01截断、内容重叠、无统一索引
2. **project-flow/**：~10,174行，结构化架构概览，但部分文档过薄(database/仅123行)、quick-reference空表

目标：将两套文档合并为 `project-flow/` 下的单一文档体系，保留旧文档的所有独有深度内容，删除旧文档01-15。

## Scope

### In Scope
- 合并15个旧文档的全部独有内容到 project-flow/ 对应文档
- 补充 project-flow/ 中过薄文档（database/、quick-reference.md）
- 重新组织 project-flow/ 目录结构（增加子目录、合并重叠文档）
- 删除旧文档 01-15
- 更新 docs/INDEX.md 和 docs/README.md 反映新结构
- 启动子代理对 Legado 源码进行交叉验证，补充文档缺失内容

### Out of Scope
- Skill 文档（.trae/skills/）不做修改
- project-rules/ 不做修改
- specs/ 其他功能设计文档不做修改

## Approach

### 核心策略：深度合并而非简单拼接

1. **以 project-flow/ 为骨架**：保留其目录结构和架构视角
2. **从旧文档提取独有内容**：Python伪代码、算法详解、完整字段清单、技术选型建议
3. **去重**：两套文档重叠部分以 project-flow/ 版本为准（更新、更结构化），旧文档独有内容补充进去
4. **源码验证**：对关键模块启动子代理对照源码验证，补充文档中缺失的内容

### Alternatives Considered

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 以project-flow为骨架合并(推荐) | 保留结构化优势，补充深度内容 | 工作量中等 |
| B. 以旧文档为骨架重组 | 保留最完整内容 | 丢失project-flow的结构化和索引 |
| C. 完全重写 | 最干净 | 工作量巨大，可能丢失已有细节 |

### Drawbacks
- 合并后文档行数会显著增加（project-flow/从~10K行增至~25K行）
- 部分文档可能过长需要拆分（如规则引擎、阅读引擎）

## Requirements

### R1: 目录结构重组
- project-flow/ 保持 architecture/ + modules/ + database/ 三级结构
- 新增 `architecture/overview.md` 合并 01-项目概述.md 的完整内容
- database/ 目录扩展为完整数据库文档
- quick-reference.md 填充空表

### R2: 内容合并映射

| 旧文档 | 目标位置 | 合并策略 |
|--------|---------|---------|
| 01-项目概述 | architecture/overview.md | 补充完整项目定位内容 |
| 02-数据库设计 | database/ 扩展 | 合并完整DDL+字段详解+索引+迁移 |
| 03-规则引擎 | architecture/rule-engine.md | 补充算法详解+JS环境+变量机制 |
| 04-网络请求 | architecture/network-layer.md | 补充AnalyzeUrl管线+并发控制+Cookie算法 |
| 05-WebBook业务 | modules/webbook-search.md | 补充5步正文管线+Mermaid时序图 |
| 06-内容处理 | modules/content-pipeline.md | 补充8步管线+ReplaceRule引擎 |
| 07-搜索并发模型 | modules/webbook-search.md | 合并到搜索文档的并发章节 |
| 08-本地书籍解析 | modules/local-book.md | 补充5种格式解析+编码检测算法 |
| 09-阅读引擎 | modules/reading-engine.md | 补充分页算法+预下载策略+6种翻页 |
| 10-API规范 | modules/web-service.md + architecture/api-dataflow.md | 补充完整API端点+WebSocket协议 |
| 11-Vue3前端架构 | architecture/frontend.md | 补充完整组件/Store/API实现 |
| 12-服务层 | modules/service-layer.md + modules/android-services.md | 补充7个服务Python伪代码 |
| 13-配置与重构 | modules/config-system.md | 补充17条Python重构建议 |
| 14-遗漏补充 | 分散到对应模块文档 | 70+ JS扩展→js-extensions.md, RSS→rss-subsystem.md等 |
| 15-深层补遗 | 分散到对应模块文档 | AppConfig字段→config-system.md, BookHelp→reading-engine.md等 |

### R3: 源码验证补充
- 对关键模块启动子代理对照 Legado 源码验证文档准确性
- 补充文档中与源码不一致或缺失的内容

### R4: 导航更新
- 更新 docs/INDEX.md 反映新文档结构
- 更新 docs/README.md
- 更新 project-flow/INDEX.md 关键词索引
- 更新 project-flow/quick-reference.md 填充空表

### R5: 清理
- 删除旧文档 01-15
- 删除 docs/README.md 中旧文档列表

## Scenarios

### S1: 开发者查找规则引擎实现细节
- 当前：需同时看 03-规则引擎.md(2556行) 和 architecture/rule-engine.md(419行)
- 合并后：只需看 architecture/rule-engine.md，包含完整算法+概览

### S2: 开发者查找数据库表结构
- 当前：database/entities.md(67行) 远不如 02-数据库设计.md(1305行) 详细
- 合并后：database/ 目录包含完整DDL+字段详解

### S3: 新开发者了解项目
- 当前：需看 README.md + 01-项目概述.md(截断) + architecture/overview.md
- 合并后：architecture/overview.md 包含完整项目定位+架构总览
