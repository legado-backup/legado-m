# ui-theme-gap-audit 技术设计

## Technical Approach

### 0. 设计阶段清单先行（用户强制：功能清单 + 页面清单 + 流程清单）

> 全量覆盖可对账的前提是**先有清单**。设计阶段即产出三清单，实施以此为锚：

- **`features-inventory.md`（功能清单，v1）**：31 功能域（F1-F31）+ M1-M7 消费对账 + **P1-P14 流程级（业务流转链）+ S-P1~P5 场景级处置组合**。
- **`pages-inventory.md`（页面清单，v2 分层模型）**：L1 Activity 98 / L2 Fragment 25 / L3 Screen·Route 61 / L4 弹框·弹层 130+ / L5 layout XML 208 / L6 设置项 ~68（task 1.1 提取）；页面单位 184，交互全量 500+。
- **修订机制**：实施中回填清单打版本（v0→v1→...），交付以清单版本核对表证明"全面"。

### 1.0 全量页面清点与页面覆盖矩阵（用户强制"全面"）

> 目的：保证审计与测试"不落一页"，交付时可对账"是否真的全面"。

- **清点源（分层）**：L1 `AndroidManifest.xml` `<activity>` 全集；L2 `ui/**` Fragment 类；L3 `ui/**/*Screen.kt/*Route.kt`；L4 `*Dialog*.kt/*Sheet*.kt` + `dialog-shell.md`；L5 `res/layout/*.xml`（前缀分类：activity/fragment/item/dialog/view/popup/switch/video）。
- **产出 `pages-inventory.md`**：分层清点模型（L0-L6）+ 每页属性（入口、骨架 S1-S6、技术栈、模块锚点、Compose 化状态）。
- **覆盖矩阵**：`页面 × 样式维度`（头部 / 三点菜单 / 弹框 / 底部弹层 / 列表卡片 / 搜索框 / 空态 / 主题联动 / 处置前后）。审计与用例**逐格推进**，每格状态：未审 / 已审无缺口 / 已审有缺口(Cx) / 无法触达(原因)。
- **覆盖率**：`已审页面 / 全量页面`，交付附矩阵核对表（S-10），无法触达页面登记原因，后续轮补触达。

### 1.1 流程级/场景级覆盖（用户强制：全部功能流转链）

> 页面静态清单证明"每页可用"，**流程清单证明"每条功能流转链的每个环节都一致"**。功能趋稳期，跨页面跳转点/弹框入口/模式切换是脱节高发区，必须全链穿行验证。流程清单见 `features-inventory.md` P1-P14 + 场景 S-P1~P5。

- **流程覆盖协议**：
  ```
  P1-P14 每条流程 → 用例组（全链穿行）：
    环节链逐环节截图（[VL]）+ 每环节断言（[UI]）
    中途执行处置（A1-A8，[联动]）→ 后段环节必须保持处置生效
    出口环节（如换源弹框、导入弹框）重点核家族一致性（M6/M7）
  ```
- **场景覆盖协议**：S-P1~P5 处置组合场景，验证"叠加处置不打架、不丢配置"。
- **流程×页面交叉**：每条流程登记其经过的页面/弹框 → 与页面覆盖矩阵交叉核对，保证"流程覆盖 ⊆ 页面覆盖、每条流程至少 1 条穿行用例"。

### 1. 主题管理面（7 类设置项基线）

| # | 管理面 | 产生方（入口） | 消费 API / 组件 | 判定"被管理"的判据 |
|---|--------|---------------|----------------|-------------------|
| M1 | 主色 / 强调色 / 背景 / 底部背景 / 导航栏色 / 沉浸 | ThemeManageActivity / ThemeConfigFragment → `ThemeConfig` + `ThemeStore` | `ThemeStore` 静态读、`LegadoComposeTheme`（toM3Scheme）、`ThemeSpec` | 组件取色应源于 M3 colorScheme（由 LegadoTheme 桥接）或 ThemeStore，不得直写字面量 |
| M2 | 顶栏（标签栏色/选中色/壁纸/圆角/胶囊） | TopBarManageActivity / TopBarEditDialog → `TopBarConfig` | `MainTopBarView`（Mode.NORMAL/MY/SUB）、`TitleBar(topBarColorManaged)` | 主界面头部必须读 TopBarConfig；子页 TitleBar 须经 `topBarColorManaged` 读配色 |
| M3 | 圆角（全局倍率 `uiCornerScale`） | 主题设置 → `UiCorner` / `AppShapes` | `AppShapes` 7 token、`UiCorner.panelRadius/actionRadius/searchRadius` | 禁止散落 `RoundedCornerShape(N.dp)` / View radius 魔数 |
| M4 | 字号（全局刻度 `text_10sp..text_36sp` + 缩放） | 主题设置字号缩放 | `res/values/dimens.xml` 刻度表、MaterialTheme.typography | 禁止散落 `fontSize = N.sp` / `android:textSize="Ndp"` 魔数 |
| M5 | 搜索框（18dp 圆角浅底） | 统一口径（bugfix ②） | `SettingsSearchBar`(Compose) / `TopBarSearchStyle` / `bg_searchview`(View) | 两端均 18dp，不再出现胶囊形/35dp |
| M6 | 弹框族（确认/编辑/单选/列表/分组/日志/帮助） | ComposeDialogFragment 家族 | `AppDialogFrame` / `AppDialogStyle` / dialog-shell.md 清单 | 弹框必须 `ComposeDialogFragment` 子类，禁止 `BaseDialogFragment`+XML 新建 |
| M7 | 底部弹层 / 菜单 | AppModalBottomSheet / AppMenuSheet / ModernActionPopup | `AppModalBottomSheet`、`ModernActionPopup` | 三点菜单统一 `ModernActionPopup`；底部弹层统一 `AppModalBottomSheet`/ComposeDialog 底部档位 |

> 管理面基线中"设置项 key 清单"（PreferKey/ThemeConfig Config 字段）在 tasks 1.1 中从 `constant/PreferKey.kt` + `help/config/ThemeConfig.kt` 提取，作为 M1/M2 的判定锚点。

### 2. 静态审计判据矩阵（C1-C6）

| 判据 | 扫描模式（Grep/脚本） | 命中样例 | 说明 |
|------|----------------------|---------|------|
| C1 硬编码颜色（Kotlin） | `Color(0x`、`Color\.(Black|White|Gray|Red|Blue|Green|Yellow|Cyan|Magenta)`、`Color\.LightGray|DarkGray` | `Color(0xFF888888)` | 命中→归属页面，核验是否为合理例外 |
| C2 硬编码颜色（XML/drawable） | `android:textColor="@android:#`、`#RRGGBB`(values/layout)、`solid android:color` | `#EF5350` 直写 | res 中 unqualified 色值 |
| C3 硬编码圆角（Kotlin/XML） | `RoundedCornerShape(`、`<corners android:radius="\d+dp"`、`CornerRadius(` | `RoundedCornerShape(8.dp)` | 应为 AppShapes/UiCorner |
| C4 硬编码字号/间距 | `fontSize = \d+\.?\d*\.sp`、`android:textSize="[\d.]+(dp|sp)"`、`Modifier.padding\(\d+\.dp\)` | `fontSize = 12.sp` | 字号走刻度表；间距是低危项仅登记 |
| C5 误取色源 | Compose 内 `MaterialTheme.colorScheme` 但事务应读 `TopBarConfig`/`ThemeSpec`/PreferKey 处（按 M1/M2 归属） | 头部取 `colorScheme.primary` 而非 TopBarConfig | 人工核验为主，Grep 定位引用点 |
| C6 不响应主题（联动缺口） | `ThemeSync.kt` RECREATE 订阅者清单 vs 全 Activity 清单求差集；EventBus 主题事件订阅检查 | 设置页改色后某 Activity 不重建 | 联动覆盖矩阵（见 tasks 2.6） |

**执行方式**：Grep 模式集（固定到 `docs/project-flow/ui-standards/` 或 tasks 中登记）→ 命中落盘 `docs/temp-analysis/ui-gap-hits/`（gitignored）→ 子代理按 `task-navigation.md` 模块分组核验 → 汇总 `问题清单 v0`。

**合理例外清单（核验时豁免）**：封面占位色、阅读正文可配置色、视频播放器控制层品牌色、品牌强调色（如 Logo）、语义红绿蓝（成功/失败/预警提示）。

### 2.5 处置前后预期效果协议（before/after，用户强制）

> 静态判据只能发现"硬编码"，**"设置项改了到底变没变 / 哪些页面应变却不变"**必须靠处置前后对照暴露。这是"全面发现问题"的最后一块拼图。

- **处置（Action）类型全集**（对应 M1-M7 管理面）：
  | 处置 | 触发点 | 预期生效面 |
  |------|--------|-----------|
  | A1 改主色/强调色 | ThemeManageActivity 色板 | 全体页面头部(M1-M2 消费方)、按钮、标签、进度条、选中态 |
  | A2 改背景/底部背景/导航栏/沉浸 | 主题设置 | 主体背景、底部导航、状态栏/导航栏透明 |
  | A3 顶栏配置（标签栏色/选中色/壁纸/圆角） | TopBarManageActivity | 五主界面头部 + `topBarColorManaged` 子页标题栏 |
  | A4 圆角倍率 | 主题设置 | 全部 AppShapes/UiCorner 消费组件 |
  | A5 字号缩放 | 主题设置 | 全页面刻度表字号 |
  | A6 日夜切换 | 主题模式 | 全页面日/夜配色（含栈内已打开页） |
  | A7 经典/新版切换 | 订阅页模式开关 | 头部标签/搜索框/列表呈现（回归 bugfix ⑤） |
  | A8 E-Ink | 墨水屏开关 | 强制黑白 + 透明导航栏 |
- **三段式记录**（每个处置用例强制）：
  ```
  before 基线：处置前该页面截图 + 关键色值/圆角记录（u2 dump + 截图）
  处置：执行 A1-A8 之一 + 记录设置项 key 实际写入值（prefs 断言）
  after 生效：处置后同页面截图 + 重新断言
  对账：预期应变的消费方清单 × 实际变化 → 差额 = "改了不生效/半生效"缺口（P0）
  ```
- **对账矩阵**：`管理面(A1-A8) × 全量页面`，每格记录 before→after 是否变化。此矩阵与静态 C6 联动覆盖矩阵（RECREATE 订阅）交叉验证。

### 3. 测试用例设计（对接 ai_tests + VL）

- 新模块 `ai_tests/cases/F-UI-THEME/case.md`，沿用 F-P0-6 格式（TC-ID / 关联源码 / 前置 / 步骤 / 预期），每条新增 `验证法` 字段：`[UI]` 元素断言（uiautomator2）/ `[VL]` 截图送审 / `[联动]` 处置前后对照（before/after，见 §2.5）。
- **用例生成主循环 = 页面覆盖矩阵逐格**：`pages-inventory.md` 每个页面 → 至少 1 条"静态样式呈现"用例（[UI]+[VL]） + 涉及主题消费的页面再挂该页的处置用例（[联动]）。**禁止按"骨架×族"抽样代替逐页覆盖**（用户强制）。
- 用例矩阵（维度为辅，逐页为主）：

| 维度 | 用例组 | 验证法 |
|------|--------|--------|
| 逐页样式呈现 | 覆盖矩阵每个页面（头部/三点菜单/弹框/弹层/列表卡片/搜索框/空态） | `[UI]`+`[VL]` |
| 处置前后联动 | A1-A8 处置 × 受影响页面（§2.5 对账矩阵） | `[联动]` |
| 经典/新版切换 | 订阅页切换无残留 + 结构性问题清点 | `[UI]`+`[VL]` |
| 特殊态 | 空态/骨架/墨水屏/E-Ink/夜间 | `[VL]` |

### 4. 多模态判定协议（VL Protocol）

- **system prompt 模板**（写入 `ai_tests/lib/ui_visual_prompt.py` 或用例共享段）：角色=UI 样式审计员；判定维度=头部一致性 / 三点菜单一致性 / 弹框家族一致性 / 圆角 token 合规 / 配色跟随主题 / 与 Archive 基线差异；输出必须 JSON。
- **输出 Schema**（`chat_json`）：
```json
{
  "observations": "整页样式概述（技术描述，无业务数据）",
  "issues": [
    {"element": "元素定位", "style_desc": "观察到的样式", "expected": "基线预期",
     "actual": "实际", "match": true|false, "confidence": 0.0-1.0,
     "reason": "不一致的技术原因推测"}
  ]
}
```
- **采样**：页面全图（最长边 640 降采样）+ 局部放大区域（头部/菜单/弹框单独裁图）+ 主题切换前后对照图；送审前统一 `downscale_image_b64`。
- **校准**：每批取 10% 命中由人工/主代理复核；若与 VL 判定差值 > 15%，调整 prompt 或采样，重跑该批。

### 5. 轮次协议（Gate）

```
R1：run_e2e.py --tc F-UI-THEME（全量样式批次）→ 证据 + VL 分析 → 问题清单 v1（代码定位+方案，P0/P1/P2）
   ↓ 用户确认清单
一次修复（本任务阶段 3，另立 spec 或续章）
R2：全量复测 → fail=0 门禁 → 未通过则修复遗漏 → 再复测
R3：终测（全量 + 关键交互专项：主题联动/经典切换/夜间）→ 验收
```

## Architecture Decisions

### AD-01: 测试用例对接既有 ai_tests 框架，不新建测试基建
- **Context**: 项目已有 `run_e2e.py`（MD 轨道 case.md + 证据收集 + 报告）、`ai_tests/lib/`（MemuController/UiExecutor/LlmClient）。
- **Concern**: 新增样式测试是否要自建工具链。
- **Decision**: 用例落 `ai_tests/cases/F-UI-THEME/case.md`，VL 走 `LlmClient.chat_json`，复用 UiExecutor/证据收集器；仅新增少量脚本（VL 分析聚合 `ui_visual_verify.py`）。
- **Goal**: 零基建成本接入既有执行/报告/模拟器链路。
- **Tradeoff**: 用例受 MD 轨道语法约束；接受（既有用例同构，维护一致）。
- **Status**: Accepted

### AD-02: VL 判定强制结构化 JSON（chat_json）而非自由文本
- **Context**: 多模态输出直接进入问题清单聚合，需要机器可读。
- **Concern**: 自由文本无法去重/聚合/置信度排序。
- **Decision**: 统一 `chat_json` + issues 数组 Schema + confidence 字段；解析失败重试 2 次。
- **Goal**: 判定结果可聚合、可对账、可排序（置信度降序人工抽查）。
- **Tradeoff**: 模板约束强，复杂问题描述空间受限；接受（问题详情由人工核验补充）。
- **Status**: Accepted

### AD-03: 静态审计与运行时测试双轨交叉验证
- **Context**: 静态判据（C1-C6）能定位硬编码，但"设置项改了到底联不联动"只能运行时验证。
- **Concern**: 单一来源会漏（静态漏运行时、运行时漏静态）。
- **Decision**: 静态产出"候选孤儿清单"，测试产出"联动失效/风格不一致清单"，两清单对账合并为问题清单 v1。
- **Goal**: 双向补盲，问题清点尽可能完整（用户核心诉求）。
- **Tradeoff**: 工作量大一倍；接受（一次清点完整 > 反复返工）。
- **Status**: Accepted

### AD-04: 一次修复策略（问题清单驱动，禁止边测边修）
- **Context**: 用户明确要求一次性全量发现问题、一次修复、再复测。
- **Concern**: 边测边修会导致回归污染与上下文碎片化。
- **Decision**: 修复阶段只在本任务"阶段 3"（后续轮），以确认后的问题清单 v1 为唯一输入，按 P0→P1→P2 分批一次修完，再进入 R2/R3。
- **Goal**: 单次编译包承载全部修复，复测一次覆盖。
- **Tradeoff**: 修复周期内用户看不到中间结果；接受（有清单可审计）。
- **Status**: Accepted

### AD-05: 问题清单优先级分级（P0/P1/P2）
- **Context**: 清点结果将达数十条，需修复排级。
- **Concern**: 无分级则修复顺序混乱。
- **Decision**: P0=设置项全局联动失效/风格冲突致观感割裂（如改主色只生效一半）；P1=单页/单族风格过期（某弹框仍是 View 样式、搜索框圆角发散）；P2=细节偏差（间距/字号刻度未收敛）。
- **Goal**: 修复时先治全局后治局部，最坏情况也能保证 P0 全清。
- **Tradeoff**: 分级标准有主观性；接受（核验时按影响面落级）。
- **Status**: Accepted

## Data Flow

```
静态审计链：
  Grep 模式集(C1-C6) → hits/ 原始命中 → 子代理按模块核验 → 合理例外豁免 → 问题清单 v0
      ↓ 对账
测试链（后续轮）：
  run_e2e --tc F-UI-THEME → 证据(截图/XML) → ui_visual_verify.py(VL chat_json) → 联动对照
      ↓
  问题清单 v1（双轨合并，P0/P1/P2 + 源码定位 + 修复方案）
      ↓ 用户确认
  一次修复 → R2 全量复测(fail=0) → R3 终测 → 验收
      ↓
  文档同步：frontend-ui-standards / ui-standards(migration-registry) / updateLog / INDEX
```

## File Changes（本轮）

| 文件 | 变更 |
|------|------|
| `docs/specs/ui-theme-gap-audit/{README,spec,design,tasks}.md` | 新增：本 spec 四文档 |
| `docs/specs/ui-theme-gap-audit/features-inventory.md` | 新增：**功能清单 v1**（F1-F31 + M1-M7 消费对账 + **P1-P14 流程链 + S-P1~P5 场景组合**，设计阶段强制产出，已交付） |
| `docs/specs/ui-theme-gap-audit/pages-inventory.md` | 新增：**页面清单 v2 分层模型**（L1-L6 全覆盖，设计阶段强制产出，已交付） |
| `docs/specs/ui-theme-gap-audit/issue-list-template.md` | 新增：问题清单 v0 模板（FR-3 字段） |
| `docs/specs/ui-theme-gap-audit/management-surface.md` | 新增：7 类设置项管理面基线映射（FR-1 产出，tasks 1.1 生成） |
| `ai_tests/cases/F-UI-THEME/case.md` | 新增：全量样式测试用例集（FR-4） |
| `ai_tests/lib/ui_visual_prompt.py` | 新增：VL system prompt 模板 + JSON Schema 常量 |
| `ai_tests/scripts/ui_visual_verify.py` | 新增：截图送审/聚合/对账脚本骨架 |
| `docs/INDEX.md` | 更新：活跃 Specs 登记（🔄 设计中） |
| `docs/project-flow/ui-standards/migration-registry.md` | 更新：阶段 1 审计产出登记（审计后同步） |

> 本任务阶段 3（修复轮）的文件变更另立清单（以问题清单 v1 为准），不在本表。

## 经验沉淀（R1 修复轮，2026-08-26）

### K1: 大字段列表读取——禁止置空，一律按需单行加载（用户强制铁律）
- **背景**：订阅文章/收藏列表因部分源 image 存 base64 数据大图（实测单行最大 395KB），多行一次性 select 挤满 CursorWindow 2MB 窗口 → "订阅文章界面获取数据失败"。
- **反模式（已确认禁止）**：列表查询对超大 image 置空/截断（>300 字符置空）→ 用户明确否决："谁允许你置空的？我要的就是列表上有图片！要从技术手段解决加载大图！"
- **正解**：列表主查询不 select 大字段（image/content/description/variable），新增单项 `suspend fun getImage(origin, link)` 单行查询（单行远小于窗口，安全），列表项用 Glide 按需加载，**image 完整保留不裁剪**；详情页走 `get()/getByLink()` select * 单行重建，图不丢。
- **适用面**：任何含大字段（大数据 blob/base64/超长文本）的列表查询，一律主查询剔除 + 按需单行；不得置空、不得只截前 N 字符。
- **联动范围（本次已覆盖）**：`RssArticleDao.flowByOriginSort`、`RssStarDao.flowByGroup`（收藏），对应 5 个文章适配器 + 收藏适配器；使用方搜索技巧：`Grep "from rssArticles|from rssStars"` 于 data/dao。

### K2: Adapter 新增异步加载链的编译陷阱（Kotlin 连锁错误特征）
- `Coroutine.async { dao.getImage(...) }.onSuccess { }` 若文件**缺 import（appDb / Coroutine）**，错误不会报在 import 处，而会表现为**下游整链 "Cannot infer type for type parameter 'T'" / Unresolved apply/addListener/into 假象**——根源未解析时 lambda 无类型，连锁瘫痪。
- 排查手法：先核对新增符号的 import（appDb、Coroutine、RequestBuilder 等），再看报错行；`placeholder` 一律并入 `RequestOptions`，不要在 `apply(options)` 后裸链（lambda 作用域内解析不稳）。
- import 去重：Edit 增删 import 后必查重复同名 import（Conflicting import），重复 fqcn 也报错。

### K3: 复测协议（用户强制：禁止手动导航猜页面）
- F-UI-THEME 用例 verdict=**manual 属正常**（VL 判定型预期无规则可判），**步骤与证据真实执行**（截图/XML/logcat 照常收集），判定靠 `ui_visual_verify.py --evidence <report根>` 的 VL 聚合。
- 复测必须**按修复点精准选 TC**（如订阅链 → TC-113/052/051），不要全量跑、不要手动 adb 猜入口；`--tc` 单值，多用例逐个跑。
- 验收三要素：①用例步骤/证据齐全 ②VL 观察无新不合规 ③logcat 针对性问题计数=0（如 CursorWindow/SQLiteBlobTooBig）。