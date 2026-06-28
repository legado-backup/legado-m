# legado-source-creator Skill 改进

> **状态**：🔄 开发中
> **创建日期**：2026-06-03
> **最后更新**：2026-06-03

## 功能概述

基于对「阅读Skill (legado-book-source-tamer)」的深度对比分析，识别出我们的 `legado-source-creator` Skill 在 Default 语法体系、全局对象 API、高级实战技巧等方面的空白，通过源码验证后逐步补齐，提升书源/订阅源创建的准确性和完整性。

## 核心能力

- 补齐 Legado Default 简写语法体系（class/tag/id 前缀、数组区间、排除语法）
- 补齐全局对象 API（book/chapter/source/cookie/cache 属性和方法）
- 补齐 53 个缺失的 JS 扩展方法（非对称加密、字体反爬、验证码、批量请求等）
- 补齐搜索/详情/目录/正文高级实战技巧
- 补齐编码处理完整指南和动态加载系统化说明
- 新增 4 条 Rhino 陷阱（const 块作用域、select 下拉菜单、webJs 返回值、JSON.stringify 类型）
- 所有新增内容必须经过 Legado 源码验证

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 意图、范围、方法、需求、场景 |
| [design.md](./design.md) | 技术方法、架构决策、数据流、文件变更 |
| [tasks.md](./tasks.md) | 分组任务清单 |

## 关键约束

- **源码确认 + 测试验证**：来自阅读Skill 的所有经验必须先在 lyc 魔改版源码（`gitee.com/lyc486/legado`）中确认，然后编写测试方法进行测试，只有测试通过才写入文档
- **以 lyc 魔改版为准**：我们的项目就是 lyc 魔改版，所有功能以该版本源码为唯一权威
- **SKILL.md 体积控制**：新增内容优先放入 references/ 子文档，保持 SKILL.md 精炼
- **自进化流程**：验证结果写入 references/source-analysis/，经验教训更新 AGENTS.md 陷阱清单
