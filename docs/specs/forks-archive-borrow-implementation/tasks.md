# 任务清单 - 阅读 Archive 借鉴决策实施

> **生成时间**：2026-07-18
> **基于**：v5.0 终版决策（54 项借鉴决策 / 64 项不借鉴 / 0 项待评估）
> **实施周期**：P0 立即启动 / P1 季度内 / P2 年度内（AI 执行，按依赖顺序实施，无工期估算）
> **决策来源**：`docs/specs/forks-archive-comparison/final-adjustment.md` §四 v5.0 终版完整清单
> **总览统计**：P0 14 项 / P1 19 项 / P2 21 项 = 54 项借鉴
> **minSdk 一致性**（与 design.md ADR-022 一致）：所有任务统一遵循 minSdk 23（与本项目 `app/build.gradle:66` 实际一致）；引入新依赖或使用新 API 时需验证 minSdk 23 兼容性
> **借鉴代码合并策略**（与 design.md ADR-010b 一致）：本项目优先 + fork 仓库参考；合并冲突时以本项目实现为准，fork 仓库仅作参考；涉及加密密钥的场景需实现密钥丢失恢复机制（从备份恢复 + 用户提示）

---

## 1. P0 立即启动任务（14 项）

> **特征**：收益≥4.5 + 风险≤2 + 复杂度低/中，100% 聚焦用户核心场景（看书/订阅/视频）
> **v5.1 调整**：RSS-B-05/VIDEO-B-02/VIDEO-E-01/VIDEO-E-02 从 P1 升级 P0（基于 analysis-task-priority.md 用户价值再评估，评分 90-96）
> **P0 数量说明**（与 analysis-task-priority.md 跨文档一致性）：P0=14 项（v5.1 调整后），analysis-task-priority.md §1.1 表格写 P0=10 是 v5.0 版本；本 tasks.md 以 v5.1 终版为准
> **实施顺序**（与 design.md ADR-002 + R22 一致）：4 个组按文件隔离原则顺序执行（组间逻辑并行但物理串行，主 Agent 单线程），4 组分别为 RSS 组（1.1/1.5/1.7/1.8/1.11）、THEME 组（1.3/1.6）、EPUB 组（1.9/1.10）、VIDEO 组（1.4/1.12/1.13/1.14）+ DEPS（1.2）
> **文件清单补充**（与 design.md 文件清单一致）：每个新增 Activity/界面组件的任务，除主体代码外必须同步修改 3 个文件：①`app/src/main/AndroidManifest.xml` 注册组件；②`app/src/main/res/values/strings.xml` 新增字符串；③`app/proguard-rules.pro` 新增 keep 规则。任务 1.1 已展开为子任务 1.1.5/1.1.6/1.1.7，其他新增界面任务按同模式补充

### 1.1 RSS-B-01: RssSearchActivity（用户价值 5.0）
- [ ] 1.1.1 创建 RssSearchActivity.kt（继承 VMBaseActivity 本项目基类 `app/src/main/java/io/legado/app/base/VMBaseActivity.kt:9`；基于 Archive 104 行实现，激活 searchUrl 字段）
- [ ] 1.1.2 复用现有 RssSortViewModel（⚠️ **不新增 RssSearchViewModel**——Archive 项目 RssSearchActivity.kt:20 实际 `class RssSearchActivity : VMBaseActivity<ActivityRssSearchBinding, RssSortViewModel>()` 复用现有 RssSortViewModel，与 Archive 借鉴源一致，降低实施风险）
- [ ] 1.1.3 创建 RssSearchAdapter.kt
- [ ] 1.1.4 `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` 添加搜索入口（5 行代码）
- [ ] 1.1.5 修改 `app/src/main/AndroidManifest.xml` 注册 RssSearchActivity
- [ ] 1.1.6 修改 `app/src/main/res/values/strings.xml` 新增搜索相关字符串
- [ ] 1.1.7 修改 `app/proguard-rules.pro` 新增 RssSearchActivity keep 规则
- [ ] 1.1.8 单元测试覆盖搜索/分页/异常
- [ ] 1.1.9 真机验证订阅内容搜索
- **状态**：待启动
- **依赖**：无（数据已就绪，RssSource.searchUrl 字段已存在）
- **说明**：本项目 `app/src/main/java/io/legado/app/ui/rss/` 下无 search/ 子目录，需新建 `ui/rss/search/` 子目录存放 RssSearchActivity/Adapter（⚠️ ViewModel 复用现有 RssSortViewModel，无需新建）

### 1.2 DEPS-B-01: markwon 4.6.2 扩展（用户价值 5.0）
- [x] 1.2.0 ✅ 已实现（`app/build.gradle:329-332` 已引入 markwon core+image-glide+tables+html；`gradle/libs.versions.toml:24` markwon = "4.6.2"）
- [ ] 1.2.1 在 app/build.gradle 添加 markwon-strikethrough 依赖
- [ ] 1.2.2 添加 markwon-tasklist 依赖
- [ ] 1.2.3 添加 markwon-linkify 依赖
- [ ] 1.2.4 配置 Markwon 引擎使用新扩展（订阅文章渲染入口）
- [ ] 1.2.5 真机验证订阅文章渲染（删除线/任务列表/链接识别）
- [ ] 1.2.6 验证 3.x 与 4.x API 兼容性（现有 4 个依赖 core/image-glide/tables/html 与新扩展 tasklist/strikethrough/linkify 的 API 兼容性）
- **状态**：markwon 4.6.2 core 已引入 / 需补充 tasklist+strikethrough+linkify + 验证 API 兼容性
- **依赖**：无
- **说明**：markwon 4.6.2 核心已引入，仅需补充 3 个扩展模块。⚠️ **markwon 3.x 与 4.x API 不兼容**，借鉴 Archive 项目时（如 Archive 用 markwon 3）需进行 API 适配；现有 4 个依赖（core/image-glide/tables/html）与新扩展（tasklist/strikethrough/linkify）的兼容性必须在实施时验证

### 1.3 THEME-B-01: 纸墨风格（用户价值 5.0）
- [ ] 1.3.1 创建 PaperInkHelper.kt（基于 Paint.setShadowLayer，60 行零外部依赖）
- [ ] 1.3.2 集成到阅读界面（ContentTextView/PageView）
- [ ] 1.3.3 添加主题配置开关（ReadConfig 入口）
- [ ] 1.3.4 真机验证阅读视觉体验
- **状态**：待启动
- **依赖**：无
- **预计工作量**：1 天

### 1.4 VIDEO-B-01: VideoBookPreloader（用户价值 5.0）
- [ ] 1.4.1 创建 VideoBookPreloader.kt（基于 Archive 90 行实现，放置在 `app/src/main/java/io/legado/app/help/gsyVideo/`）
- [ ] 1.4.2 集成到 SearchActivity.kt（搜索结果页预加载视频书目录；⚠️ **不是 VideoPlayerActivity.kt**——VideoBookPreloader 在搜索结果页预加载，VideoPlayerActivity.kt 是视频播放页）
- [ ] 1.4.3 真机验证视频播放启动速度提升
- [ ] 1.4.4 单元测试覆盖预加载逻辑（缓存命中/超时/异常场景）
- **状态**：待启动
- **依赖**：无
- **预计工作量**：1 天
- **说明**：⚠️ 原 tasks.md 描述"集成到 VideoPlayerActivity.kt"是错误的（design.md §4.2 #2 错误标注），正确集成位置是 `app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt`（搜索结果页，已存在）。VideoBookPreloader.kt 放置在 `app/src/main/java/io/legado/app/help/gsyVideo/`，与 ChoiceSpeedDialog.kt/Exo2MediaPlayer.kt 同目录

### 1.5 RSS-E-06: cacheFirst 默认值（用户价值 4.8）
- [x] 1.5.1 ✅ 已完成（`app/src/main/java/io/legado/app/data/entities/RssSource.kt:113` cacheFirst: Boolean = true 已是默认值，无需调整）
- [x] 1.5.2 ✅ 已完成（`app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt:421` 已实现 `cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT`；原 design.md §4.1 #9 标注的 `RssWebActivity.kt` 文件不存在，正确文件为 `ReadRssActivity.kt`）
- [ ] 1.5.3 真机验证 RSS 加载速度（首次/二次进入对比）
- **状态**：✅ 已完成（仅 WebView 层需真机验证 1.5.3）
- **依赖**：无
- **说明**：数据层（RssSource.kt:113）+ WebView 层（ReadRssActivity.kt:421）均已完成，仅保留真机验证子任务

### 1.6 THEME-B-02: 字体撞色检测（用户价值 4.8）
- [ ] 1.6.1 实现 sanitizeFontColorAgainstSurfaces 方法
- [ ] 1.6.2 集成 AndroidColorUtils.calculateContrast（计算与背景对比度；本项目使用 `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt`，无 ThemeColorUtils.kt）
- [ ] 1.6.3 在主题设置界面添加撞色检测提示
- [ ] 1.6.4 真机验证配色异常场景提示
- **状态**：待启动
- **依赖**：无
- **预计工作量**：1 天

### 1.7 RSS-B-02: SourceSelectDialog（用户价值 4.5）
- [ ] 1.7.1 创建 SourceSelectDialog.kt
- [ ] 1.7.2 实现 book/rss 源统一选择逻辑
- [ ] 1.7.3 集成到源管理界面（BookSource/RssSource 共用入口）
- [ ] 1.7.4 真机验证源选择交互
- **状态**：待启动
- **依赖**：无
- **预计工作量**：2 天

### 1.8 RSS-B-03: SearchBookMergeUtils（用户价值 4.5）
- [ ] 1.8.1 创建 SearchBookMergeUtils.kt
- [ ] 1.8.2 实现搜索结果合并逻辑（同名书籍多源合并）
- [ ] 1.8.3 集成到搜索界面（SearchActivity）
- [ ] 1.8.4 真机验证多源搜索结果展示
- **状态**：待启动
- **依赖**：无
- **预计工作量**：2 天

### 1.9 EPUB-B-01: 章节资源索引（用户价值 4.5）
- [ ] 1.9.1 修改 `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` 使用 spine 优先索引（替代全资源遍历）
- [ ] 1.9.2 真机验证 EPUB 章节加载速度提升
- [ ] 1.9.3 单元测试覆盖 spine 索引逻辑（章节顺序/异常 EPUB/空 spine）
- [ ] 1.9.4 性能基准测试（首章加载时间基线 vs 改造后对比）
- **状态**：待启动
- **依赖**：无
- **预计工作量**：0.5 天

### 1.10 EPUB-B-02: 资源过滤+标题归一化（用户价值 4.5）
- [ ] 1.10.1 实现非内容资源过滤（图片/CSS/字体之外的资源跳过）
- [ ] 1.10.2 实现标题归一化（去除前后空白/统一命名规则）
- [ ] 1.10.3 真机验证 EPUB 阅读体验（目录标题展示）
- [ ] 1.10.4 单元测试覆盖资源过滤+标题归一化（边界 case/HTML 标签清理）
- **状态**：待启动
- **依赖**：无
- **预计工作量**：1 天

### 1.11 RSS-B-05: RssFragment openRssSearch 入口（用户价值 4.8，评分 96）
- [ ] 1.11.1 `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` 添加 openRssSearch 方法
- [ ] 1.11.2 真机验证入口跳转
- **状态**：待启动（v5.1 从 P1 升级 P0）
- **依赖**：RSS-B-01（1.1）
- **说明**：与 RSS-B-01 入口配套，5 行代码极低成本

### 1.12 VIDEO-B-02: 章节链接缓存+下一集预加载（用户价值 4.8，评分 96）
- [ ] 1.12.1 实现 chapterLinkCache（TTL 30 分钟）
- [ ] 1.12.2 实现 preloadNextEpisode 机制
- [ ] 1.12.3 真机验证连续看剧体验
- **状态**：待启动（v5.1 从 P1 升级 P0）
- **依赖**：VIDEO-B-01（1.4）
- **说明**：视频核心场景连续性优化

### 1.13 VIDEO-E-01: ReadRecentBook 写入（用户价值 4.5，评分 90）
- [ ] 1.13.1 新增 ReadRecentBook 实体+DAO（`app/src/main/java/io/legado/app/data/entities/ReadRecentBook.kt` + `app/src/main/java/io/legado/app/data/dao/ReadRecentBookDao.kt`；@Entity + @Parcelize + 字段默认值，遵循 Room 实体规范）
- [ ] 1.13.2 新增数据库 Migration（⚠️ **AppDatabase.kt 当前 version=98**，需新增 `Migration_98_to_99` 手写 Migration + entities 数组加入 `ReadRecentBook::class` + version 升级 98→99；迁移范围需包含 pureSearch 字段，与 design.md ADR-013 一致；schema 导出 + 真机验证覆盖安装流程）
- [ ] 1.13.3 视频书搜索结果分支集成（VideoPlay.kt 写入最近阅读）
- [ ] 1.13.4 真机验证视频书出现在"最近阅读"
- **状态**：待启动（v5.1 从 P1 升级 P0）
- **依赖**：无
- **说明**：视频书最近阅读，与 VIDEO-B-01/B-02 构成视频场景完整闭环
- **重要提示**：本项目当前无 ReadRecentBook 表（AppDatabase.kt:79-85 entities 数组共 26 个实体无 ReadRecentBook），仅 fork 仓库有，需从 fork 仓库参考实现。⚠️ 涉及数据库迁移（ADR-013），需独立验证覆盖安装流程，不可与其他任务简单并行

### 1.14 VIDEO-E-02: ChoiceSpeedDialog 增强（用户价值 4.5，评分 90）
- [ ] 1.14.1 增强 `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` 倍速选项
- [ ] 1.14.2 修改 ChoiceSpeedDialog 调用点（⚠️ 实际调用点是 `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt:600` 实例化 ChoiceSpeedDialog，**不是** `VideoPlayerActivity.kt:725-737`——VideoPlayerActivity.kt:725-737 用的是 Spinner 实现倍速，并非 ChoiceSpeedDialog）
- [ ] 1.14.3 真机验证倍速切换
- **状态**：待启动（v5.1 从 P1 升级 P0）
- **依赖**：无
- **说明**：视频倍速增强，高频交互优化
- **⚠️ 同文件冲突提示**：VIDEO-B-01/B-02/E-02 都修改 `VideoPlayerActivity.kt`，必须按顺序串行：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02（违反并发文件修改规范"同一源码文件的所有 Edit 必须由主 Agent 串行执行"）

---

## 2. P1 季度规划任务（19 项）

### 2.1 用户中高收益（13 项）

> **v5.1 调整说明**：RSS-B-05/VIDEO-B-02/VIDEO-E-01/VIDEO-E-02 已升级 P0（详见 §1.11~1.14），本节已移除并重新编号。
> **依赖关系修正**（基于 analysis-task-priority.md §5）：THEME-E-05 补充依赖 THEME-B-04；VIDEO-E-03 补充依赖 VIDEO-B-01。

#### 2.1.1 RSS-E-05: SearchBookPreviewOverlay（用户价值 4.3）
- [ ] 2.1.1.1 实现 SearchBookPreviewOverlay 搜索结果预览
- [ ] 2.1.1.2 真机验证搜索预览交互
- **状态**：待启动
- **依赖**：RSS-B-03（1.8）

#### 2.1.2 THEME-E-05: 主题预览能力（用户价值 4.3）
- [ ] 2.1.2.1 实现主题应用前预览
- [ ] 2.1.2.2 真机验证主题预览效果
- **状态**：待启动
- **依赖**：THEME-B-04（2.1.8）【v5.1 补充：预览需基于扩展后的 Config 字段】

#### 2.1.3 EPUB-E-04: 相邻预加载策略（用户价值 4.2）
- [ ] 2.1.3.1 实现相邻章节预加载机制
- [ ] 2.1.3.2 真机验证章节切换流畅度
- **状态**：待启动
- **依赖**：EPUB-B-01（1.9）

#### 2.1.4 DEPS-B-04: reorderable 拖拽排序（用户价值 4.2）
- [ ] 2.1.4.1 引入 reorderable 3.1.0 依赖
- [ ] 2.1.4.2 应用于书架/源列表拖拽排序
- [ ] 2.1.4.3 真机验证拖拽交互
- **状态**：待启动
- **依赖**：无

#### 2.1.5 EPUB-E-02: 字体内嵌（用户价值 4.1）
- [ ] 2.1.5.1 实现 EPUB 字体内嵌支持
- [ ] 2.1.5.2 真机验证字体显示
- **状态**：待启动
- **依赖**：无（注意字体版权问题）

#### 2.1.6 RSS-B-04: pureSearch 参数（用户价值 4.0）
- [ ] 2.1.6.1 实现 pureSearch 参数（纯 URL 订阅源模式）
- [ ] 2.1.6.2 真机验证纯 URL 源搜索
- **状态**：待启动
- **依赖**：无

#### 2.1.7 THEME-B-03: 主题包 ZIP 导入导出（用户价值 4.0）
- [ ] 2.1.7.1 创建 ThemePackageManager.kt（基于 Archive 1428 行实现，可裁剪）
- [ ] 2.1.7.2 实现 ZIP 导入
- [ ] 2.1.7.3 实现 ZIP 导出
- [ ] 2.1.7.4 真机验证主题包导入导出
- **状态**：待启动
- **依赖**：无

#### 2.1.8 THEME-B-04: Config 字段扩展（用户价值 4.0）
- [ ] 2.1.8.1 扩展 Config 字段（参考 Archive 30+ 字段，本项目 9 字段）
- [ ] 2.1.8.2 真机验证主题配置
- **状态**：待启动
- **依赖**：无

#### 2.1.9 THEME-B-05: 字体内嵌支持（用户价值 4.0）
- [ ] 2.1.9.1 实现主题字体内嵌
- [ ] 2.1.9.2 真机验证字体加载
- **状态**：待启动
- **依赖**：无

#### 2.1.10 THEME-E-04: 主题包导入导出格式（用户价值 4.0）
- [ ] 2.1.10.1 统一主题包导入导出格式
- [ ] 2.1.10.2 真机验证格式兼容
- **状态**：待启动
- **依赖**：THEME-B-03（2.1.7）

#### 2.1.11 EPUB-B-03: 性能日志+图片尺寸缓存（用户价值 4.0）
- [ ] 2.1.11.1 `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` 添加性能日志
- [ ] 2.1.11.2 实现图片尺寸缓存
- [ ] 2.1.11.3 真机验证 EPUB 性能
- **状态**：待启动
- **依赖**：EPUB-B-01（1.9）

#### 2.1.12 EPUB-E-06: 文本选择器（用户价值 4.0）
- [ ] 2.1.12.1 实现 EPUB 文本选择器
- [ ] 2.1.12.2 真机验证文本选择交互
- **状态**：待启动
- **依赖**：无

#### 2.1.13 VIDEO-E-03: Exo2MediaPlayer 增强（用户价值 4.0）
- [ ] 2.1.13.1 增强 `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` 封装
- [ ] 2.1.13.2 在 `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 中集成增强后的播放器
- [ ] 2.1.13.3 真机验证播放器稳定性
- **状态**：待启动
- **依赖**：VIDEO-B-01（1.4）【v5.1 补充：播放器增强应基于预加载架构】

### 2.2 开发者侧优化（6 项）

#### 2.2.1 BUILD-B-02: armv8 单架构 CI（用户价值 4.0）
- [ ] 2.2.1.1 修改 app/build.gradle 支持 -Pabi=arm64-v8a 动态注入
- [ ] 2.2.1.2 创建 armv8 单架构 CI 工作流
- [ ] 2.2.1.3 验证 CI 构建产物
- **状态**：待启动
- **依赖**：无

#### 2.2.2 BUILD-B-05: gitee 镜像同步（用户价值 4.0）
- [ ] 2.2.2.1 创建 sync-release-gitee.yml 工作流
- [ ] 2.2.2.2 验证 Gitee 镜像同步
- **状态**：待启动
- **依赖**：无

#### 2.2.3 BUILD-B-01: CI 专用调试证书（用户价值 2.8）
- [ ] 2.2.3.1 创建 ci-debug.keystore 独立证书
- [ ] 2.2.3.2 配置 CI_DEBUG_KEY_* secrets
- [ ] 2.2.3.3 验证 CI 调试证书隔离
- **状态**：待启动
- **依赖**：无
- **P1 资格提示**：用户价值 2.8 低于 P1 下限（4.0），P1 实施前需再次评估是否降级 P2（保持 P1=19 数据不变）

#### 2.2.4 BUILD-B-03: CI 增量构建缓存（用户价值 3.0）
- [ ] 2.2.4.1 配置 actions/cache/restore + save 缓存 .gradle/.kotlin/build
- [ ] 2.2.4.2 验证 CI 构建加速
- **状态**：待启动
- **依赖**：无
- **P1 资格提示**：用户价值 3.0 低于 P1 下限（4.0），P1 实施前需再次评估是否降级 P2（保持 P1=19 数据不变）

#### 2.2.5 BUILD-B-04: VERSION 注入（用户价值 3.0）
- [ ] 2.2.5.1 app/build.gradle 支持 -PVERSION_NAME / -PVERSION_CODE 注入
- [ ] 2.2.5.2 验证 CI 版本号注入
- **状态**：待启动
- **依赖**：无
- **P1 资格提示**：用户价值 3.0 低于 P1 下限（4.0），P1 实施前需再次评估是否降级 P2（保持 P1=19 数据不变）

#### 2.2.6 DEPS-B-05: lazycolumnscrollbar Compose 滚动条（用户价值 3.8）
- [ ] 2.2.6.1 引入 lazycolumnscrollbar 2.2.0 依赖
- [ ] 2.2.6.2 应用于 Compose 列表滚动条
- [ ] 2.2.6.3 真机验证滚动条交互
- **状态**：待启动
- **依赖**：无

---

## 3. P2 年度规划任务（21 项）

### 3.1 技术升级类（5 项）

> **注**：与 spec.md §4.3.1 一致，包含依赖升级 + 架构演进类任务。

#### 3.1.1 DEPS-B-02: composeBom 升级（用户价值 3.2）
- [ ] 3.1.1.1 升级 composeBom 至 2025.10.00
- [ ] 3.1.1.2 验证 Compose API 兼容性
- **状态**：待启动
- **依赖**：无

#### 3.1.2 DEPS-B-03: sora-editor 代码编辑器（用户价值 3.0）
- [x] 3.1.2.0 ✅ 已实现（`app/build.gradle:356-358` 已引入 soraEditor BOM+core+language.textmate）
- [ ] 3.1.2.1 验证 sora-editor 版本兼容性（与现有依赖无冲突）
- [ ] 3.1.2.2 应用于书源规则编辑界面（功能完整性验证）
- [ ] 3.1.2.3 真机验证代码编辑体验
- **状态**：sora-editor 已引入 / 工作量调整为验证版本兼容性+功能完整性
- **依赖**：无

#### 3.1.3 DEPS-B-09: Glide ksp 迁移（用户价值 3.0）
- [ ] 3.1.3.1 从 kapt 迁移至 ksp（解决 Windows 跨盘 bug）
- [ ] 3.1.3.2 验证 Glide 编译
- **状态**：待启动
- **依赖**：无

#### 3.1.4 THEME-B-06: AppearanceKit 套件架构（用户价值 3.8）
- [ ] 3.1.4.1 创建 AppearanceKitManager.kt（基于 Archive 905 行，可裁剪）
- [ ] 3.1.4.2 实现跨组件套件绑定
- [ ] 3.1.4.3 真机验证主题一致性
- **状态**：待启动
- **依赖**：无

#### 3.1.5 THEME-B-08: KitBinding 基础机制（用户价值 3.5）
- [ ] 3.1.5.1 实现 KitBinding 跨组件绑定机制（绑定框架）
- [ ] 3.1.5.2 真机验证 UI 一致性
- **状态**：待启动
- **依赖**：THEME-B-06（3.1.4）

### 3.2 用户中价值类（7 项）

> **注**：与 spec.md §4.3.2 一致。EPUB-B-06 已合并至 EPUB-E-03，EPUB-B-07 已合并至 EPUB-E-05（避免功能重复）。BUILD-B-06/07/08 按 3 项独立任务算。

#### 3.2.1 THEME-B-07: 主题包云端同步（用户价值 3.3）
- [ ] 3.2.1.1 实现主题包云端同步能力
- [ ] 3.2.1.2 真机验证云同步
- **状态**：待启动
- **依赖**：THEME-B-03（2.1.7）、THEME-E-04（2.1.10）【v5.1 补充：云端同步需基于统一格式保证跨设备兼容】

#### 3.2.2 EPUB-B-05: 注解系统（用户价值 3.2）
- [ ] 3.2.2.1 实现 EPUB 注解（footnote/endnote）处理
- [ ] 3.2.2.2 真机验证注解显示
- **状态**：待启动
- **依赖**：无

#### 3.2.3 EPUB-B-08: 双模式开关（用户价值 3.0）
- [ ] 3.2.3.1 实现 useExperimentalEpubCore 开关
- [ ] 3.2.3.2 验证渐进式迁移
- **状态**：待启动
- **依赖**：EPUB-B-01（1.9）、EPUB-B-02（1.10）、EPUB-B-03（2.1.11）【v5.1 补充：双模式开关需性能日志对比新旧模式性能】

#### 3.2.4 RSS-B-06: ExploreModernListScreen Compose（用户价值 3.0）
- [ ] 3.2.4.1 创建 ExploreModernListScreen.kt（Compose 列表）
- [ ] 3.2.4.2 真机验证发现页 Compose 体验
- **状态**：待启动
- **依赖**：无

#### 3.2.5 BUILD-B-06: android-fast-debug 工作流（用户价值 3.0）
- [ ] 3.2.5.1 创建 android-fast-debug.yml 工作流
- [ ] 3.2.5.2 验证 debug 工作流
- **状态**：待启动
- **依赖**：BUILD-B-02（2.2.1）

#### 3.2.6 BUILD-B-07: android-fast-release 工作流（用户价值 3.0）
- [ ] 3.2.6.1 创建 android-fast-release.yml 工作流
- [ ] 3.2.6.2 验证 release 工作流
- **状态**：待启动
- **依赖**：BUILD-B-02（2.2.1）

#### 3.2.7 BUILD-B-08: 增强 fast-debug 工作流能力（用户价值 3.0）
- [ ] 3.2.7.1 增强 fast-debug 工作流能力
- [ ] 3.2.7.2 验证增强后的 CI 工作流
- **状态**：待启动
- **依赖**：BUILD-B-06（3.2.5）

### 3.3 UI 优化类（9 项，放在最后）

> **来源**：待评估强制决策（6 项）+ UI 优化升级（3 项），用户接受增加包体积换取体验提升
> **注**：EPUB-E-03（原依赖 EPUB-B-06 已合并至本任务）、EPUB-E-05（原依赖 EPUB-B-07 已合并至本任务）作为独立任务存在，不再依赖已删除的 EPUB-B-06/B-07。

#### 3.3.1 THEME-E-01: 5 种 RED 格式兼容（用户价值 3.4）
- [ ] 3.3.1.1 实现 5 种 RED 主题格式兼容
- [ ] 3.3.1.2 真机验证外部主题导入
- **状态**：待启动
- **依赖**：无

#### 3.3.2 THEME-E-02: 主题包目录化结构（用户价值 3.4）
- [ ] 3.3.2.1 实现主题包目录化结构
- [ ] 3.3.2.2 真机验证主题包管理
- **状态**：待启动
- **依赖**：THEME-B-03（2.1.7）、THEME-E-01（3.3.1）【v5.1 补充：目录化结构需考虑多格式兼容】

#### 3.3.3 EPUB-E-03: 分页缓存架构（用户价值 3.5）
- [ ] 3.3.3.1 实现 EPUB 分页缓存架构（含持久化+预取策略）
- [ ] 3.3.3.2 真机验证 EPUB 长期阅读性能
- **状态**：待启动
- **依赖**：EPUB-B-01（1.9）

#### 3.3.4 EPUB-E-05: 错误回退机制（用户价值 3.7）
- [ ] 3.3.4.1 实现 EPUB 错误回退机制（含用户提示 UI）
- [ ] 3.3.4.2 真机验证 EPUB 错误提示
- **状态**：待启动
- **依赖**：无【v5.1 修正：错误回退与文本选择器功能独立，删除原依赖 EPUB-E-06】

#### 3.3.5 RSS-E-03: focusSearch 参数（用户价值 3.7）
- [ ] 3.3.5.1 实现 focusSearch 参数（UI 行为定制）
- [ ] 3.3.5.2 真机验证搜索框焦点行为
- **状态**：待启动
- **依赖**：RSS-B-01（1.1）

#### 3.3.6 RSS-E-04: FlexboxLayout 标签栏（用户价值 3.4）
- [ ] 3.3.6.1 引入 FlexboxLayout 替代 TabLayout
- [ ] 3.3.6.2 真机验证标签栏灵活布局
- **状态**：待启动
- **依赖**：无

#### 3.3.7 DEPS-B-06: liquidglass 液态玻璃效果（用户价值 3.8）
- [ ] 3.3.7.1 引入 liquidglass 1.0.3 依赖
- [ ] 3.3.7.2 应用于关键 UI 控件
- [ ] 3.3.7.3 真机验证视觉效果
- **状态**：待启动
- **依赖**：无

#### 3.3.8 DEPS-B-08: lottie 动画（用户价值 3.5）
- [ ] 3.3.8.1 引入 lottie 6.6.6 依赖
- [ ] 3.3.8.2 应用于加载/过渡动画
- [ ] 3.3.8.3 真机验证动画体验
- **状态**：待启动
- **依赖**：无

#### 3.3.9 THEME-E-03: KitBinding 跨组件绑定（用户价值 3.5）
- [ ] 3.3.9.1 实现 KitBinding 跨组件绑定（在 Theme/Read/Video 等组件间应用）
- [ ] 3.3.9.2 真机验证 UI 一致性
- **状态**：待启动
- **依赖**：THEME-B-08（3.1.5）

---

## 4. AOAdapt 日志

| 日期 | 变更内容 |
|------|---------|
| 2026-07-18 | 初始版本，基于 v5.0 终版决策创建 54 项任务（P0 10 / P1 23 / P2 21） |
| 2026-07-18 | 数据源：`docs/specs/forks-archive-comparison/final-adjustment.md` §四 v5.0 终版完整清单 |
| 2026-07-18 | v5.1 优先级调整：RSS-B-05/VIDEO-B-02/VIDEO-E-01/VIDEO-E-02 从 P1 升级 P0（基于 analysis-task-priority.md 用户价值再评估，评分 90-96）。调整后 P0 14 / P1 19 / P2 21。 |
| 2026-07-18 | v5.1 依赖关系修正（基于 analysis-task-priority.md §5）：补充 THEME-E-05→THEME-B-04、VIDEO-E-03→VIDEO-B-01、THEME-B-07→THEME-E-04、EPUB-B-08→EPUB-B-03、THEME-E-02→THEME-E-01；删除 EPUB-E-05→EPUB-E-06（功能独立）。 |
| 2026-07-18 | v5.1 删除工期估算：所有"2 周内""3 个月""12 个月""X 天"等工期估算改为"按依赖顺序实施（AI 执行无工期估算）"（用户反馈：AI 执行不需要工期估算）。 |
| 2026-07-18 | v5.2 文档修复（12 项严重问题）：A1 任务1.13 拆分为 3 子任务（ReadRecentBook 实体+DAO/Migration/集成）+fork 仓库参考提示；A2 任务1.1 BaseSearchActivity→VMBaseActivity；A3 任务1.5.1 标记已完成（cacheFirst 已是 true）；A4 修正 6 文件路径（EpubFile/RssFragment/VideoPlayerActivity/ChoiceSpeedDialog/Exo2MediaPlayer/ThemeUtils）；A5 标注 markwon+sora-editor 已引入；A6 标注 ui/rss/search/ 和 ui/rss/video/ 新建子目录；B1 补充 4 组顺序执行说明（ADR-002+R22）；B2 数据库迁移补充 pureSearch（ADR-013）；B3 任务1.1 补充 Manifest/strings/proguard 子任务；B4 统一 minSdk 23（ADR-022）；B5 补充借鉴代码合并策略+密钥恢复（ADR-010b）；C1 标注 P0=14 是 v5.1 调整后；C2 BUILD-B-01/03/04 标注 P1 资格提示。P0=14/P1=19/P2=21 数据不变。 |

---

## 5. 验收检查点

### 5.1 检查点 1：P0 完成（按依赖顺序实施，AI 执行无工期估算）
- [ ] 14 项 P0 任务全部完成
- [ ] 真机验证通过（每项任务的"真机验证"子项）
- [ ] `assets/updateLog.md` 更新（依据 version-delivery-sync.md 规范）
- [ ] 调试日志已清理（Grep "android.util.Log.d|android.util.Log.e" 确认无残留）
- [ ] 问题清单记录到 `issues-found.md`

### 5.2 检查点 2：P1 完成（按依赖顺序实施，AI 执行无工期估算）
- [ ] 19 项 P1 任务全部完成
- [ ] 真机验证通过
- [ ] `assets/updateLog.md` 更新

### 5.3 检查点 3：P2 完成（按依赖顺序实施，AI 执行无工期估算）
- [ ] 21 项 P2 任务全部完成（含 9 项 UI 优化放在最后）
- [ ] 真机验证通过
- [ ] `assets/updateLog.md` 更新

---

## 6. 任务统计总览

| 优先级 | 数量 | 占比 | 时间窗口 | 模块覆盖 |
|--------|------|------|---------|---------|
| P0 立即启动 | 14 | 25.9% | 按依赖顺序实施（AI 执行无工期估算） | RSS 5 / THEME 2 / EPUB 2 / VIDEO 4 / DEPS 1 |
| P1 季度规划 | 19 | 35.2% | 按依赖顺序实施（AI 执行无工期估算） | 用户中高收益 13 + 开发者侧 6 |
| P2 年度规划 | 21 | 38.9% | 按依赖顺序实施（AI 执行无工期估算） | 技术升级 5 + 用户中价值 7 + UI 优化 9 |
| **合计** | **54** | **100%** | - | - |

---

**任务清单完成**。共 54 项借鉴任务（P0 14 / P1 19 / P2 21），基于 v5.0 终版决策 + v5.1 优先级调整（RSS-B-05/VIDEO-B-02/VIDEO-E-01/VIDEO-E-02 升级 P0）。P0 100% 聚焦用户核心场景，UI 优化 9 项放在最后。
