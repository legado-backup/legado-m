# 依赖升级性能优化

> 🔄 设计中 — 等待用户审核

## 功能概述

深度分析 Legado 项目所有依赖的升级潜力，识别升级后能带来**显著性能提升**且**不影响现有功能**的依赖项，制定分优先级的升级方案，并将 minSdk 从 21 提升至 23 以解锁 AndroidX 生态升级路径。

## 核心能力

- 📊 全量依赖扫描与版本比对（74+ 依赖项）
- 🔒 锁定依赖排除分析（jsoup/rhino/hutool/protobuf 4 项硬锁定；commons-text 待验证解锁）
- ⚡ 性能增益量化评估（协程 Channel 9.8x、OkHttp 拦截器增强、Media3 ExoPlayer 优化等）
- 🛡️ 升级风险评估（7 组依赖经 3 个并行子代理深度源码验证）
- 📋 分优先级可执行升级清单（P0/P1/P2 三层渐进）
- 🔧 WebView 性能优化（代码层修复，非依赖版本问题）
- 📱 minSdk 21→23 迁移（解锁 AndroidX 1.12+/1.9+ 升级路径）

## 关键决策

| 决策 | 结论 | 说明 |
|------|------|------|
| minSdk 21→23 | ✅ 确认 | 释放 lifecycle/activity/fragment/core/material/media3/firebase 升级路径；影响 <1% 用户 |
| webkit 1.14→1.16 | ⚠️ 阻断 | webkit 1.16.0 要求 minSdk≥24（非 23），暂不可升级 |
| commons-text 1.13.1 | ⚠️ 待验证 | minSdk→23 后 desugaring 是否正确处理 Arrays.setAll 需真机验证 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求意图、范围、方案选择、替代方案、场景 |
| [design.md](./design.md) | 技术方案、升级矩阵、架构决策、文件变更 |
| [tasks.md](./tasks.md) | 分阶段任务清单 |

## 状态标记

🔄 设计中 → 待用户审核（深度分析已完成，等待检查点 1 通过）
