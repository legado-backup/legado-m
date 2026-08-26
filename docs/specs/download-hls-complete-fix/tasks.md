# HLS 下载完成链路修复 — 任务清单（tasks.md）

## 1. 重封装 csd 加固（根因 1）

- [x] 1.1 `HlsDownloader.TsToMp4Remuxer.remux` 视频轨 csd-0 严格校验：非空 && `>= 16` 字节 && 首字节 `0x01`（AVCC configurationVersion），并校验 KEY_WIDTH/KEY_HEIGHT > 0
- [x] 1.2 csd 校验不满足 → `return false` → 走 `HlsResult.TsFallback`（ts 保留，不触发 MediaMuxer）
- [x] 1.3 csd-0 为 null（MediaExtractor 读不到）→ 同样 TsFallback 兜底
- [x] 1.4 校验通过 → 保持现有 MediaMuxer remux 逻辑不变（PTS 单调矫正等）

## 2. 完成状态落库保障（根因 2）

- [x] 2.1 **升级实现（logs(3) 新铁证）**：`HlsDownloader.download` 新增 `onMerged(tsFile)` 回调，ts 合并完成即回调；`executeHls` 在回调中立即将 ts copy 到目标目录并落库 COMPLETED（localPath=ts），再尝试 mp4 转码；转码成功外层 handleSuccess 覆盖 localPath=mp4。即使转码 native 崩溃杀进程，任务已在完成列表且 ts 完整可播
- [x] 2.2 确认失败分支（Failed/UnsupportedCrypto）不误吞：仅当合并前失败且无 ts 可保留时才判失败
- [ ] 2.3 （小）`executeDirect` / `executeHls` 成功路径产物长度校验：极小产物（如 < 1KB）补日志并在有 ts 时降级 TsFallback

## 3. 软件内播放（根因 3）

- [x] 3.1 `DownloadManageActivity.openFile`：扩展名 ∈ {mp4, ts, mkv, webm, avi, mov, flv, wmv, 3gp, m4v, m2ts, rmvb, rm, f4v} → 启动 `VideoPlayerActivity`
- [x] 3.2 内置播放器传参：`videoUrl = Uri.fromFile(f).toString()`（file://）、`videoTitle = fileName`、`isNew = true`
- [x] 3.3 非视频文件保持 `openFileUri` 系统打开（行为不变）

## 4. 验证与交付

- [ ] 4.1 编译门禁：`compileAppDebugKotlin`（或 assembleAppDebug）零错误（进行中）
- [ ] 4.2 残留检查：Grep 临时日志/调试代码 0 残留
- [ ] 4.3 真机回归（测试包，Android 9 模拟器）：
  - HLS csd 缺失源 → 不崩溃、完成列表出现、软件内可播（ts）
  - 正常 HLS → mp4 完整、完成列表、软件内播放
  - 直链 mp4 → 完成列表软件内播放
  - 非视频直链 → 系统打开不变
- [x] 4.4 `updateLog.md` 新增用户可见条目（编译前同步，面向用户语言，禁止合并旧条目）
- [x] 4.5 `docs/INDEX.md` 登记本规格
- [ ] 4.6 项目记忆持久化（用户反馈 + 本规格状态 + 真机回归结论）

## AOAdapt 日志

**2026-08-25 21:30** 实施动作：
- 根因修正：logs(3) 显示 `csd0 too small` 为系统 framework 日志；真正崩溃为 `ubsan: mul-overflow`（ROM 编译期 UBSan 检查），发生在 MP4WtrVidTrkThr（MPEG4Writer 视频轨写线程），Java 层捕获不住。
- 方案升级：在"csd 严格校验"之上增加"onMerged 先落库完成"保障层，消除任何残留 native 崩溃导致任务丢失的可能。
- 完成文件：HlsDownloader.kt（onMerged 回调 + csd 严格校验 + MIN_VIDEO_CSD_BYTES）、DownloadService.kt（executeHls onMerged 先落库）、DownloadManageActivity.kt（openFile 视频走内置播放器）。