# 仿真器 vs 真机 Debug.kt 对比分析

## 概述

仿真器 `BookSourceDebugger` / `RssSourceDebugger` 与真机 `Debug.kt` 的方法对比和差异点。

- **真机源码**：`app/src/main/java/io/legado/app/model/Debug.kt`（`object Debug` 单例）
- **仿真器源码**：
  - `tools/legado-jvm/.../BookSourceDebugger.kt`（普通类）
  - `tools/legado-jvm/.../RssSourceDebugger.kt`（普通类）

## 架构层差异（根本性）

| 维度 | 真机 Debug.kt | 仿真器 |
|------|--------------|--------|
| **封装层级** | 通过 `WebBook` / `Rss` 协程封装层调用 | 直接内联 `AnalyzeUrl` + `AnalyzeRule` |
| **并发模型** | `CoroutineScope` + `CompositeCoroutine` 管理任务 | 同步顺序执行（无协程） |
| **日志机制** | `callback?.printLog(state, msg)` 回调 | `DebugLogger` 接口 |
| **实例形态** | `object Debug` 全局单例 | 每次调试 new 一个实例 |

> **说明**：仿真器跳过 `WebBook`/`Rss` 封装层，直接操作 `AnalyzeUrl`/`AnalyzeRule`，目的是暴露底层细节便于调试。真机的协程封装层主要做并发调度和错误包装，不影响规则解析逻辑本身。

## 差异点清单

### 1. baseUrl 传递

- **仿真器**：方向1已修复，搜索/详情/目录/正文阶段均传 `baseUrl = bookSource.bookSourceUrl`（或 `book.bookUrl`）
- **真机**：`Debug.kt` 中 `WebBook.searchBook` / `getBookInfo` 等内部构造 `AnalyzeUrl` 时传 baseUrl
- **差异**：无（方向1已对齐）

### 2. setRedirectUrl

- **仿真器**：方向1已添加
- **真机**：`Debug.kt` 中通过 `WebBook` 链路调用
- **差异**：无（方向1已对齐）

### 3. getSubDomain

- **仿真器**：方向7已修复，`NetworkUtilsStub.getSubDomain` 剥离 `www` 前缀
- **真机**：`NetworkUtils.getSubDomain` 使用 `PublicSuffixDatabase` 精确识别域名后缀
- **差异**：仿真器无 `PublicSuffixDatabase`，仅剥离 `www`，对复杂域名后缀（如 `.co.uk`）可能识别不准

### 4. evalJS 上下文

- **仿真器**：方向9已注入 `java` / `cookie` / `cache` / `baseUrl`
- **真机**：`AnalyzeRule.evalJS` / `AnalyzeUrl.evalJS` 注入完整上下文
- **差异**：无（方向9已对齐）

### 5. ajax 委托

- **仿真器**：方向7已修复，`AnalyzeUrl.ajax` override 委托 `AnalyzeUrl` 自身构造请求
- **真机**：`AnalyzeUrl.ajax` 直接构造请求
- **差异**：无（方向7已对齐）

### 6. 调试入口分发逻辑

| key 格式 | 真机 Debug.kt | 仿真器 BookSourceDebugger |
|----------|--------------|---------------------------|
| `isAbsUrl` | `infoDebug`（详情页） | `debugInfo`（详情页） |
| 含 `::` | `exploreDebug`（发现页） | `debugSearch`（降级为搜索） |
| `++` 开头 | `tocDebug`（目录页） | `debugToc`（目录页） |
| `--` 开头 | `contentDebug`（正文页） | `debugContent`（正文页） |
| else | `searchDebug`（搜索页） | `debugSearch`（搜索页） |

- **差异**：含 `::` 的 key，真机走 `exploreDebug`（发现页），仿真器降级为 `debugSearch`。发现页与搜索页规则解析逻辑相似，不影响核心调试能力。

### 7. RssSource 调试链路

| 场景 | 真机 Debug.kt | 仿真器 RssSourceDebugger |
|------|--------------|--------------------------|
| `isAbsUrl` | `rssContentDebug`（内容页） | `debugContent`（内容页） |
| `singleUrl=true` | 真机无此分支 | `debugSingleUrl`（直接调试内容） |
| 含 `::` | `sortDebug`（分类页） | `debugSort`（列表页） |
| else | `sortDebug`（搜索页） | `debugSort`（列表页） |

- **差异**：仿真器新增 `singleUrl` 模式分支，真机无此分支（真机 singleUrl 源走 `Rss.getArticles` 内部处理）。

### 8. 错误处理

- **真机**：通过 `Coroutine.onError` 捕获，记录 `stackTraceStr`，state=-1
- **仿真器**：try/catch 捕获，区分 `WebViewRequiredException` / `UserInterventionException` / 普通 `Exception`
- **差异**：仿真器额外识别 WebView 渲染需求和用户介入场景，真机不区分（统一走 onError）

## 保真度限制清单

1. **getSubDomain**：无 `PublicSuffixDatabase`，仅剥离 `www`，复杂域名后缀识别不准
2. **evalJS**：Rhino 1.8.1 不支持 ES6+ 语法（`let`/`const`/箭头函数/模板字符串等）
3. **jsoup 1.16.2**：破坏性变更 jsoup#2017，CSS 选择器行为与真机一致但不可升级
4. **hutool 5.8.22**：加解密依赖版本锁定，不可升级
5. **发现页调试**：仿真器将 `::` key 降级为搜索，不走 `exploreDebug` 专用链路
6. **协程并发**：仿真器同步执行，真机协程异步，调试结果一致但执行顺序不同
7. **WebView 渲染**：仿真器不支持 WebView JS 执行，遇到 `useWebView=true` 抛 `WebViewRequiredException`
