# Tasks: Legado 核心质量优化

## Batch 1 — P0: 内存泄漏 + 线程安全 + 数据库 ANR + 崩溃修复

### 1. IntentData 内存泄漏修复
- [ ] 1.1 阅读 IntentData.kt 源码，理解 put/get/clear 机制
- [ ] 1.2 添加 `cleanup(activity: ComponentActivity)` 方法，在 Activity.onDestroy 时自动清理
- [ ] 1.3 修改 bigData 为 `MutableMap<String, WeakReference<Any>>` 或添加 TTL 自动清理
- [ ] 1.4 验证：grep 确认 cleanup 方法存在，阅读页启动/退出不崩溃

### 2. ReadBook.callBack 泄漏修复
- [ ] 2.1 阅读 ReadBook.kt 源码，理解 callBack 注册/注销流程
- [ ] 2.2 `var callBack: CallBack?` → `var callBack: WeakReference<CallBack>?`
- [ ] 2.3 所有 `callBack?.xxx()` → `callBack?.get()?.xxx()`
- [ ] 2.4 ReadBookActivity.onResume 重新注册 callBack
- [ ] 2.5 验证：阅读页正常显示，切换应用返回后阅读页刷新正常

### 3. WebViewPool 泄漏修复
- [ ] 3.1 阅读 WebViewPool.kt 源码，理解 acquire/release/cleanup 流程
- [ ] 3.2 destroy 失败时加入重试队列（最多 3 次），替换 e.printStackTrace()
- [ ] 3.3 确保 MutableContextWrapper 在 release 时 detach
- [ ] 3.4 验证：grep �认 printStackTrace 替换，重试逻辑存在

### 4. ReadBook 锁策略统一
- [ ] 4.1 标注 ReadBook.kt 中所有 synchronized(this) 和 @Synchronized
- [ ] 4.2 添加统一的 Mutex 实例
- [ ] 4.3 synchronized(this) {} → mutex.withLock {}
- [ ] 4.4 @Synchronized 方法 → 挂起函数 + mutex.withLock
- [ ] 4.5 修改所有调用点适配新的挂起函数签名
- [ ] 4.6 验证：grep 确认 ReadBook.kt 无 @Synchronized 和 synchronized 残留

### 5. RecyclerAdapter 锁优化
- [ ] 5.1 阅读 RecyclerAdapter.kt 源码，理解 18 个 @Synchronized 方法
- [ ] 5.2 内部 `ArrayList<Item>` → `CopyOnWriteArrayList<Item>`
- [ ] 5.3 移除所有 @Synchronized 注解
- [ ] 5.4 验证：grep 确认 RecyclerAdapter.kt 无 @Synchronized 残留

### 6. WebViewPool 协程+锁修复
- [ ] 6.1 协程内 synchronized(this@WebViewPool) → Mutex.withLock
- [ ] 6.2 needInitialize 字段添加 @Volatile
- [ ] 6.3 验证：grep 确认 WebViewPool.kt 无 synchronized 残留

### 7. Cronet TODO 崩溃修复
- [ ] 7.1 阅读 CronetCoroutineInterceptor.kt 第 85 行
- [ ] 7.2 TODO() → 实现 or throw UnsupportedOperationException("Cronet interceptor not yet implemented for this case")
- [ ] 7.3 验证：grep 确认无 TODO("Not yet implemented") 残留

### 8. 数据库主线程查询消除（阶段 1：标注）
- [ ] 8.1 搜索所有 DAO 调用点（grep AppDatabase、各 DAO 方法名）
- [ ] 8.2 标注在主线程调用的 DAO 方法
- [ ] 8.3 创建迁移清单文件

### 9. 数据库主线程查询消除（阶段 2：高频迁移）
- [ ] 9.1 迁移搜索相关 DAO 调用（SearchViewModel 等）
- [ ] 9.2 迁移缓存相关 DAO 调用（CacheBook 等）
- [ ] 9.3 迁移书架相关 DAO 调用（BookshelfFragment 等）
- [ ] 9.4 验证：高频场景（搜索、缓存、书架）无主线程 DAO 调用

### 10. 数据库主线程查询消除（阶段 3：移除配置）
- [ ] 10.1 AppDatabase.kt 移除 allowMainThreadQueries()
- [ ] 10.2 编译检查，修复所有编译错误
- [ ] 10.3 运行应用验证核心功能
- [ ] 10.4 验证：grep 确认 allowMainThreadQueries 已移除

### 11. Batch 1 集成验证
- [ ] 11.1 执行 Gradle 构建 `./gradlew assembleAppDebug`
- [ ] 11.2 安装 APK 到设备/模拟器
- [ ] 11.3 核心链路冒烟测试：启动→书架→搜索→阅读→返回
- [ ] 11.4 标记 Batch 1 完成

---

## Batch 2 — P1: 错误处理规范化 + 测试基础设施

### 12. printStackTrace 统一替换
- [ ] 12.1 搜索所有 e.printStackTrace() 调用（约 29 处）
- [ ] 12.2 逐个替换为 `AppLog.put("Tag", e)` 或 `e.printOnDebug()`
- [ ] 12.3 验证：grep 确认无 e.printStackTrace() 残留

### 13. 空 catch 块注释补充
- [ ] 13.1 HandleFileActivity.kt:60 空 catch 添加注释说明原因
- [ ] 13.2 验证：Read 确认注释存在

### 14. LifecycleHelp ConcurrentModificationException 修复
- [ ] 14.1 阅读 LifecycleHelp.kt 第 74 行遍历中 remove
- [ ] 14.2 改用 `iter.filterNotTo()` 或 `entries.removeIf()`
- [ ] 14.3 验证：Read 确认修复正确

### 15. 核心模块测试覆盖
- [ ] 15.1 创建 AnalyzeRuleTest.kt（规则引擎核心测试）
- [ ] 15.2 创建 AnalyzeUrlTest.kt（URL 解析测试）
- [ ] 15.3 创建 DaoTest.kt（Room in-memory DB 核心 DAO 测试）
- [ ] 15.4 验证：`./gradlew test` 通过

### 16. MigrationTest 修复
- [ ] 16.1 阅读 DatabaseMigrations.kt，提取完整迁移链
- [ ] 16.2 填充 ALL_MIGRATIONS 数组
- [ ] 16.3 验证：MigrationTest 可运行

### 17. Batch 2 集成验证
- [ ] 17.1 执行 `./gradlew assembleAppDebug`
- [ ] 17.2 执行 `./gradlew test`
- [ ] 17.3 grep 确认无 printStackTrace 残留
- [ ] 17.4 标记 Batch 2 完成

---

## Batch 3 — P2: 大文件拆分 + 废弃API + 安全加固

### 18. ReadBookActivity 拆分
- [ ] 18.1 分析 ReadBookActivity.kt 职责边界
- [ ] 18.2 提取 ReadBookMenuDelegate（菜单逻辑）
- [ ] 18.3 提取 ReadBookKeyHandler（按键处理）
- [ ] 18.4 提取 ReadBookBroadcastHandler（广播注册/处理）
- [ ] 18.5 验证：各文件 ≤500 行，阅读页功能不变

### 19. ReadBook 拆分
- [ ] 19.1 分析 ReadBook.kt 职责边界
- [ ] 19.2 提取 ReadBookLoader（加载逻辑）
- [ ] 19.3 提取 ReadBookState（状态管理）
- [ ] 19.4 验证：核心单例 object 保持，各文件 ≤500 行

### 20. TextChapterLayout 拆分
- [ ] 20.1 分析 TextChapterLayout.kt 职责边界
- [ ] 20.2 提取 TextChapterMeasure（测量逻辑）
- [ ] 20.3 提取 TextChapterDraw（绘制逻辑）
- [ ] 20.4 验证：各文件 ≤500 行，排版功能不变

### 21. ProgressDialog 迁移
- [ ] 21.1 阅读 AndroidDialogs.kt，理解 18 处 ProgressDialog 使用
- [ ] 21.2 替换为 MaterialAlertDialogBuilder + ProgressBar
- [ ] 21.3 验证：grep 确认无 ProgressDialog 残留

### 22. DiffUtil 推广
- [ ] 22.1 书架 Adapter 迁移至 DiffUtil
- [ ] 22.2 搜索 Adapter 迁移至 DiffUtil
- [ ] 22.3 目录 Adapter 迁移至 DiffUtil
- [ ] 22.4 验证：列表滚动流畅，无 notifyDataSetChanged

### 23. SSL 分级策略
- [ ] 23.1 在 SSLHelper.kt 添加 `createStrictOkHttpClient()`
- [ ] 23.2 用户账户/WebDAV/更新检查使用严格 SSL Client
- [ ] 23.3 书源请求保持宽松 SSL Client（不变）
- [ ] 23.4 验证：grep 确认严格 Client 用于用户数据请求

### 24. JsEncodeUtils @Deprecated 清理
- [ ] 24.1 评估 15 个 @Deprecated 方法的使用情况
- [ ] 24.2 无引用的方法直接移除
- [ ] 24.3 有引用的方法标记 `@Removal(version = "3.27")` 并添加替代方案注释
- [ ] 24.4 验证：编译通过

### 25. inner class 泄漏治理
- [ ] 25.1 搜索 31 处 Activity inner class
- [ ] 25.2 逐个评估并改为独立 class 或 WeakReference
- [ ] 25.3 验证：grep 确认 Activity 内无直接 inner class 持有 Context

### 26. Batch 3 集成验证
- [ ] 26.1 执行 `./gradlew assembleAppDebug`
- [ ] 26.2 核心链路回归测试
- [ ] 26.3 标记 Batch 3 完成

---

## 27. 文档同步
- [ ] 27.1 更新 docs/INDEX.md
- [ ] 27.2 更新 docs/specs/INDEX.md
- [ ] 27.3 更新 docs/project-flow/ 相关文档
- [ ] 27.4 更新 app/src/main/assets/updateLog.md

---

## AOAdapt 日志

（实施过程中遇到问题时记录）
