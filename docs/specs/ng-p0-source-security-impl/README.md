# ng-p0-source-security-impl — 书源安全加固 P0 实施

> 状态：🔄 实施中 ｜ 创建：2026-09-01 ｜ 总线编排：master-track-orchestration tasks 2.1（W1）
> **权威设计账本 = docs/specs/ng-benchmark-analysis/migration-designs/P0-source-security-hardening.md（629 行，函数级+6 新类骨架+16 边界+21 单测），本 spec 只做执行清单与进度登记，不复制设计。**

## 实施范围（P0 分册五子项）

| 子项 | 内容 | 新类/改造 | 开关 |
|------|------|----------|------|
| S1 文件沙箱 | 书源上下文 getFile/readTxtFile/deleteFile/unzipFile/un7zFile/unrarFile/unArchiveFile/downloadFile 收敛 externalCache/source/{ns}/（ns=SHA-256("book\0"+sourceUrl) hex64） | StorageScope/FileAccessPolicy | bookSourceFileSandbox |
| S2 脚本缓存命名空间 | bindings["cache"]→按源 BookSourceCacheStore（DB+内存+文件三处，前缀清理），生效面含 BaseSource.evalJS（D17） | BookSourceCacheStore + CacheDao @Query 前缀能力（DB v109 不变） | bookSourceCacheScoped |
| S3 弹窗拦截 | 批量流程（搜索/换源）协程树拦截 getVerificationCode/startBrowserAwait→SourceInteractionBlockedException；toast/longToast 静默+日志 | SourceInteractionPolicy | blockSourceDialogs |
| S4 类导入灰度 | RhinoClassShutter 书源模式观察放行（AppClass 类）+CookieManager/CookieSyncManager D11 实拦 | RhinoClassShutter | 首期只记日志（D5） |
| S5 网络日志凭据脱敏 | 保护项：NetworkLog 已是超集，零修改仅回归验证（T21） | 无 | — |

已核实正交项：C0-F3 BookScriptObject（对象包装拦截）与 S4（类导入策略）机制分层；C0-F4 exploreKinds 缓存键与 S2（BookSourceExtensions vs BaseSourceExtensions 两文件）。

## 执行清单

- [ ] 1 S1 文件沙箱实施（StorageScope/FileAccessPolicy 新类+AnalyzeUrl/JsExtensions 等 5 处函数收敛+开关）
- [ ] 2 S3 弹窗拦截实施（SourceInteractionPolicy 新类+批量流程挂载 2 文件 3 行+开关）
- [ ] 3 S2 脚本缓存命名空间实施（BookSourceCacheStore+CacheDao @Query+evalJS 三入口接入+开关）
- [ ] 4 S4 类导入灰度实施（RhinoClassShutter 观察档+CookieManager 实拦）
- [ ] 5 S5 回归验证（T21 单测防回归）
- [ ] 6 22 单测（T1-T22，§9.1）落地
- [ ] 7 编译门禁+全量单测+daemon 清场+提交
- [ ] 8 L2 真机回归（§8.2 场景：沙箱路径/弹窗拦截观察/缓存前缀）→ 归 W1 收束

## AOAdapt 日志

（暂无）
