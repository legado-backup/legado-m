# Spec：亮色主题文字对比度系统性修复

> **状态**：🔄 设计中 ｜ **创建日期**：2026-08-31
> **关联文档**：[README.md](./README.md) ｜ [design.md](./design.md) ｜ [tasks.md](./tasks.md)

## Intent

用户设置内置亮色主题（默认/典雅蓝/绿意/莫兰迪/海洋/薰衣草/琥珀/护眼绿/护眼黄/牛皮纸，特征=浅色背景+深色 primary）后，很多区域字体或组件肉眼不可见。本 spec 修复这一系统性对比度缺陷：让文字颜色由**实际绘制表面的亮度**派生，而非由 primary 色亮度冒充的"主题深浅"误判派生，使所有内置主题（含夜间、e-ink）下文字均清晰可见。

三条根因（全部有源码铁证，详见 design.md）：

- **根因1（机制性，主因）**：`MaterialValueHelper.kt` L131-132 `isDarkTheme = isColorLight(ThemeStore.primaryColor)` 语义错位；L22-28 `getPrimaryTextColor(dark)` 的资源映射使亮色主题解析出白色主文字，画在 `backgroundColor=#F5F5F5` 浅底上不可见。夜间主题 primary 深+背景深，白字碰巧正确（负负得正），历史上从未暴露。消费面 204 处 / 50 文件。
- **根因2（结构性）**：`ThemeConfig.applyTheme()`（L1045-1101）三分支只写 `textColorPrimary`，从不写 `KEY_TEXT_COLOR_SECONDARY`；fallback 到 `android.R.attr.textColorSecondary`（View 主题 attr，切主题不重建时可能解析旧值），进入 M3 `onSurfaceVariant` 与弹窗 secondaryText。Compose 兜底 `withContrastGuard` 阈值 1.3 过低（WCAG 要求 4.5）且仅覆盖三个槽位。
- **根因3（点状但多处）**：浅底+硬编码亮前景——书架未读角标（`mutedColor` 亮底 + `Color.White` 字，对比度≈1.16）、封面角标白字无遮罩、渐变占位白 tint、`LegadoMiuixComponents` 的 `onAccent: Color = Color.White` 默认值、styles.xml 视频控制按钮黑字配固定黑面板。

## Scope

### 做什么（In Scope）

1. `MaterialValueHelper.kt` 以学习源 Archive（`archive-ref/legado-08172114`）同名文件为基线逐行对齐：`isDarkTheme`/`primaryTextColor`/`secondaryTextColor`/两个 disabled 变体/`buttonDisabledColor` + Fragment 扩展全部采用 Archive 修正版实现（自定义字色优先+按主题模式派生），本项目自有演进不回退。
2. `ThemeConfig.applyTheme()` 三分支补写 `textColorSecondary`（亮色 #8A000000 系 / 夜间 #B3FFFFFF 系，或主文字色降 alpha 的 Material secondary 档），消除 View attr fallback 不可控。
3. 根因3 全量点位修复（21 处 = 已知 6 处 + 第三轮地毯扫描净增 15 处，明细见 design.md 根因3 两表），accent 白字家族统一收敛 `onAccentFor` 工具。
4. Compose guard 增强：`ThemeSpec.kt` `MIN_FONT_SURFACE_CONTRAST` 1.3→3.0，覆盖槽位扩展到 `onPrimary`/`onSecondary`/`onErrorContainer`。
5. Compose 自创层槽位治理（根因4，AD-06）：`inversePrimary`/`onErrorContainer`/`surfaceContainer` 族/`outline` 族四类缺陷派生修正 + guard 压平 alpha 校验缺陷修复。
6. 204 处消费点**零改动**（深挖实锤消费层写法与 Archive 逐行一致，源头对齐后全链自动修复）；修复后 Grep 复核属性引用 + 真机逐屏走查兜底，发现 primary 表面等异常点位时用 `onPrimarySurfaceTextColor` 定点处理。
7. `updateLog.md` 编译前更新（版本交付同步强制规则）。

### 不做什么（Out of Scope）

- 不重构 `ThemeStore` / `ThemeConfig` 的主题存储与切换机制本身（仅补写 secondary 写入）。
- 不调整各内置主题的配色取值（palette 本身不改，只修文字色派生逻辑）。
- 不引入第三方对比度计算库（`ColorUtils.isColorLight` 已满足需求）。
- 不处理用户书源自定义 CSS/JS 注入的文字色（仅修应用内 UI）。
- 不在本 spec 内覆盖阅读器界面文字色（阅读界面有独立的文字色体系与用户自定义字体色，仅验证 S7 不被破坏）。
- 不改夜间主题既有视觉表现（夜间全场景回归仅保证零回归，不做视觉优化）。

## Approach

### Selected Approach（选定方案与理由）

**对齐 Archive 修正版取色派生（Archive-aligned text color）**——以学习源 `archive-ref/legado-08172114` 的 MaterialValueHelper.kt 为基线逐行对齐：

- `isDarkTheme = AppConfig.isNightTheme`（正确主题模式语义，Archive L171-172）
- `primaryTextColor = 用户自定义字色优先 ?: defaultThemeTextColor(isNightTheme)`（Archive L85-87）
- `secondaryTextColor = 主字色 alpha 0.72 派生`（Archive L96-99）
- disabled 变体按 `!isNightTheme` 取反（Archive L101-105）
- 本项目自有演进（e-ink 背景图分支/UiCorner 弹窗底）不回退；新增 `onPrimarySurfaceTextColor` 承接真正画在 primary 表面的少数消费点。

**理由**：①该实现在 Archive 已经过大规模生产验证，风险远低于自创方案；②直接回答"学到精髓"——补齐迁移时漏搬的下层取色修正；③与本项目已搬的 sanitize 防护体系（配置链）形成完整双层防护，对齐 Archive 的原设计意图；④改动集中单文件+甄别点修，夜间/e-ink 行为由 Archive 语义保证正确。

### Alternatives Considered（否决的替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| 方案A：仅改 `isDarkTheme = AppConfig.isNightTheme`（无配套） | 只改判定源一行，不动派生链 | 无自定义字色优先与 secondary 一致派生配套；primary 表面消费点（Toolbar 白字）无专用属性承接，逐点裸改风险高。其正确形态已被 Archive 证明必须与派生链配套——即本选定方案 |
| 方案A'：自创"背景表面亮度派生"（`backgroundColorBasedTextDark`） | 按实际绘制表面亮度选字色 | 语义更细但无生产验证；与 Archive 已验证实现偏离，引入自行维护的第三套语义。已由 Archive-aligned 方案替代（检查点1 用户质询后修订） |
| 方案B：维持现状仅修点状硬编码 | 只修根因3 点位 | 204 处机制性错位不解决，用户"很多区域"的系统性问题依旧 |
| 方案C：每个消费点单独写对比度计算 | 204 处逐一内联 `isColorLight` 计算 | 冗余且易漏，无单点收敛，后续新增消费点会继续犯错；应收敛到 `MaterialValueHelper` 单点派生 |

### Drawbacks（已知缺点）

- 修复面集中在源头单文件，但语义变化全局生效（204 处消费点色值来源全部切换），夜间/e-ink 需全场景回归防意外翻转。
- 改 `textColorSecondary` 写入时机影响所有弹窗/菜单次要文字，夜间模式需全场景回归防"修亮色坏夜间"。
- e-ink/护眼模式等特殊分支需单独验证，修复必须保持其碰巧正确的现状。
- 真机逐屏走查无法 100% 覆盖所有页面组合，存在残余漏判风险（issues-found.md 闭环兜底）。
- git 考古证明 `3c8aa5c7b` 迁移时曾裁剪范围，本次对齐若 Archive 后续版本演进，需另行同步（登记 forks-reference 观察项）。

### Prior Art（既有正确参照）

- **Archive MaterialValueHelper.kt（`archive-ref/legado-08172114`）**：本次修复的直接蓝本。Archive 已修复 `isDarkTheme=AppConfig.isNightTheme`（L171-172）、`primaryTextColor=自定义?:按主题模式派生`（L85-87）、`secondaryTextColor=主字色 alpha 0.72 派生`（L96-99）、disabled 按 `!isNightTheme` 取反（L101-105），经其大规模用户生产验证。本项目迁移时部分拷贝（尾部工具函数一致，核心属性漏搬），本次补齐。
- `AppComposeDialogs.kt` L147 / `AppSettingComponents.kt` L153：`if (isColorLight(accent)) 黑 else 白`——按实际表面亮度选字色的既有正确模式，本次根因3 点位修复推广该模式。
- `ThemeConfig.isDarkTheme()`（L100-102）：`getTheme() == Theme.Dark` 的正确语义判定，可作修复参照。
- Phonograph 溯源：`isDarkTheme` 按 primary 亮度判定的旧语义来自 Phonograph（`@author kabouzeid`），其原场景文字画在 primary 色 Toolbar 表面上（primary 深→白字正确）；legado 原版上游保留该旧语义，Archive 修正了它，本项目当时未同步。

## Requirements

1. `MaterialValueHelper.kt` 以学习源 Archive（`archive-ref/legado-08172114`）同名文件为基线逐行对齐：`isDarkTheme = AppConfig.isNightTheme`；`primaryTextColor = 用户自定义字色(uiFontColor)优先 ?: defaultThemeTextColor(isNightTheme)`；`secondaryTextColor = 主字色 alpha 0.72 派生`；`primaryDisabledTextColor/secondaryDisabledTextColor` 按 `!isNightTheme` 取反；`buttonDisabledColor` 按 `isNightTheme`；Fragment 扩展同步。本项目自有演进（e-ink 背景图分支/UiCorner 弹窗底）不回退。
2. 新增 `onPrimarySurfaceTextColor`（本项目扩展）供真正画在 primary 表面上的少数消费点使用（= `getPrimaryTextColor(!isColorLight(primaryColor))` 保持原逻辑）。
3. `ThemeConfig.applyTheme()` 三个分支均补写 `textColorSecondary`（亮色 #8A000000 系 / 夜间 #B3FFFFFF 系或主文字色降 alpha 的 Material secondary 档），覆盖 e-ink 分支且不得破坏其白底黑字表现。
4. 根因3 全量点位修复（21 处）：已知 6 处（BookshelfScreen.kt L825-830/L521-528、BookshelfItems.kt L111、BookshelfComposeItems.kt L185、LegadoMiuixComponents.kt L106、styles.xml L192/L205）+ 净增 15 处（activity_manga.xml L58、ClickActionConfigDialog.kt L221-244/L296-308、accent 白字家族 8 处换 `onAccentFor`、BookInfo hero 区遮罩、EpubReadView loading 遮罩、activity_rss_artivles.xml 死属性清理），明细见 design.md。
5. `ThemeSpec.kt` `MIN_FONT_SURFACE_CONTRAST` 从 1.3 提升至 3.0，guard 覆盖槽位扩展到 `onPrimary`/`onSecondary`/`onErrorContainer`（防止未来回归）。
6. Compose 自创层四类槽位缺陷修正（ThemeSpec.kt）：`inversePrimary` 按 inverseSurface 亮度派生；`onErrorContainer` 改 contrastOn 模式；`surfaceContainer` 族亮色 lerp 幅度提升（夜间不动）；`outline` 族亮色 lerp 0.12→0.22（夜间不动）；guard 对半透明前景先合成底色再校验。
7. 消费层零改动原则：204 处消费点保持与 Archive 逐行一致，不做逐点甄别与批量替换；修复后通过 Grep 复核 + 真机逐屏走查（亮色主题十套+夜间+e-ink）兜底，异常点位二轮定点补修并归档 issues-found.md；`SourceFolderAdapter` ripple 点（isDarkTheme 唯一非文字消费）纳入回归观察。
8. 修复边界：只动 MaterialValueHelper 的 `isDarkTheme`；`ThemeConfig.isDarkTheme()` 体系 4 处消费点禁止顺手改动（EInk 语义回归防线）。
9. 用户自定义字体色（阅读界面等）优先级不被本修复覆盖，仍优先生效。
10. 夜间主题、e-ink 模式、护眼模式全场景零回归（保持负负得正的碰巧行为不翻转）。
11. 编译前更新 `app/src/main/assets/updateLog.md`（追加在 `## cronet版本:` 之后、已有条目之前，面向用户语言）。
12. 构建后执行 daemon 清场（`stop-daemons.bat`），遵守强制门禁。

## Scenarios

### S1：内置默认亮色主题（primary 深）主界面文字可见

- **Given**：应用已设置内置默认亮色主题（primary=#795548 深，backgroundColor=#F5F5F5 浅）
- **When**：进入主界面（书架/发现/我的 tab、顶栏搜索入口、标签栏、全局 label）
- **Then**：主文字/次要文字均为深色（黑系），在浅色背景上对比度满足可读要求（WCAG ≥4.5），无白字浅底不可见区域

### S2：典雅蓝等浅 primary 亮色主题

- **Given**：应用已设置典雅蓝（或绿意/莫兰迪/海洋/薰衣草/琥珀/护眼绿/护眼黄/牛皮纸）等浅 primary 亮色主题
- **When**：进入主界面与各二级页面
- **Then**：文字按背景表面亮度选色（浅背景→深色字），不因 primary 亮度判定翻转而出现错误字色

### S3：切回夜间主题全功能不回归

- **Given**：从任一亮色主题切换回夜间主题
- **When**：遍历主界面、二级页面、弹窗、菜单
- **Then**：文字颜色保持夜间既有正确表现（深底浅字），弹窗/菜单次要文字正常，无"修亮色坏夜间"

### S4：e-ink 模式不回归

- **Given**：应用处于 e-ink 模式（primary=WHITE）
- **When**：进入主界面与阅读相关页面
- **Then**：保持白底黑字表现不变，判定链路（primary 亮→文字深色）不被重构翻转

### S5：弹窗/菜单在两种模式下文字可见

- **Given**：分别在亮色主题与夜间主题下
- **When**：打开任意 Compose 弹窗（AppComposeDialogs）与 View 菜单/对话框，观察主文字与次要文字
- **Then**：主文字由 `textColorPrimary`、次要文字由 `applyTheme()` 显式写入的 `textColorSecondary` 决定，不再依赖不可控 View attr fallback；两种模式下主/次文字均清晰可见且层级分明

### S6：书架角标/视频面板等根因3 点位

- **Given**：亮色主题下，书架存在未读更新书籍（hasNew=false 角标场景）、封面占位渐变，播放器处于视频控制面板
- **When**：查看书架未读角标、封面角标/占位、视频控制按钮
- **Then**：未读角标文字按 mutedColor 实际亮度选黑/白（亮底→深色字）；封面角标与占位文字有遮罩或按底色选色保证可见；视频控制按钮在固定黑面板上显示亮色字（与主题模式解耦）

### S7：用户自定义字体色仍优先生效

- **Given**：用户在阅读界面设置了自定义字体颜色
- **When**：切换亮色/夜间主题后进入阅读界面
- **Then**：阅读界面文字使用用户自定义颜色，不被本修复的派生文字色覆盖

### S8：Compose 弹框表面层级与描边可见（根因4）

- **Given**：亮色主题与夜间主题下分别打开 Compose 弹框/底部面板/输入框（surfaceContainer 族/outline 消费场景），并在夜间浅主色主题（如暗夜紫）下触发 inversePrimary 消费场景
- **When**：观察弹框与页面背景的层级区分、输入框描边、错误容器文字、inversePrimary 元素
- **Then**：弹框表面与背景层级可辨（不再同色观感）；输入框描边可见；onErrorContainer 上文字达标；inversePrimary 在 inverseSurface 上可读（夜间 1.05:1 必然不可见问题消除）

### S9：isDarkTheme 修复边界不回归

- **Given**：修复只改 MaterialValueHelper 的 `isDarkTheme` 定义
- **When**：验证 ChangeThemeDialog/CodeEditActivity（ThemeConfig.isDarkTheme() 体系）与 SourceFolderAdapter（唯一非文字消费点，ripple）
- **Then**：前者行为零变化；后者按压水波纹反馈在亮/夜两模式下方向合理且可见
