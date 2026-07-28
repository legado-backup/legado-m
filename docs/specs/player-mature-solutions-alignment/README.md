# 播放器成熟方案对齐 - 项目导航

> **创建时间**：2026-07-26
> **状态**：✅ 设计完成（2026-07-26 用户审查通过） → 🔄 开发中（Phase 1 可观测性+错误反馈闭环）
> **优先级**：P0（用户核心诉求 + 成熟方案短板补齐）
> **来源**：[V2 深度架构分析报告](../player-deep-analysis-20260726-v2.md) + [行业成熟方案查证报告](../../temp-analysis/industry-mature-solutions-verification-report-20260726.md)（49 个权威来源交叉验证）

---

## §1 功能概述

**一句话**：对齐行业成熟方案，补齐播放器核心能力短板，提升视频抓取/播放成功率和图片阅读体验。

### 1.1 背景

V2 深度架构分析（2026-07-26）从架构合理性、效果达成度、成熟方案支撑度三个维度验证播放器体系，结论：

| 维度 | 结论 |
|------|------|
| 设计合理性 | 70% 合理，10% AI 臆想，20% 成熟方案遗漏 |
| 运行稳定性 | 0 崩溃 / 0 ANR / 0 OOM，非阻断站点抓流成功率 89% |
| 核心短板 | 8 个日志实证问题 + 8 个成熟方案遗漏 + 3 个图片用户核心诉求未实现 + 2 个 AI 臆想设计（共 21 项） |

---

## §2 核心能力（5 个 Phase）

### Phase 1：可观测性 + 错误反馈闭环（P0，1-2 天）

- 播放成功埋点（STATE_READY / onRenderedFirstFrame），logcat 可统计播放成功率
- 重试耗尽后发送 videoPlayError 事件 + UI 错误提示，失败不再无感知
- sniffVideoType 双回调竞态修复（AtomicBoolean）
- SniffingMime 日志输出到 logcat，ai_test 可自动化分析

### Phase 2：视频播放器核心能力补齐（P0，2-3 天）

- BandwidthMeter 动态调整缓冲参数（对齐 Android 开发者官方指南）
- 首帧预加载（I-frame，对齐快手官方方案，目标命中率 ≥80%）
- 下一个视频预加载（256KB，对齐抖音官方方案，WiFi 3 个 / 4G 1 个）
- 指数退避重试策略（1s/2s/4s/8s/16s，对齐 hls.js）
- 显式指定 MediaSource 类型（对齐 ExoPlayer 官方建议）

### Phase 3：图片播放器核心诉求补齐（P0，2-3 天）

- 点击图片后切换为左右滚动播放（ViewPager2 + PhotoView，对齐 BigImageViewer）
- 图片金字塔（多分辨率瓦片，对齐微信读书 + SSIV，长图防 OOM）
- 图片适配性最大尺寸展示（极端尺寸处理）
- 图片预加载时机智能判断（结合滚动速度/位置）
- 渐进式加载（JPEG/WebP，先模糊后清晰）

### Phase 4：网络层韧性（P1，1-2 天）

- DoH 绕过 DNS 污染（对齐 Square 官方方案，应对 SNI 阻断/本地 DNS 过滤）
- 302 重定向缓存（自定义 OkHttp Interceptor）
- Cronet 降级阈值宽限期 + 恢复探测
- RSS 正文解析视频型订阅源降级（正文为空不抛异常）

### Phase 5：架构优化（P2，1 天）

- 播放器实例池（3 个实例复用，对齐 GSYVideoPlayer）
- 修正"五级识别链"术语为"三级识别链 + URL 后缀兜底"（对齐 WHATWG 规范）
- L3 URL 后缀检测降级为 Range 请求失败时兜底（对齐 WHATWG 规范）

---

## §3 文档索引

| 文档 | 内容 | 状态 |
|------|------|------|
| [spec.md](./spec.md) | 功能规格（Intent / Scope / Approach / Requirements / Scenarios） | ✅ 已完成 |
| [design.md](./design.md) | 架构设计（技术方案 + 10个ADR Y-Statement + Data Flow + File Changes） | ✅ 已完成 |
| [tasks.md](./tasks.md) | 分阶段任务清单（22个任务+5项验证，含成熟方案参考+验收标准） | ✅ 已完成 |
| [V2 深度架构分析报告](../player-deep-analysis-20260726-v2.md) | 21 项短板清单 + 5 Phase 优化策略 + 验收标准 | ✅ 完成 |
| [行业成熟方案查证报告](../../temp-analysis/industry-mature-solutions-verification-report-20260726.md) | 49 个权威来源交叉验证（70% 真实支撑 / 10% AI 臆想 / 20% 遗漏） | ✅ 完成 |

---

## §4 项目状态

| 阶段 | 状态 | 完成时间 |
|------|------|---------|
| V2 深度架构分析 | ✅ 完成 | 2026-07-26 |
| 成熟方案查证（49 来源） | ✅ 完成 | 2026-07-26 |
| README.md | ✅ 完成 | 2026-07-26 |
| spec.md | ✅ 完成 | 2026-07-26 |
| design.md | ✅ 完成 | 2026-07-26 |
| tasks.md | ✅ 完成 | 2026-07-26 |
| 用户审查 | ✅ 通过 | 2026-07-26 |
| Phase 1 实施 | 🔄 开发中 | — |
| Phase 2-5 实施 | ⏳ 待实施 | — |

**总体状态**：✅ 设计完成 → 🔄 开发中（Phase 1）
