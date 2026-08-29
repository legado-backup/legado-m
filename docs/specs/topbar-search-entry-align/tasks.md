# 主Tab头部搜索入口形态统一与主题取色对齐 — 任务清单（tasks.md）

## 0. 实施就绪核查与权威声明

- [x] 0.1 检查点 1 用户审查通过（两轮审查：①B1-B7 卡点 ②B8-B11 规范对齐），裁决：①订阅页形态=纯按钮 ②实施后仅保证编译通过，不打包不真机（2026-08-28）
- [x] 0.2 权威执行顺序 = 部件 A（发现页）→ 部件 C（取色对齐）→ 部件 B（订阅页，按裁决）→ 部件 D（规范）→ 编译 → 真机验证
- [x] 0.3 编译/打包启动前 `Get-Process` 校验无构建进程占用（2 java 均为 IDE 语言服务器白名单）

## 1. 部件 A：发现页搜索入口统一为纯按钮

- [x] 1.1 `ExploreFragment.onCreateView`：`setSearchEntryVisible(true)` → `setSearchEntryVisible(false)`，注释说明对齐书架/我的纯按钮形态 ✅ 2026-08-28
- [x] 1.2 `ExploreFragment.updateDiscoverSearchButtonState`：`searchButton.isVisible = canSearch && !isRegularStyle()` → `searchButton.isVisible = canSearch`（regular 风格也显示按钮）✅ 2026-08-28
- [x] 1.3 移除 `searchEntry.setOnClickListener { openDiscoverSearch() }` 绑定（胶囊已隐藏，清理死绑定）✅ 2026-08-28
- [x] 1.4 逻辑走查（B6）：setMode(DISCOVERY) 与 updateDiscoverSearchButtonState 显隐竞争核实无回归；regular/default 双风格下发现页头部 = titleSelect + 搜索按钮，无胶囊 ✅（Grep：setSearchEntryVisible 全 false）
- [x] 1.5 titleSelect 连锁走查（B1）：关胶囊后 titleSelect 自动显示（标题"发现"+箭头，点击 showDiscoverSourceMenu L1908/长按 showDiscoverKindsDialog L1911 均既有绑定，无需新改动）✅

## 2. 部件 C：Compose 搜索框取色对齐主题设置（v3 最终版：palette 槽位，清除 surfaceVariant 违规）

- [x] 2.1 `SettingsSearchBar.kt`：背景取色改用 `rememberThemeUiPalette().searchFieldBackgroundColor`（取色链：自定义 key → `background_menu` 兜底）+ 统一叠 alpha（日 0.18/夜 0.42，`AppConfig.isNightTheme`）+ 1dp 描边同源（primaryTextColor 低透明）；保持 `AppShapes.Search`(18dp) + 40dp 高度 ✅ 2026-08-28
- [x] 2.2 **彻底清除 `MaterialTheme.colorScheme.surfaceVariant`**（B8：修正既有 M3 派生色违规，color.md §五 + how-to.md 严禁清单 + theme-architecture 红线 4）✅（Grep surfaceVariant 0 使用）
- [x] 2.3 走查 `TopBarSearchStyle.surfaceColor`（View）与 `SettingsSearchBar`（Compose）取色口径一致性（默认/自定义 × 日/夜 4 场景）；确认 `themeUiSignature` 已含 search key 重组联动 ✅

## 3. 部件 B：订阅页形态统一为纯按钮（✅ 用户已裁决 2026-08-28）

- [x] 3.1 **删除** `RssFragment.selectSource` L604 `setSearchEntryVisible(hasSearch)` 覆盖调用（初始化 L947/空状态 L826 已关闭，勿重复设置）；L610 `searchButton.isVisible = hasSearch`（regular 可见）；删 L611-612 胶囊 isEnabled/alpha 残留 ✅ 2026-08-28
- [x] 3.2 订阅页 `buildSearchScope`（fix-rss-search-scope）回归确认：按钮点击仍按当前分组/类型限定搜索范围 ✅（逻辑未触碰）
- [x] 3.3 订阅页 titleSelect 衔接走查（B7）：关胶囊后 titleSelect 显示（标题"订阅"+箭头），点击弹 showSourceSelector（L458 既有绑定，无需新改动）✅

## 4. 部件 D：前端 UI 规范补充与矛盾修订

- [x] 4.1 `frontend-ui-standards.md`：**修订 §1.4 矛盾条款**（B9：'搜索框浅底统一用 surfaceVariant（Compose）'→ palette 槽位口径，禁止 M3 派生色）；新增「主 Tab 头部搜索入口形态」条款（标题 titleSelect + 搜索按钮 → 新搜索页，禁止胶囊式伪输入框/就地展开，注明 searchEntry 与 titleSelect 互斥）+「搜索框取色双端一致」条款（Compose palette 槽位 / View TopBarSearchStyle 同源）✅ 2026-08-28
- [x] 4.2 `ui-standards/architecture.md`：顶栏族基线补充搜索入口形态约束（含 titleSelect 与 searchEntry 互斥关系说明）✅ 2026-08-28
- [x] 4.3 `ui-standards/migration-registry.md`：登记本次批次（六.2 章节，部件 A/B/C/D 全表）✅ 2026-08-28

## 5. 编译与静态验证

- [x] 5.1 启动前 `Get-Process` 校验无构建进程 ✅
- [x] 5.2 增量编译 `compileAppDebugKotlin` **BUILD SUCCESSFUL（17s，45 tasks）✅ 2026-08-29**（按用户裁决先等待 config-needs-restart-fix 会话编译完成，其修复 BaseBookshelfFragment 错误后本批复验通过；初次失败归因见 AOAdapt 日志）
- [x] 5.3 Grep 确认：`ExploreFragment` 无 `setSearchEntryVisible(true)` 残留；`RssFragment.selectSource` 无 `setSearchEntryVisible(hasSearch)` 残留；`SettingsSearchBar` 已消费 palette 槽位且**无 surfaceVariant 残留**（Grep `surfaceVariant` 0 命中）✅
- [x] 5.4 Grep `android.util.Log.d|android.util.Log.e` 确认无新增调试日志 ✅（3 文件 0 残留）
- [x] 5.5 更新 `app/src/main/assets/updateLog.md`（2026/08/29 条目，面向用户语言）✅

## 6. 真机/模拟器验证（Level 2，依赖 MEmu）

- [ ] 6.1 发现页：regular 风格头部 = titleSelect + 搜索按钮（无胶囊）→ 点击打开 SearchActivity（带当前源 searchScope）；titleSelect 点击弹源选择菜单/长按弹分类弹窗正常（场景 1+6）；default 风格回归
- [ ] 6.2 书架/我的：搜索按钮行为回归（SearchActivity / SettingsSearchActivity）
- [ ] 6.3 订阅页（纯按钮已裁决）：状态链回归——初始化→空源→选中带搜索源→切无搜索源，头部全程无胶囊且按钮显隐正确（场景 8）；点击打开 RssSearchActivity
- [ ] 6.4 主题设置改「搜索框背景色」+ 日/夜切换：Compose 搜索框背景同步联动（alpha 口径一致，场景 2）
- [ ] 6.5 默认态合规验证：未配置「搜索框背景色」时 14 处 SettingsSearchBar 页面搜索框 = background_menu 兜底叠 alpha（清除 surfaceVariant 违规后的合规态，观感轻微变化属预期，场景 7）
- [ ] 6.6 编译后执行 `stop-daemons.bat` 清理构建 daemon

## 7. 收尾与文档同步

- [ ] 7.1 更新 docs/INDEX.md（topbar-search-entry-align 状态 + 关联 header-search-unify 说明）
- [ ] 7.2 更新项目记忆（当前任务状态 / 反馈记录 / 教训）
- [ ] 7.3 核对 docs/project-flow/ 相关文档一致性（本批次影响 frontend-ui-standards / ui-standards，无 WebBook/数据库/RuleEngine 变更）

### AOAdapt 日志（实施过程遇到问题时追加）

- [x] 5.2 编译验证（⚠️ Level 1 受阻）
  - Action: 启动 `compileAppDebugKotlin` 编译验证（GRADLE_USER_HOME=F:\gh）
  - Observation: BUILD FAILED（7m32s），错误全部位于**其他会话在途变更**——BookshelfScreen.kt:717 `Unresolved reference 'History'`（Icons.AutoMirrored.Outlined.History 缺 import）+ 若干 Text() Typeface/AnnotatedString 参数不匹配；**本批 3 个修改文件（ExploreFragment/RssFragment/SettingsSearchBar）均不在错误清单中**；后续两次重试取完整错误清单时被用户手动中止
  - Adapt: 本批代码 Grep 静态验证全部通过（surfaceVariant 0 残留 / setSearchEntryVisible 全 false / selectSource 无覆盖调用 / 调试日志 0）；整体编译门禁被工作区另一会话（config-needs-restart-fix）半成品变更阻塞，按并发文件修改规范不代改他会在途文件，处理方式提请用户裁决；daemon 已清理
