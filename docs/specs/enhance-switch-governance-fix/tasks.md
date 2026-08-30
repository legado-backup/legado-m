# tasks.md — 画质增强总开关治理与解码兜底修复

> OpenSpec 变更：`enhance-switch-governance-fix`
> 来源：commit `6bc9fd98f` 交付后的 4 项代码审查问题（1 major：总开关关不掉 B 批 media3 锐化/降噪链；3 minor：滑条预设联动 / 无长度响应 OOM 兜底 / Paint 重复重建）
> 设计权威源：[design.md](./design.md)（AD-01 ~ AD-04）
> 真机验证规范：`ai_tests/docs/fixed_test_workflow.md`；必须用 `ai_tests\venv\Scripts\python.exe`；MEmu 模拟器 + 测试包 `io.legado.miss.app.debug`

## 1. 准备

- [ ] 1.1 Read 四处改动点现状核对设计假设：`ImageEnhanceEffects.buildEffects()`（`help/exoplayer/ImageEnhanceEffects.kt`）、总开关 `onCheckedChange` 与 4 处滑条 `onCommit`（`ui/video/VideoSettingsPanelContent.kt` L316-320 / L327-361）、封面解密分支（`help/glide/OkHttpStreamFetcher.kt` L182-191）、`ImageEnhanceController.apply()`（`ui/video/ImageEnhanceController.kt` L99-111）；确认与 design.md 引用的行号/函数签名一致，若有偏移先更新 design.md 再动代码
  - AOAdapt: [执行后回填] 核对结论（一致/行号偏移清单）
- [ ] 1.2 确认 `SKIP_DECODE_SIZE_BYTES` 与 `MemoryPressure.isSmallHeap` 现值：`OkHttpStreamFetcher.kt` L62（预期 10MB）与 `help/MemoryPressure.kt`（isSmallHeap 判定阈值与来源），确认 AD-03 有界缓冲上限直接复用该常量，不新造阈值
  - AOAdapt: [执行后回填] 常量现值 + MemoryPressure 判定逻辑摘要

## 2. 核心实现

- [ ] 2.1 **AD-01a** `ImageEnhanceEffects.buildEffects()` 开头加总开关守卫：`if (!VideoPlay.enhanceEnabled) return emptyList()`，同步更新函数 KDoc（注明守卫语义与 K4 空列表清空关系），约 +3 行
  - AOAdapt: [执行后回填] diff 摘要 + 是否更新 KDoc
- [ ] 2.2 **AD-01b** `VideoSettingsPanelContent.kt` 总开关 `onCheckedChange`（L316-320）在 `applyToRegistered()` 后补调 `ImageEnhanceController.applyEffectsToPlayer()`，+1 行；注意主线程语义（applyEffectsToPlayer 必须主线程调用，面板本身在 Compose 主线程）
  - AOAdapt: [执行后回填] diff 摘要
- [ ] 2.3 **AD-02** `VideoSettingsPanelContent.kt` 4 个 `EnhanceSliderRow` 的 `onCommit`（L327-361：亮度/对比度/饱和度/色温）内各加 `if (enhancePreset != 3) { enhancePreset = 3; VideoPlay.enhancePreset = 3 }`，+2 行 ×4；本地 Compose 状态与 `VideoPlay` 全局状态同步写
  - AOAdapt: [执行后回填] diff 摘要（4 处是否全部覆盖）
- [ ] 2.4 **AD-03** `OkHttpStreamFetcher.kt` 无 `contentLength`（-1）时新增有界缓冲分支：`MemoryPressure.isSmallHeap && contentLength < 0` → `ByteArrayOutputStream` 增量读至 `SKIP_DECODE_SIZE_BYTES + 1` 上限；超限 → `SequenceInputStream(ByteArrayInputStream(缓冲) + responseBody.byteStream())` 透传；未超限 → `toByteArray()` 走 `ImageUtils.decode(url, bytes, ...)`；保留既有「有长度且 >10MB 直接透传」路径不动，约 +20 行
  - AOAdapt: [执行后回填] diff 摘要 + 三分支（有长度超限/无长度超限/无长度未超限）逻辑核对结论
- [ ] 2.5 **AD-04** `ImageEnhanceController.kt` `object` 内增加 `private var cachedPaint: Paint?` 与 `private var lastParams: Long`（四参数 b/c/s/t 打包指纹）；`apply()` 计算指纹 → 未变直接 `return` → 变化时复用 `cachedPaint` 更新 `colorFilter` 再 `setLayerType`；`reset()` 路径保持 `setLayerType(NONE, null)` 不清缓存（惰性复用），约 +15 行
  - AOAdapt: [执行后回填] diff 摘要 + 指纹打包方式说明

## 3. 编译门禁

- [ ] 3.1 `updateLog.md` 编译前更新（强制规则 §1）：基于 `git diff` 逐文件对照（本 spec 5 处源码变更）追加用户语言条目到 `app/src/main/assets/updateLog.md` 的 `## cronet版本:` 之后、已有条目之前；禁止合并旧条目
  - AOAdapt: [执行后回填] updateLog 追加条目内容
- [ ] 3.2 `./gradlew compileAppDebugKotlin` BUILD SUCCESSFUL（命令带 App 前缀 flavor；若走 IDE/直连 gradlew 构建后须执行 `stop-daemons.bat` 清理 daemon，强制规则 §6）
  - AOAdapt: [执行后回填] 构建结果 + 是否执行 daemon 清场
- [ ] 3.3 Grep `android.util.Log.d|android.util.Log.e` 确认本次改动文件无残留调试日志（logging-during-refactoring.md；OkHttpStreamFetcher 既有 `Log.e` TAG 日志为审查期合法保留项，不在清理范围，但新增代码禁止引入）
  - AOAdapt: [执行后回填] Grep 结果统计（本次新增代码 0 残留）

## 4. L2 真机/模拟器验证（强制）

> 环境：MEmu 模拟器 + `ai_tests\venv\Scripts\python.exe`；脚本入口新增 `ai_tests/scripts/l2_verify_image_enhance_governance.py`，风格参照 `ai_tests/scripts/` 固化脚本（`quick_build_install.py` / `import_rss_source.py` / `l2_verify_video_player.py` / `swipe_test_log.py`）；禁止在 `temp/` 创建临时测试脚本。真机问题记入 issues-found.md。

- [ ] 4.1 **T1 效果链正向生效**：开总开关 + 锐化「强」+ 降噪「中」播放视频，断言效果生效（截图对比锐化前后 + logcat 断言 buildEffects 非空链注入日志；日志只取技术行：tag/异常码/链长度，不引用业务数据）
  - AOAdapt: [执行后回填] T1 结果（PASS/FAIL + 截图路径 + 日志断言计数）
- [ ] 4.2 **T2 播放中关总开关立即恢复原画**：播放中切面板关总开关，断言 `setVideoEffects` 空链日志 + 画面无锐化（AD-01a 守卫返回 emptyList + AD-01b 立即触发当前实例）
  - AOAdapt: [执行后回填] T2 结果（空链日志行计数 + 截图）
- [ ] 4.3 **T3 关开关后重新播放仍原画**：关闭总开关 → 退出播放 → 重新进播放，走 `onPrepared` 钩子重建路径，断言仍无锐化/滤镜（守卫对重建路径同样生效）
  - AOAdapt: [执行后回填] T3 结果
- [ ] 4.4 **T4 滑条联动自定义预设**：预设选「柔和」后拖动任一滑条 → 断言面板预设标签变「自定义」（AD-02）；重进设置面板 → 断言预设选中项为「自定义」且四参数保留
  - AOAdapt: [执行后回填] T4 结果（UI dump 断言：标签文本命中「自定义」，脚本输出编号化）
- [ ] 4.5 **T5 拖动流畅度**：连续快速拖动四滑条（低端实例/低配模拟器），断言无掉帧闪烁（AD-04 指纹短路 + cachedPaint 复用后滑条跟手；以画面无闪黑/无卡死为准）
  - AOAdapt: [执行后回填] T5 结果 + 拖动帧稳定性结论
- [ ] 4.6 **T6 小内存无长度大图不 OOM**：本地起 chunked HTTP 服务器（无 `Content-Length` 响应头）提供 >10MB 加密概率低的大图，模拟器开启小内存条件（或用堆限制等效实例），加载封面断言：走有界缓冲透传分支、无 OOM、图片正常展示（AD-03）
  - AOAdapt: [执行后回填] T6 结果（透传分支日志命中 + 无 OOM 崩溃）
- [ ] 4.7 **T7 回归：既有画质增强 A 期无回归**：四参数调节（亮度/对比度/饱和度/色温）+ 预设选择 + 滤镜视图通道 + onPrepared/全屏切换/切集数重建路径全部按 A 期行为复验，确认本批修复零破坏
  - AOAdapt: [执行后回填] T7 结果（回归用例通过数/总数）

## 5. 收尾

- [ ] 5.1 调试日志清理：Grep `android.util.Log.d|android.util.Log.e` 复扫本次全部改动文件，确认新增代码 0 残留（OkHttpStreamFetcher 既有审查期日志除外）
  - AOAdapt: [执行后回填] 复扫结果 0 残留
- [ ] 5.2 文档同步：`docs/specs/INDEX.md` 登记本 spec；ai_memory_main 沉淀本批经验（AD-01 守卫模式 / AD-03 有界缓冲模式可复用）；issues-found.md 归档 T1~T7 真机结论
  - AOAdapt: [执行后回填] 已同步文档清单
- [ ] 5.3 提交推送：master 分支 Conventional Commits 提交（源码 + updateLog + 本 spec 目录 + ai_tests 脚本），推送前 `git diff` 复核变更范围仅含预期文件
  - AOAdapt: [执行后回填] commit hash + 变更文件数
