# C5 用户日志勾选体系 + 工程纪律实施级设计

> 对应 `design.md` AD-06（工程纪律借入"用户日志+防泄露+产物验证"三件，不借其禁测宪法）。
> 证据源：`evidence-pack.md` §F/§G/§L；legadoC 源码 `F:\myself\github\WeAgentChat\temp\legadoC_src\legadoC-own`。
> 本文档为实施级设计（OpenSpec 步骤 2 输入），零源码变更。
> 总线修订 2026-08-31：fromTag 映射表登记规则改为"按实施时 AppLog 实际全集登记"（ng P0/P1/P2 将新增 Tag），不锚定 26 TAG 基线（master-track tasks 1.8.2，X6）

## 1. 目标与非目标

### 1.1 目标

| # | 目标 | 来源 |
|---|------|------|
| G1 | 用户日志模块勾选体系：LogModule 按类名自动归属 + 钉定表 + 勾选 UI + app.log 持久化重启恢复 | legadoC §F |
| G2 | 与本项目现有 26 TAG AI 采集体系**叠加**成双层日志架构，两层共存不冲突 | AD-06 Decision |
| G3 | pre-push 防泄露 hook + 发布清洗脚本范式，适配本项目敏感物路径清单（jks/output/temp/bak） | legadoC §G |
| G4 | 交付产物验证纪律：aapt dump badging + apksigner verify 下沉到 build-legado.bat 单包门禁 | legadoC AGENTS.md:209-217 |

### 1.2 非目标

- **不引入** legadoC"工作模式五级分层"禁测宪法（本项目 ai_tests 是核心资产，AD-06 明确排除）。
- **不替换**现有 26 TAG 体系：`putDebugWithTag` / `adb logcat -s` 采集链路一行不动。
- **不建双仓**：本项目当前为单私有仓（`github.com/syq17496152/legado.git`），无公开镜像；防泄露 hook 只做**按需启用的机械兜底范式**（见 §4.4）。
- 不改 LogUtils（文件日志 `externalCacheDir/logs/` 7 天清理机制保持现状）。
- 无数据库变更（勾选状态存 SharedPreferences StringSet），零 Room migration。

## 2. legadoC 源码证据（逐函数）

### 2.1 LogModule.kt（`app/src/main/java/io/legado/app/constant/LogModule.kt`）

| 位置 | 内容 | 设计要点 |
|------|------|---------|
| :14-24 | `enum class LogModule(val labelRes: Int)` 十模块：GENERAL 兜底常显 + READ_ALOUD/BAIDU_TTS/TTS_CACHE/AI_CAST/DOWNLOAD_CACHE/READING/SOURCE_NETWORK/PERFORMANCE/AI 九个可勾选 | 枚举即模块清单，labelRes 挂 UI 文案 |
| :28-40 | `selectable: List<LogModule>` | 不含 GENERAL，顺序即弹窗展示顺序 |
| :42 | `selectableNames: Set<String>` | 勾选持久化的白名单校验基准 |
| :44-61 | `pinnedByClassPrefix: List<Pair<String, LogModule>>` 钉定表 | 显式归属表优先于关键词匹配；用于收纳**同时命中多组关键词**的类（bdtts 含 tts、bdreadaloud 含 readaloud、ttscache 含 tts、localBook 内嵌 JsExtensions 双命中）；前缀按"外层类名"写，天然覆盖内部类 `$`/companion/Kt 文件变体 |
| :68-154 | `classify(callerClassName: String?): LogModule` | 单点归类：null/blank → GENERAL；先钉定表前缀匹配（`startsWith`，lowercase 后）；再 `when` 关键词 `containsAny`（:156-158），分组内有序（ttscache 先于 tts、bdtts 先于 readaloud 判定）；**未匹配一律归 GENERAL，保证不丢日志也不需逐调用点打标** |

### 2.2 AppLog.kt（`app/src/main/java/io/legado/app/constant/AppLog.kt`）

| 位置 | 内容 | 设计要点 |
|------|------|---------|
| :22-27 | `Entry(time, message, throwable, module)` | 模块在写入时单点判定 |
| :29-31 | `init { loadPersisted() }` | object 首次触达即恢复历史日志 |
| :42-46 | `logsForView(shownModules)` | GENERAL 恒显 + 其余按勾选过滤，`synchronized` 内快照 |
| :48-75 | `put(message, throwable?, toast?, module?)` | `module ?: callerModule()` 自动归属；100 条内存环（:59-61 `removeLastOrNull`）；新条目 `add(0, ...)` 头插 |
| :83-89 | `callerModule()` | `Thread.currentThread().stackTrace` 找第一个非 AppLog/非 Thread 帧 → `LogModule.classify` |
| :135-144 | `putDebug` | "记录调试日志开关已删"——调试日志始终记录，是否显示由模块勾选决定 |
| :146-156 | `persist(entry)` | `filesDir/app.log` 逐条 `appendText`：`time\tBase64(msg)\tBase64(stack)\tMODULE\n`；Base64 NO_WRAP 防止 tab/换行注入；失败 `runCatching` 静默不阻断 |
| :158-177 | `loadPersisted()` | `readLines().takeLast(100)`；按 `\t` 拆列，`decodeModule`（:180-183）兼容无模块列的旧格式（`[AI]` 前缀 → AI 模块） |
| :185-192 | `rewritePersisted()` | clearAi 后全量重写文件 |

### 2.3 勾选 UI 与查看过滤

- `ui/config/OtherConfigFragment.kt:242-268` `showLogShownModulesDialog()`：alert DSL 多选弹窗（legadoC 原生实现；本项目对齐 architecture.md 铁律 3 改用 Compose 多选弹框族，见 §4.3 入口 B），okButton 保存 `putPrefStringSet(PreferKey.logShownModules)`，negativeButton 全选，neutralButton 恢复默认（removePref → 空 set）。
- `help/config/AppConfig.kt:87-92/185-188`：`logShownModules` 白名单过滤（`it in LogModule.selectableNames`）防脏数据；`debugLogEnabled = logShownModules.isNotEmpty()` 联动重型诊断开关。
- `ui/about/AppLogDialog.kt:63-66`：`visibleLogs() = AppLog.logsForView(AppConfig.logShownModules)`，**显示与复制共用同一份数据**；:48-52 `observeEvent(APP_LOG_CHANGED)` 实时刷新。

### 2.4 工程纪律（`.githooks/` + `publish-oss-source.ps1` + AGENTS.md）

| 文件:行 | 内容 |
|---------|------|
| `.githooks/pre-push:10-30` | 禁直推公开仓：remote 名为 origin 或 name/URL 匹配公开仓名结尾 → `refs/heads/own` 一律 exit 1；私有仓名不同后缀天然不匹配。定位"只做机械兜底，不改规则" |
| `.githooks/commit-msg:10-24` | 中文提交校验：豁免 `^Merge|^Revert`；MSYS2 grep ERE 不支持 `\xHH`，改用 `tr -d '\n\r'` 后 `[^ -~]` 探测 0x80+ 字节 |
| `publish-oss-source.ps1:37-44` | 剥离清单 6 条路径（相对仓库根）集中声明 |
| :46-47 | `git filter-repo` 可用性预检（pip install git-filter-repo） |
| :53-65 | 临时克隆（filter-repo 要求新克隆）→ `--force --invert-paths` 逐路径剥离，纯专有提交变空被剪除 |
| :67-71 | **全历史零命中校验**：`git log --all --oneline -- <path>` 逐条断言为空，失败 throw |
| :73-85 | 确定性时间戳注入空壳引导提交（`GIT_AUTHOR_DATE/COMMITTER_DATE` 固定，保证清洗哈希可复现） |
| :99-106 | 从临时克隆 `--force` 推清洗镜像（本地历史与远端不同，非快进必拒 = 泄露保护） |
| AGENTS.md:209-217 | 产物验证：`aapt.exe dump badging` + `apksigner.bat verify --print-certs`，交付前确认包名/版本号递增/中文名/abi/退出码 0 |

## 3. 本项目对接点现状 + 双层日志架构设计

### 3.1 现状清单

| 对接点 | 现状 | 差距 |
|--------|------|------|
| `constant/AppLog.kt` | 26 TAG 常量（:13-42 `TAG_WEB_BOOK`…`TAG_THOUGHT_EXPORT`）+ `Level` 枚举（:44）+ `LogEntry(time,message,throwable,level)`（:46-51）+ 100 条内存环 + `truncateSafely`（:63-75，data URI 专项截断/代码点安全截断）+ `put/putError/putWarn/putInfo/putNotSave/putDebug/putDebugWithTag`（:148-174，recordLog 守卫 + tag 透传 logcat） | **无 module 归属、无 logsForView、无持久化**；LogEntry 无 module 字段 |
| `ui/about/AppLogDialog.kt` | 已 Compose 化：`ComposeDialogFragment` + `AppDialogFrame` + `LazyColumn`（:54-176），Level 过滤菜单（AppDropdownMenu+MenuAction :110-160）；`logs = remember { mutableStateOf(AppLog.logs) }`（:66） | **一次性快照无实时刷新**（legadoC 有 `observeEvent(APP_LOG_CHANGED)`）；无模块维度过滤 |
| `constant/EventBus.kt` | 无 `APP_LOG_CHANGED` 事件 | 需新增 |
| `help/config/AppConfig.kt:91/:188` | 已有 `recordLog`（putDebugWithTag 守卫）；PreferKey.kt:64 `recordLog` | 无 `logShownModules` |
| `ui/config/OtherConfigFragment.kt` | 存在（preference 方式，与 legadoC 同构） | 无日志模块勾选入口 |
| `apk-publish-workflow.md §2.2 Stage3` | 一键编排器 `scripts/publish_release.py` **已有** apksigner 验签 + aapt2 badging 包名版本一致性（R5 致命项，:456-474）+ libcronet.so 三包检查 | 一键发布已覆盖 |
| `build-legado.bat` | 仅 libcronet.so 强制校验块（:186-215，Expand-Archive 检查 so）；`EnableDelayedExpansion` 已修复 | **单包构建场景缺 aapt/apksigner 门禁**（日常调试包/单发 release 包不经过 publish_release.py） |
| `.gitignore` | 已含 `temp/ output/ *.jks *.keystore *.bak bak/ bak-*/ scripts/publish_config.json *.log .trae/memory/cache/` | 敏感物豁免清单基本齐；无 pre-push 机械兜底 |

### 3.2 双层日志架构（核心设计）

```
┌─────────────────────────── AppLog 单例（唯一汇聚点）───────────────────────────┐
│                                                                              │
│  AI 层（现有 26 TAG，不动）                 用户层（C5 新增）                    │
│  ─────────────────────────                ─────────────────────────           │
│  putDebugWithTag(tag, msg, level)          put/putError/putWarn/putInfo       │
│    ├─ LogUtils.d(tag, …)   → 文件日志        ├─ classify(调用方类名) 自动归属    │
│    ├─ Log.e(tag, …)        → logcat         ├─ level + module 双维度入 Entry    │
│    └─ ai_tests: adb logcat -s <TAG>          ├─ persist → filesDir/app.log     │
│    ▲ recordLog 守卫不变                      └─ logsForView(勾选) → AppLogDialog │
│                                                                              │
│  交叉点 ①：mLogs 内存环共享——putDebugWithTag 通过 tagToModule(tag) 显式映射表    │
│  打上 module，两条路径写入同一个 100 条环；AI 层采集走 logcat 不受勾选影响，        │
│  勾选只过滤 AppLogDialog 显示与复制。                                            │
│  交叉点 ②：LogEntry 增加可空 module 字段（默认 GENERAL），AI 层调用方零改动。      │
└──────────────────────────────────────────────────────────────────────────────┘
```

**共存不冲突的三条铁律**：

1. **AI 层输出通道不变**：26 TAG → `LogUtils.d` + `Log.e(logcat)` 的过滤采集链路是 ai_tests 的采集契约（`adb logcat -s <TAG>:E`），C5 不触碰任何 tag 透传逻辑。勾选体系只作用于"用户可见视图"，logcat 采集与用户勾选**正交**。
2. **用户层归属自动兜底**：`put/putError/...` 不要求调用方传 module，`classify` 按调用方类名自动归属，未匹配归 GENERAL——存量 200+ 个 `AppLog.put` 调用点**零改动**获得模块归属。
3. **AI 埋点显式映射**：`putDebugWithTag` 走 `tagToModule(tag)` 显式映射表（26 TAG 全覆盖，编译期常量表），避免高频埋点路径再付一次 stackTrace 成本；映射 miss 时 fallback 到 `callerModule()`。

### 3.3 全局思考检查清单（6 维，门禁要求）

- **前端入口**：AppLogDialog（模块过滤菜单）、OtherConfigFragment（勾选偏好入口）——共 2 处，无遗漏场景（日志无 RSS/书源分场景入口）。
- **后端接口**：AppLog.put 系 5 个方法签名不变（新增可选参数带默认值）；putDebugWithTag 签名不变。
- **数据库改动**：否（StringSet 偏好）。
- **覆盖安装**：兼容（无 schema 变更；app.log 为新增文件，旧版本无此文件时 loadPersisted 直接 return）。
- **使用场景**：用户查日志（过滤降噪）/ AI 真机采集（logcat 不受影响）/ 重启后回看（持久化恢复）三场景全覆盖。
- **回填点**：真实使用层（put 系 5 方法 + putDebugWithTag）、调试层（EventBus 通知 UI 刷新）、校验层（单测归属表 + L2 重启断言）。

## 4. 改造方案（逐文件函数级）

### 4.1 新增 `constant/LogModule.kt`（分类器 Kotlin 骨架 + 本项目模块清单映射）

```kotlin
package io.legado.app.constant

import androidx.annotation.StringRes
import io.legado.app.R

/**
 * 用户日志模块归属。GENERAL 兜底常显；其余模块由"日志模块勾选"控制是否显示。
 * 双层架构：本枚举只影响 AppLogDialog 显示/复制，不影响 AI 层 logcat 采集（26 TAG 链路不动）。
 */
enum class LogModule(val labelRes: Int) {
    GENERAL(R.string.log_module_general),
    SOURCE_NETWORK(R.string.log_module_source_network), // TAG_WEB_BOOK/TAG_ANALYZE/TAG_HTTP/TAG_SOURCE_MECHANISM/TAG_NETWORK_LOG
    RSS(R.string.log_module_rss),                       // TAG_RSS
    READING(R.string.log_module_reading),               // TAG_CONTENT/排版/ContentTextView
    READ_ALOUD(R.string.log_module_read_aloud),         // 朗读/TTS/AudioPlayService
    VIDEO(R.string.log_module_video),                   // 视频播放器（本项目独有）
    IMAGE(R.string.log_module_image),                   // TAG_IMAGE_CANVAS/DETAIL/PLAY/SNIFF
    DOWNLOAD_CACHE(R.string.log_module_download_cache), // CacheBook/下载
    AI(R.string.log_module_ai),                         // ui/main/ai + AI 套件
    PERFORMANCE(R.string.log_module_performance);       // TAG_MEMORY_PRESSURE/CACHE_STATS/CACHE_CONCURRENT/FreezeMonitor

    companion object {
        val selectable: List<LogModule> get() = entries.filter { it != GENERAL }
        val selectableNames: Set<String> = selectable.map { it.name }.toSet()

        /** 钉定表：调用方类名（lowercase 含包名）前缀命中即唯一归属，优先于关键词匹配 */
        private val pinnedByClassPrefix: List<Pair<String, LogModule>> = listOf(
            // 示例骨架（实施时按归属表单测补齐）：
            // "io.legado.app.model.localbook.textfile\$jsextensions" to READING（防 READING+SOURCE_NETWORK 双命中）
            // "io.legado.app.ui.rss.read.readview…" 类 RSS/READING 双命中类逐条钉定
        )

        fun classify(callerClassName: String?): LogModule {
            if (callerClassName.isNullOrBlank()) return GENERAL
            val name = callerClassName.lowercase()
            pinnedByClassPrefix.firstOrNull { name.startsWith(it.first) }?.let { return it.second }
            return when {
                containsAny(name, "freezemonitor", "dispatchersmonitor", "memorypressure",
                    "cachestats", "cacheconcurrent", "liveeventbus", "threadutils") -> PERFORMANCE
                // 先于 READ_ALOUD：含 tts 子串的缓存/引擎类需按钉定表或本组顺序裁决
                containsAny(name, "audioplay", "readaloud", "aloudservice", "tts") -> READ_ALOUD
                containsAny(name, "imagecanvas", "imagedetail", "imageplay", "imagesniff",
                    "imageurl", "coverimage") -> IMAGE
                containsAny(name, "videoplayer", "videobook", "videoextractor", "gsyvideo",
                    "exoplayer", "m3u8", "hls") -> VIDEO
                containsAny(name, "cachebook", "download", "bookhelp") -> DOWNLOAD_CACHE
                containsAny(name, "rss") -> RSS
                containsAny(name, "aichat", "aiprovider", "aitask", "aiworld") -> AI
                containsAny(name, "readbook", "textchapterlayout", "chapterprovider",
                    "contenttextview", "contentprocess", "readview", "localbook", "epubfile",
                    "mobifile", "pdffile", "textfile", "bookmark") -> READING
                containsAny(name, "webbook", "analyze", "jsextensions", "regexjsextensions",
                    "cronet", "cookiestore", "networkutils", "okhttp", "http",
                    "basesource", "booksource", "rsssource", "searchmodel", "source") -> SOURCE_NETWORK
                else -> GENERAL
            }
        }

        /** AI 层 26 TAG → 模块显式映射（putDebugWithTag 专用，免 stackTrace 开销） */
        fun fromTag(tag: String): LogModule? = when (tag) {
            AppLog.TAG_WEB_BOOK, AppLog.TAG_ANALYZE, AppLog.TAG_HTTP, AppLog.TAG_SOURCE_MECHANISM,
            AppLog.TAG_NETWORK_LOG -> SOURCE_NETWORK
            AppLog.TAG_RSS -> RSS
            AppLog.TAG_CONTENT -> READING
            AppLog.TAG_IMAGE_CANVAS, AppLog.TAG_IMAGE_DETAIL, AppLog.TAG_IMAGE_PLAY,
            AppLog.TAG_IMAGE_SNIFF -> IMAGE
            AppLog.TAG_MEMORY_PRESSURE, AppLog.TAG_CACHE_STATS, AppLog.TAG_CACHE_CONCURRENT -> PERFORMANCE
            AppLog.TAG_WEBDAV_BACKUP, AppLog.TAG_DATA -> GENERAL
            // 其余 TAG（WebView/CRYPTO_SCOPE/DECOMPRESS/…）实施时逐条映射，miss 返回 null 走 callerModule()
            else -> null
        }

        private fun containsAny(source: String, vararg keywords: String): Boolean =
            keywords.any { source.contains(it) }
    }
}
```

> 顺序敏感注释：`rss` 与 `rsssource`、`ai` 与业务词（如 `certai(n)` 类误命中）——实施时**必须先跑归属表驱动单测再合入**（§8），双命中类一律进钉定表，不允许靠 when 分支顺序裁决（legadoC LogModule.kt:44-50 纪律）。

### 4.2 改造 `constant/AppLog.kt`（双层共存改造，存量调用点零改动）

| 改动 | 函数级方案 |
|------|-----------|
| LogEntry 加字段 | `data class LogEntry(..., val level: Level = Level.ERROR, val module: LogModule = LogModule.GENERAL)`——带默认值，200+ 存量调用点零改动 |
| put/putError/putWarn/putInfo/putNotSave/putEntry | 内部统一 `module ?: callerModule()`；`callerModule()` 照搬 legadoC :83-89（stackTrace 首个非 AppLog/Thread 帧 → classify）。`truncateSafely` 保持前置（本项目已有，legadoC 没有） |
| putDebugWithTag | 首行加 `val mod = LogModule.fromTag(tag) ?: callerModule()`，写环时带上；tag→LogUtils/Log.e 透传逻辑一行不动 |
| persist | 新增 `private fun persist(entry)`：`"${entry.time}\t${entry.level.name}\t" + Base64(msg) + "\t" + Base64(stack) + "\t${entry.module.name}\n"` appendText 到 `filesDir/app.log`；**仅 putEntry/putDebugWithTag 路径持久化**，putNotSave 语义就是"不保存"维持不落盘；写入后行数 > 500 时滚动截断重写保留末 100 行（改进 legadoC 无上限 append 的膨胀缺陷，§6 R3） |
| loadPersisted | init 触发；格式 `time\tLEVEL\tb64msg\tb64stack\tMODULE`，按列数容错（缺 LEVEL 列默认 ERROR、缺 MODULE 列走 GENERAL）；`takeLast(100)` + `reverse()` 头插序 |
| logsForView | `fun logsForView(shownModules: Set<String>): List<LogEntry>`——GENERAL 恒显 + 勾选模块过滤，`synchronized` 快照 |
| EventBus 通知 | put 系写入后 `postEvent(EventBus.APP_LOG_CHANGED, mLogs.size)`；EventBus.kt 新增 `const val APP_LOG_CHANGED` 常量（本项目 EventBus 为 object + const val 常量集合，非枚举，见 `constant/EventBus.kt:4-8`） |
| 脱敏铁律前置 | persist 与内存环共用同一条消息（已过 `truncateSafely`）；调用点脱敏遵守 logging_rules.md:133-137（URL 路径模式化/凭证 `***`/源名编号化），app.log 落盘使脱敏从"建议"升级为"铁律"（§6 R4） |
| JVM 单测安全 | persist/load 逻辑抽为 `internal fun serializeEntry/deserializeLine(file: File)` 纯函数（File 参数注入），AppLog 组合之——JVM 测试不经 splitties appCtx（对齐 recordLogOrOff() :125-129 既有守卫思路） |

### 4.3 勾选 UI（对齐本项目设置页/组件族，两入口）

**入口 A（主）：AppLogDialog 内模块过滤菜单**（`ui/about/AppLogDialog.kt`）

- 与现有 Level 过滤菜单并排：新增 `LegadoMiuixActionButton("模块")` + `AppDropdownMenu`，`MenuAction` 列表 = `LogModule.selectable`（GENERAL 常显不进菜单）；勾选状态存 `AppConfig.logShownModules`。
- 数据源切换：`AppLog.logs` → `AppLog.logsForView(AppConfig.logShownModules)`，与复制/清空共用同一份数据（legadoC AppLogDialog.kt:63 显示=复制共用纪律）。
- 实时刷新：Fragment `observeEvent<Int>(EventBus.APP_LOG_CHANGED)` → 更新 `logs` mutableState（补齐本项目当前一次性快照缺陷）。
- 行组件 `AppLogRow` 增加模块徽标前缀（`[模块名]` 文本，复用 `formatLogMessage` 前缀机制 :205-213），与 `[E]/[W]` 级别前缀并排。

**入口 B（辅）：OtherConfigFragment 偏好入口**（对齐 legadoC OtherConfigFragment.kt:242-268）

- preference XML 新增 `logShownModules` 条目（"日志模块勾选"），点击弹出 Compose 多选弹框（对齐 `ui-standards/architecture.md` 铁律 3：禁止新建 alert{} DSL；复用 `ui/widget/compose/ComposeChoiceListDialog.kt` 既有先例挂载候选模块清单）；legadoC 的全选/恢复默认两按钮语义保留（转由弹框底部操作区实现）。
- `AppConfig` 新增 `var logShownModules`（`private set` + `readLogShownModules()` 白名单过滤 `it in LogModule.selectableNames` 防脏数据，照搬 legadoC AppConfig.kt:185-188）+ `upConfig` 分支；PreferKey 新增 `const val logShownModules = "logShownModules"`。
- strings.xml 新增 `log_module_*`（10 条）+ `log_shown_modules_t`，中文文案。

### 4.4 pre-push 防泄露 hook + 发布清洗脚本范式（适配本项目路径清单）

**现状定位**：本项目单私有仓、无公开镜像，legadoC 的"双仓双历史"架构不适用；借的是**范式**——hook 机械兜底 + 剥离清单 + 零命中校验三件套，作为"未来开源/外发"时的即插即用资产。

1. **`.githooks/pre-push`（新增，启用需 `git config core.hooksPath .githooks`）**：
   - 规则适配：本项目敏感物 = `*.jks` / `*.keystore` / `output/` / `temp/` / `bak*/` / `scripts/publish_config.json`（API token）/ `.trae/memory/`（本地记忆）。
   - 校验逻辑：读取 stdin 的 `<local_ref> <local_sha> <remote_ref> <remote_sha>`，对待推 sha 执行 `git diff --name-only <remote_sha>..<local_sha>`，命中敏感路径 → exit 1 并提示"走打包交付而非 git 推送"（本项目 APK 才是交付物，源码仓本就私有）。
   - 保留 legadoC 两原则：只做机械兜底不改规则（AGENTS.md 为规则源）；MSYS2 兼容写法（`LC_ALL=C grep`，禁 `\xHH`）。
2. **`commit-msg`（可选引入）**：中文提交校验照搬 legadoC :10-24（`^Merge|^Revert` 豁免 + `[^ -~]` 多字节探测）；本项目 Conventional Commits 主体中文化，兼容 `feat: 中文描述`。
3. **`scripts/publish-clean-source.ps1`（范式预留，不默认执行）**：
   - `stripPaths` 适配本项目：`*.jks`、`output/`、`temp/`、`bak*/`、`scripts/publish_config.json`、`ai_tests/`（含真机行为数据）、`.trae/memory/`。
   - 保留 legadoC 三步核心：临时克隆 → `git filter-repo --invert-paths` 逐路径剥离 → `git log --all -- <path>` 逐条**零命中校验** throw。
   - **不移植**：确定性空壳注入提交（legadoC 为保公开树可编译的私有机制）、双备份仓推送（本项目无此拓扑）。头部注释声明"启用前必须先更新本清单与 AGENTS.md 同步"。

### 4.5 交付产物验证纪律（build-legado.bat 门禁段草案 + 规范补记）

**现状**：`publish_release.py` Stage3 已有 apksigner/aapt2（:456-474），但 `build-legado.bat` 单包场景只有 libcronet.so 校验——日常 `build-legado.bat release` 后手工交付/测试包分发不经过一键编排器，缺门禁。

`build-legado.bat` 在 libcronet.so 校验块（:186-215）之后、`:STOP_DAEMON`（:217）之前新增产物校验段（仅 release 包执行，debug 包跳过保持构建速度）：

```bat
:: ============================================================
:: APK 产物验证（强制，仅 release；来源: C5 对齐 legadoC AGENTS.md:209-217）
:: aapt dump badging 包名/版本 + apksigner verify 退出码门禁
:: ============================================================
if "!BUILD_TYPE!"=="release" if "!APK_FOUND!"=="1" (
    for %%f in ("%DIST_DIR%\*.apk") do (
        call :VERIFY_APK "%%f" || (echo [FAIL] 产物校验未通过，禁止交付 %%~nxf & exit /b 1)
    )
)
goto :EOF

:VERIFY_APK
set "BT_VER="
for /f "tokens=* delims=" %%v in ('dir /b /ad "%ANDROID_HOME%\build-tools" ^| sort') do set "BT_VER=%%v"
set "AAPT=%ANDROID_HOME%\build-tools\%BT_VER%\aapt.exe"
set "APKSIGNER=%ANDROID_HOME%\build-tools\%BT_VER%\apksigner.bat"
"%AAPT%" dump badging "%~1" | findstr /r "^package: name=\"io.legado.miss.app.release\"" >nul || exit /b 1
"%APKSIGNER%" verify --print-certs "%~1" >nul 2>&1 || exit /b 1
echo   [OK] %~n1: badging + apksigner passed
exit /b 0
```

配套文档门禁：

- `docs/project-rules/apk-publish-workflow.md` §2.2 Stage3 表格补一行：`build-legado.bat 单包内嵌校验（libcronet.so + badging 包名 + apksigner 验签，release 包 fail-fast exit）`——与 publish_release.py 形成双层（脚本编排层 + 单包层）防线。
- 校验断言点对齐 legadoC AGENTS.md:217：包名（本项目 `io.legado.miss.app.release`/`io.legado.miss.app.debug`/`io.legado.app.debug` 三包各一断言）、版本号、`apksigner` 退出码 0（META-INF 部分条目未受签名的提示可接受）。

## 5. 数据流

```mermaid
flowchart TD
    A[业务调用点 put/putError/putWarn/putInfo] --> B[truncateSafely 截断保护]
    C[AI 埋点 putDebugWithTag/tag/ level] --> B
    B --> D{module 来源}
    D -->|put 系| E[callerModule: stackTrace 首帧 → LogModule.classify]
    D -->|putDebugWithTag| F["LogModule.fromTag(tag) 显式映射\nmiss 时 fallback E"]
    E --> G["LogEntry(time,msg,throwable,level,module)"]
    F --> G
    G --> H["mLogs 内存环（100 条，头插）"]
    G --> I[LogUtils.d(tag) 文件日志 — AI 层不动]
    G --> J["Log.e(tag) logcat — ai_tests adb logcat -s 采集（不受勾选影响）"]
    G --> K["persist → filesDir/app.log\nBase64+tab 行格式，>500 行滚动截断"]
    G --> L[EventBus.APP_LOG_CHANGED]
    H --> M["AppLogDialog\nlogsForView(勾选集) ∩ Level 过滤\n显示=复制共用"]
    K --> N["重启 init → loadPersisted\ntakeLast(100) 恢复"]
    N --> M
    L --> M
```

## 6. 风险清单

| # | 风险 | 场景 | 缓解 |
|---|------|------|------|
| R1 | classify 误归类 | 关键词子串嵌套（如 `readview` 含于其他类名/`source` 过宽命中 `sourceLogin` 以外类）；跨组双命中类靠 when 顺序裁决 | 钉定表优先（legadoC 纪律：双命中必须钉定，不靠分支顺序）；`source` 类关键词实施时收窄为显式类名清单；归属表驱动单测全量断言（§8）后方可合入 |
| R2 | 性能：每条日志一次 stackTrace + 同步 IO | 高频路径（B12 CacheConcurrent/B13 MemoryPressure 统计埋点）；**绘制路径**（ReadView/ContentTextView）违规打点 | ① putDebugWithTag 已有 recordLog 守卫（关闭时 return 零开销）；② 绘制路径禁 AppLog 打点为既有铁律，C5 不放松（stackTrace 属绘制路径禁打点对齐项）；③ persist 失败静默不阻断主流程；④ 内存环/持久化写入均在调用线程，超过阈值的高频埋点建议由调用方自行节流（现状已如此，C5 不加新锁） |
| R3 | app.log 膨胀 | appendText 无上限（legadoC 同样存在此缺陷，实测风险） | 写入后行数 > 500 触发 `rewritePersisted` 截断至末 100 行；`*.log` 已在 .gitignore（:65），不入库 |
| R4 | 敏感信息入 app.log | 落盘 = 日志生命周期从"进程内"升级为"磁盘持久"，重启恢复+复制分享都会带出 | 脱敏铁律前置为 persist 门禁：URL 只留路径模式、cookie/token 隐藏 `***`、源名称编号化（logging_rules.md:133-137）；data URI 已有 truncateSafely 专项截断；L2 测试断言 app.log 无敏感模式（§8） |
| R5 | hook 绕过 | `git push --no-verify` 可跳过 pre-push/commit-msg | hook 定位为"机械兜底"（legadoC 同定位）；规则源在规范文档；未来开源启用时叠加 publish-clean-source.ps1 零命中校验双保险 |
| R6 | 勾选隐藏导致"日志丢了"误判 | 用户勾选后部分日志不可见，AI 排障时误以为未记录 | UI 明示"通用模块始终显示"；恢复默认=全显；AI 层 logcat 采集不受勾选影响（双层正交写进 UI 说明文案） |
| R7 | Enum 与项目 @IntDef 风格冲突 | checkstyle_rules.md:94-107 倡导 @IntDef | 见 DR-C5-2：本场景非位标志、需 name 持久化反解，enum 合理，核查表留痕 |
| R8 | mLogs 并发 | 双路径（put 系 + putDebugWithTag）写同一环 | 沿用既有 `@Synchronized` 方法级保护（checkstyle :73 object 可变状态必须同步），C5 不新增锁粒度 |

## 7. 规范符合性核查表 + 规范提升点

| 规范项 | 出处 | 符合性 |
|--------|------|--------|
| object 单例 + @Synchronized | checkstyle :62-73 | ✅ AppLog 保持 object；新增读写均在 @Synchronized 方法内 |
| kotlin.runCatching 带前缀 | checkstyle :39-51 | ✅ persist/loadPersisted/rewritePersisted 用 `kotlin.runCatching` |
| isNullOrBlank 判空 | checkstyle :57 | ✅ classify 入口判空 |
| UPPER_SNAKE_CASE 新常量 | naming :46-55 | ✅ PreferKey.logShownModules、PERSIST_MAX_LINES |
| 字段全默认值 | checkstyle :75-92 | ✅ LogEntry.module/level 均带默认值（Room 实体规则类推到 data class） |
| enum vs @IntDef | checkstyle :94-107 | ⚠️ 偏离但留痕：见 DR-C5-2 |
| 中文注释 + KDoc | checkstyle :139-141 | ✅ 骨架已中文注释 |
| 禁 Timber / 禁裸 android.util.Log | logging :53-59 | ✅ 不引入；AppLog 内部 Log.e 属既有豁免模式 |
| 脱敏铁律 | logging :133-137 | ✅ 升级为 persist 门禁（R4） |
| AI E2E 门禁 | AGENTS 强制规则 2 | ✅ 实施含 L2 真机断言，不借 legadoC 禁测宪法 |
| 打包后清 daemon | AGENTS 强制规则 6 | ✅ build.bat 校验段插在 :STOP_DAEMON（:217）之前，清场路径不变 |
| 构建验证复验 | 并发修改规范 | ✅ §9 每阶段 build-legado.bat 复验 + stop-daemons.bat 清场 |
| UI 组件族消费 | ui-standards/architecture.md（铁律 3） | ✅ 勾选 UI 全部复用既有 Compose 组件族：入口 A 走 AppDropdownMenu/AppDialogFrame；入口 B 多选弹框走 ComposeChoiceListDialog 先例，不新建 alert{} DSL |
| 前端 UI 标准 | frontend-ui-standards.md | ✅ 涉及（P2 双入口）：取色走组件族取色唯一基线、禁硬编码色；模块徽标复用 formatLogMessage 前缀机制，不私拉样式 |

**规范提升点（回灌）**：

1. `logging_rules.md` 新增"模块归属规范"节：classify 单点归类 + 钉定表防双命中 + "未匹配归兜底不丢日志"三原则（legadoC LogModule.kt:44-50/:63-66 沉淀），并登记 Tag→Module 显式映射表（§4.1 fromTag，26 TAG 逐条登记、miss fallback callerModule）与双层架构图（§3.2）。
2. `docs/project-flow/git-repo-management.md` 增补 `.githooks` 机械兜底范式（启用方式 + MSYS2 兼容写法 `[^ -~]` 陷阱）。
3. `docs/project-flow/build-apk-guide.md` §4.10 补 build-legado.bat release 产物校验段说明（与 apk-publish-workflow.md Stage3 互链）。

## 8. 测试设计

### 8.1 单测（JVM，`app/src/test/`）

| 用例 | 内容 |
|------|------|
| LogModuleClassifyTest（表驱动） | 驱动表：每模块 ≥3 个真实类名正例（含包名小写形态）、钉定表 4 类双命中负例断言唯一归属、null/""/未知类 → GENERAL、内部类 `$`/Kt 变体命中 |
| LogModuleFromTagTest | 26 TAG 全量映射断言 + 未知 tag → null |
| LogStoreRoundtripTest | serialize/deserialize 纯函数 roundtrip：中文/emoji/换行/tab 注入消息、data URI 截断消息、含堆栈、全 Level × 全 Module 笛卡尔抽样；旧格式行（缺 LEVEL/MODULE 列）容错解析；>500 行滚动截断断言剩余 100 行且为新行格式 |
| logsForViewTest | GENERAL 恒显、勾选集过滤、空勾选集仅 GENERAL、synchronized 快照不可变性 |

### 8.2 L2 真机（ai_tests/scripts/ 固化，venv python）

1. **勾选过滤**：`adb logcat -s AppLog` + UI automator 勾选"订阅源"→ 断言 AppLogDialog 仅 GENERAL+RSS 条目；取消勾选恢复。
2. **重启恢复**：`AppLog.put` 注入标记条目 → `am force-stop` → 重启 → 断言 logsForView 含标记条目且 module 正确（app.log roundtrip 真机断言）。
3. **AI 层回归**：`adb logcat -s WebBook:E AnalyzeRule:E` 采集行数与改造前基线一致（双层正交铁证）。
4. **发布链演练**：`build-legado.bat release` 后断言校验段输出 `[OK] badging + apksigner passed`；`publish_release.py --dry-run` Stage3 负向（篡改包名 apk → fail-fast）。
5. **敏感断言**：拉取 app.log grep 断言无 `cookie=`/`data:image/` 全文/完整 URL 模式（仅路径形态）。

## 9. 实施顺序 + 门禁

| 阶段 | 内容 | 门禁 |
|------|------|------|
| P1 | LogModule.kt + AppLog 双层改造（4.1/4.2）+ 单测 | 单测全绿；Grep 无 `android.util.Log.d\|Log.e` 新残留；updateLog 更新后编译 |
| P2 | UI 双入口（4.3）+ EventBus.APP_LOG_CHANGED（const val 常量） | 真机 L2-1/2；UI 取色走组件族（AppDialogFrame/Miuix 按钮），多选弹框走 ComposeChoiceListDialog 既有先例（禁新建 alert{} DSL，architecture.md 铁律 3），禁硬编码色（global-checklist G2） |
| P3 | build-legado.bat 校验段（4.5）+ apk-publish-workflow.md/build-apk-guide.md 补记 | dry-run 构建 + release 包校验段实测 + stop-daemons.bat 清场 |
| P4 | .githooks + publish-clean-source.ps1 范式（4.4）+ git-repo-management.md 补记 | hooks 默认不启用（Open Question Q3 裁决）；脚本 `-DryRun` 演练零命中 |
| P5 | logging_rules.md 回灌 + 收尾核查清单 | docs/INDEX.md 挂接本设计文档 |
| 规范回灌 | 按 design.md 提升清单执行本期对应条目——logging_rules 三条（§7 规范提升点：模块归属规范节 classify/钉定表/兜底原则 + Tag→Module 映射表 + 脱敏铁律升级 persist 门禁）+ git-hooks 机械兜底范式（git-repo-management 补记 .githooks 范式与 MSYS2 兼容写法陷阱，对齐提升点 #7/#8）+规范核查表执行（§7 逐条打勾） | 回灌完成后验证轮复核规范文件变更与 design.md 清单一致 |

## 10. Open Questions

1. **Q1 模块清单粒度**：10 模块（§4.1）是否够？是否需要 `WEBDav/备份` 独立模块（当前 TAG_WEBDAV_BACKUP 暂归 GENERAL）？——实施首周按真实日志分布回归调整。
2. **Q2 app.log 是否纳入用户可导出**：AppLogDialog 复制已覆盖；是否加"导出文件"入口（可能放大 R4 敏感面）？——建议本期不做。
3. **Q3 hook 是否默认启用**：`core.hooksPath` 切换影响全体开发者工作流（commit-msg 中文强校验）——默认启用或文档引导按需启用，待检查点裁决。
4. **Q4 putNotSave 是否也持久化**：语义为"不保存"，维持不落盘；若真机反馈"重启后 toast 过的错误消失"再评估。

## 11. 工作量

| 阶段 | 内容 | 估算 |
|------|------|------|
| P1 | LogModule + AppLog 双层 + 4 组单测 | 0.5 人日 |
| P2 | UI 双入口 + EventBus + strings | 0.5 人日 |
| P3 | build.bat 校验段 + 双文档补记 | 0.5 人日 |
| P4 | hooks + 清洗脚本范式 | 0.5 人日 |
| P5 | 规范回灌 + L2 固化 + 收尾 | 0.5 人日 |
| **合计** | | **2.5 人日** |

## 12. 设计决策记录

| # | 决策 | 理由 | 备选与取舍 |
|---|------|------|-----------|
| DR-C5-1 | 双层叠加，AI 层 26 TAG 链路一行不动 | ai_tests logcat 采集是运行契约（AD-06）；勾选与采集正交 | 替代"统一到 LogModule"——否，破坏 ai_tests 契约且迁移 200+ 调用点 |
| DR-C5-2 | LogModule 用 enum 而非 @IntDef | 需 name 持久化反解 + StringSet 勾选存储 + entries 遍历；非位标志场景（BookType 位标志才用 @IntDef） | @IntDef 需自写 name 映射表，徒增维护面 |
| DR-C5-3 | 持久化行格式 `time\tLEVEL\tb64msg\tb64stack\tMODULE` + 500 行滚动截断 | 本项目 LogEntry 有 Level（legadoC 无）；legadoC append 无上限是缺陷，吸收时修复 | 纯 legadoC 5 列格式——否，丢 Level 维度 |
| DR-C5-4 | 勾选 UI 双入口：AppLogDialog 过滤菜单（主）+ OtherConfigFragment 偏好（辅） | 主入口贴近使用场景且复用既有 AppDropdownMenu 组件族；偏好入口对齐 legadoC 习惯 | 仅偏好单入口——否，用户查日志时多跳转一层 |
| DR-C5-5 | 新增 EventBus.APP_LOG_CHANGED 实时刷新 | 补齐本项目"一次性快照"缺陷；legadoC 已验证该模式 | 轮询/手动刷新——否，体验倒退 |
| DR-C5-6 | 产物校验下沉 build-legado.bat（单包层）+ publish_release.py（编排层）双层 | 日常单包交付不经编排器，门禁须在最小构建单元生效 | 仅编排层——否，release 单包直发场景裸奔 |
| DR-C5-7 | 防泄露 hook/清洗脚本为"范式预留"，默认不启用 | 本项目单私有仓无公开镜像；三件套（hook+剥离清单+零命中校验）按需即插即用 | 全量移植双仓拓扑——否，过度工程 |
| DR-C5-8 | 不借 legadoC"调试日志开关已删"语义 | 本项目 recordLog 守卫承担节流 + JVM 单测安全双职责，是 AI 采集体系一部分 | 照删——否，putDebugWithTag 零开销特性丢失 |
