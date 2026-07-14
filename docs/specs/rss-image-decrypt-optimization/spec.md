# 需求规格：订阅源图片解密优化

## Intent（意图）

修复 91 大事件等订阅源 `ruleImage` 为 JS 脚本且内部执行图片解密时导致的两个用户可感知问题：

1. **调试功能崩溃**：用户调试此类源时，软件直接崩溃（OOM/ANR/TransactionTooLargeException）
2. **列表加载明显变慢**：用户浏览此类源列表时，加载耗时从毫秒级退化到秒级甚至数十秒

## Scope（范围）

### 涉及组件

| 组件 | 路径 | 变更范围 |
|------|------|---------|
| RssParserByRule | `model/analyzeRule/RssParserByRule.kt` | 调试输出截断 + for 循环并行化 |
| Debug | `help/Debug.kt` | log 函数全局截断保护 |
| AppLog | `AppLog.kt` | putEntry 同步截断 |
| 91大事件源 JS | ruleImage 字段 | 引入 CacheManager 缓存解密结果 |

### 不在范围内

- 不重构 AnalyzeRule 内部结构（仅做实例隔离）
- 不改造 Legado JS 引擎同步模型
- 不修改 Glide 缓存机制
- 不修改普通 RssSource 的非 JS ruleImage 流程

## Approach（方案）

### 三管齐下

| 阶段 | 措施 | 解决问题 |
|------|------|---------|
| P0 | 调试输出截断（2000 字符全局上限 + data URI 专项截断） | 调试崩溃 |
| P1-1 | for 循环改 `async{}.awaitAll()` + Semaphore(6) 限流 | 列表串行慢 |
| P1-2 | JS 内 CacheManager 缓存解密结果 | 重复解密 |

### Alternatives Considered（备选方案）

#### 备选1：纯 JS 异步化（不推荐）
- **方案**：将 JS 内 `OkHttpClient.newCall(req).execute()` 改为异步回调
- **拒绝原因**：
  - Legado JS 引擎 evalJS 是同步模型，异步化需改造引擎
  - 改造成本高，风险大，影响所有书源/订阅源
  - 收益有限（并行化已能解决列表慢的问题）
- **结论**：不采用，改为在 Kotlin 层并行化调用整个 ruleImage JS

#### 备选2：data URI 改 file:// 路径（不推荐）
- **方案**：JS 解密后将图片写入本地文件，返回 `file://` 路径，让 Glide 磁盘缓存
- **拒绝原因**：
  - JS 内无文件写入 API（需扩展引擎）
  - 文件清理机制缺失，导致磁盘泄漏
  - 缓存由 JS 内 CacheManager 已足够（内存级缓存）
- **结论**：不采用，保留 data URI，但用 CacheManager 内存缓存

## Drawbacks（缺点）

### 源码验证后的真实风险（子代理深度验证）

| 缺点 | 影响 | 缓解措施 | 验证状态 |
|------|------|---------|---------|
| **并行化需每item独立 AnalyzeRule 实例** | AnalyzeRule L859-870 evalJSCallCount++/topScopeRef/scriptCache(HashMap) 并发非线程安全，复用实例必崩溃/数据错乱 | 🔴 硬性前提1：tasks.md 3.0a 明确，async块内new独立实例 | ✅ 源码确认 |
| **并行化需保护 articleList** | RssParserByRule L43 mutableListOf 非线程安全，并行add丢数据/崩溃 | 🔴 硬性前提2：tasks.md 3.0b 明确，awaitAll后批量收集 | ✅ 源码确认 |
| Semaphore 限流可能降低极端场景速度 | 网络极好时无法满速 | 限流值6可配置；OkHttp连接池50空闲(HttpHelper L91) | ✅ 源码确认 |
| 截断2000字符可能丢失部分调试信息 | 长文本调试输出被截断 | UTF-8安全截断(offsetByCodePoints) + data URI专项(前80字符) + 长度提示 | ✅ 设计保证 |
| CacheManager runBlocking 阻塞线程 | cache.get/put内部runBlocking(IO)阻塞调用线程 | 缓存命中跳过网络+解密净收益正；IO调度器64线程6并行不死锁 | ✅ 源码确认 CacheManager L69/L91 |

### 已排除的风险（源码验证后确认安全）

| 风险点 | 排除依据 |
|--------|---------|
| Rhino JS引擎并发不安全 | RhinoScriptEngine L261-269 Context.enter() 基于 ThreadLocal，每线程独立 Context |
| AnalyzeRule 有共享静态状态 | AnalyzeRule L960-986 companion object 只有 Pattern（不可变）+ 扩展函数 |
| OkHttpClient 每次 new 爆炸 | 短生命周期 GC 可回收，6个约15MB，不会爆炸（可后续优化） |
| item 之间有状态依赖 | RssParserByRule L73 variable 是 String? 不可变，L76 index==0 仅控制 log 开关 |

## Requirements（需求）

### R1：调试功能不崩溃
- R1.1：对 `data:image/...;base64,...` 格式 data URI 在调试输出前截断为前 80 字符 + 长度提示
- R1.2：Debug.log 函数入口加全局截断（>2000 字符截断为前 2000 字符 + 截断提示）
- R1.3：AppLog.putEntry 同步应用截断逻辑
- R1.4：截断后的调试信息仍可读（包含类型标识 + 前缀内容 + 总长度）

### R2：列表加载提速 50%+
- R2.1：RssParserByRule 的 for 循环改为 `async{}.awaitAll()` 并行执行
- R2.2：使用 Semaphore(6) 限流，避免 AnalyzeRule 非线程安全 + 网络压力
- R2.3：每个 item 创建独立 AnalyzeRule 实例
- R2.4：保持原有错误处理逻辑（单个 item 失败不影响整体）
- R2.5：20 条目列表加载时间从 4~40 秒降至 1~8 秒

### R3：不影响现有源
- R3.1：普通 RssSource（非 JS ruleImage）流程不变
- R3.2：无图片字段的源不受影响
- R3.3：调试功能对短文本源仍输出完整内容（<2000 字符不截断）

### R4：解密结果缓存（可选优化）
- R4.1：91 源 JS 内使用 CacheManager 缓存解密后的 data URI
- R4.2：缓存 key 基于图片 URL（去参数后）
- R4.3：缓存命中时直接返回，跳过网络请求 + AES 解密

## Scenarios（场景）

### S1：调试 91 大事件源
- **前置**：用户导入 91 大事件订阅源，进入调试界面
- **动作**：点击"调试"按钮
- **期望**：
  - 软件不崩溃
  - 调试日志显示"图片字段：data:image/jpeg;base64,/9j/4AAQ...(共 72800 字符，已截断)"
  - 列表项正常显示图片

### S2：浏览 91 大事件列表
- **前置**：用户在订阅源列表中打开 91 大事件
- **动作**：滑动浏览列表
- **期望**：
  - 首屏加载 < 8 秒（20 条目）
  - 滑动不卡顿
  - 图片正常显示
  - 二次刷新（缓存命中）加载 < 2 秒

### S3：普通订阅源不受影响
- **前置**：用户使用普通 RssSource（非 JS ruleImage）
- **动作**：调试 + 列表浏览
- **期望**：
  - 调试输出完整（<2000 字符不截断）
  - 列表加载速度与改造前一致
  - 无回归问题

### S4：网络异常场景
- **前置**：部分图片 URL 不可达
- **动作**：列表加载
- **期望**：
  - 单个图片失败不影响其他图片
  - 失败图片显示占位图
  - 调试日志记录失败原因
