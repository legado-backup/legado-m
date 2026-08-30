# Spec: Legado 核心质量优化

## Intent

Legado 项目经过长期迭代，积累了大量技术债务：内存泄漏、线程不安全、数据库 ANR、测试覆盖为零等问题。这些问题在普通使用场景下可能不明显，但在高并发书源搜索、大量书籍缓存、长时间阅读等极端场景下会导致 ANR、崩溃和数据丢失。本优化旨在系统性治理这些技术债务，使项目从"能用"提升到"稳定可靠"。

## Scope

### 包含

1. **内存泄漏治理**（P0）：IntentData、ReadBook.callBack、WebViewPool、31处 inner class
2. **线程安全统一**（P0）：ReadBook 的 synchronized+Mutex 混用、RecyclerAdapter 18个@Synchronized、WebViewPool 协程+锁
3. **数据库主线程查询消除**（P0）：移除 allowMainThreadQueries()，排查所有主线程 DAO 调用
4. **错误处理规范化**（P1）：29处 printStackTrace 替换、CronetCoroutineInterceptor TODO 崩溃修复、日志体系统一
5. **测试基础设施建设**（P1）：核心模块（规则引擎、DAO、ViewModel）最小测试覆盖
6. **大文件拆分**（P2）：ReadBookActivity（1717行）、ReadBook（991行）、TextChapterLayout（1271行）
7. **废弃API清理**（P2）：ProgressDialog 迁移、29处 notifyDataSetChanged→DiffUtil、JsEncodeUtils 15个@Deprecated 清理
8. **安全加固**（P2）：SSL 证书验证分级策略（书源请求保持宽松，用户数据传输严格验证）

### 不包含

- **UI/UX 重设计**：已在 android-ui-optimization spec 中完成
- **Jetpack Compose 迁移**：范围过大，独立规划
- **minSdk 提升**：当前 minSdk=21 覆盖 Android 5.0+，暂不调整
- **依赖版本大升级**：jsoup/rhino/hutool 已锁定，暂不可升级
- **WebDAV 同步协议重写**：功能层面无问题，不纳入
- **新功能开发**：本优化聚焦质量，不新增功能

## Approach

### Selected Approach

**分阶段渐进式治理**：按 P0→P1→P2 优先级分 3 批次实施，每批次完成后验证可运行性，确保核心阅读链路始终可用。

**核心策略**：
- **内存泄漏**：使用 WeakReference + Lifecycle 感知替换强引用，而非改变单例架构
- **线程安全**：统一使用 Mutex 替换 @Synchronized（协程友好），CopyOnWriteArrayList 替换粗粒度锁
- **数据库 ANR**：先标注所有主线程调用点，再逐步迁移至协程 IO
- **错误处理**：全局替换 + Lint 规则防止回退
- **测试**：先建基础设施（Room in-memory DB、MockWebServer），再逐步补充
- **大文件**：按职责边界拆分，保持公共 API 不变
- **废弃API**：按替换难度排序，逐个迁移
- **安全**：分级策略——书源请求保持宽松（业务刚需），用户账户/同步数据严格验证

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| **A1: 全量重写 ReadBook 单例为 ViewModel** | ReadBook 被 50+ 文件引用，全量重写风险过高；且 object 单例是项目架构约定，违反架构规范 |
| **A2: 全面迁移至 Jetpack Compose** | 范围过大（849个Kotlin文件），与质量优化目标偏离；Compose 迁移应独立规划 |
| **A3: 一步到位移除 allowMainThreadQueries()** | 影响范围不可控，需要先全面标注再逐步迁移，否则编译通过但运行时 ANR |
| **A4: 引入 DI 框架（Hilt/Koin）** | 项目约定手动 DI（object 单例），引入 DI 框架与架构规范冲突，且收益不明确 |
| **A5: 全面启用 SSL 证书验证** | 书源核心需求是抓取任意网站内容，大量 HTTPS 站点证书不合规，全面启用会导致大量书源不可用 |
| **A6: 大幅提升 minSdk 至 26+** | 当前 minSdk=21 覆盖更多用户；rhino 1.8.1 的 Arrays.setAll 问题仅在 API 23 以下出现，影响范围小 |

### Drawbacks

1. **Mutex 替换 @Synchronized 性能折中**：Mutex 是协程挂起锁，在非协程上下文中无法使用；部分代码需要调整调用链路为挂起函数，可能影响公共 API 签名
2. **WeakReference 运行时开销**：WeakReference 每次 get() 需判空，增加调用复杂度；若 GC 过早回收可能导致功能异常（如 ReadBook.callBack 被回收后阅读页不刷新）
3. **渐进式治理周期长**：8 个方向分 3 批次，预计需要多次迭代才能完成，期间可能产生新旧模式并存的过渡期
4. **测试覆盖建设成本高**：项目无测试文化，从零建立需要投入大量精力编写测试桩和 Mock
5. **SSL 分级策略复杂度**：需要维护两套 SSL 配置（书源宽松 + 用户数据严格），增加了网络层代码的分支逻辑

### Prior Art

- **Android 官方内存泄漏指南**：使用 WeakReference + Lifecycle 感知组件
- **Kotlin 协程最佳实践**：Mutex 优于 @Synchronized 用于协程代码
- **Room 官方建议**：禁止主线程查询，使用 Flow/LiveData 异步观察
- **LeakCanary**：可作为后续集成工具用于运行时泄漏检测

## Requirements

### P0 - 必须完成

| ID | 需求 | 验收标准 |
|----|------|---------|
| P0-1 | IntentData 内存泄漏修复 | put() 的对象在 Activity.onDestroy 时自动清理；无 StrongReference 持有 Activity |
| P0-2 | ReadBook.callBack 泄漏修复 | callBack 使用 WeakReference 持有，Activity 销毁后自动置空 |
| P0-3 | WebViewPool 泄漏修复 | release 时 WebView 正确 destroy；cleanup 定时器 destroy 失败时重试而非静默忽略 |
| P0-4 | ReadBook synchronized+Mutex 混用消除 | 统一为 Mutex，无 @Synchronized 残留 |
| P0-5 | RecyclerAdapter 锁优化 | 内部数据改用 CopyOnWriteArrayList，移除 18 个 @Synchronized |
| P0-6 | allowMainThreadQueries() 移除 | 数据库配置中删除此调用；所有主线程 DAO 调用迁移至协程 IO |
| P0-7 | Cronet TODO 崩溃修复 | 替换 TODO() 为合理实现或异常处理 |

### P1 - 应该完成

| ID | 需求 | 验收标准 |
|----|------|---------|
| P1-1 | printStackTrace 统一替换 | 29 处全部替换为 AppLog.put() 或 e.printOnDebug() |
| P1-2 | 空 catch 块注释补充 | HandleFileActivity:60 的静默 catch 添加原因注释 |
| P1-3 | 核心模块测试覆盖 | AnalyzeRule、AnalyzeUrl、AppDatabase DAO 至少 1 个单元测试 |
| P1-4 | MigrationTest 修复 | ALL_MIGRATIONS 数组填充完整迁移链 |
| P1-5 | LifecycleHelp ConcurrentModificationException 修复 | 遍历+remove 改用 Iterator.remove() 或 filterTo |

### P2 - 计划完成

| ID | 需求 | 验收标准 |
|----|------|---------|
| P2-1 | ReadBookActivity 拆分 | 从 1717 行拆分为≤500 行的多个文件，公共 API 不变 |
| P2-2 | ReadBook 拆分 | 从 991 行按职责拆分，核心单例保持 |
| P2-3 | ProgressDialog 迁移 | 替换为 MaterialAlertDialogBuilder + ProgressBar |
| P2-4 | DiffUtil 推广 | 高频列表（书架、搜索、目录）迁移至 DiffUtil/ListAdapter |
| P2-5 | SSL 分级策略 | 书源请求保持宽松，用户账户/WebDAV/更新检查使用严格验证 |
| P2-6 | JsEncodeUtils @Deprecated 清理 | 15 个废弃方法评估并移除或标记 @Removal |
| P2-7 | inner class 泄漏治理 | 31 处 Activity inner class 改为独立 class 或 WeakReference |

## Scenarios

### Scenario 1: 用户阅读时切换应用返回崩溃

**前置条件**：用户正在阅读书籍，ReadBook.callBack 持有 ReadBookActivity 引用

**当前行为**：用户切换到其他应用，系统回收 ReadBookActivity，但 ReadBook.callBack 仍强引用 Activity，导致内存泄漏；若系统尝试回收后用户返回，可能 NPE 崩溃

**期望行为**：ReadBook.callBack 使用 WeakReference，Activity 被回收后 callBack 自动置空；用户返回时 Activity 重建，重新注册 callBack

### Scenario 2: 多书源并发搜索时 ANR

**前置条件**：用户搜索关键词，16-32 个书源并发搜索

**当前行为**：搜索结果写入数据库时，部分 DAO 调用在主线程执行（allowMainThreadQueries），当书源返回数据量大时阻塞 UI → ANR

**期望行为**：所有 DAO 调用在 Dispatchers.IO 执行，UI 通过 Flow/LiveData 观察数据变化

### Scenario 3: WebView 池未清理导致 OOM

**前置条件**：用户频繁使用 JS 渲染书源（如带登录的源），WebViewPool 分配多个 WebView

**当前行为**：WebView destroy 可能静默失败（e.printStackTrace()），WebView 驻留池中，累积至 OOM

**期望行为**：destroy 失败时重试；定时清理强制释放；使用 MutableContextWrapper 替换 Context 后及时 detach

### Scenario 4: 书源搜索时 ReadBook 死锁

**前置条件**：用户在阅读页使用换源功能，ReadBook 同时执行 synchronized 和 Mutex 保护的代码

**当前行为**：协程持有 Mutex 等待 synchronized 块，或 synchronized 持有锁等待 Mutex → 线程池饥饿/死锁

**期望行为**：统一使用 Mutex，避免混用导致的死锁风险

### Scenario 5: 数据库升级后数据丢失

**前置条件**：用户从旧版本升级，数据库从版本 80 升级到 89

**当前行为**：MigrationTest 的 ALL_MIGRATIONS 为空数组，迁移链未经验证；若自动迁移定义有误，静默失败 → 数据丢失

**期望行为**：MigrationTest 覆盖完整迁移链，升级前 CI 验证通过
