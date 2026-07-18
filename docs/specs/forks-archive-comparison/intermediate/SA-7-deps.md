# SA-7 依赖库模块深度对比分析

> 数据来源：Archive 私仓（`temp/forks-comparison/legado-archive/`）vs 本项目（`f:\myself\github\WeAgentChat\temp\legado\`）
> 对比文件：`gradle/libs.versions.toml` + `app/build.gradle` + `modules/book/build.gradle` + `modules/rhino/build.gradle`
> 分析日期：2026-07-18

## 1. 模块概览

| 维度 | Archive | 本项目 |
|------|---------|--------|
| 对比文件数 | 4 | 4 |
| `libs.versions.toml` 总行数 | 246 | 246 |
| `app/build.gradle` dependencies 范围 | L184-L343（159 行） | L196-L359（163 行） |
| `modules/book/build.gradle` | 34 行 | 34 行（**完全一致**） |
| `modules/rhino/build.gradle` | 47 行 | 47 行（**完全一致**） |
| 独有依赖（versions.toml 层面） | 5 项 | 11 项 |
| 独有依赖（app/build.gradle 层面） | 5 项 | 6 项 |
| 锁定依赖数量（带 #noinspection） | 9 项 | 9 项 |
| 关键差异类型 | 引入 5 个 UI 增强库 | 引入 Firebase + 完整 Compose 工具链 |

**核心结论**：`modules/book` 与 `modules/rhino` 两边**字节级一致**，所有差异都在 `app` 模块。Archive 走"UI 增强库"路线（liquidglass/miuix/reorderable/lazycolumnscrollbar/lottie），本项目走"Firebase 监控 + 完整 Compose MVVM 工具链"路线（firebase-bom/analytics/perf + activity-compose + lifecycle-viewmodel-compose + glide-compose + material-icons-extended）。

## 2. Archive 依赖清单分析

### 2.1 Archive `libs.versions.toml` 完整依赖列表

**versions 块（L1-L84）**：

| 类别 | 依赖名 | 版本 | 备注 |
|------|--------|------|------|
| 构建 | kotlin | 2.3.10 | - |
| 构建 | ksp | 2.3.7 | 比本项目新 |
| 构建 | agp | 8.13.2 | - |
| 构建 | composeBom | 2025.10.00 | 比本项目新半年 |
| 构建 | composeMaterial3 | 1.4.0 | 显式版本 |
| androidX | appcompat | 1.7.1 | - |
| androidX | constraintlayout | 2.2.1 | - |
| androidX | core | 1.17.0 | 比本项目旧 |
| androidX | fragment | 1.8.9 | - |
| androidX | documentfile | 1.1.0 | - |
| androidX | preference | 1.2.1 | - |
| androidX | swiperefreshlayout | 1.2.0 | - |
| androidX | collection | 1.5.0 | - |
| androidX | recyclerview | 1.4.0 | 锁定 |
| androidX | viewpager2 | 1.0.0 | 锁定 |
| androidX | webkit | 1.14.0 | 锁定 |
| androidX | activity | 1.11.0 | 比本项目旧 |
| androidX | lifecycle | 2.9.4 | - |
| androidX | room | 2.7.1 | 锁定 |
| androidX | media | 1.7.1 | - |
| **UI 独有** | **liquidglass** | **1.0.3** | **Archive 独有** |
| **UI 独有** | **miuix** | **0.8.8** | **Archive 独有** |
| **UI 独有** | **reorderable** | **3.1.0** | **Archive 独有** |
| **UI 独有** | **lazyColumnScrollbar** | **2.2.0** | **Archive 独有** |
| **UI 独有** | **lottie** | **6.6.6** | **Archive 独有** |
| google | material | 1.13.0 | 比本项目旧 |
| google | flexbox | 3.0.0 | - |
| google | gson | 2.13.2 | - |
| media | media3 | 1.8.0 | 比本项目旧 |
| media | gsyvideoplayer | 11.3.0 | 锁定 |
| media | danmaku | 0.9.25 | - |
| 网络 | okhttp | 5.3.2 | 比本项目旧 |
| 视频 | libarchive | 1.1.6 | - |
| 歌词 | lyricViewx | 1.3.2 | - |
| 编辑器 | soraEditor | 0.24.4 | - |
| 图像 | glide | 5.0.5 | - |
| 工具 | splitties | 3.0.0 | - |
| 工具 | desugar | 2.1.5 | - |
| 工具 | jsonPath | 2.10.0 | - |
| 工具 | jsoupxpath | 2.5.3 | - |
| 工具 | markwon | 4.6.2 | - |
| 工具 | nanoHttpd | 2.3.1 | - |
| 工具 | liveeventbus | 1.8.14 | - |
| 工具 | quickChineseTransfer | 0.2.17 | - |
| 工具 | zxingLite | 3.3.0 | - |
| 工具 | colorpicker | 1.1.0 | - |
| 工具 | protobufJavalite | 4.26.1 | 锁定 |
| **锁定** | **hutool** | **5.8.22** | 锁定（书源加解密） |
| **锁定** | **jsoup** | **1.16.2** | 锁定（#3811 破坏性变更） |
| **锁定** | **rhino** | **1.8.1** | 锁定（API 26 以下 VarHandle） |
| **锁定** | **commonsText** | **1.13.1** | 锁定（API 23 以下 Arrays.setAll） |

**libraries 块关键条目**：
- L96: `liquidglass = { module = "com.qmdeve.liquidglass:core", version.ref = "liquidglass" }`
- L97: `reorderable = { module = "sh.calvin.reorderable:reorderable", version.ref = "reorderable" }`
- L98: `lottie = { module = "com.airbnb.android:lottie", version.ref = "lottie" }`
- L114: `libarchive = { module = "me.zhanghai.android.libarchive:library", version.ref = "libarchive" }`
- L118: `lyricViewx = { module = "com.github.Moriafly:LyricViewX", version.ref = "lyricViewx" }`
- L168-170: `soraEditor-bom` / `soraEditor-core` / `soraEditor-language-textmate`
- L182-188: Compose 系列用 `androidx-compose-*` 前缀
- L189: `miuix-android = { module = "top.yukonga.miuix.kmp:miuix-android", version.ref = "miuix" }`
- L190: `lazycolumnscrollbar = { module = "com.github.nanihadesuka:LazyColumnScrollbar", version.ref = "lazyColumnScrollbar" }`
- L215: `renderscript-intrinsics-replacement-toolkit = { ... version = "8eaa829ddd" }`（commit hash 锁定）

### 2.2 Archive `app/build.gradle` dependencies 块（L184-L343）

按类别分组：

| 类别 | 行号 | 依赖 |
|------|------|------|
| desugar | L188 | coreLibraryDesugaring(libs.desugar) |
| 测试 | L189-L190 | junit / bundles.androidTest |
| kotlin | L193 | libs.kotlin.stdlib |
| 协程 | L201 | bundles.coroutines |
| 图像处理 | L205 | renderscript.intrinsics.replacement.toolkit |
| androidX | L208-L219 | core.ktx / appcompat / activity.ktx / fragment.ktx / preference.ktx / constraintlayout / swiperefreshlayout / recyclerview / viewpager2 / webkit / documentfile |
| **Compose** | L220-L228 | **compose.bom / compose.ui / compose.ui.graphics / compose.ui.tooling.preview / compose.foundation / compose.material3** |
| **Compose 扩展** | L226-L228 | **reorderable / lazycolumnscrollbar / miuix.android** |
| **liquidglass** | L214 | **libs.liquidglass（位于 androidX 与 Compose 之间）** |
| google | L231-L234 | material / flexbox / gson / **lottie** |
| lifecycle | L237-L238 | lifecycle.common.java8 / lifecycle.service |
| media | L241-L247 | media.media / media3.exoplayer / media3.datasource.okhttp |
| 视频 | L252-L255 | gsyVideoPlayer.java / gsyVideoPlayer.exo2 / danmakuFlameMaster |
| splitties | L258-L260 | appctx / systemservices / views |
| room | L263-L267 | runtime / ktx / ksp(compiler) / testing |
| liveEventBus | L270 | liveeventbus |
| 规则 | L273-L277 | jsoup / json.path / jsoupxpath / **project(:modules:book)** / **project(:modules:rhino)** |
| 网络 | L282-L284 | okhttp / fileTree(cronetlib) / protobuf.javalite |
| Glide | L287-L289 | glide.glide / glide.okhttp / **ksp(glide.ksp)** |
| SVG | L292-L294 | androidsvg / glide.svg |
| webServer | L297-L298 | nanohttpd / nanohttpd.websocket |
| 二维码 | L302 | zxing.lite |
| 颜色 | L305 | colorpicker |
| 压缩 | L308 | libarchive |
| apache | L311 | commons.text |
| MarkDown | L314-L320 | markwon.core / image.glide / ext.tables / ext.strikethrough / ext.tasklist / html / linkify |
| 繁体 | L323 | quick.chinese.transfer.core |
| 加解密 | L327 | hutool.crypto |
| glide扩展 | L329 | glide.recyclerview |
| 歌词 | L337 | lyricViewx |
| **Compose 工具** | L338 | debugImplementation(compose.ui.tooling) |
| **sora-editor** | L340-L342 | **platform(soraEditor.bom) / soraEditor.core / soraEditor.language.textmate** |

### 2.3 Archive `modules/book/build.gradle`

L1-L34，与本项目**完全一致**，仅依赖 `libs.androidx.annotation`，namespace=`me.ag2s`，minSdk=21，targetSdk=36，Java 17。

### 2.4 Archive `modules/rhino/build.gradle`

L1-L47，与本项目**完全一致**，依赖 `libs.mozilla.rhino`（api）+ `kotlinx.coroutines.core` + `okhttp` + `androidx.collection`，namespace=`com.script`。

## 3. 本项目依赖清单分析

### 3.1 本项目 `libs.versions.toml` 完整依赖列表

**versions 块（L1-L77）关键差异**：

| 类别 | 依赖名 | 版本 | 与 Archive 对比 |
|------|--------|------|---------------|
| 构建 | ksp | 2.3.4 | Archive 新（2.3.7） |
| 构建 | composeBom | 2025.04.01 | Archive 新半年（2025.10.00） |
| 构建 | **无 composeMaterial3** | - | Archive 显式锁定 1.4.0 |
| androidX | core | 1.18.0 | Archive 旧（1.17.0） |
| androidX | activity | 1.13.0 | Archive 新（1.11.0） |
| google | material | 1.14.0 | Archive 旧（1.13.0） |
| 网络 | okhttp | 5.4.0 | Archive 旧（5.3.2） |
| 协程 | coroutines | 1.11.0 | Archive 旧（1.10.2） |
| media | media3 | 1.10.1 | Archive 旧（1.8.0） |
| **独有** | **firebaseBom** | **34.12.0** | **本项目独有** |
| 缺失 | liquidglass | - | Archive 独有 |
| 缺失 | lottie | - | Archive 独有 |
| 缺失 | miuix | - | Archive 独有 |
| 缺失 | reorderable | - | Archive 独有 |
| 缺失 | lazyColumnScrollbar | - | Archive 独有 |
| 锁定 | hutool / jsoup / rhino / commonsText / gsyvideoplayer / webkit / room / recyclerview / viewpager2 | 同 Archive | 两边锁定策略一致 |

**libraries 块关键差异**：
- L81: `activity-compose = { module = "androidx.activity:activity-compose", version.ref = "activity" }` ← 本项目独有
- L84-L95: Compose 系列用 `compose-*` 前缀（无 `androidx-` 前缀），且额外有：
  - `compose-material3-window-size`
  - `compose-runtime`
  - `compose-material-icons-extended`
  - `lifecycle-viewmodel-compose`
  - `lifecycle-runtime-compose`
- L110-L112: `firebase-bom` / `firebase-analytics` / `firebase-perf` ← 本项目独有
- L168: `glide-compose = { module = "com.github.bumptech.glide:compose", version = "1.0.0-beta08" }` ← 本项目独有
- **无** liquidglass / miuix / reorderable / lazycolumnscrollbar / lottie 定义
- L239: `google-services = { id = "com.google.gms.google-services", version = "4.4.2" }` ← 本项目独有 plugin

### 3.2 本项目 `app/build.gradle` dependencies 块（L196-L359）

| 类别 | 行号 | 依赖 | 与 Archive 对比 |
|------|------|------|---------------|
| desugar / 测试 / kotlin / 协程 | L200-L213 | 同 Archive | 一致 |
| **Compose 完整工具链** | L216-L227 | bom / material3 / ui / graphics / tooling.preview / foundation / **runtime** / **material-icons-extended** / **activity-compose** / **lifecycle-viewmodel-compose** / **lifecycle-runtime-compose** / debugImplementation(tooling) | Archive 仅 bom+ui+graphics+tooling.preview+foundation+material3，缺 runtime/icons/viewmodel-compose/runtime-compose/activity-compose |
| 图像处理 / androidX | L230-L243 | 同 Archive（无 liquidglass） | - |
| google | L246-L248 | material / flexbox / gson（**无 lottie**） | - |
| lifecycle / media / 视频 / splitties / room / liveEventBus / 规则 / 网络 / Glide / SVG / webServer / 二维码 / 颜色 / 压缩 / apache / MarkDown / 繁体 / 加解密 | L251-L339 | 同 Archive | 一致 |
| **Glide 编译器** | L304 | **kapt(libs.glide.compiler)** | Archive 用 `ksp(libs.glide.ksp)` |
| **MarkDown 扩展** | L329-L332 | core / image.glide / ext.tables / html（**缺 ext.strikethrough / ext.tasklist / linkify**） | Archive 多 3 个扩展 |
| **Firebase** | L342-L344 | **platform(firebase.bom) / firebase.analytics / firebase.perf** | **本项目独有** |
| glide扩展 / 歌词 / sora-editor | L346-L358 | 同 Archive | 一致 |

**关键技术差异（Glide 编译器）**：
- Archive L289: `ksp(libs.glide.ksp)` — 使用 KSP
- 本项目 L304: `kapt(libs.glide.compiler)` — 使用 kapt，注释（L303）："KSP 存在 Windows 跨盘 bug（C:\Gradle缓存 vs F:\项目），暂用 kapt"

## 4. Archive 独有依赖详细分析

| 依赖 | 版本 | 引入位置（文件+行号） | 用途分析 | 收益(1-5) | 风险(1-5) | 借鉴成本 |
|-----|------|---------------------|---------|----------|----------|---------|
| liquidglass | 1.0.3 | libs.versions.toml:L10,L96 + app/build.gradle:L214 | iOS 风格毛玻璃效果 UI 库（`com.qmdeve.liquidglass:core`），从依赖名与命名空间推断为视觉风格增强，可能用于设置页/书架页背景 | 2 | 4 | 中 |
| miuix.android | 0.8.8 | libs.versions.toml:L42,L189 + app/build.gradle:L228 | 小米 KMP UI 组件库（`top.yukonga.miuix.kmp:miuix-android`），提供 HyperOS 风格组件，与 Material3 设计语言冲突 | 2 | 5 | 高 |
| reorderable | 3.1.0 | libs.versions.toml:L43,L97 + app/build.gradle:L226 | Compose 拖拽排序库（`sh.calvin.reorderable:reorderable`），用于书架/书源列表拖拽排序 | 4 | 2 | 低 |
| lazycolumnscrollbar | 2.2.0 | libs.versions.toml:L44,L190 + app/build.gradle:L227 | Compose LazyColumn 长列表滚动条库（`com.github.nanihadesuka:LazyColumnScrollbar`），用于长列表快速定位 | 3 | 2 | 低 |
| lottie | 6.6.6 | libs.versions.toml:L11,L98 + app/build.gradle:L234 | Lottie 动画库（`com.airbnb.android:lottie`），用于启动动画/加载动画/复杂矢量动画 | 3 | 2 | 低 |
| composeMaterial3（显式版本） | 1.4.0 | libs.versions.toml:L41,L188 | Archive 显式锁定 Material3 版本，本项目依赖 composeBom 传递版本 | 2 | 3 | 低 |

**合计 6 项 Archive 独有依赖**（>=9 项要求未达成，实际仅 5 个真正独有库 + 1 个版本锁定策略差异；详见 §10 待评估说明）。

## 5. 锁定依赖对比（关键）

| 依赖 | Archive 版本 | 本项目锁定版本 | 是否可借鉴升级 | 理由 |
|-----|-------------|--------------|--------------|------|
| jsoup | 1.16.2 | 1.16.2 | ❌ | 两边都锁定 1.16.2，#3811 破坏性变更（jsoup#2017），升级会破坏 AnalyzeByJSoup.kt 与 JsoupXpath 库 |
| rhino | 1.8.1 | 1.8.1 | ❌ | 两边都锁定 1.8.1，新版使用 VarHandle.compareAndExchange（API 26/33 以下不可用），desugaring 不覆盖 VarHandle |
| hutool | 5.8.22 | 5.8.22 | ❌ | 两边都锁定 5.8.22，书源加解密依赖（hutool-crypto 模块），升级可能破坏书源规则兼容性 |
| commonsText | 1.13.1 | 1.13.1 | ❌ | 两边都锁定 1.13.1，新版使用 Arrays.setAll（API 23/24 以下不可用），desugaring 不覆盖 |
| gsyvideoplayer | 11.3.0 | 11.3.0 | ❌ | 两边都锁定 11.3.0，视频播放器核心库，API 稳定性要求高 |
| webkit | 1.14.0 | 1.14.0 | ❌ | 两边都锁定 1.14.0，WebView 兼容性依赖 |
| room | 2.7.1 | 2.7.1 | ⚠️ | 两边都锁定 2.7.1，可评估升级到 2.8.x，但需验证 migration 兼容性 |
| recyclerview | 1.4.0 | 1.4.0 | ❌ | 两边都锁定 1.4.0，RecyclerView 核心库 |
| viewpager2 | 1.0.0 | 1.0.0 | ❌ | 两边都锁定 1.0.0，ViewPager2 核心库 |
| protobufJavalite | 4.26.1 | 4.26.1 | ❌ | 两边都锁定 4.26.1，Protobuf 序列化 |

**核心结论**：两边锁定策略**完全一致**（10 项锁定依赖版本号相同）。差异在于注释说明——
- Archive `commonsText` 注释（L60-L62）："Android 6 以下缺少 Arrays.setAll"（API 23 以下）
- 本项目 `commonsText` 注释（L54-L56）："API 24 以下不可用的 Arrays.setAll"（本项目 minSdk 提升到 23 后仍保留 1.13.1）
- Archive `rhino` 注释（L64-L66）："Android 8 以下无法编译的 VarHandle.compareAndExchange"（API 26 以下）
- 本项目 `rhino` 注释（L58-L60）："API 33 以下不可用的 VarHandle.compareAndExchange"（本项目对 desugaring 边界更严格）

## 6. 版本差异依赖清单

| 依赖 | Archive 版本 | 本项目版本 | 差异类型 | 借鉴建议 |
|-----|-------------|-----------|---------|---------|
| ksp | 2.3.7 | 2.3.4 | 构建工具版本 | ⚠️ 可评估升级到 2.3.7（与 kotlin 2.3.10 配套） |
| composeBom | 2025.10.00 | 2025.04.01 | Compose BOM | ✅ 建议升级到 2025.10.00（半年差距，含修复） |
| core | 1.17.0 | 1.18.0 | androidx.core | ❌ 本项目已比 Archive 新 |
| activity | 1.11.0 | 1.13.0 | androidx.activity | ❌ 本项目已比 Archive 新 |
| material | 1.13.0 | 1.14.0 | Material Components | ❌ 本项目已比 Archive 新 |
| okhttp | 5.3.2 | 5.4.0 | 网络库 | ❌ 本项目已比 Archive 新 |
| coroutines | 1.10.2 | 1.11.0 | 协程库 | ❌ 本项目已比 Archive 新 |
| media3 | 1.8.0 | 1.10.1 | ExoPlayer | ❌ 本项目已比 Archive 新 |

**核心结论**：除 `ksp` 与 `composeBom` 外，本项目所有非锁定依赖的版本都**比 Archive 新**。Archive 的依赖更新策略比本项目保守。

## 7. 差异清单

| ID | 差异点 | Archive 实现 | 本项目实现 | 差异类型 | 收益(1-5) | 风险(1-5) | 借鉴成本 | 源码依据 |
|----|-------|-------------|-----------|---------|----------|----------|---------|---------|
| DEP-001 | liquidglass 玻璃效果库 | 引入 1.0.3 | 无 | 独有 | 2 | 4 | 中 | libs.versions.toml:L10,L96 + app/build.gradle:L214 |
| DEP-002 | miuix 小米 UI 库 | 引入 0.8.8 | 无 | 独有 | 2 | 5 | 高 | libs.versions.toml:L42,L189 + app/build.gradle:L228 |
| DEP-003 | reorderable 拖拽排序 | 引入 3.1.0 | 无 | 独有 | 4 | 2 | 低 | libs.versions.toml:L43,L97 + app/build.gradle:L226 |
| DEP-004 | lazycolumnscrollbar 滚动条 | 引入 2.2.0 | 无 | 独有 | 3 | 2 | 低 | libs.versions.toml:L44,L190 + app/build.gradle:L227 |
| DEP-005 | lottie 动画库 | 引入 6.6.6 | 无 | 独有 | 3 | 2 | 低 | libs.versions.toml:L11,L98 + app/build.gradle:L234 |
| DEP-006 | Firebase 监控 | 无 | 引入 firebase-bom 34.12.0 + analytics + perf | 反向独有 | 4 | 3 | 中 | 本项目 libs.versions.toml:L76,L110-L112 + app/build.gradle:L342-L344 |
| DEP-007 | Glide 编译器 | ksp(glide.ksp) | kapt(glide.compiler)（Windows 跨盘 bug） | 实现差异 | 3 | 3 | 中 | Archive app/build.gradle:L289 vs 本项目 L304 |
| DEP-008 | Compose 工具链完整度 | 6 项（bom/ui/graphics/preview/foundation/material3） | 12 项（含 runtime/material-icons-extended/activity-compose/lifecycle-viewmodel-compose/lifecycle-runtime-compose/window-size） | 实现差异 | - | - | - | Archive app/build.gradle:L220-L225 vs 本项目 L216-L227 |
| DEP-009 | glide-compose | 无 | 引入 1.0.0-beta08 | 反向独有 | 3 | 4 | 中 | 本项目 libs.versions.toml:L168 |
| DEP-010 | Markwon 扩展 | 7 项（含 strikethrough/tasklist/linkify） | 4 项（缺 strikethrough/tasklist/linkify） | 实现差异 | 3 | 2 | 低 | Archive app/build.gradle:L314-L320 vs 本项目 L329-L332 |
| DEP-011 | composeMaterial3 显式版本 | 1.4.0 显式锁定 | 由 composeBom 传递 | 策略差异 | 2 | 3 | 低 | Archive libs.versions.toml:L41,L188 vs 本项目 L85 |
| DEP-012 | renderscript toolkit commit 锁定 | 8eaa829ddd | 8eaa829ddd | 一致 | - | - | - | 两边 libs.versions.toml:L215/L213 |

## 8. 关键发现

1. **Compose 两边都启用但路线分歧大**：Archive 启用 Compose 但仅作"装饰层"（bom+ui+graphics+preview+foundation+material3 共 6 项），重点用 Compose 扩展库（liquidglass/miuix/reorderable/lazycolumnscrollbar）做 UI 增强；本项目启用完整 Compose MVVM 工具链（12 项，含 runtime/material-icons-extended/activity-compose/lifecycle-viewmodel-compose/lifecycle-runtime-compose），走"正经 Compose 应用"路线。本项目 app/build.gradle L189-L194 注释明确说明"F-P0-1 调试工具集需要"，原全局排除配置已移除。

2. **sora-editor 两边都引入且版本一致**：两边都引入 sora-editor 0.24.4（libs.versions.toml:L17/L175-177，app/build.gradle:L340-L342/L356-L358），用途相同——"代码编辑器，更丰富的编辑功能"。无需借鉴差异。

3. **liquidglass + miuix 设计语言严重冲突**：liquidglass 是 iOS 风格毛玻璃，miuix 是小米 HyperOS 风格，两者与 Material3 三套设计语言混用，长期维护成本高。本项目已用 Material3，借鉴 miuix 会引入设计语言碎片化。

4. **libarchive 两边都引入**：libarchive 1.1.6（`me.zhanghai.android.libarchive:library`）两边都有，用于 7z/rar/tar.gz 解压，替代 ZipFile。无需借鉴差异。

5. **弹幕库版本一致**：danmakuFlameMaster 0.9.25（`com.github.CarGuo.DanmakuFlameMaster:DanmakuFlameMaster`）两边都有，与 gsyvideoplayer 11.3.0 配套。无需借鉴差异。

6. **椒盐歌词 lyricViewx 两边都引入**：lyricViewx 1.3.2（`com.github.Moriafly:LyricViewX`）两边都有，用于音频播放时的歌词显示。无需借鉴差异。

7. **reorderable 与 lazycolumnscrollbar 借鉴价值高**：这两个库都是 Compose 生态成熟库，风险低、收益明确——reorderable 可用于书架拖拽排序（替换现有 ItemTouchHelper），lazycolumnscrollbar 可用于长列表（如目录页、书源列表）快速定位。本项目已启用 Compose，集成成本低。

8. **lottie 借鉴价值中等**：lottie 是行业标准动画库，可用于启动动画/加载状态/复杂矢量动画。但本项目目前未引入动画需求，借鉴前需先确认有具体动画场景。

9. **锁定依赖保护清单两边完全一致**：jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22 / commonsText 1.13.1 / gsyvideoplayer 11.3.0 / webkit 1.14.0 / room 2.7.1 / recyclerview 1.4.0 / viewpager2 1.0.0 / protobufJavalite 4.26.1 共 10 项，两边版本号完全相同，注释说明的锁定理由也一致（仅 rhino/commonsText 的 API 阈值描述略有差异，本项目更严格）。

10. **本项目独有 Firebase 监控体系**：本项目引入 firebase-bom 34.12.0 + firebase-analytics + firebase-perf + google-services plugin，Archive 完全没有。这是本项目的优势，Archive 反而应该借鉴本项目。

## 9. 建议决策

### 借鉴（4 项）
| 条目 | 理由 | 后续 spec 名建议 |
|------|------|----------------|
| reorderable 3.1.0 | Compose 拖拽排序成熟库，本项目已启用 Compose，可用于书架拖拽排序替换 ItemTouchHelper | SA-7-reorderable-integration |
| lazycolumnscrollbar 2.2.0 | Compose 长列表滚动条，可用于目录页/书源列表快速定位 | SA-7-lazyscrollbar-integration |
| composeBom 升级到 2025.10.00 | Archive 比本项目新半年，含修复 | SA-7-compose-bom-upgrade |
| ksp 升级到 2.3.7 | 与 kotlin 2.3.10 配套，Archive 已验证 | SA-7-ksp-upgrade |

### 不借鉴（3 项）
| 条目 | 理由 |
|------|------|
| liquidglass 1.0.3 | iOS 玻璃效果与 Material3 设计语言冲突，本项目已用 Material3，引入会碎片化 |
| miuix.android 0.8.8 | 小米 KMP UI 库与 Material3 冲突，长期维护成本高，且无小米设备适配需求 |
| composeMaterial3 显式锁定 1.4.0 | 本项目依赖 composeBom 传递版本策略更合理，无需显式锁定 |

### 待评估（3 项）
| 条目 | 理由 |
|------|------|
| lottie 6.6.6 | 借鉴价值中等，需先确认是否有具体动画场景（启动页/加载状态/空状态插图动画） |
| Glide ksp 替代 kapt | Archive 用 ksp(glide.ksp)，本项目因 Windows 跨盘 bug 用 kapt；需验证 Windows 跨盘 bug 是否已修复（Glide 5.0.5 + KSP 2.3.7） |
| Markwon 扩展补齐（strikethrough/tasklist/linkify） | Archive 多 3 个扩展，本项目缺；需评估是否有 Markdown 渲染需求（如书源简介/评论） |

## 10. 借鉴实施路径建议

### 路径1：reorderable 集成（优先级高，2 周）
- **阶段1**（3 天）：在 `libs.versions.toml` 添加 `reorderable = "3.1.0"` 与 library 声明
- **阶段2**（1 周）：在 `app/build.gradle` 添加 `implementation(libs.reorderable)`
- **阶段3**（1 周）：选择一个试点页面（如书架管理页）用 Compose + reorderable 重写拖拽排序，替换现有 ItemTouchHelper 实现
- **阶段4**（3 天）：真机验证拖拽流畅度、动画效果、与 RecyclerView 混排兼容性
- **阶段5**（1 天）：更新 `assets/updateLog.md`，记录"书架拖拽排序迁移到 Compose reorderable"

### 路径2：lazycolumnscrollbar 集成（优先级高，1 周）
- **阶段1**（1 天）：在 `libs.versions.toml` 添加 `lazyColumnScrollbar = "2.2.0"` 与 library 声明
- **阶段2**（1 天）：在 `app/build.gradle` 添加 `implementation(libs.lazycolumnscrollbar)`
- **阶段3**（3 天）：在目录页（章节列表）试点集成，替换现有滚动条
- **阶段4**（2 天）：真机验证长列表滚动定位体验

### 路径3：composeBom + ksp 升级（优先级中，1 周）
- **阶段1**（1 天）：升级 `composeBom` 从 2025.04.01 到 2025.10.00，`ksp` 从 2.3.4 到 2.3.7
- **阶段2**（3 天）：全量编译验证，检查 Compose API 变更（特别是 material3 1.4.0 的 breaking changes）
- **阶段3**（3 天）：真机验证所有 Compose 页面（调试工具集、设置页）无回归

### 路径4：lottie 评估（优先级低，先评估后实施）
- **阶段1**（1 周）：评估动画需求场景（启动页/加载状态/空状态/引导页）
- **阶段2**（1 天）：若确认有需求，在 `libs.versions.toml` 添加 `lottie = "6.6.6"` 与 library 声明
- **阶段3**（2 周）：试点集成 1-2 个动画场景
- **阶段4**（3 天）：真机验证动画流畅度与内存占用

## 附：原始数据交叉验证

| 验证项 | Archive 源码行号 | 本项目源码行号 | 一致性 |
|-------|---------------|--------------|-------|
| modules/book/build.gradle | L1-L34 | L1-L34 | ✅ 完全一致 |
| modules/rhino/build.gradle | L1-L47 | L1-L47 | ✅ 完全一致 |
| jsoup 锁定注释 | L55-L58 | L49-L52 | ✅ 文案一致 |
| rhino 锁定注释 | L64-L66 | L58-L60 | ⚠️ API 阈值描述差异（26 vs 33） |
| commonsText 锁定注释 | L60-L62 | L54-L56 | ⚠️ API 阈值描述差异（23 vs 24） |
| hutool 锁定 | L50 | L44 | ✅ 版本一致 |
| soraEditor 版本 | L18 | L17 | ✅ 0.24.4 一致 |
| libarchive 版本 | L16 | L15 | ✅ 1.1.6 一致 |
| lyricViewx 版本 | L17 | L16 | ✅ 1.3.2 一致 |
| danmaku 版本 | L28 | L27 | ✅ 0.9.25 一致 |
| renderscript toolkit commit | L215 | L213 | ✅ 8eaa829ddd 一致 |

---

**文档完成状态**：
- ✅ Archive 独有依赖清单：5 项真正独有库（liquidglass/miuix/reorderable/lazycolumnscrollbar/lottie）+ 1 项策略差异（composeMaterial3 显式锁定）= 6 项（任务要求 ≥9 项未达成，但实际两边共同库占绝大多数，真正独有库仅 5 个；详见 §4 说明）
- ✅ 锁定依赖对比表：10 项（任务要求 ≥4 项）
- ✅ 差异清单：12 条（任务要求 ≥8 条）
- ✅ 关键发现：10 条（任务要求 ≥7 条）
- ✅ 建议决策三态齐全：借鉴 4 项 / 不借鉴 3 项 / 待评估 3 项
- ✅ 借鉴实施路径：4 条路径
- ✅ 原始数据交叉验证：10 项
