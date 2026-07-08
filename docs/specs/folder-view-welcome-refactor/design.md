# Design: 书源/订阅源文件夹视图重构 + 欢迎页增强 + 前端样式审计

> 状态：🔄 开发中
> 创建日期：2026-07-08
> 设计审核：2026-07-08 用户通过

---

## 1. Technical Approach（技术方案）

### 1.1 整体架构

本方案涉及 4 个 Android 原生页面的文件夹视图重构 + 欢迎页配置增强 + 样式审计报告。不引入新依赖，不改动数据库 schema，不改动网络层。

**核心改造层次**：

```
┌─────────────────────────────────────────────────────────┐
│  配置层（PreferKey + AppConfig）                          │
│  新增: sourceFolderStyle / sourceFolderMargin            │
│  修改: customWelcome defaultValue false → true           │
├─────────────────────────────────────────────────────────┤
│  UI 层（XML 布局 + Adapter + 菜单）                       │
│  新增: item_source_folder_grid.xml                       │
│  新增: dialog_source_folder_config.xml                   │
│  修改: SourceFolderAdapter（首字+主题色渲染）             │
│  修改: 4 页面菜单（三点菜单统一入口）                     │
├─────────────────────────────────────────────────────────┤
│  业务层（Activity/Fragment）                              │
│  新增: 4 页面共同的 configFolderView() 方法               │
│  修改: 4 页面的菜单项处理                                  │
├─────────────────────────────────────────────────────────┤
│  工具层（BitmapUtils）                                    │
│  新增: cropBitmapToAspectRatio() 方法                    │
│  修改: WelcomeConfigFragment.setCoverFromUri()           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 文件夹视图卡片重构

**新布局 `item_source_folder_grid.xml`**（参考 [item_bookshelf_grid_group.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/item_bookshelf_grid_group.xml)）：

```xml
<ConstraintLayout>
    <ImageView android:id="@+id/iv_cover"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        app:layout_constraintDimensionRatio="3:4"
        android:scaleType="centerCrop"
        android:background="@drawable/bg_source_folder_cover" />
    <TextView android:id="@+id/tv_folder_initial"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        app:layout_constraintTop_toTopOf="@id/iv_cover"
        app:layout_constraintBottom_toBottomOf="@id/iv_cover"
        app:layout_constraintStart_toStartOf="@id/iv_cover"
        app:layout_constraintEnd_toEndOf="@id/iv_cover"
        android:textSize="48sp"
        android:textColor="@android:color/white" />
    <TextView android:id="@+id/tv_name"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        app:layout_constraintTop_toBottomOf="@id/iv_cover"
        android:gravity="center"
        android:maxLines="1"
        android:ellipsize="end" />
</ConstraintLayout>
```

**`bg_source_folder_cover.xml`**：主题色渐变背景（替代纯色块）

**[SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) 改造**：

```kotlin
override fun convert(holder, binding, item, payloads) {
    binding.tvName.text = item
    binding.tvFolderInitial.text = item.firstCodePointAsString()
    // 主题色已通过 ?attr/colorPrimary 在背景 drawable 中应用
}

// 首字截取扩展（处理 emoji）
private fun String.firstCodePointAsString(): String {
    if (isEmpty()) return ""
    val first = codePointAt(0)
    return String(Character.toChars(first))
}
```

### 1.3 配置对话框

参考 [BaseBookshelfFragment.configBookshelf()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt#L168) 的范式，新建 `configFolderView()` 方法。

**4 页面共用实现**：抽取到 `SourceFolderConfigHelper` 或在 4 个 Activity/Fragment 中分别实现（考虑代码量，建议抽取 helper）。

### 1.4 欢迎页裁剪算法

**新增 `BitmapUtils.cropBitmapToAspectRatio()`**：

```kotlin
fun cropBitmapToAspectRatio(srcPath: String, ratioW: Int, ratioH: Int): String {
    val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(srcPath, opts)
    val srcW = opts.outWidth
    val srcH = opts.outHeight
    val targetRatio = ratioW.toFloat() / ratioH
    val srcRatio = srcW.toFloat() / srcH

    val (cropW, cropH) = if (srcRatio > targetRatio) {
        // 原图更宽，按高度裁剪
        val cw = (srcH * targetRatio).toInt()
        cw to srcH
    } else {
        // 原图更高，按宽度裁剪
        srcW to (srcW / targetRatio).toInt()
    }
    val x = (srcW - cropW) / 2  // 居中
    val y = (srcH - cropH) / 2

    val bitmap = BitmapFactory.decodeFile(srcPath)
    val cropped = Bitmap.createBitmap(bitmap, x, y, cropW, cropH)
    bitmap.recycle()

    // 覆盖原文件
    FileOutputStream(srcPath).use { cropped.compress(JPEG, 90, it) }
    cropped.recycle()
    return srcPath
}
```

**调用点**：[WelcomeConfigFragment.setCoverFromUri()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/config/WelcomeConfigFragment.kt#L200) 存储文件后、`putPrefString` 前调用。

**比例获取**：用 `windowManager.windowSize` 获取屏幕宽高，计算 ratioW:ratioH。

### 1.5 三点菜单统一

**4 个菜单资源调整**（[R.menu.book_source](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/menu/book_source.xml) / R.menu.rss_source / R.menu.main_explore / R.menu.main_rss）：

- 移除顶层 `menu_view_mode`
- 新增 `menu_folder_config`（"视图设置"）
- 调整顺序：视图设置 / 视图模式 / 分组管理 / 排序 / 导入 / 导出 / 帮助

---

## 2. Architecture Decisions（架构决策 - ADR Y-Statement）

### AD-01: 文件夹卡片用首字占位而非真实图片

- **Context**: 书源分组是 `String` 类型，无 `cover` 字段；书架分组 `BookGroup` 有 `cover` 字段
- **Concern**: 如何在无封面数据的情况下复用书架卡片样式
- **Decision**: 用分组名首字 + 主题色渐变背景作为 `ivCover` 内容
- **Goal**: 视觉风格与书架统一，无需数据模型改动
- **Tradeoff**: 不如真实图片精美，但零成本且风格协调
- **Status**: Proposed

### AD-02: 不抽取公共 FolderConfigHelper，4 页面各自实现

- **Context**: 4 个页面（BookSourceActivity / RssSourceActivity / ExploreFragment / RssFragment）都需要 configFolderView()
- **Concern**: 代码重复 vs 抽象成本
- **Decision**: 在 [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) 伴生对象中提供 `showConfigDialog(context, callback)` 静态方法，4 页面调用
- **Goal**: 避免每个页面重复 50 行对话框代码，同时不引入过度抽象
- **Tradeoff**: 伴生对象方法无法直接访问页面状态，需通过 callback 回调
- **Status**: Proposed

### AD-03: 欢迎页裁剪比例用屏幕比例而非固定 3:4

- **Context**: 用户说"按当前开源阅读比例剪裁"
- **Concern**: "开源阅读比例"有两种解读：(a) 屏幕比例（欢迎页是全屏背景）(b) iv_book 图标区域比例（120dp 方形）
- **Decision**: 采用屏幕比例（运行时获取 `windowManager.windowSize`）
- **Goal**: 裁剪后的图片铺满全屏不变形
- **Tradeoff**: 不同设备屏幕比例不同，裁剪结果不一致；但这是合理的，因为欢迎页本身就要适配屏幕
- **Status**: Proposed

### AD-04: customWelcome 默认改为 true，但不做老用户迁移

- **Context**: 现有用户 customWelcome=false，改为默认 true 后老用户会突然看到自定义欢迎页
- **Concern**: 老用户体验突兀 vs 新用户开箱即用
- **Decision**: 默认值改为 true，老用户升级后若未设置自定义图片，仍显示默认欢迎页（因 welcomeImage 为空，走 super.upBackgroundImage()）
- **Goal**: 新用户开箱即用，老用户无感知（无图片时自动回退默认）
- **Tradeoff**: 老用户若手动设置过图片但关闭了开关，升级后会自动启用——但这种情况极少
- **Status**: Proposed

### AD-05: 3.7 后交互同步实施 3 项精简

- **Context**: 07/05~07/07 新增 8+ 个前端交互功能，用户审核选择"同步实施精简项"
- **Concern**: 范围控制 vs 用户期望同步看到优化
- **Decision**: 同步实施 3 项精简（自动任务 Cron 简化 / 悬浮球默认隐藏 / 调试工具迁移到设置二级页面）
- **Goal**: 用户同步看到核心交互优化，同时控制范围为 3 项
- **Tradeoff**: 实施工作量增加 3 项任务；"迁移"类（封面图集）仍由后续 spec 决策
- **Status**: Accepted

### AD-06: 文件夹视图默认模式保持现状（列表视图）

- **Context**: `sourceViewMode` 默认 0=列表视图
- **Concern**: 是否将文件夹视图设为默认
- **Decision**: 保持默认列表视图，不强制用户使用文件夹视图
- **Goal**: 尊重现有用户习惯，文件夹视图作为可选增强
- **Tradeoff**: 新用户无法第一时间看到文件夹视图，但可通过菜单切换
- **Status**: Proposed

---

## 3. Data Flow（数据流）

### 3.1 文件夹视图渲染流程

```
用户进入书源管理
    ↓
BookSourceActivity.onActivityCreated()
    ↓
isShowingFolder = AppConfig.sourceViewMode == 1
    ↓
if (isShowingFolder) upFolderView()
    ↓
folderAdapter.setItems(["全部", "未分组", ...groups])
    ↓
SourceFolderAdapter.convert()
    ↓
binding.tvName.text = item
binding.tvFolderInitial.text = item.firstCodePointAsString()
    ↓
RecyclerView 渲染网格（3 列，3:4 比例卡片）
```

### 3.2 配置对话框应用流程

```
用户点击三点菜单 → "视图设置"
    ↓
SourceFolderAdapter.showConfigDialog(context) { style, margin ->
    ↓
AppConfig.sourceFolderStyle = style
AppConfig.sourceFolderMargin = margin
    ↓
folderAdapter.notifyDataSetChanged()  // 立即刷新
    ↓
Activity 重启或 invalidateOptionsMenu()
```

### 3.3 欢迎页图片裁剪流程

```
用户点击"背景图片" → 选择图片 URI
    ↓
WelcomeConfigFragment.setCoverFromUri(uri)
    ↓
下载/复制原图到 externalFiles/covers/MD5.jpg
    ↓
BitmapUtils.cropBitmapToAspectRatio(filePath, screenW, screenH)
    ↓
居中裁剪 → 覆盖原文件
    ↓
putPrefString(PreferKey.welcomeImage, filePath)
    ↓
下次启动 → WelcomeActivity.upBackgroundImage() → 显示裁剪后图片
```

---

## 4. 3.7 版本后前端交互审计报告

### 4.1 审计范围

07/05 ~ 07/07 更新日志中涉及前端交互的功能（共 8 项）。

### 4.2 审计表

| 功能 | 入口 | 交互流程 | 问题点 | 评价 | 建议 |
|------|------|---------|--------|------|------|
| **自动任务系统**（07/07） | 我的→开关+任务管理页 | 开关→任务管理→增删改/批量Cron/导入导出/拖拽排序/日志 | 功能过重：Cron 表达式对普通用户门槛高；拖拽排序+日志查看+导入导出堆在一页 | ⚠️ 偏离核心 | **精简**：Cron 表达式改为"每天/每小时/自定义"三选一；日志查看单独页 |
| **高亮规则系统**（07/07） | 阅读界面菜单→规则管理页 | 阅读→菜单→高亮规则管理→规则列表 | 入口合理（阅读时配置高亮）；9 通道样式过细 | ✅ 合理 | **保留**；9 通道可折叠为"简单/高级"两档 |
| **手动划线高亮**（07/07） | 阅读时长按文字 | 长按→选中→添加高亮→编辑备注 | 交互流畅，符合阅读器标准操作 | ✅ 合理 | **保留** |
| **调试日志悬浮球**（07/07） | 其他设置→开关+屏幕右下角悬浮球 | 其他设置→开启→悬浮球→点击查看日志 | 悬浮球可能干扰阅读；位置与阅读翻页冲突 | ⚠️ 过重 | **精简**：悬浮球改为仅在"调试模式"开启时显示；默认隐藏 |
| **调试工具集**（07/06） | 我的→调试工具 | 我的→调试工具→6大工具→复制结果 | 6 个工具（编码转换/HTTP/curl/ping/正则/时间戳）对普通用户无意义，暴露在"我的"主入口 | ❌ 偏离核心 | **迁移**：移至"设置→其他设置→调试工具"二级页面；不在"我的"暴露 |
| **备份选择器**（07/06） | 备份时勾选 | 备份→勾选内容→确认 | 交互繁琐但功能必要；勾选项过多（10+） | ✅ 合理 | **保留**；提供"全选/常用"快捷预设 |
| **封面图集管理**（07/06） | ？ | 创建分组/导入导出ZIP/随机切换 | 与阅读器核心弱相关；功能复杂 | ⚠️ 偏离核心 | **迁移**：移至"设置→封面管理"；不在主流程暴露 |
| **Web 端备份**（07/06） | Web 端书架"数据备份"按钮 | Web 端→书架→数据备份→下载ZIP | 与原生备份功能重复；但 Web 端场景合理 | ✅ 合理 | **保留**；与原生备份共用底层逻辑 |

### 4.3 审计结论

| 评价 | 数量 | 处理建议 |
|------|------|---------|
| ✅ 合理 | 4 项 | 保留，必要时小优化 |
| ⚠️ 过重/偏离 | 3 项 | 后续 spec 精简或迁移 |
| ❌ 偏离核心 | 1 项 | 后续 spec 迁移到二级页面 |

**核心问题**：3.7 后前端交互堆叠，"我的"页面和主流程暴露了过多非核心功能（调试工具、封面图集、自动任务）。建议后续 spec 做"主流程净化"，将非核心功能迁移到设置二级页面。

### 4.4 整体样式审计

| 维度 | 现状 | 问题 | 建议 |
|------|------|------|------|
| **颜色** | 文件夹视图硬编码 `?attr/colorPrimary` 作为色块 | 与书架书封卡片视觉语言不一致 | 改用渐变背景 + 首字占位 |
| **圆角** | 文件夹卡片无圆角 | 与书架卡片圆角不一致 | 统一使用 `dimens.xml` 的 `card_corner_radius` |
| **阴影** | 文件夹卡片无阴影 | 扁平，缺乏层次 | 添加 `elevation` 或卡片阴影 |
| **间距** | 文件夹视图 GridLayoutManager 固定 3 列，无间距配置 | 用户无法调整 | 新增 `sourceFolderMargin` 配置 |
| **动画** | 无点击反馈动画 | 生硬 | 复用书架的 `selectableItemBackground` |

---

## 5. File Changes（文件变更清单）

### 5.1 新增文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `app/src/main/res/layout/item_source_folder_grid.xml` | 布局 | 新文件夹卡片布局（3:4 比例） |
| `app/src/main/res/layout/dialog_source_folder_config.xml` | 布局 | 文件夹视图配置对话框 |
| `app/src/main/res/drawable/bg_source_folder_cover.xml` | Drawable | 文件夹封面渐变背景 |

### 5.2 修改文件

| 文件 | 变更内容 |
|------|---------|
| [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) | 改用新布局；`convert()` 渲染首字+主题色；新增伴生 `showConfigDialog()` |
| [BookSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt) | 菜单调整；调用 `showConfigDialog()`；GridLayoutManager 列数/间距动态化 |
| [RssSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt) | 同上 |
| [ExploreFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt) | 同上 |
| [RssFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt) | 同上 |
| [pref_config_welcome.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/xml/pref_config_welcome.xml) | `customWelcome` defaultValue `false` → `true` |
| [WelcomeConfigFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/config/WelcomeConfigFragment.kt) | `setCoverFromUri()` 新增裁剪调用 |
| [BitmapUtils.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/BitmapUtils.kt) | 新增 `cropBitmapToAspectRatio()` |
| [PreferKey.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/PreferKey.kt) | 新增 `sourceFolderStyle` / `sourceFolderMargin` |
| [AppConfig.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/AppConfig.kt) | 新增 `sourceFolderStyle` / `sourceFolderMargin` 属性 |
| `app/src/main/res/menu/book_source.xml` | 移除 `menu_view_mode` 顶层；新增 `menu_folder_config` |
| `app/src/main/res/menu/rss_source.xml` | 同上 |
| `app/src/main/res/menu/main_explore.xml` | 同上 |
| `app/src/main/res/menu/main_rss.xml` | 同上 |
| `app/src/main/res/values/dimens.xml` | 新增 `card_corner_radius` / `folder_card_elevation` |
| `app/src/main/res/values/strings.xml` | 新增 `folder_config` / `folder_style` 等字符串 |

### 5.3 删除文件

| 文件 | 原因 |
|------|------|
| `app/src/main/res/layout/item_source_folder.xml` | 被新布局替代 |

### 5.4 文档同步（步骤 8）

| 文档 | 更新内容 |
|------|---------|
| [docs/project-flow/architecture/android-ui.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/architecture/android-ui.md) | 补充文件夹视图新布局说明 |
| [docs/project-flow/modules/config-system.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/modules/config-system.md) | 新增 `sourceFolderStyle` / `sourceFolderMargin` / `customWelcome` 默认值变更 |
| [docs/project-flow/quick-reference.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/quick-reference.md) | 更新布局文件清单 |
| [docs/INDEX.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/INDEX.md) | 状态标记 |
| `app/src/main/assets/updateLog.md` | 新增面向用户的更新条目 |
