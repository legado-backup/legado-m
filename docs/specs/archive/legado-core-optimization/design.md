# Design: Legado 核心质量优化

## Technical Approach

### 整体策略

采用 **3 批次渐进式治理**，每批次独立验证：

```
Batch 1 (P0): 内存泄漏 + 线程安全 + 数据库 ANR + 崩溃修复
    ↓ 验证：APK 构建 + 核心阅读链路可用
Batch 2 (P1): 错误处理规范化 + 测试基础设施建设
    ↓ 验证：单元测试通过 + 无 printStackTrace 残留
Batch 3 (P2): 大文件拆分 + 废弃API清理 + 安全加固
    ↓ 验证：APK 构建 + 功能回归测试
```

### 关键技术决策

1. **内存泄漏修复**：不改单例架构，改引用类型
   - IntentData：添加 `cleanup(activity)` 方法，Activity.onDestroy 时调用
   - ReadBook.callBack：`var callBack: CallBack?` → `var callBack: WeakReference<CallBack>?`
   - WebViewPool：destroy 失败时加入重试队列，最多重试 3 次

2. **线程安全统一**：Mutex 替换 @Synchronized
   - ReadBook：4 个 @Synchronized 方法 → 挂起函数 + Mutex
   - RecyclerAdapter：`ArrayList<Item>` → `CopyOnWriteArrayList<Item>`，移除所有 @Synchronized
   - WebViewPool：协程内 synchronized → Mutex

3. **数据库 ANR 消除**：渐进式迁移
   - 阶段 1：标注所有主线程 DAO 调用点（约 200+ 处）
   - 阶段 2：高频调用点（搜索、缓存）优先迁移至 `withContext(Dispatchers.IO)`
   - 阶段 3：移除 allowMainThreadQueries()，编译期强制

4. **测试基础设施**：Room in-memory + MockWebServer
   - AppDatabase 测试：使用 Room.inMemoryDatabaseBuilder
   - 网络层测试：使用 okhttp3.mockwebserver.MockWebServer
   - 规则引擎测试：直接实例化 AnalyzeRule（无 Android 依赖）

---

## Architecture Decisions

### AD-01: ReadBook.callBack 引用策略

- **Context**: ReadBook 是 object 单例，callBack 持有 Activity 引用，Activity 销毁时若未手动清理则泄漏
- **Concern**: 全局单例持有 Activity 强引用导致内存泄漏
- **Decision**: 使用 WeakReference<CallBack> 替换 CallBack?，get() 为 null 时视为未注册
- **Goal**: Activity 销毁后 callBack 自动置空，无需手动清理
- **Tradeoff**: GC 可能过早回收 callBack，导致阅读页刷新短暂中断；需要在 Activity.onResume 时重新注册
- **Status**: Proposed

### AD-02: ReadBook 锁策略统一

- **Context**: ReadBook 同时使用 synchronized(this) 和 Mutex，混用有死锁风险
- **Concern**: synchronized 阻塞线程，Mutex 挂起协程，两者不可互换
- **Decision**: 统一使用 kotlinx.coroutines.sync.Mutex，所有 synchronized 块改为 mutex.withLock {}
- **Goal**: 消除死锁风险，与协程模型一致
- **Tradeoff**: synchronized 块内的代码需要变为挂起函数，影响调用链；部分在非协程上下文的调用需要包装为 Coroutine.async
- **Status**: Proposed

### AD-03: RecyclerAdapter 并发策略

- **Context**: RecyclerAdapter 有 18 个 @Synchronized 方法，粗粒度锁在高频场景下锁竞争严重
- **Concern**: notifyDataSetChanged、getItem 等高频方法的锁竞争影响列表滚动性能
- **Decision**: 内部数据从 ArrayList 改为 CopyOnWriteArrayList，移除所有 @Synchronized
- **Goal**: 读操作无锁，写操作复制开销可接受（列表规模通常 <1000）
- **Tradeoff**: 写操作时复制整个数组，大数据量时内存开销增加；但列表数据量通常较小（<1000），CopyOnWrite 策略适用
- **Status**: Proposed

### AD-04: 数据库主线程查询消除策略

- **Context**: AppDatabase 配置了 allowMainThreadQueries()，允许主线程执行 DAO 查询，可能导致 ANR
- **Concern**: 一步到位移除会导致大量运行时崩溃，需要渐进式迁移
- **Decision**: 三阶段渐进——① 标注 → ② 高频迁移 → ③ 移除配置
- **Goal**: 消除 ANR 根因，同时保证渐进式迁移不破坏功能
- **Tradeoff**: 过渡期新旧模式并存，代码风格不一致；迁移周期长
- **Status**: Proposed

### AD-05: SSL 证书验证分级策略

- **Context**: 当前全局禁用 SSL 证书验证，存在中间人攻击风险
- **Concern**: 书源抓取需要宽松验证（大量自签名证书网站），但用户数据传输需要严格验证
- **Decision**: 按请求类型分级——书源请求使用宽松 SSL（维持现状），用户账户/WebDAV/更新检查使用系统默认严格验证
- **Goal**: 保护用户敏感数据传输安全，同时不影响书源核心功能
- **Tradeoff**: 需要在 OkHttp Client 配置层区分请求类型，增加网络层代码分支逻辑
- **Status**: Proposed

### AD-06: 测试基础设施选型

- **Context**: 项目测试覆盖率近乎为零，需要建立最小测试基础
- **Concern**: 核心模块（规则引擎、DAO）无测试保障，重构风险极高
- **Decision**: 使用 Room in-memory DB（DAO 测试）+ MockWebServer（网络测试）+ 纯 JVM 单元测试（规则引擎）
- **Goal**: 核心模块具备最小可运行测试，为后续重构提供安全网
- **Tradeoff**: 仅覆盖核心模块，覆盖率仍较低；但建立基础设施后可逐步补充
- **Status**: Proposed

### AD-07: 大文件拆分策略

- **Context**: ReadBookActivity（1717行）、ReadBook（991行）、TextChapterLayout（1271行）过于庞大
- **Concern**: 单文件职责过多，维护困难，变更风险高
- **Decision**: 按职责边界拆分——ReadBookActivity 拆为 ReadBookMenuDelegate + ReadBookKeyHandler + ReadBookBroadcastHandler 等；ReadBook 拆为 ReadBookLoader + ReadBookState 等
- **Goal**: 单文件 ≤500 行，职责单一，降低维护成本
- **Tradeoff**: 拆分后类间通信增加（通过接口/delegate）；公共 API 不变，内部结构变化
- **Status**: Proposed

---

## Data Flow

### 内存泄漏修复数据流

```
Before:
  Activity → (strong ref) → ReadBook.callBack → (strong ref) → Activity
  ↑ 泄漏：Activity 无法被 GC 回收

After:
  Activity → (strong ref) → ReadBook.callBack → (WeakReference) → Activity
  ↑ 安全：Activity 被 GC 回收后，WeakReference.get() = null
  ↑ 恢复：Activity.onResume() → ReadBook.callBack = WeakReference(this)
```

### 数据库查询迁移数据流

```
Before:
  UI (Main Thread) → DAO.query() → Room (allowMainThreadQueries) → SQLite
  ↑ 阻塞主线程，可能 ANR

After:
  UI → viewModelScope.launch { withContext(IO) { DAO.query() } → Room → SQLite }
  ↑ IO 线程执行，Main 线程观察 Flow/LiveData
```

### 线程安全统一数据流

```
Before (ReadBook):
  Coroutine A: mutex.withLock { ... } ←→ synchronized(this) { ... }
  ↑ 混用：Mutex 挂起 + synchronized 阻塞 = 死锁风险

After (ReadBook):
  Coroutine A: mutex.withLock { ... }
  Coroutine B: mutex.withLock { ... }
  ↑ 统一：协程友好的互斥锁，无死锁风险
```

---

## File Changes

### Batch 1 (P0) 核心变更

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `model/ReadBook.kt` | 修改 | callBack 改为 WeakReference；4 处 @Synchronized → Mutex；synchronized(this) → mutex.withLock |
| `help/IntentData.kt` | 修改 | 添加 cleanup() 方法 + Lifecycle 感知自动清理 |
| `help/webView/WebViewPool.kt` | 修改 | destroy 失败重试机制；协程内 synchronized → Mutex |
| `base/adapter/RecyclerAdapter.kt` | 修改 | ArrayList → CopyOnWriteArrayList；移除 18 个 @Synchronized |
| `data/AppDatabase.kt` | 修改 | 移除 allowMainThreadQueries() |
| `lib/cronet/CronetCoroutineInterceptor.kt` | 修改 | TODO() → 实现 or throw UnsupportedOperationException |
| **50+ DAO 调用文件** | 修改 | 主线程 DAO 调用迁移至 withContext(Dispatchers.IO) |

### Batch 2 (P1) 变更

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| 21 个含 printStackTrace 的文件 | 修改 | e.printStackTrace() → AppLog.put() |
| `ui/file/HandleFileActivity.kt` | 修改 | 空 catch 块添加注释 |
| `help/LifecycleHelp.kt` | 修改 | 遍历中 remove → Iterator.remove() |
| `src/test/java/io/legado/app/AnalyzeRuleTest.kt` | 新增 | AnalyzeRule 单元测试 |
| `src/test/java/io/legado/app/AnalyzeUrlTest.kt` | 新增 | AnalyzeUrl 单元测试 |
| `src/androidTest/.../MigrationTest.kt` | 修改 | ALL_MIGRATIONS 填充完整迁移链 |
| `src/androidTest/.../DaoTest.kt` | 新增 | 核心 DAO 单元测试 |

### Batch 3 (P2) 变更

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `ui/book/read/ReadBookActivity.kt` | 拆分 | → ReadBookMenuDelegate + ReadBookKeyHandler + ReadBookBroadcastHandler |
| `model/ReadBook.kt` | 拆分 | → ReadBookLoader + ReadBookState（object 保持） |
| `ui/book/read/page/provider/TextChapterLayout.kt` | 拆分 | → TextChapterMeasure + TextChapterDraw |
| `lib/dialogs/AndroidDialogs.kt` | 修改 | ProgressDialog → MaterialAlertDialogBuilder + ProgressBar |
| 19 个 Adapter 文件 | 修改 | notifyDataSetChanged → DiffUtil/ListAdapter |
| `help/http/SSLHelper.kt` | 修改 | 添加严格 SSL Factory 用于用户数据请求 |
| `help/JsEncodeUtils.kt` | 修改 | 15 个 @Deprecated 方法清理 |
| 31 个 Activity 文件 | 修改 | inner class → 独立 class 或 WeakReference |
