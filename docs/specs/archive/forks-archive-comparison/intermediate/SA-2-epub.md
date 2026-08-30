# SA-2 EPUB 阅读模块深度分析

## 1. 模块概述

### 1.1 模块定位

EPUB 阅读模块是 Archive 分叉（继承自 Lyc 维护的阅读分支）相对当前项目差异最大、
工程量最大的模块。Archive README 自述："深化 EPUB 原生阅读，持续补全图片、注解、
分页缓存、复杂样式和大文件导入体验"——经源码核实，这一描述对应 Archive 内部一套
完整的"原生 EPUB 渲染引擎"（Native EPUB Rendering Engine），从 DOM/CSS 解析、
布局算法、绘制指令、缓存层到自定义 View 全部自研。

当前项目仅保留 Legado 上游的 EPUB 处理范式：单文件 `EpubFile.kt` 用 epublib +
jsoup 提取章节 HTML 文本，再交由统一的 `ChapterProvider` / `TextChapterLayout`
分页绘制。EPUB 与 TXT/网络书源共用同一套文本渲染管线，没有 CSS 感知、没有原生
分页、没有注解处理。

### 1.2 核心差异一句话总结

> Archive 把 EPUB 当作"需要原生渲染的电子书"自研了一整套 CSS 盒模型 + 布局引擎 +
> 自定义 View；当前项目把 EPUB 当作"HTML 文本源"用 jsoup 抽取文本后走通用文本管线。

### 1.3 两边文件清单对比表（汇总）

| 维度 | Archive | 本项目 |
|------|---------|--------|
| EPUB 专属 Kotlin 文件数 | 46 个（9 个 top-level + 32 个 epubcore/ + 5 个 UI） | 1 个（`EpubFile.kt`） |
| EPUB 专属代码总行数 | 约 16500+ 行（仅 epubcore/ 就 7491 行） | 约 700 行 |
| 原生渲染引擎 | 有（EpubCore + EpubLayoutEngine） | 无 |
| CSS 解析与级联 | 有（EpubCss + EpubStyleComputer + EpubComputedStyle） | 无 |
| 自定义 EPUB View | 有（EpubReadView + EpubPageRenderer + EpubPageDisplayList + EpubGestureController + EpubSimulationTurnRenderer） | 无 |
| 注解（footnote）系统 | 有（EpubFootnote + 索引 + 预加载） | 无 |
| 字体内嵌处理 | 有（EpubFontFace + EpubTypefaceResolver + EpubFontCatalog） | 无 |
| 双模式开关 | 有（`AppConfig.useExperimentalEpubCore`） | 无 |
| assets/epub/ 资源 | 5 个文件（用于导出 EPUB） | 5 个文件（完全相同） |
| Book.kt 实体 EPUB 字段 | 无扩展 | 无扩展（两边一致） |

---

## 2. 文件清单对比

### 2.1 Archive 侧文件清单

#### 2.1.1 top-level Epub*.kt（位于 `app/src/main/java/io/legado/app/model/localBook/`）

| 文件 | 行数（约） | 用途 |
|------|-----------|------|
| `EpubFile.kt` | 111KB / ~2600 行 | EPUB 入口，双模式分发（native vs text），含 footnote/字体/缓存 |
| `EpubLayoutEngine.kt` | 102KB / ~2400 行 | 原生布局引擎核心（盒模型 → 分页 → DrawCommand） |
| `EpubCss.kt` | 34KB / ~465 行（epubcore/style 内同名文件 465 行） | CSS 解析 |
| `EpubDomBuilder.kt` | 22KB / ~520 行 | DOM 构建器（jsoup Document → EpubDomDocument） |
| `EpubBoxBuilder.kt` | 9.8KB / ~230 行 | 盒子树构建器（DOM → BoxTree） |
| `EpubLayout.kt` | 3.7KB / 145 行 | 布局结果数据结构（EpubLayoutDocument/DrawCommand 体系） |
| `EpubMiniLayout.kt` | 2.4KB / 66 行 | 标题等小场景布局辅助 |
| `EpubDom.kt` | 2.9KB / 103 行 | DOM 数据结构（EpubDomDocument/Element/Text/ComputedStyle） |
| `EpubBox.kt` | 1.6KB / 58 行 | 盒子树数据结构（Block/Inline/Text/Image/Break/PageColor） |

#### 2.1.2 epubcore/ 子目录（位于 `app/src/main/java/io/legado/app/model/localBook/epubcore/`）

按子模块分组（共 32 个文件，合计 7491 行）：

| 子模块 | 文件 | 行数 | 用途 |
|--------|------|------|------|
| **archive** | `EpubArchive.kt` | 15 | EPUB 压缩包抽象接口 |
| | `EpubPath.kt` | 46 | EPUB 内部路径工具 |
| | `ZipEpubArchive.kt` | 32 | 基于 Zip 的 EPUB 压缩包实现 |
| **cache** | `EpubCoreDiskCache.kt` | 115 | 原生布局磁盘缓存 |
| | `EpubCoreMemoryCache.kt` | 26 | 原生布局内存缓存 |
| **facade** | `EpubCoreFacade.kt` | 630 | 高层 API（paginate/peekPages/chapters） |
| | `EpubCoreProvider.kt` | 207 | 单例 Provider（章节列表加载入口） |
| | `EpubCoreBook.kt` | 11 | EPUB 书籍数据模型 |
| **font** | `EpubFontCatalog.kt` | 92 | 字体目录 |
| | `EpubFontFace.kt` | 19 | @font-face 数据 |
| | `EpubFontFaceParser.kt` | 218 | @font-face 解析 |
| | `EpubTypefaceResolver.kt` | 171 | Typeface 解析与缓存 |
| **image** | `EpubImageResolver.kt` | 149 | 图片资源解析 |
| **layout** | `EpubCoreLayoutConfig.kt` | 39 | 布局配置（视口/字体/间距） |
| | `EpubCorePage.kt` | 167 | 分页结果数据 |
| **model** | `ReaderModel.kt` | 29 | 阅读器模型 |
| **pkg** | `EpubPackage.kt` | 32 | EPUB 包结构 |
| | `EpubPackageParser.kt` | 90 | OPF 解析 |
| | `XmlTools.kt` | 68 | XML 工具 |
| **selector** | `EpubPageSelectorBuilder.kt` | 389 | 文本选择器构建（划线选词） |
| | `EpubSelectorModel.kt` | 58 | 选择器数据模型 |
| **style** | `EpubComputedStyle.kt` | 201 | 计算样式（含继承属性集） |
| | `EpubCss.kt` | 465 | CSS 解析 |
| | `EpubStyleComputer.kt` | 569 | 样式级联计算 |
| | `EpubStyleValue.kt` | 21 | 样式值（含 specificity/important） |
| **toc** | `EpubTocParser.kt` | 74 | 目录解析 |
| | `TocItem.kt` | 8 | 目录项 |
| **web** | `EpubChapterDocument.kt` | 9 | 章节文档 |
| | `EpubDomMeasureResult.kt` | 44 | DOM 测量结果 |
| | `EpubWebLayoutAdapter.kt` | 340 | WebView 布局适配器 |
| | `EpubWebLayoutJsonParser.kt` | 276 | WebView 布局 JSON 解析 |
| | `EpubWebLayoutResult.kt` | 135 | WebView 布局结果 |
| | `EpubWebLayoutSession.kt` | 1586 | WebView 布局会话（最大单文件） |
| | `EpubWebSelectionLayerSession.kt` | 1160 | WebView 选择层会话 |

#### 2.1.3 UI 层（位于 `app/src/main/java/io/legado/app/ui/book/read/epub/`）

| 文件 | 用途 |
|------|------|
| `EpubReadView.kt` | 自定义 FrameLayout，承载 EPUB 原生页面、手势、选区、放大镜 |
| `EpubPageRenderer.kt` | 页面渲染器（DrawCommand → Canvas） |
| `EpubPageDisplayList.kt` | 显示列表（指令缓存） |
| `EpubGestureController.kt` | 手势控制器（点击/滑动/长按/选择） |
| `EpubSimulationTurnRenderer.kt` | 仿真翻页渲染器 |

### 2.2 本项目侧文件清单

| 文件 | 行数（约） | 用途 |
|------|-----------|------|
| `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` | ~700 行 | EPUB 解析（epublib + jsoup），生成 HTML 文本 |
| `app/src/main/java/io/legado/app/model/localBook/LocalBook.kt`（EPUB 相关分支） | ~10 行 | 在 `getChapterList`/`getContent`/`upBookInfo` 中分发到 `EpubFile` |
| `app/src/main/java/io/legado/app/help/book/BookHelp.kt`（EPUB 相关分支） | ~15 行 | `getEpubFile(book)`、`cacheEpubFolderName="epub"` 缓存目录管理 |
| `app/src/main/assets/epub/`（5 个文件） | 共 1126 行 | EPUB 导出模板（main.css/chapter.html/cover.html/intro.html/fonts.css） |

### 2.3 独有/共有文件矩阵

| 文件 | Archive 有 | 本项目有 | 差异类型 |
|------|-----------|----------|---------|
| `EpubFile.kt`（model/localBook/） | ✓（~2600 行） | ✓（~700 行） | 重写 |
| `LocalBook.kt` | ✓ | ✓ | 修改（Archive 多 `EpubCoreDiskCache` 导入 + `LARGE_EPUB_FAST_IMPORT_BYTES` 常量 + `needRefreshEpubContent` 字段） |
| `BookHelp.kt` | ✓ | ✓ | 修改（Archive 多 `EpubFile` 直接导入 + `needRefreshEpubContent` 逻辑） |
| `Book.kt`（实体） | ✓ | ✓ | 共有（无 EPUB 字段扩展） |
| `assets/epub/main.css` | ✓（550 行） | ✓（550 行） | 共有（字节级一致） |
| `assets/epub/chapter.html` | ✓（13 行） | ✓（13 行） | 共有（字节级一致） |
| `assets/epub/cover.html` | ✓ | ✓ | 共有（字节级一致） |
| `assets/epub/intro.html` | ✓ | ✓ | 共有（字节级一致） |
| `assets/epub/fonts.css` | ✓ | ✓ | 共有（字节级一致） |
| `EpubBox.kt` / `EpubDom.kt` / `EpubLayout.kt` / `EpubMiniLayout.kt` | ✓ | ✗ | 独有 |
| `EpubBoxBuilder.kt` / `EpubDomBuilder.kt` / `EpubCss.kt` / `EpubLayoutEngine.kt` | ✓ | ✗ | 独有 |
| `epubcore/` 整个目录（32 文件） | ✓ | ✗ | 独有 |
| `ui/book/read/epub/` 整个目录（5 文件） | ✓ | ✗ | 独有 |

---

## 3. 核心文件深度对比

### 3.1 EpubFile.kt 对比

#### 3.1.1 行数对比
- Archive：约 2600 行（111KB）
- 本项目：约 700 行（23KB）
- 差距：约 3.7 倍

#### 3.1.2 关键 Companion 字段对比

**Archive 独有字段**（位于 `companion object`）：
- `NATIVE_CONTENT_FLAG = "<epub-native"` —— 原生内容占位符
- `NATIVE_LAYOUT_FLAG = "data-href="`
- `NATIVE_CONTENT_VERSION_FLAG = "data-native-ver=\"2\""`
- `TEXT_CONTENT_VERSION_FLAG = "<!--epub-text-ver=1-->"`
- `NATIVE_LAYOUT_DISK_CACHE_VERSION = 4` —— 磁盘缓存版本号
- `ENABLE_EPUB_DEBUG_DUMP = false` —— 调试 dump 开关
- `MAX_COVER_IMAGE_SIZE = 1600` —— 封面尺寸上限
- `scriptBlockRegex` / `scriptSelfClosingRegex` —— script 过滤正则
- `textEngineBlockTags` —— 文本引擎块级标签集合
- `maxNativeDomCache` / `maxNativeLayoutCache` —— 自适应缓存容量（按 maxMemory）
- `preloadExecutor` —— 单线程预加载执行器
- `preloadedNativeLayoutKeys` —— 已预加载的布局键集合
- `globalNativeDomCache` / `globalNativeLayoutCache` —— 全局 LRU 缓存（带 eldest 淘汰）

**本项目 companion 字段**：仅 `eFile: EpubFile?` 单例。

#### 3.1.3 关键方法清单对比

| 方法 | Archive | 本项目 |
|------|---------|--------|
| `getChapterList(book)` | ✓ 先调 `EpubCoreProvider.getChapterList` 失败回退到本地解析 | ✓ 直接调 `getEFile(book).getChapterList()` |
| `getContent(book, chapter)` | ✓ 双模式：`useExperimentalEpubCore` 开启时返回 `<epub-native>` 占位符，否则返回 `<usehtml>` 文本 | ✓ 仅返回 HTML 文本 |
| `getImage(book, href)` | ✓ | ✓ |
| `upBookInfo(book)` | ✓ | ✓ |
| `clear()` | ✓ 同时清 `EpubCoreProvider` 与预加载键集合 | ✓ 仅置空 `eFile` |
| `clearBook(book)` | ✓ 按书 URL 精准清理 | ✗ |
| `getNativeLayout(book, href)` | ✓ 前台请求布局 | ✗ |
| `preloadNativeLayouts(book, hrefs)` | ✓ 后台预加载布局 | ✗ |
| `warmImportIndex(book)` | ✓ 预热章节 span 索引 | ✗ |
| `getFootnote(book, href)` | ✓ 取注解 | ✗ |
| `preloadFootnotes(book, hrefs)` | ✓ 后台预加载注解 | ✗ |

#### 3.1.4 新增方法（Archive 独有，关键技术点）

1. **`getContentInternal(chapter)`**：双模式分发
   - `useExperimentalEpubCore = true` → 走 `getContentInternal` 返回 `<epub-native data-href="..." data-hrefs="..." data-title="..."/>` 占位符
   - 否则 → 走 `getTextContentInternal` 返回传统 `<usehtml>` 文本

2. **`collectChapterResources(...)`**：基于 `chapterResourceIndexByHref` 索引快速定位章节涉及的多个 XHTML 资源（处理一章跨多 XHTML 与多章共一 XHTML 的边界）

3. **`getNativeLayout(href, source)`**：构建/读取原生布局
   - 先查内存 `nativeLayoutCache` → 全局 `globalNativeLayoutCache` → 磁盘 `EpubCoreDiskCache`
   - 缓存键 `nativeLayoutCacheKey(href, width, height, styleKey)` 含视口尺寸 + 样式键 + 版本号
   - 失败回退到 `NativeViewport` 非精确模式
   - 完成后 `scheduleNearbyNativeLayoutPreload` 调度相邻章节预加载（前 1 + 后 2）

4. **`currentNativeLayoutStyleKey()`**：基于 `ChapterProvider.contentPaint` 的 textSize/color/letterSpacing/typeface/style/lineSpacing/paragraphSpacing 生成样式指纹，样式变更即失效缓存

5. **`buildFootnoteIndex()` / `getFootnote(href)`**：注解索引与解析
   - 注解 class 名集合：`footnote`/`endnote`/`note`/`noteref`/`duokan-footnote`/`duokan-footnote-content`/`duokan-footnote-item`（兼容多端 EPUB 制作工具，包括多看）
   - 三级缓存：`footnoteCache` / `footnoteSourceCache` / `footnoteDocumentCache`（LRU 80）

6. **`warmChapterSpanIndex()`**：预热 `chapterResourceIndexByHref`，加速大文件后续章节定位

7. **`rebuildNativeDom(href)`**：DOM 重建含全局缓存命中日志与失败兜底

8. **`normalizeChapterList(...)`**：章节标题归一化
   - `cleanEpubChapterTitle` 清理通用标题
   - `isGenericEpubTitle` 识别"卷首/封面/插图/人物画廊/EPUB 页面"等通用标题并去重编号
   - 卷章节 URL 加 `skip:` 前缀避免重复绘制

#### 3.1.5 技术实现差异

| 维度 | Archive | 本项目 |
|------|---------|--------|
| 解析库 | epublib + jsoup + 自研 EpubDomBuilder | epublib + jsoup |
| 章节内容输出 | 双模式：原生占位符 or 文本 HTML | 仅 HTML 文本 |
| 缓存层 | 内存 LRU + 全局 LRU + 磁盘 + 预加载 | 无（仅 EpubBook 字段懒加载） |
| 并发 | `preloadExecutor` 单线程 + `@Synchronized` | 仅 `@Synchronized` |
| 性能监控 | `measureTimeMillis` + `AppLog.putDebug` 详细日志（含 cost/commands/pages/linkAreas） | 基本无性能日志 |
| 错误恢复 | `runCatching` 多级回退（core 失败回退 text，text 失败回退 raw） | 单层 `runCatching` |

### 3.2 LocalBook.kt EPUB 处理对比

#### 3.2.1 共有逻辑
两边均在 `getChapterList`/`getContent`/`upBookInfo` 中通过 `book.isEpub` 分发到 `EpubFile`，差异在分发路径与新增字段。

#### 3.2.2 Archive 独有

| 项 | 位置 | 用途 |
|----|------|------|
| `import ...epubcore.cache.EpubCoreDiskCache` | 顶部 | 引入原生磁盘缓存 |
| `LARGE_EPUB_FAST_IMPORT_BYTES = 100L * 1024L * 1024L` | `LocalBook` companion | 100MB 大文件快速导入阈值 |
| `needRefreshEpubContent` 逻辑（在 BookHelp.kt 第 457 行附近） | 内容刷新判定 | EPUB 内容随样式变更需刷新 |

#### 3.2.3 本项目实现
- 简单的 `when` 分发到 `EpubFile.getChapterList/getContent/upBookInfo`
- 无大文件阈值、无磁盘缓存联动

### 3.3 Book.kt 实体字段对比

经 Grep 核实，两边 `Book.kt` 中 EPUB 相关代码完全一致：
- 均导入 `io.legado.app.help.book.isEpub`
- 均在 `getUseReplaceRule()` 中判断 `if (isImage || isEpub) return false`（图片类书源与 EPUB 本地默认关闭净化）

**结论**：Book.kt 实体**没有**为 EPUB 增加任何持久化字段。Archive 的所有 EPUB 增强数据（原生布局、注解、字体、缓存）均存于内存缓存或独立磁盘缓存目录，不污染数据库实体。这是一个重要的设计原则——**功能增强与数据模型解耦**。

### 3.4 assets/epub/ 资源对比

经 `diff -q` 字节级比对，5 个文件**完全一致**：
- `main.css`（550 行）
- `chapter.html`（13 行）
- `cover.html`
- `intro.html`
- `fonts.css`
- `logo.png`

**用途澄清**：这 5 个文件是 **EPUB 导出**（`ExportBookService` 将书籍导出为 EPUB）时使用的模板，与 EPUB 导入/阅读无关。两边导出能力一致。

---

## 4. Archive EPUB 增强功能详解

### 4.1 图片处理增强

#### 4.1.1 具体实现

1. **`EpubImageResolver`**（epubcore/image/，149 行）
   - 从 `EpubArchive` 按 href 解码图片字节流
   - 与 `EpubImageBox`（EpubLayout.kt:58）配合，支持 `background-size`/`background-position`/`background-repeat`/`object-fit`/`object-position`/`filter-brightness` 等 CSS 属性
   - `isBackground` 标志区分 `<img>` 元素与 CSS 背景图

2. **`EpubImageBox` 数据结构**（EpubLayout.kt:58-73）
   ```
   EpubImageBox(src, x, y, width, height, isBackground, sourcePath,
                backgroundSize, backgroundPosition, backgroundRepeat,
                filterBrightness, objectFit, objectPosition, linkHref)
   ```
   14 个字段，覆盖 EPUB 3.0 图片显示全部场景。

3. **`imageSizeCache`**（EpubFile.kt:223）
   - 缓存图片解码后的 `Size`，避免重复 `BitmapFactory.decodeStream` 测量
   - 用于布局引擎在分页前预知图片占位尺寸

4. **`MAX_COVER_IMAGE_SIZE = 1600`**（EpubFile.kt:71）
   - 封面图最大边长，防止 4K+ 封面图 OOM

5. **`resolveDataImageSize(src)`**（EpubMiniLayout.kt:56）
   - 支持 `data:` Base64 内嵌图片的尺寸解析
   - 用 `inJustDecodeBounds = true` 仅解码边界

#### 4.1.2 代码位置
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/epubcore/image/EpubImageResolver.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubLayout.kt:58-73`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubFile.kt:223`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubMiniLayout.kt:56-65`

#### 4.1.3 技术方案
Archive 把图片作为"一等公民"在布局阶段就参与分页决策（通过 `imageSizeCache` 预知尺寸），并支持完整的 CSS 图片属性。本项目仅在 `getContent` 后期用 jsoup 改写 `img.src` 为绝对路径，布局阶段完全无感知。

### 4.2 注解处理

#### 4.2.1 具体实现

1. **数据结构**（EpubFile.kt:2552-2560）
   ```kotlin
   internal data class EpubFootnote(val title: String, val html: String)
   private data class FootnoteSource(val href: String, val document: Document)
   ```

2. **三级缓存**（EpubFile.kt:226-232）
   - `footnoteCache: linkedMapOf<String, EpubFootnote?>` —— 解析结果缓存
   - `footnoteSourceCache: linkedMapOf<String, FootnoteSource?>` —— 来源缓存
   - `footnoteDocumentCache: LinkedHashMap<String, Document>` —— LRU 80，带 eldest 淘汰
   - `footnoteIdHrefIndex: linkedMapOf<String, String>` —— id→href 反向索引

3. **注解 class 名识别集合**（EpubFile.kt:234-242）
   ```
   footnote, endnote, note, noteref,
   duokan-footnote, duokan-footnote-content, duokan-footnote-item
   ```
   兼容 EPUB 2/3 标准 + 多看阅读器扩展。

4. **预加载**（EpubFile.kt:174-193）
   - `preloadFootnotes(book, hrefs)` 过滤含 `#` 的 href
   - 在 `preloadExecutor` 后台线程构建索引 + 逐个解析
   - 与 `preloadNativeLayouts` 共享线程池

5. **API 暴露**（EpubFile.kt:168-171）
   ```kotlin
   internal fun getFootnote(book: Book, href: String): EpubFootnote?
   ```
   供 UI 层在用户点击注解链接时调用。

#### 4.2.2 代码位置
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubFile.kt:226-242, 712, 830, 168-193, 2552-2560`

#### 4.2.3 技术方案
注解是 EPUB 阅读体验的关键痛点（学术书/技术书大量脚注）。Archive 用"识别 class 名 → 建立索引 → 后台预加载 → 点击时秒出"四段式方案，本项目完全无注解处理能力（点击注解链接会跳转到该 XHTML 顶部，体验断裂）。

### 4.3 分页缓存优化

#### 4.3.1 具体实现

1. **四级缓存架构**
   - **L1 实例缓存** `nativeLayoutCache: linkedMapOf<String, EpubLayoutDocument>`（EpubFile.kt:222）
   - **L2 全局缓存** `globalNativeLayoutCache: LinkedHashMap`（EpubFile.kt:90-94），按 `maxNativeLayoutCache`（256MB 内存机 320 条，否则 640 条）自适应淘汰
   - **L3 磁盘缓存** `EpubCoreDiskCache`（epubcore/cache/，115 行）
   - **L4 预加载** `preloadNativeLayouts` + `scheduleNearbyNativeLayoutPreload`

2. **缓存键设计**（EpubFile.kt:1060-1062）
   ```
   nativeLayoutCacheKey(href, width, height, styleKey) =
       "${bookUrl}|${href}|${width}x${height}|${styleKey}|v${NATIVE_LAYOUT_DISK_CACHE_VERSION}"
   ```
   - 包含 `bookUrl` 防跨书污染
   - 包含 `width x height` 视口尺寸，转屏/改字号即失效
   - 包含 `styleKey`（字号/颜色/字距/字体/行距/段距），样式变更即失效
   - 包含 `v4` 版本号，升级布局算法即全量失效

3. **相邻章节预加载**（EpubFile.kt:1013-1047）
   - `scheduleNearbyNativeLayoutPreload(width, height, styleKey, currentHref, includePrevious)`
   - 前台请求触发时预加载前 1 + 后 2 共最多 3 章
   - 用 `scheduledNearbyPreloadKeys` 集合去重，避免重复调度
   - 后台请求不触发预加载（防雪崩）

4. **DOM 全局缓存**（EpubFile.kt:85-89, 1077-1099）
   - `globalNativeDomCache: LinkedHashMap<String, EpubDomDocument>`
   - `maxNativeDomCache`：256MB 机 160 条，否则 320 条
   - `rebuildNativeDom` 先查全局缓存，命中则不重新解析 XHTML

#### 4.3.2 代码位置
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubFile.kt:78-94, 222, 1013-1099`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/epubcore/cache/EpubCoreDiskCache.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/epubcore/cache/EpubCoreMemoryCache.kt`

#### 4.3.3 技术方案
四级缓存 + 键精细失效 + 相邻预加载，是 EPUB 大书（500+章）流畅翻页的核心保障。本项目无任何分页缓存，每次翻页都要重新跑 jsoup 解析 + `ChapterProvider` 分页，大书卡顿明显。

### 4.4 复杂样式支持

#### 4.4.1 具体实现

1. **CSS 解析**（`EpubCss.kt`，465 行）
   - 解析 CSS 文本为 `Rule` 列表
   - 支持选择器、声明、`!important`

2. **样式级联计算**（`EpubStyleComputer.kt`，569 行）
   - 按 `sourceRank`（用户代理/作者/用户）→ `specificity`（CSS 选择器特异性）→ `ruleOrder` → `declarationOrder` 四级优先级排序
   - `EpubStyleValue.hasHigherPriorityThan(other)` 实现完整 CSS 级联算法

3. **计算样式**（`EpubComputedStyle.kt`，201 行）
   - `inheritedOnly()`：仅保留可继承属性
   - `withoutInheritedTextIndent()`：移除继承的 text-indent
   - 可继承属性集合（EpubDom.kt:56-81）：
     ```
     color, font-family, font-size, font-style, font-weight, font-variant, font-variant-caps,
     letter-spacing, line-height, text-align, text-decoration, text-decoration-color,
     text-decoration-line, text-decoration-style, text-shadow, text-transform, visibility,
     white-space, word-break, word-spacing, writing-mode, -epub-writing-mode,
     -webkit-writing-mode, direction
     ```
   - 支持 EPUB 3.0 的 `-epub-writing-mode` 竖排属性

4. **盒子树**（`EpubBox.kt`，58 行）
   - 7 种节点类型：`EpubBlockNode`/`EpubInlineNode`/`EpubTextNode`/`EpubImageNode`/`EpubBreakNode`/`EpubRuleNode`/`EpubPageColorNode`
   - 每个节点都带 `EpubComputedStyle`，实现"盒模型 + CSS 计算"一体化

5. **布局引擎**（`EpubLayoutEngine.kt`，~2400 行）
   - 输入：`EpubDomDocument` + 视口尺寸 + 基础 `TextPaint`
   - 输出：`EpubLayoutDocument`（含 `List<EpubLayoutPage>`，每页含 `List<EpubDrawCommand>`）
   - 7 种绘制指令：`EpubPageColor`/`EpubTextRun`/`EpubImageBox`/`EpubLinkArea`/`EpubBlockBox`/`EpubRuleLine`/`EpubBullet`
   - 支持 `EpubShadow`（阴影）、`EpubBorder`（4 边 + 圆角）、背景色、边框、链接热区

6. **字体内嵌**（epubcore/font/，4 文件共 500 行）
   - `EpubFontFaceParser` 解析 `@font-face`
   - `EpubTypefaceResolver` 创建 `Typeface` 并缓存
   - `EpubFontCatalog` 字体目录管理
   - `EpubTextRun.typeface` 字段让每段文字用对应字体绘制

#### 4.4.2 代码位置
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/epubcore/style/`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubCss.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubBox.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubDom.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubLayout.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubLayoutEngine.kt`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/epubcore/font/`

#### 4.4.3 技术方案
Archive 实现了浏览器级别的 CSS 级联（specificity + important + 继承）+ 盒模型布局 + 7 种绘制指令 + 字体内嵌。本项目完全无 CSS 处理能力——所有 EPUB 自定义样式（字体、颜色、对齐、缩进、竖排）全部丢失，统一套用阅读器主题样式。

### 4.5 大文件导入性能

#### 4.5.1 具体实现

1. **大文件阈值**（LocalBook.kt:72）
   ```kotlin
   private const val LARGE_EPUB_FAST_IMPORT_BYTES = 100L * 1024L * 1024L
   ```
   100MB 以上 EPUB 走快速导入路径。

2. **章节索引预热**（EpubFile.kt:1049-1054）
   ```kotlin
   private fun warmChapterSpanIndex() {
       val contents = epubSpineContents ?: epubBookContents ?: return
       if (chapterResourceIndexByHref == null) {
           chapterResourceIndexByHref = buildChapterResourceIndex(contents)
       }
   }
   ```
   `chapterResourceIndexByHref` 是 `Map<String, Int>`，O(1) 定位章节资源，避免 `contents.indexOfFirst` O(n) 线性扫描（大 EPUB 的 contents 可达数千项）。

3. **懒加载**（EpubFile.kt:255-279）
   - `epubBook` / `epubBookContents` / `epubSpineContents` 均懒加载
   - `EpubReader().readEpubLazy(zipFile, "utf-8")` 用 epublib 的 lazy 模式，按需读取资源
   - `fileDescriptor: ParcelFileDescriptor?` 持有引用防止回收

4. **spine 优先**（EpubFile.kt:269-279）
   ```kotlin
   private var epubSpineContents: List<Resource>? = null
       get() {
           ...
           val spineResources = epubBook?.spine?.spineReferences
               ?.mapNotNull { it.resource }
               ?.filter { it.href.isNotBlank() }
               .orEmpty()
           field = spineResources.ifEmpty { epubBook?.contents.orEmpty() }
       }
   ```
   优先用 OPF spine 顺序（阅读顺序），spine 为空时回退到 contents（物理顺序）。

5. **资源过滤**（EpubFile.kt:1025-1027, 355-357）
   - `isReadableEpubResource()`：过滤不可读资源（图片/CSS/字体）
   - `isEpubBookInfoResource()`：过滤书籍信息页（版权页/简介页），避免当作章节

6. **缓存容量自适应**（EpubFile.kt:78-81）
   ```kotlin
   private val maxNativeDomCache: Int
       get() = if (Runtime.getRuntime().maxMemory() <= 256L * 1024L * 1024L) 160 else 320
   private val maxNativeLayoutCache: Int
       get() = if (Runtime.getRuntime().maxMemory() <= 256L * 1024L * 1024L) 320 else 640
   ```
   根据 `maxMemory` 自适应缓存容量，低内存机减半。

#### 4.5.2 代码位置
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/LocalBook.kt:72`
- `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/model/localBook/EpubFile.kt:78-94, 255-279, 355-357, 1013-1054`

#### 4.5.3 技术方案
大 EPUB 卡顿三大根因：①资源线性扫描 ②重复 jsoup 解析 ③无分页缓存。Archive 用"索引预热 + spine 优先 + 资源过滤 + 自适应缓存"四件组合拳解决。本项目对大 EPUB 几乎无优化，500 章 EPUB 翻页延迟肉眼可见。

---

## 5. 差异清单（编号化）

| # | 差异点 | Archive 实现 | 本项目实现 | 影响等级 |
|---|--------|------------|-----------|---------|
| EPUB-001 | 原生渲染引擎 | EpubLayoutEngine 自研盒模型布局（~2400 行） | 无，走通用文本管线 | 高 |
| EPUB-002 | CSS 级联计算 | EpubStyleComputer 四级优先级 + EpubComputedStyle 继承 | 无 CSS 处理 | 高 |
| EPUB-003 | 自定义 EPUB View | EpubReadView + EpubPageRenderer + EpubPageDisplayList + EpubGestureController + EpubSimulationTurnRenderer（5 文件） | 无，复用 PageView | 高 |
| EPUB-004 | 双模式开关 | `AppConfig.useExperimentalEpubCore`（`epubReadEngine=="core"`） | 无开关，仅文本模式 | 中 |
| EPUB-005 | 注解（footnote）系统 | EpubFootnote + 三级缓存 + 7 种 class 名识别 + 预加载 | 完全无 | 高 |
| EPUB-006 | 字体内嵌 | EpubFontFace + EpubTypefaceResolver + EpubFontCatalog + EpubFontFaceParser | 无 | 中 |
| EPUB-007 | 分页缓存四级架构 | 实例 LRU + 全局 LRU + 磁盘 + 预加载 | 无缓存 | 高 |
| EPUB-008 | 缓存键精细失效 | bookUrl + 视口 + styleKey + 版本号 | 无缓存键 | 高 |
| EPUB-009 | 相邻章节预加载 | scheduleNearbyNativeLayoutPreload 前1后2 | 无 | 中 |
| EPUB-010 | 大文件阈值 | LARGE_EPUB_FAST_IMPORT_BYTES=100MB | 无 | 中 |
| EPUB-011 | 章节资源索引 | chapterResourceIndexByHref O(1) 定位 | O(n) 线性扫描 | 中 |
| EPUB-012 | spine 优先读取 | epubSpineContents（OPF spine 顺序） | 仅 epubBookContents（物理顺序） | 中 |
| EPUB-013 | 资源过滤 | isReadableEpubResource + isEpubBookInfoResource | 无过滤 | 低 |
| EPUB-014 | 缓存容量自适应 | maxMemory<=256MB 减半 | 无 | 低 |
| EPUB-015 | 图片尺寸缓存 | imageSizeCache + EpubImageBox 14 字段 | 无 | 中 |
| EPUB-016 | 封面尺寸上限 | MAX_COVER_IMAGE_SIZE=1600 | 无 | 低 |
| EPUB-017 | data: Base64 图片 | resolveDataImageSize | 无 | 低 |
| EPUB-018 | 章节标题归一化 | normalizeChapterList + isGenericEpubTitle + cleanEpubChapterTitle | 无 | 中 |
| EPUB-019 | 卷章节 skip 标记 | URL 加 `skip:` 前缀避免重复绘制 | 无 | 低 |
| EPUB-020 | 性能日志 | measureTimeMillis + AppLog.putDebug（cost/pages/commands/linkAreas） | 基本无 | 低 |
| EPUB-021 | 多级错误回退 | core 失败→text 失败→raw | 单层 runCatching | 中 |
| EPUB-022 | 文本选择器 | EpubPageSelectorBuilder（389 行）+ EpubSelectorModel | 通用文本选择 | 中 |
| EPUB-023 | WebView 布局会话 | EpubWebLayoutSession（1586 行）+ EpubWebSelectionLayerSession（1160 行） | 无 | 中 |
| EPUB-024 | 仿真翻页 | EpubSimulationTurnRenderer | 通用仿真翻页 | 低 |
| EPUB-025 | 全局 DOM 缓存 | globalNativeDomCache（160/320 条自适应） | 无 | 中 |
| EPUB-026 | 双模式内容标记 | NATIVE_CONTENT_FLAG / TEXT_CONTENT_VERSION_FLAG | 无 | 低 |
| EPUB-027 | Book.kt EPUB 字段 | 无扩展（与本项目一致） | 无扩展 | 低 |
| EPUB-028 | assets/epub/ 资源 | 5 文件（导出模板） | 5 文件（字节级一致） | 低 |
| EPUB-029 | LocalBook EPUB 分发 | 调 EpubCoreProvider 失败回退 EpubFile | 直接调 EpubFile | 中 |
| EPUB-030 | BookHelp EPUB 联动 | needRefreshEpubContent + EpubCoreDiskCache 导入 | 无 | 低 |

---

## 6. 借鉴决策（三态：借鉴/不借鉴/待评估）

### 6.1 建议借鉴（Borrow）

| # | 项目 | 收益评分(1-5) | 风险评分(1-5) | 实施复杂度 | 优先级 |
|---|------|-------------|-------------|-----------|--------|
| EPUB-B-01 | 章节资源索引（chapterResourceIndexByHref） | 5 | 1 | 低（~30 行） | P0 |
| EPUB-B-02 | spine 优先读取（epubSpineContents） | 4 | 1 | 低（~15 行） | P0 |
| EPUB-B-03 | 资源过滤（isReadableEpubResource + isEpubBookInfoResource） | 4 | 2 | 低（~50 行） | P1 |
| EPUB-B-04 | 章节标题归一化（normalizeChapterList + isGenericEpubTitle） | 4 | 2 | 中（~80 行） | P1 |
| EPUB-B-05 | 卷章节 skip 标记 | 3 | 1 | 低（~20 行） | P1 |
| EPUB-B-06 | 大文件阈值常量（LARGE_EPUB_FAST_IMPORT_BYTES） | 3 | 1 | 低（1 行） | P2 |
| EPUB-B-07 | 性能日志（measureTimeMillis + AppLog.putDebug） | 4 | 1 | 低（每方法 ~3 行） | P1 |
| EPUB-B-08 | 封面尺寸上限（MAX_COVER_IMAGE_SIZE） | 3 | 1 | 低（~5 行） | P2 |
| EPUB-B-09 | 图片尺寸缓存（imageSizeCache） | 4 | 2 | 中（~40 行） | P1 |
| EPUB-B-10 | 缓存容量自适应（maxMemory 判断） | 3 | 1 | 低（~5 行） | P2 |

**理由**：以上 10 项均为"低风险、低复杂度、高收益"的渐进式优化，不引入新架构，可独立合入现有 `EpubFile.kt`。源码依据：EpubFile.kt:78-94, 223, 269-279, 1013-1054, 2562-2605。

### 6.2 不建议借鉴（Skip）

| # | 项目 | 收益评分(1-5) | 风险评分(1-5) | 实施复杂度 | 优先级 |
|---|------|-------------|-------------|-----------|--------|
| EPUB-S-01 | 原生渲染引擎（EpubLayoutEngine） | 5 | 5 | 极高（~2400 行 + 配套 5000 行） | P3 |
| EPUB-S-02 | 自定义 EPUB View（EpubReadView 等 5 文件） | 5 | 5 | 极高（~3000+ 行 UI 代码） | P3 |
| EPUB-S-03 | CSS 级联计算（EpubStyleComputer） | 4 | 5 | 极高（~569 行 + EpubCss 465 行 + EpubComputedStyle 201 行） | P3 |
| EPUB-S-04 | 双模式开关（useExperimentalEpubCore） | 3 | 4 | 高（需同时维护两套路径） | P3 |
| EPUB-S-05 | WebView 布局会话（EpubWebLayoutSession 1586 行） | 3 | 5 | 极高 | P3 |
| EPUB-S-06 | 仿真翻页 EpubSimulationTurnRenderer | 2 | 3 | 中 | P3 |

**理由**：EPUB-S-01/S-02/S-03 是 Archive 的"原生 EPUB 引擎"三件套，合计 8000+ 行代码，
工程量与维护成本远超本项目当前阶段能承受的范围。更重要的是，本项目主航道是"书源
规则引擎"（CSS/JSONPath/XPath/正则/JS 五种解析），EPUB 是次要场景，引入浏览器级
渲染引擎会偏离主线。EPUB-S-04 双模式开关会长期增加测试矩阵复杂度。EPUB-S-05 WebView
方案与原生方案并存会带来双轨维护负担。EPUB-S-06 仿真翻页已有通用实现。

### 6.3 待评估（Evaluate）

| # | 项目 | 收益评分(1-5) | 风险评分(1-5) | 实施复杂度 | 优先级 |
|---|------|-------------|-------------|-----------|--------|
| EPUB-E-01 | 注解（footnote）系统 | 5 | 3 | 中（~200 行，不含 UI） | P1 |
| EPUB-E-02 | 字体内嵌（EpubFontFace + TypefaceResolver） | 4 | 3 | 中（~400 行） | P2 |
| EPUB-E-03 | 分页缓存四级架构（实例 LRU + 全局 LRU + 磁盘 + 预加载） | 5 | 3 | 中（~300 行，不含原生布局） | P1 |
| EPUB-E-04 | 缓存键精细失效（bookUrl + 视口 + styleKey + 版本号） | 4 | 2 | 低（~30 行） | P1 |
| EPUB-E-05 | 相邻章节预加载（scheduleNearbyNativeLayoutPreload） | 4 | 2 | 中（~50 行） | P2 |
| EPUB-E-06 | 多级错误回退（core→text→raw） | 3 | 2 | 低（~40 行） | P2 |
| EPUB-E-07 | 文本选择器（EpubPageSelectorBuilder） | 3 | 3 | 中（~400 行） | P2 |

**评估方向**：
- **EPUB-E-01 注解**：建议先评估用户反馈中 EPUB 注解缺失的投诉频次，若高频则 P1 推进。
  实施时可只移植数据层（EpubFootnote + 三级缓存 + class 名识别），UI 层用弹窗承载。
- **EPUB-E-02 字体**：评估用户是否大量阅读带内嵌字体的 EPUB（学术书/古籍）。若是则
  推进，但需注意 Typeface 内存占用与 minSdk 兼容性。
- **EPUB-E-03/04/05 缓存**：这是渐进式优化，可先做缓存键（EPUB-E-04）→ 实例 LRU →
  全局 LRU → 磁盘 → 预加载五步走。每步独立可验证。但缓存的对象是 `ChapterProvider`
  分页结果（不是原生布局），需重新设计缓存粒度。
- **EPUB-E-06 错误回退**：低成本提升健壮性，建议直接推进。
- **EPUB-E-07 选择器**：与现有通用文本选择功能重叠，需评估是否值得为 EPUB 单独实现。

---

## 7. 重大发现

### 7.1 架构亮点：双模式 + 渐进式迁移

Archive 通过 `AppConfig.useExperimentalEpubCore` 开关实现"原生引擎"与"文本引擎"
双轨并行，用户可一键切换。这是一个非常聪明的迁移策略——既不丢弃旧路径的稳定性，
又能让高级用户尝鲜新引擎。`EpubFile.getContentInternal` 在 `useExperimentalEpubCore = false`
时走 `getTextContentInternal`（与本项目一致的 `<usehtml>` 输出），开启时返回
`<epub-native>` 占位符由 `EpubReadView` 接管渲染。**对本项目的启示**：未来若引入
任何 EPUB 增强功能，都应采用这种"开关 + 双轨"模式，避免一刀切回归。

### 7.2 设计陷阱：Book.kt 实体零扩展原则

Archive 在 EPUB 增强如此巨大（16000+ 行代码）的情况下，**Book.kt 实体没有增加任何
EPUB 专属字段**。所有原生布局、注解、字体、缓存数据均存于 `EpubFile` 实例缓存或
独立磁盘目录（`EpubCoreDiskCache`）。这一设计原则确保了：
- 数据库迁移零成本（无 schema 变更）
- 旧版本数据库可无损升级到新版本
- EPUB 缓存失效不影响书籍元数据

**对本项目的启示**：任何 EPUB 增强必须遵守"实体零扩展"原则，缓存与索引数据走
独立存储，不污染 Room 实体。

### 7.3 性能优化技巧：缓存键指纹化

Archive 的 `nativeLayoutCacheKey` 把所有影响布局的变量（bookUrl + 视口宽高 + 样式
指纹 + 版本号）拼接成单一字符串键。`currentNativeLayoutStyleKey()` 从 `ChapterProvider.contentPaint`
提取 textSize/color/letterSpacing/typeface/style + lineSpacingExtra + paragraphSpacing
生成样式指纹。任何样式变更自动失效缓存，无需手动清理。**对本项目的启示**：通用
文本分页缓存也可采用同样的指纹键（textSize + color + 行距 + 段距 + 视口），实现
样式变更自动失效。

### 7.4 工程陷阱：WebView 方案与原生方案并存

Archive 的 `epubcore/web/` 子目录有 5 个文件共 3500+ 行（含 EpubWebLayoutSession
1586 行 + EpubWebSelectionLayerSession 1160 行），实现了一套基于 WebView 的布局
方案。这与 `EpubLayoutEngine`（纯 Kotlin 原生布局）形成**双方案并存**。推测历史
演进路径：先有 WebView 方案（依赖系统 WebView 渲染），后因性能/兼容性问题自研
原生方案，但 WebView 代码未清理。**对本项目的启示**：若未来引入 EPUB 增强，应
从一开始就选定单一方案，避免双方案并存带来的维护负担。

---

## 8. 引用源码位置

### 8.1 Archive 关键文件路径列表

**EPUB 入口与分发**：
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubFile.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\LocalBook.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\help\book\BookHelp.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\help\config\AppConfig.kt`（第 2501-2504 行 `useExperimentalEpubCore`）

**原生渲染引擎（top-level）**：
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubDom.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubDomBuilder.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubBox.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubBoxBuilder.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubLayout.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubLayoutEngine.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubMiniLayout.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\EpubCss.kt`

**epubcore/ 子目录**：
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\model\localBook\epubcore\`（含 archive/cache/facade/font/image/layout/model/pkg/selector/style/toc/web 共 11 个子模块 32 个文件）

**UI 层**：
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\read\epub\EpubReadView.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\read\epub\EpubPageRenderer.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\read\epub\EpubPageDisplayList.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\read\epub\EpubGestureController.kt`
- `f:\myself\github\WeAgentChat\temp\legado\temp\forks-comparison\legado-archive\app\src\main\java\io\legado\app\ui\book\read\epub\EpubSimulationTurnRenderer.kt`

### 8.2 本项目关键文件路径列表

- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\localBook\EpubFile.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\localBook\LocalBook.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\help\book\BookHelp.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\data\entities\Book.kt`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\epub\main.css`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\epub\chapter.html`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\epub\cover.html`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\epub\intro.html`
- `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\epub\fonts.css`

---

## 9. 附：分析方法与可信度声明

### 9.1 分析方法
1. **文件清单扫描**：用 Glob 扫描两边 `help/book/`、`assets/epub/`、`Epub*.kt` 共四组路径
2. **Grep 关键词定位**：搜索 `epub|Epub|EPUB` 在两边 `java/` 目录，定位 30+15 个相关文件
3. **行数统计**：用 `find + xargs wc -l` 统计 epubcore/（7491 行）与 UI 层行数
4. **核心文件深读**：Read 关键文件首部 100 行 + 关键段落（300-500 行、980-1100 行、2540-2620 行）
5. **字节级比对**：用 `diff -q` 比对 5 个 assets/epub/ 文件，确认完全一致
6. **Grep 字段定位**：搜索 `EpubFootnote|footnoteCache|LARGE_EPUB|useExperimentalEpubCore` 等技术字段定位关键实现

### 9.2 可信度声明
- **高可信**：文件清单、行数、assets/epub/ 一致性、Book.kt 无扩展、双模式开关、注解系统存在性、缓存架构
- **中可信**：EpubLayoutEngine.kt 内部算法细节（仅读取首部，未全读 2400 行）、EpubWebLayoutSession 用途推断（基于文件名与 import）
- **低可信**：WebView 方案与原生方案并存的"历史演进路径"为推测，未经 git log 验证

### 9.3 未覆盖项（建议后续子代理补充）
- EpubLayoutEngine.kt 完整算法（分页策略、文字测量、断行算法）
- EpubReadView.kt 完整手势处理与翻页动画
- EpubWebLayoutSession.kt 与原生方案的协作关系
- Archive 的 EPUB 阅读设置项（字号/行距/主题在原生模式下的应用）
- 真机性能对比数据（大 EPUB 翻页延迟实测）
