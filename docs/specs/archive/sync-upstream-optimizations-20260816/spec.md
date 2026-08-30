# sync-upstream-optimizations-20260816 · spec

> OpenSpec 四文档之一 ｜ 上游同步优化批次（2026-08-16） ｜ 状态：✅ 设计完成（待实施）

## 1. Intent（意图）

将开源阅读生态近一个月（2026-07-16 ~ 2026-08-16）已验证的优化成果同步进本项目，一次性补齐 12 项确认缺失的能力/修复（含 1 项本项目已实锤存在的位运算 bug），保持 fork 与活跃上游（喵公子阅读、legado-E）的持续对齐，避免闭门造车与已知 bug 长期滞留。方法论遵循 `docs/project-rules/forks_comparison_methodology.md` 五阶段流程（本次完成 Phase 1-5 全程，产出决策表见 README §1.2）。

## 2. Scope（范围）

### 2.1 做

README §1.2 **A 类 12 项**全部实施，按三级优先级分四个阶段（P0 修复 4 项 → P1 阅读体验 3 项 → P2 进阶增强 5 项 → 收尾）。每项以「上游来源 + 本项目文件锚点」双重锚定，落地设计见 design.md。

### 2.2 不做（红线）

- ❌ B 类 4 项大特性（段评 UI 体系、批量网络封面管理、批量换源缓存、直链口令分享）——工程量大（段评为独立子系统），各自单独立项
- ❌ D 类阅读NG Compose 迁移代码搬运——与 `ui-redesign-m3` 职责重叠，仅输出模式参考
- ❌ C 类已对齐项重做（Brotli/Cronet 版本/书架进度条/UA 统一/ARM 包/页眉页脚模板化等）——已各有等价实现或已有用户决策
- ❌ 不改数据库 schema（本批全部无 Room 迁移需求）
- ❌ 不动网络协议栈架构（Cronet/OkHttp 双栈结构维持，仅加 URL 级选项）
- ❌ 不在 Compose 化未提交工作区上直接实施（阶段 0 前置门禁）

### 2.3 影响模块

`data/entities/Book.kt`、`model/localBook/EpubFile.kt`、`help/book/BookHelp.kt`、`help/update/*`、`ui/about/*`、`ui/book/read/page/*`、`ui/book/toc/*`、`service/*ReadAloudService`、`ui/book/read/config/*`、`help/JsExtensions.kt`（+新文件 JsConcurrencyHelper）、`ui/book/manga/*`、`ui/book/info/*`、`help/AppWebDav.kt`、`AndroidManifest.xml`、`model/analyzeRule/AnalyzeUrl.kt`、`ui/widget/dialog/TextDialog.kt`、`model/localBook/TextFile.kt`、`data/entities/HttpTTS.kt`、`data/dao/ReadRecordDao.kt`（核查）、`constant/PreferKey.kt`、`res/values/strings.xml`、`assets/updateLog.md`。

## 3. Approach（方法）

### 3.1 Selected Approach

**参照上游实现、按本项目现状重实现**：以上游 release/commit 为行为规格（不是逐行 cherry-pick），落点锚定本项目实际文件与行号，代码风格遵循项目规范（`Coroutine.async/onError` 链、`kotlin.runCatching`、`AppLog.put`、object 单例、Compose 化页面用现有组件库 TagChip/SettingsSelectableRow 等）。每项改动最小化，12 项彼此独立、可分阶段独立验收与回滚。

### 3.2 Alternatives Considered

| 方案 | 否决理由 |
|------|----------|
| 直接 cherry-pick 上游 commit | UI 层已因 Compose 化大面积分叉，喵公子未做 Compose 迁移，其 UI commit 100% 冲突；业务层虽可 cherry-pick 但将带入项目不存在的依赖面（如其段评服务端） |
| 全量移植喵公子 8 月所有更新 | 含大量段评/Web 写源体系（B 类红线），且其备份/WebDAV 实现与本项目刚完成的增强（975992f53）冲突 |
| 只做 EPUB bug 一项 P0 | 收益面太窄；已核实的 11 项缺口一次性补齐的边际成本低（调研成本已沉没） |
| 等上游原版 gedoor 恢复更新再同步 | 原版已停更近 3 个月（最后推送 2026-05-27），等待无意义 |

### 3.3 Drawbacks

- 上游行为规格依赖 release notes 与 commit diff 的准确解读，个别项（下拉书签手势细节）上游实现细节不可见，需按本项目手势体系自行设计——已通过「仅滚动模式启用 + 可关闭」约束降低风险
- 12 项跨 15+ 模块，单批次任务量大——以阶段化 + 项间独立 + 逐项验收对冲
- 预测返回（R11）为全局行为开关，理论回归面覆盖全部页面——用回归清单 + 手工用例对冲，且代码已全面 `onBackPressedDispatcher` 化，前置风险低
- 与 Compose 化未提交改动存在时序耦合——阶段 0 强制门禁：先固化工作区再实施

### 3.4 Prior Art

- 项目已有同类「上游同步」模式：`sigma-sync-202607`（已完成）、`forks-archive-borrow-implementation`（进行中）
- EPUB 修复直接采用 legado-E 已验证算法（PR#451 合并进 legado-E master，7/24）
- 章节缓存保护参考本项目图片下载已验证的 Mutex 模式（`BookHelp.kt:62,233`）
- 阅读T/MD3 提交为行为规格来源：T 的 TextDialog 搜索（8/14）、HttpTTS 字段（8/14），MD3 的读完本章（PR#2024，8/12）、TXT 分割字数（8/10）；Jingshiro OOM 修复（8/7）为核查参照

## 4. Requirements

### P0（阶段 1）

- **R1 EPUB delTag 修复**：`addDelTag` 位运算由 `and` 修正为 `or`（`Book.kt:345`），使「删除 Ruby 标签」「删除 H 标签」开关真正生效；开启 ruby 删除时，将 `ruby` 元素整体替换为纯 TextNode 并与前后相邻 TextNode 合并，消除注音残留多余空格；`getDelTag`/`removeDelTag` 语义不变；已存库的 `ReadConfig.delTag` 位含义不变（覆盖安装无迁移需求）。
- **R2 章节缓存写入保护**：并发场景（批量缓存 / 阅读 / 换源同书同章）下，同一章节缓存文件的「检查-下载-写入」互斥，不产生半写/撕裂文件；写入采用临时文件 + 原子改名；锁粒度为单章节文件级，不阻塞不同章节/书籍的并发。
- **R3 更新弹窗信息增强**：GitHub Releases 更新源解析 asset size 与发布日期，弹窗展示（如 `12.3 MB ｜ 2026-08-11`）；第三方 JSON 更新源无该字段时优雅降级不占位。
- **R4 日志导出分享**：关于页新增「分享日志」，复用现有 logs.zip 打包（`AboutActivity.copyLogs`），经 FileProvider（`${applicationId}.fileProvider`）拉起 `ACTION_SEND`；debug/release 双包名均可分享成功。

### P1（阶段 2）

- **R5 阅读页下拉书签**：滚动阅读模式下，从内容区顶部下拉触发为当前位置添加书签，带可视提示（提示条/Toast）；不与滚动/点击既有手势冲突；提供设置开关，默认开启。
- **R6 目录分卷折叠**：目录中点击卷名行折叠/展开该卷章节列表；搜索时显示匹配章节数量（总数与各卷）；折叠状态在当前目录会话内保持；与既有「卷名跳转」行为兼容（折叠态点击标题展开）。
- **R7 TTS 增强双项**：
  - R7.1 段落间隔：朗读设置新增段落间停顿时长（0=关闭，默认 0）；系统 TTS 与 Http TTS 均生效；Http TTS 复用既有无声音频机制实现停顿。
  - R7.2 定时朗读增强：朗读定时对话框由单模式扩展为**三模式**——按分钟（既有）/ 读完本章（MD3 PR#2024）/ 剩余 N 章；三模式互斥单选；「读完本章」在当前章节朗读完成时停止，「剩余 N 章」在章节切换回调时递减计数，归零或到点自动停止朗读并发通知。

### P2（阶段 3）

- **R8 书源 JS 并发工具**：JsExtensions 新增 `singleFlight(key, fn)`（并发去重：同 key 并发调用共享首次结果）、`lock(key, fn)`（互斥队列）、`tick(ms)`（延时）；键按书源命名空间隔离（`bookSourceUrl#key`），跨源不串扰；JS 侧异常不逃逸到 Kotlin 层；注册表无泄漏（调用结束清理 in-flight 状态）。
- **R9 漫画长按保存**：漫画阅读页长按当前图片弹出保存（复用文本页 `onImageLongPress`→`saveImage` 既有路径）；Android 10+ 走 MediaStore，低版本走既有文件路径；保存成功/失败有 Toast。
- **R10 WebDAV 删书联动**：删书确认对话框新增「同时删除 WebDAV 上的书籍文件」复选项（记忆用户选择，**默认关闭**）；开启时删本地书后异步删除 WebDAV 对应书籍文件；WebDAV 不可达/失败时仅提示不阻塞本地删书。
- **R11 预测返回动画**：manifest 开启 `android:enableOnBackInvokedCallback="true"`；全页面返回行为回归（重点：阅读页、视频播放、WebView、各 Compose 页）；API < 34 无行为变化。
- **R12 URL 超时/重定向开关**：URL 选项 JSON 支持 `readTimeout`（毫秒）与 `redirect`（bool，默认 true），作用于该次 OkHttp 请求；`redirect:false` 时不自动跟随（返回 3xx 响应本体供规则处理）；与既有 `dnsIp/resolveIp` 别名机制共存；书源编辑器字段说明文档同步。

### P2 增补（阶段 3，来源：阅读T / MD3 / Jingshiro，08-16 20:15 补充调研）

- **R14 帮助文档内搜索**：`TextDialog`（帮助文档查看器）新增文档内搜索：输入关键词全文匹配、当前页高亮命中、上一处/下一处跳转、命中计数；无命中提示；不影响既有文本展示/复制功能。
- **R15 TXT 分割字数可配置**：TXT 导入且无目录规则匹配时，默认按字数分割成章的长度由硬编码（`TextFile.analyze()` 的 `maxLengthWithNoToc`）改为可设置项（阅读设置-本地书籍，默认值不变）；仅影响后续导入/重新分析，已导入书籍不受影响。
- **R16 阅读记录页 OOM 核查加固**（核查型任务）：对照 Jingshiro 2026-08-07 修复（阅读记录页 OOM 崩溃 + 详细记录重复膨胀），审计本项目 ReadRecord 链路（`ReadRecordActivity`/`ReadRecordDao`/`ReadRecordShow`）在超长明细数据下的内存行为与数据膨胀面；发现同类问题则修复（分页/截断/去重），无问题则在 issues-found.md 记录核查结论。
- **R17 HttpTTS CookieJar 字段**：`HttpTTS` 实体、导入解析（JSON path `$.enableCookieJar`）与编辑页补「启用CookieJar」开关；默认关闭；Http 朗读请求按开关携带 CookieJar。

### 流程合规（阶段 4）

- **R13**：`updateLog.md` 在编译前更新（版本交付同步门禁）；执行步骤 5.5 AI E2E 测试（`ai_tests\venv\Scripts\python.exe` + `run_e2e.py --diff`，真机测试包 `io.legado.miss.app.debug`）；`docs/specs/INDEX.md` 收尾同步；无 `android.util.Log` 残留。

## 5. Scenarios

### 正常

- S1：EPUB 注音书 → 阅读菜单开启「删除 Ruby 标签」→ 刷新后注音消失且正文无连续空格；关闭后注音恢复。
- S2：批量缓存 500 章 + 同时前台阅读同书 → 缓存完成后逐章打开无空章/乱码；中途杀进程后重启，已完整章节可读、半写章节自动重新下载。
- S3：GitHub 有新版 → 弹窗显示 `新版本 x.x.x（12.3 MB，2026-08-11）` → 下载安装一气呵成。
- S4：滚动模式阅读中顶部下拉 → 「已添加书签」提示 → 书签列表出现当前进度条目。
- S5：多卷书目录 → 点击卷二折叠 → 仅剩卷名行 → 搜索「第」显示 `卷一 12 处 / 卷二 8 处`。
- S6：Http TTS 段落间隔设 500ms → 朗读在段落间可听出停顿；定时朗读选「读完本章」→ 本章结束自动停止；选「剩余 3 章」→ 读完第 3 章自动停止。
- S7：书源 JS `java.singleFlight("token", () => fetchToken())` 并发 5 章节 → 仅 1 次真实请求，5 处共享结果。
- S8：开启删书联动 → 删除本地书 → WebDAV 书籍目录中对应文件同步消失。
- S15：帮助文档长文内搜索「重定向」→ 命中 12 处 → 上下键跳转高亮逐处可见（对应 R12 字段说明文档自验）。
- S16：无目录规则的 TXT（默认 30 万字）导入 → 按设置字数（如 2 万）分割出 15 章；改设置后重新导入生效。
- S17：HttpTTS 源 JSON 含 `"enableCookieJar": true` → 导入后编辑页开关为开；发起朗读请求带 Cookie。

### 异常

- S9：WebDAV 断网时删书 → 本地删除完成，提示「WebDAV 文件删除失败」，应用不卡死。
- S10：书源 JS 在 `lock` 回调中抛异常 → 锁释放、异常按 JS 调试日志输出，不影响其他书源。
- S11：更新源为第三方 JSON（无 size/date）→ 弹窗只显示版本号与更新说明，无空占位。

### 边界

- S12：覆盖安装（老版本 delTag 已有错误位数据）→ 开关首次点击后即正确生效，无需清数据。
- S13：API 23 低端机 + 预测返回开启 → 无崩溃、无行为变化（特性自然降级）。
- S14：同一章节「批量缓存与前台阅读」同时到达 → 后到方等待锁后命中前者结果，不重复下载。
