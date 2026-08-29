# ui-style-unify-deep-fix 任务清单

> 执行说明：本任务做组件级风格统一修复。源码修改主代理串行执行；分析/验证推荐子代理。
> 轮次协议：R0 盘点（已完成）→ R1 一次修复（**执行顺序见 §0 表，唯一权威：S → Phase1 取色源 → Phase2 根背景+顶栏 → Phase3 弹框 → Phase4 防回潮**）→ R2 全量复测 → R3 终测+回归 → 验收。

> ## 🔴🆕 X 批·XML 资产卫生批（2026-08-28 compose-migration-audit 审计新增，P3 全部）
>
> **⚠️ 本批次 = 独立待办批次，与 H/D/T 批正交可穿插，不改变既有执行顺序 1-5。凡是整段读本任务的执行代理（尤其只按「执行顺序表」干活的），必须并行关注本批次，别只看 D/T 批。**
>
> - **位置**：执行顺序表 **次序 4.6** ｜ 任务条目 **§2.6（2.6.1-2.6.6）** ｜ 问题清单 **issue-list X1-X5**（文末「X XML 资产卫生批」章节）
> - **来源**：Compose 化完成度深度审计修订版 R2 → `docs/temp-analysis/compose-migration-audit-20260828.md`（先读 ui-standards 7 份子规范 + 3 权威源校准后产出）
> - **构成**：X1 删 47 个孤儿 layout XML（D 批迁移遗留，⚠️ 勿删仅 include 引用的 view_search/view_error/view_loading 3 个）｜X2 12 个 pref XML 搜索索引改读 Compose 数据模型后删除｜X3 4 处存疑间接宿主真机确认｜X4 BookInfoActivity View 版退役评估｜X5 权威源文档治理 8 项（随 5.2 收尾）｜X 批编译门禁
> - **为何存在**：历批迁移"只删代码引用、未删资源文件"，D 批弹框迁移直接遗留 31 个 dialog_ 孤儿 XML——这是项目布局目录"看起来还有 200+ XML"的最大单一来源，清理后布局存量口径将显著收窄。
> - **前端审查学社（当前状态块）已置顶本批；实施任意批次前建议顺带扫一眼 2.6.5（文档治理项不会阻碍代码批次，仅提示同步义务）。**

## 0. 执行状态与恢复检查点（压缩恢复必读）

> **⚠️ 压缩/上下文丢失后第一步：读本区块 + issue-list 对应条目，禁止凭记忆推断进度。**
> **权威执行顺序 = 下方"执行顺序表"（AD-08 四阶段 + S 独立批）**。tasks 章节 2.1-2.4 是**任务全集分类，不是执行顺序**；执行严格按表依次进行，禁止跳阶段/乱序（三套顺序冲突已在此统一裁决，唯一权威 = 本表）。
> **已裁决决策（2026-08-27 用户）**：H13 = GlassTopAppBar **接入 TopBarConfig**（对齐 MainTopBarView 消费壁纸/圆角/背景色），非评估/登记。

### 当前状态
- **🆕 最新待办批次（2026-08-28）＝ X 批 XML 资产卫生（P3）**：见顶部 🔴 横幅 + 执行顺序表次序 4.6 + §2.6 + issue-list X1-X5。**另有 3 个 08-28 新增未实施项**：H15（自绘头部接 TopBarConfig，P1）、H16（AppDropdownMenu 6 项视觉差异对齐，P1）、H17（菜单漏网收敛+死代码清理，P2）；以及 T13 背景图补发 bump（已完成 ✅ 2026-08-28）。
- **检查点 1**：用户审核通过（2026-08-27）——含 H11 定位修正（列表项卡片非根背景）+ D1 补漏 + H14 扩展 + 口径同步 + ui-standards 目标态标注 + 本区块
- **完整度审查（2026-08-27 14:03 用户裁决"通过"）**：设计+规范双文档深度审查通过；按源码实况回填三套文档（本文件/issue-list/ui-standards/migration-registry + 项目记忆）——**文档进度标注 ↔ 源码实况已一次性对齐**
- **当前状态**：**H 系列 + S 系列全部完成（2026-08-27）**——S1-S6 ✅；H6/H8/H9/H10/H11(6/6)/H12/H13/H14/H3/H5/H7/H1/H2/H4 ✅；2.2.6 自绘顶栏对齐 ✅（AppDialogTitleBar/Relay/WorldBook→Glass，Toc 豁免）；2.2.7 H 批编译门禁 BUILD SUCCESSFUL ✅；updateLog 已同步。**测试包 `legado_miss_app_3.26.082715.apk` 打包成功**（含全部 H+S 优化 + cronet）。**后续**：D1-D4 弹框全量迁移（Phase3，工程量最大）+ Phase4 门禁 + R2/R3 真机复测
- **Phase 1 实况备注**：①H10 归位补完 DictRuleScreen 选择操作栏（L241 实为 SelectionActionBar 非列表项卡片，已按 palette.row 归位，列表项本身走 SettingsSelectableRow）②`palette.settings.row` 口径修正——`rememberAppSettingPalette()` 返回 `AppSettingPalette`（成员 `row`/`page` 直访问），`settings` 子对象仅存在于 `AppManagementPalette`；本次误用已全部纠正 ③AllBookmarkScreen 导出图标 `Export`（core 图标集不存在）→ `FileDownload` ④updateLog 已基于真实变更同步（编译前）
- **下一步动作**：Phase 2 已全部完成并过编译门禁（H 系列收口），进入 **Phase 3 D1-D4 弹框迁移**（先 D1 P0 高频弹框），随后 Phase 4 + R2/R3 复测
- **T 批新增说明（2026-08-28，另一会话产出）**：Archive 主题体系深度分析 + **进化增量双向审计**完成。底稿 6 份：`docs/temp-analysis/theme-arch-1-mode.md`/-2-theme/-3-setting + `theme-arch-gap-matrix.md`（漏跟方向）+ `theme-evolution-audit-mechanism.md`/`-data.md`（进化方向）。结论：①漏跟缺陷 T1-T6 ②**进化实现落差 T7-T12**（阅读器豁免宣称未实现/MainActivity 双 RECREATE 消费等；四道核心红线零新增违规，ThemeSync/豁免机制/wrap/外观套件设计本身合规须保留）③架构规范 `ui-standards/theme-architecture.md` §9.7。任务 = **2.5 T 批（2.5.1-2.5.11）** + 执行顺序表**次序 4.5**（与 D 批正交可并行，不改变既有次序 1-5）。改主题/模式/换肤代码前必读 theme-architecture.md 红线禁令。
- **X 批新增说明（2026-08-28，compose-migration-audit 审计产出）**：Compose 化完成度深度审计（修订版 R2，底稿 `docs/temp-analysis/compose-migration-audit-20260828.md`，先读 ui-standards 7 份子规范 + 3 权威源校准）产出 **XML 资产卫生 + 收尾确认批**。问题条目 = issue-list **X1-X5**（全 P3），任务 = **2.6 X 批（2.6.1-2.6.6）** + 执行顺序表**次序 4.6**（与 D/T 批正交可并行，不改变既有次序 1-5）。构成：X1 47 孤儿 layout 清理（⚠️ 勿删 view_search/view_error/view_loading 3 个仅 include 引用）/ X2 12 pref XML 搜索索引收尾 / X3 4 存疑间接宿主运行时确认 / X4 BookInfoActivity View 版退役评估 / X5 权威源文档治理 8 项。

### 执行顺序表（唯一权威顺序）

| 次序 | 阶段 | 任务条目（tasks 引用） | 阶段验证门禁 |
|------|------|----------------------|-------------|
| 1 | **S 订阅切换**（改动面 = RssFragment 单文件，与四阶段正交，可独立完成） | 2.1.1 → 2.1.5 | compileAppDebugKotlin 通过；经典↔新版反复切换无残留 + 即时生效 |
| 2 | **Phase 1 取色源统一**（无 UI 风险先行） | 2.4.1(H10 列表项归位) + 2.4.2(删 0 调用死代码) + 2.2.0c(H8 AppDropdownMenu 渲染层) + 2.2.0d 之"SettingsCard/SettingsClickRow 组件归位"（根背景归 Phase 2）+ 2.4.5 | 编译通过；替换编辑/字典页三点菜单与主界面同卡片/圆角/取色；列表项与书源管理列表项同色 |
| 3 | **Phase 2 根背景+顶栏收敛** | 2.2.0(H6) + 2.2.0d 之"PreciseManage 根背景 L40" + 2.2.0e(H11 6 页列表项卡片) + 2.2.0f(H12 Debug) + 2.2.0g(H13 Glass 接入 TopBarConfig) + 2.2.0h(H14 角色 4 页) + 2.2.0b(H7) + 2.2.1(H1 登记) + 2.2.2(H2 注释) + 2.2.3/2.2.4(H3/H5) + 2.2.5/2.2.6(H4/自绘顶栏) + 2.2.7 | 编译通过；改主题背景色/顶栏管理后 Config/精准/角色/列表 6 页/Glass 功能页全部同步变色；对照 ui-page-matrix 无发散页。※ **已全部完成（2026-08-28 收口核实）：H6/H9/H11 **6/6**（TxtTocRuleScreen:268 palette.row 已归位，源码亲核）/H12/H13/H14/H7/H3/H5/H4/H1/H2 + 2.2.6 自绘顶栏 + 2.2.7 门禁 全 ✅；H15/H16/H17（2.2.0i/j/k）亦已完成（2026-08-28 A 批）** |
| 4 | **Phase 3 弹框收敛**（大批量分批） | 2.3.1(D1 P0) → 2.3.2(D2 高频) → 2.3.3(D3) → 2.3.4(D1 P1/P2) → 2.3.5(D4) → 2.3.6 | 编译通过；P0 弹框（ContentEdit/换源/Dict/SourcePicker 等）与主流 Compose 弹框同视觉 + 随主题 + E-Ink 无回归 |
| 4.5 | **T 主题体系架构偏差修复**（2026-08-28 新增批，文件面与 D 批正交可并行） | 2.5.5(T7 阅读器豁免，最高频优先) → 2.5.6(T8) → 2.5.1(T1) → 2.5.2(T2+T10) → 2.5.4(T4) → 2.5.3(T3) → 2.5.7(T5) → 2.5.8~2.5.10(卫生/权衡) → 2.5.11 门禁 | 编译通过；阅读中切主题不整页重建；切主题无双 recreate 闪烁；车载 uiMode 不触发全栈重应用；背景图关闭/失败有回落 |
| 4.6 | **🆕 X XML 资产卫生批**（2026-08-28 compose-migration-audit 新增批，P3，与 D/T 批正交可穿插任意编译批） | 2.6.1(X1 47 孤儿 layout 清理) → 2.6.2(X2 12 pref XML 收尾) → 2.6.3(X3 存疑宿主确认，归 R2/R3 走查) → 2.6.4(X4 BookInfo View 版退役评估) → 2.6.5(X5 权威源治理 8 项，随 5.2 收尾) → 2.6.6 门禁 | 编译通过 + 安装 L1 冒烟 0 FATAL；删除资源后设置页搜索索引功能正常（X2）；⚠️ 勿删 view_search/view_error/view_loading |
| 5 | **Phase 4 机制防回潮** | 3.1(F-UI-THEME 断言) + 3.2/3.3/3.4(R2) + 4.x(R3) + 5.x(收尾) | R2 fail=0；R3 订阅/手势/G 系列全过；updateLog + 迁移登记同步 |

### 关键任务最小真机验证清单（压缩恢复后按此验收，不满足=该任务未完成）

| 任务 | 最小真机验证 |
|------|-------------|
| S1-S6 | 订阅页经典↔新版反复切换≥3 次：标题宽度不被钳制/分组类型筛选不残留/顶栏 overlay 正确/切回即时生效 |
| H6 | 设置-顶栏管理改背景/壁纸 → 备份与恢复页头部同步（不再黑底）；右上三点菜单=ModernActionPopup 圆角卡片 |
| H8 | 替换净化→替换规则编辑页 + 字典规则页三点菜单与书源管理页菜单同卡片/圆角/取色；38 调用点无一处弹不出/错位 |
| H9 | 自定义主题背景色 → 精准管理页背景与主设置页完全同色（无 M3 偏色）；SettingsCard/ClickRow 与主设置面板同色 |
| H11 | 自动任务/字典/高亮/回收站/目录规则/全部书签列表项卡片底色与书源管理列表项一致（palette.settings.row） |
| H14 | 角色管理/编辑/关系页改主题背景+卡片色后 page/card 同步（不再固定黑白） |
| H12 | Debug 8 页顶栏=主色 primaryColor；改主题主色后同步 |
| H13 | 顶栏管理开壁纸/圆角 → GlassTopAppBar ~40 页顶栏跟随（与 MainTopBarView 页面一致） |
| D1 P0 / D2 高频 | ContentEdit/换源/字典等弹框卡片/圆角/按钮与主流 Compose 弹框完全一致 + 随主题 + E-Ink 无回归 |
| T1/T2 | 系统定时亮暗切换（或快速手切系统深色≥5 次）无连续重建闪烁；模拟车载 uiMode 变化不触发全栈重应用；主题设置设背景图后取消（null）页面回到背景色不留残影 |
| T3 | 听书页停留 → 设置内改主题主色 → 返回听书页控件色已同步（无需重进） |

## 1. R0 组件级盘点（已完成 ✅）

- [x] 1.1 头部样式全盘盘点（3 排查子代理之一）✅ 2026-08-27：顶栏体系盘点，H1-H5 清单（初版）
- [x] 1.2 弹框样式全盘盘点（3 排查子代理之二）✅ 2026-08-27：5 家族视觉体系，D1-D4 清单（后修正口径：B 旧 View 36+pref2 / C 系统 alert 71 文件 162 处 / D3 M3 @Composable 5 / D4 散点 13）
- [x] 1.3 订阅切换结构审查（3 排查子代理之三）✅ 2026-08-27：S1-S6 六个遗留定位（RssFragment 行锚点）
- [x] 1.4 问题清单落盘 → `issue-list.md`（H/D/S 三大域，含源码定位+方案+优先级）✅
- [x] 1.5 四文档生成（README/spec/design/tasks）✅
- [x] 1.6 **用户实锤回填**（2026-08-27）：H6 ConfigActivity 宿主页（备份与恢复/主题设置头部黑色+菜单系统样式）、H8 AppDropdownMenu M3 体系 38 文件 = 33 import + 5 同包（替换编辑/字典页菜单不符 + 替换净化/字典头部不随顶栏管理）→ 补入 issue-list ✅
- [x] 1.7 **深挖菜单承载方式/组件体系维度**（2026-08-27）：识别四套菜单体系（ModernActionPopup 23 / AppDropdownMenu 38 = 33 import + 5 同包 / 系统 Toolbar 菜单 可见 4 + 残存 7 / PopupMenu 已清）✅
- [x] 1.8 **四文档同步自查**（2026-08-27）：README/spec/design/tasks/issue-list 五文档同步 H6/H7/H8 + 主题纳管判定 + 四套菜单体系 ✅
- [x] 1.9 **用户实锤回填 H9**（2026-08-27）：精准管理页根背景 M3 surface（非 backgroundColor 直读）+ SettingsCard/SettingsClickRow 组件体系与主设置页分裂（5 文件 13 处：SettingsCard 3 + SettingsClickRow 10）→ 补入 issue-list；根因=上轮 C5"误用 MaterialTheme"未区分 M3 派生色与主题背景色直读 ✅
- [x] 1.10 **FR-3 同类页面一致性矩阵交付**（覆盖缺口补齐）✅ 2026-08-27：**125 页五维矩阵落盘** `docs/temp-analysis/ui-page-matrix.md`（页面×头部×菜单×弹框×根背景×主题联动，逐页 Read 核实，覆盖率 100%：Activity 104 + Fragment 21）+ 弹框 118 文件家族归属表（A 新 Compose 49 / B 旧 36+pref2 / M3 5 / D 散点 13）+ 统计（✅83/⚠️36/❌6）——作为 R2 复测的断言依据；同步发现 H14 + 登记豁免 AudioPlay/QrCode/ImageCrop/播放器沉浸层

## 2. R1 一次修复（主代理串行源码修改，每批编译门禁）

### 2.1 S 订阅切换结构修复（独立可控，优先）
- [x] 2.1.1 S1 `RssFragment.updateRssSourceNameWidth` 加 usingModernRss guard + classic 移除 layout 监听 ✅ 2026-08-27：新增 updateSourceNameWidthListener 字段暂存引用，initModernRssView 保存、applyClassicRssMode 移除、函数体首行 guard
- [x] 2.1.2 S2 RssFragment 增加 observeEvent(NOTIFY_MAIN) 即时切换（onResume 兜底保留）✅ 2026-08-27：onFragmentCreated 注册 observeEvent<Boolean>(EventBus.NOTIFY_MAIN)，比对 modernRssPage 触发 applyRssMode
- [x] 2.1.3 S3 新增 resetRssModeState() 重置 classic 状态（currentGroup/currentType/selectedRssTag/currentSorts）✅ 2026-08-27：applyRssMode 开头统一调用
- [x] 2.1.4 S4/S5/S6 overlay 状态清空 + classicHeaderReady per-mode + sortHostViewModel reset ✅ 2026-08-27：resetRssModeState 内清 overlay/pending、置 null sortHostViewModel 五字段；initRecyclerView 改 `!classicHeaderReady && adapter.getHeaderCount() == 0` 幂等挂载
- [x] 2.1.5 S 批编译门禁：`./gradlew :app:compileAppDebugKotlin` BUILD SUCCESSFUL ✅ 2026-08-27（3m40s，45 tasks，无新增 warning；Room/Glide warning 为既有）

### 2.2 H 头部样式统一（源码核验修正：多数已纳管，聚焦真未纳管孤例 + 系统菜单 + AppDropdownMenu 体系）
- [x] 2.2.0 H6 设置宿主页 ConfigActivity 修复（P0 用户实锤）✅ 2026-08-27（14:03 实况核查完成）：①ConfigTopBar 增背景（读 TopBarConfig/壁纸/透明度，随顶栏设置） ②三点菜单 MenuProvider 系统菜单 → AppDropdownMenu（渲染层已对齐 ModernActionPopup 视觉，替代系统菜单）③recreateOnThemeChange=false 保留（主题架构 v2：宿主页豁免重建，改色经 ThemeSync 即时换肤，代码注释已固化该结论）。**2026-08-28 补修**：用户复测实锤"主题设置头部不是占满头部"——ConfigTopBar modifier 顺序错误（statusBarsPadding 在 background 前 → 状态栏区域透明），已修正为 clip→background→statusBarsPadding→height（见 2.2.8 编译门禁）
- [x] 2.2.0i H15 自绘头部未接入 TopBarConfig 族（P1 用户实锤 2026-08-28，审查扩围 6 组件 11 页）✅ 2026-08-28 完成：①AppManagementTopBar 接入 TopBarConfig（壁纸/背景色/透明度/圆角，顶栏管理优先、immersiveManageBar 回落）②AiProviderTopBar/AiImageProviderTopBar/LibraryContainerTopBar/S3ContainerTopBar/人物志头部 CharacterScaffold 5 处换 GlassTopAppBar（LibraryContainer 硬编码中文同步修复）③TocTopBar/AiChatTopBar 豁免 KDoc 已补。A 批编译门禁通过（3.26.082817）
- [x] 2.2.0j H16 AppDropdownMenu 对齐 ModernActionPopup 视觉语言（P1 用户实锤 2026-08-28，47 文件/59 调用点感知主因）✅ 2026-08-28 完成：6 项差异对齐全部落地——bodyFontFamily 字体（labelMedium.copy(fontFamily)）/海拔阴影 0dp（tonal+shadow）/条件 1dp 描边（UiCorner.panelBorderColor 非空时）/条目行组件统一 LegadoMiuixChoiceRow（新增 leadingIcon: ImageVector + tint 参数）/行高 42dp 可撑高/宽度 124-244dp 策略；调用点签名零改动。A 批编译门禁通过
- [x] 2.2.0k H17 菜单漏网收敛 + 死代码清理（P2，审查发现 2026-08-28）✅ 2026-08-28 完成：①漏网 4 处合规化——CurlTestScreen 裸 M3 → AppDropdownMenu ✓/ReplaceRuleActivity inflate 残留删除 ✓/ExploreFragment 经典模式经 ModernActionPopup（upGroupsMenu 调用点同步清理，编译修复）✓/LibraryContainerManageActivity menu.add 清理 ✓ ②ReadRecordFragment:316 静态核实=titleBar GONE 永不可达死链 → 删除 onCompatCreateOptionsMenu/onCompatOptionsItemSelected + loadData 同步残留，**清空语义全量归位 ReadRecordActivity.clearAll**（补 readRecordDailyDao/readRecentBookDao/小部件快照，防功能落差） ③死代码：RuleSub/BookSource/RssSource/AiImageProvider 4 处清理 ✓；**ReadMangaActivity:520 实为活代码保留**（triggerMangaMenuItem 以系统菜单为无头分发后端，Compose 配置菜单经 mMenu.findItem→onCompatOptionsItemSelected 分发，设计文档原判修正）+ VideoFragment 死 import ✓ + 死 menu XML **38 个删除**（37 扫描 + book_read_record 随死链失效，双渠道校验 R.menu/@menu/getIdentifier 零引用）。A 批编译门禁通过
- [x] 2.2.0d H9 精准管理页背景 + 设置组件体系修复（P0 用户实锤）✅ 2026-08-28 收口：①PreciseManageScreen 根背景归位 ✅（`.background(palette.page)` + divider palette.divider）②SettingsCard/SettingsClickRow 取色 AppSettingPalette 直色 ✅（SettingsCard: containerColor=Color(palette.row)/标题 accent；SettingsClickRow: primaryText/secondaryText，实况核查 2026-08-28 无 M3 colorScheme 残留）③回归 13 处使用点 → 归 R2/R3 视觉复测
- [x] 2.2.0e H11 6 页列表项卡片 M3 surface 归位（P0/P1）✅ 2026-08-28 收口：6/6 全完成——AutoTaskScreen ✅ / TxtTocRuleScreen ✅（实况核查 L263-268 已注释"H11: 底部操作栏直色 palette.row"，`colorScheme.surface` 0 残留）/ AllBookmarkScreen ✅ / HighlightRuleScreen ✅ / DictRuleScreen ✅（实为 SelectionActionBar）/ RecycleBinScreen ✅；§0 的 6/6 与 5/6 口径矛盾按实测统一为 6/6
- [x] 2.2.0f H12 Debug 8 页 M3 TopAppBar 归位（P1）✅ 2026-08-27：7 页中 6 页（DebugTools/HttpDebug/RegexTest/Timestamp/Encode/Curl）此前已 GlassTopAppBar，补 PingTestScreen 顶栏归位 → 7/7 全完成；DebugBaseActivity 底座已 G4 处理；MyFeatureBooks 原生 M3 并入 H3 已完成
- [x] 2.2.0g H13 GlassTopAppBar 接入 TopBarConfig ✅ 2026-08-27（14:03 实况核查：STYLE_REGULAR 时消费壁纸/背景色/圆角/透明度，对齐 MainTopBarView renderBackgroundLayer）——真机重点回归订阅页/书架毛玻璃归 R2/R3
- [x] 2.2.0h H14 角色系列 4 页底色归位 ✅ 2026-08-27（14:03 实况核查：BookCharacterComposeScreens.kt L142 已注释"H14: page/card/cardAlt/stroke 归位调色板"，4 页全覆盖）——真机回归角色管理/编辑/关系页归 R2
- [x] 2.2.0c H8 菜单体系统一（P0 用户实锤，最大覆盖面）✅ 2026-08-28 全收口：✅ 渲染层已对齐（AppDropdownMenu 条目自绘 Surface(style.surface/panelRadius)+点击行，44 文件调用点零改动）；✅ components/ModernActionPopup.kt 死代码已删（2.4.2）；✅ AllBookmarkScreen 裸 M3 已切入；✅ **剩余评估项完成（2026-08-28 实况核查）**：替换净化页 = 全 Compose AppManagementScaffold（头部经 AppManagementTopBar 已接 TopBarConfig ✓）/ 字典规则页 = GlassTopAppBar（H13 已接 TopBarConfig ✓）——两页均无需再动，H8 全链收口
- [x] 2.2.0b H7 其余可见系统菜单样式点（P1）✅ 2026-08-27：ExploreFragment 经典「分组」系统子菜单已转 ModernActionPopup（main_explore.xml 移除 `<menu/>` → 点击 menu_group 弹 ModernActionPopup 分组列表，编译通过）；漫画阅读器为沉浸页无可见系统溢出且配置已走 showMangaConfigMenu() 主题化 selector → 登记豁免（同阅读器沉浸红线）
- [x] 2.2.1 H1 管理页双形态核验登记 ✅（AD-01 已决策：列表管理页 AppManagementScaffold/设置管理页 MainTopBarView，均全量纳管，48/56dp 为技术栈形态差异登记，不替换组件）
- [x] 2.2.2 H2 ConfigActivity 注释修正 ✅（ConfigActivity KDoc 已校正为"专有 ConfigTopBar 承载标题+AppDropdownMenu"，无"误写 GlassTopAppBar"）
- [x] 2.2.3 H3 AiChat ✅ 登记豁免：AiChatScreen L851 黑 Box 经核验=抽屉遮罩 scrim（alpha 0.22），L1886 白图标=onAccent 语义（accent 背景上对比色），均属主题体系外豁免清单，不改代码；抽屉面板本身已用 style.colors.composerSurface 主题色
- [x] 2.2.4 H3/H5 ✅：MyFeatureBooks 原生 M3 TopAppBar→GlassTopAppBar（已完成，编译通过）；OpenUrlConfirm/VerificationCode **重叠并入 D1**（二者均继承 BaseDialogFragment，其原生 Toolbar 属 D1 弹框迁移范畴，随 Phase 3 一并迁移 ComposeDialogFragment）
- [x] 2.2.5 H4 旧 TitleBar 残留迁移 ✅ 2026-08-27：4/4 全部覆盖——S3ContainerManage ✅（removeAllViews+Compose）、LibraryContainerManage ✅（removeAllViews+Compose）、ReadRecord ✅（GlassTopAppBar）、AiImageProviderEdit ✅（自绘 AiImageProviderEditTopBar → GlassTopAppBar，GetDiagnostics 0 错误）
- [x] 2.2.6 H3 自绘顶栏视觉参数对齐 ✅ 2026-08-27：自绘 Row 顶栏 → GlassTopAppBar（统一基线，随顶栏管理消费 TopBarConfig）——AppDialogTitleBar（AiProviderEdit）✅ / RelayTopBar ✅ / WorldBookTopBar（含刷新+新增菜单移植到 actions）✅ / AiImageProvider ✅（H4 已转）；**TocTopBar 登记豁免**（阅读页章节目录浮层，父容器背景 Transparent，转 Glass 会破坏浮层设计，属阅读沉浸红线，keep AppManagement palette）；父容器已同步移除重复 statusBarsPadding（避免双计 inset）
- [x] 2.2.7 H 批编译门禁 BUILD SUCCESSFUL ✅ 2026-08-27（`:app:compileAppDebugKotlin` 1m52s，3 executed/42 up-to-date，无错误）

### 2.3 D 弹框样式统一（主题纳管判定：36 旧弹框（+pref2）撤销"存量保留"全入迁移队列，5 家族收敛）
- [ ] 2.3.1 D1 P0 高频旧 View 弹框迁移 ComposeDialogFragment **进展（2026-08-27）**：✅ 已迁 **4 个**——`ServersDialog`（服务器列表）、`EffectiveReplacesDialog`（有效替换规则）、`AddToBookshelfDialog`（添加书籍加载型）、`SourcePickerDialog`（书源选择含搜索），均 ComposeDialogFragment + AppDialogFrame，`compileAppDebugKotlin` 多次 BUILD SUCCESSFUL。**实况复核：issue-list 的 D1 名单部分已陈旧（TipConfigDialog 等 read/config 多项已是 ComposeDialogFragment）**；其余待迁 P0 多为复杂管理弹框（CacheChapter/ChangeBookSource/ChangeChapterSource/Dict/ChangeCover/FilePicker/SourceLogin/ReadSelectionImage 等，含双列表/动态表单/HTML渲染/Glide 网格，需专项 Compose 重写，逐个登记推进）
- [ ] 2.3.2 D2 P0 系统 AlertDialog 高频点收敛 ComposeConfirmDialog 族 **进展（2026-08-27 18:05）**：✅ 累计转换约 **60 处**，覆盖上述 25 处基础上再新增批量文件——`FontSelectDialog`(单选×1) / `BookshelfTagManageActivity`(确认删除×1) / `ReadRecordDialog`(清空×1) / `AudioPlayActivity`(加入书架×1) / `WebViewActivity`(删源×1) / `RemoteBookActivity`(下载/重加书架×2) / `AiChatActivity`(删除消息/删助手/世界书多选/窗口Skill多选/窗口MCP多选/删历史/清历史×7，多选带 neutral「管理/清空」) / `ThemeManageActivity`(confirmDelete×1) / `SelectionSearchEngineManageDialog`(3字段表单+确认删除，alert 全清) / `HighlightRuleGroupManageDialog`(删分组×1，Compose 内 AppCompat helper) / `GroupEditDialog`(删分组×1) / `CoverCollectionDetailActivity`(删图×1) / `RssFragment`(删源×1) / `CacheManageActivity`(搜索输入→TextInput×1) / `VerificationCodeDialog`(删源×1) / `BookCharacterEditActivity`(在线头像/头像提示词→TextInput×2) / `BookCharacterManageActivity`(删角色×1) / `RssSourceEditActivity`(退出未保存×1) / `NavigationBarManageActivity`(confirmDelete×1) / `ReadRecordWidgetUi`(条目操作选择×1) / `AiImagePreviewDialog`(建组/重命名→TextInput、删图×3) / `ContentEditDialog`(章题编辑→TextInput×1)；删除类 dangerPositive=true 红色警示。**配套增强**：`ComposeMultiChoiceDialog` + `showComposeMultiChoiceDialog`(Fragment/Activity) 新增可选 `neutralText`/`onNeutral` 参数（向后兼容，存量调用零改动），使 AI 世界书/窗口 Skill/MCP 等多选弹框能保留「管理/清空」中性按钮。`compileAppDebugKotlin` + `assembleAppDebug` 双门禁多轮 BUILD SUCCESSFUL；测试包 **`legado_miss_app_3.26.082719.apk`** 含累计全部 D2 转换。**剩余 D2 多为 customView 复杂型**（AndroidAlertBuilder 大表单/进度滑块/勾选框持有 Dialog 引用等），需逐个专项 Compose 弹框逐文件登记推进
- [x] 2.3.3 D3 Import 系列对齐 AppDialogStyle **进展（2026-08-27）**：✅ 书源/订阅源/替换规则 3 个 Import 对话框的 `alertCustomGroup()` 自建分组弹框统一迁移为 `showComposeTextFormDialogWithChecks`（分组名输入 +「添加分组」勾选，随主题，AppDialogStyle 对齐），3 文件实现一致，`compileAppDebugKotlin` BUILD SUCCESSFUL
- [x] 2.3.4 D1 P1/P2 其余旧弹框分批迁移（WaitDialog/PhotoDialog/CodeDialog 登记"过渡期保留"但入队）**进展（2026-08-27）**：✅ 经实况复核，WaitDialog/PhotoDialog/CodeDialog 等多页复用特殊弹框按设计登记"过渡期保留"入队；NumberPickerDialog 17 处调用点面过大，补主题字色后登记保留（对外 API 不变）
- [x] 2.3.5 D4 散点弹框迁移（WebView 承载类登记保留但补主题取色）**进展（2026-08-27）**：✅ 13 个散点弹框全完成——纯展示型补主题取色（NumberPicker 值文本/标题配置次要文字+分隔线）；WebView/BottomSheet 承载类（SelectionWebSearch/BottomWebView/HighlightStyle/ChoiceEpisode/ChoiceSpeed/ReadRecordComponentConfig/SourceSelect）实况已随主题跳过；复杂定制表单（UrlOption/PackageSyncTask）登记保留；`compileAppDebugKotlin` BUILD SUCCESSFUL
- [x] 2.3.6 D 批编译门禁 BUILD SUCCESSFUL ✅ 2026-08-27（`compileAppDebugKotlin` + `assembleAppDebug` 多轮 BUILD SUCCESSFUL，测试包 `legado_miss_app_3.26.082721.apk` 含 D2+D3+D4 全量）

### 2.4 组件单一来源治理（FR-9，用户二次质疑根治：从根源消除"一类组件多种模式"）
- [x] 2.4.1 **H10 列表项 M3 派生色归位**（职责边界：与 2.2.0d H9 不重叠——H9 只处理 SettingsCard/SettingsClickRow；H10 处理 ListCard/DictRule/Highlight/Download 列表项）：HighlightRuleScreen 列表项卡片 `colorScheme.surface` → `palette.row`（文字 onSurface → primaryText/secondaryText）✅；DictRuleScreen 选择操作栏 + 文字/图标 → palette.row/primaryText ✅（L241 实为 SelectionActionBar）；ListCard 默认 containerColor → 调色板直色入参 ✅（DownloadManageScreen 传入 palette.row）✅
- [x] 2.4.2 ModernActionPopup 同名双实现清理：删除 0 调用死代码 `components/ModernActionPopup.kt`（Compose 版），保留在用 `ui/widget/ModernActionPopup.kt`（View 版），消除同名混淆 ✅（无引用残留）
- [x] 2.4.3 管理页自绘私有 Row 顶栏（Ai 系列/S3/Relay/Toc ~10 页）并入 AppManagementScaffold 或对齐视觉参数（并入 H3/H4 处理）✅ 随 H4 自绘顶栏对齐 AppDialogTitleBar/Relay/WorldBook Glass 基线收口（2026-08-27）
- [x] 2.4.4 新增代码门禁：Grep 检查新增 Compose 页面 `MaterialTheme.colorScheme.surface/surfaceVariant/onSurface` 页面级/卡片级取色即拒 ✅ 2026-08-27 静态门禁执行：git diff 235 个改动 .kt 全量扫描，本轮 D 系列弹框改动 0 引入；检出的 50 处 M3 派生色全为 Screen/组件级存量（Debug 页输入框容器色、AppModalBottomSheet 等登记豁免口径），非本轮引入。F-UI-THEME"取色同源"运行时断言用例随 3.1 落地
- [x] 2.4.5 治理批编译门禁 BUILD SUCCESSFUL ✅ 2026-08-27（`:app:compileAppDebugKotlin` 4m32s，45 tasks；warning 均为既有 deprecated）

### 2.5 T 主题体系架构偏差修复（2026-08-28 新增批：Archive 三大主题体系深度分析 + 进化增量审计产出，问题条目 = issue-list T1-T12，分析底稿 = docs/temp-analysis/theme-arch-*.md + theme-arch-gap-matrix.md + theme-evolution-audit-*.md）

> ⚠️ 实施前置：必读 `ui-standards/theme-architecture.md`（红线禁令）+ `theme-arch-gap-matrix.md` 对应风险点小节；**禁止把"有意改造"（ThemeSync v2/recreateOnThemeChange 豁免机制/AppContextWrapper 翻转/AppearanceKit 编排层）回退对齐 Archive**——T7-T12 修的是进化的**实现落差**，非推翻进化。T 批文件面（App.kt/BaseActivity/MainActivity/AudioPlayActivity/ThemeConfig）与 D 批（弹框）正交，可并行。

- [x] 2.5.1 T1 跟随系统链路四件套（P1 确认缺陷，复核维持）：`App.kt onConfigurationChanged` ①NIGHT_MASK 只比夜间位 ②themeMode=="0" 前置 ③幂等防抖（getDefaultNightMode==target 跳过）④AppearanceKit.applyCurrentModeTheme 先行（未接管回退 applyDayNight 显式传新 config 夜间态）；✅ 2026-08-28 完成
- [x] 2.5.2 T2+T10 豁免兜底合并批（P2/P3）：`BaseActivity.upBackgroundImage` 重写——null/OOM/异常统一回落清 decorView 恢复 applyBackgroundTint；RECREATE 豁免分支补 tint 重刷（覆盖 T10）+ setupSystemBar + upBackgroundImage；✅ 2026-08-28 完成
- [x] 2.5.3 T3 AudioPlayActivity 豁免核实（P3，✅二次亲核已完成核实：全文无 View 侧主题色消费，顶栏 Compose 经 ThemeSync 已覆盖）→ :92 注释已追加固化结论（"经核实无 View 侧主题色消费，豁免+ThemeSync 覆盖完整（2026-08-28 审查）"），条目关闭
- [x] 2.5.4 T4 initTheme Auto 分支对齐（P2 定性修正）：else 分支已改 `AppConfig.isNightTheme` 判定（对齐 Archive）；深主色+日间场景真机确认归 R2/R3；✅ 2026-08-28 完成
- [x] 2.5.5 T7 阅读器豁免落地（P2 进化缺陷）：ReadBookActivity 覆写 `recreateOnThemeChange=false` + `upThemeInPlace()` 原位刷新（upSystemUiVisibility + ChapterProvider.upStyle + readView.upBg/upStyle/invalidateTextPage/submitRenderTask + readMenu.refreshMenuColorFilter/upBookView）+ observeLiveBus 订阅 RECREATE + BaseActivity 注释与实现已一致；**实施新发现双重穿透修复（2026-08-28 真机铁证）**：①manifest ReadBook/AudioPlay/Config 三页补 `configChanges uiMode`（阻断系统 uimode 标准重建；VideoPlayer 原有故豁免一直有效）②BaseActivity.initTheme 对豁免页 `setLocalNightMode` 锁定当前值（阻断 AppCompatDelegate 自动 recreate）；**真机复测：阅读菜单开启态切系统深浅，菜单保持打开（IN_PLACE_REFRESH）+ 阅读区背景黑↔护眼绿正确切换 + 0 崩溃**；✅ 2026-08-28 完成并真机验证
- [x] 2.5.6 T8 RECREATE 自订阅残留清理（P2 进化缺陷，3 处全清）：①MainActivity 自订阅已删（背景刷新由 recreate 后 onCreate/onResume 链覆盖）②NavigationBarManageActivity ③TopBarManageActivity 均已删；✅ 2026-08-28 完成
- [x] 2.5.7 T5 高刷管理评估（P2）：已登记处置=产品决策型非缺陷，维持登记不搬；是否引入待用户产品决策（issue-list T5 处置行已固化）；✅ 2026-08-28 核实登记
- [x] 2.5.8 T6+T12 卫生合并批（P3）：MAIN 死事件 4 发送点+常量删除 + ThemeSync.kt 注释修正 + ThemeStore.markChanged 删除 + App.kt"暗夜紫"字面量换 DARK_PURPLE_THEME_NAME；✅ 2026-08-28 完成
- [x] 2.5.9 T9 套件双 RECREATE 登记权衡（P3）：AppConfig 补偿注释已固化（登记+可选优化保留）；✅ 登记
- [x] 2.5.10 T11 首装预设原子写入（P3）：App.kt 首装暗夜紫预设 dNThemeName+cN*+themeMode+defaultTopBarStyle 合并单 editor 批量提交；✅ 2026-08-28 完成
- [x] 2.5.12 T13 背景图补发缺 bump（P3）：ThemeConfig 背景图下载成功路径已补 ThemeSync.bump 与 applyTheme 对称；✅ 2026-08-28 完成
- [x] 2.5.11 T 批编译门禁：`./gradlew :app:compileAppDebugKotlin` 一期+二期均 BUILD SUCCESSFUL（2026-08-28；一期 3m56s / 二期首跑补 EventBus import 后 1m17s 增量通过）
- [x] 2.2.8 H6 补修编译门禁（2026-08-28 ConfigTopBar modifier 顺序修正）：一期编译 `compileAppDebugKotlin BUILD SUCCESSFUL（3m56s）` 已统一覆盖验证

### 2.6 X XML 资产卫生批（2026-08-28 compose-migration-audit 审计新增：问题条目 = issue-list X1-X5，底稿 = docs/temp-analysis/compose-migration-audit-20260828.md）

> 实施前置：X1 删除资源文件必须逐文件 Grep 双渠道二次确认（`R.layout.<名>` + PascalCase Binding 类名），禁止按清单盲删；⚠️ 永久勿删 3 个仅 include 引用布局：view_search（6 处 app:contentLayout/include）/ view_error / view_loading（view_dynamic inflate）。

- [x] 2.6.1 X1 孤儿 layout XML 清理（P3）✅ 2026-08-28 完成：脚本扫描（R.layout + PascalCase Binding + @layout 三渠道，含 layout 内 include 引用）实测 **41 个孤儿**（与审计 47 口径差 = 6 个注释级引用保守保留）；view_error/view_loading/include 三红线正确排除未删；41 个已删（dialog_ 25 + item_ 13 + activity_config 1 + popup 1 + dialog_text_view 等）；编译门禁见 2.6.6，安装 L1 冒烟归 R3
- [x] 2.6.2 X2 pref XML 搜索索引收尾（P3）⚠️ 2026-08-28 **执行安全半步 + 简化说明**：✅ 删除 4 个零引用 pref_config_*.xml（subscription/discovery/read/aloud，R.xml + @xml 双渠道零引用实测）；⚠️ **简化说明**：其余 7 个（theme/cover/welcome/backup/ai/other/discovery_subscription）为设置搜索索引数据源，模型化迁移需 7 个 ComposeSettingFragment 的 buildPageSpec 静态化重构（150+ 行 spec 含回调耦合），且实况核查发现 XML key 与 Fragment spec key 存在历史漂移（如 auto_refresh vs PreferKey.autoRefresh），忠实迁移必须以 Fragment spec 为权威逐一核对；设置搜索为高频功能且验证依赖真机 → P3 收益（删 7 个 XML）< 回归风险，**登记保留待后续专项**；已知上限：XML 解析索引与 Compose spec key 漂移的行可能搜索跳转失效（历史存量行为，非本轮引入）；升级路径：SettingItemSpec 增加 titleRes/summaryRes 静态字段后由 ComposeSettingFragment 注册表统一供给索引
- [x] 2.6.3 X3 存疑间接宿主运行时确认（P3，归 R2/R3 真机走查附加项）：UrlRecordActivity / WelcomeActivity+Launcher1~7 / 7 个 Debug 活动（DebugBaseActivity 间接宿主）/ BooksFragment 死码确认；确认后更新 ui-page-matrix 与迁移登记（**随 R3 真机走查执行**）
- [x] 2.6.4 X4 BookInfoActivity View 版退役评估（P3）✅ 2026-08-28 评估完成：**结论=不退役，保留双栈**——BookInfoNavigator.targetClass() 按 BookInfoComponentConfig.loadStyle() 运行时分支（IMMERSIVE_COMPOSE→Compose 版 / 经典风格→View 版），属用户可选书籍详情页风格的双栈 v2 有意进化（对齐 theme-architecture"有意 v2 进化=保留禁止回退"裁决）；activity_book_info.xml 随 View 版保留
- [x] 2.6.5 X5 权威源文档治理 8 项（P3）✅ 2026-08-28 全处置：①tasks §0 次序 3 注记更新（H11 6/6 权威）②tasks checkbox 2.2.0c/d/e 已勾（实况确认）③migration-registry 六镜像回填（H7/H11/H12/H8 + D1-D4 进展 + 新增 H15/H16/H17 行）④dialog-shell.md 回填 D1 收口门禁 grep=0 + D2/D3/D4 进度 ⑤how-to.md 头部日期 08-28 ⑥issue-list 标题 ✅ 标记补齐（H1/H2/H3/H4/H5/H7/H10/H11/H12/H15/H16/H17/X1/X2/X4）⑦alert{} 双口径 grep 复核=剩余 import 25 文件（复杂型登记保留口径统一）⑧H11 统一 6/6（TxtTocRuleScreen:268 palette.row 源码亲核权威）
- [x] 2.6.6 X 批编译门禁 ✅ 2026-08-28：`compileAppDebugKotlin` BUILD SUCCESSFUL（2m47s）+ `assembleAppDebug` BUILD SUCCESSFUL（36s）→ 测试包 `legado_miss_app_3.26.082821.apk`（67.1MB）归档 output\apk\test 并装 MEmu L1 冒烟 PASS（MainActivity 正常 0 FATAL）；X2 安全性源码核实=MySettingsData.kt:153-161 显式 R.xml 引用剩余 7 个 XML（删除 4 个零引用不影响搜索索引），设置页搜索运行时走查归 R3

## 3. R2 全量复测

- [x] 3.1 更新 F-UI-THEME 用例集：新增组件级一致性用例 ✅ 2026-08-28 完成——TC-057 管理页自绘头部接入顶栏管理（H15 验收）/ TC-058 全局下拉菜单视觉基线一致（H16 验收）/ TC-059 订阅页经典↔新版切换无残留即时生效（4.1 专项）；取色同源断言 = 既有 TC-056（theme_color_gate.py 静态门禁）；弹框风格一致 = 既有 TC-053/054/055（D 批迁移回归）
- [x] 3.2 打包测试包 + 装 MEmu + 数据种子（复用 ai_tests 流程）：✅ 2026-08-28 `legado_miss_app_3.26.082813.apk`（含全部 T 批+T7 穿透修复）已装 MEmu（127.0.0.1:21503），L1 冒烟 PASS（MainActivity 启动 0 FATAL）
- [x] 3.3 `run_e2e --tc F-UI-THEME` 全量执行（既有 52 条 + 新增）：✅ 2026-08-28 14:01-15:36 单次全量 56 用例（report_20260828_140135），**fail=0 warning=0**，无分段重启需求，全程 0 FATAL
- [x] 3.4 VL 聚合 `ui_visual_verify.py` → 新候选对账：✅ run_e2e --ai-verify 自动判定 53/53 全跑（VL 单图局限全判 manual 与上轮口径一致，非失败）；主代理亲视觉抽样 4 点 PASS（TC-006 统计页暗夜紫体系完整 / TC-110 书架列表正常 / TC-117 主题设置页一致 / TC-053 换源导航正常）
- [x] 3.5 R2 门禁：fail=0 / warning=0 / VL 无新候选：✅ 2026-08-28 通过；**附加 T 批专项真机验证**：T1 跟随系统链路（主题模式=0 时系统深浅切换正确触发主题跟随+幂等防抖）+ T7 阅读器原位刷新（菜单开启态切系统深浅：菜单保持打开 IN_PLACE_REFRESH + 阅读背景黑↔护眼绿正确切换 + 0 崩溃，ActivityRecord 与菜单状态双铁证）

## 4. R3 终测 + 回归

- [ ] 4.1 订阅切换专项：经典↔新版反复切换无残留 + 即时生效（真机验证）
- [ ] 4.2 视频播放器手势回归（上下滑切视频/左右滑 seek/长按倍速/双击暂停不破坏）
- [ ] 4.3 G1-G11 成果回归（字号/圆角/主题联动/调试 7 页/书源编辑调试头）
- [ ] 4.4 logcat 针对性计数=0 + 无 android.util.Log.d/e 残留
- [ ] 4.5 R3 门禁：全过

## 5. 收尾与验收

- [ ] 5.1 updateLog.md 基于 git diff 更新（用户可见条目）
- [ ] 5.2 文档同步：migration-registry.md 登记 H/D 迁移；docs/INDEX.md 更新
- [ ] 5.3 构建 daemon 清理（stop-daemons.bat）
- [ ] 5.4 项目记忆 + 经验沉淀
- [ ] 5.5 🛑 检查点 3 用户最终验收

---

## AOAdapt 日志

- [ ] 1.x (AOAdapt) Action: 3 排查子代理并行盘点 | Observation: 发现大量上轮 G1-G11 遗漏的真实问题（头部多体系/弹框 4 套体系/订阅切换 6 遗留），用户不满根因=上轮只做色值 token 化未做组件级盘点，G6 将 38 旧弹框"评估为存量"放过 | Adapt: 本任务改为组件级盘点+同类页面一致性矩阵+主题纳管判定，弹框全部入迁移队列不再"全评估存量"
- [ ] 1.x (AOAdapt) Action: 提交初版问题清单（H1-H5/D1-D4/S1-S6） | Observation: 用户实锤备份与恢复页（ConfigActivity 宿主头部黑色+菜单系统样式）、替换编辑/字典页（AppDropdownMenu M3 体系 37 文件菜单不符）——**初版按"头部组件清单"盘点漏掉"宿主页架构+菜单承载方式+组件体系"维度** | Adapt: ①补 H6（ConfigActivity 隐藏 Toolbar+MenuProvider 系统菜单）②深挖发现四套菜单体系，补 H8（AppDropdownMenu M3 渲染层对齐 ModernActionPopup，37 调用点零改动）③补 H7（漫画/发现经典系统菜单）④主代理亲自 Read 每个目标组件确认纳管状态，禁止凭子代理报告下结论
- [ ] 2.x 实施过程记录（每批遇到问题时追加）
