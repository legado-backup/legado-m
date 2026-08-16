# L-C17 欢迎页（Welcome）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：WelcomeActivity（`ui/welcome/`，View）
- **所属族文档**：`pages/P4-my-config.md`（继承 S6）
- **骨架归类**：S6 弹窗/展示页（欢迎启动展示）
- **对应 task**：tasks.md `12.5B`；pages-inventory C17（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S6 弹窗/展示范式（P8 §2 L3 透明窗壳）
- 复用组件（§3.4）：`GlassTopAppBar`（可选）、主题 token（accent）
- 复用状态范式：AppConfig（PreferKey）+ 启动 Intent 分发

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 无 Room；AppConfig PreferKey.welcomeShowTime | 显示时长（0 直接跳转） |
| 布局结构 | 自定义欢迎图 customWelcome + welcomeImage(Dark)（.9.png decodeNinePatchDrawable/普通位图按窗口解码）；文字图标显隐（日/夜两套） | — |
| 交互 | FLAG_ACTIVITY_BROUGHT_TO_FRONT 防重复；startMainActivity + defaultToRead 直达阅读器；图标标题 setColorFilter(accent) | — |
| 功能点 | 欢迎展示 + 直达主界面/阅读器 | 对照 pages-inventory C17 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| — | 纯展示页，无差异表单组件 | setColorFilter 走主题 accent token |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 欢迎图解码加载 | 欢迎图解码加载 |
| 空态 | 不适用 | 展示页无空态 |
| 错误 | `EmptyStatePlaceholder` | 加载失败降级 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（accent 走主题 token）

## 6. 验收标准（轻量）

- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C17 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.5B / pages-inventory C17）
