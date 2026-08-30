# APK 体积审核与精简优化

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 状态：🔄 设计中（v3，基于 debug APK 解压深度分析 + 打包技术手段全量评估）
> 创建日期：2026-07-08
> 功能名称：apk-size-optimization
> 核心约束：**绝对不能影响当前功能**

## 功能概述

对 Legado（阅读M）APK 打包体积进行多维度深度审核，在"绝对不能影响当前功能"的硬约束下，输出可落地的精简方案。

当前 debug APK 体积 **50.51 MB**（解压后 125.7 MB）。本次通过：
1. 四路并行子代理深度核查代码（material-icons/Firebase/ProGuard/资源）
2. **debug APK 解压深度分析**（125.7MB 内部构成：DEX/lib/assets/tables/res 逐项体积）
3. **native .so ELF strip 检测**（14 个 .so 文件均已 strip，无额外空间）
4. **打包技术手段全量评估**（R8/resourceOptimizations/preciseShrinking/nonTransitiveRClass/.so strip/ABI/resConfigs 逐项核查）

逐项验证每个候选精简项的功能影响，只保留**零功能影响**的精简项。

## 深度核查结论（v3 修正）

| 精简项 | 原估算 | v3 核查后实际 | 功能影响 | 决策 |
|--------|--------|--------------|---------|------|
| material-icons-extended | -3~8 MB | **0**（R8已tree-shake） | 移除丢17图标 | ❌ 保留 |
| Firebase（analytics+perf） | -1~2 MB | **-1.5~2.5 MB** | **零**（源码零调用） | ✅ 移除 |
| 视频/弹幕/歌词栈 | -3~6 MB | — | 用户明确保留 | ❌ 保留 |
| ProGuard keep 收敛 | -0.3~0.5 MB | **0~30KB** | jsoup/okio/hutool反射硬约束 | ❌ 不动 |
| 背景图转 WebP | -0.4~0.6 MB | **-837 KB** | 零（保留.jpg扩展名） | ✅ 做 |
| drawable 转 WebP | -0.1~0.2 MB | **-54 KB** | 零 | ✅ 做 |
| web/images/bg.jpg 转 WebP | — | **-40 KB** | 零 | ✅ 做 |
| **packaging 补 src/**** | — | **-40 KB** | 零（JDT源码不应在APK中） | ✅ 做 |
| packaging 补 kotlin/** | — | -0~30 KB | 零 | ✅ 做 |
| toml 清理9个未用声明 | — | 0 KB | 零 | ✅ 做（整洁） |
| okhttp3 keep allowobfuscation | — | -30 KB | 需回归 | ⚠️ 可选 |
| 前端 tree-shake | — | ~225 KB | 非零（改源码） | ❌ 不做 |
| **native .so strip** | — | **0**（已strip） | — | ❌ 无空间 |
| **R8 full mode** | — | 1-2 MB | 破坏反射 | ❌ 硬约束禁止 |
| **ABI splits（仅arm64）** | — | ~1 MB | 牺牲老设备 | ❌ 牺牲兼容 |

**合计预估收益（零功能影响）：约 -2.5~3.5 MB**

## 打包技术手段评估结论（v3 新增，回答用户"打包技术手段"诉求）

**核心结论：项目已启用几乎所有稳定的打包技术手段，无遗漏。**

| 打包技术手段 | 状态 | 说明 |
|-------------|------|------|
| R8 minify + shrinkResources | ✅ 已启用 | build.gradle:105-106 |
| enableResourceOptimizations | ✅ 已启用 | gradle.properties:25 |
| preciseShrinking（精确资源压缩） | ✅ 已启用 | gradle.properties:29 |
| nonTransitiveRClass（非传递R类） | ✅ 已启用 | gradle.properties:42 |
| abiFilters（arm64-v8a + armeabi-v7a） | ✅ 已启用 | build.gradle:67（已排除x86） |
| resConfigs 限语言 | ✅ 已启用 | build.gradle:74（已限6语言） |
| native .so 自动 strip | ✅ 已做 | ELF检测无.debug段，AGP默认strip |
| R8 full mode | ❌ 未启用 | 破坏Rhino/Gson/Hutool反射（硬约束） |
| ABI splits（仅arm64） | ❌ 未做 | 牺牲老设备兼容（用户否决） |
| useEmbeddedDex | ❌ 不适用 | DEX不压缩嵌入APK，增大体积 |

**没有"被遗漏的打包技术手段"能让体积额外减少 5MB+。**

## 核心发现

1. **项目已用所有稳定打包技术手段**：v3 解压 APK + 检测 .so strip + 核查 gradle.properties，确认 R8/resourceOptimizations/preciseShrinking/nonTransitiveRClass/abiFilters/resConfigs/.so strip 全部已启用。用户期望的"打包技术手段减5MB+"在零功能影响约束下不成立。

2. **native .so 已 strip 无额外空间**：14 个 .so 文件（libarchive 3.5MB/renderscript 0.84MB/rtmp 0.16MB）全部已 strip（无 .debug 段），且全部功能必需（libarchive 被 JsExtensions 引用、renderscript 用于 Bitmap.blur/resize、rtmp 用于视频流）。

3. **原估算高估的根因**：material-icons-extended 在 release 已被 R8 tree-shaking，实际只链接 17 个被引用的图标代码。ProGuard keep 主体全部有反射硬约束（jsoup 被 JS 脚本字符串引用、okio 被 RhinoClassShutter 安全层匹配）。

4. **Firebase 是最大的"纯冗余"**：源码零调用、Manifest零配置、App零初始化，本地已有 CrashHandler+AppLog 完整体系，含 google/ 301KB + firebase/ 16KB proto 文件，可安全移除。

5. **WebP 是最稳的"资源优化"**：保留原文件扩展名（Android 按文件头识别格式），零引用改动，零功能影响。

6. **src/ 40KB JDT 源码不应在 APK 中**：debug APK 解压发现 `org/eclipse/jdt/annotation/*.java` 源码文件被错误打包，可通过 packaging 排除。

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含打包技术手段评估 + Alternatives + Drawbacks + 折中选项）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / 8 条 ADR（含 AD-08 打包技术手段评估结论）/ Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单（4 Batch + 验证，`- [ ] X.Y` 格式）+ AOAdapt 日志 |

## 核心设计决策（摘要）

- **Selected Approach**：零功能影响精简——Firebase 移除 + WebP 转换（保留原扩展名）+ packaging 排除 src/**+kotlin/** + toml 微调，不动 Compose/视频弹幕/ProGuard keep 主体。
- **打包技术手段评估**：项目已启用所有稳定打包优化选项（R8/resourceOptimizations/preciseShrinking/nonTransitiveRClass/abiFilters/resConfigs/.so strip），无遗漏。
- **Alternatives Considered**：R8 full mode（否决，破坏反射）、ABI splits（否决，牺牲兼容）、前端 tree-shake（否决，非零影响）。详见 spec.md。
- **Drawbacks**：预估收益 -2.5~3.5MB，未达用户期望 5MB+；要达到 5MB+ 需从 F1(ABI单架构)/F2(R8 full mode)/F3(移除日韩转换表) 折中选项决策。详见 spec.md。

## 实施批次

| Batch | 内容 | 预估收益 | 风险 |
|-------|------|---------|------|
| Batch 1 | Firebase 移除 | -1.5~2.5 MB | 零 |
| Batch 2 | 图片 WebP 转换 | -931 KB | 零 |
| Batch 3 | packaging 排除 src/**+kotlin/** + toml 清理 | -40~70 KB | 零 |
| Batch 4（可选） | okhttp3 keep allowobfuscation | -30 KB | 需回归 |

## 折中选项（要达到 5MB+ 需用户决策）

| 选项 | 额外收益 | 代价 |
|------|---------|------|
| F1. ABI 仅 arm64-v8a | +1 MB | 不支持纯 armeabi-v7a 老设备 |
| F2. R8 full mode + 精细 keep | +1-2 MB | 需全量回归，可能崩溃 |
| F3. 移除日韩转换表 | +0.5 MB | 需改库配置 |
