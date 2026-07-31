# 嗅探稳定性修复 - 任务清单（V3 修订版）

> 状态：🔄 设计中（V3 修订版）
> 创建日期：2026-07-31
> 修订日期：2026-07-31 16:18（V3：基于渗透式深度审计+主代理源码逐行核实）
> 关联文档：[README.md](./README.md) / [spec.md](./spec.md) / [design.md](./design.md)
> Spec ID：sniff-stability-fix-20260731
> 审计报告：[audit-report-v2-deep.md](./audit-report-v2-deep.md)（44个纰漏，V3已全部修复）

## 任务执行说明

- 每个任务下预留 AOAdapt 日志位置（Action / Observation / Adapt）
- 任务状态标记：`- [ ]` 未完成 / `- [x]` 已完成
- 阶段完成后需进行构建复验，禁止跨阶段并行
- 涉及代码变更的任务必须使用测试包真机验证（包名：io.legado.miss.app.debug）
- ProGuard 验证必须使用正式包真机测试（包名：io.legado.miss.app.release）
- 输出安全：AOAdapt 只记录技术结论（错误码/异常类型/调用栈），禁止记录业务数据

## 1. 阶段一：准备工作（P0）

- [ ] 1.1 读取当前 CronetInterceptor.kt + DohDns.kt + SSLHelper.kt + HttpHelper.kt + RedirectCacheInterceptor.kt 完整源码
  - 范围：CronetInterceptor.kt 全文 + DohDns.kt 全文 + SSLHelper.kt 全文 + HttpHelper.kt 关键配置 + RedirectCacheInterceptor.kt 全文
  - 目的：确认 P0-fix + P1-2 + SSLHelper + RedirectCacheInterceptor 已实施状态，避免重复修改
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.2 备份待修改文件到 .bak 目录
  - 范围：RedirectCacheInterceptor.kt + CronetInterceptor.kt + DohDns.kt
  - 命名：{文件名}.bak
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 2. 阶段二：FR-1 增强现有 RedirectCacheInterceptor（V3：多层重定向）

> **V3 变更**：不在 CronetInterceptor 内部新增302缓存（避免双重缓存），改为增强现有 RedirectCacheInterceptor

- [ ] 2.1 修改 RedirectCacheInterceptor.kt L67-84 响应处理逻辑
  - 修改点：从 `response.request.url` 获取跟随所有重定向后的最终URL（而非仅 Location 头）
  - 逻辑：响应 301/302/307/308 时，比较 `request.url` 与 `response.request.url`
  - 如果不同（发生重定向）：缓存 `request.url` → `response.request.url` 映射
  - 如果相同（未发生重定向）：不缓存
  - 保持现有：缓存键（URL+Referer+Cookie维度）+ LruCache 500条 + TTL 10分钟
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.2 验证 RedirectCacheInterceptor 命中缓存后走 Cronet
  - 验证点：命中缓存走 `chain.proceed(redirectedRequest)`，触发后续 CronetInterceptor（收到 finalUrl）
  - 验证点：CronetInterceptor 收到 finalUrl 后正常走 Cronet 引擎（保留 BoringSSL TLS 指纹）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 3. 阶段三：FR-2 证书错误降级 OkHttp 重试（V3：前缀匹配+分支前置return）

> **V3 变更**：源码 L208-212 已有前缀匹配跳过 printOnDebug，真正修复是分支前置 return

- [ ] 3.1 在 CronetInterceptor.kt companion object 新增证书错误单独去重状态
  - 新增：`@Volatile private var lastCertError: String? = null`
  - 新增：`@Volatile private var lastCertErrorTime = 0L`
  - 复用：`LOG_DEDUP_INTERVAL_MS`（60s）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 3.2 实现证书错误判定方法 isCertificateError()
  - 判定：前缀匹配 `ERR_CERT_` + `ERR_SSL_`（覆盖20+错误码）
  - 位置：companion object 内
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 3.3 实现证书错误日志去重方法 logCertError()
  - 逻辑：60s 内相同错误只记一次，WARN 级别
  - 日志内容：明确标识"证书错误降级 OkHttp（复用 SSLHelper 信任所有证书），不累计降级计数"
  - 使用 `lastCertError`/`lastCertErrorTime`（不与协议错误共享 `lastLoggedError`）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 3.4 在 intercept() 异常处理集成证书错误降级（V3 关键：分支前置 return）
  - 位置：Canceled 处理之后、isProtocolError/isHttp2ProtocolError 判定之前
  - 逻辑：`if (isCertificateError(errMsg)) { logCertError(errMsg); return chain.proceed(original) }`
  - V3 关键：必须在 isProtocolError 之前插入并 return（避免 ERR_SSL_PROTOCOL_ERROR 误匹配 isHttp2ProtocolError）
  - OkHttp 失败时：日志输出"OkHttp 降级失败，疑似 TLS 指纹问题" + 抛出 OkHttp 异常
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 4. 阶段四：FR-3 NAME_NOT_RESOLVED 处理实施（V3：host级清理+清熔断）

> **V3 变更**：host级清理（非全清）+ 清 `dohDisabledUntil`（解决熔断期间清理无效）

- [ ] 4.1 在 DohDns.kt 新增公开方法 clearNegativeCache(hostname: String)
  - 逻辑：`negativeCache.remove(cacheKey(hostname))` + `dohDisabledUntil = 0L`
  - V3 关键：同时清 `dohDisabledUntil`（源码 L189 熔断检查优先于 L179 负缓存检查）
  - 日志：DEBUG 级别，host 脱敏
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 4.2 实现 NAME_NOT_RESOLVED 判定方法 isNameNotResolvedError()
  - 判定：异常消息包含 `ERR_NAME_NOT_RESOLVED`
  - 位置：CronetInterceptor.kt companion object 内
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 4.3 在 intercept() 异常处理集成 NAME_NOT_RESOLVED 处理
  - 位置：证书错误处理之后、协议错误处理之前
  - 逻辑：`isNameNotResolvedError(errMsg)` → 日志"DoH failure, not Cronet issue" → `DohDns.clearNegativeCache(original.url.host)` → `return chain.proceed(original)`
  - 不累计 protocolErrorCount
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 5. 阶段五：FR-5 Cronet-OkHttp 桥接层评估（V3：仅方案A，评估后推荐不实施）

> **V3 变更**：删除方案B（Call.Factory 客户端级别不能按请求切换）

- [ ] 5.1 评估 cronet-okhttp 依赖可用性
  - 评估点：Maven Central 坐标 + 版本 + 下载可用性
  - 命令：WebSearch 查询 com.google.net.cronet:cronet-okhttp 最新版本
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 5.2 评估方案A影响清单（完全替换为 CronetTransport）
  - 评估点：OkHttp core 失效（缓存/重试/认证/网络拦截器/CookieJar/Response字段缺失）
  - 评估点：与现有 CronetInterceptor 的集成度差异
  - 评估点：代码改动量（HttpHelper.kt 的 okHttpClient 配置变更）
  - 评估点：兼容性（与现有 SSLHelper / CookieManager / 其他拦截器的兼容性）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 5.3 给出实施建议（V3 推荐：不实施）
  - 选项：实施（方案A）/ 不实施（保持 CronetInterceptor）
  - V3 推荐不实施原因：现有 CronetInterceptor 已获得完整 Cronet 能力，FR-1 V3 改进后缓存命中走 Cronet 保留 TLS 指纹
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 6. 阶段六：FR-6 降级策略优化（V3：移除cronetEngineHealthy+独立常量）

> **V3 变更**：移除 cronetEngineHealthy（避免死锁）+ 新增独立常量 RECOVERY_PROBE_CHECK_INTERVAL_MS

- [ ] 6.1 新增独立常量 RECOVERY_PROBE_CHECK_INTERVAL_MS
  - 新增：`private const val RECOVERY_PROBE_CHECK_INTERVAL_MS = 3 * 60 * 1000L`（3分钟）
  - 用途：仅用于恢复探测触发检查（L96）
  - 不修改：`RECOVERY_PROBE_INTERVAL_MS`（保持 5 分钟，用于 L239/L261/L277）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 6.2 修改 intercept() 恢复探测触发检查使用新常量
  - 修改：L96 `RECOVERY_PROBE_INTERVAL_MS` → `RECOVERY_PROBE_CHECK_INTERVAL_MS`
  - 保持：L239/L261/L277 继续使用 `RECOVERY_PROBE_INTERVAL_MS`
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 6.3 V3 移除 cronetEngineHealthy 标志位（V2 未实施，V3 确认不实施）
  - 确认：V2 设计的 cronetEngineHealthy 死锁（初始 false + 仅 Cronet 成功后置 true = 永远走 OkHttp）
  - V3 决策：不实施 cronetEngineHealthy，依赖现有 `engine == null` 检查
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 6.4 验证降级计数豁免清单扩展已生效
  - 验证：FR-2 证书错误不累计 + FR-3 NAME_NOT_RESOLVED 不累计 + 连接拒绝不累计（已实施）
  - 验证：其他协议错误保持 5 次降级阈值
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 7. 阶段七：FR-7 图片加载根因分析（V3 新增）

> **V3 变更**：新增图片加载下降根因分析（评估任务，非代码实施）

- [ ] 7.1 分析图片加载接入 Cronet 路径
  - 分析：`okHttpClientManga` 通过 `newBuilder()` 继承 CronetInterceptor
  - 分析：HttpHelper.kt L169-187 `okHttpClientManga` 的两个特殊拦截器
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 7.2 评估 ProgressResponseBody 开销
  - 分析：进度回调对图片加载性能的影响
  - 分析：`ProgressResponseBody` 包装 Response body 的开销
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 7.3 评估 ReadManga.rateLimiter 限流影响
  - 分析：`withLimitBlocking` 限流对图片加载延迟的影响
  - 分析：限流参数配置是否合理
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 7.4 评估 Glide 磁盘缓存配置
  - 分析：Glide 磁盘缓存配置是否合理
  - 分析：连接池配置（okHttpClient 50个空闲连接）对图片加载的影响
  - 分析：Cronet 降级对图片加载的影响
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 7.5 输出图片加载下降根因分析报告
  - 输出：根因分析报告（含优化建议）
  - 输出：优化建议（如适用）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 8. 阶段八：单元测试（V3 新增）

- [ ] 8.1 编写 RedirectCacheInterceptor 单元测试
  - 测试项：302 缓存命中/未命中
  - 测试项：多层重定向（A→B→C）缓存 A→C 映射
  - 测试项：缓存过期自动失效
  - 测试项：多线程并发访问
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 8.2 编写 CronetInterceptor 证书错误降级单元测试
  - 测试项：ERR_CERT_AUTHORITY_INVALID 触发 OkHttp 重试
  - 测试项：ERR_SSL_PROTOCOL_ERROR 触发 OkHttp 重试（不匹配 isHttp2ProtocolError）
  - 测试项：证书错误不累计 protocolErrorCount
  - 测试项：60s 内相同错误只记一次日志
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 8.3 编写 DohDns clearNegativeCache 单元测试
  - 测试项：host级清理（非全清）
  - 测试项：清理 dohDisabledUntil
  - 测试项：不影响其他域名
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 9. 阶段九：编译验证与真机测试

- [ ] 9.1 编译测试包验证（io.legado.miss.app.debug）
  - 命令：使用 ai_tests/scripts/quick_build_install.py
  - 验证点：编译通过、安装成功、L1 验证通过
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.2 真机测试 302 缓存功能（多层重定向）
  - 测试项：访问多层重定向站点，验证第二次请求命中缓存
  - 日志验证：grep "RedirectCache: hit" / "redirect cached"
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.3 真机测试证书错误降级（复用 SSLHelper）
  - 测试项：访问自签名证书站点，验证自动降级 OkHttp（复用 SSLHelper 信任所有证书）
  - 日志验证：grep "cert error, fallback OkHttp"
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.4 真机测试 NAME_NOT_RESOLVED 处理
  - 测试项：模拟 DoH 失败场景（断网后重连），验证不累计降级
  - 日志验证：grep "NAME_NOT_RESOLVED" / "DoH failure"
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.5 真机测试降级策略优化效果
  - 测试项：对比修复前后 Cronet 降级频率
  - 通过标准：修复后降级频率 ≤ 修复前
  - 日志验证：grep "RECOVERY_PROBE_CHECK_INTERVAL_MS" / "降级计数豁免"
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.6 真机测试嗅探成功率对比
  - 测试项：对比修复前后嗅探成功率（相同订阅源相同视频）
  - 通过标准：修复后嗅探成功率 ≥ 修复前
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.7 真机测试图片加载稳定性对比
  - 测试项：对比修复前后图片加载失败率
  - 通过标准：修复后失败率 ≤ 修复前
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.8 回归测试（V3 新增）
  - 测试项：现有9+降级机制不受影响
  - 测试项：现有 RedirectCacheInterceptor 功能正常（仅增强，不破坏）
  - 测试项：现有 SSLHelper 信任所有证书功能正常
  - 测试项：现有 P0-fix（DoH）+ P1-2（HTTP/2降级）功能正常
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.9 性能测试（V3 新增）
  - 测试项：302 缓存查询延迟 ≤ 1ms
  - 测试项：首帧延迟对比（修复后 ≤ 修复前）
  - 测试项：图片加载延迟对比（修复后 ≤ 修复前）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.10 多层重定向测试（V3 新增）
  - 测试项：A→B→C 多层重定向，缓存 A→C 映射
  - 测试项：第二次请求 A 直接用 C，跳过 B→C 往返
  - 测试项：缓存过期后重新发起 302 请求
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 9.11 编译正式包+mapping.txt 检查（io.legado.miss.app.release）
  - 验证点：ProGuard 规则完整性、release 包功能正常
  - 包名：io.legado.miss.app.release（正式包，release 构建，含 ProGuard 混淆+正式签名）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 10. 阶段十：文档同步

- [ ] 10.1 更新 updateLog.md
  - 要求：基于真实代码变更分析生成，禁止文字合并已有条目
  - 面向用户：通俗语言描述可感知变化（"优化视频嗅探成功率"+"提升图片加载稳定性"），不暴露内部技术术语
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 10.2 更新 docs/INDEX.md
  - 要求：同步新增 sniff-stability-fix-20260731 索引条目
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 10.3 更新项目记忆
  - 路径：.trae/memory/ai_memory_main.md
  - 要求：记录关键决策、文件路径、任务状态、设计文档路径
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 10.4 沉淀经验到子规范
  - 范围：302 缓存设计模式、证书错误降级策略、NAME_NOT_RESOLVED 与 DoH 协同、Cronet-OkHttp 桥接层评估、降级策略优化、图片加载根因分析
  - 目标：避免重复踩坑，为后续网络层优化提供参考
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 阶段交付检查清单

每阶段完成后需逐项核对：

| 检查项 | 说明 |
|--------|------|
| 调试日志已清理 | Grep 确认无 android.util.Log.d/e 残留 |
| updateLog 已更新 | 基于真实代码变更分析生成 |
| 文档同步已检查 | INDEX/project_memory 是否最新 |
| 构建复验通过 | 每阶段结束重新构建验证 |
| 真机验证通过 | 测试包真机验证关键场景 |
| ProGuard 验证（涉及混淆时） | release 包真机测试 + mapping.txt 检查 |
| AOAdapt 日志已记录 | 每个任务记录执行动作、观察结果、调整说明 |

## 任务依赖关系

- 阶段一（准备工作）为前置依赖，必须先完成
- 阶段二（FR-1 增强 RedirectCacheInterceptor）依赖阶段一完成
- 阶段三（FR-2 证书错误处理）依赖阶段一完成，与阶段二可并行
- 阶段四（FR-3 NAME_NOT_RESOLVED 处理）依赖阶段一完成，与阶段二/三可并行
- 阶段五（FR-5 桥接层评估）依赖阶段一完成，与阶段二/三/四可并行
- 阶段六（FR-6 降级策略优化）依赖阶段三/四完成（FR-2/3 是降级计数豁免清单的基础）
- 阶段七（FR-7 图片加载根因分析）依赖阶段一完成，与阶段二/三/四/五/六可并行
- 阶段八（单元测试）依赖阶段二/三/四/六完成
- 阶段九（编译验证与真机测试）依赖阶段二/三/四/六/八全部完成
- 阶段十（文档同步）为收尾，依赖阶段九完成

## 风险提示

| 风险项 | 等级 | 阶段 | 缓解措施 |
|--------|------|------|---------|
| FR-1 增强后多层重定向缓存失效 | 中 | 阶段二 | TTL 10 分钟 + 仅缓存 301/302/307/308 响应 + 单元测试覆盖 |
| FR-2 证书错误降级 OkHttp 仍失败 | 中 | 阶段三 | 说明是 TLS 指纹问题，日志输出建议启用 FR-5 |
| FR-3 host级清理影响其他域名 | 低 | 阶段四 | host级清理（非全清），不影响其他域名 |
| FR-6 恢复探测频率缩短导致震荡 | 低 | 阶段六 | 仅缩短恢复探测触发检查，保持其他降级时长不变 |
| FR-7 图片加载根因分析不充分 | 中 | 阶段七 | 深度分析 ProgressResponseBody/rateLimiter/Glide 配置 |
| 真机测试环境差异 | 中 | 阶段九 | 测试包+正式包双重验证 |
| 单元测试覆盖不足 | 中 | 阶段八 | 覆盖所有 FR 关键场景 + 多层重定向 + 并发安全 |
