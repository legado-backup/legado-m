# Tasks: Android UI/UX 优化

## 1. P0 Bug 修复（阻塞性）

- [x] 1.1 修复 Style.Text.Primary.Normal 暗色不可见（textColor #000 → @color/primaryText）
- [x] 1.2 修复 Style.Text.Second.Normal 暗色不可见（textColor #676767 → @color/secondaryText）
- [x] 1.3 修复 bg_gradient_cover.xml px→dp（12px → 12dp）
- [x] 1.4 修正 shape_radius_10dp.xml 文件名（重命名为 shape_radius_16dp.xml + 全局替换引用）
- [x] 1.5 修复 ic_back.xml viewport 异常（1024×1024 → 24×24，路径坐标同步缩放）
- [x] 1.6 修复 RotateLoading 暗色模式不可见（硬编码 #1a000000 → 跟随主题）
- [x] 1.7 WCAG：tv_text_summary 亮色对比度提升（#8A2C2C2C → #8A000000）
- [x] 1.8 WCAG：accent 暗色对比度提升（#D84315 → #FF5722）
- [x] 1.9 WCAG：primary 亮色对比度提升（#039BE5 → #0277BD）
- [x] 1.10 修复 grid2 书名浅色封面不可读（字色→primaryText + 字号 11sp→12sp + 遮罩加深）
- [x] 1.11 修复自定义 Toast Android 11+ 失效（改用 Snackbar 或系统 Toast 降级）

## 2. Design Token 体系建立

- [x] 2.1 在 dimens.xml 中新增 Corner Radius token（corner_extra_small/small/medium/large）
- [x] 2.2 在 dimens.xml 中新增 Typography Scale token（text_display_small → text_label_small）
- [x] 2.3 在 dimens.xml 中新增 Spacing token（spacing_xs → spacing_xxl，4dp grid）
- [x] 2.4 在 dimens.xml 中新增 Elevation token（elevation_level0 → level5）

## 3. 暗色模式颜色覆盖补全

- [x] 3.1 在 values-night/colors.xml 中补充 highlight 暗色覆盖
- [x] 3.2 在 values-night/colors.xml 中补充 error 暗色覆盖
- [x] 3.3 在 values-night/colors.xml 中补充 success 暗色覆盖
- [x] 3.4 在 values-night/colors.xml 中补充 lightBlue_color 暗色覆盖
- [x] 3.5 替换布局中硬编码色值（activity_book_info.xml #50000000 → 语义色值）

## 4. 关键布局现代化

- [x] 4.1 Ripple 前景化：item_bookshelf_list.xml 独立 View → 根布局 foreground（已存在 vw_foreground）
- [x] 4.2 图标尺寸 sp→dp：activity_book_info.xml 18sp → 18dp + dimens.xml desc_icon_size 18sp→18dp
- [x] 4.3 触控目标补足：activity_search_content.xml 底部栏 36dp → 48dp
- [x] 4.4 BottomNavigationView 高度：activity_main.xml 50dp → 56dp
- [x] 4.5 FAB Elevation 规范化：view_read_menu.xml 2dp → 6dp
- [x] 4.6 封面加载添加 crossfade 过渡动画（BookCover.kt 普通封面加载）
- [x] 4.7 搜索 Activity 添加 windowSoftInputMode=adjustResize|stateHidden

## 5. Drawable 圆角体系统一

- [x] 5.1 创建 shape_corner_extra_small.xml（4dp）、shape_corner_small.xml（8dp）、shape_corner_medium.xml（12dp）、shape_corner_large.xml（16dp）
- [x] 5.2 shape_card_view.xml 圆角从 3dp → 12dp（@dimen/corner_medium）
- [x] 5.3 Popup 背景改用 shape_corner_small（8dp）：popup_seek_bar、popup_action_menu、popup_action

## 6. 图标体系修正

- [x] 6.1 ic_search.xml viewport 从 48×48 归一化到 24×24
- [x] 6.2 ic_share.xml 尺寸从 20dp 统一为 24dp
- [x] 6.3 ic_arrow_down/right.xml 尺寸从 64dp → 24dp
- [x] 6.4 ic_export/import.xml 尺寸从 28dp → 24dp
- [x] 6.5 ic_search_hint.xml 尺寸从 8dp → 12dp
- [x] 6.6 fillColor 统一为 #FF000000：ic_arrow_down、ic_arrow_right、ic_author、ic_book_last、ic_history、ic_export

## 7. 卡片/容器/对话框规范

- [x] 7.1 对话框圆角统一为 12dp（shape_card_view → corner_medium，10个dialog自动升级）
- [x] 7.2 触控目标修复：seek控制24→48dp（view_detail_seek_bar、view_preference_seekbar）
- [x] 7.3 触控目标修复：播放控制30→48dp（dialog_read_aloud 6处）
- [x] 7.4 触控目标修复：列表项操作图标36→48dp+padding 6→12dp（10文件20处）
- [x] 7.5 Popup 背景圆角统一为 8dp（corner_small）

## 8. 验证

- [x] 8.1 自动化验证：10项检查全部通过（styles硬编码色/WCAG色/DesignToken/ShapeCorner/IconSize/BottomNav/SoftInputMode/CrossFade/Toast11+）
- [x] 8.2 构建项目确认无编译错误（✅ assembleAppDebug 构建成功，APK 生成）
- [ ] 8.3 暗色模式视觉验证（需真机验证）
- [ ] 8.4 触控目标 48dp 视觉验证（需真机验证）
- [ ] 8.5 WCAG 对比度真机实测（需真机验证）

---

## 变更文件清单

### XML 布局 (14个)
- activity_book_info.xml、activity_main.xml、activity_search_content.xml
- dialog_read_aloud.xml、dialog_open_url_confirm.xml
- item_bookshelf_grid2.xml、item_bookshelf_list.xml、item_bookshelf_list2.xml
- item_book_source.xml、item_dict_rule.xml、item_http_tts.xml
- item_replace_rule.xml、item_rss_source.xml、item_rule_sub.xml
- item_theme_config.xml、item_server_select.xml、item_toc_regex.xml、item_txt_toc_rule.xml
- popup_seek_bar.xml、popup_action_menu.xml、popup_action.xml
- view_detail_seek_bar.xml、view_preference_seekbar.xml、view_read_menu.xml

### Drawable (12个新建/修改)
- shape_corner_extra_small.xml、shape_corner_small.xml、shape_corner_medium.xml、shape_corner_large.xml（新建）
- shape_card_view.xml、bg_gradient_cover.xml、ic_back.xml
- ic_search.xml、ic_share.xml、ic_arrow_down.xml、ic_arrow_right.xml
- ic_export.xml、ic_import.xml、ic_search_hint.xml
- ic_author.xml、ic_book_last.xml、ic_history.xml

### Kotlin (3个)
- ToastUtils.kt、BookCover.kt、RotateLoading.kt

### Values (4个)
- colors.xml、values-night/colors.xml、styles.xml、dimens.xml

### Manifest (1个)
- AndroidManifest.xml
