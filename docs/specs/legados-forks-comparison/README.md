# legados Fork 对比与集成方案 ✅ 设计完成

> **状态**：✅ 设计完成
> **创建时间**：2026-07-22
> **任务来源**：用户要求下载 Gitee 上的 GEd520/legados 项目，与当前项目深度对比并生成 OpenSpec 设计文档
> **类型**：延伸版本对比（参考 `docs/project-rules/forks-reference.md`）

---

## 功能概述

本方案旨在对比分析 Gitee 上的 legados 分支（聚焦音频/TTS 增强）与当前项目（阅读 Sigma）的差异，基于**逐文件源码深度阅读**而非仅凭文件名推测，识别可集成的高价值特性，同时梳理双方各自独有的功能模块，为跨分支功能融合提供决策依据和实施路径。

### 核心发现

经过深度源码分析后，**纠正了多处初始误判**：

| 原始判断 | 纠正后 | 纠正原因 |
|---------|--------|---------|
| JsCacheManager = JS脚本编译缓存（P0） | JsCacheManager = CacheManager的JS调试包装层（降为P2） | 读源码发现只是 `cache.get()/cache.put()` 的调试日志包装，无编译缓存功能 |
| BubblePackageManager = Android 11+ 气泡通知 | BubblePackageManager = 段评/内容气泡包管理 | 读源码发现是内容评注气泡包的导入导出管理，非系统通知气泡 |
| BackupFileValidator = P1 中价值 | BackupFileValidator = P0 高价值 | 读源码发现是 597 行完整验证系统，JSON/XML格式校验+加密配置检查 |
| StorageCalculator = P1 中价值 | StorageCalculator = P0 高价值 | 读源码发现是 782 行完整存储管理工具，覆盖6种缓存类型+清理操作 |

---

## 核心能力

### legados 分支独有（当前项目缺失，经源码验证）

1. **内置帮助文档系统** — `HelpDoc`(68行) + `HelpDocManager`(68行)：从 assets 加载 Markdown 文件并在对话框中展示，支持显隐切换列表
2. **内存压力监控** — `MemoryPressure`(90行)：基于 `ComponentCallbacks2.onTrimMemory`，提供 `maxMemory`/`availableMemory`/`isSmallHeap` 属性，按级别释放缓存
3. **URL 记录拦截器** — `UrlRecordInterceptor`(201行)：OkHttp Interceptor，记录请求URL/域名/HTTP方法/响应状态/耗时，支持异步写数据库和调试事件中心，支持POST body记录
4. **内部浏览器链接解析** — `InnerBrowserUrlSpan`(24行) + `InnerBrowserLinkResolver`(24行)：基于 `AppConfig.mdLinkInnerBrowser` 设置，决定链接在应用内浏览器还是外部浏览器打开，使用 Markwon 链接解析
5. **备份文件验证** — `BackupFileValidator`(597行)：验证 JSON/XML 格式正确性，检查必需字段，处理加密服务器配置文件
6. **备份信息展示** — `BackupInfoHelper`(324行)：统计备份数据、提供备份概况和分类信息
7. **存储空间管理** — `StorageCalculator`(782行)：计算书籍/EPUB/临时文件/TTS/ACache/数据库/日志 6种缓存大小，提供缓存详情列表和清理操作
8. **内容保护** — `SpecialContentProtector`(41行)：用正则替换 HTML 标签和特殊标记，防止 HTML 解析时破坏特殊内容
9. **封面 HTML 模板配置** — `CoverHtmlTemplateConfig`(189行)：HTML 封面模板 CRUD + 默认模板机制 + 持久化存储
10. **段评气泡包管理** — `BubblePackageManager`(287行)：内容评注气泡包的导入导出和应用管理（非系统通知气泡）
11. **动态主题包管理** — `ApplicationThemeManager`(566行)：主题包导入导出+应用+命名+UI组件打包（vs 本项目 ThemeConfig 557行，功能侧重不同）
12. **字典调试配置** — `DictDebugConfig`(??行)：字典功能调试开关与参数配置
13. **UI 栏配置体系** — `NavigationBarConfig` + `TopBarConfig`：导航栏/顶栏配置化
14. **液态玻璃视觉效果库** — `liquidglass` 依赖：类玻璃质感视觉特效

### 当前项目独有（legados 分支缺失）

1. **高亮体系** — 8个文件（HighlightTextBuilder/HighlightStyles/HighlightStyle/HighlightRulePreview/HighlightRuleMatcher/HighlightMatcher/HighlightGeometry/HighlightColors）
2. **调试浮球** — `DebugFloatBallManager`：开发调试悬浮球工具
3. **封面画廊系统** — `CoverGalleryGroup` + `CoverGalleryImage` + `CoverGalleryGroupWithImages`：封面分组浏览
4. **书籍高亮持久化** — `BookHighlight` 实体：高亮数据持久存储
5. **视频链接提取** — `VideoUrlExtractor`：嵌入页面视频地址提取
6. **书源碎片管理** — `BookSourcePart` 实体
7. **RSS 增强** — `RssEpisode`/`RssRoute`/`SearchRssArticle`/`RssStar` 四个实体
8. **键盘辅助配置** — `KeyboardAssist` 实体
9. **搜索关键词管理** — `SearchKeyword` 实体
10. **阅读记录详情** — `ReadRecordDetail` 实体
11. **音频片头片尾跳过** — `AudioSkipCredits`(86行)：本项目独有，fork 将此逻辑内嵌到 Book 实体中

### 双方共有但实现差异（经源码对比验证）

1. **AudioPlay.kt** — fork 635行 vs 本项目 488行，fork 多出约147行功能（包括歌词回调、更多状态管理）
2. **AudioPlayService.kt** — fork 758行 vs 本项目 726行，fork 多32行，含片头片尾跳过内嵌逻辑
3. **AudioPlayActivity.kt** — 双方几乎一致（416 vs 417行）
4. **HttpTTS 实体** — 双方结构类似
5. **TTS 服务链** — 双方均有 TTS/TTSReadAloudService/HttpReadAloudService/BaseReadAloudService
6. **BackupConfig** — fork 221行 vs 本项目 147行，fork 多出 bookCacheKey 处理和更多配置项
7. **BackupAES** — 双方均有，但实现方式不同（fork 为独立类，本项目为扩展类）

---

## 关键约束

1. **合并冲突风险**：双方共有的音频/TTS 模块实现路径不同，直接合并可能导致运行时行为不一致
2. **API 兼容性**：部分特性依赖 Android 11+ API（如段评气泡），需确认本项目 minSdk 兼容策略
3. **依赖引入评估**：liquidglass 等新依赖需评估体积影响和许可证合规性
4. **数据模型兼容**：集成 legados 新实体时需确保 Room 数据库迁移安全
5. **功能优先级**：基于源码深度分析而非文件名推测来评估集成价值
6. **回归验证**：每个集成特性必须通过源码验证和真机测试

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 功能规格定义（Intent/Scope/Approach含Alternatives+Drawbacks/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计文档（Technical Approach/ADR Y-Statement/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务拆解与进度追踪（`- [ ] X.Y` 格式） |

---

## 状态追踪

| 阶段 | 状态 | 备注 |
|------|------|------|
| 项目下载 | ✅ 已完成 | 克隆到 temp/forks-comparison/legados/ |
| 深度源码分析 | ✅ 已完成 | 逐文件阅读 P0/P1 候选功能源码，纠正4处误判 |
| 功能规格 | ✅ 已生成 | spec.md 含 P0/P1/P2 三级18项候选 |
| 技术设计 | ✅ 已生成 | design.md 含4个ADR + 数据流 + 文件变更清单 |
| 任务拆解 | ✅ 已生成 | tasks.md 含7阶段29项任务 |
| 用户审查 | ⏳ 待确认 | 等待用户审核设计方案 |
