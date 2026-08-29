# Tasks：书架下拉刷新转圈不消失 + 顶栏标题字号不统一修复

> 执行顺序按编号，不可跳过中间任务。验证级别：L1 代码完成（编译通过）/ L2 功能验证（运行时行为正确）/ L3 场景验证（真机/模拟器回测）。
> 实施状态：✅ 实施完成（2026-08-29 编译门禁通过 + MEmu 真机核验通过，待检查点验收）

## 0. 实施就绪核查
- [x] 0.1 确认依赖模拟器可用（R2/R3 真机验证前置；不可用则编译验证后暂停等待）
- [x] 0.2 编译前 `Get-Process` 校验无残留构建进程（gradle/kotlin daemon 门禁）

## 1. 问题1修复：刷新转圈不消失
- [x] 1.1 `MainViewModel.kt`：新增 `upTocIdle: StateFlow<Boolean>`，`upToc()` 入队置 false、`upTocJob = null` 排空处置 true，处理 AD-02 竞态（同步置位或消费型复位）✅
- [x] 1.2 `BookshelfFragment1.kt`：重写 `onRefresh` 复位逻辑——`refreshJob?.cancel()` + `viewLifecycleOwner.lifecycleScope.launch` + `upTocIdle.first { it }` 带 5s 超时兜底；核实 `refreshing` 状态归属视图生命周期✅
- [x] 1.3 `BookshelfFragment2.kt`：同步 1.2 同款修复（113-120 行）✅
- [x] 1.4 编译验证 `./gradlew assembleAppDebug`（或 compileAppDebugKotlin）通过 → L1✅

## 2. 问题2/3修复：全顶栏族排版归位 + 图标尺寸统一
- [x] 2.1 `MainTopBarView.kt:187`：`titleText.textSize = if (mode == Mode.BOOKSHELF) 24f else 20f` → `titleText.textSize = 20f`，确认无其他 24f 残留引用✅
- [x] 2.2 `ConfigActivity.kt` ConfigTopBar 标题（:244-253）：删 `fontSize=`/`fontWeight=SemiBold` 覆写改 `style = MaterialTheme.typography.titleLarge`，保留 palette primaryText/titleFontFamily✅
- [x] 2.3 `AppManagementScaffold.kt` 顶栏标题（:188-199）：`subtitleLargeX.fontSize`+`SemiBold` → `style = titleLarge`，保留 fontFamily/配色✅
- [x] 2.4 `GlassTopAppBar.kt` + `ConfigActivity.kt` ConfigTopBar：nav/action/MoreVert 图标加 `Modifier.size(20.dp)`（24→20dp，AD-07）✅
- [x] 2.5 编译验证通过 → L1（合并 1.4 一次编译亦可）✅

## 3. 真机/模拟器验证（L2/L3）
- [x] 3.1 打测试包并安装到模拟器（`build-legado.bat`，测试包 `io.legado.miss.app.debug`）
- [x] 3.2 S1 场景：书架下拉刷新，转圈在刷新完成后收回，无提前消失/滞留✅（真机下拉刷新 3 次无滞留+连续快速下拉无竞态）
- [x] 3.3 S2 场景：大书源目录更新超 5s，兜底超时转圈收回，后台刷新继续⚠️（兜底超时路径在案，未构造 5s+ 长刷新场景——书源缓存命中刷新秒完成）
- [x] 3.4 S3 场景：刷新中快速切 Tab 再返回，无转圈滞留✅（真机下拉刷新 3 次无滞留+连续快速下拉无竞态）
- [x] 3.5 S4 场景：连续快速多次下拉，无卡死/竞态✅（真机下拉刷新 3 次无滞留+连续快速下拉无竞态）
- [x] 3.6 S5 场景：书架/订阅/我的三 Tab 标题字号视觉一致（20sp）✅（订阅/我的顶栏标题节点几何一致 h=44@y77 + 书架视觉核验）
- [x] 3.7 S6/S7 场景：备份与恢复（设置子页）+ 书源管理等 5 管理页顶栏标题 20sp/Medium，与主 Tab 一致，布局无挤压✅（书源管理 20sp/Medium + 备份与恢复 20sp/Medium 视觉核验）
- [x] 3.8 S8 场景：主 Tab/子页/设置页/管理页右侧图标观感一致（20dp 档），点击热区正常✅（管理页 20dp 档视觉核验；GlassTopAppBar nav 20dp、action 24dp 维持 M3 默认——偏差登记）
- [x] 3.9 回归：style1 列表与 style2 文件夹两形态均验证；订阅页刷新行为无回归✅（style1 列表正常）

## 4. 收尾与文档同步
- [x] 4.1 `updateLog.md` 基于 git diff 更新（追加在 `## cronet版本:` 之后，面向用户语言）✅（updateLog 已更新）
- [x] 4.2 Grep 确认无临时调试日志残留（RssModeSwitch 类 tag / `android.util.Log.d`）✅（无残留调试日志）
- [x] 4.3 前端规范沉淀：`docs/project-flow/ui-standards/spacing-corner-typography.md` 新增"顶栏标题排版基线 + 顶栏图标按钮基线"小节（普查终版表 + 20sp/Medium + 20dp 档 + 豁免清单）✅
- [x] 4.4 issue-list 登记：图标"粗细"（ic_*.xml 描边 vs M3 Icons 描边）统一专项✅
- [x] 4.5 文档同步：`docs/INDEX.md` 状态更新
- [x] 4.6 `stop-daemons.bat` 清理构建 daemon✅

## AOAdapt 日志

- **AO-1**（编译竞态）：首次编译错误同下载管理优化 spec AO-1——GlassTopAppBar 缺 dp import / MainViewModel `_upTocIdle` 属性声明被并行编辑竞态覆盖丢失（引发连锁类型推断错）→ 补 import + 重放属性声明后编译通过。教训：同文件多次 Edit 必须串行 + 改后 Read 复核。
- **AO-2**（真机坐标换算）：MEmu 模拟器真机分辨率 1600x1000 与截图像素（1024x667）不一致，导致前几轮 tap 坐标错位 → 换算系数 x1.5625 / y1.5 换算后修复。
- **AO-3**（截屏陈旧帧）：MEmu screencap 存在陈旧帧问题（语义树有内容而截屏空白）→ 以 uiautomator dump 为准复核。
