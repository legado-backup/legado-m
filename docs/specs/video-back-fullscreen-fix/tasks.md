# tasks.md — 视频播放器返回按钮修复 + 全屏按钮迁移 + 真全屏优化

## 1. 准备工作

- [x] 1.1 确认源码分析结论（TitleBar attachToActivity 时序冲突 + ActionBar hide 不释放空间）
- [x] 1.2 阅读相关源码：VideoPlayerActivity.kt switchToViewPagerMode/toggleFullScreen + VideoFragment.kt onFullScreenChanged/applyState + fragment_video.xml

## 2. B1 返回按钮修复

- [x] 2.1 在 switchToViewPagerMode() 中 setSupportActionBar 之后添加 setNavigationOnClickListener 直接绑定点击事件
  - 加临时日志 Log.d("VideoBack", "NavigationOnClickListener triggered")
- [x] 2.2 保留 onSupportNavigateUp 重写（兼容系统返回键的 navigateUp 路径，不删除）
- [x] 2.3 编译验证 ✅ BUILD SUCCESSFUL

## 3. U1 全屏按钮迁移

- [x] 3.1 fragment_video.xml: 将 btn_fullscreen 从独立位置移到 right_buttons 容器内（作为第一个按钮，在 btn_rewind 之前）
- [x] 3.2 VideoFragment.kt: 保持 updateFullscreenButtonVisibility 不变（仍需根据视频宽高比控制 btn_fullscreen 自身 visibility；"横屏视频一直显示"行为已通过 btn_fullscreen 移入 rightButtons 容器自动消除——容器随 3 秒自动隐藏，btn_fullscreen 作为子控件随之隐藏）
- [x] 3.3 VideoFragment.kt: 保持 applyState(FULLSCREEN) 中 btnFullscreen?.visible() 不变（全屏态需强制显示 btn_fullscreen 以便用户退出全屏，此调用设置 btn_fullscreen 自身 visibility 而非容器 visibility）
- [x] 3.4 VideoFragment.kt: 保持 onFullScreenChanged 中 btnFullscreen?.visible() 不变（同 3.3 理由）
- [x] 3.5 编译验证 ✅ BUILD SUCCESSFUL
- [x] 3.6 VideoFragment.kt: 更新 getOverlayControls() 注释反映 btn_fullscreen 已移入 rightButtons

## 4. F1 真全屏

- [x] 4.1 VideoPlayerActivity.kt toggleFullScreen(): 将 supportActionBar?.hide() 改为 binding.titleBarNew.gone()
- [x] 4.2 VideoPlayerActivity.kt toggleFullScreen(): 退出全屏时将 supportActionBar?.show() 改为 binding.titleBarNew.visible() + supportActionBar?.show()
- [x] 4.3 加临时日志 Log.d("VideoFS", "enter/exit fullscreen: titleBarNew gone/visible")
- [x] 4.4 编译验证 ✅ BUILD SUCCESSFUL

## 5. 日志验证 + L2 真机验证

- [x] 5.1 L1 验证通过（App 启动无崩溃）✅ quick_build_install.py 全部通过
- [x] 5.2 真机日志分析确认横屏返回按钮 Bug 根因 ✅
  - 日志证据：logcat.txt L7852 进入全屏 → L7977 退出全屏（9秒），期间无 VideoBack 日志触发
  - 根因：F1 的 titleBarNew.gone() 隐藏了整个 TitleBar 包括返回按钮
- [x] 5.3 B1+ 修复：添加独立的悬浮返回按钮 btn_back_overlay ✅
  - fragment_video.xml: 添加 btn_back_overlay 到 controlsLayer
  - VideoFragment.kt: 声明变量 + 初始化 + 点击事件 + onFullScreenChanged 显隐 + getOverlayControls
  - VideoPlayerActivity.kt: isFullScreen 改为 internal 供 Fragment 访问
  - 编译验证 ✅ BUILD SUCCESSFUL (legado_app_3.26.071222.apk)
- [ ] 5.4 真机 L2 验证：全屏模式下点击悬浮返回按钮 → logcat 确认 "btnBackOverlay clicked" 日志触发
- [ ] 5.5 真机 L2 验证：全屏按钮在右侧功能区，随整体显隐
- [ ] 5.6 真机 L2 验证：全屏时 playerView 铺满整个屏幕（无 TitleBar 空白）
- [ ] 5.7 验证通过后移除临时日志（VideoBack / VideoFS）
- [ ] 5.8 重新编译确认无临时日志

## 6. 文档同步

- [x] 6.1 更新 app/src/main/assets/updateLog.md（编译前更新）✅
- [ ] 6.2 更新 docs/INDEX.md（spec 状态 → 🔄 开发中待真机验证）
- [ ] 6.3 更新 docs/specs/video-back-fullscreen-fix/README.md 状态
- [x] 6.4 更新 tasks.md ✅

## AOAdapt 日志

### 2026-07-12 实施

1. **U1 实施决策调整**：原计划"简化 updateFullscreenButtonVisibility + 移除 applyState/onFullScreenChanged 中的 btnFullscreen?.visible()"，实施时发现这些调用仍需保留：
   - `updateFullscreenButtonVisibility()` 控制 btn_fullscreen 自身 visibility（横屏 visible / 竖屏 gone），与容器显隐独立
   - `applyState(FULLSCREEN)` 中的 `btnFullscreen?.visible()` 确保全屏态下 btn_fullscreen 可见（竖屏视频时 btn_fullscreen 默认 gone，需强制 visible 以便退出全屏）
   - "横屏视频一直显示"行为的消除通过 XML 移入 rightButtons 容器自动实现（容器随 3 秒自动隐藏，btn_fullscreen 作为子控件随之隐藏）

2. **L2 验证降级**：模拟器 Room 数据库 schema hash 机制导致 import_rss_source.py 导入的订阅源在 App 启动时被清空（Room 检测到 schema hash 不匹配后重建数据库），无法在模拟器上完成 L2 真机验证。L1 验证通过（App 启动无崩溃），L2 需用户真机验证。

3. **临时日志保留**：VideoBack / VideoFS 临时日志暂未移除，等用户真机验证通过后再移除（任务 5.6/5.7）。
