# 画质增强治理修复（总开关失灵 / 预设脱节 / 无长度响应 OOM / 滑条帧级开销）

## 状态

✅ 实施完成（2026-08-30：5 处修复+T6 单测 PASS+L2 自动项 T1/T3 MEmu 实测 PASS 0 FATAL；面板交互项 T2/T4/T5/T7 因模拟器 Compose 无障碍盲区转用户真机手动清单，见 tasks.md AOAdapt）

🔄 设计中（2026-08-30，OpenSpec spec 阶段；基于 commit `6bc9fd98f` 画质增强两期落地后的代码审查结论）

## 功能概述

commit `6bc9fd98f` 落地画质增强 A 期（TextureView Paint 滤镜）与 B 期（CAS 锐化+降噪效果链）后，代码审查发现 4 项缺陷：

1. **[major] 总开关关不掉 B 批锐化/降噪**：总开关 `onCheckedChange` 只调 `ImageEnhanceController.applyToRegistered()`（仅覆盖 A 期滤镜）；B 批 `ImageEnhanceEffects.buildEffects()` 不读 `VideoPlay.enhanceEnabled`，`ExoVideoManager.applyImageEnhanceEffects()` 直接注入，`VideoPlayer` onPrepared 每次重新注入；且关闭后 B 批设置行被隐藏，用户失去唯一档位复位入口——与 `VideoPlay.kt`「关闭时完全回退原画渲染」注释承诺矛盾。
2. **[minor] 滑条调节后预设标签永久脱节**：四个画质滑条 onCommit 只写参数不联动 `enhancePreset=3`（自定义），预设弹框选中项与实际参数永久脱节。
3. **[minor] 无长度响应绕过 OOM 守卫**：`OkHttpStreamFetcher` 小内存跳过解密守卫以 `contentLength > SKIP_DECODE_SIZE_BYTES` 判断，chunked/无长度响应 `contentLength=-1` 绕过守卫仍全量 decode，OOM 防护未闭环。
4. **[minor] 滑条拖动帧级开销**：onValueChange 每帧触发 onCommit → SharedPreferences 落盘 + `ImageEnhanceController.apply()` 每次 new Paint + setLayerType(HARDWARE)，拖动过程硬件层反复重建，低端机卡顿/闪烁风险。

本任务以最小改动闭环 4 项缺陷，总开关治理单点化收敛到效果链构建入口。

## 核心能力

- **总开关单点治理（AD-01）**：`buildEffects()` 开头加开关守卫（关闭即返回空列表），覆盖 onPrepared 重注入 / 弹框 / 未来所有调用方；总开关切换补调 `applyEffectsToPlayer()` 立即作用于当前播放实例，无需重播
- **滑条联动自定义预设（AD-02）**：四个画质滑条 onCommit 联动 `enhancePreset=3`，预设标签与实际参数永不脱节
- **无长度响应有界缓冲（AD-03）**：contentLength 未知（-1）且小内存时增量读取至阈值上限缓冲，超限拼接透传（不解密）、未超限走 decode，内存峰值 ≤ SKIP 阈值与现状等价，OOM 防护闭环
- **Paint 缓存 + 参数指纹短路（AD-04）**：单例缓存 Paint 与四参数指纹（亮度/对比度/饱和度/色温），参数未变跳过重建与 setLayerType，参数变化复用同一 Paint 更新 colorFilter，消除拖动帧级硬件层重建

## 文档索引

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 功能概述 + 状态 + 索引 |
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：ADR/数据流/文件变更（待产出） |
| [tasks.md](./tasks.md) | 任务清单（待产出） |

## 关联 spec

- 前置：[video-player-image-enhance](../video-player-image-enhance/README.md) —— 画质增强 A/B 两期主 spec，本任务修复其落地后的缺陷；沿用 RA2「参数拖动即时生效（实时预览）」规格与 K4 清空语义
- 关联：[sniff-regression-rss-image-crash](../sniff-regression-rss-image-crash/README.md) —— 其 H3 修复引入小内存 >10MB 跳过解密透传守卫（`OkHttpStreamFetcher`），本任务补齐其无长度响应绕过分支
