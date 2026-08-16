# L-E4 其它配置（OtherConfig）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：OtherConfigFragment（`ui/config/other/`，PreferenceFragment，pref_config_other）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.4D`；pages-inventory E4（优先级 P2）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` / `SettingsToggleRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 大量 NumberPicker（预下载/线程/搜索线程/缓存线程/RSS并发/图片并发/Web端口/位图缓存/图片保留/编辑最大行）；`userAgent`/`customHosts`（JSON 校验） | NumberPicker 为密集差异点 |
| 布局结构 | 视频设置/默认书目录/清理/密码/高级跳转/开关 多分组 | — |
| 交互 | `videoSetting`→SettingsDialog；默认书目录 TreeUri；`cleanCache`/`clearWebViewData`/`shrinkDatabase`（确认框）；`localPassword`；`checkSource`→CheckSourceConfig；`uploadRule`→DirectLinkUploadConfig；`debug_tools`→DebugToolsActivity | 清理类操作带确认框 |
| 功能点 | 开关：记录日志/调试浮球/processText 文本选择分享/显示发现-RSS/语言重启/自动刷新 | — |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppNumberPickerDialog`（L2 族） | L2 NumberPicker 弹窗 | 10 项 NumberPicker 数值配置 |
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 跳转/清理/密码行 |
| `SettingsToggleRow` | h16 v12、bodyLarge、v12 垂直内边距 | 记录日志/调试浮球/processText/显示发现-RSS/语言重启/自动刷新 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/空态/错误 | — | Preference 页无列表三态；清理类操作以确认框 + toast 反馈 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] 功能点对照 pages-inventory E4 无遗漏（10 项 NumberPicker/JSON 校验/TreeUri/清理确认框/各跳转/6 开关）
- [ ] customHosts JSON 校验、清理类确认框正确
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory E4），task 12.4D
