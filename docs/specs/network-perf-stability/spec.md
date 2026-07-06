# spec.md - 网络性能与稳定性深度优化 + 延伸版本功能借鉴

> **状态**：🔄 设计中（第四版，基于 8 份深度分析文档整合）
> **创建日期**：2026-07-06
> **最新调整**：2026-07-06（整合优化点影响分析 + 缺失功能分析）

---

## 一、Intent（意图）

### 1.1 业务意图

Legado 作为开源电子书阅读器，**网络层是其一切业务的基础**。当前项目已完依赖升级（OkHttp 5.4.0、Kotlin 协程、AndroidX），本次在**保证稳定性优先**的前提下，进一步优化网络组件性能，并借鉴延伸版本的优秀功能提升用户体验。

### 1.2 关键约束（用户明确要求）

> "一定要把升级后的功能稳定性放在第一位，别为了性能升级，导致跟之前你搞得一些版本升级一样，各种问题，导致功能不可用"

> "完全可以参考借鉴引入到我们的项目中去！"

**因此本次优化的核心原则**：
1. **稳定性 > 性能**：宁可少优化，不可引入回归
2. **借鉴成熟实现**：参考 7 个可达延伸版本（蛋蛋Max/阅读NG/阅读T/阅读Archive/阅读R/Jingshiro/喵公子）的做法，不闭门造车
3. **不偏离生态**：不改变主流版本共有的设计选择（如不重试 IOException）
4. **对比方法论规范**：所有优化/借鉴必须遵循 [延伸版本对比方法论规范](../../project-rules/forks_comparison_methodology.md)
5. **分阶段实施**：P0 立即 → P1 谨慎 → P2 评估 → P3 暂缓

### 1.3 衡量标准

| 指标 | 当前 | 目标 | 备注 |
|------|------|------|------|
| 明确 Bug 修复数 | 0 | 9（P0） | 全部是低风险，不会导致功能不可用 |
| 中风险优化数 | 0 | 8（P1） | 需充分回归测试 |
| 高风险暂缓数 | 0 | 5（P3） | 可能影响书源可用性，暂缓 |
| 内存泄漏修复 | 0 | 5 处（P1） | LRU 治理 |
| 功能借鉴（短平快） | 0 | 3 项（P0） | 用户可感知 |
| 功能借鉴（中等） | 0 | 5 项（P1） | 用户体验提升 |
| 功能借鉴（长期） | 0 | 5 项（P2/P3） | 长期演进 |
| 回归风险 | - | 极低 | 不改主流版本共有的设计 |

---

## 二、Scope（范围）

### 2.1 In Scope（本次实施）

#### P0 立即实施（9 项低风险优化 + 3 项短平快功能借鉴）

##### P0 优化点（9 项低风险，不会导致功能不可用）

| 编号 | 优化点 | 文件锚点 | 性质 | 影响分析结论 |
|------|--------|----------|------|------------|
| A1 | CancellationException 透传修复 | `Coroutine.kt:182` + `WebBook.kt` 5 处 + `FlowExtensions.kt:59-70` | 明确 Bug | 标准协程用法，不会导致功能不可用 |
| A2 | mutexMap 线程安全修复（ConcurrentHashMap） | `BookSourceExtensions.kt:27,50` | 明确 Bug | 行为一致，仅修复线程安全 |
| A4 | OkHttpExceptionInterceptor CancellationException 透传 | `OkHttpExceptionInterceptor.kt:13-17` | 明确 Bug | 仅影响取消异常传播，不影响正常请求 |
| B3 | MainViewModel poll() race condition 修复（ConcurrentLinkedQueue） | `MainViewModel.kt:55,148` | 明确 Bug | API 兼容，行为一致 |
| B4 | CacheBook.close() 同步修复（@Synchronized） | `CacheBook.kt:117` | 明确 Bug | 与其他方法锁一致 |
| B5 | BookHelp 互斥失效修复（unlock 后 remove） | `BookHelp.kt:261` | 明确 Bug | 修复互斥失效，无功能影响 |
| B6 | WebViewPool 池化修复（借鉴阅读Archive closed 标志） | `WebViewPool.kt` | 防御性增强 | 引用相等检查，避免数据串错 |
| C2 | 307/308 重定向保持 method+body（借鉴蛋蛋Max） | `OkHttpUtils.kt:29-43` | 借鉴成熟实现 | RFC 7538 标准，蛋蛋Max 已验证 |
| P0-6 | SSLContext "SSL" → "TLS" | `SSLHelper.kt:57` | 明确 Bug | TLS 是 SSL 的安全替代，行为兼容 |

##### P0 功能借鉴（3 项短平快，用户可感知）

| 编号 | 功能 | 来源版本 | 文件数 | 借鉴依据 |
|------|------|---------|--------|---------|
| F-P0-1 | 调试工具集（编码/HTTP/curl/ping/正则/时间戳） | 蛋蛋Max | 14 | 用户可感知，难度低 |
| F-P0-2 | 备份选择器（分类预览+一键备份） | 蛋蛋Max | 前端+后端 | 用户可感知，难度低 |
| F-P0-3 | Web 端备份管理（BackupManager 完整移植） | 蛋蛋Max | 4 | 用户可感知，难度低 |

#### P1 谨慎实施（8 项中风险优化 + 5 项中等难度功能借鉴）

##### P1 优化点（8 项中风险，需谨慎实施）

| 编号 | 优化点 | 文件锚点 | 影响场景 | 影响分析结论 |
|------|--------|----------|---------|------------|
| A3 | CookieStore 随机删除改 LRU 淘汰 | `CookieStore.kt:85-90` | 大 Cookie 站点登录态 | 可能影响边缘场景，但不会导致功能不可用 |
| A6 | proxyClientCache LRU 上限（20-30） | `HttpHelper.kt:25-27` | 多代理书源切换 | 影响代理书源请求性能，但不影响功能可用性 |
| A7 | BackstageWebView 复用回调错乱修复（closed 标志） | `BackstageWebView.kt:243-247` | WebView 书源批量校验 | 涉及 WebView 核心调用链，但修复是纯防御性增强 |
| C3 | 连接池显式调优（50 连接 / 5 分钟） | `HttpHelper.kt:51-127` | 内存占用 +200KB | 200KB 内存占用可接受 |
| C5 | customIp LRU 上限（100） | `AnalyzeUrl.kt:773` | DNS 缓存场景 | 与 P0-7 协同，LruCache 自身线程安全 |
| B1 | BackstageWebView runBlocking 修复（预查询+内存缓存） | `BackstageWebView.kt:118` | 书源调试场景 | 采用预查询方案，改动小风险低 |
| B2 | BottomWebViewDialog runBlocking 修复（优化内部逻辑） | `BottomWebViewDialog.kt:819` | RSS 阅读/源编辑预览 | shouldInterceptRequest 必须 synchronous，runBlocking 不可避免，仅优化内部逻辑 |
| C4 | failUrl / concurrentRecordMap / stringRuleCache LRU 治理 | 多文件 | 长跑稳定性 | 5 处内存泄漏全部加 LRU 上限或定期清理 |

##### P1 功能借鉴（5 项中等难度）

| 编号 | 功能 | 来源版本 | 文件数 | 用户价值 |
|------|------|---------|--------|---------|
| F-P1-1 | 自动任务系统（Cron + AlarmManager） | 阅读T | 11 | ⭐⭐⭐⭐ |
| F-P1-2 | 高亮规则系统（关键词/正则+多 Span 样式） | 蛋蛋Max/阅读T | 10 | ⭐⭐⭐⭐ |
| F-P1-3 | 调试日志面板 + 浮球（Overlay 窗口） | 蛋蛋Max | 13 | ⭐⭐⭐⭐ |
| F-P1-4 | 阅读热力图 | 蛋蛋Max | - | ⭐⭐⭐ |
| F-P1-5 | 书籍想法/笔记系统（含 Obsidian 导出） | Jingshiro | 8 | ⭐⭐⭐⭐ |

#### P2 评估实施（高风险项评估 + 长期功能借鉴）

##### P2 优化点（评估后决定是否实施）

| 编号 | 优化点 | 风险 | 评估倾向 |
|------|--------|------|----------|
| P2-1 | retry 重试 IOException | 高 | **倾向不实施** - 主流版本都有意不重试，是生态设计选择 |
| P2-2 | Cronet 熔断器 | 中 | 评估 - 自实现熔断需充分测试 |
| P2-3 | 启用 Cronet 协程拦截器 | 中 | 评估 - 协程版有 runBlocking 需先修复 |
| P2-4 | 限流器 Mutex 化 | 高 | 评估 - 锁结构变更风险高 |
| P2-5 | CacheBook 锁优化 | 高 | 评估 - @Synchronized 是稳定选择 |

##### P2 功能借鉴（长期功能）

| 编号 | 功能 | 来源版本 | 文件数 | 用户价值 |
|------|------|---------|--------|---------|
| F-P2-1 | AI 聊天框架（三大 AI Provider 统一接口） | 阅读NG/Rimchars/refgd | 22+15+8 | ⭐⭐⭐⭐⭐ |
| F-P2-2 | MCP 服务（Legado 作为 MCP Server） | 阅读NG | 7 | ⭐⭐⭐⭐ |
| F-P2-3 | 主题包管理器 | 蛋蛋Max/Rimchars | - | ⭐⭐⭐ |

### 2.2 Out of Scope（不在本次实施）

#### P3 暂缓实施（5 项高风险优化，可能影响书源可用性）

> **核心结论**：5 项高风险优化可能导致部分书源不可用，**强烈建议暂缓实施**。

| 编号 | 优化点 | 文件锚点 | 影响场景 | 暂缓理由 |
|------|--------|----------|---------|---------|
| A5 | ObsoleteUrlFactory 自定义证书失效修复 | `ObsoleteUrlFactory.kt:988-991` | 自签名证书书源 | 修复后传入自定义 TrustManager 不信任自签名证书，会导致 SSL 握手失败 → 书源不可用 |
| C1 | SOCKS5 隧道完整实现 | `HttpHelper.kt` + 新增 3 文件 | 网络层核心逻辑 | 阅读T 独有的协议级实现，改动面大，风险高 |
| C6 | HttpLogInterceptor | `HttpHelper.kt` | 网络层核心逻辑 | 阅读T 独有，影响所有请求，需充分测试 |
| C7 | SSL 配置可选化 | `HttpHelper.kt` + `AppConfig` | 默认不启用 unsafe SSL 后部分书源不可用 | 蛋蛋Max 独有，默认不启用 unsafe SSL 后部分自签证书网站将无法访问 |
| C8 | NetworkLogInterceptor | `HttpHelper.kt` | 网络层核心逻辑 | 阅读NG 独有，影响所有请求，需充分测试 |

#### P3 长期功能借鉴

| 编号 | 功能 | 来源版本 | 文件数 | 用户价值 |
|------|------|---------|--------|---------|
| F-P3-1 | Epub 独立渲染引擎 | Rimchars | 5 | ⭐⭐⭐⭐ |
| F-P3-2 | 阅读菜单自定义按钮（JS 注入） | Rimchars | 4 | ⭐⭐⭐ |

#### 其他 Out of Scope

- **OkHttp/Cronet 版本升级**：当前版本已稳定
- **Vue3 前端网络层重构**：本次仅优化 Android 端 + 借鉴蛋蛋Max 备份功能
- **下载服务 OkHttp 化**：大范围重构，单独 spec

---

## 三、Approach（方案）

### 3.1 Selected Approach（选定方案）

**保守修复 + 借鉴成熟实现 + 低风险优化 + 分阶段功能借鉴**

#### 核心原则

1. **仅修复明确 Bug（P0）**：9 项低风险优化全部是不改变行为的 Bug 修复或防御性增强
2. **借鉴蛋蛋Max/阅读Archive 验证过的优化（P0）**：307/308 重定向 + WebView 池化修复
3. **P1 谨慎实施中风险优化**：8 项中风险优化需充分回归测试
4. **分阶段功能借鉴**：3 项短平快（P0） + 5 项中等难度（P1） + 5 项长期（P2/P3）
5. **高风险项全部暂缓（P3）**：5 项可能导致书源不可用的优化不实施

#### 关键技术决策

| 决策点 | 选定方案 | 理由 |
|--------|----------|------|
| 重试策略 | **保持现状**（不重试 IOException） | 主流版本都有意不重试，是生态设计选择 |
| 307/308 重定向 | 借鉴蛋蛋Max 实现 | 已验证的优化，保持 POST body |
| 取消异常处理 | `if (e is CancellationException) throw e` 守卫 | 协程取消语义不可破坏 |
| runBlocking 防护 | 预查询 + 内存缓存（B1）/ 优化内部逻辑（B2） | 避免 ANR，改动小 |
| LRU 上限 | `LruCache` 或 `LinkedHashMap` + `removeEldestEntry` | 复用标准库 |
| 连接池 | `ConnectionPool(50, 5, MINUTES)` | 平衡内存与复用率 |
| 锁结构 | **保持 @Synchronized 不变** | 主流版本都这么用，稳定 |
| Cronet 拦截器 | **保持同步版不变** | 协程版有 runBlocking 问题，需单独评估 |
| WebView 池化 | 借鉴阅读Archive closed 标志 + isActiveWebView | 防御性增强，避免数据串错 |
| 功能借鉴 | 分阶段（P0 短平快 → P1 中等 → P2/P3 长期） | 按价值/难度排序 |

### 3.2 Alternatives Considered（替代方案）

| 替代方案 | 描述 | 否决理由 |
|---------|------|----------|
| **A1. 激进优化方案（原方案）** | 包括 retry 重试 IOException、CacheBook 锁优化、Cronet 熔断器、限流器 Mutex 化 | **主流版本都没做这些优化**，贸然修改偏离生态，回归风险高；用户明确要求"稳定性优先" |
| **A2. 大重构方案** | 引入 Resilience4j + Retrofit + 协程原生客户端 | 改动范围过大；引入新依赖违反"不引入无用依赖"原则 |
| **A3. retry 重试 IOException** | 捕获 IOException + 指数退避 + 最多 3 次 | **5 个主流延伸版本都有意不重试**，是生态设计选择；可能增加服务端压力被识别为恶意请求 |
| **A4. CacheBook 锁优化** | @Synchronized 改 computeIfAbsent + AtomicReference | 主流版本都用 @Synchronized，稳定；锁结构变更风险高 |
| **A5. 启用 Cronet 协程拦截器** | 替换同步版 | 协程版内部有 runBlocking（L56, L78），需先修复；功能等价性需验证 |
| **A6. 限流器 Mutex 化** | synchronized → Mutex | 非重入语义差异；主流版本都用 synchronized |
| **A7. 引入 Resilience4j 熔断** | 用成熟库替代自实现 | 引入 200KB+ 依赖；自实现熔断也需充分测试 |
| **A8. HTTP 响应缓存** | 启用 OkHttp Cache | 可能影响书源实时性（书源列表更新需立即生效） |
| **A9. 仅 P0 修复方案** | 只修复 9 个低风险 Bug | 内存泄漏不修复会影响长跑稳定性；P1 中风险项应一并做 |
| **A10. 不做功能借鉴** | 仅优化网络层，不借鉴延伸版本功能 | 用户明确要求"完全可以参考借鉴引入到我们的项目中去" |
| **A11. 一次性实施所有功能借鉴** | P0/P1/P2/P3 功能借鉴全部实施 | 改动面过大，回归风险高；分阶段实施更稳妥 |
| **A12. 实施 P3 高风险优化** | A5/C1/C6/C7/C8 全部实施 | 可能导致部分书源不可用，用户明确要求"稳定性优先" |

### 3.3 Drawbacks（选定方案的缺点）

| 缺点 | 影响 | 接受理由 |
|------|------|----------|
| **D1. 不重试 IOException** | 网络瞬时故障不可恢复 | 主流版本都有意不重试，是生态设计选择；用户可配置 retry；不偏离生态 |
| **D2. 不做锁结构优化** | 多书并发下载吞吐仍是串行 | @Synchronized 是稳定选择；主流版本都这么用；性能优化不应以稳定性为代价 |
| **D3. 不做 Cronet 熔断** | Cronet 持续故障耗时翻倍 | 自实现熔断需充分测试；本轮聚焦稳定性；列入 P2 评估 |
| **D4. P1 连接池扩大到 50 增加内存占用** | 每个空闲连接约 4KB，50 个约 200KB | 200KB 内存占用可接受；连接复用率提升带来的收益远大于内存成本 |
| **D5. 高风险项全部暂缓（P3）** | 部分性能问题未解决 | 用户明确要求稳定性优先；P3 项可能影响书源可用性 |
| **D6. 307/308 重定向处理可能改变现有行为** | 部分书源可能依赖 OkHttp 默认重定向 | 蛋蛋Max 已验证；307/308 保持 method+body 是 RFC 7538 标准 |
| **D7. 功能借鉴分阶段实施，周期长** | P2/P3 功能借鉴需 3-6 个月 | 按价值/难度排序，短平快先做，长期功能后做 |
| **D8. B2 BottomWebViewDialog runBlocking 无法彻底修复** | shouldInterceptRequest 必须 synchronous | WebView API 的固有限制，仅能优化内部逻辑 |
| **D9. A3 CookieStore LRU 淘汰可能删除关键 Cookie** | 大 Cookie 场景登录态丢失 | 需设计合理策略（优先删除 tracking Cookie），充分测试 |

### 3.4 Prior Art（参考）

- **蛋蛋阅读·Max（DandanLLab/Legado_Max）**：307/308 重定向处理 + 调试工具集 + 备份管理 + 高亮规则 + 调试日志面板
- **阅读Archive（Rimchars/legado）**：WebView 池化修复范式（closed 标志 + isActiveWebView）+ Epub 渲染引擎 + AI 框架
- **阅读NG（joestar817/legado_NG）**：AI 聊天框架 + MCP 服务
- **阅读T（skybbk1001/legadoT）**：自动任务系统 + 高亮规则 + SOCKS5 隧道 + Brotli 解压
- **Jingshiro（Jingshiro/legado）**：书籍想法/笔记系统
- **OkHttp 官方文档**：连接池配置、重试拦截器最佳实践
- **Kotlin 协程官方文档**：CancellationException 处理语义
- **RFC 7538**：307/308 重定向标准

---

## 四、Requirements（需求）

### 4.1 功能需求 - P0 优化点（9 项低风险）

#### FR-A1：CancellationException 透传修复

- **FR-A1.1**：`Coroutine.executeInternal` 的 catch 块首行必须 `if (e is CancellationException) throw e`
- **FR-A1.2**：`WebBook.kt` 中 5 处 `catch (_: Throwable) { throw throwable }` 必须加 CancellationException 守卫
- **FR-A1.3**：`FlowExtensions.mapParallelSafe` 的 catch 块必须先判断 CancellationException
- **FR-A1.4**：`OkHttpExceptionInterceptor` 的 catch 块必须先判断 CancellationException
- **FR-A1.5**：不改变其他异常的处理逻辑

#### FR-A2：mutexMap 线程安全修复

- **FR-A2.1**：`BookSourceExtensions.mutexMap` 从 `hashMapOf` 改为 `ConcurrentHashMap`
- **FR-A2.2**：`exploreKinds` 方法中 `mutexMap[bookSourceUrl] ?: Mutex().apply { ... }` 改为 `computeIfAbsent`

#### FR-B3：MainViewModel poll() 线程安全修复

- **FR-B3.1**：`MainViewModel.waitUpTocBooks` 从 `LinkedList` 改为 `ConcurrentLinkedQueue`
- **FR-B3.2**：`addToWaitUp` 的 `@Synchronized` 可保留（保护复合操作）

#### FR-B4：CacheBook.close() 同步修复

- **FR-B4.1**：`CacheBook.close()` 方法添加 `@Synchronized` 注解

#### FR-B5：BookHelp 互斥失效修复

- **FR-B5.1**：`BookHelp.saveImage` 的 finally 块中 `mutex.unlock()` 必须在 `downloadImages.remove(src)` 之前

#### FR-B6：WebViewPool 池化修复（借鉴阅读Archive）

- **FR-B6.1**：`WebViewPool` 增加 `closed` 标志
- **FR-B6.2**：增加 `isActiveWebView(webView: WebView? = null)` 方法（引用相等检查）
- **FR-B6.3**：`destroy()` 方法增加 closed 和 callback 清理，重入安全
- **FR-B6.4**：`EvalJsRunnable.run` 的检查改为 `isActiveWebView(mWebView.get())`

#### FR-C2：307/308 重定向处理（借鉴蛋蛋Max）

- **FR-C2.1**：`OkHttpUtils.newCallResponse` 增加 307/308 状态码处理
- **FR-C2.2**：重定向时保持原 method 和 body
- **FR-C2.3**：跟随 Location header
- **FR-C2.4**：受 retry 次数限制

#### FR-P0-6：SSLContext 协议修正

- **FR-P0-6.1**：`SSLHelper.kt` 的 `SSLContext.getInstance("SSL")` 改为 `getInstance("TLS")`

### 4.2 功能需求 - P0 功能借鉴（3 项短平快）

#### FR-F-P0-1：调试工具集（借鉴蛋蛋Max）

- **FR-F-P0-1.1**：新增 6 个调试工具：编码转换/HTTP 请求/curl 命令/ping/正则测试/时间戳转换
- **FR-F-P0-1.2**：每个工具独立 Activity，支持复制结果
- **FR-F-P0-1.3**：入口在"我的"页面 → 调试工具

#### FR-F-P0-2：备份选择器（借鉴蛋蛋Max）

- **FR-F-P0-2.1**：备份预览功能（6 大类：书籍/源/规则/语音/配置/其他）
- **FR-F-P0-2.2**：分类聚合 + 可折叠详情
- **FR-F-P0-2.3**：一键备份 ZIP

#### FR-F-P0-3：Web 端备份管理（借鉴蛋蛋Max）

- **FR-F-P0-3.1**：移植 `BackupManager.vue` + `backupRouter.ts` + `pages/backup/{index.html,main.js}`
- **FR-F-P0-3.2**：修改 `router/index.ts` 集成 backupRoutes
- **FR-F-P0-3.3**：修改 `views/BookShelf.vue` 增加"数据备份"入口按钮
- **FR-F-P0-3.4**：修改 `api/api.ts` 新增 `BackupItemInfo`/`BackupOverview` 类型 + `getBackupPreview()`/`getBackupUrl()` 方法
- **FR-F-P0-3.5**：**后端配合**：确认 `WebServer.kt` 已实现 `/backup` 和 `/backupPreview` 接口

### 4.3 功能需求 - P1 优化点（8 项中风险）

#### FR-A3：CookieStore LRU 淘汰

- **FR-A3.1**：`CookieStore.getCookie` 的随机删除改为优先删除 tracking Cookie（_ga/_gid/_gat/Hm_lvt_*/_hjid）
- **FR-A3.2**：其次按 key 长度降序删除
- **FR-A3.3**：不新增 lastAccessTime 字段，避免数据库迁移

#### FR-A6：proxyClientCache LRU 上限

- **FR-A6.1**：`proxyClientCache` 加 LRU 上限 20-30
- **FR-A6.2**：用 `LinkedHashMap` + `removeEldestEntry` + 同步包装

#### FR-A7：BackstageWebView 复用回调错乱修复

- **FR-A7.1**：增加 `closed` 标志和 `isActiveWebView(webView)` 方法
- **FR-A7.2**：`destroy()` 增加 closed 和 callback 清理，重入安全
- **FR-A7.3**：`EvalJsRunnable.run` 改为 `isActiveWebView(mWebView.get())` 检查

#### FR-C3：连接池调优

- **FR-C3.1**：`HttpHelper.okHttpClient` 显式配置 `ConnectionPool(50, 5, TimeUnit.MINUTES)`
- **FR-C3.2**：派生客户端继承新连接池

#### FR-C5：customIp LRU 上限

- **FR-C5.1**：`AnalyzeUrl.customIp` 改用 `LruCache<String, String>(100)`（与 P0-7 协同）

#### FR-B1：BackstageWebView runBlocking 修复

- **FR-B1.1**：在 `SourceHelp` 增加 `getCachedBookSource(key: String): BookSource?` 内存缓存方法
- **FR-B1.2**：`BackstageWebView.load()` 先读缓存，未命中再 runBlocking
- **FR-B1.3**：`SourceHelp.loadBookSource` 等方法同步写入缓存

#### FR-B2：BottomWebViewDialog runBlocking 优化

- **FR-B2.1**：优化 `runBlocking` 内部逻辑（改用同步 OkHttp 请求避免线程切换）
- **FR-B2.2**：不改变 runBlocking 本身（shouldInterceptRequest 必须 synchronous）

#### FR-C4：内存泄漏治理

- **FR-C4.1**：`failUrl` 改 `LruCache<String, Boolean>(200)`
- **FR-C4.2**：`concurrentRecordMap` 在删源时清理（新增 `clearRecord(sourceUrl)` 方法）
- **FR-C4.3**：`stringRuleCache` 改 `LruCache<String, String>(64)`

### 4.4 功能需求 - P1 功能借鉴（5 项中等难度）

#### FR-F-P1-1：自动任务系统（借鉴阅读T）

- **FR-F-P1-1.1**：支持 Cron 表达式定时任务
- **FR-F-P1-1.2**：使用 AlarmManager 调度
- **FR-F-P1-1.3**：支持书源更新/订阅源更新/书架备份等任务类型

#### FR-F-P1-2：高亮规则系统（借鉴蛋蛋Max/阅读T）

- **FR-F-P1-2.1**：关键词/正则高亮匹配
- **FR-F-P1-2.2**：多种高亮样式（背景色/前景色/下划线/波浪线/双下划线/虚线）
- **FR-F-P1-2.3**：颜色选择器、字体选择
- **FR-F-P1-2.4**：高亮规则分组管理

#### FR-F-P1-3：调试日志面板 + 浮球（借鉴蛋蛋Max）

- **FR-F-P1-3.1**：调试浮球（Overlay 窗口）
- **FR-F-P1-3.2**：日志分类（ERROR/WARN/INFO/DEBUG）
- **FR-F-P1-3.3**：流程日志（请求/响应链路）

#### FR-F-P1-4：阅读热力图（借鉴蛋蛋Max）

- **FR-F-P1-4.1**：按日期统计阅读时长
- **FR-F-P1-4.2**：热力图可视化（GitHub 风格）

#### FR-F-P1-5：书籍想法/笔记系统（借鉴 Jingshiro）

- **FR-F-P1-5.1**：读书笔记功能
- **FR-F-P1-5.2**：Markdown 生成
- **FR-F-P1-5.3**：Obsidian 集成导出

### 4.5 非功能需求

- **NFR-1 稳定性**：不引入任何回归，现有书源/RSS 源 API 行为完全兼容
- **NFR-2 可测性**：每个修复点有单元测试或集成测试
- **NFR-3 可观测性**：关键决策点记录 `AppLog.put` 日志
- **NFR-4 资源占用**：连接池扩大后内存占用增加 ≤ 200KB
- **NFR-5 长跑稳定性**：24 小时长跑无 OOM、无内存泄漏
- **NFR-6 功能借鉴兼容性**：借鉴功能不破坏现有功能，需端到端验证
- **NFR-7 对比方法论合规**：所有优化/借鉴遵循 [延伸版本对比方法论规范](../../project-rules/forks_comparison_methodology.md)

---

## 五、Scenarios（场景）

### 5.1 场景一：协程取消传播（P0 - A1）

**前置条件**：用户快速翻页，触发多次预下载取消

**当前行为**：
1. 翻页触发 `downloadScope.cancelChildren()`
2. 子协程抛出 `CancellationException`
3. `Coroutine.executeInternal` 的 `catch (e: Throwable)` 捕获
4. 调用 `errorReturn` 或 `error` 回调
5. 取消异常被当业务异常处理，破坏取消传播链

**优化后行为**：
1. 翻页触发 `downloadScope.cancelChildren()`
2. 子协程抛出 `CancellationException`
3. `Coroutine.executeInternal` 的 catch 块首行 `if (e is CancellationException) throw e`
4. 取消异常正确传播，不触发 error 回调

**验证标准**：取消操作不触发 error 回调

### 5.2 场景二：307/308 重定向保持 POST body（P0 - C2）

**前置条件**：书源 POST 请求遇到 307 重定向

**当前行为**：
1. OkHttp 默认跟随重定向，但可能将 POST 改为 GET
2. 丢失 body，服务端返回错误

**优化后行为**（借鉴蛋蛋Max）：
1. 检测 307/308 状态码
2. 保持原 method 和 body
3. 跟随 Location header
4. 受 retry 次数限制

**验证标准**：307/308 重定向保持 POST body

### 5.3 场景三：WebView 复用不串错（P0 - B6）

**前置条件**：批量校验含 WebView 的书源

**当前行为**：
1. WebView 池复用 WebView 后
2. 旧 EvalJsRunnable 的回调可能误把新实例的结果当作自己的
3. 数据串错

**优化后行为**（借鉴阅读Archive）：
1. 引入 closed 标志
2. isActiveWebView 引用相等检查
3. 回调只处理当前活跃 WebView 的结果

**验证标准**：批量 WebView 书源校验不出现数据串错

### 5.4 场景四：长跑稳定性（P1 - C4）

**前置条件**：用户连续使用 App 24 小时

**当前行为**：
1. `proxyClientCache` / `customIp` / `failUrl` / `concurrentRecordMap` / `stringRuleCache` 持续增长
2. 24 小时后内存占用显著增长

**优化后行为**：
1. 5 处内存泄漏全部加 LRU 上限或定期清理
2. 24 小时后内存占用稳定

**验证标准**：24 小时长跑后内存增长 ≤ 50MB

### 5.5 场景五：大 Cookie 站点登录态保持（P1 - A3）

**前置条件**：用户访问 Cookie 总长度超 4096 字节的站点

**当前行为**：
1. `CookieStore.getCookie` 随机删除 Cookie key
2. 可能命中关键 session_id/token Cookie
3. 用户被强制登出

**优化后行为**：
1. 优先删除 tracking Cookie（_ga/_gid 等）
2. 其次按 key 长度降序删除
3. 保护关键登录 Cookie

**验证标准**：大 Cookie 站点登录态保持

### 5.6 场景六：Web 端一键备份（P0 - F-P0-3）

**前置条件**：用户在浏览器访问 Legado Web 端

**当前行为**：
1. 用户必须打开 App 才能备份
2. 无 Web 端备份能力

**优化后行为**（借鉴蛋蛋Max）：
1. Web 端新增"数据备份"入口
2. 点击进入 BackupManager 页面
3. 分类预览（书籍/源/规则/语音/配置/其他）
4. 一键下载备份 ZIP

**验证标准**：Web 端一键备份功能可用

### 5.7 场景七：高亮规则匹配（P1 - F-P1-2）

**前置条件**：用户阅读时希望高亮特定关键词

**当前行为**：
1. 无高亮规则系统
2. 用户无法自定义高亮

**优化后行为**（借鉴蛋蛋Max/阅读T）：
1. 配置高亮规则（关键词/正则）
2. 选择高亮样式（背景色/下划线/波浪线等）
3. 阅读时自动高亮匹配内容

**验证标准**：高亮规则匹配正确，样式生效

---

## 六、验收标准

### 6.1 P0 阶段验收

- [ ] 所有 P0 优化点（A1/A2/A4/B3/B4/B5/B6/C2/P0-6）实施完成
- [ ] 所有 P0 功能借鉴（F-P0-1/F-P0-2/F-P0-3）实施完成
- [ ] 单元测试覆盖每个修复点
- [ ] 现有书源/RSS 源功能回归测试通过
- [ ] 编译通过，无新增警告

### 6.2 P1 阶段验收

- [ ] 所有 P1 优化点（A3/A6/A7/B1/B2/C3/C4/C5）实施完成
- [ ] 所有 P1 功能借鉴（F-P1-1 ~ F-P1-5）实施完成
- [ ] 24 小时长跑测试无 OOM
- [ ] 内存泄漏检测通过（LeakCanary 无报错）
- [ ] 连接复用率提升验证

### 6.3 整体验收

- [ ] 全量回归测试通过
- [ ] 文档同步完成（docs/project-flow/ + AGENTS.md + updateLog.md）
- [ ] 5 项高风险优化（P3）暂缓实施，不影响本轮稳定性
- [ ] 功能借鉴端到端验证（含真机测试）
