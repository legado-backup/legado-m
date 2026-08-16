# L-E6 欢迎配置（WelcomeConfig）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md` 的 S2 设置族骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P4-my-config.md` + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：WelcomeConfigFragment（`ui/config/welcome/`，PreferenceFragment，pref_config_welcome）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2 设置族）
- **骨架归类**：S2 配置列表页
- **对应 task**：tasks.md `12.62`；pages-inventory E6（优先级 P3）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 配置列表页（见 P4 §2），PreferenceFragment **保留 View**
- 复用组件（§3.4）：`SettingsClickRow` / `SettingsToggleRow` 组合语义（等价 Preference 行）
- 复用状态范式：SharedPreferences 直读直写 + Preference 监听

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 欢迎页图片日/夜 | 支持 http 下载：AnalyzeUrl + `BitmapUtils.cropBitmapToAspectRatio` 按屏幕比例裁剪 |
| 布局结构 | 欢迎页图片（日/夜）行 | — |
| 交互 | 选图/删除 | 图片下载为私有逻辑 |
| 功能点 | 文字/图标开关已注释留空 | 预留项，无需实现 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsClickRow` | h16 v12、bodyLarge 标题、行高≥48dp | 欢迎页图片日/夜行 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载/错误 | — | 图片 http 下载失败需 toast 反馈（Preference 页无列表三态） |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）

- [ ] 复用 S2 设置族骨架 + Preference 保留 View，无私有复制组件
- [ ] 功能点对照 pages-inventory E6 无遗漏（欢迎页图片日/夜、选图/删除、http 下载裁剪；文字/图标开关留空）
- [ ] http 下载 + 屏幕比例裁剪正确
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-16：12.62 深化——内容区由 PreferenceFragment 改为全 Compose（WelcomeConfigScreen，Slider 显示时间 + SettingsToggleRow 自定义欢迎 + SettingsClickRow×2 日/夜背景图），选图/删除/http 下载裁剪/SharedPreferences 监听逻辑保留 Fragment；顶栏仍由 ConfigActivity 提供（setTitle 联动）
- 2026-08-15：12.62 交付——PreferenceFragment 保留 View（S2 设置族骨架），共享 ConfigActivity Compose 顶栏（setTitle 联动词条标题），功能点全量对照 pages-inventory E6：欢迎页图片日/夜（选图/删除/HTTP 下载 + BitmapUtils.cropBitmapToAspectRatio 按屏幕比例裁剪）；硬编码中文「下载图片中...」「设定成功」迁 strings.xml 双语（新增 downloading_image/set_success）；文字/图标开关保持注释留空；tasks.md 标记 ✅
- 2026-08-13：初始建立（关联 pages-inventory E6），task 12.62
