# sync-upstream-optimizations-20260816 · tasks

> OpenSpec 四文档之一 ｜ 上游同步优化批次（2026-08-16） ｜ 状态：✅ 设计完成（待实施）
> 覆盖 16 项（项 1-12：喵公子/legado-E；项 13-16：阅读T/MD3/Jingshiro，08-16 20:15 并入）
> 完成标准三级：L1 代码完成⚠️ / L2 功能验证⚠️ / L3 场景验证✅（含真机）。完成后补 `✅ 日期` 与偏差说明。

## 0. 前置与基线（门禁）

- [x] 0.1 等待当前 Compose 化工作区（591 个未提交文件）提交固化 —— ✅ 2026-08-16 用户已提交（5f5652dbc 等），目标文件全 CLEAN 零冲突
- [ ] 0.2 基线构建：`build-legado.bat` 产测试包 `io.legado.miss.app.debug` 并安装 MEmu，冒烟主链路（书架/阅读/搜索）确认起点无坏 — L1（随最终打包执行）
- [x] 0.3 锚点复核：design.md 引用锚点于 2026-08-16 提交后工作区逐一实测（Book.kt:345/EpubFile:176/BookHelp:178/UpdateDialog:22/AboutActivity:111 等全部命中）— ✅ 2026-08-16
- [ ] 0.4 修正 `docs/project-rules/forks-reference.md` 集散地地址（momo-b5a.pages.dev → momoa.cc.cd）与原版停更状态备注

## 1. 阶段 1 · P0 修复（项 1-4）

### 1.1 EPUB delTag 修复（R1）

- [x] 1.1.1 `Book.kt` addDelTag `and`→`or`（对照 legado-E 964d49e diff）— L1 ✅ 2026-08-16
- [x] 1.1.2 `EpubFile.kt` ruby→TextNode→相邻合并算法 + import TextNode — L1 ✅ 2026-08-16
- [ ] 1.1.3 单元自测：构造含注音 ruby 的 EPUB 样张（可用项目 JVM 仿真器/本地测试路径），验证开/关/空格合并（S1、S12）— L2
- [ ] 1.1.4 真机验证：菜单两开关开/关切换后刷新阅读生效 — L3 🔴

### 1.2 章节缓存写入保护（R2）

- [x] 1.2.1 `BookHelp.kt` per-file Mutex 注册表 + `saveText` 临时文件原子改名 + 双重检查缓存 — L1 ✅ 2026-08-16（偏差见 AOAdapt #1）
- [ ] 1.2.2 并发自测：同书同章并发 3 路 getTextCache，验证仅一次下载且结果共享（S14）；杀进程半写场景验证 `.tmp` 不影响主文件（S2）— L2
- [ ] 1.2.3 真机验证：批量缓存 200+ 章期间前台阅读同书，完成后抽查章节完整 — L3 🔴

### 1.3 更新弹窗包大小/日期（R3）

- [x] 1.3.1 `UpdateInfo` 增 assetSize/publishDate 字段（默认值兼容第三方源）+ GitHub 资产解析（abi 匹配回退 universal）— L1 ✅ 2026-08-16（沿用既有 variant 匹配，size 取所选资产）
- [x] 1.3.2 `UpdateDialog` 副标题展示，无数据整行隐藏（S3、S11）— L2 ✅ 2026-08-16
- [ ] 1.3.3 真机验证：测试包内模拟 GitHub 更新弹窗展示（可用正式包 release 对照）— L3

### 1.4 日志导出分享（R4）

- [x] 1.4.1 `AboutActivity` shareLog()：buildLogsZip → Context.share(file)（FileProvider+AppConst.authority 既有工具复用）— L1 ✅ 2026-08-16
- [x] 1.4.2 Compose About 页加「分享日志」入口 — L1 ✅ 2026-08-16
- [ ] 1.4.3 真机验证：debug/release 包名均拉起分享且接收方可解压（S9 之外的正常路径）— L3 🔴

## 2. 阶段 2 · P1 阅读体验（项 5-7）

### 2.1 阅读页下拉书签（R5）

- [x] 2.1.1 `ScrollPageDelegate` 顶部下拉手势判定（阈值 64dp + ContentTextView.atChapterStart 判定），EventBus 触发 — L1 ✅ 2026-08-16
- [x] 2.1.2 Toast 提示 + 同位置去重直接入库（不弹窗，S4）+ `PreferKey.pullDownBookmark` 设置项（默认开，阅读设置-更多配置，View 偏好体系非 Compose）— L1 ✅ 2026-08-16（偏差见 AOAdapt #2）
- [ ] 2.1.3 验证：滚动模式加书签成功（S4）；页模式翻页无回归；开关关闭后手势无效 — L2
- [ ] 2.1.4 真机验证 🔴：连续下拉无重复书签堆积（同章节同位置去重）

### 2.2 目录分卷折叠 + 搜索匹配数（R6）

- [x] 2.2.1 ChapterListAdapter 折叠数据结构（allItems + collapsedVolumeUrls + applyCollapse 派生）— L1 ✅ 2026-08-16
- [x] 2.2.2 折叠箭头（▾/▸）渲染 + 卷头点击切换（折叠态点击先展开再跳转，兼容原跳转行为）— L1 ✅ 2026-08-16
- [x] 2.2.3 搜索态匹配计数：卷头行显示该卷匹配数（S5）— L1 ✅ 2026-08-16（总数在标题栏的展示留待真机阶段评估）
- [ ] 2.2.4 真机验证 🔴：多卷书折叠/展开/搜索/跳转 + 当前阅读章节高亮定位不受折叠影响 — L3

### 2.3 TTS 增强（R7）

- [x] 2.3.1 `ttsParagraphPauseMs` 配置 + 朗读设置面板入口（ListPreference 5 档：关/0.3/0.5/0.8/1.2s）— L1 ✅ 2026-08-16
- [x] 2.3.2 Http TTS 段落静音段插入（生成指定时长静音 WAV 媒体项 + onMediaItemTransition 停顿项不推进段落守卫，双模式均接）— L1 ✅ 2026-08-16
- [x] 2.3.3 系统 TTS 段落停顿（playSilentUtterance + onDone 停顿项守卫）— L1 ✅ 2026-08-16
- [x] 2.3.4 定时朗读对话框三模式（按分钟既有 / 读完本章【MD3】/ 剩余 N 章）+ BaseReadAloudService 计数/章末判定与停止通知（S6）— L1 ✅ 2026-08-16
- [ ] 2.3.5 真机验证 🔴：Http/系统双引擎段落停顿可感知；三模式定时（分钟/读完本章/剩余 3 章）到点停止准确；模式互斥切换 — L3

## 3. 阶段 3 · P2 进阶增强（项 8-12）

### 3.1 书源 JS 并发工具（R8）

- [ ] 3.1.0 🛑 前置门禁：浅克隆喵公子/阅读T 仓库（temp/forks-comparison，不入库），对比 singleFlight/lock/tick 真实实现的 Rhino Context 线程处理方式，结论回填本节后方可编码 — L1
- [ ] 3.1.1 新增 `JsConcurrencyHelper.kt`（singleFlight in-flight 表 / lock Mutex 队列 / tick；源级命名空间键；finally 清理；JS 回调在发起线程 Rhino Context 内求值）— L1
- [ ] 3.1.2 `JsExtensions` 三方法桥接（Rhino lambda 反射，对齐既有 java.* 方法模式）— L1
- [ ] 3.1.3 自测脚本：书源调试页运行并发 5 路 singleFlight（仅 1 次真实请求）、lock 串行、异常释放（S7、S10）— L2
- [ ] 3.1.4 真机验证 🔴：调试页断点/日志确认跨源键隔离 — L3

### 3.2 漫画长按保存（R9）

- [ ] 3.2.1 `ReadMangaActivity` 长按手势 + 确认弹窗（应用级弹窗容器）— L1
- [ ] 3.2.2 保存工具复用/提取（Android 10+ MediaStore，低版本既有路径 + 权限）— L1
- [ ] 3.2.3 真机验证 🔴：相册可见已存图（S 正常路径）— L3

### 3.3 WebDAV 删书联动（R10）

- [ ] 3.3.1 删书弹窗复选项 + `PreferKey.delBookSyncWebDav` 记忆（默认 false）— L1
- [ ] 3.3.2 `delBook` 异步删 WebDAV 书籍文件分支（**精确文件名匹配 + 歧义(0/≥2 命中)跳过提示**，失败 onError 提示不回滚，S9）— L1
- [ ] 3.3.3 真机验证 🔴：开启联动删本地后云端文件消失；断网删书不阻塞；同名歧义场景安全跳过（S8、S9）— L3

### 3.4 预测返回动画（R11）

- [ ] 3.4.1 🛑 硬门禁：grep `onBackPressed(` 覆写残留清零（**未清零前禁止 3.4.2**；Compose 化中途的 View 残留页面必须先迁移 dispatcher，否则 API 34+ 返回键失效）— L1
- [ ] 3.4.2 manifest 加 `enableOnBackInvokedCallback` — L1
- [ ] 3.4.3 回归清单 🔴：API 34+ 手势动画（阅读页/视频播放/WebView/Compose 列表页/弹窗返回），API < 34 无变化（S13）— L3

### 3.5 URL 超时/重定向开关（R12）

- [ ] 3.5.1 `AnalyzeUrl` 选项解析 readTimeout/redirect + 请求构建按 call 派生 client（不改全局单例）— L1
- [ ] 3.5.2 `redirect:false` 时 3xx 响应本体返回规则层验证；带选项请求**强制走 OkHttp 原生栈**（绕过 CronetTransport，选项不传导 Cronet 引擎）— L2
- [ ] 3.5.3 resolveIp 旧别名回归验证（既有机制，仅确认）+ URL 选项帮助文档补字段（含 Cronet 限制说明）— L2
- [ ] 3.5.4 真机验证 🔴：书源调试页 URL 带 `{"readTimeout":5000,"redirect":false}` 表现符合预期 — L3

### 3.6 TextDialog 帮助文档内搜索（R14，来源：阅读T 8/14）

- [ ] 3.6.1 `TextDialog` 顶栏可折叠搜索框 + 全文匹配 + 命中计数（44dp 搜索框高度规范）— L1
- [ ] 3.6.2 命中高亮（Spannable 语义色）+ 上一处/下一处跳转定位（S15）— L1
- [ ] 3.6.3 真机验证 🔴：书源帮助/URL 选项说明等长文档搜索可用，无命中提示正常 — L3

### 3.7 TXT 无规则分割字数可设置（R15，来源：MD3 8/10）

- [ ] 3.7.1 `PreferKey.txtSegmentLength`（默认=现硬编码值）+ `TextFile.analyze()` 读配置 — L1
- [ ] 3.7.2 阅读设置/本地书籍分区设置入口（数值选择弹窗，区间校验）— L1
- [ ] 3.7.3 验证：默认值行为零变化；改配置后重新导入/重新分析目录按新字数分割（S16）— L2

### 3.8 阅读记录页 OOM 核查加固（R16，来源：Jingshiro 8/7，核查型）

- [ ] 3.8.1 审计：构造压力明细数据实测内存曲线 + 写入路径同日重复膨胀检查（AD-10 先审计后修复）— L2
- [ ] 3.8.2 视审计结论修复（明细分页/按需加载 + 写入去重）或记录核查结论进 issues-found.md 后关闭 — L2
- [ ] 3.8.3 真机验证 🔴（若修复）：超长明细下阅读记录页无 OOM、列表流畅 — L3

### 3.9 HttpTTS 启用CookieJar 字段（R17，来源：阅读T 8/14）

- [ ] 3.9.1 `HttpTTS` 实体 + fromJSON 解析 + 编辑页开关行 — L1
- [ ] 3.9.2 `HttpReadAloudService` 按开关携带 CookieJar；默认 false 行为不变 — L2
- [ ] 3.9.3 真机验证 🔴：含 `"enableCookieJar": true` 的源导入解析与请求生效（S17）— L3

## 4. 收尾（门禁合规）

- [ ] 4.1 编译前按 `git diff` 逐文件对照更新 `assets/updateLog.md`（面向用户语言，追加于 cronet 版本条目后）— 强制门禁
- [ ] 4.2 步骤 5.5 AI E2E：`ai_tests\venv\Scripts\python.exe ai_tests/run_e2e.py --diff <基线>` 双轨用例 + 8 类证据 + 五件套报告；测试包 `io.legado.miss.app.debug`，禁止混用正式包 — 强制门禁
- [ ] 4.3 手工用例补测：E2E 无法覆盖的真机项（4.4 手势动画、3.5 长按保存、TTS 听感等）逐项执行并记录
- [ ] 4.4 检查 `android.util.Log.d|e` 零残留；工具输出敏感词扫描
- [ ] 4.5 🛑 检查点2：用户审核（含 5.5 测试报告）
- [ ] 4.6 INDEX.md 移入「已完成」；tasks 全项勾选补日期
- [ ] 4.7 文档同步：`docs/project-flow/task-navigation.md`、`quick-reference.md` 对应锚点更新
- [ ] 4.8 大型任务沉淀检查（spec-sedimentation）：本批上游对比方法论新经验（原版停更、喵公子为事实上游）回写 `forks-reference.md`

## 页面回执（实施完成后回填）

- 实施范围：16 项 / 实际改动文件数：__
- 组件复用：应用级弹窗容器 / 确认弹窗 / SettingsSelectableRow / 阅读浮层原语（复用情况回填）
- 真机状态：MEmu 测试包 io.legado.miss.app.debug（L3 项通过清单回填）

## AOAdapt 日志

### #1 任务 1.2.1 · 章节缓存保护降范围为写入层（2026-08-16）

- **Action**：原设计为「检查-下载-写入」全周期互斥（WebBook 层加锁 + 缓存命中短路）。实施时改为仅写入层保护：`saveContent` per-file Mutex + `saveText` 原子写（tmp+rename）。
- **Observation**：缓存键 `{index}-{titleMD5}.nb` 不含章节 URL，换源后同题章节指向同一文件；若在 `getContentAwait` 加缓存命中短路，换源刷新流程（先 `delContent` 再重取）语义可能被并发短路破坏，回归风险大于收益。
- **Adapt**：撕裂/覆盖由原子写+写互斥根治（R2 主诉求）；下载去重（S14 后半语义）暂缓，待真机确认重复下载确有体感损耗后再评估 WebBook 层方案。design.md §3.2 数据流图相应简化。

### #2 任务 2.1.2 · 下拉书签提示从浮层降级为 Toast + 设置入口落在 View 偏好页（2026-08-16）

- **Action**：原设计「阅读浮层提示条（独立配色）」改为 Toast 提示；设置开关落在 `pref_config_read.xml`（MoreConfigDialog 的 View 偏好体系）而非 Compose 阅读设置。
- **Observation**：阅读浮层提示条原语需要新增 Compose 组件并接入阅读菜单状态流，改动面与手势逻辑不成比例；Toast 已满足「触发可感知」验收。
- **Adapt**：首版 Toast；真机验证若用户要求浮层提示再升级。设置项随 MoreConfigDialog 既有体系，符合最小改动原则。

### #3 阶段2/3 之间 · 编译门禁被并行任务阻塞（2026-08-16）

- **Action**：阶段2 编译验证时发现工作区出现另一会话的半成品改动（SourceFolderAdapter/BookSourceActivity/RssSourceActivity/ExploreFragment/RssFragment + DB v104 SourceGroupCover 新文件），11 个编译错误均来自这些文件。
- **Observation**：本批次所有改动文件编译错误为零（单独验证通过）；全量 assemble 被并行工作阻塞，无法打包做 5.5 E2E。
- **Adapt**：本批次阶段3（P2 八项）与 5.5 E2E 暂停，等并行任务编译恢复或用户协调后继续；不得代改并行任务的文件。
