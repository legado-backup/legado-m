# Spec: 书源/订阅源布局参考书架重构（Issue-6 方案D）

## 背景

### 用户原始诉求

> "我说过，你的书源订阅源首页模式参考书架布局呀，艹！"
>
> "你自己思考怎么样更合理！我要求的是尽可能一致，视觉一致性，功能一致性！"

### 方案演进

| 方案 | 内容 | 状态 |
|------|------|------|
| A | 调整字号对齐书架（仅改字号） | 否决（治标不治本） |
| B | 增加视觉层次（增加字段/图标） | 否决（局部修改） |
| C | 保持现状 | 否决（违背用户要求） |
| **D** | **三种模式全面参考书架布局重构** | **用户确认** |

### 关联文档

- `v3.26.0717-bug-fix-batch/problem-6-evaluation.md` — 方案A/B/C评估，已被否决
- `source-layout-redesign/` — 视图模式扩展（2种→5种）+ 排序 + 类型筛选（与本spec正交）
- `source-layout-detail-refinement/` — 标签+分组两模式（与本spec正交）

## Intent

让书源/订阅源列表的视觉布局和功能模式与书架完全对齐：**书架有3种视图（列表/紧凑列表/网格），书源/订阅源也要有相同的3种视图且布局结构参考书架**。

**核心目标**：
1. **视觉一致性**：书源/订阅源列表左侧有首字图标，右侧有多字段信息，结构同书架
2. **功能一致性**：书源/订阅源也支持3种模式（列表/紧凑列表/网格），与书架模式对齐
3. **不破坏现有功能**：保留多选（CheckBox）、启用开关（Switch）、编辑/更多按钮、调试状态、发现标识

## Scope

### In Scope

- **6个布局XML重构**：
  - 书源：item_book_source.xml / item_book_source_compact.xml / item_book_source_grid.xml
  - 订阅源：item_rss_source.xml / item_rss_source_compact.xml / item_rss_source_grid.xml
- **2个Activity适配**：BookSourceActivity / RssSourceActivity 的 layout=0/1/2 分支
- **Adapter代码适配**：新增控件ID（tv_source_initial/tv_book_source_url/v_enabled_dot等）的绑定
- **新增列表模式**：订阅源原来只有compact+grid，新增列表模式（layout=0）

### Out of Scope

- 书源/订阅源编辑页（SourceEditActivity）改动
- 书架本身的改动（书架是参考对象，不改）
- 视图模式值域扩展（已在 source-layout-redesign 中处理）
- 排序/类型筛选/标签+分组（已在 source-layout-detail-refinement 中处理）
- 数据库字段变更（无新增字段，仅复用现有 sourceName/sourceUrl/lastUpdateTime）

## Approach

### 方案：参考书架布局结构重构

**核心设计模式**：左侧首字图标 + 右侧多字段信息 + 右侧操作按钮区

**书架列表参考（item_bookshelf_list.xml）**：

| 区域 | 控件 | 尺寸 | 字号 |
|------|------|------|------|
| 左侧封面 | CoverImageView | 66x90dp | - |
| 书名 | tv_name | 0dp(match) | 16sp |
| 作者 | iv_author + tv_author | - | 13sp |
| 更新时间 | tv_last_update_time | - | 13sp |
| 阅读进度 | iv_read + tv_read | - | 13sp |
| 最新章节 | iv_last + tv_last | - | 13sp |
| 右侧操作 | fl_has_new + BadgeView + RotateLoading | - | - |

**书架紧凑列表参考（item_bookshelf_list2.xml）**：

| 区域 | 控件 | 尺寸 | 字号 |
|------|------|------|------|
| 左侧封面 | CoverImageView | 48x64dp | - |
| 书名 | tv_name | 0dp(match) | 16sp |
| 作者•进度合并 | tv_author + isolate + tv_read | - | 13sp + 11sp + 13sp |
| 最新章节 | iv_last + tv_last | - | 13sp |
| 右侧操作 | fl_has_new | - | - |

**书架网格参考（item_bookshelf_grid.xml）**：

| 区域 | 控件 | 尺寸 | 字号 |
|------|------|------|------|
| 封面 | CoverImageView | match_parent + 4dp margin | - |
| 名称 | tv_name | match_parent | 12sp, 2行 |

### 书源三种模式映射

| 模式 | 参考书架 | 左侧图标 | 右侧字段 |
|------|---------|---------|---------|
| 列表(layout=0) | item_bookshelf_list.xml | 66x90dp 首字 | 名称16sp + 域名13sp + 调试13sp |
| 紧凑(layout=1) | item_bookshelf_list2.xml | 48x64dp 首字 | 名称16sp + 域名•校验合并13sp |
| 网格(layout≥2) | item_bookshelf_grid.xml | 自适应3:4比例 | 名称12sp 2行 |

### 订阅源三种模式映射

与书源完全一致，仅字段差异（订阅源无"调试"字段，可显示"最后更新时间"或"文章数"）

### 关键设计决策

1. **首字图标实现**：FrameLayout + bg_source_folder_cover背景 + 首字TextView（白色加粗大字）
   - 复用已有 drawable `bg_source_folder_cover`（网格布局已用）
   - 复用已有 drawable `bg_source_enabled_dot`（启用状态点）
2. **图标使用 drawableStart 而非独立 ImageView**：
   - 原因：`ic_link` drawable 不存在
   - 方案：用已有 `ic_author` + drawableTint 设置颜色，作为 TextView 的 drawableStart
3. **保留原有控件ID**：cb_book_source / swt_enabled / iv_edit / iv_menu_more / iv_explore / iv_progressBar / tv_debug_text / tv_host_text
4. **新增控件ID**：iv_source_cover / tv_source_initial / v_enabled_dot / tv_book_source_url

### Alternatives Considered

**Alt 1：直接复制书架布局文件，只改字段名**
- 优点：最直接，100%视觉一致
- 缺点：丢失多选/启用开关/编辑/更多按钮等书源特有功能
- **否决**：书源是配置项，需要操作按钮，不能完全复制书架

**Alt 2：保留现有布局，仅增加首字图标**
- 优点：最小侵入
- 缺点：不符合"参考书架布局结构"的核心要求
- **否决**：用户明确要求参考书架布局，不是局部增强

**Alt 3：在书架列表基础上扩展**
- 优点：最大化复用书架布局
- 缺点：书架列表的"封面图+作者+最新章节"等字段对书源无意义
- **否决**：字段语义不匹配，需要重新设计字段映射

## Requirements

### REQ-1: 书源列表布局重构（item_book_source.xml）

- 左侧：FrameLayout 66x90dp + bg_source_folder_cover背景 + tv_source_initial(28sp白色加粗) + v_enabled_dot(8dp)
- 右侧字段：
  - cb_book_source（书源名+多选）16sp
  - tv_book_source_url（域名，drawableStart=ic_author+drawableTint）13sp
  - tv_debug_text（调试/校验信息，drawableStart=ic_history）13sp
- 右侧操作：swt_enabled + iv_edit(48dp) + iv_menu_more(48dp)
- 顶部：tv_host_text（域名分组标题，可选）
- 其他：iv_explore（发现标识）+ iv_progressBar（校验进度）
- **状态：已完成**

### REQ-2: 书源紧凑列表重构（item_book_source_compact.xml）

- 左侧：FrameLayout 48x64dp + bg_source_folder_cover背景 + tv_source_initial(20sp白色加粗)
- 右侧字段（合并行）：
  - cb_book_source 16sp + tv_book_source_url 13sp（合并行：作者•域名格式）
- 右侧操作：swt_enabled
- **状态：待实施**

### REQ-3: 订阅源列表布局重构（item_rss_source.xml）

- 完全参考item_book_source.xml结构
- 字段差异：无 tv_debug_text，可显示文章数或最后更新时间
- **状态：待实施**

### REQ-4: 订阅源紧凑列表重构（item_rss_source_compact.xml）

- 完全参考item_book_source_compact.xml结构
- **状态：待实施**

### REQ-5: 网格布局字号对齐书架

- item_book_source_grid.xml：tv_source_name 12sp 2行居中（已对齐）
- item_rss_source_grid.xml：tv_source_name 12sp 2行居中（需优化）
- **状态：待优化**

### REQ-6: 订阅源新增列表模式

- RssSourceActivity.applyListView 的 layout=0 分支当前用adapter（列表模式存在）
- 但用户反馈"订阅源没有列表模式，都是卡片模式"——需调查现状
- 如确实只有2种模式，需新增列表模式layout=0分支
- **状态：待调查**

### REQ-7: Adapter代码适配

- 检查 BookSourceAdapter / BookSourceCompactAdapter / BookSourceGridAdapter
- 检查 RssSourceAdapter 等订阅源适配器
- 新增控件ID需要绑定数据：
  - tv_source_initial：取书源/订阅源名称首字（中文取首字，英文取首字母大写）
  - tv_book_source_url：取 sourceUrl 域名部分（脱敏显示，不输出完整URL）
  - v_enabled_dot：根据 enabled 字段显示/隐藏
- **状态：待实施**

## Scenarios

### Scenario 1: 书源列表视觉一致性

1. 用户进入书源管理（layout=0 列表模式）
2. **预期**：每行显示「左侧66x90dp首字图标(主题色背景+白色首字+启用状态点) + 右侧书源名16sp + 域名13sp + 调试信息13sp + 右侧操作按钮」
3. 视觉上与书架列表（左侧封面+右侧多字段）结构一致

### Scenario 2: 切换到紧凑列表

1. 用户切换到 layout=1 紧凑列表
2. **预期**：每行显示「左侧48x64dp首字图标 + 右侧书源名16sp + 域名13sp(合并行) + 启用开关」
3. 视觉上与书架紧凑列表（48x64dp封面+合并行）一致

### Scenario 3: 切换到网格

1. 用户切换到 layout=2-6 网格模式
2. **预期**：每个卡片显示「首字封面(3:4比例) + 名称12sp 2行居中」
3. 视觉上与书架网格（封面+书名）一致

### Scenario 4: 订阅源列表与书源一致

1. 用户进入订阅源管理（列表模式）
2. **预期**：布局结构与书源列表一致，仅字段差异（无调试字段）

### Scenario 5: 多选/启用/编辑/更多功能保留

1. 在新布局下点击 CheckBox 多选 → 正常选中
2. 拖动 Switch 切换启用状态 → 正常切换
3. 点击编辑图标 → 进入编辑页
4. 点击更多图标 → 弹出菜单

## Acceptance Criteria

- [ ] 编译通过（无新增 lint error）
- [ ] 书源3种模式视觉布局与书架3种模式对应一致
- [ ] 订阅源3种模式视觉布局与书架3种模式对应一致
- [ ] 原有功能（多选/启用开关/编辑/更多/发现标识/调试状态）全部保留
- [ ] 真机验证3种模式切换正常
- [ ] 真机验证多选/编辑/更多按钮可点击

## Non-Goals

- 不修改书架布局（书架是参考对象）
- 不修改书源/订阅源编辑页
- 不修改视图模式值域（由 source-layout-redesign 处理）
- 不修改排序/类型筛选/标签+分组（由 source-layout-detail-refinement 处理）
