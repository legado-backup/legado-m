# sync-upstream-optimizations-20260816 · design

> OpenSpec 四文档之一 ｜ 上游同步优化批次（2026-08-16） ｜ 状态：✅ 设计完成（待实施）
> ⚠️ 本文所有行号锚点取自 2026-08-16 工作区（含未提交 Compose 化改动）。实施前执行 tasks 0.3 锚点复核。
> 覆盖 16 项：项 1-12 来自喵公子/legado-E（release 级），项 13-16 来自阅读T/MD3/Jingshiro（提交级，08-16 20:15 补充调研并入）。

## 1. Technical Approach

总体策略：**行为规格取自上游、代码落点取自本项目**。16 项彼此独立、无相互依赖，按 P0→P1→P2 三阶段实施；每项遵循项目既有架构（object 单例、`Coroutine.async/onError` 链式封装、`kotlin.runCatching`、`AppLog.put`、Compose 页面复用现有组件库）。分四个改动层：

1. **数据/模型层**（R1 部分、R2、R3 解析、R12）：纯 Kotlin 逻辑，Compose 化无关，冲突面最小 → 阶段 1 先行
2. **服务层**（R7、R8、R10）：ReadAloudService / JsExtensions / WebDav，同样不受 UI 分叉影响
3. **UI 交互层**（R3 弹窗、R4、R5、R6、R9、R10 复选项）：落点在已 Compose 化页面，使用现有组件原语
4. **全局开关层**（R11 manifest、R12 选项解析）：改动面极小但回归面大，置于阶段 3 末尾统一验证

### 1.1 逐项落地设计

#### 项 1（R1）EPUB delTag 位运算 bug + ruby TextNode 合并 ｜ P0

- **上游规格**：legado-E commit `964d49e`（PR#451，2026-07-24）+ 可读性跟进 `1510861`
- **Bug 本质**：`Book.addDelTag` 用 `and`，新位永远置不上 → 开关无效。本项目 `Book.kt:344-346` 与修复前上游**完全同源**：

```kotlin
// Book.kt:344-346（现状，bug）
fun addDelTag(tag: Long) {
    config.delTag = config.delTag and tag   // ← and：只能清除位，永远无法置位
}
// 修复
config.delTag = config.delTag or tag
```

- 影响面：`rubyTag=4L`（`Book.kt:451`）与 `hTag=2L`（`Book.kt:450`）两组开关（入口 `ReadBookActivity.kt:512-513,620,630,1578-1580`）全部失效；`getDelTag`（`and tag == tag`）与 `removeDelTag`（`and tag.inv()`）语义本就正确，不动。
- **ruby 合并算法**（`EpubFile.kt:176-181` 升级，照搬上游已验证实现）：对每个 `ruby` 元素 → 移除其内 `rp, rt` → 以 `TextNode(ruby.text())` 整体替换 → 与 prev/next 相邻 TextNode 依次合并，消除多余空格。替换后 `import org.jsoup.nodes.TextNode`。
- 已存库数据兼容：位含义不变，旧数据无需迁移（S12）。

#### 项 2（R2）章节缓存覆盖写入保护 ｜ P0

- **上游规格**：喵公子 beta 3.26081617「修复章节缓存覆盖」（行为：并发写同章节不互相覆盖）
- **本项目现状**：`BookHelp.kt:178-190` `saveText` 直接 `writeText`，无锁；对比图片下载已有 per-src Mutex（`BookHelp.kt:62,233`）——**文本章节是唯一裸奔的缓存写入点**。
- **设计**（双保险）：
  1. **per-file Mutex**：`BookHelp` 内 `ConcurrentHashMap<String, Mutex>`，键 = 缓存文件绝对路径；`withLock` 包裹「检查存在 → 下载 → 写入」全程。调用方（`WebBook.getContent` 链 / `CacheBookService`）不感知。
  2. **原子写**：先写 `${name}.tmp` 再 `renameTo`，中途杀进程不留半写主文件（S2 后半段）；`.tmp` 残留由下次写入覆盖。
- 锁注册表用 `computeIfAbsent` 惰性创建；条目不淘汰（章节文件数有限，单 Mutex 对象开销可忽略）。

#### 项 3（R3）更新弹窗显示包大小/日期 ｜ P0

- **上游规格**：喵公子 3.26081008
- **落点**：`help/update/AppUpdate.kt:16-20` `UpdateInfo` 增加 `assetSize: Long = 0`、`publishDate: String = ""`（默认值，兼容第三方 JSON 源缺字段）；GitHub Releases 解析处（`AppReleaseInfo` 链）按设备 abi 或 universal 资产取 `size`（字节）与 `published_at`；`UpdateDialog.kt:22-28` 标题行下追加副标题 `12.3 MB ｜ 2026-08-11`（`formatFileSize` 工具已有类似实现，复用/提取）。
- 字段为 0/空时整行隐藏（S11）。

#### 项 4（R4）应用日志导出分享 ｜ P0

- **上游规格**：喵公子 3.26080421
- **落点**：`ui/about/AboutActivity.kt:111-128` 已有 `saveLog()`（logs.zip 落备份目录）、`:154-170` `copyLogs()` 打包逻辑。新增 `shareLog()`：`copyLogs()` → `FileProvider.getUriForFile(ctx, "${applicationId}.fileProvider", zip)`（manifest:623-625 已注册）→ `Intent.ACTION_SEND` + `FLAG_GRANT_READ_URI_PERMISSION` + `ctx.startActivity`。About 页已 Compose 化，入口按钮加在现有日志操作区。

#### 项 5（R5）阅读页下拉书签 ｜ P1

- **上游规格**：喵公子 3.26080800（实现细节不可见，按本项目手势体系设计）
- **落点**：`ui/book/read/page/delegate/ScrollPageDelegate.kt`（滚动模式）——既有 fling 判定（`PageDelegate.kt:62,66`）基础上，识别「内容处于顶部 + 继续下拉超过阈值（约 80dp，velocity 辅助判定）」为书签手势；触发 `ReadBook.book` 当前 durChapterPos 生成 `Bookmark`（复用书签表与 `onAddBookmark` 既有链路），顶部浮现提示条（阅读浮层原语，阅读页独立配色，遵既有决策）。
- **手势兼容约束**：仅滚动模式启用（页模式 fling 已用于翻页，AD-08）；触发后本次手势不再传递为点击/选择。设置项 `PreferKey.pullDownBookmark`（默认开），入口在阅读设置-其他。

#### 项 6（R6）目录分卷折叠 + 搜索匹配数量 ｜ P1

- **上游规格**：喵公子 3.26071522
- **落点**：`ui/book/toc/ChapterListAdapter.kt`（:56,129,138-147 现仅 `isVolume` 高亮）。数据层：ViewModel 构建分组列表 `List<TocItem>`（卷头项 / 章节项），折叠卷头时过滤该卷章节项（`itemCount` 与 `getItem` 同源计算）；卷头行加折叠箭头图标（跟随日夜主题语义色）。搜索态：现有目录搜索过滤基础上，卷头行显示该卷匹配数、标题栏显示总数（S5）。与 `ChapterListFragment.kt:183` 卷名跳转兼容：折叠态点击卷头先展开再跳转。
- 折叠状态存内存（会话级，R6 要求），不落库。

#### 项 7（R7）TTS 段落间隔静音 + 按剩余章节停止 ｜ P1

- **上游规格**：喵公子 3.26071723
- **R7.1 段落间隔**：`ReadAloudConfig`（阅读配置体系）新增 `ttsParagraphPauseMs: Int = 0`；设置入口在朗读设置面板（已 Compose 化，用现有选择行组件）。
  - Http TTS：`HttpReadAloudService` 分段合成队列中，段落边界插入静音段——复用既有「空段落无声音频」机制（`HttpReadAloudService.kt:162,241`），按间隔 ms 生成对应时长静音。
  - 系统 TTS：`speak(..., QUEUE_MODE_ADD, params, utteranceId)` 段落边界追加 `KEY_PARAM_DELAY`/零长静默 utterance 实现。
- **R7.2 定时朗读增强**：`BaseReadAloudService.kt:157` 定时对话框（现有「按分钟」入口）扩展模式枚举 `NONE / MINUTES / FINISH_CHAPTER / CHAPTERS`；`FINISH_CHAPTER`（MD3 PR#2024）在段落/章节完成回调（`paragraphUp`/`chapterChange` 既有回调）处判定当前章末尾即停止；`CHAPTERS` 在 `:402-420` `doDs` 倒计时体系旁增 `remainChapters` 计数，`onChapterChanged` 时递减，归零 → `stopReadAloud()` + 通知栏提示。模式互斥单选。

#### 项 8（R8）书源 JS 并发工具 ｜ P2

- **上游规格**：喵公子 3.26071723（singleFlight / lock / tick 三原语）
- **落点**：新文件 `app/src/main/java/io/legado/app/help/JsConcurrencyHelper.kt`（object 单例）+ `JsExtensions.kt` 挂三个桥接方法（JS 侧经 `java.xxx` 或直接全局调用，与既有 JsExtensions 方法同机制）：

```kotlin
// 伪代码规格
singleFlight(key, fn): 同 key 并发调用共享首个 in-flight Deferred 的结果；失败结果同样共享（不缓存）
lock(key, fn):        per-key Mutex 串行队列，finally 释放
tick(ms):             挂起延时（delay），返回当前时间戳
```

- **命名空间隔离**：实际键 = `analyzeRule.sourceKey + "#" + key`（AD-04），跨书源/调试页不串扰；`singleFlight` in-flight 表调用结束即移除条目（无泄漏，R8）；fn 异常按 JS 异常路径回抛给该次调用方（S10）。JS 桥接用 Kotlin lambda 反射调用（Rhino 兼容，参考 JsExtensions 既有 `java.ajax` 等实现模式）。
- 价值锚点：本项目视频/嗅探类 JS 重度书源（token 获取去重、集数并发控制）直接受益。
- ⚠️ **技术风险（本批最高）**：Rhino `Context` 为线程绑定，后到协程线程共享/执行首个调用的 JS 结果会撞线程模型。**实现前必须先浅克隆喵公子/阅读T 仓库对比其真实实现**（forks_comparison_methodology Phase 1-2），禁止凭设计闭门实现；桥接层需保证 JS 回调始终在发起调用的 Rhino Context 内同步求值，Kotlin 侧仅做结果去重/排队。

#### 项 9（R9）漫画长按保存图片 ｜ P2

- **上游规格**：喵公子 3.26080421（漫画长按保存图片）
- **落点**：`ui/book/manga/ReadMangaActivity.kt` 长按手势（对齐文本页 `ReadBookActivity.kt:2094` `onImageLongPress` 模式）→ 弹确认（应用级弹窗容器组件）→ 复用图片保存工具（`ReadBookViewModel.kt:540` `saveImage` 路径提取为公共工具或直接调用）：Android 10+ MediaStore 插入（Pictures/legado），低版本走既有导出路径 + 权限检查；成功/失败 Toast + `AppLog.put` 记录。

#### 项 10（R10）删除本地书联动删 WebDAV 文件 ｜ P2

- **上游规格**：喵公子 3.26080800
- **落点**：删书确认弹窗（`ui/book/info/BookInfoViewModel.kt:483-495` `delBook` 上游入口，弹窗用应用级确认弹窗组件）加复选「同时删除 WebDAV 上的书籍文件」，选择记忆到 `PreferKey.delBookSyncWebDav`（**默认 false**，AD-06）。开启时：`delBook` 完成本地清理（`LocalBook.kt:388-403` 既有）后，`Coroutine.async` 异步调 `RemoteBookWebDav`/`WebDav` 删除 `books/{bookName}(+扩展名匹配)`；失败 `onError` → Toast 提示 + `AppLog.put`，不阻塞、不回滚本地删除（S9）。
- ⚠️ **文件名歧义防护（设计补强）**：云端按书名+扩展名存文件，存在同名不同书误删风险。删除对象必须**由本地书籍记录精确构造完整文件名**（本地导入书取其原始文件名；网络书仅在云端存在同名唯一文件时删除）；构造不出唯一目标（无本地文件名锚点且云端匹配到 0 或 ≥2 个文件）时**跳过删除并提示**，宁漏勿误。

#### 项 11（R11）Android 预测返回动画 ｜ P2

- **上游规格**：喵公子 3.26080821
- **落点**：`AndroidManifest.xml` `<application>` 加 `android:enableOnBackInvokedCallback="true"`（targetSdk 36 已满足，`build.gradle:75`）。代码零改动——本项目已全面 `onBackPressedDispatcher`（`BaseActivity.kt:90`、`ReadBookActivity.kt:325` 等）。
- **前置核查**（tasks 内）：grep `onBackPressed(` 覆写残留为 0（有则先迁移 dispatcher）；WebView（`BackstageWebView`/视频 WebView 返回拦截）与 GSY 播放器全屏返回链路列入回归清单。
- API 34+ 手势动画生效；API < 34 自然降级无行为变化（S13）。

#### 项 12（R12）URL 读取超时/重定向开关 ｜ P2

- **上游规格**：喵公子 3.26071522（URL 请求支持读取超时和重定向开关）+ 3.26080517（旧书源 resolveIp 兼容——本项目 `AnalyzeUrl.kt:873` 已有 `dnsIp` alternate 别名，此项仅回归验证）
- **落点**：`AnalyzeUrl` 选项解析（optionJson 机制）新增 `readTimeout: Int?`（毫秒）、`redirect: Boolean = true`；请求构建处按选项应用：
  - 超时：`okHttpClient.newBuilder()` 按 call 派生（`callTimeout`/`readTimeout` 后 build，仅该请求生效，不改全局单例）
  - 重定向：`redirect=false` 时派生 `followRedirects(false).followSslRedirects(false)` 的 client，3xx 响应本体直接返回给规则层
- 书源帮助文档（`assets/web/help/md/` 下 URL 选项说明）同步补字段；`BookSource.kt` **不加实体字段**（URL 选项级而非源级，与既有 webView/dnsId 选项同层，降低 schema 影响）。
- ⚠️ **Cronet 路径盲区（设计补强）**：本项目为 OkHttp+Cronet 双栈，请求若经 CronetTransport，OkHttpClient builder 的 `followRedirects/readTimeout` 不保证传导至 Cronet 引擎。**带 `readTimeout`/`redirect` 选项的请求强制走 OkHttp 原生栈**（该类精细控制请求本就不该吃 QUIC 红利），并在帮助文档注明；3.5.x 任务含 Cronet 全局开启状态下的验证项。

#### 项 13（R14）TextDialog 帮助文档内搜索 ｜ P2 ｜ 来源：阅读T（2026-08-14）

- **上游规格**：阅读T「feat(帮助)： TextDialog 支持文档内搜索——全文高亮、上下跳转」
- **本项目现状**：`ui/widget/dialog/TextDialog.kt` 为帮助文档查看器，0 处搜索能力。
- **设计**：对话框顶栏加可折叠搜索框：输入关键词 → 全文（content 字符串）大小写不敏感匹配 → 命中计数 `n/m`；命中词背景高亮（Spannable + 主题语义色）；「上一处/下一处」跳转滚动定位并居中当前命中；无命中提示不遮挡正文。搜索框样式遵循 08/16 用户反馈的 44dp 高度规范（与 SettingsSearchBar 调整方向一致）。

#### 项 14（R15）TXT 无规则分割字数可设置 ｜ P2 ｜ 来源：MD3（todoXu，2026-08-10）

- **上游规格**：MD3「feat: 允许设置无规则匹配时的章节分割字数」
- **本项目现状**：`TextFile.kt:394` `analyze()`（无规则拆分目录）使用硬编码 `maxLengthWithNoToc`，用户不可调。
- **设计**：`PreferKey` 新增 `txtSegmentLength`（默认 = 现硬编码值，行为零变化）；`analyze()` 读配置；设置入口在阅读设置/本地书籍分区（Compose 设置行 + 数值选择弹窗，区间如 2k~100k）；帮助文档注明仅影响新导入与「重新分析目录」。

#### 项 15（R16）阅读记录页 OOM 核查加固 ｜ P2 ｜ 来源：Jingshiro（2026-08-07）｜ 核查型

- **上游规格**：Jingshiro「fix: 修复阅读记录页OOM崩溃及详细记录重复膨胀」
- **本项目现状**：`ReadRecordActivity.kt:88`（allTime）/`:98`（search）→ `ReadRecordDao.search` 返回 `ReadRecordShow` 明细全量列表；ReadRecord 页刚 Compose 化。**风险面与上游修复前同构：明细全量进内存 + 每书详细记录无上限膨胀**。
- **设计**（先审计后修复，见 AD-10）：
  1. 审计：构造超长明细数据（如 500 书 × 365 日）实测内存曲线与 UI 表现；检查 `ReadRecord` 写入路径是否存在同日重复膨胀
  2. 修复（若确认同类问题）：明细查询 LIMIT + 展开时按需分页；写入侧同日去重合并；Compose LazyColumn 虚拟化确认
  3. 无问题：结论写入 issues-found.md 后关闭任务

#### 项 16（R17）HttpTTS 启用CookieJar 字段 ｜ P2 ｜ 来源：阅读T（2026-08-14）

- **上游规格**：阅读T「fix(朗读)： HttpTTS 导入解析与编辑页补 jsLib/启用CookieJar 字段」——jsLib 本项目已有（`HttpTTS.kt:27,73`），仅缺 cookieJar。
- **设计**：`HttpTTS.kt` 实体增 `enableCookieJar: Boolean = false`（默认值兼容旧数据，无 Room 迁移）；`fromJSON` 解析 `$.enableCookieJar`；编辑页（已 Compose 化）加开关行；`HttpReadAloudService` 发起朗读请求按开关启用 CookieJar；默认 false 保持现行为。

## 2. Architecture Decisions（ADR Y-Statement）

### AD-01: 同步策略——参照重实现而非 cherry-pick

- **Context**：上游更新来自喵公子/legado-E 两仓库；本项目 UI 层正大规模 Compose 化（591 文件未提交），喵公子未做 Compose 迁移。
- **Concern**：cherry-pick 冲突与依赖面污染 vs 重实现的走样风险。
- **Decision**：Y：以上游 release/commit 为行为规格，在本项目锚点上重实现；K：绝不直接 apply 上游 patch。
- **Goal**：零冲突合入 + 行为对齐上游已验证逻辑。
- **Tradeoff**：重实现可能引入细节偏差 → 每项以 S 场景验收 + 与上游 release notes 逐条对照。
- **Status**：Proposed

### AD-02: EPUB 修复采用「or 语义修正 + 完整 TextNode 合并」组合

- **Context**：两处独立缺陷（位运算 bug / rp-rt 残留空格），上游一并以验证。
- **Concern**：只修 `or` 不做合并，注音文本仍有多余空格。
- **Decision**：Y：照搬上游 PR#451 完整算法（ruby→TextNode→相邻合并）；K：不自行发明简化版。
- **Tradeoff**：合并算法稍复杂 → 上游已验证 + jsoup 1.16.2 行为与上游一致（同锁定版本）。
- **Status**：Proposed

### AD-03: 章节缓存保护用 per-file Mutex + 临时文件原子改名双保险

- **Context**：并发写章节来源三处（批量缓存/前台阅读/换源）；图片已有 per-src Mutex 先例。
- **Concern**：全局锁串行化一切缓存（性能）vs 只加锁不做原子写（杀进程仍留半文件）。
- **Decision**：Y：单章节文件粒度 Mutex + `.tmp` 改名；K：不加全局锁、不改调用方接口。
- **Tradeoff**：同章节并发时后到方等待 → 换来命中前者结果（S14），正确性优先。
- **Status**：Proposed

### AD-04: JS 并发工具以 JsExtensions 桥接 + 源级命名空间键

- **Context**：JS 沙箱内书源共享一个 JsExtensions 实例。
- **Concern**：不同书源同 key 互相干扰 / in-flight 状态泄漏。
- **Decision**：Y：键 = sourceKey#key，object 单例注册表，调用结束清理；K：不做跨源全局锁、不做结果缓存（singleFlight 仅去重在途，不缓存历史）。
- **Tradeoff**：注册表常驻 → 单 Mutex/Deferred 对象开销可忽略，换取无泄漏强保证。
- **Status**：Proposed

### AD-05: 预测返回 = 仅 manifest 开关 + 全量回归清单

- **Context**：代码已 dispatcher 化，缺的只是 opt-in 标志。
- **Concern**：全局返回行为回归风险。
- **Decision**：Y：单行 manifest 改动 + 专项回归清单（阅读/视频/WebView/Compose 页）；K：不引入 OnBackInvokedCallback 手写适配（dispatcher 已是推荐路径）。
- **Tradeoff**：极端页面（自绘手势返回）理论可漏 → 回归清单覆盖高频页面，遗留页面按反馈修。
- **Status**：Proposed

### AD-06: WebDAV 删书联动默认关闭且失败不阻塞

- **Context**：云端文件可能被多设备共享。
- **Concern**：误删共享数据 vs 一致性便利。
- **Decision**：Y：复选记忆、默认 false；删除失败仅提示不回滚本地删除；K：不做云端回收站、不做批量预览。
- **Tradeoff**：极端断网下云端残留 → 用户可手动清理，数据安全优先。
- **Status**：Proposed

### AD-07: Http TTS 段落停顿复用既有无声音频机制

- **Context**：`HttpReadAloudService` 已有「空段落用无声音频占位」实现。
- **Concern**：新起合成暂停逻辑（改播放器状态机）复杂且易回归。
- **Decision**：Y：段落边界插入按 ms 时长生成的静音段，与内容段同一队列；K：不动播放器状态机、不加定时器。
- **Tradeoff**：静音段占缓存/带宽（极小）→ 实现面最小且天然有序。
- **Status**：Proposed

### AD-08: 下拉书签仅滚动模式启用

- **Context**：页模式 fling 已被翻页手势占用（`PageDelegate.kt:62,66`）。
- **Concern**：同手势双语义导致误触。
- **Decision**：Y：仅 ScrollPageDelegate 顶部下拉判定；页模式不启用；K：不做「按住时长区分」等复合手势。
- **Tradeoff**：页模式用户无此功能 → 该手势在页模式与系统返回/翻页冲突，收益不成比例。
- **Status**：Proposed

### AD-09: URL 超时/重定向做成 URL 选项级而非书源实体字段

- **Context**：喵公子同时存在源级与 URL 级配置；本项目已有成熟 optionJson 机制（webView/dnsId）。
- **Concern**：加实体字段需动 BookSource schema 与编辑 UI 全链路。
- **Decision**：Y：`readTimeout`/`redirect` 进 URL 选项 JSON（规则内 `@json:` 或源内 urlOption 均可用）；K：不加 BookSource Room 字段。
- **Tradeoff**：配置粒度到单请求（更灵活）但源级统一设置稍繁琐 → 可后续按需在源编辑页加「应用到全部」快捷项。
- **Status**：Proposed

### AD-10: ReadRecord OOM 项采用「先审计后修复」核查型任务

- **Context**：Jingshiro 修复的 OOM 在其代码库实锤；本项目数据模型相近但写入路径/页面实现（刚 Compose 化）不同构，无法直接断言存在同一 bug。
- **Concern**：盲目照搬修复（分页/去重）可能引入无问题的问题；不处理则可能遗留同类崩溃。
- **Decision**：Y：先构造压力数据实测审计（内存曲线 + 写入膨胀检查），确认后才修；无问题则记录核查结论关闭；K：不做推测式防御改动。
- **Tradeoff**：审计占任务时间 → 换取修复的必要性与正确性双重确认。
- **Status**：Proposed

### AD-11: 下拉书签为无上游参照的自研交互，接受行为差异

- **Context**：喵公子仅 release note 一句话，手势阈值/触发区域/提示形式实现不可见。
- **Concern**：自研交互可能与上游体验不一致，且需自行消化手势冲突。
- **Decision**：Y：明确为自研规格（仅滚动模式、80dp 阈值、可关闭），真机验收以本项目 S4 场景为准而非上游对齐；K：不逆向猜上游实现。
- **Tradeoff**：与上游行为可能不同 → 换来交互与本项目手势体系（fling 翻页/边缘滑动）的确定性兼容。
- **Status**：Proposed

## 3. Data Flow

### 3.1 EPUB 解析修复流（项 1）

```
EPUB 打开(EpubFile)
  └─ getBody → jsoup Elements
       ├─ ruby 删除开启(getDelTag(rubyTag)  ← addDelTag(or) 修正后可正确置位)
       │    └─ 每个 ruby: 移除 rp/rt → TextNode(ruby.text()) 替换 → prev/next TextNode 合并
       ├─ h 删除开启(getDelTag(hTag)) → select("h1..h6").remove()   ← 开关随 or 修复生效
       └─ outerHtml → HtmlFormatter.formatKeepImg → 章节
```

### 3.2 章节缓存并发保护流（项 2）

```
WebBook.getContent(book, chapter)
  └─ BookHelp.getTextCache(file)  miss
       └─ fileMutex(file.absolutePath).withLock {      // per-file
            re-check cache（双重检查，S14 命中前者结果）
            miss → AnalyzeUrl 下载正文（可选 readTimeout/redirect，项 12）
                  → saveText: 写 ${file}.tmp → renameTo(file)   // 原子
          }
```

### 3.3 JS 并发工具调用流（项 8）

```
书源JS: java.singleFlight("token", fn)
  └─ JsExtensions.singleFlight(key, fn)
       └─ JsConcurrencyHelper: registry["src#token"]
            ├─ 存在 in-flight → await 同一 Deferred（共享结果/异常）
            └─ 不存在 → 启动 async(fn) 注册 → finally 移除条目
```

## 4. File Changes

| 文件 | 操作 | 说明（对应项） |
|------|------|----------------|
| `data/entities/Book.kt` | 修改 | `addDelTag` and→or（项1，:344-346） |
| `model/localBook/EpubFile.kt` | 修改 | ruby TextNode 合并 + import TextNode（项1，:176-181） |
| `help/book/BookHelp.kt` | 修改 | per-file Mutex + 原子写 saveText（项2，:178-190） |
| `help/update/AppUpdate.kt` / `AppReleaseInfo.kt` | 修改 | UpdateInfo 增 size/date 字段 + 解析（项3） |
| `ui/about/UpdateDialog.kt` | 修改 | 副标题展示大小/日期（项3） |
| `ui/about/AboutActivity.kt`（Compose 壳） | 修改 | 新增分享日志入口 shareLog()（项4） |
| `ui/book/read/page/delegate/ScrollPageDelegate.kt` | 修改 | 顶部下拉书签手势（项5） |
| `ui/book/read/` 提示条原语 + 阅读设置页 | 修改 | 书签提示 + `pullDownBookmark` 开关（项5） |
| `ui/book/toc/ChapterListAdapter.kt` + VM | 修改 | 分卷折叠数据结构 + 匹配计数（项6） |
| `service/BaseReadAloudService.kt` | 修改 | 定时模式枚举 + 剩余章节计数（项7.2，:157,402-420） |
| `service/HttpReadAloudService.kt` | 修改 | 段落静音段插入（项7.1，:162,241） |
| 朗读配置 + 设置面板 | 修改 | `ttsParagraphPauseMs` 设置（项7.1） |
| `help/JsConcurrencyHelper.kt` | **新增** | 三原语注册表（项8） |
| `help/JsExtensions.kt` | 修改 | 桥接 singleFlight/lock/tick（项8） |
| `ui/book/manga/ReadMangaActivity.kt`（+VM） | 修改 | 长按保存手势（项9） |
| `ui/book/info/BookInfoViewModel.kt` | 修改 | delBook 联动分支（项10，:483-495） |
| `help/AppWebDav.kt` / `model/remote/RemoteBookWebDav.kt` | 修改 | 删书籍文件接口（项10） |
| `AndroidManifest.xml` | 修改 | enableOnBackInvokedCallback（项11） |
| `model/analyzeRule/AnalyzeUrl.kt` | 修改 | readTimeout/redirect 选项（项12） |
| `ui/widget/dialog/TextDialog.kt` | 修改 | 文档内搜索（高亮/跳转/计数）（项13） |
| `model/localBook/TextFile.kt` | 修改 | maxLengthWithNoToc 配置化（项14，:394 analyze） |
| `ui/about/ReadRecordActivity.kt` + `data/dao/ReadRecordDao.kt` | 核查/修改 | OOM 审计 + 视结论分页/去重（项15） |
| `data/entities/HttpTTS.kt` + 编辑页 + `service/HttpReadAloudService.kt` | 修改 | enableCookieJar 字段全链路（项16） |
| `constant/PreferKey.kt` | 修改 | 新增 4 个 key（项5/7/10/14） |
| `res/values/strings.xml` | 修改 | 新增文案（约 25 条） |
| `assets/web/help/md/`（URL 选项文档） | 修改 | 补 readTimeout/redirect（项12） |
| `assets/updateLog.md` | 修改 | 编译前按门禁更新 |
| `docs/project-rules/forks-reference.md` | 修改 | 集散地地址更新为 momoa.cc.cd（本次调研已发现过期） |

> 实施顺序：阶段1（前 6 行）→ 阶段2（次 8 行）→ 阶段3（其余）→ 阶段4 收尾。每阶段独立可编译、可验收、可回滚。
