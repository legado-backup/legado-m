# tasks.md — 视频播放器返回按钮修复 + 全屏按钮迁移 + 真全屏优化

## 1. 准备工作

- [ ] 1.1 确认源码分析结论（TitleBar attachToActivity 时序冲突 + ActionBar hide 不释放空间）
- [ ] 1.2 阅读相关源码：VideoPlayerActivity.kt switchToViewPagerMode/toggleFullScreen + VideoFragment.kt onFullScreenChanged/applyState + fragment_video.xml

## 2. B1 返回按钮修复

- [ ] 2.1 在 switchToViewPagerMode() 中 setSupportActionBar 之后添加 setNavigationOnClickListener 直接绑定点击事件
  - 加临时日志 Log.d("VideoBack", "NavigationOnClickListener triggered")
- [ ] 2.2 保留 onSupportNavigateUp 重写（兼容系统返回键的 navigateUp 路径，不删除）
- [ ] 2.3 编译验证

## 3. U1 全屏按钮迁移

- [ ] 3.1 fragment_video.xml: 将 btn_fullscreen 从独立位置（L125-141）移到 right_buttons 容器内（作为第一个按钮，在 btn_rewind 之前）
- [ ] 3.2 VideoFragment.kt: 简化 updateFullscreenButtonVisibility()，移除"横屏视频一直显示全屏按钮"的特殊逻辑，改为仅根据视频宽高比决定是否显示
- [ ] 3.3 VideoFragment.kt: applyState(FULLSCREEN) 中移除 btnFullscreen?.visible() 的特殊处理（随 rightButtons 整体显隐）
- [ ] 3.4 VideoFragment.kt: onFullScreenChanged 中移除 btnFullscreen?.visible() 的特殊处理
- [ ] 3.5 编译验证

## 4. F1 真全屏

- [ ] 4.1 VideoPlayerActivity.kt toggleFullScreen(): 将 supportActionBar?.hide() 改为 binding.titleBarNew.gone()
- [ ] 4.2 VideoPlayerActivity.kt toggleFullScreen(): 退出全屏时将 supportActionBar?.show() 改为 binding.titleBarNew.visible() + supportActionBar?.show()
- [ ] 4.3 加临时日志 Log.d("VideoFS", "titleBarNew visibility=${binding.titleBarNew.visibility}")
- [ ] 4.4 编译验证

## 5. 日志验证 + L2 真机验证

- [ ] 5.1 安装 APK 到 MEmu/真机，测试返回按钮点击 → logcat 确认 "VideoBack" 日志触发
- [ ] 5.2 测试全屏按钮在右侧功能区，随整体显隐
- [ ] 5.3 测试全屏时 playerView 铺满整个屏幕（无 TitleBar 空白）
- [ ] 5.4 测试退出全屏恢复正常
- [ ] 5.5 验证通过后移除临时日志（VideoBack / VideoFS）
- [ ] 5.6 重新编译确认无临时日志

## 6. 文档同步

- [ ] 6.1 更新 app/src/main/assets/updateLog.md（编译前更新）
- [ ] 6.2 更新 docs/INDEX.md（spec 状态）
- [ ] 6.3 更新 docs/specs/video-back-fullscreen-fix/README.md 状态为 ✅ 已完成
- [ ] 6.4 更新 tasks.md 全部标记 ✅

## AOAdapt 日志

（实施过程中遇到问题时记录）
