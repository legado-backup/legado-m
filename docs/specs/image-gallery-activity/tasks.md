# Tasks: 图片浏览器 Activity 化改造

## 1. 准备工作

- [ ] 1.1 阅读 VideoPlayerActivity 架构（ViewPager2 嵌套、VideoPlay 单例、rssArticles 传递）
- [ ] 1.2 阅读 PhotoDialog 现有实现（确认保留场景：验证码/书籍插图/文本图片）
- [ ] 1.3 阅读 ReadRss.readNoHtml 现有逻辑（type==1 分支）
- [ ] 1.4 阅读 RssArticlesFragment.readRss（确认 rssArticles 传递方式）
- [ ] 1.5 确认 Rss.getContentAwait 返回格式（多图URL换行分隔）

## 2. 核心实现：新建 ImageGalleryActivity

- [ ] 2.1 新建 `ImagePlay.kt` 单例（字段对齐 VideoPlay：rssArticles/rssArticleIndex/rssSortName/rssSortUrl/rssNextPageUrl/rssArticlePage/rssArticlesHasMore/lastPlayedArticleLink）
- [ ] 2.2 新建 `ImageGalleryViewModel.kt`（持有文章列表、当前文章索引、当前图片URL列表；提供 loadArticleContent 方法）
- [ ] 2.3 新建 `activity_image_gallery.xml` 布局（外层 ViewPager2 垂直 + 页码 TextView + 加载进度 ProgressBar + 错误重试按钮 + 底部旋转工具栏含顺时针/逆时针/重置3按钮）
- [ ] 2.4 新建 `item_image_article.xml` 布局（内层 ViewPager2 水平 + 加载进度）
- [ ] 2.5 新建 `item_image_page.xml` 布局（PhotoView 全屏）
- [ ] 2.6 新建 `ImageArticlePagerAdapter.kt`（外层适配器，跨文章切换，参考 VideoArticlePagerAdapter）
- [ ] 2.7 新建 `ImagePageAdapter.kt`（内层适配器，图集内多图切换，PhotoView + Glide 加载）
- [ ] 2.8 实现 `ImageGalleryActivity.kt` 主类（绑定 ViewModel + ViewPager2 初始化 + 沉浸式全屏 + 点击切换 UI）
- [ ] 2.9 实现页码显示（"当前 / 总数"，单图时隐藏）
- [ ] 2.10 实现长按菜单（保存图片、分享图片、复制URL）
- [ ] 2.11 实现旋转工具栏（顺时针旋转 / 逆时针旋转 / 重置视图 3个按钮）
- [ ] 2.12 实现顺时针旋转 90°（photoView.rotation = (rotationDegree + 90) % 360）
- [ ] 2.13 实现逆时针旋转 90°（photoView.rotation = (rotationDegree + 270) % 360）
- [ ] 2.14 实现重置视图（rotation=0 + scale=1f）
- [ ] 2.15 实现旋转状态翻页重置（每张图独立，不跨图继承）
- [ ] 2.16 旋转工具栏与沉浸式联动（点击切换显隐，旋转按钮随工具栏显隐）

## 3. 入口改造：ReadRss.readNoHtml

- [ ] 3.1 修改 `ReadRss.readNoHtml()` Fragment 版：type==1 时启动 ImageGalleryActivity 而非 PhotoDialog
- [ ] 3.2 修改 `ReadRss.readNoHtml()` Activity 版：同上
- [ ] 3.3 实现多图URL解析：body split "\n" → URL 列表 → NetworkUtils.getAbsoluteURL → 过滤空URL
- [ ] 3.4 ruleContent 为空时：用 article.link 作为单图URL，仍启动 ImageGalleryActivity
- [ ] 3.5 设置 ImagePlay 单例（rssArticles/rssArticleIndex/rssSortName/rssSortUrl/rssNextPageUrl/rssArticlePage/rssArticlesHasMore）

## 4. RssArticlesFragment 改造

- [ ] 4.1 修改 `RssArticlesFragment.readRss()`：调用 ReadRss.readRss 时传递 rssArticles 列表（已支持，确认即可）
- [ ] 4.2 实现 onResume 位置记忆：检查 `ImagePlay.lastPlayedArticleLink` 并滚动到对应位置（参考 VideoPlay 逻辑）

## 5. 跨文章切换

- [ ] 5.1 在 ImageGalleryViewModel 实现 `loadArticleContent(article: RssArticle)`：调用 Rss.getContentAwait 获取 body
- [ ] 5.2 实现 body 解析为图片URL列表（split 换行符 + getAbsoluteURL + 过滤）
- [ ] 5.3 实现外层 ViewPager2 切换监听：切换时加载新文章图集
- [ ] 5.4 实现加载进度显示（切换文章时显示 ProgressBar）
- [ ] 5.5 实现加载失败处理（错误提示 + 重试按钮）

## 6. AndroidManifest 注册

- [ ] 6.1 在 AndroidManifest.xml 注册 ImageGalleryActivity

## 7. 验证

- [ ] 7.1 编译通过（./gradlew assembleDebug）
- [ ] 7.2 真机测试：站点D图片订阅源（多图浏览主流程）
- [ ] 7.3 真机测试：左右滑动切换图片（图集内）
- [ ] 7.4 真机测试：上下滑动切换文章（跨文章）
- [ ] 7.5 真机测试：双指缩放
- [ ] 7.6 真机测试：长按保存图片
- [ ] 7.7 真机测试：页码显示
- [ ] 7.8 真机测试：沉浸式全屏切换
- [ ] 7.9 真机测试：顺时针旋转 90°（点击按钮，图片旋转，布局不裁剪）
- [ ] 7.10 真机测试：逆时针旋转 90°（点击按钮，图片旋转，布局不裁剪）
- [ ] 7.11 真机测试：重置视图（旋转+缩放恢复默认）
- [ ] 7.12 真机测试：旋转状态翻页重置（翻页后新图 rotation=0）
- [ ] 7.13 真机测试：旋转工具栏显隐（点击切换沉浸式时同步显隐）
- [ ] 7.14 回归测试：PhotoDialog 单图场景不受影响（验证码、书籍插图）
- [ ] 7.15 回归测试：type==0（web）和 type==2（视频）不受影响

## 8. 文档同步

- [ ] 8.1 更新 `assets/updateLog.md`（基于 git diff 分析真实代码变更）
- [ ] 8.2 更新 `docs/project-flow/task-navigation.md`（新增 Image 模块代码锚点）
- [ ] 8.3 更新 `docs/INDEX.md`（移动到"已完成的功能"）

## AOAdapt 日志

> 在实施过程中记录遇到的问题及调整

（待实施时填写）
