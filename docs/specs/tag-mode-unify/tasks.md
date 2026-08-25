# tasks.md — 书架订阅标签样式统一

> 状态图例：`- [ ]` 待办 ｜ `- [x]` 完成（⚠️/✅ 完成级别）。全程记录 AOAdapt 日志。

## 1. 准备工作
- [x] 1.1 复核需求范围与参考实现（Rimchars/订阅 BookshelfFragment1 顶栏接线），确认已调研（✅ design.md Prior Art + 读透当前 BookshelfScreen/BookshelfFragment1/BaseBookshelfFragment/RssFragment）
- [x] 1.2 确认 `MainTopBarView` BOOKSHELF 模式下 `titleSelect`/`primaryBar`/`tagsBar`/`filterToggleButton` 可用性（✅ 组件存在且为同一套，与订阅同源）
- [x] 1.3 定位 `BookshelfScreen` 中 `BookGroupTabs`/`topBarVersion`/`readableTagColor` 引用面（✅ 仅 style1 使用 topBarVersion；style2 用 isFolder 不传；readableTagColor 仅 BookGroupTabs 私有使用）+ 依赖核验无阻塞（ModernActionPopup.show/BookTagHelper/RoundedTagBarView API 均可用）

## 2. 核心实现
- [x] 2.1 `BookshelfScreen.kt`：删除 `BookGroupTabs` Composable 与 `topBarVersion` 入参、`readableTagColor` 辅助（若仅此处使用）
- [x] 2.2 `BookshelfFragment1.kt`：更新 `BookshelfContent` 调用，去掉 `topBarVersion`/`isFolder` 外不必要的分组 Tab 参数
- [x] 2.3 `BookshelfFragment1.kt`：接入顶栏 `primaryBar`（`setPrimaryItems(groups, idx)`）+ 点击切换分组
- [x] 2.4 `BookshelfFragment1.kt`：接入 `titleSelect` 动态标题 + 向下箭头 + `showGroupSwitchMenu()`（`ModernActionPopup` 全分组，选中 `✓`）
- [x] 2.5 `BookshelfFragment1.kt`：接入 `tagsBar`（`BookTagHelper` 提取 `customTag` 标签 + 「全部」占位）+ 点击按标签过滤
- [x] 2.6 `BaseBookshelfFragment.initComposeTopBar()`：改为支持动态分组标题并启用 `titleSelect`/`primaryBar`/`tagsBar`（bookshelf 场景）
- [x] 2.7 处理 `TOP_BAR_CHANGED`/主题变更在 View 层顶栏自动刷新（移除 Compose `topBarVersion` 依赖）——MainActivity `refreshMainTopBars(root)` 递归 refreshStyle + `onAttachedToWindow` re-apply
- [x] 2.8 处理结构变更事件（`BOOKSHELF_STRUCTURE_CHANGED`/`BOOKSHELF_REFRESH`）重建分组数据与书本标签

## 2.9 文档复核修正（2026-08-24 14:11 用户选择"先审查设计文档"）
- [x] 清除 `BookshelfScreen.kt` 空 `else if (bookGroups.size > 1)` 死分支
- [x] 修正 `fragment_bookshelf1.xml` 过期注释（BookGroupTabs → titleSelect/primaryBar）
- [x] 核对"可被主题/顶栏设置管理"刷新链路闭环（TOP_BAR_CHANGED → refreshAppearanceKit → refreshMainTopBars → topBar.refreshStyle）

## 3. 验证
- [x] 3.1 编译通过（`./gradlew compileAppDebugKotlin`）
- [ ] 3.2 真机验证：书架 style1 分组胶囊、标题下拉菜单、书本标签过滤、右侧向下展开按钮
- [ ] 3.3 真机验证：订阅页标签观感与书架一致
- [ ] 3.4 真机验证：单分组/空标签/分组结构变更边界
- [x] 3.5 updateLog.md 已更新（编译前）
- [ ] 3.6 清理临时代码与调试日志（`Grep` 确认 0 残留）

## 4. 文档同步
- [x] 4.1 更新 `docs/INDEX.md` 状态
- [ ] 4.2 若涉及模块结构/功能说明同步 `docs/project-flow/`（按映射表核对，本次为 UI 改动，无 DB/规则/网络变更）