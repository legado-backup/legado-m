# tasks.md — 管理页样式统一与交互回归修复

> 状态：🔄 设计中
> 顺序强制；验证级别 ⚠️ L1 编译 / ⚠️ L2 真机功能 / ✅ L3 场景回测

## 1. 准备工作

- [ ] 1.1 `git show 05e4dde3c` 提取 5 处注入 diff 原文（ExploreShowActivity/ExploreFragment/SearchActivity/BookshelfFragment1/BookshelfFragment2）
- [ ] 1.2 Read BookshelfScreen.kt 刷新/状态/分支结构（L130-230）与 LockableViewPager 拦截逻辑
- [ ] 1.3 Read MainTopBarView.kt L460-780（LayoutTransition/updateFilterBarsVisibility/animateFilterToggle）与 RoundedTagBarView.kt L140-210
- [ ] 1.4 Read AppSettingComponents.kt page 定义、三个全屏根层（ThemePackageManageScreen/AppPackageManageComponents/BookInfoManageScreen）、BaseActivity manageHostTintColor 现状
- [ ] 1.5 Read AppManagementScaffold 签名+BookshelfTagManage 接入范例+A 类 9 页现有顶栏/菜单/多选结构（抽样 TxtTocRule 全读）

## 2. F1 视频队列注入恢复

- [x] 2.1 按提取 diff 重放 5 处 `VideoPlaylistHolder.set` 注入（isVideo 分支内，含索引计算）
- [x] 2.2 rg 复核：5 处 set（统一 isVideo 过滤）+ 消费 neighborOf + onDestroy clear 链路完整；真机矩阵含混排分类+suite 横排入口
- [x] 2.3 验证（L1✅；L2/L3 待用户视验）：编译通过；真机 S-F1 三入口×首/中/末矩阵（L2/L3）

## 3. F2 书架手势三修

- [x] 3.1 刷新条件化（红队 R5-3 层级整改）：onRefresh lambda 内 `books.isNotEmpty() && listState.canScrollBackward` 短路（或内容层 onPostScroll 全量消费——PullToRefreshBox 外层拦截无效，二选一）
- [x] 3.2 State hoist+Saveable：两 state 提升至分支外（现 loading 时不组合）+rememberSaveable(Saver)；loading 骨架改 Box 叠加常驻；upConnect loading 仅首次置位；无 key=跨组保持为有意决策
- [x] 3.3 LockableViewPager 从零实现轴向锁定（现状仅 swipeEnabled 布尔）：onInterceptTouchEvent 记录触点，move 累计 |dx|/|dy|>1.2 才拦截
- [x] 3.4 验证（L1✅；L2/L3 待用户视验）：编译通过；真机 S-F2 三手势+斜滑+顶部刷新可用（L2/L3）

## 4. F3 发现页头部闪烁三修

- [x] 4.1 LayoutTransition 禁 APPEARING/DISAPPEARING
- [x] 4.2 animateFilterToggle 目标一致不重启（updateFilterBarsVisibility 旧值比较已存在，销项）

- [x] 4.3 验证（L1✅；L2/L3 待用户视验）：编译通过；真机 S-F3 浅色主题标签点击/切源/筛选展开（L2/L3）

## 5. F4 透明度消费模型重构

- [x] 5.1 BaseActivity.manageHostTintColor 改预混 manageBgBlendedColor（红队 R5-1：禁 alpha 叠加/同色底）+ AppConfig 新增预混 helper
- [x] 5.2 AppSettingComponents.page 改预混 blendedColor（15 处消费点全域生效；TocComposeScreen 吸顶分支随预混自然生效）
- [x] 5.3 三个全屏根层复核防叠加（page 预混后 Surface 保留、去重复 alpha 语义）
- [x] 5.4 验证（L1✅；L2/L3 待用户视验）：编译通过；真机 S-F4 四页透明度 50%/0%/100% + E-Ink 回归 + 壁纸背景图路径回归（L2/L3）

## 6. F5 子页面统一第一期

- [x] 6.1 AppManagementAction 增加 icon: ImageVector? 槽位（AppManagementScaffold.kt；红队第 3 轮⑤：iconRes 不可逆转换）
- [x] 6.2 A 类 9 页平移 AppManagementScaffold：TxtTocRule/DictRule/HighlightRule/FileManage/StorageManage/LibraryContainer/BookCharacter/Download/AiProvider（删自绘 SelectionActionBar）
- [x] 6.3 B 类：AppPackageManageComponents 共享组件统一顶栏（TopBarManage/NavigationBarManage/ShareNoteTemplate 随之）；BookInfo/Bubble/AdvancedTitle/CoverCollection/DiscoverySuite 摘 View TitleBar
- [x] 6.4 C 类 4 页（CacheManage/ParagraphRule/ReadMenuButton/ReadAloudBgm）TitleBar 基色对齐 backgroundColor
- [x] 6.5 GlassTopAppBar 族顶栏基色 backgroundColor 语义（过渡期消白带）
- [x] 6.6 验证（L1✅；L2/L3 待用户视验）：编译通过；真机 S-F5 TxtTocRule 浅色顶栏+列表同族 + A 类抽样 2 页四象限（浅/深/REGULAR 顶栏包/透明度）（L2/L3）

## 7. 综合验证与收尾

- [x] 7.1 全量回归（L1 编译✅+装机冒烟 FATAL=0；场景回归随用户视验）：VideoPlay 既有切换链/书架顶部刷新/E-Ink/壁纸背景图路径
- [x] 7.2 静态检查（随实施逐步复核）：无新增裸 colorScheme 硬编码/无临时日志残留
- [x] 7.3 updateLog 基于 git diff 更新（编译前）
- [x] 7.4 文档同步：ui-standards 架构登记（透明度内容层模型 v2/管理族统一进度）/INDEX 流转
- [x] 7.5 测试包 090321（build-legado.bat 成功） build-legado.bat + daemon 管理（按新规保留复用）
- [ ] 7.6 真机批全量 S-F1~F5（用户视验，待走查）

## AOAdapt 日志

（实施中记录）
