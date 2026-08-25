# tasks.md — 视频下载与下载管理整合

## 1. 准备工作
- [ ] 1.1 阅读 FileDownloader/HlsDownloader 对应网络栈（OkHttp/Cronet、buildAntiLeechHeaders）与 ExoPlayerHelper 嗅探
- [ ] 1.2 阅读 VideoFragment right_buttons / DownloadService / DownloadState 现状，确认接入点
- [ ] 1.3 确认 m3u8 分片解析与 MediaExtractor/MediaMuxer 可用性（平台 MediaExtractor 支持 TS）

## 2. 下载引擎核心
- [ ] 2.1 实现 FileDownloader：Range 探测 + 多片并发 + Part 合并 + 单线程降级
- [ ] 2.2 实现 FileDownloader：暂停(断点续传)/取消(清理 Part)/失败重试
- [ ] 2.3 实现 HlsDownloader：解析 master/playlists/segments，选主码流
- [ ] 2.4 实现 HlsDownloader：并发下载 ts 分片 + 按序合并单个 .ts
- [ ] 2.5 实现 TsToMp4Remuxer：MediaExtractor 解封装 + MediaMuxer 重封装（PTS 偏移矫正）
- [ ] 2.6 m3u8 失败回退保留 .ts；识别并拒绝 AES-128/DRM 流

## 3. 服务与状态
- [ ] 3.1 改造 DownloadService：由系统 DownloadManager 切换自研引擎调度
- [ ] 3.2 扩展 DownloadState：新增 taskType / 本地路径，适配新引擎操作
- [ ] 3.3 更新 Download.kt：start 增加 headers / taskType 参数统一入口

## 4. 前端集成
- [ ] 4.1 fragment_video.xml：right_buttons 内新增下载按钮
- [ ] 4.2 VideoFragment：btnDownload 挂载 + 点击读取 videoUrl/headers/videoTitle 发起下载
- [ ] 4.3 DownloadManageActivity：暂停/重试/删除/打开/清理适配新引擎
- [ ] 4.4 strings.xml：新增下载相关文案与图标

## 5. 验证
- [ ] 5.1 编译门禁通过（./gradlew assembleAppDebug）
- [ ] 5.2 单元/静态：分片合并、ts 合并、remux 关键路径正确性抽查
- [ ] 5.3 真机 L2：直链 mp4 一键下载 + 进度展示 + 打开本地文件
- [ ] 5.4 真机 L2：m3u8 下载转 mp4，验证分类/完成、本地产物为 .mp4、无残留分片
- [ ] 5.5 回归：播放器手势（切视频/seek/倍速/双击暂停）不受下载按钮影响
- [ ] 5.6 updateLog 更新 + 文档同步（INDEX / project-flow）

## AOAdapt 日志

> 实施过程中遇到的问题与调整，按 `Action / Observation / Adapt` 记录。

- [ ] 待实施过程中补充