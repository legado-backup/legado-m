# Spec：视频播放器画质增强（A 基础 / B 进阶 / B+ 高级 / C 探索）

## Intent

让内置视频播放器具备成熟播放器软件的画质增强能力：用户可实时调节画面色彩（亮度/对比度/饱和度/色温），并按设备能力分级获得 CAS 锐化、降噪与实时超分等增强效果，改善低码率订阅源视频的观感。在不破坏现有播放核心与手势体系的前提下，按"基础档（全机型）→ 进阶档（中端+）→ 高级档（中高端+）"分级渐进交付。

## Scope

**做什么**：

- **A 期（本次实施优先）**：色彩调节四参数（亮度/对比度/饱和度/色温）+ 预设（护眼/暖色/冷色/原画），TextureView ColorFilter 实时渲染；设置面板分区 UI + 滑条实时预览 + `video_config` 持久化
- **B 期（二期专项）**：CAS 自适应锐化（AMD FidelityFX，MIT）+ 轻度降噪，档位化（关/轻/中/强）；补 `media3-effect` 依赖；`Exo2MediaPlayer` 暴露 ExoPlayer 实例 getter；GL 渲染链与 SurfaceControl 路径兼容性实测
- **B+（高级档，中高端解锁）**：Anime4K v3 轻量 CNN 超分 2x（M 变体单 pass，MIT）+ CAS 组合管线，输出 2x 分辨率；SoC/GPU 设备定级检测门禁 + Choreographer 掉帧守护
- **C 期（仅登记不实施）**：TFLite/NNAPI AI 超分降噪、SDR→HDR 实时转换

**不做什么**：

- 不做 Real-ESRGAN/waifu2x 等重型模型实时超分（推理开销超出移动端实时预算）
- 不做 MEMC 插帧（软件光流补偿开销极重，旗舰机有系统级方案）
- 不做 HDR 色调映射 UI（C 期探索后再议）
- 不改 WebView 降级引擎的渲染（网页内 video 无法介入，UI 标注不适用）
- 不动手势体系（上下滑切视频/左右滑 seek/长按倍速/双击暂停）
- 不改播放核心缓冲/嗅探/缓存链路

## Approach

### Selected Approach

**总体架构**：三级档位 + 设备自动定级——基础档（A 期，全机型，ColorFilter）→ 进阶档（B 期，中端+，CAS+降噪 GL Effect）→ 高级档（B+，中高端+，Anime4K CNN 超分+CAS 组合管线）；`DeviceGrade` 静态 SoC/GPU 检测定级 + Choreographer 运行时掉帧守护。

**A 期（色彩调节）**：

1. TextureView `setLayerType(LAYER_TYPE_HARDWARE, Paint(ColorMatrixColorFilter))`，四参数合成单一 `ColorMatrix`（色温→饱和→对比→亮度）
2. `VideoPlay` 新增持久化参数（Int 十倍值复用既有模式）
3. `VideoSettingsPanelContent` 新增"画质增强"分区：总开关 + 4 滑条 + 预设单选；变更即写回 + 即时刷新
4. `VideoFragment`/`VideoPlayer` 播放视图就绪后应用滤镜；全屏/切集/切线路/降级返回后重新应用

**B 期（CAS 锐化+降噪）**：

1. toml + build.gradle 补 `media3-effect:1.10.1`
2. `Exo2MediaPlayer` 新增 internal getter 暴露 `mInternalPlayer`
3. 运行时 `exoPlayer.setVideoEffects(降噪 → CAS)`（pass 顺序先除噪再锐化）；自定义 `GlEffect`（GLSL ES 3.0 移植 CAS 核心 ~40 行）
4. 兼容性实测：API 29+ `SurfaceControl` 路径冲突时强制 TextureView 渲染

**B+（Anime4K 超分高级档）**：

1. Anime4K v3 Luma CNN Up 单 pass（M 变体，4x4 卷积）+ CAS 组合 2 pass，输出 2x 分辨率（Effect 链原生支持尺寸变更）
2. `DeviceGrade` SoC/GPU 分级检测：旗舰解锁高级档，未知 SoC 归进阶档可手动越级
3. 性能门禁：各档位实测 ≥24fps 方可交付

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| SurfaceView 渲染 + SurfaceControl | SurfaceView 非 View 体系，无法用 ColorFilter 介入；B/B+ 期 Effects 走 GL+SurfaceTexture，TextureView 是共同最优载体 |
| B 期用 PlayerInstancePool.acquire 时 Builder 注入 effects | 池复用分支（L123-130）直接 return 旧实例不重建，新效果不生效；运行时 `player.setVideoEffects` 是公开 API，天然支持复用实例 |
| 锐化用固定系数 USM | 平坦区放大压缩噪点；CAS 局部对比度自适应，效果与噪声表现显著更好，且单 pass 开销同级 |
| 实时超分选 Real-ESRGAN/waifu2x/TFLite 重型模型 | 推理 10ms+/帧超出移动端实时预算（Anime4K 官方对比实测：FSRCNNX/Anime4K 可实时，waifu2x/Real-ESRGAN 不可）；TFLite 方案登记 C 期探索 |
| Anime4K 旧版 monolithic shader 或 v4 多 pass 组合 | v3 模块化 M 变体是速度/质量平衡点；v4 多 pass 组合 GPU 开销翻倍，旗舰也吃紧 |
| HDR 色调映射 UI | ExoPlayer 内置 tonemap 仅对 HDR 源有效，订阅源绝大多数 SDR；SDR→HDR 逆映射登记 C 期 |
| 色彩调节用自定义 GL shader（提前上 GL 链） | A 期目标是"全机型零风险立即可用"，ColorMatrix 走系统硬件合成零开销；GL 链留给 B 期与锐化一并验证 |
| 画质参数存 AppConfig | 视频设置统一在 `video_config` prefs（既有模式），AppConfig 无视频 key，跨处存储制造分裂 |

### Drawbacks

- **K1（最高危，A0 门禁）**：GSY fork 默认渲染类型未穿透验证（`mTextureView` 为历史命名 RenderView 包装，L865 SurfaceView 兜底分支是反证信号）——若默认 SurfaceView，ColorFilter 方案整体不适用，需先切 `setRenderType(TEXTURE_TYPE)` 并回归行为差异，或改走 GL 提前
- **K2/K3（A0 门禁）**：TextureView 硬件层 ColorFilter 对 SurfaceTexture 内容生效性未实测；失败替代路线（软件层 saveLayer / GL 提前）已预定义，A0 批全绿才开工 A1
- **A 期**：色温用 RGB 矩阵近似，非专业色准调节；GSY 内部重建渲染视图时序依赖容器遍历+实时查找兜底
- **B 期**：media3 Effect 强制 GL 渲染链，与 API 29+ SurfaceControl 路径存在兼容风险（预案：检测 + 强制 TextureView）；池化实例需显式清空 effects（K4 已入任务）；GlEffect API 签名以 1.10.1 源码为准（K7）
- **B/B+ 期**：Effect 管线引入 ~1 帧显示延迟；GL 链内存峰值上升；性能门禁需真机（K6，模拟器仅验功能）
- **B+ 期**：Anime4K 对 720p/480p 低分辨率源非最优（官方定位原生 1080p）；Effect 输出 2x 与 SurfaceTexture buffer 兼容性待实测（K5，预案：末尾下采样回原尺寸）；设备分级表需持续维护；越级试开可能掉帧（用户自主）

### Prior Art

- MX Player 色彩调节（ColorMatrix 四参数模式）
- AMD FidelityFX CAS（MIT，官方 GLSL/HLSL 实现，现代播放器主流锐化方案）
- Anime4K v3（bloc97，MIT，模块化 CNN 超分 M/UL 变体，Android libmpv 移植先例 mpv-android-anime4k）
- Media3 Effect 实时播放（`ExoPlayer.setVideoEffects`）与自定义 GLSL ES 效果（开源播放器 sakuro 先例）
- GSY CustomRenderView 官方示例模式（RenderViewFactory）
- 本项目 `video-player-ux-fixes` 刚建立的设置行 + `video_config` 持久化模式（seekSensitivity）

## Requirements

### RA（A 期）

- RA1 色彩调节四参数：亮度（-50~50）/对比度（-50~50）/饱和度（-100~100）/色温（-50~50 暖冷），默认值均为 0（原画）
- RA2 参数拖动即时生效（实时预览），无需暂停/重启播放器
- RA3 预设：原画 / 护眼（暖色降蓝光）/ 鲜艳（提饱和对比）/ 自定义；应用预设后滑条联动
- RA4 参数持久化 `video_config`，跨会话记忆；总开关关闭时完全回退原画渲染
- RA5 设置入口：`VideoSettingsPanelContent` 新增"画质增强"分区（Dialog 壳/BottomSheet 壳双入口一致）
- RA6 全屏/切集数/切线路/WebView 降级→回 Exo 后滤镜自动重新应用
- RA7 WebView 降级模式下分区标注"仅 ExoPlayer 引擎生效"
- RA8 手势体系与播放核心零影响（纯渲染层）

### RB（B 期：CAS 锐化+降噪）

- RB1 CAS 锐化档位：关/轻/中/强（默认关），sharpness 映射 0.3/0.6/0.85，GLSL ES 3.0 移植（GLSL 核心约 40 行）
- RB2 轻度降噪档位：关/轻/中（默认关），与锐化联动（pass 顺序降噪→锐化）防噪点放大
- RB3 运行时切换档位无需重建播放器实例（`player.setVideoEffects` 热更新）
- RB4 `media3-effect:1.10.1` 依赖引入，无版本漂移（对齐既有 media3 版本）
- RB5 GL 渲染链与 SurfaceControl 路径冲突时：强制 TextureView 渲染 + 设置页提示
- RB6 低端机保护：默认全关；档位开启时帧率实测 ≥ 24fps 方可交付该档位

### RB+（B+ 期：Anime4K 超分高级档）

- RB7 Anime4K v3 Luma CNN Up 单 pass（M 变体）+ CAS 组合 2 pass 管线，输出 2x 分辨率
- RB8 高级档仅中高端解锁：`DeviceGrade` SoC/GPU/RAM 静态分级检测；未知 SoC 归进阶档，允许手动越级试开（含风险提示）
- RB9 运行时掉帧守护：Choreographer 连续 3 秒丢帧 >25% 提示降档
- RB10 超分与 A 期色彩调节正交叠加（Effect 在解码纹理层，ColorFilter 在显示层）
- RB11 高级档帧率门禁 ≥24fps（旗舰机实测）方可交付

### RC（C 期：仅登记，不实施）

- RC1 TFLite/NNAPI AI 超分降噪（轻量 CNN 模型 + GPU/NPU delegate）——管线复杂度高，待 B/B+ 验证后评估
- RC2 SDR→HDR 实时逆色调映射——依赖 Android 14 UltraHDR 生态，收益待验证

## Scenarios

### SA1: 护眼观影

1. 用户播放视频 → 设置面板 → 画质增强 → 开启
2. 选"护眼"预设 → 画面立即变暖（蓝光降低），无卡顿
3. 手动微调亮度 +10 → 实时变化；退出播放器重进 → 参数保持

### SA2: 低码率在线视频增强（B/B+ 期）

1. 用户播放低码率订阅源视频 → 画质增强 → 锐化"中"+ 降噪"轻"（进阶档）
2. 画面边缘清晰度提升（CAS 平坦区无噪点放大），帧率无肉眼可见下降
3. 中高端设备 → 高级档解锁提示 → 开启 Anime4K 超分 2x → 线条/细节明显增强
4. 低端机模拟器 → 高级档不可见（设备定级门禁），进阶档默认全关，手动开"轻"档验证帧率
5. 播放中持续掉帧 >25% → 收到降档提示

### SA3: 渲染引擎切换

1. ExoPlayer 播放失败自动降级 WebView → 画质增强分区显示"仅 ExoPlayer 引擎生效"且参数不变
2. 切回 ExoPlayer → 滤镜/效果自动重新应用

### SA4: 全屏与切换场景

1. 开启色彩调节后进全屏 → 滤镜保持；切集数/线路 → 滤镜保持
2. 关闭总开关 → 画面完全回退原画
