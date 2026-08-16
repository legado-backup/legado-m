# L-D5 RSS 搜索/详情（RssSearch/RssArticleInfo）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P7-rss.md`（S2 列表管理骨架），本文只写「继承 + 差异」。开发本页只读本文档 + P7 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssSearchActivity + RssArticleInfoActivity（`ui/rss/search/`，View）
- **所属族文档**：`pages/P7-rss.md`
- **骨架归类**：S2 列表管理页（搜索）+ S4 详情页（RssArticleInfo）
- **对应 task**：tasks.md `12.16p`（v2.8 预审）；pages-inventory D5（优先级 P2）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理骨架（见 P7 §2）；RssArticleInfo 仿书源详情（见 P3-bookinfo 范式）
- 复用组件（§3.4）：`GlassTopAppBar`、`SettingsSearchBar`、`EmptyStatePlaceholder`、`AppSelectDialog`
- 复用状态范式：LiveData 流式输出；主题 applyThemeColors 动态适配

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | **统一搜索** searchRssLiveData 流式无分页；搜索历史 searchKeywordDao type=1（与书源隔离） | 独有 DAO |
| 搜索历史 | Flexbox + 点击即搜 + 长按删除 + 清空 | 历史交互 |
| 交互 | fbStartStop 停止（红色图标）+ 进度条；类型筛选 + 动态分组；**搜索范围筛选**（已选组勾选/全部源/全部组，变更重搜） | 独有 |
| 空态 | 空结果 alert 切全部 | — |
| 详情页 | 仿书源详情：ArcView + CardView 封面 Glide + OkHttpModelLoader referer/标题/时间/类型/来源数 | 独有 |
| 多源 | 多源列表 rv_source_list 点击某源→setSelected + 立即跳阅读；底部阅读按钮 tvRead + 返回 tvCancel；主题动态适配 applyThemeColors | 独有 |
| 路由 | 条目点击→showArticleInfo 写入 RssSearchSourceHolder→详情页 | 数据传递 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsSearchBar` | 搜索栏（孤儿） | 搜索输入 |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空结果/空历史 |
| `AppSelectDialog` | RadioButton primary 高亮 | 搜索范围筛选 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `LinearProgressIndicator` | 搜索进行中 |
| 空态 | `EmptyStatePlaceholder` | 空结果（alert 切全部） |
| 错误 | `EmptyStatePlaceholder` | 搜索失败 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；封面 contentDescription；触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 S2 骨架 + 书源详情范式，无私有复制组件
- [ ] 功能点对照 pages-inventory D5 无遗漏（统一搜索/历史隔离/停止/范围筛选/详情页/多源跳读）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory D5，task 12.16p）
