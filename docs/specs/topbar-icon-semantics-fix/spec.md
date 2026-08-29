# 顶栏一级图标语义修复与死按钮防线（topbar-icon-semantics-fix）

> 状态：🔄 开发中（主代理全面审查通过，按 tasks.md 串行实施）
> 前置分析：已基于源码逐点核实（ConfigActivity / BackupConfigFragment / AppManagementScaffold / GlassTopAppBar / ui-standards 规范目录 / archive-ref 原版参照）

---

## 1. Intent（意图）

恢复顶栏一级功能图标语义（问号帮助等），建立死按钮防线，补齐规范四层面（门禁/严禁/迁移登记/审计）。

具体目标：

1. **恢复回归**：备份恢复页等页面顶部原本应有的一级功能图标（如问号帮助）被 ConfigTopBar 统一下拉方案吞掉，需恢复"一级图标直达 + 其余进溢出"的原版语义。
2. **建立死按钮防线**：静态排查虽未发现确认死按钮，但存在 2 处结构性隐患（onClick 默认空实现、onNavClick 漏传静默消失），需从编译期约束 + 规范门禁 + 真机走查三个层面建立防线。
3. **补齐规范**：ui-standards 体系缺失"图标功能有效性 / 图标语义保留 / actions 分级标准"三条款，防止同类回归再次发生。

### 背景结论（已核实源码，直接采信）

- **回归铁证**：
  - `ConfigActivity.kt:180-268` 的 ConfigTopBar 只渲染「返回键 + 单一 MoreVert + AppDropdownMenu」，无一级图标 actions 能力；
  - `BackupConfigFragment.kt:130-146` 上报 Help（`Icons.AutoMirrored.Filled.Help`）+ Log 两个 MenuAction，`showHelp("webDavHelp")` 链路完整（含首次自动弹帮助 `LocalConfig.backupHelpVersionIsLast`）。即数据侧上报了问号图标，但渲染侧被折叠进 MoreVert 溢出菜单，一级图标语义丢失。
- **原版参照（archive-ref/legado-08172114）**：
  - menu XML `showAsAction` 分级策略——核心动作 `always` 1-3 个（保存/代码编辑/调试），其余 `never` 进溢出；
  - `showHelp(fileName)` 扩展函数读 `assets/web/help/md/{fileName}.md` 弹 `TextDialog(MD)`；
  - 活跃菜单零死按钮。
- **死按钮静态排查结论**：全项目 onClick 接线完整，无确认死按钮；隐患 2 处：
  - `AppManagementScaffold.kt:53`：`AppManagementAction.onClick` 默认 `{}`（漏传即静默死图标）；
  - `GlassTopAppBar.kt:138`：漏传 `onNavClick` 时返回键静默消失。
  - **疑似机制（待真机验证）**：ConfigActivity 单 Activity 多 Fragment 共享 `menuActions` 状态，Fragment 切换可能残留上一页菜单（点击弹出错误菜单/无响应）。
- **规范缺口**：`docs/project-flow/ui-standards/`（architecture.md §四门禁、how-to.md §八严禁清单）均无"图标功能有效性 / 图标语义保留 / actions 分级标准"条款；`MenuAction` 数据类（AppMenuSheet.kt:32-39，6 字段 icon/title/tint/checked/header/onClick）无 alwaysShow 概念。

---

## 2. Scope（范围）

### In scope（纳入范围，二次全量普查后完整范围）

**修复原则（总纲，逐页处置唯一基准）**：对齐 Archive 原版 showAsAction 语义——原 `always` → 恢复一级图标；原 `never` → 保持下拉溢出；D 类重构页与有意进化项除外；判定型页面（ifRoom/动态）逐项裁决并登记。

> 普查结论：B 类"一级图标被收拢"共 **18 页/25 项**（原版 59 个 menu 文件 / 87 个 `showAsAction="always"` 项逐页对照），远超首轮识别的 3-4 处。

1. **MenuAction 数据模型扩展**：增加 `alwaysShow: Boolean = false` 字段（默认值保证向后兼容）。
2. **ConfigTopBar 分级渲染**：
   - `alwaysShow = true` 的动作 → 一级 IconButton 直接渲染（用 icon + onClick）；
   - 其余动作 → 保持现有 MoreVert 下拉（AppDropdownMenu）；
   - 当存在 alwaysShow 动作且无普通动作时，不渲染空 MoreVert。
3. **B 类收拢恢复（18 页/25 项）——按组件体系四层实施**：
   - **① ConfigTopBar 系**（组件层一次改造，多页受益）：备份恢复页 Help、主题设置页 DarkMode（ThemeConfigFragment.kt:32-39）；
   - **② GlassTopAppBar 系**（组件 actions 槽已支持，逐页直写一级 IconButton）：订阅源编辑（代码/保存/调试）、替换编辑（代码/保存）、缓存页分组、WebDav 书仓刷新/排序、本地导入选目录/排序、txt_toc/dict 管理新增、收藏夹分组；
   - **③ MainTopBarView 系**（View 体系改 Mode 布局或回调）：我的 tab 帮助（moreButton 点击直接 `showHelp("appHelp")`，语义不符非死按钮，MyFragment.kt:120）、订阅 tab 历史/分组/设置（RssFragment:950-962）；
   - **④ View TitleBar 系**（TitleBar 加一级图标按钮）：书源编辑（moreButton 弹 ModernActionPopup(R.menu.source_edit)，代码/保存/调试在弹窗内——用户已裁决恢复一级）；
   - **判定型页面（批E 逐项裁决）**：书籍信息页 6 项 ifRoom、视频浮窗、发现 tab modern 形态分组、换源弹窗筛选——按对照表逐项裁决并登记，判定"修复"者实施。
4. **C 类疑似彻底丢失 3 项——真机复核闭环**：封面更换页启停（change_cover.xml 已死）、正文全屏编辑（dialog_text.xml 已死）、主题剪贴板导入（语义消失）——逐项真机复核，实锤则修复，证伪则关闭并记录结论。
5. **ConfigActivity Fragment 切换 menuActions 残留排查与修复**：真机验证疑似机制，实锤则修复（菜单随页面正确刷新，无残留）。
6. **ui-standards 规范补齐（原三条款扩展为四层面）**：
   - **门禁**：行为语义保留审查（门禁 checklist 置顶，防重犯机制）；
   - **严禁**：静默收拢 + 空 onClick + 占位图标；
   - **迁移登记**：migration-registry.md 增加"原 showAsAction 处置"必填列；
   - **审计维度**：visual-audit 增加"图标行为走查"；
   - 原三条款内容（图标功能有效性 → architecture.md §四门禁 + how-to.md §八严禁清单；图标语义保留迁移条款；actions 分级标准对齐 always/never 策略）并入上述四层面落盘；门禁条款含"禁止硬编码图标 tint"（新增一级图标按组件系接入取色权威源，见 R10）。

### Out of scope（明确排除）

1. **H16 AppDropdownMenu 视觉 6 项差异**（tasks 2.2.0j 已有任务承接，不重复立项）；
2. **31 死 menu XML 清理**（H17 已有任务承接）；
3. **阅读页豁免区顶栏**（不在本修复范围）；
4. **A 类正常 18 页**（阅读/漫画 View menu 保留、管理列表页 topActions 显式列出等）：普查确认无回归，不做改动；
5. **D 类重构页 5 页**（分组管理 / ServersDialog / TocSearchField / SpeakEngineDialog / ReadRecordDialog）：重构后功能完整，非 showAsAction 语义回归，不回退；
6. **有意进化项**：原版语义已被有意替代且功能完整的页面，不回退原样；
7. **判定型低优先项**：换源弹窗筛选等 ifRoom/动态项，按对照表登记处置结论即闭环，低优先/维持现状项不强制在本 spec 内实现修复。

---

## 3. Approach（方案）

### Selected Approach（选定方案）

**数据驱动分级 + 语义对齐分层修复**——扩展现有 `MenuAction` 增加 `alwaysShow` 字段，`ConfigTopBar` 依据字段分流渲染；修复原则**对齐 Archive 原版 showAsAction 语义**（原 always→恢复一级图标、原 never→保持下拉、D 类重构页与有意进化除外、判定型逐项裁决登记）；按组件体系**四层分层修复**（① ConfigTopBar 系分级渲染 / ② GlassTopAppBar 系 actions 槽直写 / ③ MainTopBarView 系 Mode 布局或回调 / ④ View TitleBar 系加一级图标按钮）；规范补齐从三条款扩展为**四层面**（门禁/严禁/迁移登记/审计），与"**编译期必填 onClick + 规范门禁 + 真机走查**"共同构成防线。

**理由**：

1. 复用 H6 `setConfigMenuActions` 上报机制，零架构变更；
2. 对齐 Archive 原版分级策略（always/never 语义等价映射为 alwaysShow 布尔分级）；
3. 最小改动面：数据模型 +1 字段、渲染层一处分流、上报方仅备份恢复页一处标记；
4. showAsAction 对照为 18 页逐页处置提供唯一客观基准，避免主观裁定与漏修；
5. 四组件系分层使改动收敛在各自组件体系内，页面级改动最小化、可逐层验证。

### Alternatives Considered（备选方案）

| 方案 | 否决理由 |
|------|----------|
| A. 每页手写独立 actions，放弃 ConfigTopBar 统一下拉 | 割裂 H6 统一成果、7+ Fragment 重复代码 |
| B. 仅补规范不修回归 | 用户实锤现象不修，违反需求完整性 |
| C. 新建 TopBarActionsRow 组件 | 组件族已三基线 + 菜单族，再造轮子 |
| D. 回退原版 View menuInflater 体系 | 与 Compose 化方向相反，how-to.md §八已禁止 |
| E. 仅修用户实锤 3 处，其余 15 页不修 | 二次全量普查已实锤同型回归共 18 页/25 项，仅修 3 处违反需求完整性；二次审查明确要求全量处置 |

### Drawbacks（代价与风险）

1. **MenuAction 字段膨胀**：+1 布尔字段，可接受；
2. **一级图标增多顶栏视觉密度上升**：用准入标准（≤2-3 个）控制；
3. **用户感知死按钮静态无法定位**：需真机专项走查（列入任务）；
4. **Fragment 残留假设未证实**：需真机验证，排查后可能为空结论（接受该风险，验证本身即任务产出）。

### Prior Art（先例参照）

1. **Archive 原版 showAsAction 分级策略**：核心动作 always 1-3 个、其余 never 进溢出的成熟分级模型；
2. **GlassTopAppBar actions 槽自由组装模式**：actions 槽位已支持自由组装，分级渲染在其上叠加即可；
3. **tasks 2.2.6 WorldBookTopBar 移植个案**：顶栏能力移植的既有流程参照。

---

## 4. Requirements（需求）

| 编号 | 需求描述 |
|------|----------|
| R1 | ConfigTopBar 支持一级图标渲染（alwaysShow 动作以 IconButton 直出），且保持现有 MoreVert 下拉功能不回归 |
| R2 | 备份恢复页问号图标恢复至一级，点击弹帮助（webDavHelp 链路完整可用） |
| R3 | MenuAction 向后兼容（alwaysShow 默认 false，现有调用零修改即可编译） |
| R4 | 规范三条款落盘（architecture.md §四 + how-to.md §八 + 分级标准），且与代码实现一致 |
| R5 | 死按钮防线：onClick 必填确认（编译期约束）+ GlassTopAppBar onNavClick 警示注释 |
| R6 | Fragment 切换菜单残留排查（真机验证；实锤则修复为随页面正确刷新） |
| R7 | 编译通过 + 真机 L2 走查通过 |
| R8 | 修复原则合规：每一页处置均与 Archive 原版 showAsAction 对照（原 always→恢复一级、原 never→保持下拉、判定型逐项裁决），处置结论登记成表可查 |
| R9 | C 类 3 项（封面更换页启停 / 正文全屏编辑 / 主题剪贴板导入）真机复核闭环：实锤则修复，证伪则关闭并记录结论 |
| R10 | 全部新增一级图标按组件系接入取色权威源（View 系=updateIconColors 清单 / GlassTopAppBar 系=actionIconContentColor 禁自传 tint / ConfigTopBar 系=contrastOn(bgColor) / View TitleBar 系=titleTextColor），零硬编码 tint；换肤 + 夜间切换后图标颜色正确 |

---

## 5. Scenarios（场景）

| 编号 | 场景 | 预期结果 |
|------|------|----------|
| S1 | 用户打开备份恢复页 | 右上角直接见问号图标，点击弹帮助（webDavHelp） |
| S2 | 用户打开无自定义动作的设置页 | 顶栏无 MoreVert，也无空白异常 |
| S3 | 用户在设置宿主页切换 Fragment | 顶栏菜单随页面正确刷新，无残留 |
| S4 | 开发者新增页面漏传 onClick | 编译期报错（必填参数），无法静默产生死图标 |
| S5 | 用户进入"我的" tab | 右上角显示问号图标而非竖点，点击弹出 appHelp 帮助 |
| S6 | 判定型页面（ifRoom/动态，如换源弹窗筛选、书籍信息页）处置 | 每页按对照表逐项裁决，处置结论在登记表中可查（含维持现状项） |
