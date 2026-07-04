# Design: Android UI/UX 优化

## Technical Approach

### 总体策略：P0 修复 → Token 建立 → 逐步替换 → 现代化微调

采用分层渐进策略，每层可独立验证：

```
Layer 1: P0 Bug 修复（暗色模式可见性、px→dp、文件名修正）
   ↓
Layer 2: Design Token 体系建立（dimens.xml 扩展）
   ↓
Layer 3: 暗色模式颜色覆盖补全
   ↓
Layer 4: 关键布局现代化（Ripple/触控/sp→dp/Elevation）
   ↓
Layer 5: Drawable 圆角体系统一
```

### Layer 1: P0 Bug 修复

#### 1.1 Style.Text.Primary/Second 暗色修复

**当前**：`styles.xml` 中 `Style.Text.Primary.Normal` 和 `Style.Text.Second.Normal` 硬编码 `#000` 和 `#676767`

**方案**：将 textColor 改为引用 `@color/primaryText` 和 `@color/secondaryText`，这两个色值在 `values/colors.xml` 和 `values-night/colors.xml` 中已有正确的明暗值定义。

#### 1.2 bg_gradient_cover.xml px→dp

**当前**：`<corners android:radius="12px" />`

**方案**：改为 `<corners android:radius="12dp" />`

#### 1.3 shape_radius_10dp.xml 文件名修正

**当前**：文件名 `shape_radius_10dp.xml` 但实际值为 16dp

**方案**：将文件重命名为 `shape_radius_16dp.xml`，全局搜索替换引用

### Layer 2: Design Token 体系

在 `app/src/main/res/values/dimens.xml` 中新增 token 定义：

```xml
<!-- ========== Design Tokens: Corner Radius ========== -->
<dimen name="corner_extra_small">4dp</dimen>
<dimen name="corner_small">8dp</dimen>
<dimen name="corner_medium">12dp</dimen>
<dimen name="corner_large">16dp</dimen>
<!-- corner_full 使用 50% 需在代码/drawable 中设置 -->

<!-- ========== Design Tokens: Typography Scale ========== -->
<!-- M3 Typography 子集（项目实际使用的字号） -->
<dimen name="text_display_small">36sp</dimen>
<dimen name="text_headline_medium">28sp</dimen>
<dimen name="text_headline_small">24sp</dimen>
<dimen name="text_title_large">22sp</dimen>
<dimen name="text_title_medium">16sp</dimen>
<dimen name="text_title_small">14sp</dimen>
<dimen name="text_body_large">16sp</dimen>
<dimen name="text_body_medium">14sp</dimen>
<dimen name="text_body_small">12sp</dimen>
<dimen name="text_label_large">14sp</dimen>
<dimen name="text_label_medium">12sp</dimen>
<dimen name="text_label_small">11sp</dimen>

<!-- ========== Design Tokens: Spacing (4dp Grid) ========== -->
<dimen name="spacing_xs">4dp</dimen>
<dimen name="spacing_sm">8dp</dimen>
<dimen name="spacing_md">12dp</dimen>
<dimen name="spacing_lg">16dp</dimen>
<dimen name="spacing_xl">24dp</dimen>
<dimen name="spacing_xxl">32dp</dimen>

<!-- ========== Design Tokens: Elevation ========== -->
<dimen name="elevation_level0">0dp</dimen>
<dimen name="elevation_level1">1dp</dimen>
<dimen name="elevation_level2">3dp</dimen>
<dimen name="elevation_level3">6dp</dimen>
<dimen name="elevation_level4">8dp</dimen>
<dimen name="elevation_level5">12dp</dimen>
```

### Layer 3: 暗色模式颜色覆盖补全

在 `values-night/colors.xml` 中补充缺失的暗色覆盖：

| 色值名 | 亮色值 | 建议暗色值 | 说明 |
|--------|--------|-----------|------|
| `highlight` | #d3321b | #ff6e40 | 提高亮度保证对比度 |
| `error` | #eb4333 | #ff5252 | M2 error 暗色标准值 |
| `success` | #439b53 | #66bb6a | 提高亮度 |
| `lightBlue_color` | #FF578FCC | #FF90CAF9 | 降低饱和度+提高亮度 |
| `tv_text_book_detail` | #dfdfdf | #dfdfdf | 暗色模式下保持 |

### Layer 4: 关键布局现代化

#### 4.1 Ripple 前景化

**当前做法**（`item_bookshelf_list.xml`）：
```xml
<!-- 独立 View 覆盖做 ripple -->
<View android:foreground="?attr/selectableItemBackground" .../>
```

**改进**：在根布局直接设置：
```xml
<LinearLayout ...
    android:foreground="?attr/selectableItemBackground"
    android:background="@color/background">
```
删除独立的 ripple View。

#### 4.2 图标尺寸 sp→dp

搜索所有布局中 ImageView/ImageButton 的 `layout_width`/`layout_height` 使用 sp 的，替换为 dp：
- `activity_book_info.xml` 行162-163: `18sp` → `18dp`

#### 4.3 触控目标补足

- `activity_search_content.xml` 底部栏高度：36dp → 48dp（最小触控目标）
- `item_book_source.xml` 图标：增大 padding 使触控区域 ≥ 48dp

#### 4.4 BottomNavigationView 高度

- `activity_main.xml`：`minHeight="50dp"` → `minHeight="56dp"`

#### 4.5 FAB Elevation 规范化

- `view_read_menu.xml` FAB：`app:elevation="2dp"` → `app:elevation="6dp"`（M 规范 resting）

### Layer 5: Drawable 圆角统一

创建规范命名的 shape drawable 并建立映射：

| 旧 drawable | 圆角值 | 新规范 drawable | token |
|------------|--------|----------------|-------|
| bg_img_border | 1dp | 保留（特殊用途） | — |
| shape_radius_1dp | 1dp | shape_corner_1dp | — |
| bg_popup_menu | 2dp | shape_corner_2dp | — |
| shape_card_view | 3dp | shape_corner_3dp | — |
| shape_translucent_card | 3dp | shape_corner_3dp | — |
| bg_find_book_group | 6dp | shape_corner_6dp | — |
| card_video_background | 8dp | shape_corner_small | corner_small |
| bg_video_chapter_item | 8dp | shape_corner_small | corner_small |
| card_border_background | 12dp | shape_corner_medium | corner_medium |
| shape_fillet_btn | 16dp | shape_corner_large | corner_large |
| shape_pop_checkaddshelf_bg | 15dp | shape_corner_large | corner_large |
| bg_searchview | 35dp | shape_corner_search | — |

## Architecture Decisions

### AD-01: 渐进式 Token 而非全量迁移

- **Context**: 项目 220 个布局 + 70+ 自定义 Widget，全量替换风险极高
- **Concern**: 一次性替换所有硬编码值可能导致大量回归问题，难以定位
- **Decision**: 建立 token 体系但不强制立即替换所有现有值，新代码必须使用 token，旧代码逐步迁移
- **Goal**: 在不引入回归风险的前提下，为后续优化奠定规范基础
- **Tradeoff**: 短期内新旧值并存，代码一致性暂时不够完美
- **Status**: Accepted

### AD-02: 保留 M2 而非迁移 M3

- **Context**: 项目使用 Material Components 1.13.0 (M2)，Theme 继承链基于 AppCompat DayNight
- **Concern**: M3 迁移涉及 Theme 体系全换、组件替换、Dynamic Color 适配，改动量巨大
- **Decision**: 本次仅做 M2 框架内的优化（token + Bug 修复 + 现代化微调），M3 迁移独立立项
- **Goal**: 控制本次改动范围在可验证范围内，避免引入不可控风险
- **Tradeoff**: 无法获得 M3 Dynamic Color、pill indicator 等现代化视觉提升
- **Status**: Accepted

### AD-03: 暗色模式保持色相切换而非统一品牌色

- **Context**: 亮色用 LightBlue+Pink，暗色用 BlueGrey+DeepOrange，完全不同色相
- **Concern**: 统一品牌色会改变暗色模式的整体视觉风格，大量用户已习惯当前配色
- **Decision**: 本次仅补全缺失的暗色覆盖值，不改变亮暗模式的色相选择。色相统一作为 P1 后续任务讨论
- **Goal**: 修复暗色模式 Bug 和缺失覆盖，不破坏现有用户习惯
- **Tradeoff**: 亮暗模式仍看起来像不同 app，未解决根本一致性
- **Status**: Accepted

### AD-04: Drawable 圆角兼容而非强制替换

- **Context**: 20 种圆角值散布在 181 个 drawable 中，强制统一工作量大且可能破坏视觉效果
- **Concern**: 全量替换圆角可能让某些精心调整的视觉效果变差
- **Decision**: 创建规范 token drawable，新代码使用 token drawable；旧 drawable 暂时保留但标记 @Deprecated 注释
- **Goal**: 建立规范体系，允许过渡期共存
- **Tradeoff**: drawable 目录暂时膨胀（新旧并存）
- **Status**: Accepted

## Data Flow

```
用户操作（切换暗色模式/调整字体）
   ↓
Android 资源系统（values-night/ 覆盖 / sp 缩放）
   ↓
Theme 资源解析（AppCompat DayNight → primaryText/secondaryText）
   ↓
布局渲染（XML 引用 @color/@dimen/@drawable token）
   ↓
Widget 绘制（TitleBar/自定义 View 应用 Theme 属性）
```

本次优化主要影响 **资源层**（values/ 和 drawable/），不改变渲染和绘制逻辑。

## File Changes

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `app/src/main/res/values/styles.xml` | 修改 | Style.Text.Primary/Second 的 textColor 改为 @color/ 引用 |
| `app/src/main/res/values/dimens.xml` | 修改 | 新增 corner/text/spacing/elevation token |
| `app/src/main/res/values-night/colors.xml` | 修改 | 补充 highlight/error/success/lightBlue_color 暗色覆盖 |
| `app/src/main/res/drawable/bg_gradient_cover.xml` | 修改 | 12px → 12dp |
| `app/src/main/res/drawable/shape_radius_10dp.xml` | 重命名 | → shape_radius_16dp.xml |
| `app/src/main/res/layout/activity_main.xml` | 修改 | BottomNavigationView 高度 50dp → 56dp |
| `app/src/main/res/layout/activity_book_info.xml` | 修改 | 图标尺寸 sp→dp、硬编码色值替换 |
| `app/src/main/res/layout/activity_search_content.xml` | 修改 | 底部栏高度 36dp → 48dp |
| `app/src/main/res/layout/item_bookshelf_list.xml` | 修改 | Ripple 前景化 |
| `app/src/main/res/layout/view_read_menu.xml` | 修改 | FAB elevation 2dp → 6dp |
| `app/src/main/res/drawable/shape_corner_small.xml` | 新增 | 8dp 圆角规范 drawable |
| `app/src/main/res/drawable/shape_corner_medium.xml` | 新增 | 12dp 圆角规范 drawable |
| `app/src/main/res/drawable/shape_corner_large.xml` | 新增 | 16dp 圆角规范 drawable |
| `app/src/main/res/drawable/ic_back.xml` | 修改 | viewport 1024→24 归一化，路径坐标缩放 |
| `app/src/main/res/drawable/ic_search.xml` | 修改 | viewport 48→24 归一化 |
| `app/src/main/res/drawable/ic_share.xml` | 修改 | 尺寸 20dp→24dp |
| `app/src/main/res/values/colors.xml` | 修改 | tv_text_summary 色值提升对比度、primary 暗化 |
| `app/src/main/res/layout/item_bookshelf_grid2.xml` | 修改 | 书名字色/字号/遮罩修复 |
| `app/src/main/java/io/legado/app/ui/widget/anima/RotateLoading.kt` | 修改 | 阴影色跟随主题 |
