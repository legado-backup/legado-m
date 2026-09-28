# issues-found · 全内容平台下一阶段主线

> 记录本主线实施期间**真机 L2** 挖出的问题（含连带修复与未覆盖项）。格式：现象 → 证据 → 根因 → 修复 → 回归用例。

---

## IF-01（P0）自动路由「进了播放器但不播」——`rssArticles` 为 null 静默 return

| 项 | 内容 |
|----|------|
| 发现批次 | W2 批次 L2（`l2_verify_playback_selfheal.py` 首轮 4 项中 2 项 FAIL） |
| 归属 | W1 任务 2.2（REQ-11 自动转内置播放器） |
| 现象 | 订阅正文解析出 `<video>` ⇒ 自动进入 `VideoPlayerActivity`，但**播放器一直不播**（无报错、无提示） |
| 证据（真机日志） | `VideoPlay: rssArticle is null in startPlay, rssArticleIndex=0`；此后无 `ExoPlayer prepareAsyncInternal` / `sniffVideoType` 等任何播放链路日志 |
| 根因 | VM 侧路由只有「单篇文章」上下文（无文章列表），`ReadRss.prepareVideoPlayContext(rssArticle)` 把 `VideoPlay.rssArticles` 写成 `null`；`VideoPlay.startPlay` 的文章解析式为 `rssStar ?: rssRecord ?: rssArticles?.getOrNull(index)` ⇒ **三项全空** ⇒ 静默 `return`（设计上「滑动退出致 null 属正常」的静默分支被误命中） |
| 修复 | `ReadRss.prepareVideoPlayContext`：`VideoPlay.rssArticles = rssArticles ?: listOf(rssArticle)`（兜底「仅含本篇」列表；索引由 `indexOfFirst` 命中为 0；`rssArticlesHasMore=false` 诚实表达无上下滑动上下文） |
| 回归用例 | `RssVideoRouteTest.playContextMustBeResolvableByPlayer`（**先红后绿**：修前 FAILED → 修后 PASS） |
| 判据加强 | W1 原 L2 判据「进入 `VideoPlayerActivity`」不足以证明可用 ⇒ 加强为「**进播放器 + 有嗅探/裁决日志**」（`l2_verify_playback_selfheal.py`，4/4 PASS） |
| 教训 | 「到达目标页面」≠「功能可用」；跨层上下文（列表 → 播放器）必须有**可解析兜底**，否则静默失败无人知晓 |

---

## IF-02（P0 · 用户报障 · 更严重）订阅视频「上下滑切换上/下一个」全失效 —— `rssArticles` 退化为单篇

| 项 | 内容 |
|----|------|
| 发现批次 | **用户报障（2026-09-27 真机）**：视频订阅源在自由布局下，沉浸式上滑下滑切换上一个/下一个视频**失效**；传统式**也没有**上一部下一部；视频书源侧正常 |
| 归属 | W1 任务 2.2（REQ-11 自动转内置播放器）**×** W2 §3 连带修复（IF-01 的修法本身引入） |
| 现象 | 播放器内**无法**切换到上/下一篇文章：沉浸式 `ViewPager2` 竖滑不翻页、传统式上一部下一部不可用 |
| 证据（真机，**先红后绿**） | 新增 `l2_verify_video_article_swipe.py` 在**未修复包**（`3.26.092721`）上：路由 PASS（前台=VideoPlayerActivity）但上滑/下滑 `switchToArticle idx=N` **切换行均为空** ⇒ 两项 FAIL、退出码 1 |
| 根因 | ①W1 的 VM 路由只有「单篇文章」上下文，调用 `prepareVideoPlayContext(rssArticle)` 不传列表；②W2 为修 IF-01 在**单一写入点**内兜底 `rssArticles ?: listOf(rssArticle)` ⇒ `VideoPlay.rssArticles` **退化为 1 篇**；③播放器侧一切上下切换都要求 `size > 1`（`VideoFragment.isArticleMode`、`VideoPlayerActivity` 的 `hasPrev/hasNext`）⇒ 手势与按钮**同时**为假 |
| 书源影响面（用户要求核实） | **零影响**。书源路径不写 `rssArticles`；且 `VideoFragment.onFling` 的书源分支要求 `rssArticles.isNullOrEmpty()` 才走 `onBookVerticalFling`；`VideoPlayerActivity.onNewIntent` 在书源意图（无匹配 `record`）时以 `preserveRssArticlesContext=false` 清空 ⇒ 与用户「视频书源没问题」的观察一致 |
| 修复 | `ReadRssViewModel` 命中分支按**列表页同口径**（`RssArticleDao.getListByOriginSort`：同源 + 同分类 + `order` 倒序，不 select 大字段）补齐完整列表；并保证**含本篇**（该判定早于落库，首读文章可能尚未入库 ⇒ 不在则 `add(0)`，避免索引兜底 0 指向别的文章） |
| 回归用例（先红后绿） | `RssVideoRouteTest.autoRouteMustCarryArticleListContextForSwipe`（修前 FAILED）+ 新 `RssArticleDaoVideoContextTest`(3)（查询口径/大字段规避契约） |
| 判据重建（**关键沉淀**） | 该能力长期**无有效回测**：旧判据链（`l2_verify_video_player.py --scenario swipe_article`、`swipe_test_log.py`）依赖**已从源码移除**的 `SwipeTest`/`VideoGesture` 临时 tag ⇒ `capture_log` 恒 0 行、场景恒「未触发」（假覆盖）。新增 `l2_verify_video_article_swipe.py` 改用**现有正式日志** `VideoRoutesDiag switchToArticle idx=N` 作判据 |
| 教训 | ①「修一个静默失败」不能顺手把**能力维度**（列表上下文）降级掉 —— 兜底要诚实表达「无上下文」而非伪造单篇；②**临时埋点被清理后，依赖它的 L2 判据必须同步迁移到正式诊断日志**，否则门禁变「空心」（本项即因此静默漏过） |

---

## IF-03（P0 · 用户报障二次复现）**自由布局（样式 5）**下视频上下滑仍失效 —— `articles` 恒为空列表

| 项 | 内容 |
|----|------|
| 发现批次 | **用户真机报障（2026-09-27 深夜，安装含 IF-02 修复的 `3.26.092722` 后）**：自由布局下视频「上滑下滑 / 上一部下一步」**仍然有问题** |
| 关键区分 | **IF-02 修的是「阅读页自动路由」**（`ReadRssViewModel` → `prepareVideoPlayContext` 补齐列表）；**本条是「列表点击路径」**（`RssArticlesFragment.readRss` → `ReadRss`）—— **两条完全独立的链路**，IF-02 的修复覆盖不到 ⇒ 这正是「修完仍有问题」的原因 |
| 现象 | 从**自由布局**（`articleStyle=5`）列表点开视频文章，播放器内上下滑不切换、传统式上一部下一部不可用 |
| 根因 | `RssArticlesFragment.initData()` 的 DB 流回调中，`articlesState.value = newList` **只在 `if (useComposeList)` 分支内**赋值；而**样式 5 走 View 渲染路径**（只 `adapter.setItems(...)`）⇒ `articles` getter 所读的 `articlesState` **恒为空列表** ⇒ `readRss` 把**空列表**交给 `ReadRss` ⇒ `VideoPlay.rssArticles = emptyList()`（**非 null，故 `?:` 兜底不生效**）⇒ 播放器侧 `size > 1` 的文章模式判定全为假 |
| 引入批次 | **CF 6.2 第五批 `b2db2cc`**（RSS 五样式族换装 Compose）：新增的 `articlesState` 单源只服务 Compose 路径，**样式 5 的 View 路径未同步** |
| 修复 | 把 `articlesState.value = newList` **前置到渲染路径分派（`if (useComposeList)`）之前** —— 两条渲染路径共用同一份列表，消除口径漂移 |
| 回归用例（先红后绿） | 新 `RssArticlesReadContextTest`(2)：① `articlesState` 单一赋值点 ② 赋值必须在 `if (useComposeList)` **之前** ③ `readRss` 取自单一数据源 |
| L2 判据扩展（**已真机验证**） | `l2_verify_video_article_swipe.py` 新增 **`--scenario list`**（`type=2` + `articleStyle=5` + 真实 item 点击驱动）。因 `RssSortActivity` 未 `exported`（`am start` 不生效），脚本路径不可达 ⇒ 改走**主壳 UI 导航**取证：`订阅 Tab → 探针源 → 自由布局列表 → 点第 1 篇` ⇒ 进 `VideoPlayerActivity` 后**两次上滑**，日志出现 `VideoRoutesDiag switchToArticle idx=1` / `idx=2` ⇒ **PASS** |
| 教训 | **修一处报障必须穷举同一能力的全部入口**：同一条「上下滑切换文章」至少有 4 条进入链路（**列表点击** / 阅读页自动路由 / 历史记录 / 收藏页）。按「症状」修而不按「链路」修，必然漏（IF-02 与 IF-03 即为实例） |

---

## IF-04（P0 · 链路穷举收口）历史记录 / 收藏页两条入口未补齐列表上下文

| 项 | 内容 |
|----|------|
| 发现批次 | 2026-09-28 交接文档接手后，对 IF-02/IF-03 的「4 条链路」清单做**逐链路复核**时确认：③④ 两条**从未修**（此前仅登记为「未改（历史行为）」） |
| 现象 | 从**阅读历史**或**订阅收藏页**点开视频文章进入播放器时，沉浸式上下滑不切换、传统式上一部下一部不可用（与 IF-02/IF-03 同源同判据）；从订阅列表进入则正常 |
| 根因 | 播放器侧文章模式的唯一判据是 `VideoPlay.rssArticles.size > 1`。②③④ 三条入口都**只带单篇上下文**：③ `ReadRss.readRss(activity, record)` 直接 `startActivity`（连 `prepareVideoPlayContext` 都不走）；④ `RssFavoritesFragment.readRss` 传 `rssArticles = null` ⇒ 单一写入点内 `?: listOf(rssArticle)` 兜底为 **1 篇** |
| 修复 | `ReadRss` 抽出统一补齐入口 `resolveVideoArticles(article, given)`（口径与列表页 `flowByOriginSort`、阅读页 `getListByOriginSort` 完全一致：**同源 + 同分类**；查不到或未含本篇则**本篇补入并置首**），并把两个 `type==2` 分支收敛到 `startVideoFromActivity` / `startVideoFromFragment` 两个私有 helper。列表路径（`size > 1`）仍**同步启动**，不引入查库延迟；仅上下文缺失时走异步补齐 |
| 回归用例 | `RssVideoRouteTest.historyAndFavoriteRoutesAlsoResolveArticleList`（① 补齐入口与口径 ② 本篇补入置首 ③ 两处调用点 ④ 播放器启动点收敛为 2 个 helper） |
| 真机取证（**2026-09-28 补取 · 已通过**） | ③④ 两条链路**均已真机验证通过**。**判据**（`VideoRoutesDiag switchToArticle idx=`）：③ **阅读历史**：订阅页 ⋮ → 历史记录（`ReadRecordDialog`）→ 点探针条目 ⇒ 自动路由到 `VideoPlayerActivity`，两次上滑产生 `idx=0` / `idx=1`；④ **收藏页**：订阅页 ⋮ → 收藏夹（`RssFavoritesFragment`）→ 点同一条目 ⇒ 同样路由到播放器，上滑产生 `idx=0` / `idx=1`。两链路均**无 FATAL**。**可复用取证路径**：① 先跑 `l2_verify_video_article_swipe.py --scenario list --keep-probe` 种探针数据（该脚本 `list` 场景因 `RssSortActivity` **非 exported**、`am start` 无效 ⇒ 必在「点文章」处失败，属**预期**，数据已留存）；② 以**独立常驻内容服务**（复刻其 `/sw/paper{1..3}` 合成正文路由）+ `adb reverse tcp:8899` 恢复可达性（脚本退出会关闭服务 ⇒ 正文不可达则不会路由到播放器）；③ 手工 UI 导航（主壳底部 4 Tab 设备坐标 ≈ 330/642/955/1267，y≈836；主壳 `uiautomator dump` 恒 `could not get idle state` ⇒ 必须截图+比例坐标）；④ 收藏页需先有 `RssStar` 行（可由库直接种入：镜像同源文章行 + `starTime`）。 |

---

## IF-05（P0 · 用户真机报障 · 静默失效）书源编辑页六个 Tab 的编辑项**全部不显示**

| 项 | 内容 |
|----|------|
| 发现批次 | **用户真机报障（2026-09-28，安装 `3.26.092800` 后）**：「书源编辑页面，基本、搜索、发现等下面的编辑项全部没有了」 |
| 现象 | 页头/两行勾选/TabLayout 均在，**Tab 下方列表区空白**；切任意 Tab（基本/搜索/发现/详情/目录/正文）都无字段；**无异常、无日志**（静默失效） |
| 根因 | `f7ac81e`（CE-a #12，2026-09-26）把 `activity_book_source_edit.xml` 退役、改为 `BookSourceEditShellViews` 程序化重建时**丢失旧 XML 的 `app:layoutManager="androidx.recyclerview.widget.LinearLayoutManager"` 永久兜底**；宿主 `BookSourceEditActivity.initView()` 仅在 `adapter.editEntityMaxLine < 999` 分支内装配 layoutManager，而 `AppConfig.sourceEditMaxLine` 默认返回 `Int.MAX_VALUE`（≥999）⇒ **该分支永不成立** ⇒ `RecyclerView` 无布局管理器 ⇒ 列表项全部不渲染 |
| 引入批次 | **`f7ac81e`（CE-a #12，XML 退役 + 六段结构程序化重建）** |
| 修复 | `initView()` 改为**无条件**装配 layoutManager，条件只用于选择变体（`NoChildScrollLinearLayoutManager` vs `LinearLayoutManager`）—— 等价旧 XML 的永久兜底。commit `7d8b59d` |
| 回归用例（先红后绿） | ① `BookSourceEditShellMigrationTest.recyclerViewAlwaysGetsLayoutManager`（先写、`AssertionError@:109` 复现，修复后转绿）；② **通用防线** `ProgrammaticRecyclerViewLayoutManagerGuardTest`：全量扫描源码中**程序化创建 `RecyclerView`** 的文件，锁三条不变量 —— 「非壳文件必须自行装配 layoutManager」「壳由登记宿主无条件装配」「登记表不得过期」 |
| 同类排查（用户要求） | ① 全部「XML 退役」提交中带 `app:layoutManager` 的布局**仅 4 处**：`activity_book_source_edit`（本项）、`activity_book_source`/`activity_rss_source`/`activity_rule_sub`（后三者现已纯 Compose `LazyColumn`/`AppManagementScaffold`，无 RecyclerView）⇒ 不受影响；② 全局程序化 `RecyclerView` 创建点**共 5 处**（书源编辑壳 / 主题管理壳 / 图库 / 订阅源编辑 / 标签栏），除本页外**均已装配 layoutManager**（主题管理族 14 页宿主无条件装配、订阅源编辑无条件装配）⇒ **唯一缺陷页 = 书源编辑页** |
| 教训 | **「程序化重建 XML」必须逐属性对照**：XML 里带默认语义的属性（尤其 `app:layoutManager`、`app:itemAnimator`、`android:visibility`）是**永久兜底**，代码里的条件赋值**不能**替代它（默认配置可能恰好走不到赋值分支）。同源盲区：迁移测试的「易丢语义清单」与迁移实现出自同一次理解 ⇒ 清单漏项即测试漏项 |

### IF-05 反思：为什么测试体系没发现 · 后续如何避免

**为什么没发现（三层原因）**

1. **同源盲区**：迁移测试 `BookSourceEditShellMigrationTest` 锁的是「易丢语义逐项复刻」清单（Spinner `theme+entries` / 勾选默认值 / `review` 隐藏 / 36dp+3dp / `clipToPadding`）——**该清单本身就漏了 `layoutManager`**。测试与实现出自同一次迁移、同一份（不完整的）理解 ⇒ 清单漏项即测试漏项。
2. **静默失效 + 判据缺失**：缺陷无异常、无日志，编译与既有**文本型契约单测**全绿照样逃逸；既有 L2 脚本未覆盖「书源编辑页」这一页面。
3. **未做同构页差异比对**：同构的 `RssSourceEditActivity` **无条件**装配 layoutManager（参考实现是对的），但迁移时未把「同构页差异」当作必查项。

**后续避免（已落地 + 机制改进）**

- ✅ **已落地 · 通用防线**：`ProgrammaticRecyclerViewLayoutManagerGuardTest` 全量扫描程序化 `RecyclerView`，新壳漏登记 / 新页漏装配即红。
- ✅ **已落地 · 反例库免疫**：G-18 新增 **R-007**（invariant：宿主必须含**无条件** layoutManager 装配 + 通用防线测试必须存在）⇒ 历史失守永久免疫。
- ⏳ **机制改进（待纳入 XML 退役迁移 SOP）**：XML 退役类迁移**必须附「XML 属性全量对照表」**——逐个 `android:`/`app:` 属性标注「重建后有 / 无 / 刻意保留」，并对**永久兜底类属性**（layoutManager 等）单独加断言；同时新增「**同构页差异比对**」卡点（同构页的正确写法必须逐项比对）。

---

## IF-06（P1 · 播放器内「上下滑不切换」的**中心带阻塞**）——现象已真机复现；**因果未定位（前一版「引导卡吞手势」结论已被推翻）**

| 项 | 内容 |
|----|------|
| 发现批次 | 第 3 轮交接文档 §四 登记为「引导卡疑似吞手势、根因未定位」；本轮（2026-09-28）做定向复测 |
| **现象（可复现）** | 沉浸式播放器（文章上下文已就绪：左下「第 N 篇 · 共 M 篇」）内，**部分起点**的竖向滑动**不触发** `VideoRoutesDiag switchToArticle` |
| **复现矩阵（实测）** | 起点 `(800,760)`（卡可见）⇒ **无**切换；`(300,500)`（卡可见）⇒ **无**切换；**`(1200,760)`（卡可见）⇒ `idx=1` 可切换**；点「知道了」关卡后 `(800,760)` ⇒ `idx=2` 可切换 |
| **因果判定（重要 · 已推翻前一版结论）** | ① 卡 bounds 实测 = **[38,334]-[1562,732]**（近满宽，**含 x=1200**）⇒ 若卡是主因，`x=1200` 也应被阻塞，但实测**可切换** ⇒ **卡不是唯一/主要原因**；② 关卡后 `(800,760)` 可切换，说明该点位的阻塞**受其它状态影响**（非稳定由卡决定）⇒ 前一版「卡吞手势 ⇒ 已修」的因果**不成立**，**已从代码与 updateLog 撤回该主张**（不写未验证的用户可见修复） |
| 更可能的阻塞来源（待证） | ① 底部控件带 `left_bottom_container`（实测 bounds **[23,651]-[1450,795]**，内含可滚动子级）—— 可滚动子级会消费竖向拖动，且其水平范围**不含 x=1200**，与「x=1200 可切换」**吻合**；② 承载播放器的 `ViewPager`（bounds 近满屏，横向滚动，通常不消费竖向拖动，需排除）；③ GSY 播放器自身的控件层 |
| 已做的低风险加固（**不等于已修复**） | `VideoFragment.maybeShowGestureGuide()`：卡本身 + 卡内除确认按钮外的子级一律退出触摸路径（clickable/focusable/focusableInTouchMode=false）。**真机复测表明该加固未改变阻塞表现** ⇒ 仅作卫生性加固保留，注释已按实测边界改写 |
| 回归用例 | `VideoGestureGuideTransparencyTest`(2)：锁「加固不变量」+ 「未经验证的旧注释不得残留」；**不断言**修复该现象 |
| 下一步判据（接手直接可用） | **可复用 helper（本轮实战留在 `output/`，gitignore）**：`output/probe_server.py`（独立常驻探针内容服务 :8899，复刻 `/sw/paperN`）、`output/seed_star.py`（把探针文章镜像成 `RssStar` 收藏行）、`output/flip_pref.py`（把 `videoGestureGuideShown` 置回 false 以重置引导卡）。复核步骤：① 用 `uiautomator dump`（**播放器页可 dump**）取 `left_bottom_container` / `rv_episodes` 的实测 bounds，核对其水平范围是否恰好排除 `x=1200`；② 在其上做 `input swipe` 起点扫描（x 从 800 → 1200 二分）确定阻塞带的**左右边界**；③ 若确认为可滚动子级消费 ⇒ 按「只在可滚动子级内部消费、其余落回手势」处理；④备选方案：把手势挂点由 `surface_container` 提升到**页根**（`controlsLayer` 与 `playerView` 的公共祖先） |
| 教训 | ① **「代码看似不拦截」≠「实测不拦截」，反之亦然** —— 触摸因果必须**多点位 A/B**，单点对照会被状态混淆（本轮「卡可见/关卡」单点对照就得出了被推翻的因果）；② **证据不足时不得把结论写进注释与 updateLog**（本轮已按此原则撤回）；③ 阻塞带是**水平受限**的，说明消费者是具体子视图而非整层 |

---

## IF-07（P2 · 覆盖缺口 · 非缺陷）名场面书签**漫画/图片两路径**缺运行时打标回跳复测

**现象**：W8 9.3/9.4 的**文字路径**已真机端到端跑通（划词「加入名场面」→ 库页出现分组与条目 → 点击跳回 `ReadBookActivity`，见 tasks §9 记录 5 步取证）；**漫画路径**（`ReadMangaActivity` 长按菜单外的阅读菜单项）与**图片路径**（`ImageGalleryActivity` 长按图片菜单）只有静态锁定，未在真机上点过一次。

**未测原因（如实）**：当前模拟器样本书集只有文字书（`回归样本读物*`/`L2*`），**没有漫画书**（`isImage`）也没有**图片订阅源**（`type=1` 的 RSS 源）⇒ 无法构造两条路径的入口场景；造数据需先导入漫画源/图片订阅源，属另一批测试准备。

**当前覆盖**：`SceneBookmarkMangaEntryTest`(3) / `SceneBookmarkImageEntryTest`(2) 静态锁定（菜单项在位、`contentKind` 口径、锚点键、manga 项不得进 `mangaConfigMenuItems`）；接线方式与已验证的文字路径同源（同一 `SceneBookmarkHelper.addAndDescribe`）。

**后续复核判据（4 步）**：① 导入一个漫画源（或 `isImage` 书）+ 一个图片订阅源；② 漫画页菜单点「加入名场面」→ 库页出现 `contentKind=1` 条目（锚点含 `pageIndex`）；③ 图片页长按图片 → 菜单点「加入名场面」→ 库页出现 `contentKind=2` 条目（锚点含 `imageUrl` **与** `articleLink`）；④ 各点一次条目，确认分别落到漫画页 / 图片浏览页。

---

## 未覆盖项（如实登记，非缺陷）

| 项 | 说明 | 当前覆盖方式 |
|----|------|-------------|
| 音频侧真实播放错误（听书 / HTTP 朗读） | L2 需可用有声书 + 可控失效地址（造源成本高） | 单测 `PlaybackErrorPolicyTest`(13) + `AudioPlaybackSelfHealWiringTest`(5) |
| 多线路真实换线（`VideoRouteSelfHeal`） | L2 需多线路视频源（`type=2` + `ruleRoutes`/`ruleEpisodes`） | 单测 `decideRouteSelfHeal` 系列 + `VideoPlayerRouteSelfHealWiringTest`(5) |
| `ABORT`（预算耗尽 / 冷却期）真机触发 | 需连续 4 次不同档失败 | 单测覆盖（上限 3 → 第 4 次 ABORT + 冷却 + 冷却到期复位） |