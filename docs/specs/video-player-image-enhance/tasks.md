# Tasks：视频播放器画质增强（A 基础 / B 进阶 / B+ 高级 / C 探索）

> 分批实施：**Phase-A（色彩调节·基础档）本次执行**；Phase-B / Phase-B+ 为后续批次，A 期真机验证通过后启动。
> 验证门禁：编译通过（L1）→ 模拟器 L2（S 场景）→ 真机回测（L3）。

## Phase-A：色彩调节（本次实施）

### A0 卡点验证批（A 期开工门禁，对应 design.md 穿透验证清单 K1/K2/K3）

- [ ] A0.1 **K1 渲染类型核实**：反编译 carguo fork 11.3.0 库核实 `GSYVideoType` 渲染类型默认值 + 播放器运行时打印 `getShowView()` 实际类型；若默认 SurfaceView → 评估 `GSYVideoType.setRenderType(TEXTURE_TYPE)` 切换成本（全屏/旋转/双指缩放回归 + 性能）并向用户汇报决策
- [ ] A0.2 **K2 ColorFilter 生效性实测**：最小改动在 MEmu 模拟器实测 TextureView `LAYER_TYPE_HARDWARE` + ColorMatrixColorFilter 对播放内容的实际效果（先于全部功能开发）
- [ ] A0.3 **K3 失败替代路线预定义**：若 A0.2 失败，评估 ① 自定义 TextureView 覆写 draw + `canvas.saveLayer(paint)` ② GL 管线提前（B 期工作重排），结论汇报用户决策后再继续
- [ ] A0.4 A0 批结论落盘（tasks AOAdapt + design 卡点清单状态更新），全绿后放行 A1 渲染层开发

### A1 渲染层

- [ ] A1.1 新增 `ImageEnhanceController`：四参数合成单一 ColorMatrix（色温→饱和→对比→亮度顺序）+ `apply(TextureView)` 硬件层滤镜 + `reset()` 回退原画
- [ ] A1.2 `VideoPlayer.kt` 播放视图就绪钩子：`surface_container` 遍历 TextureView 后应用滤镜（GONE→attach 完成时序验证）
- [ ] A1.3 `VideoFragment` 事件钩子接入：`onFullScreenChanged` / 切集数（`updateEpisodeList` 播放回调）/ 切线路 / WebView 降级返回后重新应用
- [ ] A1.4 兜底预案（仅 A0.2/A1.2 实测异常时启用）：反编译核实 fork 库 RenderViewFactory API，注册自定义 TextureView

### A2 设置层

- [ ] A2.1 `VideoPlay.kt` 新增持久化属性：`enhanceEnabled`（Boolean）/ `enhanceBrightness` / `enhanceContrast` / `enhanceSaturation` / `enhanceColorTemp`（Int 十倍值）/ `enhancePreset`
- [ ] A2.2 `VideoSettingsPanelContent.kt` 新增"画质增强"分区：总开关 + 亮度/对比度/饱和度/色温 4 滑条（拖动即写回+实时预览）+ 预设单选（原画/护眼/鲜艳/自定义，应用后滑条联动）
- [ ] A2.3 WebView 降级模式分区标注"仅 ExoPlayer 引擎生效"
- [ ] A2.4 `strings.xml` 新增画质增强文案

### A3 验证（Phase-A）

- [ ] A3.1 编译门禁 `compileAppDebugKotlin`（L1）
- [ ] A3.2 模拟器 L2：护眼预设暖色生效+滑条实时预览（SA1）；全屏/切集/切线路滤镜保持（SA4）；总开关关闭回退原画；重启参数保持
- [ ] A3.3 回归：手势体系/播放核心零影响；`error_patterns` 场景 4 种错误模式 0 出现；Grep 无调试日志残留
- [ ] A3.4 测试包构建 + 安装（与 video-player-ux-fixes L2 验证合并回归）
- [ ] A3.5 文档同步：updateLog / INDEX / ui-standards（如 ColorFilter 经验值得沉淀）

## Phase-B：CAS 锐化 + 降噪（进阶档，中端+；A 期验收后启动）

### B1 依赖与实例

- [ ] B1.1 toml + build.gradle 引入 `media3-effect:1.10.1`（对齐既有 media3 版本）
- [ ] B1.2 `Exo2MediaPlayer` 新增 internal getter 暴露 `mInternalPlayer`
- [ ] B1.3 `ImageEnhanceEffects.kt`：CAS 锐化 GlEffect（AMD FidelityFX 核心 ~40 行 GLSL ES 3.0 移植，sharpness 0.3/0.6/0.85 档位映射）+ 轻量双边降噪 GlEffect（亮度域 5x5）+ 效果链组装（pass 顺序：降噪→锐化）

### B2 效果链

- [ ] B2.1 运行时注入：`exoPlayer.setVideoEffects(...)` 热更新封装（复用实例生效验证，RB3）；**档位=关时显式 `setVideoEffects(emptyList())` 清空残留（K4，池化实例跨会话防效果残留）**
- [ ] B2.2 兼容性实测：API 29+ SurfaceControl 路径与 GL pipeline 冲突检测；冲突时强制 TextureView 渲染 + 设置页提示（RB5）
- [ ] B2.3 `VideoSettingsPanelContent` 新增锐化/降噪档位行（关/轻/中/强，默认关）
- [ ] B2.4 `DeviceGrade.kt` SoC/GPU/RAM 分级检测（进阶档门槛：GLES 3.0+、非 lowRam）

### B3 验证（Phase-B）

- [ ] B3.1 编译门禁（L1）
- [ ] B3.2 模拟器 L2：低码率视频锐化"中"档清晰度提升且平坦区无噪点放大（SA2）；档位热切换无需重建播放器（RB3）；关档回退原画
- [ ] B3.3 性能门禁（RB6）：各档位帧率实测 ≥ 24fps；`error_patterns` 0 出现
- [ ] B3.4 测试包 + 真机回测 + 文档同步

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
