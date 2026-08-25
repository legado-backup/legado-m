# tasks.md — 子页面头部统一：全 App TitleBar 子页迁移 MainTopBarView

## 1. 组件扩展（Mode.SUB）

- [ ] 1.1 `MainTopBarView` 新增 `Mode.SUB`，`titleSelect` 子页态显示「标题 + 返回箭头」
- [ ] 1.2 暴露 `setMenu` / `setSubtitle` / `setContentLayout` API（等价替代 `TitleBar` 对应能力）
- [ ] 1.3 返回箭头接线 `onBackPressedDispatcher`；`Mode.SUB` 按钮可见性按需配置
- [ ] 1.4 `Mode.SUB` 样式全程读取 `TopBarConfig` + 主题 token，无硬编码颜色
- [ ] 1.5 编译通过后回归验证主 Tab 页（书架/订阅/发现/我的）不受影响

## 2. 批次 A：列表/管理页迁移

> 实施结论：以下列表条目中 Compose 化页面豁免（头部由 Compose 自绘、`title_bar` 已 GONE，套 MainTopBarView 将破坏其头部）；复用 `activity_theme_manage` 共享布局的 12 个"我的"子页（不属于下列清单）已随共享布局一并迁移并编译通过。

- [x] 2.1 `activity_book_source`（书源管理）— 豁免：Compose `AppManagementScaffold` 自绘头部，titleBar GONE
- [x] 2.2 `activity_rss_source`（RSS 管理）— 豁免：Compose `AppManagementScaffold` 自绘头部，titleBar GONE
- [x] 2.3 `activity_cache_manage`（缓存管理）— 已迁移 MainTopBarView(Mode.SUB)+action 插槽
- [x] 2.4 `activity_read_record`（朗读记录）— 豁免：Compose `ReadRecordScreen` 宿主，titleBar/topBar GONE
- [x] 2.5 `activity_theme_manage`（主题管理）— 已迁移；共享布局复用页（TopBarManage/NavigationBarManage/BubbleManage/AppearanceKit/AppearanceKitEdit/AdvancedTitle/BookInfo/ShareNoteTemplate/ReadMenuButtonManage/ReadAloudBgmManage/ParagraphRuleManage/AiReadAloudUsage/DiscoverySuiteManage）一并迁移
- [~] 2.6 批次 A 编译通过（assembleAppDebug SUCCESS）；真机回归（返回/菜单/标题/主题切换）待设备

## 3. 批次 B：编辑页迁移

> 实施结论：`rule_sub` / `ai_image_provider_edit` / `replace_rule` 为 Compose `AppManagementScaffold`/自绘 Screen 宿主（运行时移/隐 TitleBar），豁免。

- [x] 3.1 `activity_book_source_edit`（书源编辑，15+ 菜单）— 已迁移 MainTopBarView(Mode.SUB)，菜单由 moreButton 弹 PopupMenu（source_edit）
- [x] 3.2 `activity_paragraph_rule_edit`（段落规则编辑）— 已迁移（批次 B 早前完成）
- [x] 3.3 `activity_replace_rule`（替换规则）— 豁免：Compose `AppManagementScaffold` 自绘头部
- [x] 3.4 `activity_rule_sub`（订阅规则）— 豁免：Compose `AppManagementScaffold` 自绘头部
- [x] 3.5 `activity_ai_image_provider_edit`（AI 图片源编辑）— 豁免：Compose `AiImageProviderEditScreen` 自绘头部
- [~] 3.6 批次 B 编译通过（compileAppDebugKotlin SUCCESS）；真机回归待设备

## 4. 批次 C：详情/杂项页迁移

> 实施结论：`s3_container_manage` 为 Compose `S3ContainerManageScreen` 宿主（运行时 removeAllViews 移除含 TitleBar 全部子 View），豁免。

- [x] 4.1 `activity_about`（关于）— 已迁移 + 复杂菜单
- [x] 4.2 `activity_explore_show`（探索详情）— 已迁移 + 页码/排序菜单
- [x] 4.3 `activity_cover_collection_detail`（封面收藏详情）— 已迁移
- [x] 4.4 `activity_cover_collection_manage`（封面收藏管理）— 已迁移
- [x] 4.5 `activity_s3_container_manage`（S3 容器管理）— 豁免：Compose `S3ContainerManageScreen` 自绘头部
- [x] 4.6 `activity_source_debug`（源调试，view_search 搜索）— 已迁移 MainTopBarView(Mode.SUB)，搜索框解耦独立驻留 + moreButton 弹 PopupMenu（book_source_debug）
- [x] 4.7 `activity_ai_image_gallery`（AI 图片画廊）— 已迁移
- [~] 4.8 批次 C 编译通过（compileAppDebugKotlin SUCCESS）；真机回归待设备

## 5. 收尾验证

- [x] 5.1 全量回扫：Grep 确认无 `TitleBar` 页面级非豁免残留。剩余 `TitleBar` 均在豁免/Out-of-Scope 清单：`activity_ai_image_provider_edit`/`activity_book_source`/`activity_rss_source`/`activity_replace_rule`/`activity_rule_sub`/`activity_s3_container_manage`/`activity_read_record`（Compose 自绘头部宿主，titleBar 运行时 GONE/移除）、`dialog_cache_chapters`/`view_manga_menu`（弹窗）、`fragment_explore`（发现经典主 Tab 变体，spec Out-of-Scope 单独评估，未迁）
- [x] 5.2 `updateLog` 已同步（书源编辑/调试页条目）；`docs/INDEX.md` 已登记本 spec；批次 A/B/C 全量编译通过（assembleAppDebug SUCCESS）

## 5.3 评估 `TitleBar.kt` 废弃

- [ ] 5.3.1 评估 `TitleBar.kt` 废弃（记录决策，本次不强制删除）

## 5.4 测试包与真机回归

- [x] 5.4.1 重打测试包：`output/apk/test/legado_miss_app_3.26.082423.apk`（io.legado.miss.app，标准 debug 签名，BUILD SUCCESS 4m32s）
- [ ] 5.4.2 批次 A/B/C 各页真机回归（返回/菜单/标题显示/主题切换跟随刷新，含夜间切换）待设备
- [ ] 5.4.3 残留调试日志确认（Grep `android.util.Log.d|Log.e` 0 残留）
- [ ] 5.4.4 主题设置变更 → 已迁移子页面头部跟随刷新（含夜间切换，真机验证）

## AOAdapt 日志

- 待实施阶段记录：遇到问题按 `Action → Observation → Adapt` 追加。