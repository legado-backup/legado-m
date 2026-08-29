# §9.7 主题体系架构总纲（Theme Architecture）— 三大体系 + 红线禁令

> 来源：Archive 参考快照（`archive-ref/legado-08172114/`）主题体系深度分析（2026-08-28，分析底稿 `docs/temp-analysis/theme-arch-1-mode.md` / `-2-theme.md` / `-3-setting.md` / `theme-arch-gap-matrix.md`）。
> **定位**：`color.md` 讲"UI 取什么色"，本文讲"主题体系怎么运转、哪些架构约束不可破坏"。**改任何主题/模式/换肤相关代码前必读**；触犯红线 = 架构回退，代码审查驳回。

## 一、三大体系全景

| 体系 | 单一真源 | 核心链路 | 关键文件 |
|------|---------|---------|---------|
| **主题模式**（日/夜切换） | `themeMode` pref 字符串 | 纯函数派生 `isNightTheme()` → `applyDayNight` 一次性下发 AppCompat nightMode + `RECREATE` 事件 + `ThemeSync.bump()` → View 侧 style+令牌懒刷新 / Compose 侧签名重组 | `ThemeConfig.applyDayNight`、`App.initNightMode`、`ThemeStore` |
| **应用主题**（动态换色/主题包） | `ThemeStore` 运行时库 + `cPrimary/cNPrimary` 日夜持久板 | 换色路径全部收敛 `applyConfig → applyTheme → ThemeStore` 单点 → 打 `VALUES_CHANGED` 时间戳令牌 → View onResume 懒比对 / Compose prefs 监听重算 palette | `lib/theme/ThemeStore.kt`、`ThemeUiPalette.kt`、`ThemeRuntimeKeys.kt`、`ThemePackageManager.kt` |
| **主题设置**（配置页交互） | `ThemeConfig.Config` 业务态 → PreferKey 模式成对键持久层 | 写 prefs → 刷 ThemeStore → `RECREATE` 双事件收尾；预览与生效同源（唯一 Config 既持久化又 applyConfig） | `ui/config/ThemeConfigFragment.kt`、`ThemeManageActivity.kt`、`ComposeSettingFragment` |

## 二、设计精髓十条（AI 必须内化的架构事实）

1. **单一真源，即时派生**：模式只有 `themeMode` 一份状态，`isNightTheme`/Theme 全部即时推导；`sysConfiguration` 用 `Resources.getSystem()` 避开包装上下文固定陷阱。
2. **pref 只存原始值，派生色运行时算**：`primaryColorDark` 自动 darken、divider 依表面明暗派生——禁止把派生色持久化。
3. **单一变更令牌**：`ThemeStore.VALUES_CHANGED` 时间戳是唯一失效源，View 懒比对与 Compose 监听共享同一令牌；`ThemeSync.bump()`（OURS v2 新增）是 Compose 后台页重组信号，唯一写点在 `ThemeConfig.applyTheme` 末尾。
4. **双事件原子收尾**：主题/背景/模式变更统一 `RECREATE` 事件 + `ThemeSync.bump` 收尾；冷启动走 init 路径不广播。禁止自造第三种刷新通道。
5. **日夜键物理拆分**：17 组 `N` 后缀成对键 = 配置即快照；逻辑 key 一律经 `ThemeRuntimeKeys` 工厂路由（含 legacy 迁移兜底），禁止手写字符串 key。
6. **双栈统一出口**：View 体系走 `ThemeStore` 直读 + style 应用；Compose 体系走 `LegadoTheme → rememberThemeUiPalette`（bump/令牌驱动重组）。两栈禁止互相取色。
7. **主题包 = 自包含目录事务**：theme.json manifest（≤512KB）+ 前缀化资产，安装走 staging→backup→rollback，防路径逃逸；应用经 `ThemePackageManager.apply → ThemeConfig.applyConfig` 单点。
8. **写后即刷 + 预览同源**：设置页唯一 Config 既持久化又 applyConfig，卡片预览直接读包内 config（Glide ObjectKey 签名保缓存失效）。
9. **ComposeSettingFragment 声明式**：SharedPreferences 监听自动回调 `onSettingPreferenceChanged(key)`，设置页只声明 key→副作用映射，零硬编码取色。
10. **recreate 换绝对一致**：`recreateOnThemeChange=false` 豁免是 v2 特性——豁免页必须自带兜底（ThemeSync 订阅 或 `setupSystemBar`/`upBackgroundImage`），否则改主题后残留旧色。

## 三、红线禁令（触犯 = 架构回退）

1. **禁止绕过 `isNightTheme()` 自判夜间**：业务代码不得直接读系统 `uiMode`/`isNightMode` 做分支——跟随系统/手动/Auto 三种模式语义在 `themeMode` 派生函数里。
2. **禁止绕过 `ThemeConfig.applyTheme` 直写换色**：直接写 `ThemeStore` 或 pref 不经 applyTheme = 不打令牌不 bump = 双栈部分刷新（半残换肤）。
3. **禁止自建刷新通道**：主题变更不得新发明 broadcast/回调/手动 recreate 链——统一走双事件；`MAIN_THEME_BACKGROUND_CHANGED` 已是死事件（4 发送 0 订阅），禁新增订阅，待 T6 清理。
4. **禁止 Compose 侧自建 colorScheme / M3 派生色取色**：必须经 `LegadoTheme` palette（见 `color.md` M3 派生色禁令）。
5. **豁免页红线**：新增 `recreateOnThemeChange=false` 豁免页必须同步实现 ThemeSync 订阅或 `setupSystemBar`/`upBackgroundImage` 兜底，并登记到 issue-list（反例：T3 AudioPlayActivity 无兜底残留旧色）。
6. **禁止手写日夜成对键字符串**：一律 `ThemeRuntimeKeys` 工厂。
7. **跟随系统链路改动门禁**：`App.kt` `CONFIG_UI_MODE` 处理是已知薄弱点（T1：缺 NIGHT_MASK 过滤 + 防抖），改动前必读 `theme-arch-gap-matrix.md` R1；禁止再简化（如删除 AppearanceKit 套用点）。

## 四、已知偏差与修复指针（OURS vs Archive）

**双向审计口径**（2026-08-28 用户裁决）：漏跟 Archive 进化的（T4 类）= 对齐修复；OURS 进化实现落差（T7-T12 类，如豁免宣称未实现/事件双消费）= 修落差不推翻进化；有意的 v2 进化（ThemeSync/豁免机制/wrap/外观套件）= 保留禁止回退。

偏差矩阵全文：`docs/temp-analysis/theme-arch-gap-matrix.md` + 进化审计 `theme-evolution-audit-mechanism.md`/`-data.md`；问题条目：`docs/specs/ui-style-unify-deep-fix/issue-list.md` **T 批次 T1-T12**；执行任务：`tasks.md` **2.5 T 批**（执行顺序表次序 4.5）。

有意改造（禁止"回退对齐 Archive"）：`AppContextWrapper` night bit 同步翻转、`ThemeSync` v2 换肤体系（bump 唯一写点 ThemeConfig.applyTheme 末尾，双令牌恒成对已验证）、`recreateOnThemeChange` 豁免机制、AppearanceKit 编排层（全链路收敛 applyTheme 已验证）、Compose 设置页/菜单承载演进。
