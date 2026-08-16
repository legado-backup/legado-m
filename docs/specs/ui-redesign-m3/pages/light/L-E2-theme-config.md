# L-E2 主题配置（ThemeConfig）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。⚠️ 本页为**唯一改主题入口**，主题权威源红线见下。

## 0. 页面身份

- **页面名 / 文件锚点**：ThemeConfigFragment（`ui/config/theme/`，PreferenceFragment，pref_config_theme）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.16p`（v2.8 预审已深审）、pages-inventory E2（优先级 P1）
- **fork 借鉴来源**：pages-inventory E2 预审（fork 差距见 P4 族文档背景）

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` / `SettingsToggleRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 主题色 6 项（日/夜 主色/强调/背景/导航栏，ColorPreference 明暗校验：白天禁太暗/夜间禁太亮）；`bgImage`/`bgImageN` 背景图（选图/模糊 SeekBar/删除三选）；`barElevation`/`fontScale` NumberPicker | 主题权威源 = ThemeStore+ThemeSpec（AD-01），**34 槽位只在运行时推导，不改 themeConfig.json 格式**（Config 保持 9 历史字段） |
| 布局结构 | themeList 主题列表 Dialog；saveDayTheme/saveNightTheme 保存；coverConfig/welcomeStyle 跳子配置；launcherIcon 换图标 | — |
| 交互 | 状态栏/导航栏切换重建；换肤即时切换（postEvent(RECREATE)，无全量 animateColor）；背景图下载（url→Content-Type 判扩展名→MD5 文件名） | — |
| 功能点 | 主题列表 Dialog / 保存主题 / 跳子配置 / 换图标 | 预审已登记 12 符合 + 15 违例（见 pages-inventory E2） |

> **⚠️ 红线**：主题权威源 ThemeStore+ThemeSpec（AD-01），此页为唯一改主题入口，34 槽位只在运行时推导，不改 themeConfig.json 格式；不引 Room 主题表（生态/风险）；不学 MoRealm 每书配色（ReadBookConfig 每书配色红线）。

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppSelectDialog` | S6 L2 通用选择弹窗 | **差异化 V4**：替换 themeList 私有全屏 Dialog（ThemeListDialog） |
| `AppNumberPickerDialog`（L2 族） | L2 NumberPicker 弹窗 | **差异化 V6**：替换私有 NumberPickerDialog（barElevation/fontScale） |
| `SettingsClickRow` / `SettingsToggleRow` | h16 v12、行高≥48dp | 主题行/开关行等价语义 |

> 差异化项（P1 通用五件套）：V1 顶栏私有 TitleBar→GlassTopAppBar；V2 页面零 Compose（未包 LegadoTheme，M3 34 槽位未接入）；V3 状态收敛到 ViewModel；V4-V6 弹窗族收敛；V7-V9 i18n 11 处硬编码中文；V15 无障碍缺口（三选弹窗触控 ≥48dp）。

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/错误 | — | **差异化 V11**：ThemeListDialog 三态不齐（RotateLoading 私有/空态裸 tv_msg/无错误态）需收敛 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；**差异化 V7/V8**：迁移 7 处硬编码中文 + 1 处硬编码英文 hint；触控 ≥48dp（**V15** 补三选弹窗触控确认）；颜色只 colorScheme

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] **红线零越界**：34 槽位只在运行时推导、themeConfig.json 格式不改、SharedPreferences 旧 key 不改、不引 Room 主题表
- [ ] 差异化 V1-V15 按 P1 通用五件套收敛；功能点对照 pages-inventory E2 无遗漏
- [ ] 明暗校验正确；换肤即时切换；真机覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.16p / pages-inventory E2，预审结论 12 符合 + 15 违例）
