# Tasks：视频播放器画质增强（A 基础 / B 进阶 / B+ 高级 / C 探索）

> 分批实施：**Phase-A（色彩调节·基础档）本次执行**；Phase-B / Phase-B+ 为后续批次，A 期真机验证通过后启动。
> 验证门禁：编译通过（L1）→ 模拟器 L2（S 场景）→ 真机回测（L3）。

## Phase-A：色彩调节（本次实施）

### A0 卡点验证批（A 期开工门禁，对应 design.md 穿透验证清单 K1/K2/K3）✅ 全绿（2026-08-29）

- [x] A0.1 **K1 渲染类型核实** ✅ 无侵入反编译：javap 解包 gsyvideoplayer-java-11.3.0.aar，GSYVideoType `<clinit>` `sRenderType=iconst_0` → 默认 TEXTURE(0)=TextureView；项目 setRenderType 零命中
- [x] A0.2 **K2 ColorFilter 生效性实测** ✅ 临时验证代码（EnhanceTest，已移除 0 残留）：负片 ColorMatrix 应用到播放中 TextureView，MEmu 截图确认画面完全反色 → **生效**；附带实证：GSY 播放状态变化会重置渲染视图（onViewCreated 固定延迟应用 6 秒后失效）→ A1.3 应用时机钩子为必要机制
- [x] A0.3 **K3 失败替代路线预定义** ✅ K2 通过未触发（saveLayer/GL 提前两路线保留在 design 穿透验证清单）
- [x] A0.4 A0 批结论落盘 ✅ design 穿透验证清单 K1/K2 状态更新；实测证据：ai_tests/enhance_test.png（正常）/enhance_test2.png（反色）

### A1 渲染层

- [x] A1.1 新增 `ImageEnhanceController`：四参数合成单一 ColorMatrix（色温→饱和→对比→亮度顺序）+ `apply(TextureView)` 硬件层滤镜 + `reset()` 回退原画 ✅ L1（含 registerPlayerView/applyToRegistered 注册机制供设置面板实时刷新）
- [x] A1.2 `VideoPlayer.kt` 播放视图就绪钩子 ✅ L1（onPrepared post apply，切集/重播均触发；AOAdapt：AOAdapt-1 setSaturation API 名修正）
- [x] A1.3 `VideoFragment` 事件钩子接入 ✅ L1（onFullScreenChanged 进/退 + retryExoPlayback 降级返回 + onViewCreated registerPlayerView；K2 实证 GSY 重置渲染视图→钩子为必要机制）
- [x] A1.4 兜底预案 ✅ 未触发（A0.1/A0.2 全绿，默认已是 TextureView 且滤镜生效）

### A2 设置层

- [x] A2.1 `VideoPlay.kt` 画质参数持久化 ✅ L1（enhanceEnabled/四参数十倍值/enhancePreset；实施顺序调整：存储层先行于 A1 渲染层，AOAdapt-2）
- [x] A2.2 `VideoSettingsPanelContent.kt` 画质增强分区 ✅ L1（总开关+4 EnhanceSliderRow 拖动实时写回+预设 SingleChoiceDialog 联动滑条；Slider 组件 material3）
- [x] A2.3 WebView 降级模式标注 ✅ L1（分区说明常显"仅内置播放器（ExoPlayer）生效，网页播放模式不适用"）
- [x] A2.4 `strings.xml` 画质增强文案 ✅ L1（13 条目）

### A3 验证（Phase-A）

- [x] 3.1 编译门禁 ✅ BUILD SUCCESSFUL 7m13s（AOAdapt-1：setToSaturation→setSaturation API 名修正一次）
- [x] 3.2 模拟器 L2 ✅ 核心场景 PASS（2026-08-29 MEmu）：设置弹框开启画质增强→拖色温滑条 +49.1→关弹框截图暖色滤镜生效（RA2 实时预览）✓；force-stop 重启自动重应用（RA4/onPrepared 钩子）✓；SettingsDialog 不透明 ✓。**AOAdapt-3：L2 首测黑屏根因=播放进度记忆恢复到视频末尾（resume to 300034ms→立即 ENDED），非滤镜问题，换新文件名复测通过**
- [x] 3.3 回归 ✅ 手势/播放核心零改动（静态确认）；AppLog 永久日志仅存留既有模式；无 Log.d/e 新增
- [x] 3.4 测试包构建 + 安装 ✅ debug 包 legado_miss_app_3.26.082920/083000 双轮构建安装实测（082920=A 期画质增强，083000=A 期+样式专项）
- [x] 3.5 文档同步 ✅ updateLog 画质增强+样式条目 / INDEX 状态 / video-player-theme-unify spec 演进记录

### A4 样式专项（2026-08-29 用户指令"优化播放器样式+弹框规范"，子代理盘点后自主实施）

- [x] A4.0 盘点 ✅ 子代理报告：video-player-theme-unify spec 已全部落地被后续超越；剩余 5 缺口（P1 圆角 1 项+P2 卫生 4 项）
- [x] A4.1 `VideoSettingsPanel` BottomSheet 圆角接 `UiCorner.panelRadius`（跟随全局圆角缩放）+ ThemeStore/GradientDrawable import 规范化 ✅
- [x] A4.2 倍速（ChoiceSpeedDialog）/选集（SwitchVideoAdapter）未选中项背景动态取色（fieldSurface=背景混 accent+actionRadius+divider 描边，替换 card_video_background water 色板）✅
- [x] A4.3 集数（RssEpisodeAdapter）/线路（RssRouteAdapter）/章节（ChapterAdapter）悬浮列表对齐悬浮层例外体系：未选中白字+bg_overlay_button，选中 accent 字+accent 20% 透明底（替换静态 primaryText+water 卡片，修复夜间不可读）✅
- [x] A4.4 `card_video_background.xml` 删除（0 引用）；3 个 item XML 移除静态背景引用 ✅
- [x] A4.5 编译 ✅ BUILD SUCCESSFUL 3m41s（AOAdapt-4：SwitchVideoAdapter 误删 R import 一次修正）
- [x] A4.6 模拟器 L2 ✅ BottomSheet 面板不透明+顶部 UiCorner 圆角渲染正常+样式随主题；SettingsDialog 此前已验证不透明

## Phase-B：CAS 锐化 + 降噪（进阶档，中端+；A 期验收后启动）🔄 实施完成（L2 通过；性能门禁挂真机待验 K6）

### B1 依赖与实例

- [x] B1.1 toml + build.gradle 引入 `media3-effect:1.10.1`（对齐既有 media3 版本） ✅ 首次拉取成功
- [x] B1.2 `Exo2MediaPlayer` 新增 internal getter 暴露 `mInternalPlayer` ✅（`exoPlayerInstance: ExoPlayer?`）
- [x] B1.3 `ImageEnhanceEffects.kt` ✅ **方案演进（AOAdapt-5）**：K7 调研实锤 1.10.1 无 SinglePassGlEffect/VideoInfo（原设计伪代码是新版 API）→ 改用 1.10.1 公开效果类**零手写 GL**：锐化=`SharpenEffect : SeparableConvolution`（1D 可分离核 [-k,1+2k,-k]，亮度守恒；ConvolutionFunction1D 连续函数语义参照 GaussianFunction）+ 降噪=`GaussianBlur(sigma)` 现成类；效果链顺序降噪→锐化；档位映射 轻k0.15/中0.30/强0.50、降噪 sigma 0.5/1.0

### B2 效果链

- [x] B2.1 运行时注入 ✅ `ExoVideoManager.applyImageEnhanceEffects()`（playerManager protected→访问链必须在管理器内部，AOAdapt-6）+ `ImageEnhanceController.applyEffectsToPlayer()` 统一入口；**K4 已实现**：全关时 setVideoEffects(空列表) 显式清空
- [x] B2.2 兼容性 ✅ 部分（功能链路全通：档位选择→持久化→onPrepared 注入→播放正常渲染无崩溃无黑屏；SurfaceControl 场景与扩展渲染器命中场景留真机复测）
- [x] B2.3 `VideoSettingsPanelContent` 锐化/降噪档位行 ✅（画质增强分区内，SelectSharpen/EnhanceDenoise 单选弹窗+applyEffectsToPlayer 即时生效）
- [x] B2.4 `DeviceGrade.kt` ⚠️ 简化：B 批不做独立分级文件（档位默认关+用户自选已覆盖低端机保护 RB6 前半）；完整 SoC 分级表移至 B+（超分门禁刚需）——AOAdapt-7

### B3 验证（Phase-B）

- [x] B3.1 编译门禁（L1） ✅ BUILD SUCCESSFUL 3m14s（含 media3-effect 首次拉取）
- [x] B3.2 模拟器 L2 ✅ 档位选择"中"→效果链注入→播放正常渲染（时间码清晰）无崩溃无 FATAL 无黑屏；关档清空逻辑就位（RB3 档位热切换走同一入口）
- [ ] B3.3 性能门禁（RB6）⚠️ 真机待验（K6：模拟器 PC GPU 不代表中端 SoC；锐化视觉量化需高细节视频源）
- [ ] B3.4 测试包 + 真机回测 + 文档同步 ⏳ 待统一打包时合并

## Phase-B+：Anime4K 超分（高级档，中高端+；B 期验收后启动）

### Bp1 超分管线

- [ ] Bp1.1 Anime4K v3 Luma CNN Up 单 pass（M 变体，4x4 卷积）GLSL ES 移植（MIT 协议核实与来源标注）
- [ ] Bp1.2 组合管线：降噪 → CNN 超分 2x → CAS（Effect 链尺寸变更验证，输出 2x 分辨率）
- [ ] Bp1.3 高级档门禁：`DeviceGrade` 旗舰判定（骁龙 8 系/天玑 9 系清单）解锁；未知 SoC 归进阶档 + 手动越级试开（含风险提示）（RB8）

### Bp2 验证（Phase-B+）

- [ ] Bp2.1 旗舰机/模拟器实测：超分后线条/细节增强（SA2 场景 3）；与 A 期色彩调节叠加生效（RB10）
- [ ] Bp2.2 性能门禁（RB11）：≥24fps；Choreographer 掉帧守护 >25% 提示降档（RB9）
- [ ] Bp2.3 真机回测 + 文档同步 + 高级档设备清单沉淀

## Phase-C：探索项（仅登记，不实施）

- [ ] C1 TFLite/NNAPI AI 超分降噪（轻量 CNN + GPU/NPU delegate）可行性预研（RC1）
- [ ] C2 SDR→HDR 逆色调映射（Android 14 UltraHDR 生态依赖评估）（RC2）

## AOAdapt 日志

（实施中遇到问题时记录）
