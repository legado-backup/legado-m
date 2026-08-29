# Tasks：视频播放器体验五项修复

> 执行顺序：按节顺序串行；1.x 准备 → 2.x 实现 → 3.x 验证 → 4.x 交付同步。
> 验证门禁：核心变更编译通过（Level 1）+ 模拟器运行验证（Level 2）+ 真实场景回测（Level 3）。

## 1. 准备工作

- [x] 1.1 阅读 `VideoFragment.kt` 相关段落（bindViews / handleSlideSeekMove / onFullScreenChanged / overlay 显隐组） ✅
- [x] 1.2 阅读 `VideoSettingsPanelContent.kt` 全文结构（分区/取色点/SingleChoiceDialog 模式）与 `AppDialogFrame` / `rememberAppDialogStyle` API ✅
- [x] 1.3 确认 `video_config` prefs 既有 key 清单，避免命名冲突 ✅（无 seekSensitivity 冲突）

## 2. 核心实现

### P2 前置（存储层先行，供 P3 UI 接入）

- [x] 2.1 `VideoPlay.kt` 新增 `seekSensitivity` 属性（Int 5/7/10/15/20，默认 10，持久化 video_config） ✅ L1

### P3 配置弹框规范对齐

- [x] 2.2 `SettingsDialog.kt` 内容接入 `AppDialogFrame` + `rememberAppDialogStyle()` 规范壳，确认与 `VideoSettingsPanelContent` 内部滚动的嵌套参数化（滚动嵌套禁令） ✅ L1（scrollContent=false，内容自身 verticalScroll+heightIn(540) 单层滚动；title=video_settings_title；actions 空）
- [x] 2.3 `VideoSettingsPanelContent.kt` 取色同源治理：`MaterialTheme.colorScheme.*` → `themeUiPalette`（cardColor/secondaryText 等），BottomSheet 版共享组件同步生效 ✅ L1（Grep 确认 colorScheme 0 残留，仅注释提及）

### P2 滑动灵敏度（UI 层 + 计算层）

- [x] 2.4 `VideoSettingsPanelContent.kt` 播放设置区新增"滑动快进灵敏度"设置行 + `SingleChoiceDialog` 五档选择（0.5x/0.7x/1.0x/1.5x/2.0x），变更即写回 `VideoPlay.seekSensitivity` ✅ L1（PanelSelection.SeekSensitivity）
- [x] 2.5 `strings.xml`（含 values-zh）新增灵敏度设置文案 ✅ L1（默认 values 为中文，其他语言 fallback）
- [x] 2.6 `VideoFragment.handleSlideSeekMove` seek offset 计算乘 `seekSensitivity / 10f` 系数 ✅ L1

### P1 本地视频隐藏下载按钮

- [x] 2.7 `VideoFragment` 视图绑定后初始化段：`VideoPlay.videoUrl` 以 `file://` 开头时 `btnDownload.gone()` ✅ L1

### P4 全屏标题移位

- [x] 2.8 `fragment_video.xml` 新增 `tv_title_fullscreen`（左上角返回按钮右侧，垂直居中，单行省略，默认 gone） ✅ L1
- [x] 2.9 `VideoFragment` 新增 `tvTitleFullscreen` 绑定 + 统一 `setTitle(text)` 方法；三处赋值点（`updateVideoTitle` / 集数切换 / 初始化）收敛到 `setTitle` ✅ L1（实际收敛 4 处含 updateEpisodeSelector；Grep 确认 tvVideoTitle?.text 仅剩 setTitle 内部一处）
- [x] 2.10 `VideoFragment.onFullScreenChanged` 切换双标题显隐（全屏：fullscreen 标题显示+左下角标题隐藏；退出反向）；`tvTitleFullscreen` 加入 overlay controls 显隐组（3 秒自动隐藏） ✅ L1（AOAdapt：发现 showControlsAnimated 无条件 visible GONE 控件，非全屏单击会误显全屏专属控件（B1+ 存量隐患被 P4 放大）→ 修正为 getOverlayControls 按 currentState==FULLSCREEN 过滤全屏专属控件）

### P5 返回按钮尺寸

- [x] 2.11 `fragment_video.xml` `btn_back_overlay` padding 12dp → 14dp（图标净 20dp） ✅ L1

## 3. 验证

- [x] 3.1 编译验证：`compileAppDebugKotlin` 通过（Level 1） ✅ BUILD SUCCESSFUL 12m45s（AOAdapt：首次失败=C:\Users\shiyq\.gradle transforms 缓存损坏 metadata.bin，切 GRADLE_USER_HOME=F:\gh 后通过；非代码错误）
- [ ] 3.2 模拟器 L2 验证（测试包 `io.legado.miss.app.debug`）：⚠️ 待真机/模拟器（依赖 MEmu 模拟器拉起）
  - 下载管理播放本地视频 → 下载按钮不显示（S1）；在线订阅源播放 → 下载按钮显示（S2）
  - 设置弹框不透明、圆角/取色随主题（S5）；BottomSheet 入口视觉一致（S5）
  - 灵敏度选择 0.5x/2.0x 滑动 seek 生效，重启保持（S3）
  - 全屏标题在返回键右侧、随 3 秒自动隐藏、退出恢复左下角（S4）；线路/集数选择器正常
  - 全屏返回按钮图标视觉对齐非全屏顶栏
- [x] 3.3 回归检查：手势体系不受影响（上下滑切视频/长按倍速/双击暂停——仅 seek offset 一行乘系数，方向锁定/阈值逻辑未动）；Grep 确认无调试日志残留 ✅（video 目录 Log.d/e 均为 WebViewVideoPlayer 存量永久日志，本会话零新增）

## 4. 交付同步

- [x] 4.1 基于 git diff 更新 `updateLog.md`（编译前完成） ✅（注意：工作区混有其他会话在途变更，updateLog 仅登记本会话 6 文件变更）
- [ ] 4.2 打测试包并真机/模拟器安装验证 ⚠️ 待执行（依赖 3.2）
- [x] 4.3 文档同步：`docs/INDEX.md` 状态更新；如 AppDialogFrame 接入有新经验沉淀到 `ui-standards/dialog-shell.md` ✅（INDEX 已登记；经验沉淀：scrollContent=false 与内容自滚动隔离 + 全屏专属控件显隐组过滤，见 AOAdapt）
- [x] 4.4 构建后执行 `stop-daemons.bat` 清理 daemon ✅ [OK] Build daemons stopped

## AOAdapt 日志

- **2.2**：设计预估 AppDialogFrame 无必填 title/actions，实际签名 `AppDialogFrame(title, modifier, message, scrollContent, messageInContent, content, actions)` 必填 title+actions → 接入方式调整为 title=video_settings_title、actions={}（空 Row 仅多 16dp 底部留白）；新增 showDragHandle 参数隐藏 BottomSheet 专属拖拽手柄
- **2.10**：发现 `showControlsAnimated()` 无条件 visible 所有 GONE 控件——非全屏态单击屏幕会误显全屏专属控件（btnBackOverlay 存量隐患，P4 新增 tvTitleFullscreen 会放大）→ getOverlayControls 按 `currentState == PlayState.FULLSCREEN` 过滤全屏专属控件，显隐严格受全屏态控制
- **3.1**：首次编译 BUILD FAILED 20s——`Could not read workspace metadata from C:\Users\shiyq\.gradle\caches\8.14.4\transforms\...\metadata.bin`（Gradle transforms 缓存损坏，非代码错误）→ 切 `GRADLE_USER_HOME=F:\gh`（对齐 build-legado.bat）后 BUILD SUCCESSFUL 12m45s
