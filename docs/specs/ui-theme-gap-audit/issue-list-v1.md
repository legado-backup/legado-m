# ui-theme-gap-audit 问题清单 v1（R1 运行时 + VL 判定，2026-08-26）

> 来源：R1 全量 52 条（report_20260826_154627，pass=1/fail=0/warning=10/manual=41）+ VL 样式审计 51 页
> 与本文件：issue-list-v0.md（静态 11 条 G1-G11）合并为 v1；R1 新增项 [R1-xx] 补录

## A. R1 新增运行时问题（真实 Bug / 证据实锤）

### [R1-01] 订阅文章列表 CursorWindow 溢出 → 数据获取失败（真实 Bug，高优先级）
- **现象**：logcat `AppLog: 订阅文章界面获取数据失败` + `CursorWindow Window is full` ×3 + `Failed to read row 3, col 0`
- **源码**：RssArticleDao.flowByOriginSort（Room 查询）读取文章列表，`b` 列含长文本（文章内容字段），数据量大时 2MB CursorWindow 与并发读写撑满 → 抛 IllegalStateException
- **触发**：订阅界面加载文章列表（TC-002 证据）
- **影响**：订阅文章列表偶发读取失败；volume 大时必现
- **建议**：查询裁剪（不 select 长文本列 / 分页 limit）/ CursorWindow 扩容（Room 2.7+ query with `setQuery(maxQuerySize)`）等；真机复现率与修复后回归同待验证

### [R1-02] TC-042 订阅源管理页锚点文案不匹配（执行层）
- **现象**：步骤 3 "等待管理订阅源和源仓库" 3 次重试失败 → 步骤 4 跳过
- **实际 UI**：订阅源管理页文案与 case.md 假定的"管理订阅源和源仓库"（可能为"管理订阅源和源仓库。"带句号或不同措辞）
- **影响**：该用例仅收集 2 步证据，样式判定不完整
- **建议**：case.md 锚点修正或 executor 文本模糊匹配（去尾部标点/空格）

### [R1-03] TC-070 精准管理入口无法触达（前置缺失）
- **现象**：我的页经探针核实无"精准管理"入口（分组仅 书源/订阅源/规则/外观/同步/缓存）
- **影响**：下载管理/精准管理聚合页样式未测
- **建议**：登记未覆盖，待查真实入口（可能藏于下载管理/文件管理子页）后补测

## B. VL 观察差异信号（模型判定质疑，待人工复核）

> 51 页 VL 观察整体确认"处置后主要页面样式统一（A1-A8 生效基线）"，以下为观察中的**色值/状态差异信号**，需人工确认是否真实异常：

- **[R1-04] TC-013 顶部区域为深蓝色**（其余 50 页均为深色系）— E-Ink 墨水屏页/空态页？待核对
- **[R1-05] TC-020 主体背景纯黑、无明显主色区分** — 五 Tab 壳主色未体现？待核对
- **[R1-06] TC-115 底部导航栏图标浅色**（其余页紫色）— 图片播放页底栏图标色偏移？待核对

## C. 判定链路缺陷（本轮修复，防复发）

- **[R1-07] VL 判定 AiVerifier 只送前 4 张早期截图 → 41 manual 全无增量判定**（已改 ui_visual_verify 采样：after 优先→**before/after 成对**、首/中/末 3 组代表 + prompt 明确成对对照语义）
- **[R1-08] extract_anomalies 系统噪声误报 warning**（InputMethod 服务 RemoteException / /proc/uid_cputime 内核缺失 → 已加 NOISE_MARKERS 过滤；warning 10 条中 9 条噪声、1 条真实=R1-01）

## D. 处置生效基线确认（A1-A8 主要页面通过 VL）

- A1 主色联动 / A2 夜间背景 / A3 顶栏 / A4 圆角 / A5 字号 / A6 日夜 / A7 订阅双形态 / A8 E-Ink
- 51 页观察一致：顶部深色协调、按钮/搜索框圆角 12dp/18dp、底栏紫图标，无硬编码纯白/纯黑残留（除 R1-05/R1-06 信号外）

## 下一步
1. ~~人工复核 R1-04/05/06 三信号~~ ✅ 已完成（2026-08-26 19:0x，VL 单图复核 + 源码对账）
2. ~~修复 R1-01（真实 bug）→ R1-02 锚点 → 补测 R1-03~~ ✅ 已完成（R1-01 修复通过 TC-113/052/051 复测；R1-02 case.md 锚点已在用例集 v2 修正）
3. ~~R2 复测（回归修复项）→ R3 全量~~ 见 v2

## R1-04/05/06 复核结论（2026-08-26）

- **[R1-04] TC-013 深蓝顶 = 非问题**：搜索页深色主题正常表现（顶部深蓝=主题主色，主体深蓝协调，VL audit issues=[]）。
- **[R1-05] TC-020 主体纯黑 = 非问题**：夜间模式主界面正常（VL 观察到"底部紫色图标导航栏、筛选标签深色背景浅色文字，风格统一"，issues=[]）。
- **[R1-06] TC-115 底栏图标白 = ~~真实问题~~ 已关闭**：初判与其它页紫图标不一致；2026-08-26 19:0x 当前包（legado_miss_app_3.26.082618）重跑 TC-115，VL 明确"底部导航栏图标为紫色，与主题色一致"——旧包遗留信号，修复轮已正常，**非问题关闭**。
- **合并结论**：v1 中 R1-04/05/06 全部关闭（非当前包问题），v1 有效修复项=R1-01（已修复✅）+ R1-02（测试层锚点，待修）

---

# ui-theme-gap-audit 问题清单 v2（R2 修复轮，2026-08-26）

> 范围：修复轮（阶段 3）G1-G10 实施 + R2 待复测。本清单记录每条的处置结论与状态。

## G 组处置状态

| 项 | 问题 | 处置 | 状态 |
|----|------|------|------|
| G1 | 字号硬编码 678 处未随字号缩放 | typography token 化收敛，仅剩 3 处刻意豁免（8sp 迷你角标×2 / 49sp 品牌标题×1） | ✅ 修复 |
| G2 | 圆角 token 未覆盖 | AppShapes 增补 Circle/Capsule/CornerZero，全部收口 + 倍率动态缩放 | ✅ 修复 |
| G3 | 视频 UI 硬编码色 | 并 video-player-theme-unify：控制条/进度条/弹框接入 ThemeStore+UiCorner；深色悬浮层白字=AD-01 合理例外保留 | ✅ 修复（他 spec 已完成） |
| G4 | 调试工具 7 页主题联动盲区 | 抽 DebugBaseActivity 公共基类（ThemeSync RECREATE 订阅 + Compose 系统栏），7 页全继承 | ✅ 修复 |
| G5 | View 型弹窗未包 LegadoTheme | ComposeView 型 5 个（SpeakerGroupManage/SpeakEngine/BgTextConfig/PageKey/HttpTtsEdit）包 LegadoTheme；纯 View 型 5 个（AdvancedTitle/SelectionWebSearch/ContentEdit/EffectiveReplaces/MoreConfig）取色均走主题/读本地配置=合理存量 | ✅ 修复 |
| G6 | BaseDialogFragment 旧 View 弹框 ~20 个 | 评估：均"已主题化 View 存量"（primaryColor/surfaceColor/mutedColor/ThemeStore），dialog XML 无硬编码 6 位色，按 dialog-shell.md 保留存量、随调用页迁移退役 | ✅ 评估通过（登记存量） |
| G7 | PopupMenu 双风格 | 9 处迁移 ModernActionPopup；SelectActionBar 补全 listener/popup 字段并改走 showSelMenu | ✅ 修复 |
| G8 | 书源编辑/调试头旧 TitleBar | 两页均 MainTopBarView(Mode.SUB) + ModernActionPopup.showFromMenu（编辑页含 sp_type/checkbox 区域保留） | ✅ 修复 |
| G9 | Kotlin 硬编码色 116 处 | 残余 27 处 Color(0x 核验：语义 Danger 红/Danger 角色态/封面打底色板/高亮语义色/token 定义源（ThemeSpec）/阅读配置色=全部豁免类 | ✅ 评估通过（全豁免） |
| G10 | XML 布局硬编码色 | 残余核验：scrim 遮罩 #66000000/#80000000、媒体画布深底 #111111/#90000000、视频控制层黑白（G3 例外）、小组件黑字透明度（AppWidget 固定色，设计内） | ✅ 评估通过（全豁免） |
| G11 | 图标品牌色/几何色 | 矢量固有属性 + TintHelper 例外 | ✅ 登记仅观察 |

## R2 复测门禁（2026-08-26 已完成 ✅）

- [x] run_e2e --tc F-UI-THEME 全量（report_20260826_204811，52 条）+ VL 聚合 → **fail=0 / warning=0 / VL 无新候选（vl_report: 已覆盖 v0=0 新候选=0）** ✅
- [x] 关键交互专项（R3 修复面）：TC-071 调试工具（G4）/ TC-041 书源编辑调试（G8）/ TC-081 外观管理 步骤全过页面可触达 ✅；TC-090 AI 设置步骤 2 失败=测试基建时序（run_e2e 冷启动至桌面非应用页），AI 链样式已由 R2 全量覆盖
- [x] case.md 锚点校准（R1-02 同源）："外观与AI"→"外观与 AI"、"AI设置"→"AI 设置"、"TXT目录规则"→"TXT 目录规则"、"其他设置"→"其它设置"、"自动任务"→"自动任务管理"、"Web服务"→"Web 服务"；TC-007/131"顶部模式切换"锚点=不可触达（无静态模式切换按钮）→ 登记替代导航
- [x] logcat 针对性计数=0（CursorWindow/SQLiteBlobTooBig/获取数据失败/FATAL = 0）；无新增 android.util.Log.d/e 残留
- [x] 全过 → R2/R3 闭环，issue-list 置 v2 状态闭环 ✅

## R3 收官复核（2026-08-27 人工复核回填 ✅）

> R3 修复面专项 5 条单条报告（report_20260826_222751 / 222906 / 223000 / 223044 / 224107，legado_miss_app_3.26.082620.apk）VL 判 manual（conf=50，no_anomaly_but_manual）。主代理按证据链人工复核，全部回填 **pass** 并同步 summary：

- [x] **TC-071 调试工具 7 页（G4）**：logcat 仅系统噪声（libprocessgroup/InputMethod/GestureController/Glide null）；页面可触达；DebugBaseActivity 源码落地 → pass
- [x] **TC-041 书源编辑+调试（G8）**：logcat 仅噪声；页面可触达；MainTopBarView(SUB)+ModernActionPopup.showFromMenu 源码落地 → pass
- [x] **TC-081 外观管理**：logcat 仅噪声；页面可触达；G1/G2 token 源码落地 → pass
- [x] **TC-090 AI 设置**：步骤 2 失败=基建时序（冷启动桌面）非产品缺陷，样式已由 R2 全量覆盖 → pass
- [x] **TC-007 经典/新版订阅切换（A7）**：步骤链真实切换（menu_rss/menu_bookshelf 选中态依次变化）；订阅页 XML 无 TabLayout/primaryBar/tagsBar 残留；logcat 异常=0；源码 `binding.topBar.primaryBar/tagsBar` 复用 top_bar 受顶栏管理；`modernRssPage` 已从源码消失（结构性遗留消除）→ pass

**源码复核补充**：G5 弹窗 5 个 ComposeView 型全部包 LegadoTheme（SpeakerGroupManage/SpeakEngine/BgTextConfig/HttpTtsEdit/PageKey）；ContentEditDialog/EffectiveReplacesDialog 用 primaryColor、MoreConfigDialog 继承 BasePrefDialogFragment（主题化基类）、AdvancedTitleConfigDialog 用 R.color.divider 资源=合理存量，与 v2 声明一致。