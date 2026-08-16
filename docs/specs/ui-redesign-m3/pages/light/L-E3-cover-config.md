# L-E3 封面配置（CoverConfig）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：CoverConfigFragment（`ui/config/cover/`，PreferenceFragment，pref_config_cover）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.60`；pages-inventory E3（优先级 P3）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` / `SettingsToggleRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 默认封面图日/夜（选图/删除） | 变更 `BookCover.upDefaultCover` |
| 布局结构 | 封面规则行 | — |
| 交互 | `coverRule` 封面规则→`CoverRuleConfigDialog`；`coverShowName(N)`/`coverShowAuthor(N)` 联动（作者依赖书名 enabled） | 联动 enabled 为私有交互点 |
| 功能点 | 默认封面图 / 封面规则 / 书名·作者显隐开关 | — |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 封面规则/选图行 |
| `SettingsToggleRow` | h16 v12、bodyLarge、v12 垂直内边距 | coverShowName/coverShowAuthor 开关 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/空态/错误 | — | Preference 页无列表三态 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] 功能点对照 pages-inventory E3 无遗漏（封面图日/夜、封面规则、书名/作者联动、upDefaultCover）
- [ ] 作者依赖书名 enabled 联动正确
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-16：内容区 Compose 化——PreferenceFragment→Fragment+ComposeView（CoverConfigScreen），仅Wifi加载封面/封面规则/始终显示默认封面/日·夜默认封面选图与删除/书名·作者显隐开关（作者依赖书名 enabled）全 Compose 渲染；选图/删除/SharedPreferences 监听/BookCover.upDefaultCover 逻辑保留 Fragment；compileAppDebugKotlin BUILD SUCCESSFUL
- 2026-08-15：12.60 交付——PreferenceFragment 保留 View（S2 设置族骨架），共享 ConfigActivity Compose 顶栏（setTitle 联动词条标题），功能点全量对照 pages-inventory E3：默认封面图日/夜（选图/删除+upDefaultCover）、封面规则→CoverRuleConfigDialog、书名/作者显隐开关（作者依赖书名 enabled 联动）；CoverRuleConfigDialog 清理调试日志 Log.e + 硬编码中文迁 strings.xml 双语（新增 cover_rule_empty）；tasks.md 标记 ✅
- 2026-08-13：初始建立（关联 pages-inventory E3），task 12.60
