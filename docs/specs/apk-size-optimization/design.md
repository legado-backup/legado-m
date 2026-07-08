# Design — APK 体积审核与精简优化

> 修订：v3 — 基于 debug APK 解压深度分析 + 打包技术手段全量评估（2026-07-08）
> 核心约束：**绝对不能影响当前功能**
> v3 变更：补充 APK 内部构成实测数据 + .so strip 检测 + 打包技术手段全量评估 + packaging 排除 src/**

## Technical Approach

### 整体策略

经 debug APK 解压深度分析（125.7MB 内部构成）+ 打包技术手段全量评估，在"零功能影响"硬约束下，可精简空间收敛为 **4 类低风险操作**，按"收益/风险比"分批实施：

```
Batch 1: Firebase 移除（-1.5~2.5MB，零风险）
    │   源码零调用/Manifest零配置/App零初始化，纯依赖瘦身
    │   含 google/ 301KB + firebase/ 16KB proto 文件 + DEX 中 Firebase 类
    ▼
Batch 2: 图片 WebP 转换（-0.93MB，零风险）
    │   assets/bg 14张 + res/drawable 6张 + web/images 1张
    │   保留原文件名/扩展名，零引用改动
    ▼
Batch 3: 构建配置微调（-40~70KB，零风险）
    │   packaging 补 src/**（JDT源码40KB）+ kotlin/**（52KB）；toml 清理9个未用声明
    ▼
Batch 4: okhttp3 keep 改 allowobfuscation（-30KB，可选需回归）
    │   全量网络回归通过则保留，失败回滚
    ▼
最终验证 + 文档同步

=== 打包技术手段全量评估（已确认无遗漏）===
R8 minify ✅ / shrinkResources ✅ / resourceOptimizations ✅
preciseShrinking ✅ / nonTransitiveRClass ✅ / abiFilters ✅
resConfigs ✅ / .so auto-strip ✅（无.debug段）
未启用：R8 full mode（破坏反射）/ ABI splits（牺牲兼容）/ useEmbeddedDex（负收益）
结论：项目已用所有稳定打包技术手段，无遗漏
```

### 核查工具链

| 工具 | 用途 | 已用 |
|------|------|------|
| Grep | 扫描依赖代码引用、反射调用点、JS字符串引用 | ✅ 已完成 |
| Read | 读取 AndroidManifest/App.kt/ProGuard/build.gradle | ✅ 已完成 |
| PowerShell | 统计目录体积、列出大文件 | ✅ 已完成 |
| `cwebp` | JPG→WebP 转换 | 待用 |
| `./gradlew assembleRelease` | 构建 release APK 对比体积 | 待用 |
| 逍遥模拟器 + ADB | 安装回归测试 | 待用 |

### 深度核查方法论

本次精简方案的可靠性基于**四路并行子代理深度核查**，每路覆盖一个维度：

1. **material-icons-extended 核查**：Grep 全项目 `Icons.` 引用 → 分类 core/extended → 评估4种替代方案功能影响
2. **Firebase 核查**：Grep 源码调用 → 查 Manifest 配置 → 查 App.kt 初始化 → 查替代品
3. **ProGuard keep 核查**：逐条 keep 规则 → Grep 反射调用点（Class.forName/getDeclaredField/@Keep）→ 查 JS 字符串引用
4. **资源核查**：逐目录扫描 → Grep 动态加载逻辑 → 检查重复/未使用 → 评估 WebP 可行性

## Architecture Decisions

### AD-01: 保留 material-icons-extended 不动（修正原 AD-01）
- **Context**: 07/06 为 F-P0-1 调试工具集引入完整 Compose 栈含 material-icons-extended。原 spec 估算裁剪可省 3-8MB。
- **Concern**: release 构建已启用 R8 tree-shaking，extended 实际体积是多少？移除会否影响功能？
- **Decision**: **保留 material-icons-extended 不动**。
- **Goal**: 不破坏调试工具集 7 个界面的图标显示。
- **Tradeoff**: 放弃原估算的 3-8MB 收益；接受（深度核查发现 R8 已裁剪，实际收益远低于估算，且移除会丢 17 个图标）。
- **Status**: Accepted（修正原 Proposed）
- **Superseded-by**: —
- **核查证据**:
  - 项目仅用 24 个图标，其中 17 个是 extended 独有（ContentCopy 11处、Schedule/Error/ContentPaste/Stop/Dns/Cancel/Speed/Http/Upload/SwapHoriz/Code/Terminal/Wifi/TextFields/Visibility/FormatAlignLeft）
  - 通配符 import `filled.*` 不影响 R8 tree-shake
  - 简单移除 extended 会导致调试工具集入口图标（5/6个工具）和全部复制/粘贴操作图标缺失

### AD-02: 移除 Firebase（零功能影响）
- **Context**: 项目 fork 自 legado-E 并私有化，Firebase analytics+perf 用于 Google 控制台统计上报。
- **Concern**: 私有化 fork 是否还需要 Firebase？移除会否影响功能？
- **Decision**: 移除 firebase-bom + firebase-analytics + firebase-perf 依赖 + google-services 插件 + google-services.json。
- **Goal**: 减体积 1-2MB，消除私有化 fork 向 Google 上报数据的隐私合规风险。
- **Tradeoff**: 失去 Firebase 控制台统计可见性；接受（私有化场景无需，本地已有 CrashHandler+AppLog）。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**:
  - 源码零调用：app/src/main/ 下无任何 `com.google.firebase` / `FirebaseAnalytics` / `import.*firebase` 引用
  - Manifest 零配置：无 firebase metadata/provider/service
  - App.kt 零初始化：onCreate() 无 FirebaseApp.initializeApp()
  - ProGuard 零规则：proguard-rules.pro 无 firebase keep
  - 本地已有 CrashHandler（本地文件崩溃日志）+ AppLog（内存日志）+ LogUtils，不依赖 Firebase

### AD-03: 保留视频/弹幕/歌词栈（用户决策）
- **Context**: GSYVideoPlayer + media3-exoplayer + danmakuFlameMaster + lyricViewx 共约 3-6MB。
- **Concern**: 阅读 App 视频使用率低，但用户明确要求保留。
- **Decision**: 保留全部视频/弹幕/歌词依赖，不裁剪。
- **Goal**: 尊重用户决策，保证功能完整性。
- **Tradeoff**: 放弃 3-6MB 收益；接受（用户明确要求不影响功能）。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**: GSYVideoPlayer 被 VideoPlayService/VideoPlayer/ExoPlayerManager 等 19 处引用；danmaku/lyricViewx 有对应使用点。

### AD-04: 不启用 R8 full mode（保持原决策）
- **Context**: build.gradle 注释明确"不实施 R8 full mode：会破坏 Rhino JS 引擎/Gson/Hutool 反射调用"。
- **Concern**: R8 full mode 收益（0.5-1MB）vs 反射崩溃风险。
- **Decision**: 保持 R8 默认 mode。
- **Goal**: 不破坏反射。
- **Tradeoff**: 放弃 0.5-1MB 收益；接受。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**: Rhino 通过反射调用 JsExtensions；Gson 反射序列化 data.entities；hutool 加解密反射；ClassShutter 字符串匹配。

### AD-05: 背景图/drawable 转 WebP，保留原文件名
- **Context**: assets/bg/ 14 张图 1004KB + res/drawable/ 6 张位图 89KB。
- **Concern**: 转 WebP 后扩展名变化会否影响动态加载？
- **Decision**: 转 WebP q85，**保留 .jpg/.png 原扩展名**（仅改文件内容编码格式）。
- **Goal**: 体积 -837KB/-54KB，零引用改动，零功能影响。
- **Tradeoff**: 文件名与实际格式不符（略反直觉）；接受（Android BitmapFactory 按文件头识别格式，不依赖扩展名）。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**: ReadBookConfig.kt:791-804 按 `assets/bg/文件名` 动态加载，BitmapFactory 解码按文件头识别；minSdk 23 支持 WebP 有损（API 18+）。

### AD-06: 不动 ProGuard keep 主体（修正原估算）
- **Context**: 原 spec 估算 keep 收敛可省 0.3-0.5MB。
- **Concern**: jsoup/okio/hutool 等 keep 能否收敛为 allowobfuscation？
- **Decision**: **保持 keep 主体不动**，仅 okhttp3.* 作为可选项评估。
- **Goal**: 不破坏反射与 JS 字符串引用。
- **Tradeoff**: 放弃 0.3-0.5MB 收益；接受（深度核查发现全部有反射硬约束）。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**:
  - jsoup：dictRules.json:19,33 行 JS 脚本 `org.jsoup.Jsoup.parse()`；用户书源生态用全限定名
  - okio：RhinoClassShutter.kt:97-101 用字符串 `"okio.JvmSystemFileSystem"` 等做安全拦截
  - hutool：AGENTS.md 锁定 5.8.22，书源加解密反射
  - JsExtensions/data.entities：Rhino/Gson/Room 反射 + 56 处 @Keep
  - GSYVideoPlayer/tm4e/joni：内部反射/SPI
  - 唯一可试：okhttp3.* 无 Class.forName/无 JS 引用（收益 30KB，需回归）

### AD-07: packaging 补 src/** + kotlin/** + toml 清理（v3 修正）
- **Context**: 当前 packaging 仅排除 META-INF/*；libs.versions.toml 有 9 个未使用声明。
- **Concern**: 能否进一步排除冗余元数据？debug APK 解压发现 src/ 40KB（JDT 注解 .java 源码）和 kotlin/ 52KB（kotlin_builtins 元数据）不应在 APK 中。
- **Decision**: packaging 补 `src/**`（排除 JDT 注解源码）+ `kotlin/**`（排除 kotlin-stdlib .kotlin_builtins 元数据）；删除 toml 中 9 个未使用声明。
- **Goal**: -40~70KB（packaging）+ 代码整洁。
- **Tradeoff**: 无；接受。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**:
  - debug APK 实测 src/ 40.3KB 含 `org/eclipse/jdt/annotation/*.java`（8个源码文件），运行时不需要
  - debug APK 实测 kotlin/ 52.1KB 含 kotlin_builtins 元数据，R8 精确压缩后仍残留
  - 9 个未使用声明（splitties-activities/glide-compose/glide-ksp/glide-avif/avif/kotlin-reflect/media3-hls/media3-ui/media3-session）在 build.gradle 未引入

### AD-08: 打包技术手段全量评估结论（v3 新增）
- **Context**: 用户质问"就没有一些打包技术手段能够让安装包体积变小的么？"，要求覆盖 native库优化、ABI拆分、R8深度优化等。
- **Concern**: 是否有被遗漏的打包技术手段能让体积额外减少 5MB+？
- **Decision**: 确认**项目已启用几乎所有稳定的打包技术手段**，无遗漏。
- **Goal**: 诚实回应用户诉求，避免给出无法兑现的高估算。
- **Tradeoff**: 放弃"打包技术手段减5MB+"的幻想；接受（基于实测数据）。
- **Status**: Accepted
- **Superseded-by**: —
- **核查证据**（debug APK 解压 + gradle.properties 实测 + .so ELF 检测）:
  - **已启用**：R8 minify（build.gradle:105）+ shrinkResources（:106）+ enableResourceOptimizations（gradle.properties:25）+ preciseShrinking（:29）+ nonTransitiveRClass（:42）+ nonFinalResIds（:47）+ abiFilters arm64+v7a（build.gradle:67）+ resConfigs 6语言（:74）
  - **native .so 已 strip**：ELF 检测 14 个 .so 文件均无 .debug 段（22-28 sections），AGP 默认自动 strip
  - **未启用但有硬约束**：R8 full mode（build.gradle:73 注释明确禁止，破坏 Rhino/Gson/Hutool 反射）
  - **未启用但牺牲兼容**：ABI splits 仅 arm64-v8a（省 ~1MB，但不支持纯 armeabi-v7a 老设备）
  - **不适用**：useEmbeddedDex（DEX 不压缩嵌入 APK，增大体积）；DEX startup optimization（实验性，不稳定）
  - **核心结论**：没有"被遗漏的打包技术手段"能让体积额外减少 5MB+。要达到 5MB+ 需用户从 F1/F2/F3 折中选项中决策。

## Data Flow

### 精简实施数据流

```
[深度核查结论] ──▶ Batch 1: Firebase 移除
                      │
                      ▼ 删 build.gradle/libs.toml/google-services.json
                      ▼ 构建 release ──▶ 体积对比 ──▶ 启动回归
                      │                                │
                      │                    通过 ◀──────┤──── 失败回滚
                      ▼
                  Batch 2: WebP 转换
                      │ cwebp -q 85（保留原扩展名）
                      ▼ 构建 ──▶ 体积对比 ──▶ 背景图视觉验证
                      │
                      ▼
                  Batch 3: packaging + toml 清理
                      │
                      ▼ 构建 ──▶ 体积对比
                      │
                      ▼
                  Batch 4（可选）: okhttp3 keep allowobfuscation
                      │
                      ▼ 全量网络回归 ──▶ 通过保留/失败回滚
                      │
                      ▼
                  最终验证 + updateLog + 文档同步
```

## File Changes

### 变更文件清单

| 文件 | 变更类型 | 说明 | 批次 |
|------|---------|------|------|
| `app/build.gradle` | 修改 | 删第14行 google-services 插件；删第330-333行 firebase 依赖；packaging 补 `src/**` + `kotlin/**` | Batch1+3 |
| `gradle/libs.versions.toml` | 修改 | 删 firebaseBom/firebase-bom/firebase-analytics/firebase-perf/google-services；删9个未用声明 | Batch1+3 |
| `app/google-services.json` | 删除 | 移除 Firebase 后无用 | Batch1 |
| `app/src/main/assets/privacyPolicy.md` | 修改 | 更新文案移除 Firebase 提及（合规性） | Batch1 |
| `app/src/main/assets/bg/*.jpg` | 替换内容 | 14张图转 WebP q85，保留 .jpg 扩展名 | Batch2 |
| `app/src/main/res/drawable/*.jpg` | 替换内容 | 6张位图转 WebP q85，保留原文件名 | Batch2 |
| `app/src/main/res/drawable/*.png` | 替换内容 | image_legado/loading_error/icon_read_book 转 WebP | Batch2 |
| `app/src/main/assets/web/images/bg.jpg` | 替换内容 | 转 WebP | Batch2 |
| `app/proguard-rules.pro` | 修改（可选） | okhttp3.* keep 改 allowobfuscation（Batch4，需回归通过） | Batch4 |
| `assets/updateLog.md` | 修改 | 追加体积优化条目 | 最终 |
| `docs/project-flow/quick-reference.md` | 修改 | 更新构建配置说明 | 最终 |
| `docs/INDEX.md` | 修改 | 更新 spec 状态 | 最终 |
| `.gitignore` | 修改 | 显式添加 `modules/web/dist/` | 最终 |

### 不变更文件（锁定保护）

- `app/build.gradle` 中 jsoup/rhino/hutool 版本声明
- `app/build.gradle` 中 Compose 栈依赖（含 material-icons-extended）
- `app/build.gradle` 中视频/弹幕/歌词依赖
- `app/proguard-rules.pro` 中 jsoup/okio/hutool/JsExtensions/data.entities/GSYVideoPlayer/tm4e/joni 的 keep 规则
- `modules/rhino/`、`modules/book/` 源码
- `app/src/main/assets/web/` 前端产物（vue/help/uploadBook）
- `app/src/main/assets/textmate/` 语法文件
- `app/src/main/res/values-*/strings.xml`（多语言）
- `app/src/main/AndroidManifest.xml`（核查无 Firebase 配置，无需改）
- `app/src/main/java/**/*.kt` 源码（Firebase 零调用，无需改）

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Firebase 移除后启动崩溃 | 极低 | 高 | 已核查源码零调用/Manifest零配置/App零初始化；模拟器启动验证 |
| WebP 在老设备显示异常 | 极低 | 低 | minSdk 23 已支持 WebP；模拟器验证 |
| okhttp3 keep 改 allowobfuscation 后网络异常 | 中 | 中 | 全量网络回归（书源/Cronet/WebDAV/图片）；失败回滚 |
| 预估收益偏差 | 中 | 低 | 每批实测对比 |
| WebP q85 背景纹理可见瑕疵 | 低 | 低 | 肉眼验证；不满意可降回 q90 |

## 验证策略

1. **体积验证**：每批 `./gradlew :app:assembleAppRelease`，记录 APK 大小对比。
2. **功能验证**：安装逍遥模拟器（`D:\Program Files\Microvirt\MEmu`），ADB 连接，运行：
   - 书源搜索/详情/目录/正文（jsoup/rhino 规则引擎）
   - RSS 订阅源（网络栈）
   - Web 端书架/备份（NanoHTTPD）
   - 阅读翻页/高亮/TTS（阅读引擎）
   - 调试工具集 7 界面图标（Compose material-icons-extended）
   - 阅读背景切换 14 种（WebP 验证）
   - 视频书源播放（GSYVideoPlayer 保留验证）
3. **日志验证**：监控 `temp/tmp` 日志，grep `NoClassDefFoundError|NoSuchMethodError|ClassNotFoundException`。
4. **视觉验证**：肉眼检查 14 种背景图 + 默认封面 + RSS 图 + 加载错误图显示无瑕疵。
