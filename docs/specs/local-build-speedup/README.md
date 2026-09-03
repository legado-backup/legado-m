# 本地打包提速（local-build-speedup）

> 状态：🔄 开发中——实施完成，R1/3.5 补测待并行会话合并后执行（✅ 设计完成：基线实测支撑 + 红队 2 轮通过，2026-09-03）

## 功能概述

将日常本地打包耗时从 **7.5~10.5 分钟压缩到 ≤4 分钟**（目标 2~3 分钟），同时控制打包过程内存峰值，并保持内存安全兜底机制。纯构建链路优化，零业务代码侵入，不产生任何面向用户的 APK 功能变化。

## 背景与基线数据（2026-09-03 实测）

| 场景 | 耗时 | 系统内存峰值 | java 进程合计峰值 |
|------|------|-------------|------------------|
| 日常增量打包 | 7m33s | 93.5% | 7.59GB |
| clean 全量（历史日志） | 10m39s | 未采样 | 估 ~9GB |
| 打完包驻留 | — | 61~67% | 仅 0.5GB |

峰值构成：Gradle 主进程 4.4GB + Kotlin daemon 2.1GB + 子进程 1.1GB ≈ 7.6GB；**非 java（模拟器+IDE+系统缓存）~22GB 才是内存大头（69%）**。

三大根因（互相叠加）：
1. `build-legado.bat` 每次打包前删除 Kotlin daemon 缓存 + `--stop` → Kotlin 增量快照丢失，`compileAppDebugKotlin` 每次准全量重编（最大耗时大头）
2. `--no-daemon` 打包 → Gradle 冷启动 + configuration 全跑 + JIT 冷启动
3. `org.gradle.caching=false`、`configuration-cache=false`（历史注释"enable cache can not up app version"——根因已定位：版本号时间戳在**配置期**求值，CC 复用后版本号不更新；ValueSource 可解）

## 核心能力

- **P1 daemon 复用**：bat 去掉打包前清缓存/`--stop`/`--no-daemon`，靠已有限幅（Xmx4g×2 + 10min 空闲自退）保内存
- **P1b 分场景降堆**：debug 打包注入 Gradle 3g + Kotlin 3g，release 保持 4g（R8 OOM 防回归）
- **P2 configuration cache**：版本号 `releaseTime()`/`gitCommits` 改 ValueSource 执行期求值 + 开启 CC
- **P4 parallel**：3 模块（`:app`/`:modules:book`/`:modules:rhino`）并行
- **内存观测**：bat 打包前后输出系统内存与 java 进程 RSS 一行摘要
- **P3 build cache（二期评估）**：三包切换场景复用，本期暂缓

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach / Requirements / Scenarios |
| [tasks.md](./tasks.md) | 分级任务清单（含验证标准） |

## 变更日志

- 2026-09-03：创建，基线实测完成，设计完成进入开发
