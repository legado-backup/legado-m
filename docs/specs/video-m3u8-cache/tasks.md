# tasks.md - 视频播放器 m3u8 边下边播缓存

> **状态**：✅ 已实施（待真机验证）
> **创建日期**：2026-07-08
> **对应 spec**：[spec.md](./spec.md) / [design.md](./design.md)

---

## 任务清单

### 1. 配置层（VideoPlay.kt）

- [ ] 1.1 在 `VideoPlay.kt` 的 `videoPrefs` 块内、`autoPlay` 属性之后，新增 `cachePlay` 属性，仿照 `autoPlay` 写法：`get() = videoPrefs.getBoolean("cachePlay", true)` + `set(value) { videoPrefs.edit { putBoolean("cachePlay", value) } }`，注释标注"所有 setUp 调用应使用本属性"
- [ ] 1.2 修改 L150 单链接分支：`player.setUp(url, false, ...)` → `player.setUp(url, cachePlay, ...)`
- [ ] 1.3 修改 L181-184 订阅源无 ruleContent 分支：`player.setUp(analyzeUrl.url, false, ...)` → `player.setUp(analyzeUrl.url, cachePlay, ...)`
- [ ] 1.4 修改 L215 订阅源有 ruleContent 分支：`player.setUp(playUrl, false, ...)` → `player.setUp(playUrl, cachePlay, ...)`
- [ ] 1.5 修改 L278 书籍章节分支：`player.setUp(playUrl, false, ...)` → `player.setUp(playUrl, cachePlay, ...)`
- [ ] 1.6 自检：确认 4 处 `setUp` 调用均已替换，且其余参数（url/cachePath/title）未变

### 2. UI 层（SettingsDialog + 布局 + 字符串）

- [ ] 2.1 在 `dialog_video_settings.xml` 的 `cb_full_bottom_progress` 所在 LinearLayout 之后、`tv_press_speed` 之前，新增 1 个 LinearLayout，含 TextView（`@string/cache_play`）+ CheckBox（`@+id/cb_cache_play`，`android:checked="true"`）
- [ ] 2.2 在 `strings.xml` 新增 `<string name="cache_play">边下边播</string>`；若存在 `values-en/strings.xml` 则新增 `<string name="cache_play">Cache while playing</string>`
- [ ] 2.3 在 `SettingsDialog.kt` 的 `initData()` 中新增 `binding.cbCachePlay.isChecked = VideoPlay.cachePlay`
- [ ] 2.4 在 `SettingsDialog.kt` 的 `initView()` 中新增 `binding.cbCachePlay.setOnCheckedChangeListener { _, isChecked -> VideoPlay.cachePlay = isChecked }`
- [ ] 2.5 自检：确认新开关与既有 3 个开关（autoPlay/startFull/fullBottomProgress）行为一致，互不干扰

### 3. 编译与验证

- [ ] 3.1 执行 `./gradlew assembleDebug` 编译通过，无报错
- [ ] 3.2 真机验证 T1：首次播放 m3u8，`externalCache/exoplayer` 出现分片文件
- [ ] 3.3 真机验证 T2：关闭开关后播放 m3u8，不再写入新分片
- [ ] 3.4 真机验证 T3：关闭后重新开启，下次 `startPlay` 恢复缓存写入
- [ ] 3.5 真机验证 T5：重复播放同一剧集，第二次流量显著降低
- [ ] 3.6 真机验证 T6：弱网下拖动进度条，已缓存区间秒切
- [ ] 3.7 回归验证：既有 3 个开关功能正常，订阅源/单链接/书籍章节 4 条播放路径均可正常播放

### 4. 文档与交付同步

- [ ] 4.1 在 `app/src/main/assets/updateLog.md` 顶部追加条目（位于 `## cronet版本:` 行之后、已有条目之前）：`**2026/07/08**` + `- 视频播放新增边下边播开关（默认开启，可在视频设置-边下边播关闭以节省存储）`
- [ ] 4.2 更新 `docs/INDEX.md` 中本 spec 状态标记（🔄 设计中 → ✅ 已实施）
- [ ] 4.3 更新本 `tasks.md` 勾选所有完成项
- [ ] 4.4 将 README.md 顶部状态由"🔄 设计中"改为"✅ 已实施"

---

## AOAdapt 日志

> 用于记录实施过程中遇到的问题、偏离设计的原因、与 AOAdapt（适配）相关的决策。

### 2026-07-08

- [初始] 根据 OpenSpec 工作流程生成四文档，状态标记 🔄 设计中，等待用户审查设计后再进入实施阶段。
- [实施完成] 配置层 1.1-1.6 全部完成（cachePlay 属性 + 4 处 setUp 替换）；UI 层 2.1-2.5 全部完成（布局+字符串+绑定）；编译 3.1 通过（BUILD SUCCESSFUL）；文档 4.1-4.4 全部完成。真机验证 3.2-3.7 待做。
- [Room] 无需 Migration，@ColumnInfo defaultValue 变化不影响编译，copyRoomSchemas 正常执行。

<!-- 实施阶段开始后在此追加日志，格式：
### YYYY-MM-DD
- [问题/决策] 描述
- [偏离设计] 原因 + 影响
-->
