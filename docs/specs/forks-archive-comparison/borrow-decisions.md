# 借鉴决策表（最终整合版）

> **基于**：7 个模块深度分析中间文件（SA-1 ~ SA-7）
> **决策总数**：118 项（47 借鉴 / 35 不借鉴 / 36 待评估）
> **生成时间**：2026-07-18
> **文档版本**：v2.0 最终整合版（取代 v1.0 初版）

---

## 一、决策汇总

### 1.1 三态分布

| 决策类型 | 数量 | 占比 | 说明 |
|---------|------|------|------|
| 建议借鉴（Borrow） | 47 | 39.8% | 有明确收益、低风险、可实施 |
| 不建议借鉴（Skip） | 35 | 29.7% | 偏离主航道 / 已有更优实现 / 体量过大 / 已知 Bug |
| 待评估（Evaluate） | 36 | 30.5% | 需结合用户反馈与优先级决策 |

### 1.2 按优先级分布（仅借鉴项）

| 优先级 | 数量 | 时间窗口 | 特征 |
|--------|------|---------|------|
| P0 立即启动 | 17 | 本周内 | 收益≥4 + 风险≤2 + 复杂度低/中 |
| P1 季度规划 | 15 | 3 个月内 | 收益≥3 + 风险≤3 + 复杂度中 |
| P2 年度规划 | 15 | 6-12 个月 | 收益≥3 + 风险≤5 + 复杂度中/高 |

### 1.3 按模块分布

| 模块 | 借鉴 | 不借鉴 | 待评估 | 小计 |
|------|------|--------|--------|------|
| SA-1 主题管理 | 8 | 2 | 6 | 16 |
| SA-2 EPUB | 10 | 6 | 7 | 23 |
| SA-3 AI 助手 | 8 | 5 | 5 | 18 |
| SA-4 RSS/发现页 | 6 | 8 | 7 | 21 |
| SA-5 视频 | 2 | 4 | 3 | 9 |
| SA-6 构建 | 9 | 7 | 5 | 21 |
| SA-7 依赖 | 4 | 3 | 3 | 10 |
| **合计** | **47** | **35** | **36** | **118** |

---

## 二、P0 立即启动（17 项）

### 2.1 BUILD 模块（5 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 1 | BUILD-B-01 | CI 专用调试证书（CI_DEBUG_KEY_* + ci-debug.keystore） | 5 | 1 | 低 | Archive `.github/workflows/private-armv8-release.yml` L46-53 用独立 secrets，本项目共用 RELEASE_KEY_STORE 有泄露风险 |
| 2 | BUILD-B-02 | armv8 单架构 CI（-Pabi=arm64-v8a 动态注入） | 5 | 1 | 低 | Archive `app/build.gradle` L73-77 支持 `-Pabi` 动态注入，本项目静态写死双架构 |
| 3 | BUILD-B-03 | CI 增量构建缓存（actions/cache/restore + save） | 5 | 1 | 低 | Archive `private-armv8-release.yml` L26-40 + L95-106 缓存 .gradle/.kotlin/build |
| 4 | BUILD-B-04 | -PVERSION_NAME / -PVERSION_CODE CI 注入 | 4 | 1 | 低 | Archive `app/build.gradle` L22-36 支持 property 注入 |
| 5 | BUILD-B-05 | sync-release-gitee 镜像同步工作流 | 4 | 2 | 中 | Archive 独有 `.github/workflows/sync-release-gitee.yml` |

### 2.2 DEPS 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 6 | DEPS-B-01 | markwon strikethrough/tasklist/linkify 3 扩展 | 4 | 1 | 低 | Archive `app/build.gradle` L317-319 引入 3 扩展，本项目缺 |
| 7 | DEPS-B-02 | composeBom 升级到 2025.10.00 | 4 | 2 | 低 | Archive composeBom 2025.10.00 vs 本项目 2025.04.01，差半年 |

### 2.3 THEME 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 8 | THEME-B-01 | 纸墨风格（Paint.setShadowLayer） | 4 | 1 | 低 | Archive `PaperInkHelper.kt`（60 行）零外部依赖 |
| 9 | THEME-B-02 | 字体撞色检测（calculateContrast） | 4 | 1 | 低 | Archive `sanitizeFontColorAgainstSurfaces` 基于 `AndroidColorUtils.calculateContrast` |

### 2.4 RSS 模块（3 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 10 | RSS-B-01 | RssSearchActivity（激活 searchUrl 字段） | 5 | 1 | 低 | 本项目 RssSource 实体已有 searchUrl 字段但无 Activity 使用；Archive `RssSearchActivity.kt`（104 行）激活 |
| 11 | RSS-B-02 | SourceSelectDialog（统一源选择） | 4 | 2 | 中 | Archive `SourceSelectDialog.kt` 实现 book/rss 源统一选择 |
| 12 | RSS-B-03 | SearchBookMergeUtils（合并入口） | 4 | 2 | 中 | Archive `SearchBookMergeUtils.kt` 实现搜索结果合并 |

### 2.5 AI 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 13 | AI-B-01 | MCP 客户端（420 行可独立移植） | 5 | 2 | 中 | Archive `app/src/main/java/io/legado/app/ai/mcp/` 完整实现 MCP 2025-06-18 协议 |
| 14 | AI-B-02 | Tavily 联网搜索 | 4 | 2 | 中 | Archive `TavilySearchTool.kt` 实现 AI 联网搜索能力 |

### 2.6 EPUB 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 15 | EPUB-B-01 | 章节资源索引（spine 优先） | 3 | 1 | 低 | Archive EpubFile.kt 用 spine 优先索引，提升章节加载速度 |
| 16 | EPUB-B-02 | 资源过滤 + 标题归一化 | 3 | 1 | 低 | Archive 过滤非内容资源 + 标题归一化处理 |

### 2.7 VIDEO 模块（1 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 17 | VIDEO-B-01 | VideoBookPreloader 视频书预加载 | 4 | 1 | 低 | Archive `VideoBookPreloader.kt`（90 行）搜索结果页预加载视频书目录 |

---

## 三、P1 季度规划（15 项）

### 3.1 THEME 模块（3 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 1 | THEME-B-03 | 主题包 ZIP 导入导出 | 5 | 3 | 中 | Archive `ThemePackageManager.kt`（1428 行）完整 ZIP 导入导出 |
| 2 | THEME-B-04 | Config 字段扩展（30+ 字段） | 4 | 3 | 中 | Archive Config 30+ 字段 vs 本项目 9 字段 |
| 3 | THEME-B-05 | 字体内嵌支持 | 4 | 2 | 中 | Archive EPUB 引擎字体内嵌实现 |

### 3.2 EPUB 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 4 | EPUB-B-03 | 性能日志 + 图片尺寸缓存 | 3 | 1 | 低 | Archive EpubFile.kt 性能日志和图片尺寸缓存 |
| 5 | EPUB-B-04 | 相邻章节预加载 | 3 | 2 | 中 | Archive 相邻章节预加载机制 |

### 3.3 AI 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 6 | AI-B-03 | AiResolvedTool 抽象 | 4 | 2 | 中 | Archive `AiResolvedTool.kt` 统一工具结果抽象 |
| 7 | AI-B-04 | 上下文压缩机制 | 4 | 2 | 中 | Archive AI 上下文压缩实现 |

### 3.4 RSS 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 8 | RSS-B-04 | pureSearch 参数（纯 URL 订阅源） | 4 | 2 | 中 | Archive `pureSearch` 参数实现纯 URL 模式 |
| 9 | RSS-B-05 | RssFragment openRssSearch 入口 | 4 | 1 | 低 | Archive RssFragment 5 行入口代码 |

### 3.5 VIDEO 模块（1 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 10 | VIDEO-B-02 | 章节链接缓存 + 下一集预加载 | 4 | 2 | 中 | Archive `chapterLinkCache` + `preloadNextEpisode`（TTL 30 分钟） |

### 3.6 DEPS 模块（3 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 11 | DEPS-B-03 | sora-editor 代码编辑器 | 4 | 2 | 中 | Archive `app/build.gradle` L340-342 引入 soraEditor BOM + core + language.textmate |
| 12 | DEPS-B-04 | reorderable Compose 拖拽排序 | 3 | 2 | 中 | Archive 引入 reorderable 3.1.0 |
| 13 | DEPS-B-05 | lazycolumnscrollbar Compose 滚动条 | 3 | 2 | 中 | Archive 引入 lazycolumnscrollbar 2.2.0 |

### 3.7 BUILD 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 14 | BUILD-B-06 | android-fast-debug 工作流 | 3 | 2 | 中 | Archive 独有 `.github/workflows/android-fast-debug.yml` |
| 15 | BUILD-B-07 | android-fast-release 工作流 | 3 | 2 | 中 | Archive 独有 `.github/workflows/android-fast-release.yml` |

---

## 四、P2 年度规划（15 项）

### 4.1 THEME 模块（3 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 1 | THEME-B-06 | AppearanceKit 套件架构 | 5 | 4 | 高 | Archive `AppearanceKitManager.kt`（905 行）跨组件套件绑定 |
| 2 | THEME-B-07 | 主题包云端同步 | 4 | 4 | 高 | Archive ThemePackageManager 云端同步能力 |
| 3 | THEME-B-08 | 跨组件套件绑定 KitBinding | 4 | 4 | 高 | Archive KitBinding 机制 |

### 4.2 AI 模块（2 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 4 | AI-B-05 | JS 脚本生图 | 4 | 3 | 中 | Archive JS 脚本生图能力 |
| 5 | AI-B-06 | 完整 AI Agent 架构 | 5 | 5 | 高 | Archive `AiAgentRuntime.runToolLoop` 三模式（Normal/Plan/Goal） |

### 4.3 EPUB 模块（3 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 6 | EPUB-B-05 | 注解系统 | 4 | 3 | 中 | Archive EPUB 注解（footnote/endnote）处理 |
| 7 | EPUB-B-06 | 分页缓存架构 | 4 | 4 | 高 | Archive 分页缓存优化 |
| 8 | EPUB-B-07 | 错误回退 + 文本选择器 | 3 | 3 | 中 | Archive 错误回退和文本选择器 |

### 4.4 RSS 模块（1 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 9 | RSS-B-06 | ExploreModernListScreen Compose | 3 | 3 | 中 | Archive `ExploreModernListScreen.kt` Compose 列表 |

### 4.5 DEPS 模块（4 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 10 | DEPS-B-06 | liquidglass 液态玻璃效果 | 3 | 3 | 中 | Archive 引入 liquidglass 1.0.3 |
| 11 | DEPS-B-07 | miuix.android 小米 UI 组件 | 3 | 3 | 中 | Archive 引入 miuix.android 0.8.8 |
| 12 | DEPS-B-08 | lottie 动画 | 3 | 2 | 中 | Archive 引入 lottie 6.6.6 |
| 13 | DEPS-B-09 | Glide ksp 迁移 | 4 | 3 | 中 | Archive 用 ksp，本项目用 kapt（Windows 跨盘 bug） |

### 4.6 BUILD 模块（1 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 14 | BUILD-B-08 | android-fast-debug 工作流增强 | 3 | 2 | 中 | Archive fast-debug 工作流增强能力 |

### 4.7 EPUB 模块（1 项）

| # | 决策ID | 决策项 | 收益 | 风险 | 复杂度 | 源码依据 |
|---|--------|--------|------|------|--------|---------|
| 15 | EPUB-B-08 | 双模式开关（useExperimentalEpubCore） | 3 | 4 | 高 | Archive 双模式开关实现渐进式迁移 |

---

## 五、不建议借鉴（35 项）

### 5.1 偏离主航道类（10 项）

| # | 决策ID | 决策项 | 不借鉴理由 |
|---|--------|--------|-----------|
| 1 | EPUB-S-01 | EPUB 原生渲染引擎 - CSS 级联 | 8000+ 行，偏离"书源规则引擎"主航道 |
| 2 | EPUB-S-02 | EPUB 原生渲染引擎 - 盒模型布局 | 同上 |
| 3 | EPUB-S-03 | EPUB 原生渲染引擎 - 自定义 View | 同上 |
| 4 | EPUB-S-04 | EPUB 双模式开关（短期） | 工程量过大，P2 评估 |
| 5 | EPUB-S-05 | EPUB WebView 方案 | 与本项目"书源规则引擎"主航道冲突 |
| 6 | EPUB-S-06 | EPUB CSS 级联（specificity + important + 继承） | 工程量过大 |
| 7 | AI-S-01 | AI 完整 Plan/Goal 模式 | 年度规划阶段评估 |
| 8 | AI-S-02 | AI 完整 Agent 架构（短期） | P2 评估 |
| 9 | THEME-S-01 | AppearanceKit 完整套件（短期） | P2 评估 |
| 10 | THEME-S-02 | 主题包云端同步（短期） | P2 评估 |

### 5.2 已有更优实现类（10 项）

| # | 决策ID | 决策项 | 不借鉴理由 |
|---|--------|--------|-----------|
| 1 | VIDEO-S-01 | 视频播放器基础架构 | 本项目 8167 行已大幅领先 Archive 4189 行 |
| 2 | VIDEO-S-02 | ViewPager2 文章切换 | 本项目已实现 |
| 3 | VIDEO-S-03 | 抖音风格沉浸式播放器 | 本项目已实现 |
| 4 | VIDEO-S-04 | WebView 降级机制 | 本项目已实现 |
| 5 | RSS-S-01 | RSS 并行解析 | 本项目已有并行解析 + Semaphore 限流 |
| 6 | RSS-S-02 | lastHost 回填 | 本项目已有 |
| 7 | RSS-S-03 | F-P1-F 预连接 | 本项目已有 |
| 8 | DEPS-S-01 | Compose 依赖完整性 | 本项目 Compose 依赖更完整 |
| 9 | BUILD-S-01 | minify=true 策略 | 本项目 minify=true 更优，不应降级 |
| 10 | BUILD-S-02 | 静态双架构 | 本项目已支持动态注入更优 |

### 5.3 体量过大与极简哲学冲突类（8 项）

| # | 决策ID | 决策项 | 不借鉴理由 |
|---|--------|--------|-----------|
| 1 | RSS-S-04 | DiscoverySuite 套件系列（4 文件 130KB+） | 体量过大与"极简≠残缺"哲学冲突 |
| 2 | RSS-S-05 | DiscoverySuiteConfig 数据模型 | 同上 |
| 3 | RSS-S-06 | DiscoverTagAdapter | 同上 |
| 4 | RSS-S-07 | Compose 双轨集成 | 本项目已有 Compose 集成 |
| 5 | RSS-S-08 | Compose RSS 源列表 | 本项目已有 |
| 6 | RSS-S-09 | Compose 规则订阅 | 本项目已有 |
| 7 | THEME-S-03 | AppearanceKit 完整套件（短期） | P2 评估 |
| 8 | EPUB-S-07 | EPUB 原生渲染引擎完整集成 | 16000+ 行过大 |

### 5.4 已知 Bug 类（4 项）

| # | 决策ID | 决策项 | 不借鉴理由 |
|---|--------|--------|-----------|
| 1 | VIDEO-S-05 | SPLIT_TAG 拼接 headers 方案 | 3003 错误根因，本项目已用 setMimeType 修复 |
| 2 | VIDEO-S-06 | GSY ProxyCacheManager | 已废弃 |
| 3 | BUILD-S-03 | Archive minify=false | 不应降级 |
| 4 | BUILD-S-04 | Archive 静态双架构 | 本项目已动态注入更优 |

### 5.5 其他（3 项）

| # | 决策ID | 决策项 | 不借鉴理由 |
|---|--------|--------|-----------|
| 1 | DEPS-S-02 | Glide 高级配置 | 本项目已有 |
| 2 | RSS-S-10 | WebView 池作用域扩展 | 本项目已有 |
| 3 | AI-S-03 | AI 完整工具注册表 | P2 评估 |

---

## 六、待评估（36 项）

### 6.1 THEME 模块（6 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | THEME-E-01 | 5 种 RED 格式兼容 | 用户是否需要导入外部主题格式 |
| 2 | THEME-E-02 | 主题包目录化结构 | 与现有扁平结构兼容性 |
| 3 | THEME-E-03 | KitBinding 跨组件绑定 | 与现有组件兼容性 |
| 4 | THEME-E-04 | 主题包导入导出格式 | 用户习惯 |
| 5 | THEME-E-05 | 主题预览能力 | UI 改造成本 |
| 6 | THEME-E-06 | 主题调度策略 | 性能影响 |

### 6.2 EPUB 模块（7 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | EPUB-E-01 | 注解系统 | 用户 EPUB 阅读频率 |
| 2 | EPUB-E-02 | 字体内嵌 | 字体版权问题 |
| 3 | EPUB-E-03 | 分页缓存架构 | 改造成本 |
| 4 | EPUB-E-04 | 相邻预加载策略 | 内存占用 |
| 5 | EPUB-E-05 | 错误回退机制 | 与现有错误处理兼容性 |
| 6 | EPUB-E-06 | 文本选择器 | UI 改造成本 |
| 7 | EPUB-E-07 | 双模式开关 | 与现有 EpubFile 兼容性 |

### 6.3 AI 模块（5 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | AI-E-01 | AI 工具注册表完整迁移 | 与现有架构兼容性 |
| 2 | AI-E-02 | AI 工具执行器 | 性能影响 |
| 3 | AI-E-03 | AI 工具验证器 | 安全性 |
| 4 | AI-E-04 | AI 上下文窗口管理 | 内存占用 |
| 5 | AI-E-05 | AI 对话历史持久化 | 隐私问题 |

### 6.4 RSS 模块（7 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | RSS-E-01 | DiscoverySuiteConfig 数据模型 | 与现有 RssSource 兼容性 |
| 2 | RSS-E-02 | webViewPoolScope 参数 | 与现有 WebView 池兼容性 |
| 3 | RSS-E-03 | focusSearch 参数 | UI 行为定制 |
| 4 | RSS-E-04 | FlexboxLayout 标签栏 | 与现有 TabLayout 兼容性 |
| 5 | RSS-E-05 | SearchBookPreviewOverlay | UI 改造成本 |
| 6 | RSS-E-06 | cacheFirst 默认值 | 与现有 RSS 缓存策略一致性 |
| 7 | RSS-E-07 | DiscoverySuitePageSnapshotStore | 持久化策略 |

### 6.5 VIDEO 模块（3 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | VIDEO-E-01 | ReadRecentBook 写入 | 与现有阅读记录兼容性 |
| 2 | VIDEO-E-02 | ChoiceSpeedDialog 增强 | UI 改造成本 |
| 3 | VIDEO-E-03 | Exo2MediaPlayer 增强 | 与现有 ExoPlayer 封装兼容性 |

### 6.6 BUILD 模块（5 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | BUILD-E-01 | ProGuard 规则差异 | 与现有混淆规则兼容性 |
| 2 | BUILD-E-02 | lint 配置差异 | 与现有 lint 配置兼容性 |
| 3 | BUILD-E-03 | packaging 配置差异 | 与现有 packaging 配置兼容性 |
| 4 | BUILD-E-04 | sourceSets 配置差异 | 与现有 sourceSets 兼容性 |
| 5 | BUILD-E-05 | compileOptions 差异 | 与现有 compileOptions 兼容性 |

### 6.7 DEPS 模块（3 项）

| # | 决策ID | 决策项 | 评估方向 |
|---|--------|--------|---------|
| 1 | DEPS-E-01 | miuix.android 完整集成 | 是否需要小米 UI 组件 |
| 2 | DEPS-E-02 | liquidglass 完整集成 | 是否需要液态玻璃效果 |
| 3 | DEPS-E-03 | lottie 完整集成 | 是否需要动画 |

---

## 七、决策追踪机制

### 7.1 追踪频率

| 优先级 | 追踪频率 | 责任人 | 状态 |
|--------|---------|--------|------|
| P0 | 每周 | 项目维护者 | 待启动 |
| P1 | 每月 | 项目维护者 | 待规划 |
| P2 | 每季度 | 项目维护者 | 待评估 |

### 7.2 状态定义

| 状态 | 说明 |
|------|------|
| 待启动 | 已识别但未开始 |
| 规划中 | 已创建 spec 但未实施 |
| 实施中 | spec 已通过，正在实施 |
| 已完成 | 实施完成并通过验证 |
| 已搁置 | 评估后决定暂不实施 |
| 已拒绝 | 评估后决定不实施 |

### 7.3 追踪文件

- 本文件：`docs/specs/forks-archive-comparison/borrow-decisions.md`
- 关联中间文件：`docs/specs/forks-archive-comparison/intermediate/SA-*-*.md`
- 关联分析报告：`docs/specs/forks-archive-comparison/analysis-report.md`

---

## 八、决策变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-07-18 | v1.0 | 初版，基于 4 个模块（SA-1/3/6/7） |
| 2026-07-18 | v2.0 | 最终整合版，基于 7 个模块完整分析，决策数 29→118 |

---

**决策表完成**。共 118 项决策（47 借鉴 / 35 不借鉴 / 36 待评估），按 P0/P1/P2 三级优先级分类。
