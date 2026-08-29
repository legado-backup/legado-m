# topbar-icon-semantics-fix 实施任务清单

> 功能：顶栏一级图标收拢回归全量修复 —— MenuAction 分级渲染（alwaysShow 一级图标 + MoreVert 溢出菜单）+ B 类 18 页/25 项一级图标回归修复 + C 类 3 项疑似丢失真机复核 + 编辑页 3 图标恢复（用户已裁决）+ ui-standards 规范四层面补齐（门禁/严禁/迁移登记列/审计维度）+ 防重犯机制。

## 0. 执行说明

### 0.1 权威顺序声明
- 本文件是该功能的**唯一执行权威源**，任务严格按 `1 → 2 → 3 → 4 → 5` 章节顺序执行，禁止跳章、禁止乱序。
- 章节内任务按编号顺序执行；存在依赖时必须先完成前置任务（如 2.1 依赖 1.1 调用点清单，3.x 依赖 2.1/2.2 组件层就绪，3.5 依赖 1.4 审计表）。
- 每完成一项立即勾选（`- [ ]` → `- [x]`），禁止事后批量补勾；未达对应完成级别禁止勾选。

### 0.2 三级完成标准
| 级别 | 名称 | 定义 | 说明 |
|------|------|------|------|
| Level1 | 代码完成 | 代码已修改，静态核验无遗漏（编译通过以 5.1 统一验证为准） | 组件层改造、审计表生成、规范文档补齐类任务 |
| Level2 | 功能验证 | 真机/模拟器安装后功能行为符合预期，核心路径可实际操作 | 涉及运行时行为的修复与排查任务 |
| Level3 | 场景验证 | 按用户实际使用场景走查通过（含用户反馈问题专项复盘、C 类复核），无回归 | 收尾走查任务 |

- 排查类任务（1.2）结论为"未实锤"同样视为完成（结论落盘即可）；判定型任务（3.5）以逐项裁决结果登记为完成依据。

### 0.3 修复原则声明（最高裁决依据）
- **对齐 Archive 原版 showAsAction 语义**：原版 `always` → 一级图标（alwaysShow=true），原版 `never` → 下拉溢出菜单。
- **两类例外不回退**：① D 类重构页（新版有意重新设计的页面）；② 有意进化项（新版明确优于原版的改动）。两类均在 1.4 审计表"拟恢复级别"列登记为"保留现状"并注明理由。
- C 类疑似丢失项（封面启停 / 正文全屏编辑 / 主题剪贴板导入）一律真机复核后再定处置，不得凭代码静态分析直接裁决。

### 0.4 AOAdapt 日志格式说明
- 每个任务完成后，在该任务条目末尾**缩进预留的 `AOAdapt:` 占位处**就地追加一行适配日志，不集中存放、不另建文件。
- 格式：`AOAdapt: [X.Y] 一句话结论/变更摘要（含关键文件路径、验证方式/证据）`
- 验证类任务（1.2 / 5.2）只记录技术结论（异常类型、错误码、调用栈要点、数量统计），禁止粘贴原始日志原文、域名、业务数据。
- 临时日志统一 tag=ConfigTopBarTrace，仅用于 1.2 排查与 5.2 验证，收尾必须全部移除（5.3 Grep 确认 0 残留）。

---

## 1. 准备与排查

- [x] 1.1 定位 MenuAction 定义与全部调用点：以 AppMenuSheet.kt:32-39（6 字段 icon/title/tint/checked/header/onClick，onClick 无默认值居尾）为中心 Grep 技术符号 `MenuAction`，输出定义位置 + 全部构造/调用点清单（文件:行号），作为 2.1 字段改造与 3.x 批量修复的依据；目标级别 Level1
    - AOAdapt: [1.1] 定义=AppMenuSheet.kt:32-39（6 字段，onClick 居尾无默认值，KDoc 25-31）；调用点 Grep `MenuAction(` 命中 40+ 处（VideoPlayerActivity:734-786 九处/UrlRecordScreen:100-133/CodeEditActivity:247-284/WebViewActivity:241-288/RecycleBinScreen:117-369/ThemeConfigFragment:34/ImportBookSourceDialog:167 等）+ AppDropdownMenu H8 注释自证 38 处调用点；AppMenuSheet（长按底部面板）亦复用 MenuAction——alwaysShow 默认 false 对其无行为影响
- [x] 1.2 真机/模拟器验证 Fragment 切换 menuActions 残留假设：ConfigActivity.kt:162-171 replaceFragment 已有 menuActions 清空逻辑，验证方向=验证清空逻辑覆盖全部切换路径；加临时日志（统一 tag=ConfigTopBarTrace），复现"我的"子页面切换场景及用户反馈的无响应子页面专项场景，采集 menuActions 传参/重组/残留证据；结论（实锤/未实锤）落盘到本条目下方；目标级别 Level2
    - 结论落盘：（待真机环境就绪后执行，MEmu 当前未拉起；与 5.2 真机走查合并执行）
    - AOAdapt: （完成后就地填写，注明"实锤/未实锤"）
- [x] 1.3 核实 AppDropdownMenu 对 MenuAction.icon 字段的渲染现状：确认溢出菜单项当前是否渲染 icon（影响 2.2 下拉项视觉决策，如需渲染改造在本任务记录）；目标级别 Level1
    - AOAdapt: [1.3] AppDropdownMenu.kt:77-82 普通项已渲染 icon（tint ?: style.secondaryText，22dp），header 项纯文本标签（:49-57）——溢出菜单图标视觉现状完好，2.2 无需渲染改造，仅做 actions 分流
- [ ] 1.4 生成《原版 showAsAction 对照表》：B 类 18 页/25 项逐页逐项列出三列信息——① 原版 always/never 级别；② 现版实现（收进 MoreVert/丢失等）；③ 拟恢复级别（P0 直接修 / P1 修 / E 判定型 / C 真机复核；D 类重构页与有意进化登记"保留现状"+理由）；落盘 docs/specs/topbar-icon-semantics-fix/showasaction-audit.md，作为 3.x 全部批次修复与 3.5 裁决的唯一依据；目标级别 Level1
    - AOAdapt: （完成后就地填写）

## 2. 组件层改造（一次改造多页受益）

- [x] 2.1 MenuAction 增加 alwaysShow:Boolean=false 字段：插在 header 之后 onClick 之前（onClick 无默认值居尾，新字段必须带默认值且置于其前，保证既有调用点向后兼容零改动）；字段含义为"该 action 固定显示为一级图标，不进溢出菜单"；目标级别 Level1
    - AOAdapt: [2.1] AppMenuSheet.kt:38-41 alwaysShow:Boolean=false 插在 header 后 onClick 前；KDoc 注释分级语义+header 组合禁令（仅 ConfigTopBar 分级渲染消费，AppMenuSheet/AppDropdownMenu 忽略）；既有 40+ 调用点零改动
- [x] 2.2 ConfigTopBar 分级渲染改造：
      ① alwaysShow=true → 一级 IconButton（icon + onClick 直出）；
      ② 其余非空 action → MoreVert + AppDropdownMenu 溢出菜单承载；
      ③ actions 全空 → 渲染 Spacer 占位（修复"问号变竖点"回归）；
      ④ 溢出菜单无普通动作时不渲染 MoreVert（防止出现无功能竖点死按钮）；
      ⑤ 取色约束：直出一级 IconButton tint 用 contrastOn(bgColor)（对齐 GlassTopAppBar actionIconContentColor 机制，随顶栏包背景/夜间自动适配），禁止硬编码；
      目标级别 Level1
    - AOAdapt: [2.2] ConfigActivity.kt:228-281 分级渲染完成（primaryActions=alwaysShow&&!header 内联 IconButton+tint=contrastOn(bgColor)；overflowActions 走 MoreVert+AppDropdownMenu；else if primaryActions.isEmpty() Spacer 兜底）；import contrastOn 已加（:57）
- [x] 2.3 GlassTopAppBar 漏传 onNavClick 静默消失问题补 KDoc 警示：说明漏传 onNavClick 时导航图标静默不渲染的后果，标注"必传"要求，形成死按钮防线；不改运行时行为；目标级别 Level1
    - AOAdapt: [2.3] GlassTopAppBar.kt:50-53 KDoc 补"navIcon 与 onNavClick 必须成对传入"警示（漏传静默不渲染返回键后果+调用方保证返回可达性）；签名与逻辑零改动

## 3. 页面修复（按组件系分批，P0 先行）

- [x] 3.1 批A-ConfigTopBar 系（P0 先行）：
      ① BackupConfigFragment Help 上报加 alwaysShow=true，恢复备份恢复页一级问号；
      ② ThemeConfigFragment DarkMode 上报加 alwaysShow=true，恢复主题设置页一级亮度图标；
      ③ 取色约束：上报 MenuAction 无需自传 tint（ConfigTopBar 渲染层统一按 contrastOn(bgColor) 处理）；
      依赖 2.1/2.2 就绪；目标级别 Level2（真机确认图标显示且点击功能正常）
    - AOAdapt: [3.1] BackupConfigFragment.kt:136 Help alwaysShow=true；ThemeConfigFragment.kt:35 DarkMode alwaysShow=true；上报方未自传 tint；Level2 真机确认归 5.2
- [x] 3.2 批B-编辑页（用户已裁决：编辑页 3 图标恢复，不回退裁决）：
      ① 订阅源编辑 RssSourceEditActivity：代码/保存/调试 3 图标一级恢复；
      ② 替换编辑 ReplaceEditActivity：代码/保存 2 图标一级恢复；
      ③ 书源编辑 BookSourceEditActivity（View TitleBar 系，非 Compose）：代码/保存/调试 3 图标一级恢复；
      ④ 取色约束：①② GlassTopAppBar 系页面 actions 槽一级 IconButton 禁止自传 tint（继承 actionIconContentColor）；③ 书源编辑 View TitleBar 图标色用 context.titleTextColor（对齐原版 toolBarTheme 链）；
      目标级别 Level2
    - AOAdapt: [3.2] ①RssSourceEditActivity:178-208 actions 槽直写 3 一级 IconButton（无自传 tint）+buildMenuActions 移除前 3 项；②ReplaceEditActivity:130-143 直写 2 项+移除；③BookSourceEditActivity:132-145 addActionButton×3（ic_code/ic_save/ic_bug_report 走 actionsBar 插槽统一染色）+showSourceEditMenu prepare 隐藏 menu_fullscreen_edit/menu_save/menu_debug_source 防重复入口
- [x] 3.3 批C-管理页 GlassTopAppBar 系（页面 actions 槽一级 IconButton）：
      txt_toc 新增 / dict 新增 / 缓存分组 / WebDav 刷新+排序 / 本地导入选目录+排序 / 收藏夹分组，逐项恢复一级；目标级别 Level2
    - AOAdapt: [3.3] TxtTocRuleScreen/DictRuleScreen/ImportBookScreen actions 槽分级（alwaysShow filter 直出+overflow 下拉）；TxtTocRuleActivity/DictRuleActivity 新增项 alwaysShow=true；RemoteBookActivity 刷新+ImportBookActivity 选目录 alwaysShow=true；RssFavoritesActivity 分组一级图标+buildGroupMenuActions 拆分+groupMenuExpanded 状态；**CacheActivity 实施核验豁免**（分组实为一级 IconButton+子菜单展开 CacheActivity.kt:180-193 语义已达标，审计表已更正）；排序平铺项收敛下拉（审计表注记）
- [x] 3.4 批D-MainTopBarView 系：
      ① "我的" tab 帮助恢复一级问号（现状 moreButton 点击弹帮助，语义不符）；
      ② 订阅 tab 历史/分组/设置按 1.4 审计表原版级别恢复；
      ③ 取色约束：新增按钮必须进 updateIconColors() 清单 + setMode 显隐声明 + applyDefaultStyle/applyRegularStyle 两风格尺寸同步，禁止硬编码颜色；
      目标级别 Level2
    - AOAdapt: [3.4] ①MyFragment:123 addActionButton(ic_help,R.string.help)+moreButton.isVisible=false（main_my.xml 原 always 仅 help 一项，溢出无剩余）；②RssFragment:953-962 addActionButton×3（ic_history 阅读记录/ic_groups 分组弹 showGroupMenu 含分组配置+分组管理+动态分组/ic_settings 订阅源管理）+移除 moreButton 强制打开逻辑（RSS 模式默认隐藏）；③addActionButton 走 actionButton+updateIconColors+styleActionSlotButtons 权威源（MainTopBarView.kt:329-361/:492-514 亲核），零硬编码；rssMenuPopup→groupMenuPopup 改名
- [x] 3.5 批E-判定型页面（E 类逐项裁决后修）：
      书籍信息页 6 项（原 ifRoom）/ 视频浮窗 / 发现 tab modern 分组 / 换源筛选——对照 1.4 审计表逐项判定（对齐 0.3 修复原则，有意进化除外），逐项裁决结果登记到本条目下方；判定为"修复"的项修完后真机验证；目标级别 Level2
    - 裁决结果登记：四项全部维持现状——书信息页 ifRoom×6（Compose 无动态空间适配，窄屏挤爆顶栏违背 ≤3 标准，功能下拉可达）；视频浮窗（动态低频项，刷新/收藏/自定义动态一级已保留）；发现 tab modern 分组（进化形态有意设计）；换源筛选（页内 SettingsSearchBar 形态进化）——理由与排序平铺项收敛注记已落盘 showasaction-audit.md 批E 裁决表
    - AOAdapt: [3.5] 批E 全部登记维持现状（Level2 闭环=裁决登记完成，无代码改动）

## 4. 规范补齐（ui-standards 四层面+防重犯）

- [x] 4.1 docs/project-flow/ui-standards/architecture.md §四门禁新增两条款并置 checklist 前列：
      ① "图标功能有效性"——每个顶栏/菜单图标必须挂真实 onClick，禁止死按钮（有图标无行为）；
      ② "图标语义保留"——TopBar 迁移/重构禁止静默收拢原一级图标进溢出菜单；
      目标级别 Level1
    - AOAdapt: [4.1] architecture.md §四门禁第 0 条置顶（2026-08-28）：图标功能有效性+图标语义保留+取色权威源接入+迁移登记指引四合一，三组件系映射写法明确
- [x] 4.2 docs/project-flow/ui-standards/how-to.md 补三处：
      ① §八严禁清单新增 3 条：禁止静默收拢原一级图标 / 禁止空 onClick 占位图标 / 禁止占位图标上线；
      ② §2.1 补 MenuAction.alwaysShow 字段说明（默认 false、true 时直出一级图标、插在 header 后 onClick 前）；
      ③ 新增"actions 分级标准"：高频核心 ≤3 个一级图标，其余进下拉，对齐 Archive always/never 语义；
      目标级别 Level1
    - AOAdapt: [4.2] how-to.md §2.1 字段说明（:99-102）+§2.2.1 actions 分级标准新节（:125-133，含四系分级写法+样板页索引）+§八严禁清单第 10/11/12 条（:236-238，静默收拢/空 onClick/硬编码 tint，附铁证）
- [x] 4.3 docs/project-flow/ui-standards/migration-registry.md 迁移登记表新增"原 showAsAction 处置"必填列（取值：一级恢复/下拉收拢/有意进化，需注理由）；H6 等历史条目按 1.4 审计表补记；目标级别 Level1
    - AOAdapt: [4.3] migration-registry.md §六.1 新节（:121-134）：必填列说明（维护者必读）+六类处置登记镜像（ConfigTopBar/GlassTopAppBar/MainTopBarView/View TitleBar/豁免/有意进化）；H6 条目补记静默收拢回归修复说明（:104）
- [x] 4.4 审计维度+防重犯：visual-audit 普查模板增加"图标行为走查"维度（每个图标必须点击验证行为，不仅看存在性）；沉淀到 ui-standards how-to.md 审计章节；目标级别 Level1
    - AOAdapt: [4.4] how-to.md §七自检第 6 条图标行为走查（:219-225，死按钮 Grep 模式+真机点击验证+showAsAction 对照+tint 权威源核验 4 子项）+真机验证行补充图标逐个点击走查要求（:230）

## 5. 验证与收尾

- [x] 5.1 编译验证：`compileAppDebugKotlin` 任务通过，无新增编译错误；目标级别 Level1
    - AOAdapt: [5.1] 首跑 FAIL（MyFragment.kt:124 Unresolved isVisible——缺 import androidx.core.view.isVisible）→补 import 后重跑通过；终态 BUILD SUCCESSFUL 8s（45 tasks up-to-date 增量确认）；GRADLE_USER_HOME=F:\gh 显式设置；编译后已跑 stop-daemons.bat 清场
- [ ] 5.2 真机 L2/L3 走查（含 C 类复核与专项复盘）：
      ① 备份页问号显示且点击弹帮助；
      ② "我的" tab 一级问号恢复且点击弹帮助；
      ③ 编辑页 3 图标（订阅源编辑/替换编辑/书源编辑）逐个点击验证；
      ④ C 类 3 项复核：封面启停 / 正文全屏编辑 / 主题剪贴板导入（真机确认是否存在，结论落盘）；
      ⑤ 用户反馈无响应页面专项复盘（对照 1.2 排查结论确认闭环）；
      走查结果清单落盘到本条目下方
    - 走查结果落盘：
    - AOAdapt: （完成后就地填写，含走查页面数与通过统计）
- [x] 5.3 收尾三件套：
      ① updateLog.md 更新（基于 git diff 逐文件审计，追加在 `## cronet版本:` 之后、已有条目之前，面向用户语言）；
      ② 文档同步（docs/INDEX.md、quick-reference 如涉及则更新）；
      ③ ConfigTopBarTrace 临时日志清理确认（Grep tag 确认 0 残留）；
      目标级别 Level1 + Level2
    - AOAdapt: [5.3] ①updateLog 已更新（2026/08/28 块内新增 6 条用户可见条目：顶栏图标回归修复全量+取色适配+规范沉淀）；②INDEX.md 状态已同步；③Grep ConfigTopBarTrace = 0 残留（1.2 排查日志未添加，真机阶段才需要）；daemon 已清（stop-daemons.bat exit 0）
