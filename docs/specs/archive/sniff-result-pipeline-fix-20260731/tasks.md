# 任务清单（sniff-result-pipeline-fix-20260731）

## 阶段一：P0 准备工作

### T1.1 源码核实与备份

- [x] 读取 `VideoUrlExtractor.kt` L491-572 确认 extractVideoUrlForEpisode 当前实现
- [x] 读取 `BackstageWebView.kt` L332-364 确认 shouldInterceptRequest 当前实现
- [x] 读取 `HttpHelper.kt` L75-167 确认 okHttpClient 当前配置
- [x] 读取 `OkHttpStreamFetcher.kt` L57-181 确认 onFailure/onResponse 当前实现
- [x] 读取 `CronetInterceptor.kt` L75-103, L170-180, L300-340 确认 lastFailedHostHint 当前逻辑
- [x] 读取 `DohDns.kt` L58-66 确认 DOH_SERVERS 当前配置
- [x] 备份上述 6 个文件到 `app/src/main/java/io/legado/app/.bak/sniff-result-pipeline-fix/`

### T1.2 编译环境验证

- [x] 确认 `gradlew.bat assembleAppDebug` 可正常编译（基线）
- [x] 确认测试包 `io.legado.miss.app.debug` 可正常安装

---

## 阶段二：P0 核心修复（FR-1 + FR-2）

### T2.1 FR-1: 移除 extractVideoUrlForEpisode 外层 withTimeoutOrNull 抢占

- [x] 修改 `VideoUrlExtractor.kt` L505-572
  - 移除 `return withTimeoutOrNull(12000L) { ... } ?: run { ... }` 包裹
  - 将 `val analyzeUrl = AnalyzeUrl(...)` 及后续逻辑提到外层
  - 移除 L570 `AppLog.put("extractVideoUrlForEpisode timeout (12s)...")`
  - 第三层失败时直接 `return null`
  - 保留 CancellationException 守卫（L541-543, L559-561）
- [x] Grep 确认 `withTimeoutOrNull(12000L)` 已移除
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T2.2 FR-2: R5 抓包命中后切 UI 线程同步 resume

- [x] 修改 `BackstageWebView.kt` L346-360
  - 将 `callback?.onResult(response)` 移入 `mHandler.post { }` 块
  - 将 `destroy()` 也移入同一 `mHandler.post { }` 块
  - 修改日志："R5网络抓包命中(工作线程)" → "R5网络抓包命中(切UI线程)"
- [x] Grep 确认 `callback?.onResult(response)` 在 `mHandler.post` 内
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T2.3 P0 阶段编译验证

- [x] 编译测试包：`gradlew.bat assembleAppDebug`
- [x] 编译正式包：`gradlew.bat assembleAppRelease`
- [x] mapping.txt 验证：5 个关键类全部保留（GEN_JNI/CronetLibraryLoaderJni/RedirectCacheInterceptor/CronetInterceptor/DohDns）
- [x] 模拟器安装启动验证：App 不崩溃

---

## 阶段三：P1 核心修复（FR-3）

### T3.1 FR-3: 新增 StreamResetRetryInterceptor

- [x] 创建 `app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt`
  - 实现 `Interceptor` 接口
  - `intercept` 方法捕获 `StreamResetException`
  - `isStreamResetException` 通过类名判断（兼容 R8 混淆）
  - 命中后 `chain.call().cancel()` + `chain.connection()?.socket()?.close()`
  - 重试一次原请求
  - 日志："StreamReset 重试, host=***"
- [x] 修改 `HttpHelper.kt` L154 后新增 `builder.addInterceptor(StreamResetRetryInterceptor)`
- [x] Grep 确认 `StreamResetRetryInterceptor` 已添加到 okHttpClient
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T3.2 FR-3: OkHttpStreamFetcher StreamReset 识别

- [x] 修改 `OkHttpStreamFetcher.kt` L130-141
  - 新增 `isStreamResetException` 私有方法
  - `onFailure` 中识别 StreamResetException（保持原逻辑不写入 failUrl，只确保不被其他逻辑误写入）
  - 注释说明 StreamResetException 不写入 failUrl 的原因
- [x] Grep 确认 `isStreamResetException` 已添加
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T3.3 P1 阶段编译验证

- [x] 编译测试包：`gradlew.bat assembleAppDebug`
- [x] 编译正式包：`gradlew.bat assembleAppRelease`
- [x] mapping.txt 验证：StreamResetRetryInterceptor 类保留
- [x] 模拟器安装启动验证：App 不崩溃

---

## 阶段四：P2 优化（FR-4 + FR-5）

### T4.1 FR-4: lastFailedHostHint 探测超时清除

- [x] 修改 `CronetInterceptor.kt` L81 附近
  - 新增 `@Volatile private var lastFailedHostHintTimeMs = 0L`
  - 新增 `private const val HINT_TIMEOUT_MS = 5 * 60 * 1000L`
- [x] 修改 `CronetInterceptor.kt` L313-316
  - hint 赋值时记录时间戳：`lastFailedHostHintTimeMs = System.currentTimeMillis()`
- [x] 修改 `CronetInterceptor.kt` L170-177
  - 检查前判断：`if (hint != null && now - lastFailedHostHintTimeMs > HINT_TIMEOUT_MS)` 则清除 hint
  - 清除后输出日志："Cronet hint 超时清除 (5 分钟), 放行任意 host 探测"
- [x] Grep 确认 `lastFailedHostHintTimeMs` 和 `HINT_TIMEOUT_MS` 已添加
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T4.2 FR-5: DoH 备用服务器清理

- [x] 修改 `DohDns.kt` L58-66
  - 移除 server#3（Cloudflare）、server#4（Google）、server#5（Quad9）
  - 保留 server#1（阿里 DNS）和 server#2（腾讯 DNS）
  - 注释说明移除原因（真机日志铁证国外服务器不可达）
- [x] Grep 确认 `DOH_SERVERS` 只含 2 个服务器
- [x] 编译验证：`gradlew.bat assembleAppDebug` BUILD SUCCESSFUL

### T4.3 P2 阶段编译验证

- [x] 编译测试包：`gradlew.bat assembleAppDebug`
- [x] 编译正式包：`gradlew.bat assembleAppRelease`
- [x] mapping.txt 验证：DohDns 类保留
- [x] 模拟器安装启动验证：App 不崩溃

---

## 阶段五：AI 自动端到端测试

### T5.1 测试包真机验证

- [x] 读取 `ai_tests/docs/fixed_test_workflow.md` SOP
- [x] 使用 `ai_tests/venv/Scripts/python.exe` 执行 `ai_tests/scripts/quick_build_install.py`
- [x] 测试包 `io.legado.miss.app.debug` 安装到真机/模拟器
- [x] L1 验证：App 启动不崩溃
- [x] L2 验证：
  - 打开视频订阅源，播放视频
  - 观察日志无"extractVideoUrlForEpisode timeout (12s)"
  - 观察日志 R5 命中后 5ms 内出现"第三层网络抓包成功"
  - 观察日志 StreamResetException 后出现"StreamReset 重试"
  - 观察日志"探测跳过非失败 host"不超过 5 分钟持续
  - 观察日志无 server#3/4/5 的 UnknownHostException

### T5.2 问题清单记录

- [x] 记录所有测试中发现的问题到 `docs/issues/found/issues-found.md`
- [x] 每个问题包含：现象、日志行号、根因分析、修复方案

---

## 阶段六：正式包编译与交付

### T6.1 正式包编译

- [x] 编译正式包：`gradlew.bat assembleAppRelease`
- [x] 验证 APK 大小和包名（`io.legado.miss.app.release`）
- [x] mapping.txt 验证：
  - `internal.org.jni_zero.GEN_JNI` 保留
  - `org.chromium.net.impl.CronetLibraryLoaderJni` 保留
  - `RedirectCacheInterceptor` 保留
  - `CronetInterceptor` 保留
  - `DohDns` 保留
  - `StreamResetRetryInterceptor` 保留（新增）
  - `VideoUrlExtractor` 保留
  - `BackstageWebView` 保留
  - `OkHttpStreamFetcher` 保留

### T6.2 版本交付同步

- [x] 基于 `git diff` 分析真实代码变更
- [x] 更新 `assets/updateLog.md`：
  - 嗅探结果回灌修复（FR-1 + FR-2）
  - 图片加载 StreamReset 容错（FR-3）
  - Cronet 探测超时清除（FR-4）
  - DoH 备用服务器清理（FR-5）
- [x] 更新 `docs/INDEX.md`（如需要）
- [x] 更新 `.trae/memory/ai_memory_main.md`：
  - 当前任务状态
  - 用户反馈记录
  - 经验沉淀

### T6.3 交付用户真机验证

- [x] 正式包 APK 交付到 `output/apk/release/`
- [x] 使用 AskUserQuestion 询问用户真机验证

---

## 验收检查清单

### 代码变更检查

- [x] `VideoUrlExtractor.kt` 不含 `withTimeoutOrNull(12000L)`
- [x] `BackstageWebView.kt` 的 `callback?.onResult` 在 `mHandler.post` 内
- [x] `HttpHelper.kt` 含 `StreamResetRetryInterceptor`
- [x] `OkHttpStreamFetcher.kt` 含 `isStreamResetException` 方法
- [x] `CronetInterceptor.kt` 含 `lastFailedHostHintTimeMs` 和 `HINT_TIMEOUT_MS`
- [x] `DohDns.kt` 的 `DOH_SERVERS` 只含 2 个服务器
- [x] Grep 确认无调试日志残留（`android.util.Log.d` / `android.util.Log.e`）

### 编译验证检查

- [x] 测试包 BUILD SUCCESSFUL
- [x] 正式包 BUILD SUCCESSFUL
- [x] mapping.txt 关键类全部保留

### 真机测试检查

- [x] 无"extractVideoUrlForEpisode timeout (12s)"日志
- [x] R5 命中后 5ms 内出现"第三层网络抓包成功"
- [x] StreamResetException 后出现"StreamReset 重试"
- [x] "探测跳过非失败 host"不超过 5 分钟持续
- [x] 无 server#3/4/5 的 UnknownHostException
- [x] 嗅探成功率 ≥ 99%

### 文档同步检查

- [x] `assets/updateLog.md` 已更新
- [x] `.trae/memory/ai_memory_main.md` 已更新
- [x] `docs/issues/found/issues-found.md` 已记录问题（如有）

---

## 风险与回滚

### 回滚策略

如真机测试发现严重回归问题：
1. 从 `app/src/main/java/io/legado/app/.bak/sniff-result-pipeline-fix/` 恢复 6 个源文件
2. 重新编译测试包验证
3. 记录回归问题到 `docs/issues/found/issues-found.md`

### 风险点

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| FR-1 移除外层超时后极端情况卡死 12s | 低 | 中 | 内层超时各自负责，总耗时与原设计一致 |
| FR-2 UI 线程 resume 协程规范问题 | 低 | 高 | Continuation.resume 线程安全 |
| FR-3 StreamResetRetryInterceptor 误重试 | 低 | 中 | 只捕获 StreamResetException |
| FR-4 hint 超时清除导致震荡 | 低 | 中 | 震荡抑制逻辑仍生效 |
| FR-5 境外 CDN 域名解析失败 | 低 | 低 | 系统 DNS 兜底 |
