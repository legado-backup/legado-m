# 文档整合 — 消除双套文档，统一至 project-flow/

> 规模级别：Full
> 状态：✅ 已实施（docs/01-15 已删除，project-flow 目标拆分文件齐全）

## 核心目标

将 `docs/` 下两套文档体系（旧文档 01-15 共 ~23,000 行 + project-flow/ 共 ~10,174 行）合并为 `project-flow/` 下的单一文档体系，保留旧文档所有独有深度内容，删除旧文档 01-15。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach / Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：合并策略 / 目录结构 / 内容映射 / ADR |
| [tasks.md](./tasks.md) | 任务清单：分阶段合并 Roadmap |

## 关键决策

- **以 project-flow/ 为骨架**，从旧文档提取独有内容补充进去
- **去重原则**：重叠部分以 project-flow/ 版本为准（更新、更结构化）
- **源码验证**：对关键模块启动子代理对照 Legado 源码验证文档准确性

## 影响范围

- `docs/01-*.md` ~ `docs/15-*.md` — 旧文档，合并后删除
- `docs/project-flow/` — 目标目录，扩展补充
- `docs/INDEX.md` — 导航更新
