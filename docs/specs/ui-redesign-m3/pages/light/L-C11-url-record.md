# L-C11 URL 记录（UrlRecord）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P4-my-config.md`（S2 设置族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + P4 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：UrlRecordActivity（`ui/urlrecord/`，View）
- **所属族文档**：`pages/P4-my-config.md`（继承 S2）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.58`；pages-inventory C11（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理页（P4 §2）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`EmptyStatePlaceholder`、`AppDropdownMenu`、`SettingsCard`
- 复用状态范式：`ViewModel + StateFlow`（搜索 + 过滤派生）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | UrlRecord Room DAO | 列表数据 |
| 布局结构 | 搜索；**四维过滤**（domain/sourceName/method/status + 清除） | — |
| 交互 | 菜单（开关记录/过滤/清除7天/30天/全部）；item 着色（method GET蓝/POST紫/status 2xx绿/4xx橙/错误红）；点击详情复制URL | 状态语义着色 |
| 功能点 | URL 记录 + 四维过滤 + 清除 | 对照 pages-inventory C11 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsToggleRow` | 开关行 | 记录开关 |
| `AppSelectDialog` | L2 选择弹窗 | 过滤维度选择 |

> ⚠️ 状态着色需走语义色 token（GET 蓝/POST 紫/2xx 绿/4xx 橙/错误红），登记豁免或主题化，禁硬编码色。

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无记录空态 |
| 错误 | `EmptyStatePlaceholder` | 加载失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（状态色走语义 token）

## 6. 验收标准（轻量）

- [ ] 复用 P4 骨架/组件，无私有复制组件
- [ ] 差异点全部实现；功能点对照 pages-inventory C11 无遗漏
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-15：实施完成（task 12.58 ✅）。新增 `UrlRecordScreen.kt`（GlassTopAppBar 顶栏 + 更多下拉菜单 5 项 + SettingsSearchBar 搜索 + 列表 + 四维过滤 + 清除确认），UrlRecordActivity ComposeView 壳层接线，搜索/过滤/清除/详情逻辑保留 Activity；删除 item_url_record.xml/menu/url_record.xml；编译通过（assembleAppDebug --rerun-tasks BUILD SUCCESSFUL）
- 2026-08-13：初始建立（关联 task 12.58 / pages-inventory C11）
