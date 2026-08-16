# L-C13 源登录（SourceLogin）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P8-overlays.md`（S6 弹窗体系）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P8 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：SourceLoginActivity（`ui/login/`，View）
- **所属族文档**：`pages/P8-overlays.md`（继承 S6）
- **骨架归类**：S6 弹窗/动态表单页（WebView 登录 / 动态 UI 规则渲染）
- **对应 task**：tasks.md `12.48`；pages-inventory C13（优先级 P2）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S6 弹窗体系（P8 §2：L1 浮层/L2 Dialog 族/L3 透明窗壳）+ S3 表单字段范式（P10）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsCard`、`SettingsClickRow`、`SettingsToggleRow`、`AppDropdownMenu`、`AppTextDialog`
- 复用状态范式：`ViewModel + StateFlow`（动态 UI 受控回传）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 无 Room；loginInfo 自动保存（onDismiss） | 登录态 |
| 布局结构 | loginUi 空→WebViewLoginFragment（WebViewPool + 登录 Cookie）；非空→SourceLoginDialog；**loginUi 规则引擎**：JSON 数组或 @js:/&lt;js&gt; 求值（evalUiJs→RowUi 列表） | 双形态 |
| 交互 | **RowUi.Type 渲染**（text/password/select/button 点击长按>666ms/toggle）；viewName（null→name/'xxx'引号/JS 求值）；action（绝对URL openUrl/JS handleButtonClick）；输入防抖 600ms；style.layout_justifySelf（center/flex_start/flex_end）；菜单（确定 login()/查看删除 loginHeader/日志）；onDismiss 自动保存；upUiData/reUiView 回调更新 | — |
| 功能点 | 登录表单动态渲染 + WebView 登录 | 对照 pages-inventory C13 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppEditDialog` | L2 字段输入弹窗 | text/password 字段等价 |
| `AppTextDialog` | L2 文本弹窗 | loginHeader 查看/删除 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | WebView 进度条 | WebView 登录加载 |
| 空态 | `EmptyStatePlaceholder` | loginUi 无字段空态 |
| 错误 | 登录失败/规则求值错误提示 | 登录失败/规则求值错误 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；动态字段 label 来自 loginUi 规则（非 i18n 硬编码）；按钮触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 P8 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C13 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.48 / pages-inventory C13）
