# L-D6 RSS 网页阅读（ReadRss）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P2-reader.md`（S4 详情/阅读页，正文引擎零改动红线 AD-02），本文只写「继承 + 差异」。开发本页只读本文档 + P2 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：ReadRssActivity + ReadRss（`ui/rss/read/`，View，WebViewPool PooledWebView）
- **所属族文档**：`pages/P2-reader.md`
- **骨架归类**：S4 详情/阅读页（WebView 渲染）
- **对应 task**：tasks.md `12.4A`；pages-inventory D6（优先级 P2）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S4 详情/阅读页（见 P2 §2）：顶栏 + 正文层 + 菜单层（scrim + 底栏）
- 复用组件（§3.4）：`GlassTopAppBar`/`MenuTitleBar`、`AppModalBottomSheet`、`AppTextDialog`、`AppEditDialog`
- 复用状态范式：正文层零改动红线；菜单层 AnimatedVisibility 浮现；BackHandler 优先级链
- 差异点：正文引擎为 **WebView**（非 Canvas ReadView），P2 的 page/ 正文零改动不适用本页（WebView 池化复用）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 渲染 | WebView 三通道：contentLiveData clHtml+style / urlLiveData UA+header+Cookie / htmlLiveData loadWithBaseUrl | 独有 |
| 拦截 | 网页拦截：preloadJs 注入 JS_URL + 白黑名单 SourceContentFilter.filterUrl + legado/yuedu scheme→OnLineImport + 其他外部打开 | 独有 |
| JS 接口 | nameBasic / nameJava / nameSource / nameCache | 独有 |
| 菜单 | 刷新 refreshNameList 去重重开 / 收藏 RssFavoritesDialog 编辑标题分组 / 分享 / 朗读 TTS 抓 outerHTML+Jsoup textArray / 登录 / 浏览器打开 / 阅读记录 / 换源（仅多源）/ 编辑源 / 日志 | 独有 |
| 功能点 | 全屏视频 customWebView + toggleSystemBar + keepScreenOn；网页日志；智能返回（refreshNameList 跳过刷新页）；图片长按保存/选目录 + 下载监听 | 独有 |
| 路由 | ReadRss：type 2→VideoPlayer / 1→ImageGallery / 0→ReadRss；历史入口 | 智能分发 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppModalBottomSheet` | L1 浮层面板容器 | 阅读设置/更多操作 |
| `AppTextDialog` | Markwon 渲染、内容 maxHeight 70% | 网页日志查看 |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp、destructive 确认钮 error | 换源/清记录确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | WebView 进度条 | WebView 加载态 |
| 空态/错误 | 加载失败分支 + 重试 | 网页加载失败分支 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；JS 接口与拦截逻辑属内核不迁移

## 6. 验收标准（轻量）

- [ ] 复用 S4 骨架 + WebView 三通道渲染，无私有复制组件
- [ ] 功能点对照 pages-inventory D6 无遗漏（菜单/三通道/拦截/JS 接口/全屏视频/日志/智能返回/图片长按）
- [ ] 路由 type 0/1/2 分发正确；三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory D6），task 12.4A
