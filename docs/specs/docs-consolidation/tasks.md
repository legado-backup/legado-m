# Tasks: 文档整合任务清单

## Phase 1: 差异分析与源码验证

- [ ] 1.1 启动3个搜索子代理并行扫描，对比旧文档(01-15)与project-flow/对应文档的差异
- [ ] 1.2 标记每个文档节的 UNIQUE_OLD / OVERLAP / UNIQUE_NEW / GAP 状态
- [ ] 1.3 启动源码验证子代理，对照 Legado 源码确认文档准确性，标记 GAP 内容

## Phase 2: 并行合并（13组）

### G1: 架构总览
- [ ] 2.1 合并 01-项目概述.md 完整内容到 architecture/overview.md

### G2: 规则引擎
- [ ] 2.2 合并 03-规则引擎.md 到 architecture/rule-engine.md
- [ ] 2.3 拆分超长部分到 rule-engine-algorithms.md（算法详解）
- [ ] 2.4 拆分超长部分到 rule-engine-js-env.md（JS环境+变量机制）

### G3: 网络层
- [ ] 2.5 合并 04-网络请求.md 到 architecture/network-layer.md

### G4: 前端
- [ ] 2.6 合并 11-Vue3前端架构.md 到 architecture/frontend.md
- [ ] 2.7 拆分超长部分到 frontend-components.md（组件实现）
- [ ] 2.8 拆分超长部分到 frontend-stores.md（Store实现）

### G5: 数据库
- [ ] 2.9 扩展 database/overview.md 为完整数据库概览+ER图+迁移策略
- [ ] 2.10 迁移 architecture/entity-fields.md 内容到 database/entities.md 并扩展
- [ ] 2.11 新增 database/tables.md（21张表完整DDL+字段详解+索引）

### G6: 搜索+并发
- [ ] 2.12 合并 05-WebBook业务.md + 07-搜索并发模型.md 到 modules/webbook-search.md

### G7: 内容处理
- [ ] 2.13 合并 06-内容处理.md 到 modules/content-pipeline.md

### G8: 本地书
- [ ] 2.14 合并 08-本地书籍解析.md 到 modules/local-book.md

### G9: 阅读引擎
- [ ] 2.15 合并 09-阅读引擎.md 到 modules/reading-engine.md
- [ ] 2.16 拆分超长部分到 reading-engine-pagination.md（分页算法）
- [ ] 2.17 拆分超长部分到 reading-engine-media.md（漫画+音频）

### G10: API+Web服务
- [ ] 2.18 合并 10-API规范.md 到 modules/web-service.md + architecture/api-dataflow.md

### G11: 服务层
- [ ] 2.19 合并 12-服务层.md 到 modules/service-layer.md + modules/android-services.md

### G12: 配置
- [ ] 2.20 合并 13-配置与重构.md 到 modules/config-system.md

### G13: 补遗分散
- [ ] 2.21 分散 14-遗漏补充.md 内容到对应模块文档（JS扩展→js-extensions.md, RSS→rss-subsystem.md等）
- [ ] 2.22 分散 15-深层补遗.md 内容到对应模块文档（AppConfig→config-system.md, BookHelp→reading-engine.md等）

## Phase 3: 导航同步

- [ ] 3.1 更新 docs/INDEX.md 反映新文档结构，移除旧文档引用
- [ ] 3.2 更新 docs/README.md，移除旧文档列表，指向 project-flow/
- [ ] 3.3 更新 project-flow/INDEX.md 关键词索引
- [ ] 3.4 填充 project-flow/quick-reference.md 空表
- [ ] 3.5 更新 project-flow/task-navigation.md 代码锚点
- [ ] 3.6 删除 architecture/entity-fields.md（已迁移至 database/entities.md）

## Phase 4: 清理与验证

- [ ] 4.1 删除旧文档 01-15（共15个文件）
- [ ] 4.2 验证所有内部链接有效性
- [ ] 4.3 验证 project-flow/ 目录下文档完整性（无截断、无空章节）
- [ ] 4.4 更新 AGENTS.md 中的文档引用路径（如有）
