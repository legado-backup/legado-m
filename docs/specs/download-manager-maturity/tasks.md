# 下载器成熟化改造任务清单（download-manager-maturity）

## 1. 分析（现状盘点，已完成）
- [x] 1.1 全量下载入口盘点（确认 7 处：5 个消费场景 + 2 个管理页）
- [x] 1.2 读取 ChunkDownloader / HlsDownloader / DownloadService / DownloadState / DownloadManageActivity 现状
- [x] 1.3 日志证据复盘（native SIGABRT → 任务丢失链）

## 2. 持久化与恢复
- [ ] 2.1 新增 `DownloadTaskEntity`（Room 实体，字段默认值 + 断点/分片清单字段）
- [ ] 2.2 新增 DAO 与 `AppDatabase` v89→v90 迁移，导出 v90 schema
- [ ] 2.3 `DownloadState` 改 Room 主存 + StateFlow 缓存，新增 `resumeFromDb()`
- [ ] 2.4 `DownloadService` onCreate/onStart 调 `resumeFromDb()` 恢复未完成任务

## 3. 断点续传
- [ ] 3.1 `ChunkDownloader`：直链 `.partN` 续传点推进（按现有字节 Range 续传）
- [ ] 3.2 `HlsDownloader`：持久化已下分片清单，续传跳过已下分片

## 4. 任务能力（暂停/并发/重试）
- [ ] 4.1 真实暂停/恢复单任务（cancel 协程保留临时文件 + 恢复重新入队，补全 PAUSED 分支）
- [ ] 4.2 并发上限 `Semaphore(MAX_CONCURRENT)` + FIFO 排队（WAITING）
- [ ] 4.3 失败指数退避自动重试 + 手动重试
- [ ] 4.4 引入 `DownloadError` 枚举 + 错误码落库

## 5. 工程健壮性
- [ ] 5.1 通知 id 直映射修复（`notificationId = id.toInt()`，废弃 size/index 反查）
- [ ] 5.2 `DownloadManageActivity`：真实"已暂停"数据 + 恢复按钮 + 错误码展示
- [ ] 5.3 `Download.kt` 可选参数（autoStart/retry）透传

## 6. 验证与交付
- [ ] 6.1 编译门禁（assembleAppDebug BUILD SUCCESSFUL）+ 无残留调试日志
- [ ] 6.2 单元测试：`DownloadStateTest` 扩展（持久化/暂停/恢复/重试）
- [ ] 6.3 真机 L2 验证：进程杀后恢复、暂停/恢复、并发排队、失败重试、错误码展示
- [ ] 6.4 updateLog 追加用户向 changelog + tasks 勾选
- [ ] 6.5 文档同步：`docs/project-flow/modules/service-layer.md` / `android-services.md`
- [ ] 6.6 检查点 2 / 3 用户审核

## AOAdapt 日志
- （预留：实施过程记录偏离/调整）