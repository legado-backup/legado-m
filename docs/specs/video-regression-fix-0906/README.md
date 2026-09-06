# video-regression-fix-0906（真机回归四问题：嗅探播放下滑/书源切布局/书源上滑/分类列表页三点）

## 状态
**开发完成（L2 真机验证通过，待用户验收）**（2026-09-06）

## 功能概述
用户真机（最新测试包）实测反馈 4 个问题，日志（45 文件）+ 源码双路定位根因：

1. **嗅探/播放能力下滑**：复合根因——ExoPlayer 4003 解码失败（MediaCodec Released 竞态）+ token 竞态丢弃嗅探回调（22 次）+ DoH server#2 全程死亡（UnknownHostException 99 次）+ 同 token 重复 startPlay。修复解码失败兜底与 DoH 熔断，优化嗅探复用。
2. **书源切布局不立即生效**：切布局后书源全量重采集死窗；修复=已解析 URL 短路重采集。
3. **书源上滑失效（真回归）**：AD-01 单页化禁滑后，手势层依赖的 VideoPlaylistHolder 队列在详情页直进等入口未注入 → switchToBookFromList 静默失败。修复=补齐队列兜底注入+静默路径可观测+集内降级。
4. **分类列表页三点死按钮**：ExploreShowActivity（Mode.SUB）moreButton 宿主从未接线。修复=接线 ModernActionPopup 收纳"第 N 页"跳页并删除三横线按钮。

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格 |
| [design.md](./design.md) | 技术设计（ADR/文件变更） |
| [tasks.md](./tasks.md) | 任务清单 |

## 变更日志
| 日期 | 变更 |
|------|------|
| 2026-09-06 | 初版设计（扩展路径，日志 45 文件脱敏分析 + 3 路源码探索支撑） |
