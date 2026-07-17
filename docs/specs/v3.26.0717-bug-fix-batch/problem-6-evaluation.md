# 问题 6 评估：书源/订阅源视图布局差异

## 评估方法

对比 `item_bookshelf_list.xml`（书架列表）与 `item_book_source.xml`（书源列表）、`item_book_source_compact.xml`（书源紧凑列表）的字段、字号、布局差异。

## 字段对比

### 书架列表（item_bookshelf_list.xml）

| 字段 | 控件 | 字号 | 作用 |
|------|------|------|------|
| iv_cover | CoverImageView 66x90dp | - | 封面图 |
| fl_has_new | FrameLayout + BadgeView | - | 新章节徽章 |
| tv_name | TextView | 16sp | 书名 |
| iv_author + tv_author | 图标+TextView | 13sp | 作者 |
| tv_last_update_time | TextView | 13sp | 更新时间 |
| iv_read + tv_read | 图标+TextView | 13sp | 阅读进度 |
| iv_last + tv_last | 图标+TextView | 13sp | 最新章节 |

### 书源列表（item_book_source.xml）

| 字段 | 控件 | 字号 | 作用 |
|------|------|------|------|
| tv_host_text | AccentTextView 16sp | 16sp | 域名分组标题（可选） |
| cb_book_source | ThemeCheckBox | 默认 | 书源名称+复选框 |
| swt_enabled | ThemeSwitch | - | 启用开关 |
| iv_edit + iv_menu_more | 图标 48x48dp | - | 编辑/更多按钮 |
| iv_explore | CircleImageView 8dp | - | 发现标识 |
| iv_debug_text + iv_progressBar | TextView+ProgressBar | - | 校验信息 |

### 书源紧凑列表（item_book_source_compact.xml）

| 字段 | 控件 | 字号 | 作用 |
|------|------|------|------|
| cb_book_source | ThemeCheckBox | 14sp | 书源名称+复选框 |
| iv_type_badge | TextView | 10sp | 类型徽章 |
| swt_enabled | ThemeSwitch | - | 启用开关 |

## 核心差异

| 维度 | 书架 | 书源（列表） | 书源（紧凑） |
|------|------|------------|------------|
| 信息密度 | 5+ 字段 | 2 字段 + 操作按钮 | 3 字段 |
| 字号 | 16sp / 13sp | 默认 / 16sp | 14sp / 10sp |
| 布局 | 封面+多行文字 | 单行 + 操作按钮 | 单行紧凑 |
| 视觉层次 | 强（封面+图标+文字） | 弱（仅文字+按钮） | 弱（仅文字） |

## 评估结论

**本质差异**：书源和书架是不同类型的数据
- 书架：书籍元数据（封面、作者、阅读进度、最新章节）
- 书源：配置项（名称、启用状态、校验状态）

**用户反馈"没什么效果"的可能原因**：
1. 书源紧凑列表字号偏小（14sp + 10sp），与书架列表（16sp + 13sp）有视觉差异
2. 书源列表无封面/图标，视觉上"光秃秃"
3. 书源列表操作按钮（编辑/更多）占用空间，但缺乏信息层次

## 修复建议（待用户确认）

### 方案 A：调整字号对齐书架（最小侵入）

- 紧凑列表：cb_book_source 14sp → 16sp，iv_type_badge 10sp → 13sp
- 列表：cb_book_source 默认 → 16sp
- 调整 padding 与书架一致（书架 padding 8dp）

### 方案 B：增加视觉层次（中等侵入）

- 列表增加书源图标（用 sourceIcon 字段，显示在左侧）
- 列表增加分组标签（用 sourceGroup 字段，显示在书源名下方）
- 列表增加最后校验时间（用 lastUpdateTime 字段）

### 方案 C：保持现状

- 书源是配置项，与书架的书籍数据本质不同
- 当前紧凑/列表/网格布局已能区分不同使用场景
- 不强行参考书架布局

## 待用户确认

请选择修复方向（用 AskUserQuestion 与用户确认）
