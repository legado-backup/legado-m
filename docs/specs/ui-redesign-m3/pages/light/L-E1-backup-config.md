# L-E1 备份恢复（BackupConfig）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：BackupConfigFragment（`ui/config/backup/`，PreferenceFragment，pref_config_backup）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.4C`；pages-inventory E1（优先级 P2）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` / `SettingsToggleRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听（同族 E 族）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | WebDav 配置（URL/账号/密码掩码`*`repeat/目录/设备名） | 变更实时 `upWebDavConfig` |
| 布局结构 | 备份/恢复/导入/忽略项分组 | 纯 Preference 列表，无 Compose 区块 |
| 交互 | 备份路径选择；`web_dav_backup` 备份（权限+可写检查）；`web_dav_restore` 恢复（WebDav 文件选择器 + **长按备份名删除/重命名**）；`import_old` 导入旧数据；`restore_ignore` 忽略项 multiChoice；长按→本地 zip 恢复 | 长按手势为私有交互点 |
| 功能点 | 菜单（帮助/日志） | 顶栏菜单注入 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 备份/恢复/导入/路径选择行 |
| `SettingsToggleRow` | h16 v12、bodyLarge、v12 垂直内边距 | WebDav 相关开关（如有） |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/空态/错误 | — | Preference 页无列表三态；备份/恢复结果以 toast/确认框呈现 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] 功能点对照 pages-inventory E1 无遗漏（WebDav/备份/恢复/导入/忽略项/长按 zip 恢复/菜单）
- [ ] WebDav 密码掩码、权限+可写检查、长按删除/重命名正确
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory E1），task 12.4C
