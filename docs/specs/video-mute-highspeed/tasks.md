# tasks.md - 视频播放器优化：默认静音 + 高倍速支持

> **状态**：✅ 已实施（待真机验证）
> **创建日期**：2026-07-08
> **对应 spec**：[spec.md](./spec.md) / [design.md](./design.md)

---

## 任务清单

### 1. 配置层（VideoPlay.kt）

- [x] 1.1 在 `cachePlay` 属性之后新增 `muteOnStart` 属性（默认 true），仿照 cachePlay 写法
- [x] 1.2 ~L156 单链接分支：原计划在 startPlayLogic 后加 setNeedMute，实际改为 VideoPlayer.onPrepared 统一处理（见 AOAdapt 日志）~
- [x] 1.3 ~L190 订阅源无 ruleContent 分支：同上~
- [x] 1.4 ~L221 订阅源有 ruleContent 分支：同上~
- [x] 1.5 ~L284 书籍章节分支：同上~
- [x] 1.6 自检：静音设置统一在 VideoPlayer.onPrepared 中应用，覆盖所有播放分支

### 2. 高倍速（VideoPlayer.kt）

- [x] 2.1 修改 L404 倍速列表：`listOf(..., 3.0f, 5.0f, 10.0f, 15.0f).reversed()`
- [x] 2.2 确认 ChoiceSpeedDialog 能正常显示 11 个选项（编译通过，运行时由系统对话框自适应）

### 3. 静音按钮 UI（VideoPlayer.kt + 布局）

- [x] 3.1 在 `video_layout_controller_full.xml` 控制栏新增 ImageView（`@+id/iv_mute`，`ic_volume_off`）
- [x] 3.2 在 `video_layout_controller.xml` 控制栏同上
- [x] 3.3 在 VideoPlayer.kt 新增 `isMuted` 变量 + `ivMute` 引用
- [x] 3.4 在 `initView()` 绑定 `ivMute` 点击事件：`isMuted = !isMuted; getGSYVideoManager().player?.setNeedMute(isMuted); updateMuteIcon()`
- [x] 3.5 新增 `updateMuteIcon()` 方法：根据 isMuted 切换 ic_volume_off / ic_volume_up
- [x] 3.6 初始状态：`isMuted = VideoPlay.muteOnStart`，在 `initView` 中设置
- [x] 3.7 新增 ic_volume_off.xml 图标资源（项目原有 ic_volume_up.xml，无 ic_volume_off）

### 4. 设置开关（SettingsDialog + 布局 + 字符串）

- [x] 4.1 `dialog_video_settings.xml` 在 `cb_cache_play` 之后新增 `cb_mute_on_start` 开关
- [x] 4.2 `strings.xml` 新增 `<string name="mute_on_start">默认静音</string>`
- [x] 4.3 `SettingsDialog.kt` initData 新增 `cbMuteOnStart.isChecked = VideoPlay.muteOnStart`
- [x] 4.4 `SettingsDialog.kt` initView 新增 `cbMuteOnStart.setOnCheckedChangeListener { _, isChecked -> VideoPlay.muteOnStart = isChecked }`

### 5. 编译与验证

- [x] 5.1 执行 `compileAppDebugKotlin` 编译通过（BUILD SUCCESSFUL in 1m 45s）
- [ ] 5.2 真机验证：首次播放默认静音，显示静音图标
- [ ] 5.3 真机验证：点击静音按钮开启声音，图标切换
- [ ] 5.4 真机验证：倍速选择 15X 正常播放
- [ ] 5.5 真机验证：设置中关闭默认静音，下次播放有声音
- [ ] 5.6 回归验证：既有手势音量调节、长按倍速功能正常

### 6. 文档同步

- [x] 6.1 `updateLog.md` 追加条目
- [x] 6.2 `INDEX.md` 新增 spec 条目
- [x] 6.3 `tasks.md` 勾选完成项
- [x] 6.4 `README.md` 状态改为 ✅ 已实施

---

## AOAdapt 日志

> 用于记录实施过程中遇到的问题、偏离设计的原因。

### 2026-07-08

- [初始] 根据 OpenSpec 工作流程生成四文档，状态标记 🔄 设计中，等待用户审查设计后再进入实施阶段。
- [其他格式分析] ExoPlayerHelper.kt 源码核实确认：CacheDataSource 对所有格式生效，cachePlay=true 已覆盖 m3u8/mpd/mp4/mkv/flv，无需额外开发。
- [实施-编译失败] 首次实施按设计文档在 VideoPlay.kt 的 4 处 startPlayLogic 后调用 `player.setNeedMute(true)`，编译报错 `Unresolved reference 'setNeedMute'`。
- [根因分析] 经 javap 反编译 GSYVideoPlayer 11.x 库确认：`setNeedMute` 是 `IPlayerManager` 接口的方法，**不是** GSYVideoPlayer View 的方法。GSYVideoPlayer 基类仅通过 `getGSYVideoManager()` 返回 `GSYVideoViewBridge`，再通过 `getPlayer()` 返回 `IPlayerManager`。
- [方案调整] 将静音应用从 VideoPlay.kt 的 4 处 startPlayLogic 后，改为 VideoPlayer.kt 的 `onPrepared()` 回调中统一处理：`getGSYVideoManager().player?.setNeedMute(isMuted)`。
- [调整优势]
  1. 不管 autoPlay 与否都生效（原方案 autoPlay=false 时不执行静音设置）
  2. 每次播放/换集都应用当前静音状态（onPrepared 每次播放都回调）
  3. 代码更集中（1 处 vs 4 处），维护成本更低
  4. isMuted 变量跟踪当前状态，用户手动切换后状态保持正确
- [ivMute 点击事件] 同样改用 `getGSYVideoManager().player?.setNeedMute(isMuted)` 调用链。
- [编译验证] 修复后 BUILD SUCCESSFUL in 1m 45s，无编译错误。
