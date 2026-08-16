# L-D9 视频播放器（VideoPlayer）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P2-reader.md`（S5 全屏沉浸页范式），本文只写「继承 + 差异」。开发本页只读本文档 + P2 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：VideoPlayerActivity + VideoFragment（`ui/video/`，1702+1392 行，ViewPager2 垂直 + GSYVideoPlayer + ExoPlayer + WebView 降级）
- **所属族文档**：`pages/P2-reader.md`
- **骨架归类**：S5 全屏沉浸页
- **对应 task**：tasks.md `12.4B`；pages-inventory D9（优先级 P2）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S5 全屏沉浸页（见 P2 §2）：全屏 + 顶栏/底栏菜单 + 单态弹层 + 3s 自动隐藏 + BackHandler 优先级链
- 复用组件（§3.4）：`AppModalBottomSheet`、`AppTextDialog`、`ConfirmDialog`、`AppSelectDialog`
- 复用状态范式：正文层（视频引擎）零改动 + 菜单层 AnimatedVisibility 浮现 + 播放历史 PlayHistoryStore 状态快照

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 播放模式 | 三播放模式：文章模式上下滑动 / 集数模式 / 书源单 URL 禁滑 | 独有 |
| 分页加载 | 文章分页加载（滑到末篇 loadMoreArticles + 80% 预缓冲 preloadNextArticleHtml 5s 轮询） | 独有 |
| 线路/集数 | tvRouteSelector PopupMenu + rv_episodes + 底部 chapters/volumes 横向 | 独有 |
| 播放控制 | 倍速 Spinner 1x/2x/3x/5x/10x + 快进退 -30/-10/+10/+30s + 调试面板 + 播放地址复制 | 独有 |
| 弹层 | VideoSettingsPanel BottomSheet：线路/倍速/悬浮窗/编辑源/日志 | 独有 |
| 全屏 | isPortraitVideo 旋转 + titleBarNew gone 真全屏 + onUserLeaveHint 画中画 + 双指缩放 | 独有 |
| 降级链 | **四级降级**：L1 Exo→L2 重试→L3 WebView→L4 系统浏览器；playerType=2 自动降级不弹窗；ErrorMapper + FirstFramePreloader | 独有 |
| 历史 | PlayHistoryStore.save/load（10s 定时 + onPause 保存 + >10s 延时 seekTo）；状态快照（8 实例快速切换防串扰） | 独有 |
| 书源模式 | 封面简介 useweb/usehtml/md + 目录 showToc + 卷 showVolumes + 菜单自定义按钮/换源/登录/复制 URL/浏览器打开/外部播放器 | 独有 |
| 订阅源 | 收藏/刷新 recreate/换源对话框 | 独有 |
| 悬浮窗 | startFloatingWindow→VideoPlayService（overlay 权限先检后启） | 独有 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppModalBottomSheet` | L1 浮层面板容器 | VideoSettingsPanel |
| `AppTextDialog` | Markwon 渲染、内容 maxHeight 70% | 调试面板/网页日志 |
| `AppSelectDialog` | RadioButton primary 高亮 | 换源对话框 |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp、destructive 确认钮 error | 退出/清历史确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `FirstFramePreloader` | FirstFramePreloader 首帧加载态 |
| 空态/错误 | 四级降级链错误分支 + 重试 | 四级降级链错误分支 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；播放控制触控 ≥48dp；手势（单击/双击/长按/滑动/双指）需 contentDescription 补充

## 6. 验收标准（轻量）

- [ ] 复用 S5 骨架 + 视频引擎零改动，无私有复制组件
- [ ] 功能点对照 pages-inventory D9 无遗漏（三模式/分页预缓冲/线路集数/播放控制/全屏画中画/四级降级/历史快照/书源订阅源模式/悬浮窗）
- [ ] 手势全部实现；三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-16：视频设置对话框（`VideoPlayerActivity` 设置菜单 / `OtherConfigFragment` 视频设置入口）Compose 化：`SettingsDialog` 保留 DialogFragment 壳，`dialog_video_settings.xml` 精简为 ComposeView 宿主，共享 `VideoSettingsPanelContent` 内容组件（长按倍速/自动播放/直接全屏/底部进度条/静音/缓存播放/缓存容量 100% 保留）
- 2026-08-16：视频设置弹框 Compose 化（task 12.4B 深化）：`VideoSettingsPanel` 保留 BottomSheetDialogFragment 壳 + `VideoSettingsPanelContent` Compose 内容，全分区（播放控制/信息/功能/调试/设置/优化）改用 `SettingsToggleRow`/`SettingsClickRow`/`SingleChoiceDialog`/`PanelButton`；删除 `layout_video_settings_panel.xml` 及 `bg_settings_panel`/`bg_drag_handle` 死资源；功能 100% 保留
- 2026-08-13：初始建立（关联 pages-inventory D9），task 12.4B
