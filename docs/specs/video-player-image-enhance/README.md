# 视频播放器画质增强（A 基础 / B 进阶 / B+ 高级 / C 探索）

## 状态

✅ A 期+样式专项实施完成（2026-08-30 用户验收通过；编译门禁×2 + 模拟器 L2 PASS；K1/K2 穿透验证全绿）→ 🔄 Phase-B 开发中（CAS 锐化+降噪）

## 功能概述

对标成熟播放器软件（MX Player / VLC / Infuse），为内置视频播放器（GSY 壳 + ExoPlayer 内核，TextureView 渲染）新增画质增强能力，按设备能力分级渐进交付：

- **A 期·基础档（全机型）**：亮度 / 对比度 / 饱和度 / 色温（含护眼预设）实时调节，TextureView ColorFilter 硬件层实现，零帧率开销
- **B 期·进阶档（中端+）**：CAS 自适应锐化（AMD FidelityFX，MIT）+ 轻度降噪，Media3 Effect GL 管线，档位化
- **B+·高级档（中高端+）**：Anime4K v3 轻量 CNN 超分 2x（M 变体，MIT）+ CAS 组合管线，SoC/GPU 定级门禁 + 掉帧守护
- **C 期（仅登记）**：TFLite/NNAPI AI 超分降噪、SDR→HDR

## 核心能力

- 画质增强设置面板（`VideoSettingsPanelContent` 新增分区），参数持久化 `video_config` prefs，跨会话记忆
- A 期参数拖动即时生效（滑条实时预览），无需重启播放器
- 档位化增强（锐化/降噪/超分），`DeviceGrade` 设备自动定级 + 运行时掉帧守护降档提示
- WebView 降级引擎自动规避（UI 明确标注仅 ExoPlayer 引擎生效）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：架构决策（ADR）/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单（A 期 Phase-A / B 期 Phase-B 分批）+ AOAdapt 日志 |

## 关联任务

- 前置：`video-player-ux-fixes`（灵敏度设置已建立 `VideoSettingsPanelContent` 设置行 + `video_config` 持久化模式，本任务直接复用；该任务 L2 验证暂停中，测试包 `legado_miss_app_3.26.082910.apk` 已装机）
