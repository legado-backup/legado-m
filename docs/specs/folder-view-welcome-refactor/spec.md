# Spec: 书源/订阅源文件夹视图重构 + 欢迎页增强 + 前端样式审计

> 状态：🔄 开发中
> 创建日期：2026-07-08
> 设计审核：2026-07-08 用户通过

---

## Intent（意图）

当前书源/订阅源管理的"文件夹视图"实现简陋（120dp 主题色色块 + `ic_folder` 图标 + 渐变文字），与书架成熟的书封卡片样式严重割裂；右上角文件夹入口位置未经评估，破坏简约风格；欢迎页自定义功能虽已存在但默认关闭且缺少"按比例裁剪"逻辑；3.7 版本后陆续新增的自动任务/高亮规则/调试悬浮球/调试工具集/Web 备份等前端交互缺乏整体协调性审计。

本 spec 旨在：
1. **彻底重构文件夹视图**：复用书架封面卡片样式与配置对话框范式，统一视觉语言
2. **完善欢迎页自定义**：默认开启 + 按比例裁剪，让用户一键换图即得专业效果
3. **审计 3.7 后前端交互**：识别过重/偏离核心的功能，给出精简或迁移建议
4. **整体样式回归简约**：消除硬编码颜色/间距，统一圆角/阴影/动画节奏

---

## Scope（范围）

### In Scope（本次实施）

| # | 范围 | 涉及页面/模块 |
|---|------|--------------|
| 1 | 文件夹视图卡片样式重构（复用书架封面卡片） | BookSourceActivity / RssSourceActivity / ExploreFragment / RssFragment |
| 2 | 文件夹视图配置对话框（分组样式/视图/排序/间距） | 上述 4 页面 |
| 3 | 右上角文件夹入口位置重评估与调整 | 上述 4 页面菜单 |
| 4 | 三点菜单风格统一（展开项与书架一致） | 上述 4 页面 |
| 5 | 欢迎页 `customWelcome` 默认改为开启 | pref_config_welcome.xml |
| 6 | 欢迎页图片"按比例裁剪"逻辑新增 | WelcomeConfigFragment / BitmapUtils |
| 7 | 3.7 后前端交互审计报告（含优化建议） | 本 spec 文档输出 |
| 8 | 整体样式审计：硬编码颜色/间距/圆角清理 | 4 页面 + 欢迎页 |

### Out of Scope（不在本次实施）

- ❌ Web 端（modules/web/）源管理页面重构（本次只改 Android 原生）
- ❌ 书架本身布局重构（书架是参考基准，不改）
- ❌ 高亮规则 / 自动任务 / 调试工具集等功能本身的功能性改动（仅做交互审计报告，不本次实施）
- ❌ 为书源分组新增"封面图"数据模型（YAGNI，用首字+主题色生成）
- ❌ 欢迎页文字/图标显示逻辑改动（已有开关，保留）

---

## Approach（方案）

### Selected Approach（选定方案）

**A. 文件夹视图卡片：复用书架网格分组卡片结构 + 首字封面占位**

- 新建 `item_source_folder_grid.xml`，结构对齐 [item_bookshelf_grid_group.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/item_bookshelf_grid_group.xml)（`ivCover` + `tvName`）
- `ivCover` 区域显示：**分组名首字 + 主题色渐变背景**（类似联系人字母头像），而非 `ic_folder` 图标
- 卡片尺寸比例对齐书架网格（3:4 封面比例）
- 复用书架的圆角/阴影/间距样式

**理由**：书架分组卡片是成熟设计，直接复用消除割裂感；首字占位无需新增数据模型，符合 YAGNI。

**B. 文件夹视图配置对话框：参考 `configBookshelf()` 范式**

- 新建 `DialogSourceFolderConfigBinding`，包含：
  - 分组样式（spinner：字母封面/纯色封面/图标封面）
  - 视图（radio：列表/文件夹）
  - 排序（radio：名称/手动/地址/更新时间/响应时间/启用状态）
  - 间距（seekbar）
- 入口：右上角三点菜单 → "视图设置"

**C. 右上角文件夹入口：改为三点菜单统一入口**

- 移除当前独立的 `menu_view_mode` 顶层菜单项
- 改为右上角三点（overflow）菜单，展开后显示：视图模式切换 / 视图设置 / 分组管理 / 排序 / 导入 / 导出 / 帮助
- 与书架三点菜单风格一致

**D. 欢迎页：默认开启 + 按屏幕比例裁剪**

- `pref_config_welcome.xml` 中 `customWelcome` 的 `android:defaultValue` 改为 `"true"`
- 在 `WelcomeConfigFragment.setCoverFromUri()` 中新增裁剪步骤：按屏幕宽高比裁剪图片后再存储
- 裁剪使用 `BitmapUtils` 新增 `cropBitmapToAspectRatio(src, ratioW, ratioH)` 方法

**"按当前开源阅读比例"的解读**：欢迎页是全屏背景（`fullScreen()` + `window.decorView.background`），所以"开源阅读比例"= 设备屏幕比例。裁剪保证图片不变形地铺满屏幕。

**E. 3.7 后前端交互审计：同步实施精简项**

- 在 `design.md` 输出审计表
- 标注"过重/偏离/合理"三级评价
- 给出"保留/精简/迁移"建议
- **本次同步实施"精简"类建议**（用户审核确认）：
  - 自动任务系统：Cron 表达式改为"每天/每小时/自定义"三选一
  - 调试日志悬浮球：默认隐藏，仅在调试模式开启时显示
  - 调试工具集：从"我的"主入口迁移到"设置→其他设置→调试工具"二级页面
- "迁移"类建议（封面图集）由后续 spec 决策

### Alternatives Considered（考虑过的替代方案）

| # | 替代方案 | 否决理由 |
|---|---------|---------|
| A1 | 为书源分组新增 `cover` 字段，让用户上传分组封面 | 过度设计：需改数据库 schema + DAO + 编辑界面，收益低（用户极少为分组配图），违反 YAGNI |
| A2 | 沿用 `ic_folder` 图标但换更精美的矢量图 | 治标不治本：仍是"图标+色块"风格，与书架书封卡片视觉语言不一致，用户已明确吐槽 |
| A3 | 直接复用书架 `BooksAdapterGrid` 类 | 耦合过深：书架 Adapter 绑定 `Book`/`BookGroup` 实体，书源分组是 `String`，强行复用会引入大量空逻辑 |
| B1 | 不新增配置对话框，只改卡片样式 | 功能缺失：用户明确要求"分组/类型/视图/排序/间距"五项配置，仅改样式无法满足 |
| C1 | 保留 `menu_view_mode` 顶层入口，仅美化样式 | 位置不合理：用户吐槽"右上角文件夹感觉放哪合理么"，需重新评估而非美化 |
| D1 | 欢迎页裁剪按 `iv_book` 图标区域比例（120dp 方形） | 误读需求：欢迎页是全屏背景而非方形图标，按方形裁剪会导致背景拉伸变形 |
| D2 | 欢迎页裁剪按书封 3:4 比例 | 同 D1，与全屏背景比例不符 |
| E1 | 本次不实施任何 3.7 后交互改动 | 用户期望同步看到优化；用户审核后选择"同步实施精简项"（3 项），范围可控 |

### Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 首字封面不如真实图片精美 | YAGNI：真实图片需数据模型改动，首字方案零成本且风格统一；后续可演进 |
| 配置对话框新增 4 个配置项，增加用户认知负担 | 用户明确要求，且对话框折叠在三点菜单内，默认值合理则不影响新手 |
| 欢迎页默认开启可能让已有用户感到突兀 | 通过设置可关闭；默认开启符合"开箱即用"的产品理念 |
| 3.7 后交互仅同步实施 3 项精简（自动任务Cron/悬浮球/调试工具迁移） | "迁移"类（封面图集）工作量大，由后续 spec 决策；精简项范围可控 |
| 按屏幕比例裁剪会丢弃图片边缘内容 | 这是裁剪的本质取舍；提供"居中裁剪"策略，保留主体 |

### Prior Art（参考的已有工作）

- **书架布局**：[BookshelfFragment2.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BookshelfFragment2.kt) + [BaseBookshelfFragment.configBookshelf()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt#L168)
- **书架网格分组卡片**：[BooksAdapterGrid.GroupViewHolder](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BooksAdapterGrid.kt#L190)
- **阅读 Sigma 原版**：[legado-E](https://github.com/Luoyacheng/legado-E) 的书源管理是纯列表，无文件夹视图，本 spec 是阅读 Sigma 的增量
- **MD3 阅读**：[HapeLee/legado-with-MD3](https://github.com/HapeLee/legado-with-MD3) 的 Material3 前端改造可作为简约风格参考

---

## Requirements（需求）

### R1 文件夹视图卡片重构

- **R1.1** 新建 `item_source_folder_grid.xml`，结构对齐书架网格分组卡片（`ivCover` + `tvName`）
- **R1.2** `ivCover` 显示分组名首字 + 主题色渐变背景（删除 `ic_folder` 图标引用）
- **R1.3** 卡片宽高比 3:4（与书封一致）
- **R1.4** 复用书架的圆角/阴影/点击反馈样式
- **R1.5** [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) 改用新布局，`convert()` 设置首字 + 主题色
- **R1.6** 长按文件夹触发回调（预留 `onFolderLongClick`，暂不实现具体功能）

### R2 文件夹视图配置对话框

- **R2.1** 新建 `dialog_source_folder_config.xml` 布局
- **R2.2** 包含 4 个配置项：分组样式 / 视图模式 / 排序 / 间距
- **R2.3** 新增 PreferKey：`sourceFolderStyle`（分组样式 0/1/2）、`sourceFolderMargin`（间距）
- **R2.4** 排序复用现有 `BookSourceSort`，不新增
- **R2.5** 配置变更后立即刷新当前页面

### R3 右上角入口与三点菜单

- **R3.1** 移除 4 页面菜单中顶层 `menu_view_mode` 项
- **R3.2** 在三点菜单（overflow）中新增"视图设置"入口，点击弹出 R2 对话框
- **R3.3** "视图模式切换"保留在三点菜单中（切换列表/文件夹）
- **R3.4** 三点菜单展开项顺序与书架对齐：视图设置 / 视图模式 / 分组管理 / 排序 / 导入 / 导出 / 帮助

### R4 欢迎页默认开启 + 按比例裁剪

- **R4.1** [pref_config_welcome.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/xml/pref_config_welcome.xml) 中 `customWelcome` 的 `defaultValue` 改为 `"true"`
- **R4.2** [BitmapUtils](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/BitmapUtils.kt) 新增 `cropBitmapToAspectRatio(srcPath, ratioW, ratioH): String` 方法
- **R4.3** [WelcomeConfigFragment.setCoverFromUri()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/config/WelcomeConfigFragment.kt#L200) 在存储前调用裁剪
- **R4.4** 裁剪策略：居中裁剪（Center Crop），保留图片中央主体
- **R4.5** 裁剪后图片覆盖原文件，文件名保持 MD5 规则

### R5 整体样式审计

- **R5.1** 4 页面文件夹视图区域去除硬编码颜色，统一使用主题属性（`?attr/colorPrimary` 等）
- **R5.2** 圆角/阴影/间距统一使用 `dimens.xml` 资源
- **R5.3** 审计报告输出到 design.md 第 4 节

### R6 3.7 后前端交互审计

- **R6.1** 审计范围：07/05 ~ 07/07 更新日志中所有前端交互功能
- **R6.2** 评价维度：入口合理性 / 交互流畅性 / 与阅读器核心相关性 / 用户认知负担
- **R6.3** 输出"保留/精简/迁移"建议表
- **R6.4** 同步实施 3 项精简：自动任务 Cron 简化 / 悬浮球默认隐藏 / 调试工具迁移到设置二级页面
- **R6.5** "迁移"类（封面图集）由后续 spec 决策

---

## Scenarios（场景）

### S1 用户首次进入书源管理（文件夹视图默认）

1. 用户点击"书源管理"
2. 默认显示文件夹视图（因 `sourceViewMode` 默认 0=列表，需评估是否改默认）
3. 看到 3 列网格的分组卡片，每张卡片显示分组名首字 + 主题色渐变背景 + 底部分组名
4. 点击"全部"文件夹 → 进入全部书源列表
5. 点击"默认分组" → 进入该分组书源列表

### S2 用户切换视图模式

1. 用户点击右上角三点菜单
2. 展开后看到"视图模式 / 视图设置 / 分组管理 / ..."
3. 点击"视图模式" → 切换为列表视图
4. 点击"视图设置" → 弹出配置对话框
5. 在对话框调整间距 → 点击确定 → 列表立即应用新间距

### S3 用户自定义欢迎页

1. 用户进入"设置 → 欢迎页样式"
2. 看到"自定义欢迎页"开关已默认开启
3. 点击"背景图片" → 选择相册图片
4. 系统自动按屏幕比例裁剪图片并存储
5. 提示"设定成功"
6. 下次启动 App 显示自定义欢迎页

### S4 用户关闭欢迎页自定义

1. 用户进入"设置 → 欢迎页样式"
2. 关闭"自定义欢迎页"开关
3. 下次启动 App 显示默认欢迎页（`icon_read_book` + 文字）

### S5 用户调整文件夹视图间距

1. 用户在书源管理点击三点菜单 → "视图设置"
2. 拖动"间距"SeekBar
3. 点击确定
4. 文件夹卡片之间的间距立即变化，持久化记忆

### S6 边界：分组名为空

1. 某书源未分组（属于"未分组"）
2. 文件夹卡片显示"未"字 + 主题色背景
3. 点击进入未分组书源列表

### S7 边界：分组名首字为 emoji 或特殊字符

1. 分组名为"📚 我的书源"
2. 首字截取取首个 code point（emoji 整体），显示"📚"
3. 不出现乱码

### S8 边界：用户选择的欢迎页图片小于屏幕尺寸

1. 用户选择 200x300 的小图
2. 裁剪算法按屏幕比例（如 1080x2400）裁剪后图片过小
3. 降级策略：不放大，直接居中放置，剩余区域用主题色填充（保留原图质量）

### S9 边界：用户选择的欢迎页图片是 .9.png（九宫格）

1. 检测到 `.9.png` 后缀
2. 跳过裁剪，直接存储（九宫格图本身可拉伸）
3. WelcomeActivity 用 `decodeNinePatchDrawable` 加载
