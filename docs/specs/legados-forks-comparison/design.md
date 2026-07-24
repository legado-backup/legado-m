# legados Forks 对比与集成设计文档

## 技术方案

采用"复制-适配-验证"三步法策略处理每个集成候选功能：

1. **复制**：将 fork 的实现文件直接复制到本项目对应的包路径下
2. **适配**：修改包引用、修正代码风格差异（本项目使用 `kotlin.runCatching`、`AppLog.put()`、Coroutine 链式封装），更新 import 声明
3. **验证**：构建、运行、真机测试，确保无回归

---

## 现有接口缺口分析（经源码验证）

> 以下缺口是集成前必须解决的前置条件，已在设计阶段识别并纳入任务清单。

| 缺口 | 当前状态 | 需要的操作 | 影响的集成项 |
|------|---------|-----------|-------------|
| PaintPool 无 clear() 方法 | ObjectPool 接口只有 obtain/recycle/create（无清理方法），PaintPool 继承 BaseSafeObjectPool<Paint>(8) | 在 PaintPool 中新增 `fun clear()` 方法，回收所有对象并清空池 | MemoryPressure #2 |
| CacheManager 无通用 clear() | AppCacheManager 只有 clearSourceVariables()（清除特定 key），memoryLruCache 是 LruCache(50MB) | 调用 `memoryLruCache.evictAll()` 即可实现全量清除，无需新增方法 | MemoryPressure #2 |
| AppConfig 无 mdLinkInnerBrowser/urlRecordEnabled | AppConfig 用 SharedPreferences 存储，实现 OnSharedPreferenceChangeListener | 在 AppConfig 中新增两个 Boolean 字段，存储方式同现有字段（SharedPreferences），默认值 mdLinkInnerBrowser=true，urlRecordEnabled=false | InnerBrowserLink #3、UrlRecordInterceptor #8 |
| strings.xml 无 book_cache | 本项目 strings.xml 缺少 R.string.book_cache 条目 | 在 strings.xml 中新增 `<string name="book_cache">书籍缓存</string>` | BackupConfig #10 |
| Restore.kt 无验证入口 | Restore.kt 直接执行恢复，无前置验证步骤 | 在恢复流程中调用 BackupFileValidator.validate()，验证失败时弹出 AlertDialog | BackupFileValidator #4 |
| ContentProcessor 无内容保护步骤 | ContentProcessor.kt 有处理管线但无 HTML 标签保护 | 在处理管线中增加 SpecialContentProtector 步骤 | SpecialContentProtector #7 |

---

## P0 功能技术方案（7项，经源码验证 + 产品/架构/测试审查）

### 1. HelpDoc + HelpDocManager（136行）

- **目标包路径**：`help/`
- **源码验证**：HelpDoc 是 data class（fileName, displayName），HelpDocManager 是 object（allHelpDocs 列表含24个文档、hiddenHelpDocs 含7个隐藏文档、loadDoc 从 assets/web/help/md/ 读取）
- **UI 入口**：在 AboutActivity 添加"帮助文档"按钮 → 打开 HelpDocActivity（新建），左侧文档列表 + 右侧 Markdown 渲染
- **适配要点**：
  - `HelpDocManager.loadDoc()` 使用 `AssetManager.open("web/help/md/${fileName}.md")` → 适配为本项目的 assets 目录结构（assets/help/）
  - fork 的文档列表含24个条目（书源制作教程、JS帮助等）→ 需评估本项目是否需要全部文档，部分可能需要新增本项目特有的内容（高亮系统、RSS增强等）
  - UI 样式需匹配本项目主题
- **依赖**：无外部依赖，纯 Kotlin + Android SDK + Markwon（本项目已有）

### 2. MemoryPressure（90行）

- **目标包路径**：`help/`
- **源码验证**：object 单例，包含 `maxMemory`/`availableMemory`/`isSmallHeap` 属性，`trimLevelForCurrentState`/`trimIfNeeded`/`trimNow` 方法，基于 `ComponentCallbacks2.onTrimMemory` 回调
- **UI 入口**：无 UI 入口（后台自动运行），日志可在 DebugFloatBallManager 查看
- **适配要点**：
  - 在 `App.kt`（Application 类）中注册 `MemoryPressure` 的 `ComponentCallbacks2` 回调
  - CacheManager 释放：调用 `memoryLruCache.evictAll()`（LruCache 内置方法，50MB 全清）
  - PaintPool 释放：**需先为 PaintPool 新增 `clear()` 方法**（当前 ObjectPool 接口无清理方法）
  - 通过 `AppLog.put()` 记录释放动作
- **前置条件**：PaintPool 新增 clear() 方法
- **依赖**：CacheManager、PaintPool（需扩展）、App.kt、AppLog

### 3. InnerBrowserUrlSpan + InnerBrowserLinkResolver（48行）

- **目标包路径**：`help/`
- **源码验证**：InnerBrowserUrlSpan 是 ClickableSpan 子类（24行），检查 `AppConfig.mdLinkInnerBrowser`；InnerBrowserLinkResolver 是 Markwon 链接解析器（24行）
- **UI 入口**：SettingsActivity → 阅读设置 → "Markdown 链接使用内置浏览器"开关
- **内部链接判定规则**：
  1. URL host 与当前书源 bookSourceUrl host 相同 → 内部
  2. URL 以 http/https 开头且属已知书源域名 → 内部
  3. URL 以 file:/// 或 content:// 开头（本地资源）→ 内部
  4. 以上不满足 → 外部（系统浏览器）
- **适配要点**：
  - **AppConfig 新增 `mdLinkInnerBrowser` 字段**（SharedPreferences Boolean，默认 true）
  - 内部链接判断逻辑需获取当前书源的 bookSourceUrl host
  - 集成到本项目的 WebView 池系统
- **前置条件**：AppConfig 新增 mdLinkInnerBrowser 字段
- **依赖**：AppConfig、Markwon（本项目已有）、WebView 池

### 4. BackupFileValidator（597行）

- **目标包路径**：`help/storage/`
- **源码验证**：验证 JSON/XML 格式正确性，检查必需字段（bookSources, rssSources, replaceRules 等），处理加密服务器配置文件（BackupAES 解密验证），支持增量备份验证
- **UI 入口**：RestoreActivity 恢复流程中自动触发；验证失败弹出 AlertDialog
  - 成功：正常进入恢复流程
  - 失败：AlertDialog 标题"备份文件验证失败"，内容说明原因，按钮 [取消恢复] [查看详情]
- **适配要点**：
  - 需与本项目 `Restore.kt` 流程集成，在恢复前调用 `BackupFileValidator.validate()`
  - 本项目 BackupAES.kt 是扩展类而非独立类 → 需适配解密调用方式
  - 本项目 BackupConfig.kt 只有147行（fork 221行）→ 必需字段列表需适配本项目版本（详见 BackupConfig 字段差异清单）
  - 验证失败 UI 用 AlertDialog 与本项目风格统一
- **前置条件**：需确认 BackupConfig 必需字段列表与本项目版本一致
- **依赖**：Restore.kt、BackupAES.kt、BackupConfig.kt

### 5. BackupInfoHelper（324行）

- **目标包路径**：`help/storage/`
- **源码验证**：统计当前会备份的数据，不需要解析 ZIP，提供备份概况和分类信息
- **UI 入口**：BackupActivity 备份前展示信息卡片
- **适配要点**：
  - 分类信息需适配本项目数据模型（Highlight、CoverGallery、RssEpisode 等本项目独有实体）
  - UI 展示需与本项目风格统一
- **依赖**：Backup.kt、各 DAO

### 6. StorageCalculator（782行）

- **目标包路径**：`help/storage/`
- **源码验证**：计算 6 种缓存大小，提供 CacheDetail 列表和清理操作
- **UI 入口**：SettingsActivity → 其他设置 → "存储管理" → 打开 StorageManageActivity（新建）
- **适配要点**：
  - 缓存路径需适配本项目存储结构
  - 清理操作需调用本项目对应的清理方法（BookHelp.clearCache()、ExoPlayerHelper.clearCache() 等）
  - 新建 StorageManageActivity UI 页面
- **依赖**：各缓存清理接口

### 7. SpecialContentProtector（41行）

- **目标包路径**：`help/book/`
- **源码验证**：用正则替换 HTML 标签（`<newpage>` 等）和特殊标记为占位符
- **UI 入口**：无 UI 入口（后台自动运行，集成到 ContentProcessor 处理管线）
- **适配要点**：
  - 集成到本项目 `ContentProcessor.kt` 处理管线中，在 HTML 解析前执行保护
  - 正则规则需适配本项目的特殊标记格式
- **依赖**：ContentProcessor.kt

---

## P1 功能技术方案（5项）

### 8. UrlRecordInterceptor（201行，从P0降级）

- **目标包路径**：`help/http/`
- **源码验证**：OkHttp Interceptor，记录请求 URL/域名/HTTP 方法/响应状态/耗时，异步写数据库，支持 POST body
- **UI 入口**：SettingsActivity → 开发者选项 → "URL 记录"开关（AppConfig.urlRecordEnabled，默认 false）
- **降级原因**：主要服务高级用户/源开发者，普通用户无感知价值；需评估性能开销
- **适配要点**：
  - fork 版本写数据库 → 简化为仅用 AppLog.put() 记录（不新增 Room entity）
  - AppConfig 新增 urlRecordEnabled 字段（SharedPreferences Boolean，默认 false）
  - 在 HttpHelper OkHttpClient 构建时条件性添加此拦截器（类似 Cronet 添加方式）
  - 需测试性能影响：每个请求额外记录是否有延迟
- **前置条件**：AppConfig 新增 urlRecordEnabled 字段
- **依赖**：HttpHelper、AppConfig、AppLog

### 9. CoverHtmlTemplateConfig（189行）

- **目标包路径**：`help/config/`
- **UI 入口**：SettingsActivity → 封面设置 → "模板管理"
- **适配要点**：需与 BookCover 集成，模板格式适配本项目
- **依赖**：BookCover

### 10. BackupConfig 差异合并

- **字段差异**：详见 spec.md "BackupConfig 字段差异清单"章节
- **UI 入口**：备份恢复设置 → "书籍缓存备份"开关
- **适配要点**：新增 bookCacheKey + ignoreBookCache 属性 + R.string.book_cache
- **依赖**：Backup.kt、Restore.kt

### 11. BubblePackageManager（287行）

- **目标包路径**：`help/config/`
- **UI 入口**：段评设置 → "气泡包管理"
- **适配要点**：需理解段评机制，可能需段评 UI 支持
- **依赖**：段评 UI 模块

### 12. AudioPlay.kt 差异合并（高风险）

- **源码验证**：fork 635行 vs 本项目 488行，差异147行
- **UI 入口**：无新入口
- **适配要点**：逐行对比差异，选择性合并歌词回调等新增逻辑
- **依赖**：AudioPlayService.kt、AudioPlayActivity.kt

---

## 架构决策

### AD-01: 集成策略选择

- **Context**: legados fork 有多个可借鉴功能，需确定集成方式
- **Concern**: 全量移植维护成本高，选择性移植可能遗漏依赖链；仅凭文件名推断会导致误判
- **Decision**: 采用分层集成策略（P0 7项/P1 5项/P2 6项），每层基于源码深度阅读后的真实价值评估；经产品/架构/测试三维度审查后，UrlRecordInterceptor 从 P0 降至 P1
- **Goal**: 确保高价值用户可见功能优先集成，开发者工具类功能降级为 P1
- **Tradeoff**: UrlRecordInterceptor 降级意味着调试功能延迟提供；P2 功能暂不集成但可能未来有价值
- **Status**: Proposed

### AD-02: 代码移植方式

- **Context**: fork 的代码风格与本项目有差异
- **Concern**: 直接复制可能引入不一致代码
- **Decision**: Copy-Adapt-Verify 三步法
- **Goal**: 确保移植代码与本项目风格一致
- **Tradeoff**: 适配过程可能引入细微差异，需逐文件检查；大文件（StorageCalculator 782行）适配工作量较大
- **Status**: Proposed

### AD-03: 外部依赖处理

- **Context**: fork 引入了 liquidglass 等第三方库；InnerBrowserLinkResolver 需要 Markwon
- **Concern**: 新依赖增加 APK 体积
- **Decision**: 仅集成纯 Kotlin 实现的功能，不引入新的第三方库依赖；Markwon 已在本项目依赖中（build.gradle 已有 markwon.core/image.glide/ext.tables/html），不违反此决策
- **Goal**: 保持 APK 体积和依赖链简洁
- **Tradeoff**: liquidglass 等视觉效果功能无法集成
- **Status**: Proposed

### AD-04: BackupFileValidator 适配策略

- **Context**: BackupFileValidator(597行) 依赖 fork 的 BackupConfig(221行) 和 BackupAES
- **Concern**: 本项目的 BackupConfig(147行) 字段较少（缺 bookCacheKey），BackupAES 实现方式不同
- **Decision**: 先移植 BackupFileValidator 核心验证逻辑，必需字段列表适配本项目 BackupConfig 版本（缺 bookCacheKey 不影响核心验证逻辑，bookCache 是可选字段）；验证失败 UI 用 AlertDialog 提供具体原因和操作按钮
- **Goal**: 获得备份验证功能但不破坏本项目现有备份流程
- **Tradeoff**: 验证覆盖度可能低于 fork 版本（因本项目配置项较少）
- **Status**: Proposed

### AD-05: AudioPlay.kt 差异合并策略

- **Context**: fork AudioPlay.kt(635行) vs 本项目(488行)，差异147行含歌词回调等新功能
- **Concern**: 核心模块差异大，整体替换风险极高
- **Decision**: 仅选择性合并有价值的新增方法（如歌词回调接口），不整体替换 AudioPlay.kt
- **Goal**: 获得 fork 新增的有价值功能但不破坏本项目已有的音频播放逻辑
- **Tradeoff**: 合并后代码可能比两个版本都更复杂
- **Status**: Proposed

### AD-06: PaintPool clear() 方法新增

- **Context**: MemoryPressure 需要 PaintPool.clear() 方法，但当前 ObjectPool 接口只有 obtain/recycle/create
- **Concern**: 扩展接口会影响所有 ObjectPool 实现
- **Decision**: 仅在 PaintPool（而非 ObjectPool 接口）中新增 clear() 方法，回收所有对象并清空池；不影响 BaseSafeObjectPool 和其他 ObjectPool 实现
- **Goal**: 满足 MemoryPressure 释放需求但不扩大接口影响范围
- **Tradeoff**: 如未来其他 ObjectPool 也需要 clear()，则需提升到接口层
- **Status**: Proposed

### AD-07: AppConfig 新字段存储方式

- **Context**: 需新增 mdLinkInnerBrowser 和 urlRecordEnabled 两个 Boolean 字段
- **Concern**: 存储方式需与本项目风格一致
- **Decision**: 使用 SharedPreferences 存储（与 AppConfig 其他字段一致），mdLinkInnerBrowser 默认 true，urlRecordEnabled 默认 false
- **Goal**: 与现有 AppConfig 架构保持一致
- **Tradeoff**: SharedPreferences 重启后生效，不适合运行时动态切换（但这两个字段本身就是设置型配置，不需要动态切换）
- **Status**: Proposed

---

## 数据流

### 1. HelpDoc 数据流

用户点击 AboutActivity "帮助文档"按钮 → 打开 HelpDocActivity → HelpDocManager.allHelpDocs 列表展示左侧面板 → 用户点击某文档 → HelpDocManager.loadDoc(assets, fileName) 从 assets/help/ 加载 → Markwon 渲染 Markdown 到右侧面板 → 用户阅读内容

### 2. MemoryPressure 数据流

App.kt onCreate 注册 MemoryPressure.registerCallback() → 系统触发 onTrimMemory(level) → MemoryPressure.trimLevelForCurrentState 评估级别 → level ≥ 10(RUNNING_LOW)：调用 memoryLruCache.evictAll()（50MB 全清） + PaintPool.clear()（8对象回收）→ AppLog.put("MemoryPressure: level=X, released CacheManager+PaintPool") → 应用继续运行不崩溃

### 3. InnerBrowserLink 内部跳转数据流

用户点击阅读内容中的链接 → InnerBrowserUrlSpan.onClick() → 检查 AppConfig.mdLinkInnerBrowser（默认 true）→ 获取当前书源 bookSourceUrl 的 host → 对比链接 URL host → host 相同 → 启动 WebView Activity 在应用内打开 → 用户阅读完成后按返回键回到阅读页

### 4. InnerBrowserLink 外部跳转数据流

链接 host 与书源 host 不匹配 → InnerBrowserUrlSpan.onClick() → 检查 AppConfig.mdLinkInnerBrowser → true 但判定为外部链接 → Intent.ACTION_VIEW 启动系统浏览器

### 5. BackupFileValidator 验证数据流

用户在 RestoreActivity 选择备份文件 → Restore.kt 在恢复前调用 BackupFileValidator.validate(filePath) → 验证 JSON/XML 格式 → 检查必需字段 → 如有加密配置用 BackupAES 解密验证 → 返回 ValidationResult → 成功：继续恢复流程 → 失败：弹出 AlertDialog（原因 + [取消恢复] [查看详情] 按钮）

### 6. BackupInfoHelper 展示数据流

用户进入 BackupActivity → BackupInfoHelper.getBackupOverview() 统计数据 → 生成信息卡片（书源数/订阅源数/替换规则数等）→ UI 展示在备份按钮上方 → 用户确认后执行备份

### 7. StorageCalculator 数据流

用户进入 SettingsActivity → 其他设置 → "存储管理" → 打开 StorageManageActivity → StorageCalculator.calculateAll() 计算各缓存大小 → 生成 CacheDetail 列表 → UI 展示详情列表 → 用户点击清理 → StorageCalculator.clean(type) 调用对应清理方法 → 刷新列表

### 8. SpecialContentProtector 数据流

ContentProcessor 处理管线 → 在 HTML 解析前调用 SpecialContentProtector.protect(content) → 正则替换特殊标记为占位符 → 正常 HTML 解析 → 解析完成后 SpecialContentProtector.restore(content) 还原占位符为原始标记

---

## 测试计划

### MemoryPressure 测试

| 测试方法 | 步骤 | 验证点 |
|---------|------|--------|
| Android Studio Profiler | 1. 安装应用 2. 打开 Profiler Memory 3. 打开多本书触发大缓存 4. 点击 Profiler "Force GC" 5. 检查 AppLog 是否有 MemoryPressure 日志 | AppLog 输出"MemoryPressure: level=X"；缓存大小显著下降 |
| 低内存模拟器 | 1. 使用 Android Emulator lowRam 配置 2. 安装应用 3. 连续操作触发内存积累 4. 检查是否崩溃 | 应用在低内存设备上不崩溃 |
| ADB 命令 | `adb shell am send-trim-memory <pid> RUNNING_LOW` → 检查 AppLog 输出 | MemoryPressure 回调触发且执行了缓存清理 |

### BackupFileValidator 测试

| 测试夹具 | 准备方法 | 验证点 |
|---------|---------|--------|
| 正常备份文件 | 用本项目生成标准备份文件 | validate() 返回成功 |
| 损坏 JSON | 手动编辑备份文件 JSON 使其格式错误 | validate() 返回失败 + 原因"JSON 格式错误" |
| 缺少必需字段 | 删除备份文件中的 bookSources 节点 | validate() 返回失败 + 原因"缺少必需字段(bookSources)" |
| 加密配置验证 | 使用 BackupAES 加密服务器配置后验证 | 加密配置解密验证通过 |

### InnerBrowserLink 测试

| 测试场景 | 步骤 | 验证点 |
|---------|------|--------|
| 内部链接（mdLinkInnerBrowser=true） | 点击阅读内容中的书源内部链接 | 应用内 WebView 打开 |
| 外部链接（mdLinkInnerBrowser=true） | 点击阅读内容中的外部链接 | 系统浏览器打开 |
| 功能关闭（mdLinkInnerBrowser=false） | 关闭开关后点击任何链接 | 所有链接用系统浏览器打开 |

### UrlRecordInterceptor 测试（P1）

| 测试场景 | 步骤 | 证点 |
|---------|------|-------|
| 开关启用 | 在开发者选项启用 URL 记录 → 执行书源搜索 → 检查 AppLog | AppLog 输出完整请求链路 |
| 开关关闭 | 关闭 URL 记录 → 执行书源搜索 → 检查 AppLog | AppLog 无 URL 记录输出 |
| 性能影响 | 分别在开关开/关状态下执行100次请求 → 测量平均耗时 | 开关开启时延迟 ≤ 5ms（可接受） |

### 回归测试

每个 P0 功能集成后需执行以下回归验证：
1. 编译通过（gradle assembleDebug 无错误）
2. 现有功能不受影响：阅读、书源搜索、书架管理、备份恢复、RSS 阅读
3. 新功能不引入 ANR 或崩溃

---

## 文件变更清单

### P0 文件（新建）

| 文件路径 | 说明 | 源码来源行数 |
|---------|------|-----------|
| `app/src/main/java/io/legado/app/help/HelpDoc.kt` | 帮助文档数据类 | 6行（fork版简化为2字段） |
| `app/src/main/java/io/legado/app/help/HelpDocManager.kt` | 帮助文档管理器 | 69行 |
| `app/src/main/java/io/legado/app/ui/help/HelpDocActivity.kt` | 帮助文档展示页面（新增） | 新建 |
| `app/src/main/java/io/legado/app/help/MemoryPressure.kt` | 内存压力响应组件 | 90行 |
| `app/src/main/java/io/legado/app/help/InnerBrowserUrlSpan.kt` | 内置浏览器 URL Span | 24行 |
| `app/src/main/java/io/legado/app/help/InnerBrowserLinkResolver.kt` | 内置浏览器链接解析器 | 24行 |
| `app/src/main/java/io/legado/app/help/storage/BackupFileValidator.kt` | 备份文件校验器 | 597行 |
| `app/src/main/java/io/legado/app/help/storage/BackupInfoHelper.kt` | 备份信息读取工具 | 324行 |
| `app/src/main/java/io/legado/app/help/storage/StorageCalculator.kt` | 存储空间计算工具 | 782行 |
| `app/src/main/java/io/legado/app/ui/settings/StorageManageActivity.kt` | 存储管理页面（新增） | 新建 |
| `app/src/main/java/io/legado/app/help/book/SpecialContentProtector.kt` | 内容保护工具 | 41行 |
| `app/src/main/assets/help/` | 帮助文档 Markdown 目录 | 新建 |

### P0 文件（修改）

| 文件路径 | 修改内容 |
|---------|---------|
| `app/src/main/java/io/legado/app/App.kt` | 注册 MemoryPressure ComponentCallbacks2 回调 |
| `app/src/main/java/io/legado/app/help/PaintPool.kt` | 新增 clear() 方法（回收所有对象并清空池） |
| `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | 新增 mdLinkInnerBrowser（默认 true）字段 |
| `app/src/main/java/io/legado/app/help/book/ContentProcessor.kt` | 集成 SpecialContentProtector 处理步骤 |
| `app/src/main/java/io/legado/app/help/storage/Restore.kt` | 集成 BackupFileValidator 验证逻辑 |
| `app/src/main/java/io/legado/app/ui/main/MainFragment.kt` 或 AboutActivity | 添加"帮助文档"入口按钮 |
| `app/src/main/java/io/legado/app/ui/settings/SettingsActivity.kt` | 添加"存储管理"入口 + mdLinkInnerBrowser 开关 |

### P1 文件（新建）

| 文件路径 | 说明 | 源码来源行数 |
|---------|------|-----------|
| `app/src/main/java/io/legado/app/help/http/UrlRecordInterceptor.kt` | URL 记录拦截器 | 201行 |
| `app/src/main/java/io/legado/app/help/config/CoverHtmlTemplateConfig.kt` | 封面 HTML 模板配置 | 189行 |
| `app/src/main/java/io/legado/app/help/config/BubblePackageManager.kt` | 段评气泡包管理 | 287行 |
