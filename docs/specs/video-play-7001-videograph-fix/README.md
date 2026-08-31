# 修复内置视频播放器切视频 7001 渲染管线崩溃（media3 VideoGraph 回归）

> 状态：✅ 已完成（2026-08-31 17:2x，S1-S4 全过，用户验收"全过，收尾闭环"）

## 功能概述

修复合集/切视频场景下内置视频播放器的 `ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED(7001)` 崩溃回归：第一个视频总能正常播放，上滑切到第二个/第三个视频时首帧渲染成功（约 2307ms）后立即崩溃（`VideoFrameProcessingException` / `Presentation.createForWidthAndHeight(-1,-1)`）。用户真机 + 模拟器双确认。

> **根因一句话**：画质增强 feature 无条件注入 `setVideoEffects(emptyList())`（空列表也非 null）→ 激活 media3 GL VideoGraph 管线 → GSY 裸 Surface attach 发送负分辨率哨兵 `(-1,-1)` → renderer 只挡 0 不挡 -1 直通 GL 管线 → 首帧 `Presentation.createForWidthAndHeight(-1,-1)` 抛异常 → 7001。

根因已通过 **media3 1.10.1 源码反编译逐行实锤**（非推测），完整证据链见分析报告。三要素缺一不崩：media3 1.10.1 语义（非 null 即管线）× 无条件空列表注入（6bc9fd98f 画质增强）× PlayerInstancePool 池复用放大（ac5a0a8aa）。本次 openfix（video-sniff-403-and-rss-classic-fix，DoH/auth-retry/switchToken/HlsKeyDataSourceFactory）全在网络会话层，**明确排除**与 7001 的引入关系。

## 核心能力：A+B+C 三件套（无依赖/反射改动，3 文件）

| # | 改动 | 文件 | 作用 |
|---|------|------|------|
| **A** | 守卫零注入：`effects.isEmpty()` 时 `return`，绝不调用 `setVideoEffects` | `ExoVideoManager.kt` L120 | 增强关闭时零注入，`videoEffects` 保持 null → 永走 legacy 直渲路径，**结构性根除** GL 管线激活 |
| **B** | 池污染隔离：`tainted` 标记，注入过 effects 的实例 recycle 时用完即毁不入池 | `PlayerInstancePool.kt` | 池内零污染，杜绝复用放大（`videoEffects` 字段跨实例复用不重置） |
| **C** | 7001 重建兜底：release 当前实例 + acquire 新实例 + 重绑，按降级链重试 | `Exo2MediaPlayer.kt` L835-870 | 替换无效的"反射清 effects + 同实例重试"（必败死循环），GL 管线随 `release()` 真正销毁 |

**已知影响**：增强开启用户（非默认态，`enhanceEnabled` 默认 false）主动 `setVideoEffects` 仍走 VideoGraph；若增强开启态触发 7001（负分辨率哨兵 bug 对所有 GL 管线生效），由 C 重建实例兜底。A 修复覆盖绝大多数用户。

## 分析报告索引

| 报告 | 内容 |
|------|------|
| [media3-videograph-analysis-20260831.md](../../temp-analysis/media3-videograph-analysis-20260831.md) | media3 1.10.1 VideoGraph 管线机制源码逐行分析（onEnabled L935-943 / 负分辨率哨兵链路 / 禁用方法全评估 / A+B+C 方案详案） |
| [video-7001-regression-20260831.md](../../temp-analysis/video-7001-regression-20260831.md) | 7001 回归根因闭环（git 提交时间线 / 三要素角色裁决 / 本次 openfix 影响排除 / 字节码级反编译证据） |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent、Scope、Approach、Requirements R-7001-1~6、Scenarios S1-S4） |
| [design.md](./design.md) | 技术设计（根因链详述、A/B/C 改动详案、AD-01~04 架构决策、Data Flow、File Changes、回归风险） |
| [tasks.md](./tasks.md) | 实施任务清单（分析 / 实施 / 验证 / AOAdapt 日志） |

## 验证策略

- **编译门禁**：`./gradlew compileAppDebugKotlin` → `build-legado.bat` 测试包 → `stop-daemons.bat` 清场。
- **L2 真机核心判据**：增强关闭（默认态）连滑 3 个视频全部正常播放、无 7001、无黑屏。
- **辅助判据**：
  1. 增强开启态连滑不崩（若 7001 触发则验证 C 分支重建日志 + 自动续播成功）；
  2. 池卫生日志验证（`tainted instance released instead of pooling`，后续 acquire 均为 miss 新建）;
  3. 正常单视频播放零回归（`videoEffects==null` 走 legacy 路径行为不变）。
- **配套**：updateLog 基于 git diff 更新（编译前强制）、Grep 无调试日志残留、文档同步。

## 验证记录

| 时间 | 包 | 场景 | 结果 |
|------|-----|------|------|
| 2026-08-31 16:5x | 083116（MEmu） | S1 默认态连播 3 视频 | ✅ 全过：logcat 0×7001，video2/video3 均 `acquire hit (reuse)` 正常播放，无 markTainted（守卫生效预期）；用户确认"三个都能播，修复生效" |
| 2026-08-31 17:1x | 083117（MEmu） | S2/S3 增强开启回归 | ✅ 全过：无崩溃，logcat 缓冲 0×7000 族错误、HLS 加密流 key 请求正常；用户验收"全过，收尾闭环" |

> 补记（17:1x）：用户真机日志（083112 之前旧包）复核实锤"问题依旧"系旧包不含修复；083116 dex 扫描 markTainted=3 实锤修复在包内。C 分支首轮实现（同实例重试）与 design 2.3.4 矛盾，083117 已补齐为全量重建（markTainted+clear+detach+recycle 即毁+acquire 全新实例重绑+同类型重试，MAX_7001_REBUILD=2 防循环超限走降级链）。
