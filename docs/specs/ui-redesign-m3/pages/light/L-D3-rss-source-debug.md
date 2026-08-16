# L-D3 订阅源调试（RssSourceDebug）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P7-rss.md`（S2 语义）+ `pages/P10-booksource-edit.md`（S3 骨架范式），本文只写「继承 + 差异」。开发本页只读本文档 + P10 + P7 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssSourceDebugActivity（`ui/rss/source/debug/`，View，调试搜索 + 辅助面板）
- **所属族文档**：`pages/P10-booksource-edit.md`（S3 骨架）+ `pages/P7-rss.md`
- **骨架归类**：S3 表单/编辑器页（调试面板）
- **对应 task**：tasks.md `12.5D`；pages-inventory D3（优先级 P3）；关联 D2 V11-V13 硬编码中文归此页
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S3 表单/编辑器骨架（见 P10 §2）
- 复用组件（§3.4）：`GlassTopAppBar`、`AppTextDialog`、`AppEditDialog`
- 复用状态范式：VM 数据类 + 调试输入流式输出 observe
- 共享组件：TextDialog.kt / KeyboardToolPop.kt / KeyboardAssistsConfig.kt（与 D2 共享，迁移时一并处理）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 交互 | 调试搜索 `startDebug`；搜索提交按钮模式 + 焦点显隐辅助面板 | 调试输入交互 |
| 功能点 | 辅助面板快捷词（我的/系统/分类 URL initSortKinds **首个非空分类错误 ERROR 提示**/内容页） | 快捷词插入调试字段 |
| 分类切换 | textFl `onLongClick`→selector | 私有手势 |
| 输出 | 流式输出 `observe` | 调试结果实时呈现 |
| 菜单 | 查看列表/内容 HTML `TextDialog` | 结果查看 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `GlassTopAppBar` | surface 实底 + titleMedium | 顶栏 |
| `AppTextDialog` | Markwon 渲染、内容 maxHeight 70% | 查看列表/内容 HTML |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `LinearProgressIndicator` | 调试搜索过程加载态，字段区顶部，初始化可省略 |
| 空态/错误 | `ThemedSnackbarHost` | 调试失败提示（V19 现用 RotateLoading 非骨架屏，P2 待修） |

## 5. i18n 与无障碍

- ✅ V11-V13 硬编码中文已清理（Kotlin 4 处 + 布局 xml 7 处全部资源化，双语 values/values-zh 同步）
- 新文案 `strings.xml` 双语；触控 ≥48dp

## 6. 验收标准（轻量）

- [x] 复用 S3 骨架，无私有复制组件（GlassTopAppBar + SettingsSearchBar + AppDropdownMenu，参照 C3 内核桥接）
- [x] 功能点对照 pages-inventory D3 无遗漏（startDebug/快捷词/分类 onLongClick/流式输出/菜单）
- [x] V11-V13 硬编码中文已清理（我的/获取发现出错/选择分类/未获取到订阅源 + 布局 xml 7 处全部资源化）；三态补齐
- [ ] 真机功能点覆盖用例通过（模拟器 L1+L2 已验：打开/快捷词调试/菜单/源码对话框均无崩溃；真机由测试 AI 负责）；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-15：12.5D 实施完成（Compose 顶栏+搜索栏+菜单、i18n 清理、menu 资源删除、模拟器验证通过）
- 2026-08-13：初始建立（关联 pages-inventory D3），task 12.5D
