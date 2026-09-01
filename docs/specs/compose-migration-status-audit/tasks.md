# tasks.md — compose-migration-status-audit

> 对应 design.md 页级总表（已回写分册勘误+交叉审核轮 1-4 修订）与 AD-07 批次依赖。实施细节以 4 份分册为准（design-b1-b2 / design-b3-d4-flagship / design-b3-pages / design-b4-b5-pages）。每批完成后跑编译门禁+5.5 E2E+registry 回执，批间设检查点。状态：🔄 设计中（交叉审核 4/5 轮完成+修订闭环，待轮 5 终审）。

## 1. 进度审计与设计编制（本 spec 本体）

- [x] 1.1 三路并行扫描（文档/源码/基建）✅ 2026-08-30
- [x] 1.2 路线图/registry/红线原文抽取（S1-S6 样板定义、P2 15 组 22 页、P3 全集、N 清单）✅ 2026-08-30
- [x] 1.3 页级 69 类校准总表编制（design.md）✅ 2026-08-30
- [x] 1.4 批次计划 B0-B5 与 AD-01~08 定稿 ✅ 2026-08-30
- [x] 1.5 四份实施级设计分册产出（463/767/971/704 行，分册源码勘误 10 处回写总表）✅ 2026-08-30
- [x] 1.6 交叉审核轮 1（册间一致性 7E/6W）+轮 2（源码符合性 10 确认/2 部分）+修订闭环 ✅ 2026-08-30
- [x] 1.7 交叉审核轮 3（规范符合性 5E/12W/6I）+轮 4（完整性 1E/4W，四方映射 58/59→59/59 闭合）+修订闭环（28 条落盘+2 条合规跳过+主文档 4 处）✅ 2026-08-30

## 2. B0 deep-fix 收口（依赖前置，继承 ui-style-unify-deep-fix tasks §4/§5）

- [ ] 2.1 R3-4.1 订阅切换专项：经典↔新版反复切换无残留+即时生效（真机）
- [ ] 2.2 R3-4.2 视频手势回归：上下滑切视频/左右滑 seek/长按倍速/双击暂停四件套不破坏
- [ ] 2.3 R3-4.3 G1-G11 成果回归（字号/圆角/主题联动/调试 7 页/书源编辑调试头）
- [ ] 2.4 R3-4.4 logcat 针对性计数=0+android.util.Log.d/e 残留=0
- [ ] 2.5 R3-4.5 门禁：4.1-4.4 全过+随批散项（X1 安装 L1 冒烟/X2 设置搜索走查/X3 间接宿主确认）
- [ ] 2.6 收尾 5.1 updateLog 基于 git diff 逐文件审计更新
- [ ] 2.7 收尾 5.2 registry 登记 H/D 迁移+INDEX 更新
- [ ] 2.8 收尾 5.3 stop-daemons.bat 清场
- [ ] 2.9 收尾 5.4 项目记忆+经验沉淀
- [ ] 2.10 收尾 5.5 🛑 检查点 3 用户验收
- [ ] 2.11 B10 CacheActivity 真机回归（registry 7.11ai 销项）

## 3. B1 基线校准（纯文档，成品直接粘贴自 design-b1-b2 分册 §1）

> ⚠️ **冻结标注（2026-09-01，总线 2.7.2）**：B1 基线校准已执行——pages-inventory §0/§G 校准（变更记录 v2.13）、registry §七 7.11aq~bn 24 项登记块、ui-redesign-m3/tasks.md 头部冻结标注均已落盘。基线校准后上述编号（X-01~X-22、7.11aq~bn）与校准范围**不再变更**；后续迁移状态变化一律走 migration-registry **增量登记**（7.11 系列顺延）+ pages-inventory §0 快照随回执刷新，禁止改写本批校准条目。

- [x] 3.1 pages-inventory.md §0 替换为分册 §1.1 成品总览表（55% 行口径+双口径注释）✅ 2026-09-01（总线 2.7.1；§0 整段替换+统计定稿/双口径/权威源 3 注落盘）
- [x] 3.2 pages-inventory.md §G 按分册 §1.2 校正表 X-01~X-22 逐条执行（含 6 项"维持免改"核验）✅ 2026-09-01（总线 2.7.1；X-01~X-18 条目技术标注 18 处+X-19/X-20 §G 清单归属 2 处+X-21 权威源增注+X-22 v2.13 变更记录；6 项维持免改核验通过：C1/C2/B7/D1/D4/B6 现行标注与分册一致零改动）
- [x] 3.3 ui-redesign-m3/tasks.md 头部冻结标注（分册 §1.4 成品段落）✅ 2026-09-01（总线 2.7.2；成品 4 条已插入头部标题与 §1 之间）
- [x] 3.4 migration-registry.md §七 登记块 aq~bn 24 项按分册 §1.3 粘贴（每项含证据三元组）✅ 2026-09-01（总线 2.7.2；B1 登记 16 项 aq~bf+B2 冻结回执 8 项 bg~bn 整块追加于 §六.4 之后；编号顺延核验：registry 原止于 7.11ap，aq~bn 无冲突）
- [ ] 3.5 六.3 遗留销项：BookshelfItems GeneratedCover 归位裁决（分册 §1.5 裁决成品段：方案 A 迁 ThemeSpec 取色/B 登记豁免，建议 A，随 B2 S2 验收批次实施）（注：分册 §1.3 成品登记块无该行，裁决登记随 B2 S2 批次按 §1.5 建议 A 落 registry）
- [x] 3.6 顶栏集群 4 spec 盘点吸收/注销（总线 2.7.3 增补账本项）✅ 2026-09-01——逐 spec 结论：①**my-topbar-unify**＝实施进行中（核心实现 2.1-2.5 已勾：MainTopBarView Mode.MY+MyFragment 接线；验证 §3/文档同步 §4 未勾），**保留**；②**subpage-topbar-unify**＝实施基本完成（批次 A/B/C 迁移+三批编译全过+5.1 全量回扫过；剩真机回归 2.6/3.6/4.8/5.4.2~4+TitleBar 废弃评估 5.3.1），**保留**；③**tag-mode-unify**＝实施基本完成（§1/§2/2.9 全勾+3.1 编译过；剩真机验证 3.2~3.4+清理 3.6），**保留**，实施时点排总线 3.5 后（热点④，按总线 tasks 2.7.3 原文）；④**topbar-icon-semantics-fix**＝实施基本完成（1~4 章+5.1/5.3 全勾；仅剩 5.2 真机 L2/L3 走查，1.2 排查与之合并执行），**保留**。总判定：四 spec 代码域均基本完成、均余真机验证尾巴，**无一达"吸收完毕待归档"销档线，全部保留不注销**；吸收路径＝四 spec 剩余真机验证项并入 compose B2 样板冻结检查点的真机窗口合并执行（S1 主框架检查点覆盖 my-topbar/tag-mode 顶栏形态，图标走查覆盖 topbar-icon 审计面），避免重复打包；互斥门禁维持＝B14 ExploreShow 列 compose B4-c 整页迁移名单，届时顶栏一次性收敛为 Compose、禁再独立改动 View 顶栏（subpage-topbar-unify 4.2 ↔ compose spec.md §X2）。

## 4. B2 样板冻结验收（AD-06；检查点全表=design-b1-b2 分册 §2，35 项含 S5-7）

- [x] 4.1 AppPageSpacing token 落地（分册 §3 骨架，含与 AppListSpacing 边界注）+frontend-ui-standards 写入 ✅ 2026-09-01（`AppUiTokens.kt` 追加 `AppPageSpacing` 7 字段，与分册 §3.2 骨架逐字一致、append-only 不动存量；frontend-ui-standards §1.3.1 落档含 AppListSpacing 边界注（存量仅限列表场景、禁新代码扩散）；compileAppDebugKotlin BUILD SUCCESSFUL+daemon 清场；暂无消费方——4.2+ 样板页接入）
- [x] 4.2 L2 脚本模板落地（分册 §4，logcat 采集带 -T 时间戳起点）+首批 7 脚本 ✅ 2026-09-01（复用层 `ai_tests/lib/compose_assert.py`（§4.2 函数库沉淀：connect 探针+uiautomator 残留清理/device_now→`logcat -d -T 'ts'` 起点/dump_bounds StaleObject 兜底/assert_window_single 弹框独立窗口/assert_bounds_moved/prefs_read 三态/run_steps 步骤注册表）+7 脚本 `ai_tests/scripts/l2_verify_compose_{s1_main,s2_source,s3_source_edit,s4_book_info,s5_read_float,s6_dialog_tiers,cache}.py`（检查点覆盖 S1-1/2/3/5、S2-1~8、S3-1~6、S4-1~4、S5-1~5、S6-1~4、7.11be 销项；S3 脚本标注依赖 4.3 接线）；质量=venv py_compile 8 文件全过+config 导入链冒烟 OK；落位口径总线 2.12 三层=族命名+.gitignore 白名单 7 行+SOP 表 16l~16r+README 族索引双登记；⚠️ 真机不执行归 4.4-4.7 冻结验收窗口，锚点真机校准点已逐处标注）
- [x] 4.3 C2 BookSourceEditActivity S3 接线收尾 ✅ 2026-09-01（KeyboardToolPop insets 接线 prepare()+onImeVisibilityChanged，fullScreen 窗口失效根因修复；未保存拦截/CodeView 已就位 s3-2/3 翻盘；s3-4 真机 PASS 包 090204）
- [ ] 4.4 S1 MainActivity 冻结验收+回执 **首轮实况（2026-09-01 包 090122）**：s1-1 底栏 4 tab 切换+渲染 ✅ / s1-3 压缩态证据 ✅ / s1-2 FAIL（书架数据不足 2 屏滚动位移=0，**数据依赖型**）/ s1-5 FAIL（书架配置入口锚点待 dump 校准，脚本已标注 probe_shelf.py）；FATAL 全零。**第 2 轮实况（2026-09-01 数据播种后，书架 16 本合成书）**：s1-1 ✅（"发现"tab 数据就绪后翻盘）/ s1-3 ✅ / **s1-5 ✅ 翻盘**（③校准：入口=书架顶栏 desc="菜单"→"书架布局"，弹框出现+重渲染 before=23 after=38）/ s1-2 ❌（③锚点+滚动链待校准：锚点 y<220 修正后确证列表滚动未触发——u2 d.swipe 与 shell input swipe 在脚本上下文均位移≈0，而 assert_b2_shelf.py 同方式滚动可达 15/16 本，两场景差异待复核；数据已排除）；FATAL=0。**第 3 轮实况（2026-09-02 锚点校准代理）**：s1-1 ✅ / s1-3 ✅ / s1-5 ✅ / **s1-2 ❌=③注入通道限制**（书架 LazyGrid 触摸滚动 flaky：u2 touch 序列/shell input swipe 双通道×冷启/温启/页面切换前置组合均位移=0，dbg_drag_probe scroll 对照仅偶发成功不可复现（成功 2/3、其余 0 位移）；非回归证据——人工路径 assert_b2_shelf 曾滚 15/16 本；建议挂 L3 手动清单或升级注入通道后重验）；FATAL=0
- [ ] 4.5 S2 BookSourceActivity 冻结验收（含 copy() 强跳过验收项）+回执 **第 2 轮实况（2026-09-01）**：导航已校准打通（③：订阅 tab 顶栏 Compose 语义未暴露→am start 直拉 ui.book.source.manage.BookSourceActivity；书源列表 3 合成源）但 s2-1~8 全 FAIL=③锚点校准——**多选态功能存在**（长按批量栏实证="反选/删除"，脚本断言"全选"形态不符），拖拽 hash 不变/三视图/排序/更多菜单入口锚点均待校准；FATAL=0，无真回归证据。**第 3 轮实况（2026-09-02 锚点校准代理，实锚表=脚本头注释）**：**6/7 PASS 翻盘**——s2-1 长按多选+计数增长 ✅ / s2-2 拖拽换位+重进持久化 ✅（③：sh.calvin.reorderable 3.1.0 draggableHandle=Press 检测器**按下即拖**，u2 touch down→立即 move 序列；长按静置/draganddrop 均失配——第 2 轮位移=0 根因）/ s2-3 反选计数刷新+启用所选 ✅（⚠️AdbKeyboard 工具条陷阱：菜单 dismiss 后焦点回落搜索框→IME 视图 1.5s 内盖批量栏且 dump 不可见→动作重排规避）/ s2-4 **SKIP=N/A**（三视图载体页功能不存在：AppManagementScaffold/LazyColumn 无视图形态参数，规格 ListLayoutMenu 概念未在 C1 实现）/ s2-5 排序菜单+升降序翻转首项变化 ✅（菜单实锚=排序 ActionListDialog 8 项，非 ListLayoutMenu）/ s2-6 关键字过滤 4→1+快捷词"已禁用"→0+恢复 ✅（搜索框常驻 hint"搜索书源"，筛选入口=顶栏"分组"）/ s2-7 三点菜单 5/5 ✅（**desc="更多菜单"** 非"更多选项"——第 2 轮"未暴露"实为锚点词错）/ **s2-8 FAIL=规格差异登记**（多选态 BACK 直接 finish 回桌面——BaseActivity onBackPressedDispatcher 直连 finish 无多选态消费，"先退多选"预期不符，回归候选）；FATAL=0
- [x] 4.6 S3 BookSourceEditActivity 冻结验收+回执 ✅（第 3 轮 s3 6/6：拦截/CodeView/工具条全过；差异记录=拦截确认框否/是二元无取消留页） **第 2 轮实况（2026-09-01 导航校准后）**：s3-1 ✅（6 Tab 候选=5 命中下界；Tab=基本/搜索/发现/详情/目录/正文全暴露）；s3-2~6 ❌=③锚点（字段菜单 desc="更多选项"未暴露，同 s5 族）+**4.3 接线依赖（预期部分 FAIL 登记）**；导航校准=点击列表条目直进编辑页（原"长按→编辑菜单"真机不存在，长按=多选态）；FATAL=0。**第 3 轮实况（2026-09-02 锚点校准代理，实锚表=脚本头注释）**：**5/6 PASS 翻盘**——s3-1 ✅ / **s3-2 ✅ 翻盘**（未保存拦截确认框出现=4.3 拦截接线已存在；实现=否(不保存退出)/是(保存退出)二元，无"取消留页"项——规格差异记录）/ **s3-3 ✅ 翻盘**（全屏编辑入口=顶栏 desc"编辑内容"直钮（menu_fullscreen_edit title=R.string.edit_content，showAsAction=always；"全屏编辑"词不存在），且需先聚焦 EditText（onFullEditClicked 要求 findFocus is EditText）→CodeEditActivity 命中）/ s3-4 ❌=预期 FAIL（KeyboardToolPop undo/redo/教程未现=insets 接线依赖 4.3，锚点已校准）/ s3-5 ✅ / **s3-6 ✅ 翻盘**（保存钮=desc"保存"；表单控件实锚=MultiAutoCompleteTextView 共用 resource-id（非 EditText，hint 填充 text）→清空/回填全走 u2 Accessibility set_text/clear_text 通道；拦截=toast"名称和 URL 不能为空"+留页）；导航=am start 管理页冷启→item_containers 容器点击首条目；步骤间加页面守卫（编辑页无 BACK 拦截，任意 BACK 退页）；FATAL=0
- [x] 4.7 S4 BookInfo 双栈分支各过+回执 ✅（4/4：双栈分派/新栈锚点/旧栈 book is null 回归/AppDropdownMenu） **第 2 轮实况（2026-09-01 入口校准后）**：**4/4 ALL PASS 翻盘**——s4-1 双栈命中 BookInfoComposeActivity（③校准：有进度书点击卡片直进阅读页，详情入口=长按卡片直进，无中间菜单）/ s4-2 新栈锚点 阅读/目录/简介全 True / s4-3 无 book is null 弹框 / s4-4 顶栏菜单可点击节点=13（>5）；FATAL=0
- [ ] 4.8 S5 阅读器浮层冻结验收（3s 隐藏/单一 activeSheet/BackHandler 链/手势 R0-R4/磨砂降级/S5-7 书签高亮入口）+回执 **第 2 轮实况（2026-09-01 菜单锚点校准后）**：阅读菜单呼出正常（③校准：center tap 后菜单条文本全暴露 text 3→17，三点按钮 desc="更多选项"未暴露→锚点改菜单条特征文本）；s5-1 ❌=**①真回归候选：菜单 3s 自动隐藏未生效（两轮不同数据条件复现，待修）**；s5-2/3 ❌=级联（s5-1 菜单态污染）；s5-4 ❌=②数据（章节缓存旧正文单页 1/1，R1 翻页无余量；合成正文已加长 30 段，需清章节缓存重验）+R0/R4 待复核；s5-5 ❌=③脚本（device_info API 读取=0 走降级分支断言失效）；FATAL=0、EffectRender 异常=0
- [ ] 4.9 S6 弹窗族冻结验收（L1/L2/L3 三层）+回执 **第 2 轮实况（2026-09-01 入口+按钮锚点校准后）**：**4/4 ALL PASS 翻盘**——s6-1 L1 删除确认框（③校准：入口=详情页"删除书籍"，按钮文本="否/是"非"取消/删除"；宽比例 0.958/345dp≤620cap+双按钮）✅ / s6-2 L2 书架布局弹框（入口=书架菜单"书架布局"；0.958/345dp）✅ / s6-3 L3 分组管理弹框（入口=书架菜单"分组管理"；0.960/346dp≤760cap）✅ / s6-4 弹框独立窗口不变量 isolated=True+关闭后主界面回归=True ✅；FATAL=0。**cache（7.11be 销项）3/3 ALL PASS**：入口=书架菜单"缓存/导出"（③校准，"我的"页无缓存入口——源码锚点 BaseBookshelfFragment.buildMenuActions cache_export）→CacheActivity 命中+导出/全选锚点+退出无崩溃
- [ ] 4.10 D9/VideoFragment 残余浮层核对+S5 模式回执（手势四件套复用 2.2 证据）

## 5. B3 批次（D4 旗舰专册+其余 9 页分册；设计已函数级落盘+轮 3 骨架修订）

- [ ] 5.1 D4 旗舰：按 design-b3-d4-flagship.md 实施（五代 Adapter 收敛/RssArticleListScreen 含可选 onItemLongClick/topOverlaySpacePx 状态化/ScrollRestoreEffect snapshotFlow 化/双模式分派/embeddedInModernRss 兼容层）→ 12 场景 L2+订阅切换回归+删 4 代旧 Adapter
  - [ ] 5.1.b 批 2 宿主接线（§3.4 双模式分派+§5 RssSortActivity）✅ 2026-09-02（编译门禁 compileAppDebugKotlin BUILD SUCCESSFUL+stop-daemons 清场）。**改动 11 文件（新增 2+修改 7+勘误 2）**：新 RssArticleListBridge.kt（§3.4 兼容层共享桥：rememberSaveable 三容器 Saver 进程恢复（§4-9）→ RssArticleListState 组装 → uiState/articlesFlow 收集回填 → SideEffect 暴露 holder+topOverlaySpacePx，组件无模式分支）+ 新 RssSortScreen.kt（§5.1 GlassTopAppBar 复用+八项菜单原样平移+§5.3 SortTabBar/TabPill（行数策略横屏减 1+ensureTabVisible 等价 animateScrollToItem）+HorizontalPager beyondViewportPageCount=1+§5.4 注意①页 VM viewModel(key="rss_articles_$sortName") Activity 作用域+注意③非 preload 仅当前页一次性加载（snapshotFlow.currentPage.first，禁 repeatOnLifecycle）+页码上报仅当前页防邻页覆盖）+ RssArticlesFragment.kt 瘦身（childFragmentManager 契约不变/renderCurrentSort 零改动；壳仅保留参数/VM 桥/setTopOverlaySpace（snapshotState 承载对齐 view?.post 回放）/scrollToTop 新 API/refreshAfterLogin/ReadRss/播放器返回 requestScrollToLink；嵌入态 VM 刷新圈抑制=pullRefreshing||(isRefreshing&&!embedded) 对齐原 SwipeRefreshLayout 语义，§3.4 注意②；showPagePicker/pageLiveData 菜单上报随 classic 退役删除；fullRefresh 标志消亡=Compose 无 DiffUtil 分支）+ fragment_rss_articles.xml 缩壳单 ComposeView（id recycler_view 兜底保留，B5 随兜底删除）+ RssSortActivity.kt 全 Compose（VMBaseActivity 壳保留+activity_rss_artivles.xml 缩壳单 ComposeView 宿主=§6 XML 退役顺延至基类重构批次；ViewPager/FragmentStatePagerAdapter/手搓三行标签栈/CURRENT_POSITION 手写 save-restore 全退役为 sorts snapshotState+rememberPagerState 内建 saveable；upFragments 分类解析原地平移写 state；L452"搜索"→R.string.search 既有双语 key（未新增重复 key）；翻页菜单 NumberPickerDialog 保留+pageScrollTopRequest(index,seq) 回顶通道（§3.3 翻页后回顶）；登录返回经 ViewModelProvider.get("rss_articles_$sortName") 定位当前页 VM；文章点击走 ReadRss activity 重载（页无 Fragment），列表快照经页面 state holder 上行=原 adapter.getItems 等价）+ RssArticlesViewModel（§3.1 RssArticlesUiState StateFlow+articlesFlow=flowByOriginSort.debounce(200).flowOn(IO) 经 bindOrigin 幂等绑定（不 select image，R1 红线延续）+LiveData 过渡期共存 B5 拆）+ RssSortViewModel（§5.2 articleStyleFlow：initData 读源+switchLayout onSuccess 更新，switchLayout 原逻辑保留）+ RssFragment.gotoTop 唯一改动（modern 内嵌列表走 scrollToTop() 新 API；currentRssScrollTarget 兜底代码不动，B5 随批移除）。**勘误（分册 §1.2 盘点漏项）**：RssFavoritesFragment 复用 fragment_rss_articles.xml（ViewBinding 同布局）→ 新建同构 fragment_rss_favorites.xml+改绑定，收藏列表行为零变化，其 Compose 迁移归 D7/B4；§6 删除清单补记该布局归属。**灰度口径**：五代 Adapter 文件保留未删（批 3 §6）但分派已切新组件，无 feature flag（分册未要求开关）。**扫描命中数**：Color(/.sp/RoundedCornerShape(=0；.dp=4 全登记证据（§5.3 冻结视觉规格：TabPill 12/6dp padding+行距 6dp+选中描边 1dp，无 token）；android.util.Log 残留=0。**未验证范围（Level 1 代码完成）**：真机双模式渲染/四 style 切换/翻页菜单/登录刷新/进程恢复/12 场景 L2 全未执行（批 3 L2 窗口）
  - [ ] 5.1.a 批 1 组件层（新包 ui/rss/article/compose，纯新增零侵入）✅ 2026-09-02（编译门禁 compileAppDebugKotlin BUILD SUCCESSFUL+stop-daemons 清场）。**交付 6 文件**：RssArticleListStyle.kt（§2.1 枚举 LIST/GRID_2/MASONRY/GRID_3+Int.toRssArticleListStyle+ListBottomInset）/ RssArticleListState.kt（§2.2 holder：topOverlaySpacePx/articles/pendingLink 三 mutableStateOf backing+rememberRssArticleListState 默认工厂+requestScrollToLink/Top+consumePendingLink 一次性语义）/ RssArticleListScreen.kt（§2.1 签名+ScrollRestoreEffect snapshotFlow 常驻 key=Unit+LoadMoreEffect canScrollForward 边界（MASONRY 保留 -5 阈值）+三容器装配 key/contentType+stableListKey 碰撞守卫装配前预计算（W-3 落死，groupingBy.eachCount）+PullToRefreshDefaults.Indicator offset 随 topOverlayDp（§4-5））/ ArticleItem.kt（§2.3 三形态 ListRow/GridCell/MasonryCell+combinedClickable 长按预留 D7+AppPageSpacing token 化）/ RssArticleCover.kt（§2.4 rememberRssArticleCoverUrl 单行 getImage 防 CursorWindow 2MB+hideWhenBlank 隐藏/占位+MasonryCover 宽高比预置/回写）/ RssImageAspectRatioCache.kt（三代 LruCache(399)+CacheManager 20 天 img_ar_ 前缀原样移植）/ RssArticleListPlaceholders.kt（§2.5 ListFooter/DefaultEmptyContent/ArticleListSkeleton）。**L1 复用**：EmptyStatePlaceholder（空态）+ShelfListSkeleton/ShelfGridSkeleton（骨架，W10 语义等价）——设计册 §2.5 私有 shimmer 实现按选用阶梯改 L1 复用（证据：骨架六族已提供等价封装，禁私有复制）。**设计册 3 处失实勘误（以源码实况裁决，skill 分域权威）**：①glide-compose 1.0.0-beta08 GlideImage 无 onResourceReady 参数（Maven sources jar 实证）→ 改 CustomTarget+suspendCancellableCoroutine 桥（DrawableCoverPainter nativeCanvas 绘制，size 观测后 override 解码防 SIZE_ORIGINAL）；②beta08 传递依赖 glide 5.0.5 与项目 glide 4.16.0 版本对抗（pom 实证+ktx beta08 依赖 glide5 特有字段访问）→ 本批不引入 glide-compose，零依赖变更；③R.string.empty_message/error_ 不存在 → 新增 no_more/rss_article_list_empty 双语 key，错误行复用 load_error_retry。**签名增补披露**：Screen 增可选 error: String? = null（§2.5 错误态 footer 行需通道，命名参数不破坏冻结调用形）。**扫描命中数**：Color(=0、.sp=0、RoundedCornerShape(=0；.dp=6 全登记证据（96×64 ListRow 封面视觉规格/4dp 半格×2=E5 明示保留/24dp 加载圈/90dp 主底部栏桥接=对齐 applyMainBottomBarPadding/150dp 瀑布流最小列宽），现有封装无法表达逐处列证。android.util.Log 残留=0。**未验证范围（Level 1 代码完成）**：真机渲染/五种 style 切换/双宿主接线（批 2）/进程恢复/12 场景 L2 全未执行；preload 静默加载由宿主 isRefreshing 初值控制属批 2 契约
- [ ] 5.2 A7 classic rvFind 源行列表收敛（design-b3-pages §1，7.11aj 销项）
- [ ] 5.3 A8 RssFragment modern 全 Compose+classic 收敛（§2，复用 5.1 组件+PrimaryTagRow 泛型版，订阅切换回归）
- [ ] 5.4 B2 Toc 收尾：rememberSaveable 补齐+万章性能抽查（§3）
- [ ] 5.5 B8 BookshelfManage 整页 AppManagementScaffold 化（§4；主题包裹层级按 b4-b5 §B4-4 边界 5 统一裁决）
- [ ] 5.6 B11 残余三块收敛：searchView/btnMenu/源分组标签条（§5）
- [ ] 5.7 C3 BookSourceDebug 整页迁移（§6，ERROR 短路/前缀补全逐条保留）
- [ ] 5.8 C13 壳瘦身+S6 三层核对（§7）
- [ ] 5.9 D1 收尾清理：已全量接线，死代码删除+menu 逐项核对（§8）🔁
- [ ] 5.10 E2 违例修复：15 项逐项重判（V2/V3 销号候选）+V13 ThemeSpecPresets 落点（色值豁免声明已落册）+用户裁决程序（§9）

## 6. B4 批次（三波次；分册 design-b4-b5-pages）

- [ ] 6.1 B4-a 登记核对 6 项：B7（§B4-1）/B16（§B4-3）/C17（§B4-10）/E5（§B4-12）/D8（§B4-9）/B13 主题对齐（§B4-13）🔁
- [ ] 6.2 B4-b 收口 5 项：B9 底栏裁决（§B4-2）→D3（§B4-6）→D5（§B4-7）→D7（§B4-8，经 ReadRss.readRss 上行链）→D2 压轴（§B4-5，宿主统一包裹 LegadoTheme）
- [ ] 6.3 B4-c 迁移 4 项：B5/B14/B15 列表三连（§B4-4 共用模板；⚠️ B14 ExploreShow 列入顶栏 spec X2 互斥门禁，顶栏随整页迁移一次性收敛为 Compose，禁独立改动 View 顶栏，见 spec.md §X2）+C20 About 全新迁移（§B4-11，AnnotatedString）
- [ ] 6.4 B4 特殊：B12 漫画壳层对齐 S5（§B4-13，内核零改动断言）

## 7. B5 收官（可执行清单=design-b4-b5-pages §B5）

- [ ] 7.1 A6 BooksFragment 销号确认（已删 0 引用，走 §B5-1 清单）
- [ ] 7.2 C19 巡检：豁免色 1 处确认（§B5-2）+0 私有复制组件三步巡检法（§B5-3，含白名单落盘）+D4 recycler_view id 兜底代码随批删除
- [ ] 7.3 AiComposeTheme 五维评分（§B5-4，≥7 分启动收敛 spec）+结论登记（AD-04）
- [ ] 7.4 KPI 终值复盘：严格口径公式（§B5-4，半桥接不计入分子）落 registry+pages-inventory，对 NG 代差复盘

## 8. 每批固定验证链（模板）

- [ ] 8.1 每批：`./gradlew assembleAppDebug` 编译门禁（先 Get-Process 校验无构建进程）+5.5 E2E affected_modules 调度
- [ ] 8.2 Compose L2 脚本：按分册模板 l2_verify_compose_{page}.py（uiautomator 控件断言+截图基线+su -c 整串铁律+venv 专用 Python+logcat -T 起点）；B2 首批 7+B3 9+B4 17 场景（前缀已全册统一）
- [ ] 8.3 每批收尾：registry 回执+检查点审查+daemon 清场

## 9. 设计交叉审核（≥5 轮，用户强制要求）

- [x] 轮 1 册间一致性审核（7 ERROR/6 WARN/INFO 全过）✅ → 修订闭环
- [x] 轮 2 源码符合性抽查（12 断言：10 确认/2 部分/0 驳斥）✅ → 修订闭环
- [x] 轮 3 规范符合性审核（5E/12W/6I）✅ → 修订闭环（28 条 Edit+Grep 双向校验）
- [x] 轮 4 完整性与无悬空审核（1E/4W；四方映射 59/59 闭合；悬空词扫描 5 命中全合法）✅ → 修订闭环
- [x] 轮 5 可实施性终审（修订落实复验 14 PASS/1 PARTIAL+四维度 PASS；终审裁决 **ACCEPT-WITH-NOTES**：W-1 检查点基数 35 统一/W-2 RssSourceEditScreen modifier 已落死/W-3-W-4 为实施期指引项）✅ 2026-08-30

> **设计自审结论**：5 轮交叉审核完成，ACCEPT-WITH-NOTES 放行。遗留观察项 W-3（bottomPadding 示意注释/duplicateKeyGuard 创建点）与 W-4（ThemeSpecPresets 色值占位）均为实施期落死项，册内已有指引，非阻塞。

## AOAdapt 日志

- 轮 1：初版 tasks 路线写成"另立 spec/待校准"悬空 → 用户否决 → 页级总表+批次全量落盘
- 轮 2：页级总表仍为表格级 → 用户要求函数级深度 → 4 分册产出，分册源码勘误 10 处回写总表
- 轮 3（审核轮 1-2 修订）：统计三口径统一/B4-a 归属裁决/章节引用 10 处修正/悬空任务消除/D4 组件签名增补/占比重算 55%
- 轮 4（审核轮 3-4 修订）：①d4 骨架两处运行期缺陷修复（topOverlaySpacePx 状态化/ScrollRestoreEffect snapshotFlow 化）②AppShapes.pill 不存在→Capsule（3 处）③骨架 dp 字面量 token 化+PrimaryTagRow 泛型化+根 modifier 补齐④B4-b 链路契约统一（D7 经 ReadRss）⑤b1-b2 表头 6 列+S5-7 增补+GeneratedCover 裁决成品段⑥检查点基数 33→34⑦L2 前缀统一 l2_verify_compose_⑧统计分母 59/60 拆行口径显式化
