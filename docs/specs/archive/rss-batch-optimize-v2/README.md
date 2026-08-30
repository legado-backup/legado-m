# RSS 订阅源批量优化 v2（222源）

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

## 功能概述

对用户提供的 222 个 RSS 订阅源进行批量优化，复用 v1（65 源）的成功工作流，并扩展处理更多场景（占位符源、模板源、失效域名迁移等）。

## 核心能力

1. **批量字段补全**：用 Playwright 访问每个源首页，提取 4 个 RECOMMENDED 字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）
2. **失败源深度重试**：对访问失败的源用 14 种技术手段穷尽优化（4种UA+HTTP方法+Wayback+HTTP/1.1+HTTP降级+跟随重定向+长timeout+requests+Session+Playwright+移动UA+端口组合+60s超时+Wayback直接访问）
3. **域名迁移**：对原URL返回小HTML含"备用域名/最新域名获取地址"的源，按5步闭环迁移到新域名
4. **反爬源配置**：对反爬源配置 loginUrl=sourceUrl + enabledCookieJar=true，让用户在App内WebView登录获取Cookie
5. **占位符源处理**：对 sourceUrl 长度<20 的占位符源（68个）进行特殊处理
6. **模板源处理**：对含 `{{}}` 的模板URL源（7个）从模板提取base_url再访问
7. **JSON 类型修复**：boolean字段必须为 true/false（不能是1/0）
8. **skill 反哺**：将本次发现的新陷阱反哺到 legado-source-creator skill 文档

## 输入输出

| 项目 | 路径 |
|------|------|
| 输入JSON | `temp/rss/rssSource_202607131357/rssSource_202607182145..json`（222源） |
| 输出完整版JSON | `output/rss/optimized_v2_full.json` |
| 输出精简版JSON | `output/rss/optimized_v2_lite.json`（移除truly_dead源） |
| 测试报告 | `output/rss/v2_test_report.json` |
| skill反哺文档 | `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md` |

## 文档索引

- [spec.md](./spec.md) - 需求规格（Intent/Scope/Approach/Requirements/Scenarios）
- [design.md](./design.md) - 技术设计（架构决策/数据流/文件变更）
- [tasks.md](./tasks.md) - 任务清单（8阶段执行计划）

## 状态标记

🔄 设计中

## 复用 v1 经验

本次任务复用 v1（65源批量优化）的成功经验：
- 工作流5步闭环（export→optimize→fix→import→verify）
- 14种技术手段穷尽优化
- 域名迁移5步模式
- 反爬源loginUrl配置模式
- JSON boolean字段类型修复（陷阱15）
- 模拟器DNS问题认知（陷阱14）

详见：[batch-optimization-patterns.md](../../../.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md)
