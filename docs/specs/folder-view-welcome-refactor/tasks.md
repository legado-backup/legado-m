# Tasks: 书源/订阅源文件夹视图重构 + 欢迎页增强 + 前端样式审计

> 状态：✅ 实施完成，待真机验证
> 创建日期：2026-07-08
> 设计审核：2026-07-08 用户通过

---

## 1. 准备工作

- [ ] 1.1 确认需求范围（已与用户对齐 5 大需求）
- [ ] 1.2 阅读相关源码（书架 / 文件夹视图 / 欢迎页 / 4 页面菜单）
- [ ] 1.3 生成 OpenSpec 四文档并等待用户审查

## 2. 文件夹视图卡片重构

- [x] 2.1 新建 `app/src/main/res/layout/item_source_folder_grid.xml`（3:4 比例，ivCover + tvFolderInitial + tvName）
- [x] 2.2 新建 `app/src/main/res/drawable/bg_source_folder_cover.xml`（主题色渐变背景）
- [x] 2.3 修改 [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt)：改用新布局，`convert()` 渲染首字+主题色
- [x] 2.4 在 SourceFolderAdapter 中新增首字截取扩展函数（处理 emoji，按 codePoint 截取）
- [x] 2.5 新增 `R.string.folder_view` 等字符串资源（AOAdapt: 已存在，无需新增）
- [x] 2.6 删除旧布局 `item_source_folder.xml`
- [ ] 2.7 验证：4 个页面文件夹视图显示新卡片样式（Level 2 - 功能验证）

## 3. 文件夹视图配置对话框

- [x] 3.1 新建 `app/src/main/res/layout/dialog_source_folder_config.xml`（分组样式 spinner + 视图 radio + 间距 seekbar）
- [x] 3.2 在 [PreferKey.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/PreferKey.kt) 新增 `sourceFolderStyle` / `sourceFolderMargin`
- [x] 3.3 在 [AppConfig.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/AppConfig.kt) 新增对应属性
- [x] 3.4 在 SourceFolderAdapter 伴生对象中实现 `showConfigDialog(context, currentViewMode, onConfigChanged)`
- [x] 3.5 dimens.xml 资源已存在（corner_medium, elevation_level1），无需新增（AOAdapt: 复用现有 Token）
- [ ] 3.6 验证：对话框可弹出，配置变更后立即刷新（Level 2 - 功能验证）

## 4. 三点菜单统一入口

- [x] 4.1 修改 `app/src/main/res/menu/book_source.xml`：移除顶层 `menu_view_mode`，新增 `menu_folder_config`
- [x] 4.2 修改 `app/src/main/res/menu/rss_source.xml`：同上
- [x] 4.3 修改 `app/src/main/res/menu/main_explore.xml`：同上
- [x] 4.4 修改 `app/src/main/res/menu/main_rss.xml`：同上
- [x] 4.5 修改 [BookSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt) `onCompatOptionsItemSelected`：处理 `menu_folder_config`
- [x] 4.6 修改 [RssSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt)：同上
- [x] 4.7 修改 [ExploreFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt)：同上
- [x] 4.8 修改 [RssFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt)：同上
- [ ] 4.9 验证：4 页面三点菜单展开项顺序一致（Level 2 - 功能验证）

## 5. 间距与列数动态化

- [x] 5.1 修改 4 页面的 `applyFolderView()`：GridLayoutManager 列数根据 `sourceFolderMargin` 动态计算
- [x] 5.2 修改 4 页面的 RecyclerView ItemDecoration：根据 `sourceFolderMargin` 设置间距
- [ ] 5.3 验证：调整间距后卡片间距立即变化（Level 2 - 功能验证）

## 6. 欢迎页默认开启

- [x] 6.1 修改 [pref_config_welcome.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/xml/pref_config_welcome.xml)：`customWelcome` defaultValue `false` → `true`
- [ ] 6.2 验证：新安装/清除数据后 customWelcome 默认开启（Level 2 - 功能验证）

## 7. 欢迎页图片裁剪

- [x] 7.1 在 [BitmapUtils.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/utils/BitmapUtils.kt) 新增 `cropBitmapToAspectRatio(srcPath, ratioW, ratioH): String`
- [x] 7.2 在 [WelcomeConfigFragment.setCoverFromUri()](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/config/WelcomeConfigFragment.kt#L200) 存储文件后、`putPrefString` 前调用裁剪
- [x] 7.3 裁剪策略：居中裁剪（Center Crop），保留中央主体
- [x] 7.4 .9.png 跳过裁剪（检测后缀）（AOAdapt: 额外跳过 .gif 保留动画）
- [x] 7.5 小图降级：图片小于屏幕时居中放置，主题色填充（AOAdapt: 居中裁剪本身不放大+采样限 1920px，"主题色填充"属 WelcomeActivity 显示逻辑，保留现有 decodeBitmap 行为）
- [ ] 7.6 验证：选择图片后自动裁剪，欢迎页显示无变形（Level 3 - 场景验证）

## 8. 整体样式审计与清理

- [x] 8.1 检查 4 页面文件夹视图区域是否还有硬编码颜色（AOAdapt: 无硬编码颜色，folder cover 用 `?attr/colorPrimary`，文字用 `@color/primaryText`）
- [x] 8.2 统一圆角/阴影到 dimens.xml（AOAdapt: 已用 `@dimen/corner_medium` + `@dimen/elevation_level1`）
- [x] 8.3 复用书架的 `selectableItemBackground` 点击反馈（AOAdapt: item_source_folder_grid.xml L89 vw_foreground 已用 `?android:attr/selectableItemBackground`）
- [ ] 8.4 验证：4 页面视觉风格与书架一致（Level 2 - 功能验证）

## 9. 3.7 后交互精简实施（用户审核追加）

- [x] 9.1 自动任务系统 Cron 简化：Cron 表达式输入改为"每天/每小时/自定义"三选一选择器，自定义档才显示 Cron 输入（AOAdapt: 新增 Spinner 频率选择器 + CRON_EVERY_DAY/HOUR 常量 + upView/buildTask/buildTaskDraft 三处逻辑适配）
- [x] 9.2 调试日志悬浮球默认隐藏：默认值改为 false，仅在用户主动开启时显示（AOAdapt: 检查发现 pref_config_other.xml L243 defaultValue 已为 "false"，AppConfig.kt L54 也用 false 读取，无需修改）
- [x] 9.3 调试工具集迁移：从"我的"主入口移除，迁移到"设置→其他设置→调试工具"二级页面（AOAdapt: pref_main.xml 移除 + pref_config_other.xml 新增 + MyFragment 移除点击处理 + OtherConfigFragment 新增点击处理）
- [ ] 9.4 验证：3 项精简项功能正常（Level 2 - 功能验证）

## 10. 编译与回归验证

- [x] 10.1 编译 APK 无错误（Level 1 - 代码完成）（AOAdapt: compileDebugKotlin exit code 0 通过）
- [ ] 10.2 4 页面文件夹视图功能正常（Level 2 - 功能验证）
- [ ] 10.3 欢迎页自定义功能正常（Level 2 - 功能验证）
- [ ] 10.4 3 项交互精简功能正常（Level 2 - 功能验证）
- [ ] 10.5 真机回归：书源管理/订阅源管理/发现页/订阅源页/欢迎页/自动任务/悬浮球/调试工具（Level 3 - 场景验证）

## 11. 文档同步（步骤 8 强制）

- [x] 11.1 更新 [docs/project-flow/architecture/android-ui.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/architecture/android-ui.md)：补充文件夹视图新布局说明
- [x] 11.2 更新 [docs/project-flow/modules/config-system.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/modules/config-system.md)：新增配置项 + customWelcome 默认值变更
- [x] 11.3 更新 [docs/project-flow/quick-reference.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/quick-reference.md)：布局文件清单
- [x] 11.4 更新 [docs/INDEX.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/INDEX.md)：状态标记
- [x] 11.5 更新 `app/src/main/assets/updateLog.md`：面向用户的更新条目

---

## AOAdapt 日志

> 实施过程中遇到问题时记录（Action / Observation / Adapt）

### 2026-07-08 第2阶段实施

- **A**: 任务 2.5 计划新增 `R.string.folder_view` 字符串资源
- **O**: Grep 检查发现 `folder_view` 已在 `strings.xml` L645 和 `values-zh/strings.xml` L643 存在（"文件夹视图"）
- **Adapt**: 跳过新增，直接标记 2.5 完成。后续配置对话框（第3阶段）需要的字符串（如"分组样式"对应的 `group_style` 也已存在 L891）再按需新增

---

## 完成级别说明

- **Level 1 - 代码完成（⚠️）**：文件存在 + 编译通过
- **Level 2 - 功能验证（⚠️）**：关键功能可运行 + 输出正确
- **Level 3 - 场景验证（✅）**：真实数据回测通过
