# Spec: 图片浏览器 Activity 化改造

## Intent

将 RSS 图片订阅源（`type == 1`）的详情展示从 **PhotoDialog 单图弹出框** 改造为 **ImageGalleryActivity 多图浏览 Activity**，支持图集内左右滑动、跨文章上下切换、双指缩放、长按保存等复杂交互。

## Scope

### In Scope（本次实现）

1. 新建 `ImageGalleryActivity` + ViewModel + 布局文件
2. 改造 `ReadRss.readNoHtml()`：`type == 1` 时启动 `ImageGalleryActivity` 而非 `PhotoDialog`
3. 支持图集内多图左右滑动（ViewPager2）
4. 支持跨文章上下切换（复用 `VideoPlay.rssArticles` 机制）
5. 支持双指缩放（PhotoView 已有能力）
6. 支持长按保存图片到本地
7. 多图URL解析：`ruleContent` 返回的 body 按换行符分隔为图片URL列表
8. 在 `AndroidManifest.xml` 注册新 Activity

### Out of Scope（不在本次实现）

1. **不改 PhotoDialog 的单图查看用途**：保留 PhotoDialog 用于验证码、书籍插图、文本内图片点击等单图场景
2. **不改 articleStyle 列表布局**：列表页的 `articleStyle == 2` GridLayoutManager 保持不变
3. **不改 ruleContent 解析逻辑**：`Rss.getContentAwait()` 仍返回 String，由调用方 split
4. **不实现图片编辑功能**：裁剪、滤镜等不在范围
5. **不实现离线下载图集**：仅支持在线浏览

## Approach

### Selected Approach: 新建 ImageGalleryActivity（参考 VideoPlayerActivity 架构）

**核心理由**：
- 视频播放器已经成功用 Activity + ViewPager2 实现了"图集内切换 + 跨文章切换"的模式，图片浏览可以完全复用这一架构
- Activity 模式支持更复杂的交互（菜单、手势、状态管理），Dialog 模式受限
- 与项目现有架构一致（web→ReadRssActivity、视频→VideoPlayerActivity、图片→ImageGalleryActivity）

### Alternatives Considered

| 替代方案 | 描述 | 否决理由 |
|---------|------|---------|
| 方案B: 改造 PhotoDialog 支持多图 | 在 PhotoDialog 内加 ViewPager2，构造函数接收 `List<String>` | Dialog 受窗口大小限制，无法全屏沉浸；生命周期管理复杂；与视频/网页架构不一致；PhotoDialog 在多处用作单图查看，改动影响面大 |
| 方案C: 用 ReadRssActivity 显示图片 | 在 ReadRssActivity（web Activity）中加分支处理 type==1 | ReadRssActivity 是 WebView 容器，图片浏览用 PhotoView 更合适；混用 WebView + PhotoView 会导致架构混乱 |
| 方案D: 用系统图片查看器 Intent | 调用 `ACTION_VIEW` + FileProvider | 无法支持跨文章切换、无法预加载、用户体验割裂 |

### Drawbacks

1. **代码量增加**：新增 1 个 Activity + 1 个 ViewModel + 布局文件，约 600-800 行代码
2. **维护成本**：图片浏览 Activity 与视频播放 Activity 有相似但不完全相同的逻辑（如 ViewPager2 上下切换），可能存在代码重复
3. **PhotoDialog 保留**：PhotoDialog 仍用于单图场景，存在两套图片查看逻辑

### Prior Art

- **VideoPlayerActivity**：本项目视频播放器，已实现 ViewPager2 上下滑动切换文章 + 多线路多集，是本次改造的直接参考
- **ReadRssActivity**：本项目 RSS 网页阅读 Activity，type==0 时启动

## Requirements

### R1: 多图浏览核心功能

- **R1.1** `ImageGalleryActivity` 必须支持接收图片URL列表（`ArrayList<String>`）
- **R1.2** 必须支持 ViewPager2 左右滑动切换图片
- **R1.3** 必须支持双指缩放（复用 `PhotoView` 组件）
- **R1.4** 必须显示当前页码 / 总页数（如 "3 / 29"）
- **R1.5** 长按图片必须弹出菜单：保存图片、分享图片、复制URL

### R1b: 图片查看器常规操作（用户2026-07-25反馈强化）

- **R1b.1** **放大**：双指张开放大图片（PhotoView 已有能力）
- **R1b.2** **缩小**：双指捏合缩小图片（PhotoView 已有能力）
- **R1b.3** **双击切换缩放级别**：双击在 1x / 2x / 4x 间切换（PhotoView 已有能力）
- **R1b.4** **平移**：放大后拖动图片查看细节（PhotoView 已有能力）
- **R1b.5** **顺时针旋转 90°**：点击"顺时针旋转"按钮，图片旋转 90°（需新增）
- **R1b.6** **逆时针旋转 90°**：点击"逆时针旋转"按钮，图片旋转 -90°（需新增）
- **R1b.7** **重置视图**：点击"重置"按钮，恢复旋转和缩放到默认状态（0° + 1x）（需新增）
- **R1b.8** **旋转状态记忆**：旋转角度在翻页后重置（每张图独立旋转状态，不跨图继承）
- **R1b.9** 旋转按钮必须显示在工具栏（顶部或底部），点击切换显隐（与沉浸式联动）
- **R1b.10** 旋转操作不影响 ViewPager2 翻页（旋转手势用按钮触发，避免与双指缩放/翻页冲突）

### R2: 跨文章切换

- **R2.1** 必须支持接收文章列表 `rssArticles: List<RssArticle>` 和当前文章索引
- **R2.2** 上下滑动（或左右滑动到边界继续滑动）切换到上/下一篇文章
- **R2.3** 切换文章时必须重新加载该文章的图集（调用 `Rss.getContentAwait`）
- **R2.4** 切换文章时必须显示加载进度

### R3: 入口改造

- **R3.1** `ReadRss.readNoHtml()` 中 `type == 1` 改为启动 `ImageGalleryActivity`（不再用 PhotoDialog）
- **R3.2** 必须传递 `rssArticles` 列表和当前索引（复用 VideoPlay 机制或新建 ImagePlay 单例）
- **R3.3** 必须传递 `sortName`、`sortUrl`、`nextPageUrl`、`page` 支持分页加载
- **R3.4** `ruleContent` 为空时（直接用 article.link 作为图片URL），仍走单图逻辑（可保留 PhotoDialog 或在 Activity 内处理）

### R4: 多图URL解析

- **R4.1** `Rss.getContentAwait()` 返回的 body 按换行符 `\n` split 为图片URL列表
- **R4.2** 每个URL用 `NetworkUtils.getAbsoluteURL()` 转为绝对URL
- **R4.3** 过滤空URL和无效URL
- **R4.4** 如果解析后只有1张图片，仍用 ImageGalleryActivity（保持入口一致），但隐藏页码

### R5: 用户体验

- **R5.1** 加载图片时显示进度指示器
- **R5.2** 加载失败时显示错误占位图 + 重试按钮
- **R5.3** 支持沉浸式全屏（隐藏状态栏和导航栏，点击切换）
- **R5.4** 支持屏幕旋转（横屏适配）

### R6: 兼容性

- **R6.1** 不影响 PhotoDialog 现有用途（验证码、书籍插图、文本图片点击）
- **R6.2** 不影响 type==0（web）和 type==2（视频）的现有逻辑
- **R6.3** 不影响 articleStyle 列表布局（1/2/3/4 四种样式保持不变）

## Scenarios

### Scenario 1: 单篇文章多图浏览（主流程）

1. 用户打开"站点D图片"订阅源
2. 列表加载4篇文章（articleStyle=2 网格布局）
3. 用户点击第1篇文章
4. App 调用 `Rss.getContentAwait()` 获取详情页内容
5. `ruleContent: ".entry-content img@src"` 返回 29 张图片URL（换行分隔）
6. App 启动 `ImageGalleryActivity`，传递 29 张图片URL
7. 用户左右滑动浏览 29 张图片
8. 页码显示 "1 / 29" → "2 / 29" → ...
9. 用户双指缩放放大图片
10. 用户长按图片，弹出菜单：保存、分享、复制URL

### Scenario 2: 跨文章切换

1. 承接 Scenario 1，用户浏览完第1篇文章的 29 张图片
2. 用户在最后一张图片继续向左滑动（或上滑）
3. App 加载第2篇文章的内容
4. 显示加载进度
5. 加载完成后显示第2篇文章的图集
6. 页码重置为 "1 / N"

### Scenario 3: ruleContent 为空（单图直链）

1. 某订阅源 `ruleContent` 为空，`article.link` 直接是图片URL
2. 用户点击文章
3. App 检测 `ruleContent` 为空，直接用 `article.link` 作为图片URL
4. 启动 `ImageGalleryActivity`，传递单张图片URL
5. 隐藏页码（只有1张图）
6. 用户仍可双指缩放、长按保存

### Scenario 4: PhotoDialog 保留场景（不影响）

1. 用户在阅读电子书时点击书内插图
2. App 调用 `showDialogFragment(PhotoDialog(src, isBook = true))`
3. 弹出 PhotoDialog 显示单张图片（与本次改造无关）
4. 用户点击外部关闭

### Scenario 5: 加载失败

1. 用户点击文章
2. `Rss.getContentAwait()` 抛出异常（网络错误、CF拦截等）
3. App 显示错误提示 "加载失败"
4. 提供重试按钮
5. 用户点击重试，重新加载
