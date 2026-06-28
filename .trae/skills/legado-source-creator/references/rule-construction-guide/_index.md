# 规则构建指南索引

> Phase 2（构建规则）阶段的核心参考。指导 AI 选择解析方式、填写规则字段、应对不同网站类型。
> 本目录不重复语法和字段定义，而是提供**决策流程**和**填写模板**。

## 文档清单

| 文档 | 用途 | 何时查阅 |
|------|------|----------|
| [parse-strategy-decision-tree.md](./parse-strategy-decision-tree.md) | 5种解析方式选择决策树：输入网站特征 → 输出推荐解析方式 | 已完成网站分析，需要决定用哪种解析方式时 |
| [rule-field-template.md](./rule-field-template.md) | ruleSearch/ruleBookInfo/ruleToc/ruleContent 字段填写模板：必填/可选清单 + CSS/JSONPath 双示例 + 常见错误 | 开始填写规则字段时 |
| [site-type-strategy.md](./site-type-strategy.md) | 5种网站类型（小说/漫画/音频/视频/论坛）规则构建策略：典型结构 + 常用选择器 + 陷阱 | 针对特定类型网站构建规则时 |

## 与已有文档的关系

| 已有文档 | 本目录如何使用 |
|----------|---------------|
| [../rule-syntax.md](../rule-syntax.md) | 提供5种解析方式的**详细语法**，本目录的决策树决定用哪种，语法细节回查此文档 |
| [../site-features/site-feature-to-rule-type.md](../site-features/site-feature-to-rule-type.md) | 提供**网站特征→规则类型**的映射表，本目录的决策树是其扩展版（加入组合场景和决策表） |
| [../booksource-schema.md](../booksource-schema.md) | 提供**字段定义**，本目录的模板提供**填写示例和错误模式** |

## 使用流程

```
1. 网站分析完成 → 查 parse-strategy-decision-tree.md 决定解析方式
2. 确定解析方式 → 查 rule-field-template.md 按模板填写字段
3. 遇到特定类型网站 → 查 site-type-strategy.md 获取针对性策略
4. 语法细节不清 → 回查 ../rule-syntax.md
5. 字段定义不清 → 回查 ../booksource-schema.md
```
