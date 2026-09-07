# real-device-bugfix-0908 规格

> 来源：用户 2026-09-08 真机反馈 5 项（书源域名分组卡死/替换净化双搜索框/云同步任务弹框透明/书架媒体重复/订阅栏目文件夹残留）。
> 流程：根因排查（4 子代理源码穿透）→ 本设计 → 红队对抗 ≥3 轮 → 实施 → 自测（模拟器 L2 + 全量 L3 归用户验收）。

## Bug1 书源管理按域名分组卡死/闪退（1 万+ 书源）

### 根因（按确定性排序）
- R1-主因 `BookSourceScreen.kt:66-83`：sourcesSignature 每次重组全量 `sources.toList()` + 1 万条×13 字段 joinToString（约 1MB 巨串）未 remember；debugMessages/DB 每 500ms 发射等任一变化都触发 → 主线程持续数十~数百ms 字符串构建。
- R2-高 `BookSourceScreen.kt:157-176`：非 reorder 分支 `sources.forEach { item() }` 手工展开万级 item（域名模式近 2 万闭包），且 content 作用域直读 SnapshotStateMap（sourceHostHeaders）任意写即全量重跑；未用 `items(key)`。
- R3-高 `BookSourceActivity.kt:481-487`：hostMap 每次 DB 发射全量重算 1 万条 URL→PublicSuffix（带锁二分）；hostMap 普通 HashMap 被 IO 线程（排序比较器）与主线程（buildSourceHostHeaders/getSourceHost）并发读写 → CME/HashMap 死循环（"闪退"主形态之一）。
- R4-中高 `BookSourceActivity.kt:534-541` + `SnapshotListUpdates.kt:55-62`：replaceByIndex 万级逐项比对，同 URL 不同内容分支 removeAt+add O(n) 移位，批量更新近 O(n²)；updateSourceHostHeaders 万次 map 写；refreshDebugMessages 全量遍历每 500ms。
- 闪退定性：主线程饱和 ANR 判死 + R3 并发破坏；OOM 风险来自 R1 巨串 GC 风暴。

### 修复设计（短期止血，行为等价）
1. `BookSourceScreen`：删除 sourcesSignature 巨串指纹；改由宿主传入 `dataVersion: Int`（Activity 侧数据发射时递增）作为 orderedSources 重置 key。
2. 域名分组渲染：预构建扁平 `List<RowModel>(isHeader, headerText, source)`，单个 `items(key = { it.source.bookSourceUrl 或 header:id })` 批量提交；sourceHostHeaders 读取移出 LazyColumn content 作用域（在构建 RowModel 时完成）。
3. `BookSourceActivity`：host 预计算收敛到单次（按发射批构建 host 伴随数据，排序与 header 共用）；hostMap 写入收敛到主线程 collect 内（消除跨线程写），或换 ConcurrentHashMap。
4. `SnapshotListUpdates`：equals 成立分支改 no-op（当前 removeAt+add 恒等移位无意义）。
5. 长期（不列入本次）：分组/排序下沉 VM Flow；域名折叠/Paging。

### 验收
- 1 万+ 书源（可用备份 JSON 导入）开启域名分组：进入页面可交互、滑动不冻结、切换分组/搜索无 ANR；logcat 无 CME/死循环；功能等价（分组头/搜索/排序/多选）。

## Bug2 替换净化页头部多一个搜索框

### 根因
`ReplaceRuleActivity.initComposeContent()`（L120-122）removeView 用了 `binding.recyclerView.parent`（FrameLayout 中间层）作为容器，而 titleBar/selectActionBar 的真实 parent 是根 LinearLayout → `removeView` 静默 no-op，TitleBar（内嵌 view_search）残留显示；ComposeView 加入 FrameLayout(weight=1) 在其下 → 双搜索框。

### 修复
对齐 BookSourceActivity 正确模式：`binding.titleBar.visibility = View.GONE; binding.selectActionBar.visibility = View.GONE`（GONE 与父容器无关），并修正 L119 注释表述。

### 验收
替换净化页单搜索框（Scaffold 内），原 GONE 语义节点不再可见；功能等价（多选/拖拽/导入导出）。

## Bug3 云同步任务弹框透明（PackageSyncTaskDialog）+ 透明弹框排查

### 根因（子代理取色链闭环）
- ComposeDialogFragment 窗口层透明（styles.xml Theme_Legado_ComposeDialog_Center windowBackground=transparent + setBackgroundDrawableResource(R.color.transparent)）。
- AppDialogFrame 卡片唯一背景 = style.surface = ColorUtils.withAlpha(surfaceBase, layoutAlpha)，layoutAlpha = AppConfig.dialogAlpha/100（主题包可携带 <100）→ dialogAlpha<100 时卡片半透明，透过透明窗口直透页面背景。
- PackageSyncTaskDialog 由 View 系（applyTint 不透明窗口）重写而来，成为透明表现最显眼的弹框；AppDialogFrame 系所有弹框（60+）在 dialogAlpha<100 时统一半透明——设计语义为"主题弹框透明度"，但低值时可读性崩坏。
- **独立 bug**：SourcePickerDialog（ui/book/manage/SourcePickerDialog.kt:138）SourcePickerPanel 根 Column 无任何 background → 无关 alpha 恒透明（最严重）。

### 修复
1. SourcePickerDialog 根 Column 补 `.background(rememberAppDialogStyle().surface)`（独立 bug 修复）。
2. AppDialogFrame 可读性兜底：`rememberAppDialogStyle()` 的 layoutAlpha 语义保留（主题透明度特性不阉割），但 AppDialogFrame 卡片外增加 dim 补偿——ComposeDialogFragment 按 layoutAlpha 动态提升 dimAmount（alpha 越低 dim 越接近默认 0.32），低透明度主题下背景变暗保证可读，同时保留"透出背景"特性。
3. PackageSyncTaskDialog 无需单独修（随 2 全局收敛，与全部 Compose 弹框一致）。

### 验收
- dialogAlpha=100：全弹框不透明（现状不变）。
- dialogAlpha<100 主题：弹框半透明可读（背景 dim 补偿），SourcePickerDialog 不再透出页面。
- PackageSyncTaskDialog 与同页其他弹框视觉一致。

## Bug4 书架媒体功能重复——删除入口与页面

### 依据
入口唯一（MySettingsData.kt:117 actionRow + :335 路由）；页面 MyFeatureBooksActivity 无其他消费方；功能与书架页原生视频书点击（BookshelfFragment1/2 → 播放队列）完全重叠。

### 改动清单
1. MySettingsData.kt:117 删 actionRow、:335 删路由分支。
2. 删 ui/main/my/MyFeatureBooksActivity.kt。
3. AndroidManifest.xml:319 删声明。
4. 删字符串 my_feature_books/_desc/_empty（values 与 values-zh）。

### 验收
"我的"页无书架媒体入口；编译过；书架视频书点击播放不受影响。

## Bug5 订阅栏目文件夹视图残留（bug 复现）

### 根因
RssFragment.applyModernRssMode()（L432-442）切新版订阅时只隐藏 recyclerView/tvEmptyMsg/rss 容器，**漏 folderComposeView**（fragment_rss.xml:28-34，经典模式 applyView() 置 visible）→ 文件夹视图压在新版容器下透出。
修复丢失链路：applyModernRssMode 生于 3c8aa5c7b（创建时即缺隐藏）；e706bae53 只修了反向残留+自愈 syncRssModeIfChanged，但自愈调用的正是缺隐藏的 applyModernRssMode → 自愈永不生效。

### 修复
applyModernRssMode() 补 `binding.folderComposeView.gone()`（一行）；自愈链 L313 随之收敛。

### 验收
复现路径操作后新版订阅页无文件夹视图残留；经典↔新版双向切换、文件夹样式进出均正常。

## 红队 3 轮修订回写（2026-09-08，全部采信）

- **R1-P1.1/P3.7（T5）**：dataVersion 仅在 replaceByIndex 实际发生变更时递增（replaceByIndex 返回 Boolean），避免 identical 重发射重置拖拽中间态。
- **R1-P1.2/R2-P2.6/P3-P3.4（T4）**：dim 基线为 Theme.Dialog 默认 0.6（非 0.32）；onStart 以 window 当前 dimAmount 为基线单调取 max 上浮；dialogAlpha==100 时 dimAmount 零改动（60+ 弹框回归红线）；E-Ink 分支（dim=0）保持最高优先级。
- **R1-P1.3/R2-P2.5（T5）**：hostMap 彻底删除——map 步（IO 线程）内构建局部 url→host 表供排序比较器使用（消除比较器内查询与 IO 写）；主线程 collect 内 hostMap.clear()+putAll(local) 成为唯一写点；同步改 L433/L539 两处消费点。
- **R2-P2.1/P2.2/P2.3（T5）**：RowModel 预构建（含 toList 拷贝）必须置于 remember(dataVersion, showSourceHost, groupSourcesByDomain)；dataVersion 递增点放 collect 末尾（header 写入之后）；sourceHostHeaders 变化经 dataVersion 传递。
- **R2-P2.4**：SnapshotListUpdates equals no-op 化安全（keyed diff 下原 removeAt+add 无语义），前提迁移保持 items(key)。
- **R2-P2.9**：2 万 items 单次提交成本 ~2-5ms，无需 Paging。
- **P3.1（T3）**：补删 my_feature_video/my_feature_image 字符串（values/values-zh 各 2 条）。
- **P3.5/P3.6（T4/T6）**：自测加 alpha=0/20/50 极端档；dim 补偿不覆盖非窗口内嵌面（AiProviderEditScreen 等内嵌 AppDialogFrame 场景），登记边界。
- **R1-P1.4**：spec 措辞修正——BookSource 参照实际为 titleBar=GONE + selectActionBar=removeView（其布局恰好生效）；ReplaceRule 采用 GONE-both 最稳，不回改 BookSourceActivity。
- **R1-P1.5/P3.3/P3.8/P3.9/P3.10**：核验通过项（T2 安全且验收需含"新版→经典+文件夹样式"用例；13 处同族 removeView 仅 ReplaceRule 有中间层问题）。

## 实施顺序
Bug2 → Bug5（一行级）→ Bug4（删除链）→ Bug3（dim 补偿+SourcePicker）→ Bug1（性能止血，独立验证）→ 统一自测（模拟器 L2 全覆盖）。
