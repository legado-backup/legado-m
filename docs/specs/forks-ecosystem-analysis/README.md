# 阅读M 功能借鉴与整体实施（forks-ecosystem-analysis）

> **项目代号**：forks-ecosystem-analysis
>
> 基于对 [阅读·全版本集散地](https://momoa.cc.cd/下载/xz) 的 **17 个 Legado 直系 fork** 源码实测分析（`analysis-report.md`），筛选出**可落地的优化功能点**（`borrow-decisions.md`），本四文档负责这些功能点的**整体实施落地设计**。

## 功能概述

本项目分两阶段：

**阶段一（已完成）——生态分析**：更新+补齐 17 个 fork 仓库基线，按 9 大功能领域（排除 UI）深度分析，产出 `analysis-report.md`（分析报告）+ `borrow-decisions.md`（三态决策矩阵）。

**阶段二（本四文档支撑）——实施落地**：将决策矩阵中的 **Borrow 15 项 + 可选 Evaluate 项** 转化为可执行的技术设计、架构决策与任务清单，分阶段落地到本项目源码。**AI 集成（Rimchars Agent / Jingshiro 助手 / NG MCP / HapeLee 云TTS）按用户指示暂不接入**。

## 文档索引

| 文档 | 类型 | 说明 |
|------|------|------|
| [spec.md](./spec.md) | OpenSpec 实施 | Intent/Scope/Requirements/Scenarios（要落地什么） |
| [design.md](./design.md) | OpenSpec 实施 | Technical Approach/ADR/Data Flow/File Changes（怎么落地） |
| [tasks.md](./tasks.md) | OpenSpec 实施 | 分阶段任务清单 + AOAdapt 日志（落地动作） |
| [analysis-report.md](./analysis-report.md) | 分析参考 | 17 仓库版本基线 + 9 大功能领域汇总分析（本项目的输入事实） |
| [borrow-decisions.md](./borrow-decisions.md) | 分析参考 | 三态决策矩阵（Borrow 15 / Evaluate 13 / Not 15），四文档的功能点清单来源 |

## 实施路线概览

| 阶段 | 功能点 | 目标 |
|------|--------|------|
| **阶段 A：网络层+规则引擎**（P0，低风险纯增量） | B1 CryptoJS 内置 · B2 Brotli（OkHttp 通道）· B3 resolveIp 兼容 · B4 网络日志 | 提升规则引擎加密能力与网络诊断能力 |
| **阶段 B：数据安全**（P1） | B5 搜索存储上限 · B6 书源 URL 迁移 · B7 规则回收站 | 防崩溃 + 数据防丢失 |
| **阶段 C：阅读/稳定性增强**（P1-P2） | B8 特殊内容保护 · B13 内存压力监控 · B9 书架进度 | 阅读体验 + 低内存稳定性 |
| **阶段 D：优化补缺**（P2） | B11 缓存分项统计 · B12 缓存并发率 · B14 WebDAV 删除重命名 · B15 高亮捕获组样式 · B16 想法批注导出 | 功能补齐 |
| **评估项**（Evaluate，需专项评估） | E1 视频无缝过渡 · E2 纯 JS 书源引擎 · E3 智能分组 · E4 会话级阅读记录 等 | 价值高但改动大，单独立项 |

> **本项目生态定位提醒**：订阅源视频/图片播放器嗅探、自动滚动/连续播放、内置播放器优化均为**生态领先**（已在 analysis-report 领域 6/7 核实），不在借鉴范围内。

## 关联文档

| 文档 | 说明 |
|------|------|
| [forks_comparison_methodology.md](../../project-rules/forks_comparison_methodology.md) | 延伸版本对比方法论 |
| [forks-reference.md](../../project-rules/forks-reference.md) | 组件优化/功能借鉴方法论（实施阶段 B 遵循） |
| [forks-archive-comparison](../forks-archive-comparison/) | 阅读 Archive 深度对比（前期成果） |
| [legados-forks-comparison](../legados-forks-comparison/) | GEd520/legados fork 集成方案 |

## 状态标记

| 阶段 | 状态 |
|------|------|
| 需求分析 | ✅ 完成（仅直系 fork + 汇总式） |
| 生态分析（阶段一） | ✅ 完成（17 仓库基线 + 9 领域分析 + 决策矩阵） |
| 四文档生成（阶段二） | ✅ 完成（本四文档为实施落地设计） |
| 用户审查（检查点2） | 🔄 复核后重提 |
| 用户最终验收（检查点3） | ⬜ 待验收 |
| 功能点实施 | 🔄 阶段D完成（B12/B14/B15/B16 已实施，单测+编译全过，真机验证已执行通过；B14 云端删除/重命名待用户 WebDAV 环境） |
