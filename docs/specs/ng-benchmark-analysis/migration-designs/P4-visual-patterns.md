# P4-visual-patterns — NG 视觉体系三模式融入 ui-standards（P5 期实施级设计）

> 上游依据：总设计 [design.md](../design.md) AD-05（只借三模式不引组件）+ [evidence-pack.md](../evidence-pack.md) G 节
> 本文件性质：**P5 产出=规范条款+组件设计，非代码迁移**；经检查点审查前不实施
> 精读输入：NG `ui/design/theme/NgThemeResolver.kt`、`NgThemeSnapshot.kt`、`ui/design/components/compose/NgVisualSurface.kt`；本项目 `docs/project-flow/ui-standards/*`、`ui-style-unify-deep-fix` spec、`ThemeStore.kt`/`ThemeUiPalette.kt`/`LegadoTheme.kt`

## 1 目标与非目标

**目标**：把 NG 视觉体系的三个架构模式本项目化，产出可审查、可执行的 ui-standards 新条款与组件接口设计：
1. 材质语义角色参数化（role→spec）→ 新增 `MaterialRole` 四角色 + 材质参数表条款
2. 单一材质调度点 + 优雅降级 → 新增 View/Compose 双栈统一入口 `MaterialSurface`
3. ThemeResolver 不可变快照 → 主题解析层收口 `ThemeStore` 直读链路，生成不可变 `ThemeSnapshot`

**非目标（不做清单）**：
- ❌ 液态玻璃/AGSL 效果：`NgLiquidGlassBackdrop`（GraphicsLayer 降饱和+RenderEffect+AGSL 折射+七通道色散）、`NgViewLiquidGlassRenderer` 全族不引入，性能代价高（总设计 §2.2.4），如未来单独立项再评估
- ❌ NG 组件代码搬运：`NgVisualSurface.kt` 及 ui/design 35 个 Compose/10 个 View 组件不搬，只吸收其架构模式
- ❌ 视觉体系切换开关：不引入 `NgVisualSystemStore`（TRANSPARENT_GLASS/LIQUID_GLASS 双视觉体系、SP key `ngVisualSystem.v1`）式的体系切换，本项目单一材质体系无切换面

## 2 NG 模式源码证据（文件:行）

> NG 根：`F:\myself\github\WeAgentChat\temp\legado_NG_src\legado_NG-main`，路径前缀 `app/src/main/java/io/legado/app/`

### 模式三：ThemeResolver 不可变快照
| 证据 | 位置 | 要点 |
|------|------|------|
| 解析层职责声明 | `ui/design/theme/NgThemeResolver.kt:46-50` | "只负责把旧主题状态解析为稳定语义；不读写偏好、不修复旧状态、不决定选哪个主题" |
| 唯一解析入口 | 同文件 :51-60 | `object NgThemeResolver.resolve(context): NgThemeSnapshot`，E-Ink 分支内收 |
| 旧四色输入契约 | 同文件 :36-44 | `NgLegacyThemeInput(primary/accent/background/bottom/error/isDark/isEInk)`——旧状态显式建模 |
| 四色→语义推导 | 同文件 :102-163 | `blend` 派生 primaryContainer(:111-115)/surfaceVariant(:116-120)/cardContainer 等，`contentColorFor` 定文字色 |
| 不可变快照结构 | `NgThemeSnapshot.kt:11-21` | isDark/isEInk/colors/shapes/spacing/typography/effects/motion/systemBars 九组 token 一次成型 |
| 语义色扩展槽 | 同文件 :23-56 | M3 34 槽 + `topBarContainer/onTopBar/cardContainer/dialogContainer/drawerContainer/inputContainer/selectedContainer` 7 个业务槽 |
| 特效 token 随快照 | 同文件 :89-97 | `NgEffectTokens(blurEnabled/containerAlpha/dialogAlpha/drawerAlpha/blurRadiusDp/…)`，E-Ink 全禁用 |
| 快照内联系统栏 | `NgThemeResolver.kt:370-396` | `darkStatusBarIcons = isLight(colors.background)`(:393)——系统栏图标随快照推导 |
| 色彩数学隔离 | 同文件 :404-484 | `NgColorMath`（opaque/withAlpha/blend/contentColorFor/isLight/contrastRatio）独立 object |

### 模式一：材质语义角色参数化
| 证据 | 位置 | 要点 |
|------|------|------|
| 角色枚举 | `ui/design/components/compose/NgVisualSurface.kt:30-42` | `NgMaterialRole` 11 值（NAVIGATION/TOP_NAVIGATION/BOTTOM_NAVIGATION/OVERLAY/INTERACTIVE/CONTROL/ICON_ACTION/ACTION/CONTENT/SETTINGS/SOFT_SURFACE） |
| 材质参数结构 | 同文件 :44-58 | `NgLiquidGlassSpec` 12 参数（blurRadius/refraction/surfaceAlphaScale/saturation/高光…） |
| role→spec 参数表 | 同文件 :60-145 | `NgLiquidGlassDefaults.spec(role)` when 全覆盖，每角色一组实测参数（如 BOTTOM_NAVIGATION :87-97） |

### 模式二：单一调度点 + 优雅降级
| 证据 | 位置 | 要点 |
|------|------|------|
| 调度组件契约 | 同文件 :195-200 | KDoc："按语义角色选择渲染后端；调用方仍负责页面结构；无 backdrop 时可靠回退，不伪造背景" |
| 调度主函数 | 同文件 :201-277 | `NgVisualSurface(role, cornerRadius, style, …)` 内部三分派 |
| 降级门 | 同文件 :216 | `supportsBackdropEffect = SDK_INT >= S`——API 级判断在组件内 |
| 回退分支 | 同文件 :222-236 | 无液态条件→`NgTransparentGlassSurface`；:254-276 按 backdrop 来源分 Compose/View 后端 |
| 快照消费 | 同文件 :217-219 | `NgTheme.visualSystem` + `snapshot.isEInk` 参与调度——快照与调度点联动 |
| 体系开关与主题分离 | evidence-pack G 节 | `NgVisualSystemStore` SP key `ngVisualSystem.v1` 与主题 key 分离（本设计不引入，见非目标） |

## 3 本项目现状与痛点

### 3.1 H9/H11 复述（取色基线铁证）
- **H9**（deep-fix design.md :70）：PreciseManageScreen L40 根背景用 `MaterialTheme.colorScheme.surface`，与主设置页 `palette.settings.page`（ThemeStore 背景色直读）明显偏色；SettingsCard/SettingsClickRow 5 文件 13 处同源 M3 派生色。根因（color.md §五）：M3 `surface = lerp(bg, neutral, 4~10%)` 是**派生偏移色**，不随用户自定义背景直读。
- **H11**（deep-fix design.md :72）：AutoTask/TxtTocRule/AllBookmark/Highlight/DictRule/RecycleBin 6 页列表项卡片 `Surface(color = colorScheme.surface)` → 归位 `palette.settings.row`。H9/H11 已修复，但**防回潮只靠 Grep 门禁（architecture.md §四），无架构层约束**。
- AD-06（deep-fix design.md :126-132）确立"取色唯一基线=AppSettingPalette 直读"；AD-07/:144 确立"组件单一来源"。

### 3.2 取色链路现状证据（三轨并存）
| 轨道 | 消费方式 | 证据 |
|------|---------|------|
| View 直读 | `ThemeStore.backgroundColor()` 等静态 getter 直读 SharedPreferences | `lib/theme/ThemeStore.kt:205-213(primaryColor)/:305-310(backgroundColor)`；实测 `ThemeStore.themeColors/backgroundColor/primaryColor` 直读 **22 处/9 文件**（BaseDialogFragment/MaterialValueHelper/gsyVideo 3 弹框/ThemeManageActivity/VideoSettingsPanel/LegadoTheme/HighlightStyleDialog/SwitchVideoAdapter） |
| Compose palette 直读 | 三入口各自 remember 各自推导 | `lib/theme/ThemeUiPalette.kt:102/118-149`（themeUiPalette/rememberThemeUiPalette/themeUiSignature）、`ui/widget/compose/AppSettingComponents.kt`（rememberAppSettingPalette）、`AppComposeDialogs.kt`（rememberAppDialogStyle） |
| M3 派生 | `ThemeSpec.toM3Scheme()` 每次重组重建 colorScheme | `ui/theme/LegadoTheme.kt:91-103`（5 核心色→34 槽位，仅兜底语义，页面/卡片级已被禁令封堵） |

**痛点结论**：①派生逻辑三处重复（toM3Scheme/palette divider 推导/AppSettingPalette 明暗推导），无单一解析点；②主题切换失效靠各入口独立 signature/监听，状态不一致窗口存在；③View 侧 22 处直读游离在规范外，是 H9 类偏色回潮的残余通道；④材质参数（透明度/blur/描边）散落在 TopBarConfig/UiCorner/dialogAlpha 等多处 key，无 role 级聚合，同族组件参数漂移无门禁可判。

## 4 三个模式的本项目化设计

### 4.1 模式一：材质语义角色参数化（MaterialRole）

**本项目化**：NG 11 角色收敛为 4 角色，一一映射本项目四大组件族（architecture.md §三）：

```kotlin
// lib/theme/MaterialTokens.kt（新增）
enum class MaterialRole { TOP_BAR, BOTTOM_BAR, ITEM_CARD, OVERLAY }
// TOP_BAR→顶栏族(MainTopBarView/GlassTopAppBar/AppManagementTopBar)
// BOTTOM_BAR→底栏族(底部导航/多选底栏/Tab 底)
// ITEM_CARD→列表项卡片族(AppManagementCard/SettingsCard/appSettingRowDecoration)
// OVERLAY→浮层族(AppDialogFrame/ModernActionPopup/BottomSheet/菜单面板)

@Immutable
data class MaterialSpec(
    val containerAlpha: Float,   // 容器面透明度
    val blurRadiusDp: Int,       // 仅 API31+ 且 effects.blurEnabled 时生效
    val strokeWidthDp: Dp,       // 描边宽
    val strokeAlpha: Float,      // 描边透明度
)
object MaterialDefaults { fun spec(role: MaterialRole): MaterialSpec }
```

**材质参数表（规范条款载体，初值=现有基线实测归集）**：
| Role | containerAlpha 来源 | blur 默认 | 描边 | 高度 |
|------|--------------------|-----------|------|------|
| TOP_BAR | `TopBarConfig.layoutAlpha`（顶栏管理，优先级最高） | `themeCardBackgroundBlur` 开启时 18dp | 无 | **不入 spec**：56dp(Main)/48dp(管理) 由组件族基线持有 |
| BOTTOM_BAR | `uiLayoutAlpha`（`themeMutedColor` 面之上） | 0 | 无 | 由组件族基线持有 |
| ITEM_CARD | 1.0f（`themeCardColor`/`palette.row` 直色面） | 0 | 1dp × `panelBorderAlpha` | 自适应 |
| OVERLAY | `dialogAlpha` 现有 key | `themeCardBackgroundBlur` 开启时 18dp | 1dp × `panelBorderAlpha` | 关联 `UiCorner.panelRadius` |

**ui-standards 新条款草案**（落地为 `docs/project-flow/ui-standards/material-roles.md`）：
1. 新增/改造 UI 面必须声明 `MaterialRole`；材质参数（透明度/blur/描边）只允许由 `MaterialDefaults.spec(role)` + `ThemeSnapshot.effects` 提供，禁止组件内自定 alpha/blur/描边组合。
2. 同 role 跨组件、跨 View/Compose 双栈材质必须一致；参数表调整只允许改 `MaterialDefaults` 与规范文档两处，并同步 updateLog。
3. **高度是结构 token 不是材质 token**：高度仍由四组件族基线（architecture.md §三）持有，禁止经 spec 传递，避免双源。
4. `MaterialSurface` 是材质承载层，**不替代四组件族形态选择**——门禁第 1-3 条（选哪个基线组件）仍先行，第 5 条取色检查扩展为"取色+材质"双检查。

### 4.2 模式二：单一材质调度点（MaterialSurface）

对齐本项目组件库组织（Compose 组件在 `ui/widget/components/`，View 侧主题设施在 `lib/theme/`）：

```kotlin
// ui/widget/components/MaterialSurface.kt（新增，Compose 唯一入口）
@Composable
fun MaterialSurface(
    modifier: Modifier = Modifier,
    role: MaterialRole,
    shape: Shape = RectangleShape,
    containerColor: Color? = null,   // 缺省由 ThemeSnapshot 按 role 解析对应面
    content: @Composable BoxScope.() -> Unit,
)
// 内部职责（对调用方不透明，仿 NgVisualSurface.kt:201-277 三分派）：
//   ① spec = MaterialDefaults.spec(role)
//   ② 色面 = containerColor ?: snapshot.colors 按 role 映射（TOP_BAR→topBar/BOTTOM_BAR→muted/ITEM_CARD→card/OVERLAY→dialog）
//   ③ 降级链：blur 仅当 SDK_INT>=31 && snapshot.effects.blurEnabled，否则只涂 alpha 容器色
//   ④ 描边/高度语义按 spec 应用

// lib/theme/MaterialSurfaceStyle.kt（新增，View 侧适配器）
object MaterialSurfaceStyle {
    fun resolve(context: Context, role: MaterialRole): ResolvedMaterial  // color/alpha/blur/stroke 一次解析
    fun apply(view: View, role: MaterialRole)                            // 供 MainTopBarView/BaseDialogFragment 迁移期接入
}
```

**降级链规范**（条款 3 补充）：`SDK_INT` 分支、低端机判定全部封装在两个组件内部；业务代码出现 `Build.VERSION.SDK_INT` 参与材质分支 → 审查拒绝（对齐 NG "API 级判断不出库"模式，NgVisualSurface.kt:216 证据）。

### 4.3 模式三：主题解析层与不可变快照（ThemeSnapshot）

```kotlin
// lib/theme/ThemeSnapshot.kt（新增）
@Immutable
data class ThemeSnapshot(
    val isDark: Boolean,
    val isEInkMode: Boolean,            // 沿用 AppConfig.isEInkMode（本项目已有，BaseDialogFragment.kt:45/ThemeUiPalette.kt:182 在用）
    val colors: ThemeColorSnapshot,     // page/row/topBar/bottomBar/card/muted/overlay/input/divider/primary/accent/textPrimary/textSecondary…
    val effects: ThemeEffectTokens,     // blurEnabled/containerAlpha/dialogAlpha/drawerAlpha（对齐 NgEffectTokens，NgThemeSnapshot.kt:89-97）
    val shapes: ThemeShapeTokens,       // panelRadiusPx/actionRadiusPx（UiCorner 现值收编）
)

// lib/theme/ThemeSnapshotResolver.kt（新增，对齐 NgThemeResolver.kt:46-50 职责边界）
object ThemeSnapshotResolver {
    /** 只读旧状态→解析为稳定语义；不读写偏好、不决定主题选择 */
    fun resolve(context: Context): ThemeSnapshot
    /** signature 短路：未变化直接返回 current（复用 themeUiSignature，ThemeUiPalette.kt:149/:182 已含 mode|night|eInk|themeStore） */
    fun resolveIfChanged(context: Context, current: ThemeSnapshot?): ThemeSnapshot
}

// Compose 消费（ui/theme/LegadoTheme.kt 内 provide）
val LocalThemeSnapshot: ThemeSnapshot   // staticCompositionLocalOf
@Composable fun rememberThemeSnapshot(): ThemeSnapshot
```

**收口路径**：
1. `LegadoTheme.kt` 组合根处 `resolveIfChanged` 一次解析 → CompositionLocal 下发（替代"每个 palette 入口各自 remember 各自推导"）。
2. `rememberAppSettingPalette()` / `rememberThemeUiPalette()` / `rememberAppDialogStyle()` **公共 API 不变**，内部实现改为读 `LocalThemeSnapshot`（等价替换，字段语义=现有直读语义，不引入 M3 lerp）——Phase1 归位成果零回退。
3. View 侧 22 处 `ThemeStore` 直读**不强制一次性清零**：高频场景（View 弹框/顶栏）迁移期经 `MaterialSurfaceStyle.resolve()` 收敛，低频遗留登记豁免；`ThemeStore` 静态 getter 保留为底层能力（color.md §四"低层能力"定位一致）。
4. 解析规则归集：四色 blend 派生（对齐 NgThemeResolver.kt:102-163 模式，用现有 `ThemeSpec.toM3Scheme` 的推导系数）、divider 明暗推导、contentColorFor（新增 `ThemeColorMath`，对齐 NgColorMath.kt:404-484）全部**只在 Resolver 内出现一次**。

### 4.4 落地位置汇总

| 产物 | 位置 | 类型 |
|------|------|------|
| MaterialRole/MaterialSpec/MaterialDefaults | `lib/theme/MaterialTokens.kt` | 新增 |
| ThemeSnapshot/ThemeEffectTokens/ThemeShapeTokens | `lib/theme/ThemeSnapshot.kt` | 新增 |
| ThemeSnapshotResolver/ThemeColorMath | `lib/theme/ThemeSnapshotResolver.kt` | 新增 |
| MaterialSurface（Compose） | `ui/widget/components/MaterialSurface.kt` | 新增 |
| MaterialSurfaceStyle（View） | `lib/theme/MaterialSurfaceStyle.kt` | 新增 |
| 快照下发 | `ui/theme/LegadoTheme.kt` | 修改 |
| palette 三入口内部换源 | `ui/widget/compose/AppSettingComponents.kt`、`AppComposeDialogs.kt`、`lib/theme/ThemeUiPalette.kt` | 修改（API 不变） |

## 5 与 ui-style-unify-deep-fix 的衔接

**顺序**（不与 S 批/Phase1 冲突）：
1. **前置（已完成）**：Phase1 取色源统一（H8/H9/H10）+ H11 归位——直色基线语义已确立，本设计的快照 `colors` 字段语义与其完全一致，等价收编。
2. **本设计实施窗口**：Phase2 收尾（H12/H13/H14 残余）之后、Phase4 门禁固化之前。Phase2 在改的文件（GlassTopAppBar/Debug 页/角色系列页）不触碰 `lib/theme/ThemeSnapshot*` 新文件，无冲突。
3. **本设计落地同时**：Phase4 门禁条款由"仅 M3 surface 禁令"扩展为"M3 surface 禁令 + MaterialRole 声明 + MaterialSurface 取材质"，一次合并进 architecture.md §四 checklist。
4. **S 批（S1-S6 订阅切换）**：改动集中在 `RssFragment.kt`，与本设计零文件交集，可并行。

**冲突点与规避**：
- `AppSettingComponents.kt`/`AppComposeDialogs.kt` 内部换源 vs Phase3 D1/D3 弹框迁移同文件 → **文件级串行**：palette 换源在 D 批当前迁移子项合入后进行（同文件 Edit 串行化铁律）。
- architecture.md 双 spec 同改 → 本设计落地时与 Phase4 合并为一次文档提交，避免两处门禁文案漂移。
- `ThemeUiPalette.kt` 内部换源会触碰 `themeUiSignature()` → 签名算法保持不变（快照失效直接复用），仅消费路径切换。

**先后依赖**：快照层依赖 H9/H11 已确立的"palette 直读语义"作为 `colors` 字段权威定义；Phase4 门禁依赖本设计的 `MaterialRole` 条款先行合入。

## 6 文件变更映射表

| # | 文件 | 变更类型 | 内容 |
|---|------|---------|------|
| 1 | `docs/project-flow/ui-standards/material-roles.md` | 新增 | 材质语义角色条款全文（§4.1 草案）+ 参数表 |
| 2 | `docs/project-flow/ui-standards/architecture.md` | 修改 | §二取色链路图加快照层；§四门禁第 5 条扩展"取色+材质"双检查 |
| 3 | `docs/project-flow/ui-standards/color.md` | 修改 | §四主取色链补"快照为唯一解析点"行；§五禁令补 MaterialSurface 正例 |
| 4 | `docs/project-flow/ui-standards/components.md` | 修改 | 登记 MaterialSurface/MaterialTokens/ThemeSnapshot（基线状态） |
| 5 | `lib/theme/MaterialTokens.kt` | 新增 | MaterialRole/MaterialSpec/MaterialDefaults |
| 6 | `lib/theme/ThemeSnapshot.kt` | 新增 | ThemeSnapshot + 三组 token |
| 7 | `lib/theme/ThemeSnapshotResolver.kt` | 新增 | resolve/resolveIfChanged + ThemeColorMath |
| 8 | `ui/widget/components/MaterialSurface.kt` | 新增 | Compose 调度组件（含降级链） |
| 9 | `lib/theme/MaterialSurfaceStyle.kt` | 新增 | View 侧适配器 |
| 10 | `ui/theme/LegadoTheme.kt` | 修改 | 快照 resolve+provide |
| 11 | `AppSettingComponents.kt`/`AppComposeDialogs.kt`/`ThemeUiPalette.kt` | 修改 | 内部换源读快照，公共 API 不变 |
| 12 | `app/src/main/assets/updateLog.md` | 修改 | 面向用户语言（主题一致性加固，无可见新功能也需按规范同步） |

## 7 风险清单

| # | 风险 | 等级 | 缓解 |
|---|------|------|------|
| R1 | **与现有门禁冲突**：新组件被误判为"自造组件形态"违反铁律 3 | 高 | 条款明文：MaterialSurface 是材质承载层非形态基线，四组件族选择门禁（checklist 1-3）仍先行；审查 checklist 给出可判定区分标准（§8） |
| R2 | **快照层性能**：resolve 全量推导+CompositionLocal 误用导致高频重算 | 中 | signature 短路（复用 themeUiSignature）+ 组合根单次解析；resolve 为纯内存/SP 读操作；条款禁止非 @Composable 上下文调用 rememberThemeSnapshot；L2 验证含帧率抽查 |
| R3 | **迁移期双轨并存**：22 处 View 直读遗留与快照轨并存，主题切换瞬时窗不一致 | 中 | palette 公共 API 不变内部换源（等价替换零视觉 diff）；View 侧经 MaterialSurfaceStyle 分批收敛；低频遗留登记豁免清单，不设无限期 |
| R4 | blur 低端机性能回归 | 低 | 双闸门：API>=31 且 `themeCardBackgroundBlur` 用户开关；降级链封装组件内 |
| R5 | TOP_BAR 透明度与 H13 顶栏壁纸（TopBarConfig）叠加冲突 | 中 | 参数表明文优先级：TopBarConfig.layoutAlpha 唯一权威，spec 的 TOP_BAR alpha 不另设来源 |
| R6 | 规范条款与 how-to.md 样板不同步 | 低 | 落地时 how-to.md 补 MaterialSurface 用法小节（计入 #2 文档变更） |

## 8 验证方案

**V1 规范可执行性（审查 checklist 可判定）**：
- Grep `MaterialTheme\.colorScheme\.(surface|surfaceVariant)` 新增 → 拒（既有门禁，保留）
- Grep `Build\.VERSION\.SDK_INT` 出现在 UI 组件且参与材质/背景分支 → 拒（降级不出库判定）
- Grep `withAlpha|graphicsLayer.*alpha|blur\(` 出现在四族组件内且非 MaterialDefaults 来源 → 拒（材质参数外流判定）
- 新增 Compose UI 面未声明 `role = MaterialRole.*` → 拒
- 区分标准：形态审查看"是否四族基线组件"（checklist 1-3），材质审查看"role 是否声明+参数是否出自 spec"（本条款），两问互不替代

**V2 快照层等价性 L2 截图对比**：
- 场景×4：主题设置页 / 书源管理页（AppManagementCard）/ 确认弹框（AppDialogFrame）/ 三点菜单（ModernActionPopup）
- 主题×2：日间 + 夜间；另加"自定义背景色+卡片色 key"一轮（对齐 H9 触发条件）
- 判定：palette 换源提交前后同场景截图像素 diff = 0（等价替换铁证）；快照失效正确性：切换 themeMode/背景色 key 后截图随动
- 降级链：API<31 模拟器跑一轮，验证 blur 关闭仅剩 alpha 容器（不出库验证）
- 工具：`ai_tests/venv/Scripts/python.exe` + `ai_tests/scripts/` 截图脚本，禁入 `temp/`

**V3 解析层单测（可选）**：`ThemeSnapshotResolver.resolve` 幂等 + signature 变化重算（Robolectric 或抽纯函数 `ThemeColorMath` 做 JVM 单测）

## 9 工作量估算

| 项 | 估算 |
|----|------|
| 规范条款（material-roles.md + 三文档同步 + how-to） | 0.5 人日 |
| MaterialTokens + ThemeSnapshot + Resolver + ColorMath | 1 人日 |
| MaterialSurface（Compose，含降级链） | 1 人日 |
| MaterialSurfaceStyle（View）+ 1-2 个高频点试点接入 | 0.5-1 人日 |
| palette 三入口内部换源 + 编译回归 | 1-1.5 人日 |
| L2 截图对比回归（V2 全矩阵） | 0.5 人日 |
| **合计** | **4.5-5.5 人日**（设计已含本文件，不含 Phase4 门禁合并的公共成本） |

## 10 设计决策记录

| # | 决策 | Context / Tradeoff |
|---|------|-------------------|
| AD-P4-1 | **只借模式不搬代码**（继承总设计 AD-05） | NG ui/design 是完整设计系统且液态玻璃成本自证；吸收 role→spec/调度点/快照三模式为规范+组件设计。Tradeoff：无玻璃视觉效果短期交付（接受） |
| AD-P4-2 | **MaterialRole 收敛 4 角色，高度不入 spec** | NG 11 角色对应其组件粒度；本项目四大组件族是既定基线，角色=组件族一一映射最可判定；高度是结构 token 已由组件族持有，双源必漂移。Tradeoff：浮层子类（菜单 vs 弹框）参数趋同（接受，参数表可登记微调） |
| AD-P4-3 | **快照层不改 palette 公共 API，内部换源** | H9/H11 归位成果以 `palette.settings.page/row` 为锚点，改 API 会波及全部已归位页。等价替换=零回归面。Tradeoff：palette 与快照双层暂存（接受，signature 复用保证一致） |
| AD-P4-4 | **降级链封装组件内，API 判断不出库** | 对齐 NgVisualSurface.kt:216 证据模式；业务代码 SDK 分支是历史分裂根源之一。Tradeoff：组件内复杂度略增（接受） |
| AD-P4-5 | **不做液态玻璃/体系切换开关**（非目标固化） | 单一材质体系无切换面；若未来立项液态玻璃，参考 NG "视觉体系 SP key 与主题 key 分离"（NgVisualSystemStore）模式重设计，本设计条款不预留双体系接口 |
| AD-P4-6 | **View 侧 22 处直读不强制清零** | 一次性清零=大爆炸迁移违反分期收口（总设计 §0.3）；分批收敛+豁免登记对齐 D1 弹框迁移先例。Tradeoff：双轨过渡期存在（接受，R3 缓解） |
