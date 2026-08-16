# L-C19 调试工具（debug 7 工具）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：debug 7 工具（`ui/debug/`）— CurlTest / HttpDebug / PingTest / EncodeTools / RegexTest / TimestampConvert / DebugTools 总入口
- **所属族文档**：`pages/P4-my-config.md`（继承 S3）
- **骨架归类**：S3 工具/表单页（已纯 Compose）
- **对应 task**：tasks.md `12.16k`（v2.8 复审）；pages-inventory C19（**P0 已改造**）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S3 工具页（AppCompatActivity + setLegadoContent + LegadoThemeWithBackground）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsCard`、`SettingsClickRow`、`AppEditDialog`
- 复用状态范式：ViewModel + StateFlow（工具为枝叶，Compose 受控输入）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 无 Room；纯工具计算 | 各工具独立逻辑 |
| 布局结构 | 7 工具独立 Screen；RegexTest 带 startIntent 外部初始值 | — |
| 交互 | 各工具独有输入/输出 | — |
| 功能点 | Curl/Http 调试/Ping/编码/正则/时间戳/总入口 | 对照 pages-inventory C19 无遗漏 |

> **⚠️ 3 违例待修（归 P4 一致性巡检，非本页独立修复）**：① 硬编码中文 60 处（EncodeTools 19 / HttpDebug 16 / TimestampConvert 8 / CurlTest 6 / PingTest 6 / RegexTest 4 / DebugTools 1）；② 硬编码色 11 处（CurlTest 2 / PingTest 5 / RegexTest 4）；③ 实施回执缺失（工具族 7 Screen 均无 §3.3 回执模板）。

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsCard` | 卡 18dp | 工具字段分组容器 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | — | 工具页无持久加载 |
| 空态 | 不适用 | — |
| 错误 | `EmptyStatePlaceholder` | 工具执行错误输出（与硬编码中文违例一并修复） |

## 5. i18n 与无障碍

- **违例修复项**：迁移 60 处硬编码中文 → `strings.xml` 双语；11 处硬编码色 → 主题 token；工具按钮触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 S3 工具骨架（setLegadoContent + LegadoThemeWithBackground），无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C19 无遗漏
- [ ] **3 违例清零**：60 处硬编码中文资源化 + 11 处硬编码色主题化 + §3.3 回执补齐（归 P4 巡检）
- [ ] 真机功能点覆盖用例通过

## 7. 变更记录

- 2026-08-13：初始建立（关联 task 12.16k / pages-inventory C19，P0 已改造，3 违例待 P4 巡检修复）
