# Spec — APK 体积审核与精简优化

> 修订：v3 — 基于 debug APK 解压深度分析 + 打包技术手段全量评估（2026-07-08）
> 核心约束：**绝对不能影响当前功能**（用户明确要求）
> v3 变更：补充 APK 内部构成实测数据 + 打包技术手段全量评估 + packaging 排除 src/**

## Intent

回答用户问题：**"为什么打包现在越来越大，有没有精简的可能性，从多维度考虑（技术角度、冗余文件问题等）"**，并回应用户对 v2 方案（预估仅 -2~3MB）的不满：**"就没有一些打包技术手段能够让安装包体积变小的么？"**

通过 debug APK 解压深度分析（125.7MB 解压后内部构成）+ 打包技术手段全量评估（R8/resourceOptimizations/preciseShrinking/nonTransitiveRClass/.so strip/ABI/resConfigs 逐项核查），**逐项核查每个候选精简项的功能影响**，在"绝对不能影响当前功能"的硬约束下，输出可落地的精简方案。

### APK 内部构成实测数据（debug, 解压后 125.7MB）

| 维度 | 体积 | 占比 | release 处理 | 可精简 |
|------|------|------|-------------|--------|
| DEX（25个） | 108.03 MB | 85.9% | R8 minify 大幅缩小 | 仅 R8 full mode 有额外空间（破坏反射） |
| lib/（arm64+v7a） | 4.61 MB | 3.7% | .so 已 strip，不变 | libarchive/renderscript/rtmp 全功能必需 |
| assets/ | 3.31 MB | 2.6% | 不变（除 Firebase） | Firebase 移除省 318KB + WebP 省 837KB |
| tables/ | 2.95 MB | 2.3% | 不变 | 简繁转换必需（含日韩表 ~0.5MB 可评估） |
| res/ | 2.54 MB | 2.0% | shrinkResources 缩小 | drawable WebP 省 54KB |
| resources.arsc | 1.74 MB | 1.4% | shrinkResources 缩小 | 已优化 |
| tc/ | 1.15 MB | 0.9% | 不变 | 简繁转换字典必需 |
| META-INF/ | 0.90 MB | 0.7% | 签名 | 不变 |
| google/ | 0.30 MB | 0.2% | 随 Firebase 移除 | ✅ Firebase proto |
| dtd/ | 0.34 MB | 0.3% | 不变 | EPUB/XHTML 解析必需 |
| org/ | 0.10 MB | 0.1% | 不变 | Rhino JS 消息 + Markdown 实体必需 |
| **src/** | **0.04 MB** | 0.0% | 不变 | ✅ **JDT 注解源码，不应在 APK 中** |
| firebase/ | 0.02 MB | 0.0% | 随 Firebase 移除 | ✅ Firebase perf proto |
| kotlin/ | 0.05 MB | 0.0% | R8 处理 | 保守不动 |

## Scope

### 做什么（In Scope）

1. **体积画像**：解压 release/debug APK，统计 dex/res/assets/native/依赖占比。
2. **依赖逐项核查**：对每个候选依赖，Grep 代码引用 + 反射分析 + JS 脚本字符串引用，判定"零功能影响/有功能影响"。
3. **资源核查**：assets（bg/web/textmate）、res（drawable/多语言）冗余识别，确认每项清理无动态引用。
4. **构建配置核查**：ProGuard keep 逐条反射依赖分析、packaging 排除项、R8 模式。
5. **精简方案**：只保留"零功能影响"项，输出可执行方案。
6. **实施与验证**：分批实施，每批构建对比体积，安装逍遥模拟器回归测试。

### 不做什么（Out of Scope，基于深度核查结论）

1. **不动 material-icons-extended**：release 已 R8 tree-shake，仅链接 17 个图标；移除会丢调试工具集 7 界面 17 图标（含 5 个工具入口图标 + 全部复制/粘贴操作）。
2. **不动视频/弹幕/歌词栈**：用户明确保留（GSYVideoPlayer+media3+danmakuFlameMaster+lyricViewx）。
3. **不动 ProGuard keep 主体**：jsoup（JS脚本字符串硬约束）、okio（RhinoClassShutter安全层）、hutool（锁定+反射）、JsExtensions/data.entities（Rhino/Gson/Room反射）、GSYVideoPlayer/tm4e/joni（内部反射/SPI）全部不可动。
4. **不启用 R8 full mode**：破坏 Rhino/Gson/Hutool 反射。
5. **不动前端产物源码**：vue/help/uploadBook 优化需改源码重新构建，属非零影响。
6. **不升级锁定版本**：jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22。
7. **不删除已翻译语言资源**、不删 assets/bg 任何一张图（全部动态引用）、不删 textmate 任何语法（3语言8主题全在用）。

## Approach

### Selected Approach：零功能影响精简（修正后）

经四路子代理深度核查代码，在"绝对不能影响功能"硬约束下，可精简项收敛为以下**低风险/零风险**集合：

**A. 依赖裁剪（预估 -1~2 MB）**

| 依赖 | 核查结论 | 预估收益 | 功能影响 | 可做性 |
|------|---------|---------|---------|--------|
| `firebase-bom` + `firebase-analytics` + `firebase-perf` + `google-services` 插件 | 源码零调用、Manifest零配置、App.kt零初始化、ProGuard零规则；本地已有 CrashHandler+AppLog 完整崩溃/日志体系 | -1~2 MB | **零** | ✅ 移除 |
| `material-icons-extended` | release 已 R8 tree-shake 仅链接 17 图标；移除会丢调试工具集图标 | 0（R8已裁剪） | 破坏功能 | ❌ 保留 |
| 视频/弹幕/歌词栈 | 用户明确保留 | — | — | ❌ 保留 |

**B. 资源优化（预估 -0.93 MB）**

| 资源 | 优化方式 | 预估收益 | 功能影响 | 关键约束 |
|------|---------|---------|---------|---------|
| `assets/bg/` 14 张背景图（1004KB） | 转 WebP q85，**保留 .jpg 扩展名** | -837 KB | 零 | Android 按文件头识别格式，不改用户 SharedPreferences 引用 |
| `res/drawable/` 6 张位图（89KB） | 转 WebP q85，保留原文件名 | -54 KB | 零 | R.drawable.* 引用不变 |
| `assets/web/images/bg.jpg` | 转 WebP | -40 KB | 零 | 同步检查 CSS 引用 |

**C. 构建配置微调（预估 -40~90 KB）**

| 配置 | 优化 | 预估收益 | 功能影响 | 可做性 |
|------|------|---------|---------|--------|
| `packaging.resources.excludes` 补 `src/**` | 排除 JDT 注解 .java 源码（不应在 APK 中） | -40 KB | 零（源码文件运行时不需要） | ✅ 做 |
| `packaging.resources.excludes` 补 `kotlin/**` | 排除 kotlin-stdlib 元数据 | -0~30 KB | 零（R8 精确压缩应已处理，实测仍残留 52KB） | ✅ 做 |
| `okhttp3.*` keep 改 `allowobfuscation` | 类名混淆 | -30 KB | **需回归测试** | ⚠️ 可选（需全量网络回归） |
| 其他 keep（jsoup/okio/hutool等） | — | 0 | 破坏反射 | ❌ 不动 |

**D. 代码整洁（零 APK 影响，工程价值）**

| 项 | 操作 | APK 影响 | 价值 |
|----|------|---------|------|
| `libs.versions.toml` 删除 9 个未使用声明 | splitties-activities/glide-compose/glide-ksp/glide-avif/avif/kotlin-reflect/media3-hls/media3-ui/media3-session | 0 KB | 减少目录噪音 |
| `.gitignore` 显式添加 `modules/web/dist/` | 防止误提交前端构建产物 | 0 KB | 仓库整洁 |

**E. 打包技术手段全量评估（回答用户"打包技术手段"诉求）**

> 基于 debug APK 解压分析 + gradle.properties 实测配置 + .so ELF strip 检测

| 打包技术手段 | 当前状态 | 额外收益 | 结论 |
|-------------|---------|---------|------|
| R8 minify + shrinkResources | ✅ 已启用（build.gradle:105-106） | — | 已最优 |
| `android.enableResourceOptimizations` | ✅ 已启用（gradle.properties:25） | — | 已最优 |
| `preciseShrinking`（精确资源压缩） | ✅ 已启用（gradle.properties:29） | — | 已最优 |
| `nonTransitiveRClass`（非传递R类） | ✅ 已启用（gradle.properties:42） | — | 已最优 |
| `abiFilters`（arm64-v8a + armeabi-v7a） | ✅ 已启用（build.gradle:67） | — | 已排除 x86，省 ~5MB |
| `resConfigs` 限语言 | ✅ 已启用（build.gradle:74） | — | 已限 6 语言 |
| native .so 自动 strip | ✅ 已做（ELF 检测无 .debug 段，22-28 sections） | 0 | AGP 默认 strip，无额外空间 |
| `packaging.resources.excludes` | ⚠️ 仅 META-INF/* | +40KB | 补排除 src/**（见 C） |
| **R8 full mode** | ❌ 未启用 | 1-2 MB | **破坏 Rhino/Gson/Hutool 反射，build.gradle:73 明确禁止** |
| **ABI splits（仅 arm64-v8a）** | ❌ 未做 | ~1 MB | 牺牲纯 armeabi-v7a 老设备兼容（Android 6-7 中低端） |
| `useEmbeddedDex` | ❌ 未配置 | 负收益 | DEX 不压缩嵌入 APK，**增大体积**，不适用 |
| DEX startup optimization | ❌ 未配置 | 未知 | 实验性选项，不稳定，不推荐 |

**核心结论**：**项目已启用几乎所有稳定的打包技术手段。** 剩余技术手段要么已自动处理（.so strip），要么会破坏功能（R8 full mode），要么牺牲兼容性（ABI splits）。没有"被遗漏的打包技术手段"能让体积额外减少 5MB+。

**合计预估收益（零功能影响）：约 -2.5~3.5 MB**

（Firebase 1.5-2.5MB + WebP 0.93MB + packaging排除 0.07MB）

### 需用户决策的折中选项（要达到 5MB+ 需至少选一项）

| 折中选项 | 额外收益 | 代价 | 风险 |
|---------|---------|------|------|
| **F1. ABI 仅 arm64-v8a** | +1 MB | 不支持纯 armeabi-v7a 设备（Android 6-7 中低端，市占率<5%） | 部分老设备无法安装 |
| **F2. R8 full mode + 精细 keep** | +1-2 MB | 需全量回归测试（Rhino/Gson/Hutool/Room/Glide 反射链路） | 可能运行时崩溃 |
| **F3. 移除日韩转换表** | +0.5 MB | 需修改 quick-chinese-transfer 库配置或排除 tables/ 下 JapaneseEuc/Korean/Sjis 文件 | 简繁转换库可能硬依赖 |

### Alternatives Considered

| 替代方案 | 描述 | 否决理由 |
|---------|------|---------|
| **A. 移除 material-icons-extended** | 省 3-8MB（原估算） | 深度核查发现 release 已 R8 tree-shake，实际仅链接 17 图标；移除会丢调试工具集 7 界面 17 图标（含 ContentCopy 复制按钮 11 处、5 个工具入口图标）。**违反零功能影响约束**。 |
| **B. 移除视频/弹幕/歌词栈** | 省 3-6MB | 用户明确要求保留。 |
| **C. 全面 R8 full mode** | 省 0.5-1MB | 破坏 Rhino/Gson/Hutool 反射，build.gradle 注释明确禁止。 |
| **D. ProGuard keep 收敛 jsoup/okio** | 省 0.3-0.5MB | jsoup 被 dictRules.json 第19/33行 JS 脚本 + 用户书源生态用全限定名引用；okio 被 RhinoClassShutter.kt 第97-101行字符串匹配做安全拦截。混淆后字符串匹配失效，破坏 JS 引擎与安全沙箱。 |
| **E. 前端产物 tree-shake** | 省 ~225KB | 需改 vite 源码/help/index.html/jquery 重写，属非零功能影响，需大量回归测试。 |
| **F. 仅保留 arm64-v8a ABI** | 省 1-2MB | 牺牲老设备兼容性（Android 6-7 中低端 armeabi-v7a）。 |
| **G. 移除 sora-editor/textmate** | 省 ~1MB | 3 语言 8 主题全部被 CodeEditViewModel 加载使用，移除影响书源编辑器语法高亮。 |
| **H. 切换 AAB 分发** | 减少用户下载体积 | 私有化 fork 以 APK 分发为主，不切换分发格式。 |

### Drawbacks

1. **预估收益 -2.5~3.5MB（零功能影响约束下的真实空间）**
   - 缺点：精简幅度有限，未达到用户期望的 5MB+。
   - 接受理由：v3 基于 debug APK 解压深度分析（125.7MB 内部构成）+ 打包技术手段全量评估，确认**项目已启用几乎所有稳定的打包技术手段**（R8/shrinkResources/resourceOptimizations/preciseShrinking/nonTransitiveRClass/abiFilters/resConfigs/.so自动strip）。剩余可精简项仅 Firebase 移除 + WebP + packaging 排除 src/**。深度核查发现大部分体积是功能必需的（规则引擎反射依赖、视频弹幕栈、简繁转换数据、EPUB DTD、锁定版本库）。诚实地告诉用户真实可精简空间，优于给出无法兑现的高估算。
   - **要达到 5MB+ 的路径**：需用户从 F1/F2/F3 折中选项中至少选一项（见上方"需用户决策的折中选项"）。

2. **okhttp3 keep 改 allowobfuscation 需回归测试**
   - 缺点：收益仅 30KB，但需全量网络层回归（书源/Cronet/WebDAV）。
   - 接受理由：作为可选项，若用户接受回归成本则做，否则跳过。

3. **WebP 转换需保留 .jpg 扩展名**
   - 缺点：文件名与实际格式不符，略反直觉。
   - 接受理由：Android BitmapFactory 按文件头识别格式不依赖扩展名；保留 .jpg 扩展名可避免修改用户 SharedPreferences 中的背景图文件名引用，实现零功能影响。

4. **debug APK 数据不能完全代表 release APK**
   - 缺点：本次分析基于 debug APK（50.51MB 文件/125.7MB 解压后），DEX 未混淆体积虚高（108MB）；release 经 R8 后 DEX 会大幅缩小，真实 release 体积需构建验证。
   - 接受理由：native lib（4.61MB）、assets（3.31MB）、tables/tc（4.1MB）等不受 R8 影响，数据准确；DEX 部分的 release 收益为推算（基于 R8 通常缩小 40-60%）。实施时将构建 release APK 对比真实体积。

### Prior Art

- **07/05 排除 Compose 运行时**：DEX -21%（约 15MB）—— 但 07/06 为 F-P0-1 调试工具集又引入，本次不动 Compose 栈。
- **07/06 仅打包 ARM 架构**：-5MB —— 已生效。
- **07/07 限语言资源**：-50-100KB —— 已生效。

## Requirements

### R1 体积基线（v3 已实测）
- R1.1 debug APK 文件体积 50.51 MB，解压后 125.7 MB；release APK 体积待构建。
- R1.2 APK 内部构成实测（debug 解压后）：DEX 108.03MB(85.9%) / lib 4.61MB(3.7%) / assets 3.31MB(2.6%) / tables 2.95MB(2.3%) / res 2.54MB(2.0%) / resources.arsc 1.74MB(1.4%) / tc 1.15MB(0.9%) / META-INF 0.90MB(0.7%) / 其他 0.85MB(0.5%)。
- R1.3 native .so 全部已 strip（ELF 检测无 .debug 段）：libarchive-jni.so 3.5MB（76%）/ librenderscript-toolkit.so 0.84MB / librtmp-jni.so 0.16MB / 其他 0.11MB。
- R1.4 打包技术手段全量评估完成（见 Approach E），确认项目已启用所有稳定优化选项。

### R2 依赖审计（已完成深度核查）
- R2.1 已逐项核查，结论见 Approach A。
- R2.2 移除 Firebase 前已 Grep 确认源码零调用、Manifest零配置。
- R2.3 material-icons-extended 经核查保留（R8已裁剪，移除破坏功能）。

### R3 资源优化
- R3.1 WebP 转换用 q85（非 q80，保证背景纹理无可见瑕疵）。
- R3.2 背景图保留 .jpg 扩展名，避免改用户配置引用。
- R3.3 drawable 转换保留原文件名，R.drawable.* 引用不变。

### R4 构建配置
- R4.1 不启用 R8 full mode。
- R4.2 不动 jsoup/okio/hutool/JsExtensions/data.entities 的 keep 规则。
- R4.3 okhttp3 keep 改 allowobfuscation 为可选项，需回归测试通过才保留。

### R5 验证
- R5.1 Firebase 移除后构建 release APK，确认无编译错误。
- R5.2 安装逍遥模拟器，启动无 Firebase 初始化崩溃。
- R5.3 核心功能回归：书源搜索/详情/目录/正文（jsoup/rhino）、RSS（网络栈）、Web端书架/备份（NanoHTTPD）、阅读翻页/高亮/TTS、调试工具集（Compose 图标）。
- R5.4 检查 temp/tmp 日志无 NoClassDefFoundError/NoSuchMethodError。
- R5.5 WebP 背景图肉眼验证视觉无差异。

### R6 文档
- R6.1 更新 assets/updateLog.md 记录体积优化条目。
- R6.2 更新 docs/project-flow/quick-reference.md 构建配置说明。
- R6.3 更新 docs/INDEX.md 状态标记。

## Scenarios

### S1：Firebase 移除（零功能影响）
- **前置**：源码零调用、Manifest零配置、App.kt零初始化已核查确认。
- **操作**：删 build.gradle 第14行 google-services 插件 + 第330-333行 firebase 依赖；删 libs.versions.toml 第76/110-112/239行；删 app/google-services.json；Manifest/ProGuard/源码无需改。
- **验证**：构建 release 通过；模拟器启动无崩溃；体积 -1~2MB。

### S2：背景图 WebP 转换（零功能影响）
- **前置**：assets/bg/ 14 张图共 1004KB，全部被 ReadBookConfig.kt:791-804 动态加载。
- **操作**：用 cwebp -q 85 转换 14 张图；**保留 .jpg 扩展名**（仅改文件内容编码）；minSdk 23 支持 WebP。
- **验证**：阅读界面切换 14 种背景，显示正常无瑕疵；体积 -837KB。

### S3：drawable 转 WebP（零功能影响）
- **前置**：image_cover_default.jpg 等 6 张位图共 89KB。
- **操作**：转 WebP q85，保留原文件名；R.drawable.* 引用不变。
- **验证**：书架默认封面、RSS 文章图、加载错误图显示正常；体积 -54KB。

### S4：packaging 补 src/** + kotlin/**（零功能影响）
- **前置**：当前仅排除 META-INF/*。debug APK 实测 src/ 40KB（JDT 注解 .java 源码，不应在 APK 中）、kotlin/ 52KB（kotlin_builtins 元数据）。
- **操作**：packaging.resources.excludes 补 `src/**` 和 `kotlin/**`。
- **验证**：构建通过；体积 -40~70KB；确认无 Kotlin 反射运行时异常。

### S5：okhttp3 keep 改 allowobfuscation（可选，需回归）
- **前置**：okhttp3 无 Class.forName、无 JS 字符串引用。
- **操作**：`-keep class okhttp3.*{*;}` → `-keep,allowobfuscation class okhttp3.*{*;}`。
- **验证**：全量网络回归（书源搜索/Cronet切换/WebDAV同步/图片加载）；通过则保留，失败则回滚。

### S6：toml 清理未使用声明（零 APK 影响）
- **前置**：9 个声明在 build.gradle 未引入。
- **操作**：删 libs.versions.toml 中 splitties-activities/glide-compose/glide-ksp/glide-avif/avif/kotlin-reflect/media3-hls/media3-ui/media3-session。
- **验证**：构建通过；APK 体积不变。

### S7：回归测试失败回滚
- **前置**：某项精简后模拟器测试发现异常。
- **操作**：根据崩溃日志定位；回滚该批 commit 或补 keep 规则；重新构建验证。
