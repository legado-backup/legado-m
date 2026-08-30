# 依赖升级性能优化

> ✅ 实施完成 — Phase 0~3 代码修改+文档同步已全部完成

## 功能概述

深度分析 Legado 项目所有依赖的升级潜力，识别升级后能带来**显著性能提升**且**不影响现有功能**的依赖项，制定分优先级的升级方案，并将 minSdk 从 21 提升至 23 以解锁 AndroidX 生态升级路径。

## 核心能力

- 📊 全量依赖扫描与版本比对（74+ 依赖项）
- 🔒 锁定依赖排除分析（5 项硬锁定：jsoup/rhino/hutool/commons-text/protobuf）
- ⚡ 性能增益量化评估（协程 Channel 9.8x、Lifecycle 2.11 内存优化、Media3 ExoPlayer 优化等）
- 🛡️ 升级风险评估（6+4 个并行子代理深度源码验证 + 多轮交叉审查）
- 📋 分优先级可执行升级清单（P0/P1/P2 三层渐进）
- 🔧 WebView 性能优化（代码层修复，非依赖版本问题）
- 📱 minSdk 21→23 迁移（解锁 AndroidX 1.12+/1.9+ 升级路径）

## 关键决策

| 决策 | 结论 | 说明 |
|------|------|------|
| minSdk 21→23 | ✅ 确认 | 释放 activity/material/media3 升级路径；影响 <1% 用户 |
| core | ⏸️ 回退到 1.18.0 | 1.19.0 要求 compileSdk 37 + AGP 9.1+，当前环境不支持 |
| lifecycle | ⏸️ 保持 2.9.4 | 2.11.0 要求 compileSdk 37 + AGP 9.1+，当前环境不支持 |
| OkHttp | ✅ 升级到 5.4.0 | 迁移 4 处 internal API 为公共实现，1 处保留并标注风险 |
| fragment | ⏸️ 保持 1.8.9 | 1.9.0 仅有 alpha 版，当前为最新稳定版 |
| webkit 1.14→1.16 | 🔴 阻断 | webkit 1.16.0 要求 minSdk≥24 |
| commons-text 1.13.1 | 🔴 硬锁定 | Arrays.setAll 需 API 24+，desugaring 不覆盖 |
| Room | ⏸️ 保持 2.7.1 | 2.7.2 不存在，2.8.4 有 KMP 架构变更风险，后续单独评估 |
| AppCompat | ✅ 已最新 | 1.7.1 已是 1.7.x 最新稳定版，无需操作 |
| Glide 5.0.5 | ✅ 已最新 | 无需操作 |
| shouldInterceptRequest 缓存 | 🟡 降为 P2 | 风险较高（过滤绕过、缓存一致性、线程阻塞），延后实施 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求意图、范围、方案选择、替代方案、场景 |
| [design.md](./design.md) | 技术方案、升级矩阵、架构决策（17 项 AD）、文件变更 |
| [tasks.md](./tasks.md) | 4 Phase + P2 任务清单 |

## 状态标记

🔄 设计中 → 🛑 检查点 1：等待用户审核后开始实施
