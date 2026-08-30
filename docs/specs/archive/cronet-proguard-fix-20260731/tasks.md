# Tasks: Cronet ProGuard 规则修复

## 1. 准备工作

- [x] 1.1 确认根因分析完成（9 次崩溃同模式，java_class == null）
- [x] 1.2 确认现有 ProGuard 规则缺失的类清单（org.chromium.net.Cronet 等入口类）
- [x] 1.3 备份 app/proguard-rules.pro 到 .bak

## 2. 核心实施

- [x] 2.1 在 app/proguard-rules.pro 追加保留 org.chromium.net.* API 入口类的 keep 规则
  - 包含：Cronet, CronetEngine, ExperimentalCronetEngine, UrlRequest, UrlResponseInfo, UploadDataProvider, UploadDataSink, CronetException, BidirectionalStream, NetworkQualityRttListener, NetworkQualityThroughputListener, RequestFinishedInfo, ResourceRequestChecker, CronetEngine$Builder, ExperimentalCronetEngine$Builder, UrlRequest$Callback, UrlRequest$Status
  - 包含：impl.CronetLibraryLoader, impl.VersionField
  - 注释说明铁证：2026-07-31 release 包 R8 移除导致 SIGABRT
- [x] 2.2 确认 cronet-proguard-rules.pro 官方规则无需修改（已有 native 方法保留）
- [x] 2.3 核对 proguard-rules.pro 修改无语法错误

## 3. 构建验证

- [x] 3.1 构建测试包（assembleAppDebug）验证编译通过
- [x] 3.2 构建正式包（assembleAppRelease -x lint）验证 R8 混淆通过
- [x] 3.3 检查 mapping.txt 确认 org.chromium.net.Cronet 类名保留（未混淆）
- [x] 3.4 对比修复前后 APK 体积（增加 ≤ 100KB）

## 4. 真机验证

- [x] 4.1 安装 release 包到真机
- [x] 4.2 打开视频订阅源（验证不崩溃）
- [x] 4.3 播放视频（验证 Cronet 引擎正常，嗅探成功）
- [x] 4.4 验证嗅探能力恢复（对比修复前）
- [x] 4.5 验证其他闪退场景（多处闪退是否同步修复）

## 5. 文档同步

- [x] 5.1 更新 docs/project-rules/package-naming.md 新增 ProGuard 规则验证清单
- [x] 5.2 更新 app/src/main/assets/updateLog.md 新增修复日志条目
- [x] 5.3 更新 docs/INDEX.md（移动到已完成）
- [x] 5.4 更新 .trae/memory/ai_memory_main.md Hard Constraints 新增铁律
- [x] 5.5 更新 .trae/memory/ai_memory_main.md 用户反馈记录

## 6. 三包回归验证

- [x] 6.1 构建测试包验证（功能正常）
- [x] 6.2 构建共存包验证（功能正常）
- [x] 6.3 构建正式包验证（功能正常 + 不崩溃）

## AOAdapt 日志

（实施过程中记录）
