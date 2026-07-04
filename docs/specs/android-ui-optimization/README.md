# Android UI/UX 优化分析

> 状态：✅ 设计完成 → ✅ 开发完成 → 🔄 待真机验证

## 功能概述

对开源阅读（Legado）项目 Android 前端进行深度 UI/UX 审查，覆盖 **12 个维度** 的全面分析，识别布局、样式、主题、暗色模式、组件质量、动画、无障碍、图标、卡片、对话框、搜索、导航等方面的优化点，产出结构化优化方案。

## 核心能力

- **主题体系升级分析**：M2→M3 迁移评估、色彩一致性、Typography/Spacing token 体系
- **布局质量审查**：220 个 XML 布局的圆角/间距/触控目标/RTL 合规性
- **暗色模式质量**：颜色覆盖完整性、硬编码色值、WCAG 对比度合规
- **组件现代化**：自定义 Widget 质量、Ripple/Elevation/Drawable 现代化
- **视觉一致性**：圆角体系、Elevation 层级、Divider 规范统一
- **动画与过渡**：翻页动画质量、Activity 过渡、列表入场动画
- **无障碍(WCAG)**：色彩对比度、触控目标尺寸、屏幕阅读器支持
- **图标体系**：Vector Drawable 质量、tint 策略、viewport 规范
- **卡片/容器**：容器样式统一、elevation 策略
- **对话框**：60+ 对话框一致性、按钮样式、表单输入
- **搜索/导航**：搜索栏样式、BottomNavigationView 规范、ViewPager 版本
- **响应式适配**：横屏布局、sw 限定符、折叠屏、窄屏适配

## 文档索引

| 文档 | 核心内容 |
|------|---------|
| [spec.md](./spec.md) | 意图/范围/方案/需求/场景 |
| [design.md](./design.md) | 技术方案/架构决策/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 关键发现摘要（12 维度 × 4 优先级）

### P0 — 阻塞性问题（暗色模式下可见性 Bug / 无障碍严重违规 / 功能失效）

| # | 问题 | 维度 |
|---|------|------|
| 1 | `Style.Text.Primary.Normal` 硬编码 `#000`，暗色模式下黑底黑字 | 主题/暗色 |
| 2 | `Style.Text.Second.Normal` 硬编码 `#676767`，暗色模式下不可见 | 主题/暗色 |
| 3 | `bg_gradient_cover.xml` 使用 `12px` 而非 `12dp` | Drawable |
| 4 | `shape_radius_10dp.xml` 文件名与实际值 16dp 不匹配 | Drawable |
| 5 | 向量图标 `ic_back.xml` viewport=1024×1024 严重异常 | 图标 |
| 6 | `tv_text_summary` 亮色模式对比度仅 ~3.3:1，不达 WCAG AA | 无障碍 |
| 7 | grid2 书名 11sp 纯白叠在封面底部，浅色封面不可读(~2:1) | 无障碍/书架 |
| 8 | `accent` 色 `#D84315` 暗色模式对比度仅 ~4.0:1，不达 WCAG AA | 无障碍 |
| 9 | `primary` 色 `#039BE5` 亮色模式对比度仅 ~3.7:1，不达 WCAG AA | 无障碍 |
| 10 | `RotateLoading` 硬编码阴影色 `#1a000000`，暗色模式不可见 | 组件 |
| 11 | **自定义 Toast 在 Android 11+ 完全失效**（API 30 禁止自定义 Toast View） | 通知/Toast |

### P1 — 视觉一致性严重问题

| # | 问题 | 维度 |
|---|------|------|
| 1 | 圆角系统：20 种不同值无规范体系 | Drawable |
| 2 | 字号系统：8 种硬编码值无语义化 token | 排版 |
| 3 | 间距系统：7 种不同间距值无 4dp grid | 排版 |
| 4 | 亮暗主题完全换色相（LightBlue+Pink → BlueGrey+DeepOrange） | 主题 |
| 5 | Elevation 混乱：8 种不同值 | 视觉层次 |
| 6 | 向量图标硬编码 fillColor，不跟随主题 tinting | 图标 |
| 7 | 卡片容器样式 4 种以上不统一 | 卡片 |
| 8 | 对话框圆角不一致（2dp/3dp/无圆角） | 对话框 |
| 9 | 书架 list/list2 封面面积差 1.9 倍，切换模式视觉跳跃 | 书架 |
| 10 | `shape_card_view` 圆角仅 3dp，远低于 M3 标准 12dp | 卡片 |
| 11 | 空状态仅纯文字，无插画/CTA 引导 | UX |
| 12 | 使用废弃的 `ViewPager` + `FragmentStatePagerAdapter` | 导航 |
| 13 | 底部导航 `labelVisibilityMode=unlabeled`，M3 推荐 icon+label | 导航 |
| 14 | 普通封面无 crossfade 过渡动画，加载时硬切 | 图片 |
| 15 | 搜索 Activity 缺少 `windowSoftInputMode`，键盘遮挡搜索框 | 键盘/IME |

### P2 — 现代设计规范缺失

| # | 问题 | 维度 |
|---|------|------|
| 1 | 基于 AppCompat M2 而非 Material3，无 Dynamic Color | 主题 |
| 2 | 阴影用 gradient drawable 模拟而非 elevation | 视觉层次 |
| 3 | Ripple 用独立 View 覆盖而非 foreground | 组件 |
| 4 | 图标尺寸用 sp 而非 dp | 布局 |
| 5 | RTL 支持差（paddingLeft/Right 而非 Start/End） | 布局 |
| 6 | 触控目标尺寸不足（多处 < 48dp） | 无障碍 |
| 7 | `transitionName` 声明但共享元素过渡可能未启用 | 动画 |
| 8 | 列表项入场动画框架存在但从未启用（死代码） | 动画 |
| 9 | 3 种不同加载指示器样式 | UX |
| 10 | 搜索栏高度 30dp，Material SearchBar 推荐 56dp | 搜索 |
| 11 | 非真正 edge-to-edge（setDecorFitsSystemWindows=true） | 系统栏 |
| 12 | `TextInputLayout` 样式不统一，按钮无 primary/secondary 层次 | 表单 |
| 13 | BottomSheet 极少使用，筛选等场景用了全屏 DialogFragment | 对话框 |
| 14 | 完全无 swXXXdp 尺寸适配，无平板布局 | 响应式 |
| 15 | 仅有 4 个 layout-land 文件，关键页面缺横屏适配 | 响应式 |
| 16 | Welcome 页无首次引导流程，新用户无功能发现路径 | 引导 |
| 17 | 权限请求用原生 AlertDialog，与 App 主题风格不一致 | 权限 |
| 18 | Debug 结果无成功/失败颜色区分 | 开发者UI |

### P3 — 代码质量/可维护性

| # | 问题 | 维度 |
|---|------|------|
| 1 | TitleBar 的 0.1f elevation hack | 组件 |
| 2 | AccentBgTextView 缺 disabled 状态 | 组件 |
| 3 | View ID 命名不规范 (iv_ 前缀用于 TextView) | 代码 |
| 4 | Divider 方式三种并存 | 布局 |
| 5 | 无 BaseDialogFragment 基类，60+ 对话框无统一规范 | 对话框 |
| 6 | `grid_group` 和 `grid_group2` 布局完全一致（冗余） | 书架 |
| 7 | `CoverPageDelegate` 阴影 30px 硬编码 | 动画 |
| 8 | overscroll 策略分散 | 滚动 |
| 9 | 详情页无 CollapsingToolbarLayout | 布局 |
| 10 | `dimens.xml` 中 `desc_icon_size=18sp`（图标用 sp） | 排版 |
| 11 | Welcome 页所有文字硬编码，不支持 i18n | 引导 |
| 12 | BadgeView 无数字截断(99+)，大数字撑开 badge | 组件 |
| 13 | FastScroller bubble 无缩放动画 | 组件 |
| 14 | CoverImageView 圆角硬编码 12f，不随主题适配 | 组件 |
| 15 | RssSourceDebug 用原生 SearchView 而非自定义 | 开发者UI |
