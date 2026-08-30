# Spec: Android UI/UX 优化

## Intent

深度分析开源阅读（Legado）项目 Android 前端的 UI/UX 质量，识别布局和样式优化点，产出结构化优化方案，使界面更加美观、一致、现代，并修复暗色模式下的可见性 Bug。

## Scope

### In Scope（本次范围）

1. **P0 阻塞性 Bug 修复**：暗色模式下文字不可见、px/dp 混用、文件名与实际值不匹配
2. **P1 视觉一致性优化**：建立统一的圆角/字号/间距/Elevation token 体系
3. **P2 现代化改进**：Ripple 前景化、Elevation 规范化、触控目标达标、sp→dp 修正
4. **暗色模式完善**：颜色覆盖完整性、硬编码色值清理
5. **分析报告**：产出完整的问题清单和优化建议

### Out of Scope（不在本次范围）

- **M2 → M3 主题迁移**：涉及面太广（需替换 Theme 继承链、所有 M2 组件→M3 组件、Dynamic Color 适配），独立任务
- **Compose 迁移**：项目 0% Compose，全量迁移不在本次范围
- **功能逻辑变更**：仅优化视觉表现，不改变功能行为
- **新增 UI 功能/页面**：不新增页面或组件
- **性能优化**：布局层级优化、过度绘制等不在本次范围
- **i18n/l10n**：多语言相关问题不在本次范围

## Approach

### Selected Approach：渐进式 Design Token 体系 + Bug 修复 + 现代化微调

**理由**：
- 项目已有 220 个 XML 布局和 70+ 自定义 Widget，一次性重写不现实
- 渐进式 token 化能让每个改进独立可验证，降低回归风险
- P0 Bug 必须立即修复，P1 token 建立后后续布局可逐步迁移
- 现代化微调（Ripple/Elevation/触控目标）改动小、收益高

**具体方案**：
1. 修复 P0 Bug（硬编码色值、px→dp、文件名修正）
2. 建立 Design Token 体系（dimens.xml 扩展：圆角/字号/间距/Elevation token）
3. 建立 Shape 体系（drawable 按规范圆角值统一）
4. 暗色模式颜色覆盖补全
5. 关键布局现代化（Ripple foreground、触控目标、sp→dp）

### Alternatives Considered

| 方案 | 优点 | 缺点 | 否决理由 |
|------|------|------|---------|
| **A. 全量 M3 迁移** | Dynamic Color、统一 shape/typography 系统、长期收益最大 | 涉及 50+ Activity、220 布局、70+ Widget、Theme 继承链全换；测试回归量巨大；Android 6 兼容性需验证 | 改动量超出本次范围，风险不可控，应独立立项 |
| **B. Compose 重写核心页面** | 现代声明式 UI、Preview 工具、动画系统 | 项目 0% Compose 基础，需从零搭建；与现有 View 体系双轨并行增加维护成本 | 投入产出比极低，需先建立 Compose 基础设施 |
| **C. 仅修 P0 Bug，不做 token 体系** | 最小改动 | 不解决 P1 一致性问题，后续开发者仍会随意写硬编码值 | 治标不治本，P1 问题会持续恶化 |
| **D. 引入 UI 设计系统库（如 Material Components 主题覆写）** | 标准化程度高 | 项目已有大量自定义 Widget，覆写可能导致样式冲突；引入新依赖增加包体积 | 过度设计，项目已有 Theme 引擎（ATE），无需额外依赖 |

### Drawbacks

1. **Token 体系不会立即生效于所有布局**：建立 token 后，现有布局中的硬编码值需逐步替换，短期内新旧并存
2. **不解决 M2→M3 差距**：仍停留在 M2 设计语言，视觉上无法达到 M3 的现代感（Dynamic Color、pill indicator 等）
3. **圆角统一可能破坏现有视觉习惯**：部分用户已习惯当前的视觉风格，统一圆角后外观有变化
4. **暗色模式颜色覆盖补全可能导致部分界面色彩微调**：补全缺失的暗色覆盖值后，某些界面在暗色模式下颜色会有变化

**接受理由**：以上 drawbacks 均为渐进式改进的合理代价，P0 Bug 修复收益远大于风险，token 体系为后续优化奠定基础。

### Prior Art

- [Material Design 3 Shape System](https://m3.material.io/foundations/shape)：Small(8dp)/Medium(12dp)/Large(16dp) 三级圆角
- [Material Design 3 Elevation](https://m3.material.io/styles/elevation/overview)：5 级层级系统
- [Material Design 3 Typography](https://m3.material.io/styles/typography/overview)：15 级字号 scale
- Android 4dp baseline grid：间距必须为 4 的倍数

## Requirements

### REQ-01: P0 Bug 修复

- `Style.Text.Primary.Normal` 和 `Style.Text.Second.Normal` 的 textColor 必须使用语义色值（`?attr/primaryText` 或 `@color/primaryText`），禁止硬编码 `#000` / `#676767`
- `bg_gradient_cover.xml` 的 `12px` 必须改为 `12dp`
- `shape_radius_10dp.xml` 要么重命名匹配实际值，要么修正值为 10dp

### REQ-02: Design Token 体系

- 圆角 token：在 `dimens.xml` 中定义 `corner_extra_small`(4dp)、`corner_small`(8dp)、`corner_medium`(12dp)、`corner_large`(16dp)、`corner_full`(50%)
- 字号 token：定义 `text_display_large`(57sp)→`text_label_small`(11sp) 共 13 级 M3 Typography scale（取项目实际用到的子集）
- 间距 token：基于 4dp grid，定义 `spacing_xs`(4dp)、`spacing_sm`(8dp)、`spacing_md`(12dp)、`spacing_lg`(16dp)、`spacing_xl`(24dp)、`spacing_xxl`(32dp)
- Elevation token：定义 `elevation_level0`(0dp)→`elevation_level5`(12dp)

### REQ-03: 暗色模式颜色覆盖补全

- `values-night/colors.xml` 必须覆盖 `values/colors.xml` 中所有语义色值
- 布局中硬编码的 `#50000000` 等色值替换为语义色值或 `?attr/` 引用
- 高亮色（highlight/error/success/lightBlue_color）在暗色模式下需有对应覆盖值

### REQ-04: 关键布局现代化

- Ripple 效果：列表项从独立 View 覆盖改为 `android:foreground="?attr/selectableItemBackground"`
- 图标尺寸：`18sp` → `18dp`（图标不应随字体缩放）
- 触控目标：最小 48dp，补足不足区域
- BottomNavigationView：高度从 50dp → 56dp（unlabeled 标准值）
- FAB elevation：从 2dp → 6dp（M 规范 resting 状态）

### REQ-05: 圆角 Drawable 统一

- 梳理 20 种圆角值，映射到 token 体系
- 废弃 `shape_radius_1dp`、`shape_radius_10dp`（命名不规范的），替换为 `shape_corner_extra_small`、`shape_corner_small` 等

### REQ-06: WCAG 无障碍色值修正

- `tv_text_summary` 亮色值从 `#8A2C2C2C`(~3.3:1) 提升至 ≥ 4.5:1 对比度，建议改为 `#8A000000`(54%纯黑，~4.6:1)
- `primary` 色 `#039BE5` 亮色对比度不足(~3.7:1)，暗化至 `#0277BD`(light_blue_800, ~5.0:1)
- `accent` 暗色值 `#D84315` 对比度不足(~4.0:1)，提亮至 `#FF5722`(deep_orange_500, ~5.5:1)

### REQ-07: 图标体系修正

- `ic_back.xml` viewport 从 1024×1024 归一化到 24×24，路径坐标同步缩放
- `ic_search.xml` viewport 从 48×48 归一化到 24×24
- `ic_share.xml` 尺寸从 20dp 统一为 24dp
- 向量图标 fillColor 统一为 `#FF000000`（M 规范），通过布局中 `app:tint` 控制主题色

### REQ-08: RotateLoading 暗色模式修复

- `RotateLoading.kt` 阴影色从硬编码 `#1a000000` 改为跟随主题（`?attr/shadowColor` 或基于 background 计算暗色）

### REQ-09: 书架 grid2 可读性修复

- `item_bookshelf_grid2.xml` 书名叠加在封面上，渐变遮罩范围扩大或加深
- 字色从 `@color/md_dark_primary_text`(纯白) 改为 `@color/primaryText`（跟随主题）
- 字号从 11sp 提升至 12sp（中文最小可读字号）

### REQ-10: 卡片容器规范统一

- `shape_card_view.xml` 圆角从 3dp 提升至 8dp（M2 card 标准）或 12dp（M3 card 标准）
- 对话框圆角统一为 `corner_medium`(12dp)，popup 保持 `corner_small`(8dp)
- 空状态增强：从纯文字 TextView 升级为图标+标题+描述+CTA 的统一组件

## Scenarios

### S1: 用户切换暗色模式

**Before**：`Style.Text.Primary.Normal` 的 `#000` 在暗色背景下文字不可见  
**After**：使用 `@color/primaryText`，暗色模式下自动变为 `#ffffffff`，文字清晰可见

### S2: 用户增大系统字体

**Before**：图标尺寸 `18sp` 随字体放大，布局错乱  
**After**：图标尺寸 `18dp`，不随字体偏好变化

### S3: 开发者新增列表项布局

**Before**：随意硬编码 `android:textSize="14sp"` `android:padding="10dp"`，与其他布局不一致  
**After**：引用 `@dimen/text_body_large` `@dimen/spacing_sm`，保持全项目一致

### S4: 不同密度屏幕查看书籍封面

**Before**：`bg_gradient_cover.xml` 圆角 `12px`，在 xxhdpi 屏幕上圆角只有 4dp 效果  
**After**：圆角 `12dp`，在所有密度屏幕上一致

### S5: 触控列表项

**Before**：搜索栏底部区域 36dp 高度，手指难以精准触控  
**After**：最小触控区域 48dp，符合 M 规范无障碍要求
