# 图片浏览器 Activity 化改造（image-gallery-activity）

> 状态：✅ 设计完成 → 🔄 开发中
> 创建时间：2026-07-25
> 类型：功能优化 / 架构改造

## 功能概述

当前 RSS 订阅源类型为图片（`type == 1`）时，点击文章详情使用 `PhotoDialog`（DialogFragment）弹出**单张图片**，存在三个核心问题：

1. **不支持多图浏览**：`PhotoDialog` 构造函数只接收单个 `src: String`，布局只有一个 `PhotoView`，无法左右滑动切换多张图片
2. **弹出框而非新页面**：图片详情用 `showDialogFragment(PhotoDialog(url))` 弹出，不像视频/网页那样启动新 Activity，无法支持复杂交互（缩略图导航、双指缩放、长按保存、上下切换文章等）
3. **多图URL被当作单URL处理**：`ReadRss.readNoHtml()` 中 `Rss.getContent()` 返回的 body 可能是多图URL（换行分隔），但被 `NetworkUtils.getAbsoluteURL()` 当作单个URL处理

## 核心能力

- 新建 `ImageGalleryActivity`：独立图片浏览 Activity（参考 `VideoPlayerActivity` 架构）
- ViewPager2 左右滑动切换多张图片（图集内切换）
- 上下滑动切换文章（跨文章切换，复用 VideoPlay 的 rssArticles 机制）
- 双指缩放、长按保存、缩略图导航
- 保留 `PhotoDialog` 用于单图场景（验证码、书籍插图、文本内图片点击）

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（架构决策/数据流/文件变更） |
| [tasks.md](./tasks.md) | 任务清单（按 X.Y 格式） |

## 关联文档

- 视频播放器参考架构：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`
- 原 PhotoDialog 实现：`app/src/main/java/io/legado/app/ui/widget/dialog/PhotoDialog.kt`
- RSS 阅读 入口：`app/src/main/java/io/legado/app/ui/rss/read/ReadRss.kt`
- RSS 文章列表：`app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt`
