# L-E5 精准管理（PreciseManage）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：PreciseManageFragment（`ui/config/`，PreferenceFragment，pref_precise_manage）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.61`；pages-inventory E5（优先级 P3）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 无独有数据源 | 纯聚合入口 |
| 布局结构 | 聚合入口 4 项 | — |
| 交互 | — | 每行点击跳转 |
| 功能点 | 聚合入口 4 项：URL记录/存储管理/下载管理/文件管理 | 全部为跳转入口 |

> 本页功能极简，与族文档差异极小：仅用 `SettingsClickRow` 承载 4 个跳转入口，无私有组件/弹窗/开关。

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 4 项聚合入口（URL记录/存储/下载/文件） |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/空态/错误 | — | Preference 页无列表三态 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] 功能点对照 pages-inventory E5 无遗漏（4 项聚合入口齐全）
- [ ] 4 项跳转目标正确
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-16：12.61 深化——内容区由 PreferenceFragment 改为全 Compose（PreciseManageScreen，SettingsCard + SettingsClickRow×4），顶栏仍由 ConfigActivity 提供（setTitle 联动）；4 项聚合入口跳转目标保持不变，无私有组件/弹窗/开关
- 2026-08-15：12.61 交付——PreferenceFragment 保留 View（S2 设置族骨架），共享 ConfigActivity Compose 顶栏（setTitle 联动词条标题），4 项聚合入口（URL记录/存储管理/下载管理/文件管理）跳转目标逐一核对无误，无私有组件/弹窗/开关；tasks.md 标记 ✅
- 2026-08-13：初始建立（关联 pages-inventory E5），task 12.61
