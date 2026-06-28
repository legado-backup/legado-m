# 前端架构 — Vue3 Web 管理界面

> 基于 Vue3 + Vite + VueRouter + Pinia 的 Web 管理界面，嵌入 APK assets 提供书架/阅读/书源管理功能。
> 源码目录：`modules/web/src/`

---

## 1. 整体架构

### 1.1 多入口（MPA）架构

前端采用**多页面应用（Multi-Page Application）**架构，每个功能域是独立的 Vue 应用实例：

```
pages/
├── bookshelf/
│   ├── index.html          # HTML 入口
│   └── main.js             # 书架入口 JS（创建 App + bookRouter + store）
└── source/
    ├── index.html          # HTML 入口
    └── main.js             # 源管理入口 JS（创建 App + sourceRouter + store）
```

| 入口 | 路由模块 | 可用路由 | 用途 |
|------|----------|----------|------|
| `pages/bookshelf/main.js` | `bookRouter` | `/` , `/chapter` | 书架 + 阅读 |
| `pages/source/main.js` | `sourceRouter` | `/bookSource` , `/rssSource` | 书源/RSS源编辑 |

两个入口共享 `App.vue`、`store/`、Element Plus 等模块，但使用**不同的路由实例**。`src/main.ts` 是 Vite 开发模式下的单一入口，合并了两个路由（`.flat()`）。

**bookshelf 入口独有**：监听 `useBookStore().isNight` 同步 Element Plus 的 `dark` CSS 类到 `<html>` 元素。

### 1.2 App.vue — 极简根组件

[App.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/App.vue)（仅 3 行）

```html
<template>
  <router-view></router-view>
</template>
```

App.vue 不含任何 `<script>` 或 `<style>` 块，仅作为 `<router-view>` 的容器。所有布局逻辑（导航栏、工具栏、主题样式）均下沉到各页面组件内部实现。每个 view 页面是**自包含**的：各自管理自己的导航栏、工具栏和主题样式。

### 1.3 整体架构图

```
main.ts / pages/*/main.js (入口)
  └── createApp(App).use(store).use(router).mount('#app')
       │
       └── App.vue (<router-view>)
            │
            ├── /  → BookShelf.vue (书架页)
            │        ├── 左侧导航栏 (260px) — 搜索框 / 最近阅读 / 连接状态
            │        └── 右侧书架区 — BookItems 卡片网格
            │
            ├── /chapter → BookChapter.vue (阅读页)
            │        ├── tool-bar (左侧 fixed 浮动) — 目录/设置/书架/跳顶/跳底
            │        ├── read-bar (右侧 fixed 浮动) — 上一章/下一章
            │        └── chapter (居中 670px) — ChapterContent 正文
            │
            └── /bookSource 或 /rssSource → SourceEditor.vue (源编辑器)
                     ├── 左侧: SourceTabForm (表单编辑，接收 config prop)
                     ├── 中间: ToolBar (操作按钮 + 快捷键)
                     └── 右侧: SourceTabTools (4个 el-tabs 页签)
```

---

## 2. 路由体系

### 2.1 路由模式

- **Hash 路由**：`createWebHashHistory()`
- 无嵌套路由，子路由模块扁平化合并（`[bookRoutes, sourceRoutes].flat()`）
- `afterEach` 导航守卫：路由 name 为 `'shelf'` 时设置 `document.title = '书架'`

### 2.2 路由表

| 路径 | name | 组件 | 加载方式 | 所属模块 |
|------|------|------|----------|----------|
| `/` | `shelf` | `BookShelf.vue` | 懒加载 `() => import(...)` | bookRouter |
| `/chapter` | `chapter` | `BookChapter.vue` | 懒加载 `() => import(...)` | bookRouter |
| `/bookSource` | `book-home` | `SourceEditor.vue` | 直接导入 | sourceRouter |
| `/rssSource` | `rss-home` | `SourceEditor.vue` | 直接导入 | sourceRouter |

**关键点**：`/bookSource` 和 `/rssSource` 共用同一个 `SourceEditor.vue` 组件，通过 URL 路径正则 `/bookSource/i` 判断是书源模式还是 RSS 源模式，自动切换不同的表单配置。

### 2.3 跨页面通信

| 方向 | 机制 | 传递数据 |
|------|------|----------|
| 书架 → 章节 | `sessionStorage` | `bookUrl`, `bookName`, `bookAuthor`, `chapterIndex`, `chapterPos`, `isSeachBook` |
| 全局共享 | Pinia store | `isNight`, `shelf`, `config`, `readingBook`, `catalog` 等 |
| 持久化 | `localStorage` | `readingRecent`（最近阅读）、`tabName`（源编辑器页签）、`remoteUrl`（后端地址） |

---

## 3. 页面功能详解

### 3.1 书架页（BookShelf.vue）

[BookShelf.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/BookShelf.vue)（488 行）

#### 布局

```
index-wrapper
├── navigation-wrapper (左侧导航栏, 260px 固定宽度)
│   ├── navigation-title-wrapper — 标题"阅读" + 副标题
│   ├── search-wrapper — el-input 搜索框 (@keyup.enter 在线搜索)
│   ├── bottom-wrapper
│   │   ├── recent-wrapper — 最近阅读标签 (el-tag)
│   │   └── setting-wrapper — 连接状态标签 (el-tag)
│   └── bottom-icons — GitHub 链接图标
└── shelf-wrapper (右侧书架, flex:1)
    └── book-items (BookItems 组件, 书籍卡片网格)
```

**移动端适配**：`@media max-width: 750px` 改为纵向布局，导航栏压缩为横排。

#### 核心功能

| 功能 | 实现方式 | 说明 |
|------|----------|------|
| 本地搜索 | `watchEffect` 监听 `searchWord`，按 `name`/`author` 过滤 `shelf` | 实时过滤，无浮层 |
| 在线搜索 | `@keyup.enter` 触发 `API.search()`（WebSocket），结果写入 `store.searchBooks` | 搜索中时屏蔽本地过滤 |
| 书籍点击 | emit `bookClick` → 父组件 `handleBookClick` → `toDetail()` → `router.push('/chapter')` | 搜索书先调 `API.saveBook()` 加入书架 |
| 最近阅读 | `localStorage('readingRecent')` 持久化 | 默认显示"尚无阅读记录" |
| 连接管理 | `setLegadoRetmoteUrl()` 弹出 `ElMessageBox.prompt` 输入后端地址 | 正则校验 → `API.getReadConfig()` 验证连通性 |
| 数据加载 | `loadShelf()` = `store.loadWebConfig()` + `store.saveBookProgress()` + `store.loadBookShelf()` | 缓存优先策略 |

#### 关键状态变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `books` | `shallowRef<Book[] \| SeachBook[]>` | 当前展示列表（书架或搜索结果），shallowRef 避免深层响应式开销 |
| `shelf` | `computed<Book[]>` | 书架数据，来自 store |
| `searchWord` | `ref<string>` | 搜索关键词 |
| `isSearching` | `ref<boolean>` | 是否正在在线搜索 |
| `readingRecent` | `ref<ReadingBook>` | 最近阅读书籍信息 |

---

### 3.2 章节阅读页（BookChapter.vue）

[BookChapter.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/BookChapter.vue)（770 行）

#### 布局

```
chapter-wrapper (点击切换工具栏显示)
├── tool-bar (左侧 fixed 浮动工具栏, left:50% + margin-left 负偏移)
│   └── tools
│       ├── PopCatalog (目录弹窗, el-popover)
│       ├── ReadSettings (阅读设置弹窗, el-popover)
│       ├── 返回书架按钮
│       ├── 跳到顶部按钮
│       └── 跳到底部按钮
├── read-bar (右侧 fixed 浮动工具栏, right:50% + margin-right 负偏移)
│   └── tools
│       ├── 上一章 (toPreChapter)
│       └── 下一章 (toNextChapter)
└── chapter (阅读内容区, margin:0 auto 居中, 默认 670px)
    └── content
        ├── top-bar (顶部锚点)
        ├── chapter-content (v-for 渲染多章, 支持无限滚动)
        ├── loading (IntersectionObserver 哨兵)
        └── bottom-bar (底部锚点)
```

**工具栏定位原理**：`fixed` + `left:50%` 居中，再通过 `margin-left` 负偏移向两侧推开。移动端（776px）工具栏改为全宽横排，内容区 `width: 100vw`。

#### 核心功能

| 功能 | 实现方式 | 说明 |
|------|----------|------|
| 章节加载 | `API.getBookContent(bookUrl, chapterIndex)` → 按 `\n+` 分割 | 两种模式：`reloadChapter=true`（切换章节：清空重置）vs `reloadChapter=false`（无限滚动：追加） |
| 无限滚动 | `IntersectionObserver` 监听底部哨兵 | `rootMargin: '-100% 0% 20% 0%'`，自动预加载下一章 |
| 键盘导航 | ArrowLeft/Right 翻章，ArrowUp/Down 滚动一屏 | 使用 `jump` 插件平滑动画 |
| 进度保存 | `saveBookProgressThrottle()` 60秒节流 + `visibilitychange` 页面隐藏时保存 | 兼容 Safari<14 |
| 进度追踪 | `ChapterContent` 的 `IntersectionObserver` 上报段落阅读位置 | emit `readedLengthChange` 事件 |
| 路由离开守卫 | `onBeforeRouteLeave` 中判断搜索书 → 弹窗确认是否加入书架 | 确认：保留书；取消：`API.deleteBook()` |
| 章节切换 | `v-if="showContent"` 先销毁旧内容再加载 | 确保 DOM 完全重置 |
| 图片代理 | 正则匹配 `<img>`，base64 直出，legado 格式走 `API.getProxyImageUrl` | 加载失败自动走代理 |

#### 关键状态变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `chapterData` | `ref<{index,content[],title}[]>` | 已加载的章节内容数组 |
| `showContent` | `Ref<boolean>` | 是否渲染章节内容（面向 store） |
| `chapterIndex` | `computed<number>` | 当前章节索引（双向绑定 store） |
| `chapterPos` | `computed<number>` | 章节内阅读位置（双向绑定 store） |
| `isSeachBook` | `computed<boolean>` | 是否为搜索书 |
| `noPoint` | `ref<boolean>` | 翻页按钮禁用态 |

#### 阅读进度恢复

`scrollToReadedLength(pos)` 通过 `chapterRef[0].scrollToReadedLength(pos)` 调用子组件方法，子组件内部使用二分查找段落索引 + `jump()` 平滑滚动。

---

### 3.3 源编辑器（SourceEditor.vue）

[SourceEditor.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/SourceEditor.vue)（43 行）

#### 布局

```html
<div class="editor">
  <source-tab-form class="left" :config="config" />   <!-- 左侧: 表单编辑 -->
  <tool-bar />                                           <!-- 中间: 工具栏 -->
  <source-tab-tools class="right" />                     <!-- 右侧: 4个Tab页签容器 -->
</div>
```

**三栏布局**：左侧表单（`flex:1`）+ 中间工具栏 + 右侧工具面板（`flex:1`, 360px），全屏高度（`100vh`），隐藏溢出。

#### 书源/RSS源双模式

通过 URL 路径正则 `/bookSource/i` 判断当前模式：

| 模式 | 条件 | 配置来源 | 标题 |
|------|------|----------|------|
| 书源 | `/bookSource` | `bookSourceConfig`（7组表单） | '书源管理' |
| RSS源 | `/rssSource` | `rssSourceConfig`（5组表单） | '订阅源管理' |

通过 `provide('isBookSource', isBookSource)` 向子孙组件注入类型信息，避免 prop drilling。

#### 右侧 SourceTabTools 的 4 个页签

| 页签 | 组件 | 说明 |
|------|------|------|
| 编辑源 | `<source-json>` | JSON 文本编辑，双向绑定 `store.editTabSource` |
| 调试源 | `<source-debug>` | 搜索调试 + SSE 流式日志输出 |
| 源列表 | `<source-list>` | 虚拟列表 + 导入导出 + 批量删除 |
| 帮助信息 | `<source-help>` | 规则语法帮助链接（10个 `el-link`） |

#### 中间 ToolBar 功能

| 按钮 | 操作 | 说明 |
|------|------|------|
| 拉取 | `API.getSources()` → `store.saveSources()` | 从 APP 拉取所有源 |
| 推送 | `API.saveSources(sources)` → 标记失败项 | 推送源到 APP |
| 转为表单 | `conver2Tab()` | 当前源 → 表单编辑页签 |
| 转为源 | `conver2Source()` | 表单编辑数据 → 当前源 |
| 撤销 | `store.editHistoryUndo()` | 最多50条历史 |
| 重做 | `store.editHistoryRedo()` | 最多50条历史 |
| 保存 | 校验 → `normalizeSource` → `API.saveSource` → `store.saveCurrentSource` | 含有效性校验 |
| 调试 | `store.startDebug()` | 切换到调试页签 |
| 快捷键 | `hotkeys-js` 库绑定 + 自定义录制 | 持久化到 localStorage |

---

## 4. 组件树

### 4.1 全部组件（13 个 .vue）

```
App.vue (<router-view>)
│
├── [路由 /] → BookShelf.vue
│   └── BookItems.vue × N  (CSS Grid 自适应列, 380px)
│
├── [路由 /chapter] → BookChapter.vue
│   ├── ChapterContent.vue × N  (v-for 多章渲染)
│   │     └── 内部: IntersectionObserver 段落追踪 + jump 平滑滚动
│   ├── PopCatalog.vue  (el-popover 弹窗)
│   │   └── CatalogItem.vue × N  (虚拟列表子项, PC端每项2个章节)
│   └── ReadSettings.vue  (el-popover 弹窗, 唯一使用处)
│
└── [路由 /bookSource 或 /rssSource] → SourceEditor.vue
    ├── SourceTabForm.vue  (左侧: 表单, 接收 config prop, 按类型分发控件)
    ├── ToolBar.vue  (中间: 操作按钮 + 快捷键弹窗)
    └── SourceTabTools.vue  (右侧: el-tabs 页签容器)
        ├── [Tab: 编辑源] → SourceJson.vue  (el-input textarea)
        ├── [Tab: 调试源] → SourceDebug.vue  (SSE 流式调试)
        ├── [Tab: 源列表] → SourceList.vue  (虚拟列表)
        │   └── SourceItem.vue × N  (虚拟列表子项, el-checkbox)
        └── [Tab: 帮助] → SourceHelp.vue  (10个帮助链接)
```

### 4.2 组件 Store 依赖

| 组件 | useSourceStore | useBookStore | inject('isBookSource') |
|------|:---:|:---:|:---:|
| ToolBar | ✓ | | |
| SourceTabTools | ✓ | | |
| SourceTabForm | ✓ | | |
| SourceList | ✓ | | |
| SourceJson | ✓ | | |
| SourceItem | ✓ | | |
| SourceDebug | ✓ | | |
| SourceHelp | | | ✓ |
| ReadSettings | | ✓ | |
| PopCatalog | | ✓ | |
| ChapterContent | | ✓ | |
| BookItems | | | |
| CatalogItem | | | |

---

## 5. 状态管理（Pinia）

### 5.1 bookStore — 书籍与阅读状态

**Store ID**: `'book'`

#### State

| 字段 | 类型 | 说明 |
|------|------|------|
| `searchBooks` | `SeachBook[]` | 搜索结果列表 |
| `shelf` | `Book[]` | 书架书籍列表 |
| `catalog` | `BookChapter[]` | 当前书籍章节目录 |
| `readingBook` | `BaseBook & { chapterPos, chapterIndex, isSeachBook? }` | 当前阅读书籍信息 |
| `popCataVisible` | `boolean` | 目录弹窗可见性 |
| `contentLoading` | `boolean` | 内容加载中 |
| `showContent` | `boolean` | 是否显示正文 |
| `config` | `webReadConfig` | 阅读配置（主题/字体/字号/间距等） |
| `miniInterface` | `boolean` | 迷你界面模式 |
| `readSettingsVisible` | `boolean` | 阅读设置面板可见性 |

#### 默认配置

```typescript
{
  theme: 0, fontSize: 18, readWidth: 800,
  infiniteLoading: false, customFontName: '',
  jumpDuration: 1000,
  spacing: { paragraph: 1, line: 0.8, letter: 0 }
}
```

#### 关键 Actions

| Action | 说明 |
|--------|------|
| `loadBookShelf()` | **缓存优先**：内存有数据则立即返回，同时异步更新；按 `durChapterTime` 降序排列 |
| `loadWebCatalog(book)` | **缓存优先**：`bookUrl` 匹配 + 目录已存在 + 索引有效则返回缓存 |
| `loadWebConfig()` | **仅加载一次**：通过模块级变量 `webReadConfigLoadedDate` 控制 |
| `setSearchBooks(books)` | 添加搜索结果，自动与书架比对 `bookUrl` 去重 |
| `saveBookProgress()` | 更新内存中 shelf 对应书籍进度 + `sendBeacon` 发送到后端 |

#### Getters

| Getter | 说明 |
|--------|------|
| `bookProgress` | 从 `readingBook` + `catalog` 计算当前阅读进度 |
| `theme` | 返回 `config.theme` |
| `isNight` | `config.theme == 6` 判定夜间模式 |

### 5.2 sourceStore — 书源/RSS源状态

**Store ID**: `'source'`

#### State

| 字段 | 类型 | 说明 |
|------|------|------|
| `bookSources` | `shallowRef(BookSoure[])` | 所有书源（shallowRef 包裹） |
| `rssSources` | `shallowRef(RssSource[])` | 所有订阅源（shallowRef 包裹） |
| `savedSources` | `Source[]` | 批量保存到后端成功的源 |
| `currentSource` | `Source` | 当前编辑的源（深拷贝） |
| `currentTab` | `string` | 当前 Tab 页（持久化到 `localStorage('tabName')`） |
| `editTabSource` | `Source` | 编辑 Tab 的序列化数据 |
| `isDebuging` | `boolean` | 是否正在调试 |

#### 编辑历史系统（双栈撤销/重做）

```typescript
editHistory: { new: Source[], old: Source[] }  // 各限制最多 50 条
```

| Action | 说明 |
|--------|------|
| `editHistory(source)` | `new` 栈 push，超过 50 条时 `shift()` |
| `editHistoryUndo()` | `old` 栈 push 当前源，`new` 栈 pop 恢复 |
| `editHistoryRedo()` | `new` 栈 push 当前源，`old` 栈 pop 恢复 |
| `clearAllHistory()` | 清空 `{ new:[], old:[] }` |

#### 关键 Actions

| Action | 说明 |
|--------|------|
| `saveSources(data)` | 根据 `isBookSource` 存入 `bookSources` 或 `rssSources`（`markRaw` 标记非响应式） |
| `saveCurrentSource()` | 保存当前源到 `sourcesMap`，再同步回 `sources` 数组 |
| `changeCurrentSource(source)` | 深拷贝切换当前编辑源 |
| `changeTabName(tabName)` | 切换 Tab 名称，持久化到 `localStorage('tabName')` |

#### Getters

| Getter | 说明 |
|--------|------|
| `sources` | 根据 `isBookSource` 返回 `bookSources` 或 `rssSources` |
| `sourcesMap` | 将 sources 转换为 `Map<string, Source>` |
| `savedSourcesMap` | 将 savedSources 转换为 `Map<string, Source>` |
| `currentSourceUrl` | 当前源唯一键：书源取 `bookSourceUrl`，订阅源取 `sourceUrl` |
| `searchKey` | 调试搜索关键词 |

### 5.3 connectionStore — 连接状态

**Store ID**: `'connection'`

| 字段 | 类型 | 说明 |
|------|------|------|
| `connectStatus` | `string` | 连接状态文本（默认"正在连接后端服务器……"） |
| `connectType` | `'primary' \| 'success' \| 'danger'` | 连接状态颜色类型 |
| `newConnect` | `boolean` | 是否为新连接（为 true 时忽略状态更新） |

---

## 6. API 层

### 6.1 axios 实例配置

- **baseURL** 三级优先级：`VITE_API` 环境变量 → `localStorage('remoteUrl')` → `location.origin`
- **timeout**：120 秒
- 单一实例，全局共享

### 6.2 HTTP API 函数清单（15 个）

| 函数 | 方法 | URL | 说明 |
|------|------|-----|------|
| `getReadConfig(http_url?)` | GET | `getReadConfig` | 获取阅读配置，超时 3s |
| `saveReadConfig(config)` | POST | `saveReadConfig` | 保存阅读配置 |
| `saveBookProgress(bookProgress)` | POST | `saveBookProgress` | ⚠️ 已废弃，推荐用 Beacon 版本 |
| `saveBookProgressWithBeacon(bookProgress)` | sendBeacon | `saveBookProgress` | 浏览器关闭时可靠发送 |
| `getBookShelf()` | GET | `getBookshelf` | 获取书架书籍列表 |
| `getChapterList(bookUrl)` | GET | `getChapterList?url=...` | 获取章节目录 |
| `getBookContent(bookUrl, chapterIndex)` | GET | `getBookContent?url=...&index=...` | 获取章节正文 |
| `saveBook(book)` | POST | `saveBook` | 添加书籍到书架 |
| `deleteBook(book)` | POST | `deleteBook` | 从书架删除书籍 |
| `getSources()` | GET | `getBookSources` 或 `getRssSources` | 按 `isBookSource` 动态选择端点 |
| `saveSource(data)` | POST | `saveBookSource` 或 `saveRssSource` | 保存单个源 |
| `saveSources(data)` | POST | `saveBookSources` 或 `saveRssSources` | 批量保存源 |
| `deleteSource(data)` | POST | `deleteBookSources` 或 `deleteRssSources` | 批量删除源 |
| `getProxyCoverUrl(coverUrl)` | — | `cover?path=...` | 构造封面代理 URL |
| `getProxyImageUrl(bookUrl, src, width)` | — | `image?path=...&url=...&width=...` | 构造图片代理 URL |

### 6.3 WebSocket API 函数（2 个）

| 函数 | WS 端点 | 发送数据 | 说明 |
|------|---------|----------|------|
| `search(searchKey, onReceive, onFinish)` | `searchBook` | `{"key":"..."}` | 搜索书籍，逐条接收结果 |
| `debug(sourceUrl, searchKey, onReceive, onFinish)` | `bookSourceDebug` 或 `rssSourceDebug` | `{"tag":"...","key":"..."}` | SSE 流式调试 |

**WebSocket 端口派生规则**：WS 端口 = HTTP 端口 + 1（默认 HTTP→81，HTTPS→444）；协议：HTTP→`ws://`，HTTPS→`wss://`。

### 6.4 拦截器

| 拦截器 | 行为 |
|--------|------|
| 响应拦截器 | 校验每个响应是否为 `LegadoApiResponse` 格式（含 `isSuccess`/`errorMsg`/`data`），校验失败弹出警告 |
| 错误拦截器 | 弹出"后端连接失败"提示，设置 `connectionStore.connectType = 'danger'` |
| WebSocket 消息回调 | 每次收到消息刷新连接状态为 `'已连接' + 入口地址` |

---

## 7. config/ — 配置体系

### 7.1 bookSourceEditConfig.ts（书源编辑表单，~608 行）

定义书源编辑界面的 **7 组表单字段**，结构为 `{ name: 分组名, children: 配置项[] }`：

| 分组 | key | 字段数 | 说明 |
|------|-----|--------|------|
| 基础 | `base` | 15 | 源类型/域名/名称/分组/注释/登录/请求头/并发率/js库等 |
| 搜索 | `search` | 10 | 搜索地址 + `namespace: 'ruleSearch'` 子规则 |
| 发现 | `find` | 10 | `exploreUrl` + `namespace: 'ruleExplore'` 子规则 |
| 详情 | `detail` | 11 | `namespace: 'ruleBookInfo'` 子规则 |
| 目录 | `directory` | 10 | `namespace: 'ruleToc'` 子规则 |
| 正文 | `content` | 11 | `namespace: 'ruleContent'` 子规则 |
| 其他 | `other` | ~10 | 布尔开关 + 权重/排序编号 |

单个配置项结构：`{ title, id, type: 'String'|'Array'|'Boolean'|'Number', array?, hint?, required?, namespace? }`

**段评组（review）已整体注释掉，状态：已废弃。**

### 7.2 rssSourceEditConfig.ts（RSS源编辑表单，~277 行）

定义 RSS 源编辑界面的 **5 组表单字段**：

| 分组 | key | 字段数 | 说明 |
|------|-----|--------|------|
| 基础 | `base` | 15 | 源域名/图标/名称/分组/注释/搜索/分类/登录/请求头等 |
| 启动 | `start` | 4 | 启动页 html/css/js + 预注入 JS |
| 列表 | `list` | 7 | 列表规则/翻页/标题/时间/描述/图片/链接 |
| WebView | `webView` | 6 | 内容规则/样式/注入JS/黑白名单/链接拦截 |
| 其他 | `other` | 10 | 源类型（网页/图片/视频）、列表样式、预加载等 |

**与 bookSourceEditConfig 关键差异**：RSS 没有 `namespace` 字段，所有规则平铺；多了 `start` 和 `webView` 分组。

### 7.3 themeConfig.ts（主题配置，~74 行）

```typescript
{
  themes: [  // 7个主题，每个含 body/content/popup 三区域
    { body: string, content: string, popup: string },  // 索引4为纯色，其余使用纹理图
  ],
  fonts: [  // 3种字体栈
    'Microsoft YaHei, PingFangSC-Regular, ...',  // 无衬线
    'PingFangSC-Regular, -apple-system, Simsun', // 混合
    'Kaiti',                                      // 楷体
  ]
}
```

### 7.4 sourceConfig.d.ts（配置类型定义）

```typescript
type SourceConfigRecord = {
  title: string          // 表单字段显示名
  type: string           // "Array" | "String" | "Boolean" | "Number"
  array?: string[]       // Array类型时的可选值列表
  hint?: string          // 提示文本
  required?: boolean     // 是否必填
  namespace?: Partial<keyof Source>   // 归类到的子规则命名空间
  id: Partial<keyof Source>           // 对应的源字段名
}
type SourceConfigValue = { name: string; children: SourceConfigRecord[] }
export type SourceConfig = Partial<Record<SourceConfigKey, SourceConfigValue>>
```

---

## 8. utils/ — 工具函数

### 8.1 utils.ts — 通用工具

| 函数 | 说明 |
|------|------|
| `isNullOrBlank(str)` | 判空：null/undefined/空串/纯空白 |
| `isLegadoUrl(url)` | 判断是否为 Legado 内部链接（非 http/data/blob 开头） |
| `validatorHttpUrl(url, protocols?)` | 验证合法 HTTP/HTTPS URL |
| `dateFormat(timestamp)` | 相对时间格式化：刚刚/N秒前/N分钟前/N小时前/N天前/YYYY-MM-DD |
| `lazyRegex(pattern, flags?)` | 懒初始化正则表达式工厂函数 |

### 8.2 souce.ts — 源数据工具（注意文件名拼写）

| 函数 | 说明 |
|------|------|
| `isBookSource(source)` | 类型守卫：通过 `'bookSourceName' in source` 区分书源/RSS源 |
| `isInvaildSource(source)` | 校验源是否**有效**（注意拼写 `Invaild`，实为"有效"判断） |
| `getSourceUniqueKey(source)` | 获取源唯一键：书源用 `bookSourceUrl`，RSS 用 `sourceUrl` |
| `getSourceName(source)` | 获取源名称 |
| `isSourceMatches(source, searchKey)` | 搜索匹配：在源名称/URL/分组/注释中搜索 |
| `convertSourcesToMap(sources)` | 批量转为 `Map<string, Source>` |
| `normalizeSource(source)` | 递归清除空值（空串/null/纯空白），原地修改 |
| `emptyBookSource` (常量) | 空书源模板 |
| `emptyRssSource` (常量) | 空 RSS 源模板 |

---

## 9. hooks/ — useLoading 组合式函数

[loading.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/hooks/loading.ts)（39 行）

封装 Element Plus `ElLoading.service`，提供：

```typescript
export const useLoading = (target, text, spinner?) => {
  // 返回: { isLoading, showLoading, closeLoading, loadingWrapper }
  // loadingWrapper(promise) — 将任意 Promise 包装为自动 loading 的版本
}
```

**核心机制**：通过 `watch(isLoading, ...)` 响应式控制 `ElLoading.service` 的创建/销毁。书架页和阅读页均使用 `useLoading` 管理加载状态。这是前端唯一的自定义 hook。

---

## 10. plugins/ — jump 平滑滚动动画引擎

[jump.js](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/plugins/jump.js)（~190 行）

**架构**：闭包模块模式 → 单例导出。

**核心 API**：
```typescript
jump(target: number | string | HTMLElement, options?: Options): void
```

**target 三种类型**：

| 类型 | 行为 |
|------|------|
| `number` | 从当前位置滚动 N 像素（正值向下） |
| `HTMLElement` | 滚动到元素位置（`getBoundingClientRect` 计算） |
| `string` | `document.querySelector` 定位元素后滚动 |

**options 配置**：

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `duration` | 1000ms | 动画时长 |
| `offset` | 0 | 停止位置偏移量 |
| `callback` | undefined | 滚动完成回调 |
| `easing` | `easeInOutQuad` | 缓动函数 |
| `container` | `window` | 滚动容器 |

使用 `requestAnimationFrame` 驱动逐帧滚动。在 `ChapterContent` 中用于恢复阅读进度时的平滑滚动；在 `BookChapter` 中用于键盘导航翻屏。

[jump.d.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/plugins/jump.d.ts) 提供 TypeScript 类型声明。

---

## 11. TypeScript 类型定义体系

### 11.1 book.d.ts — Book 类型体系

```
BaseBook { name, author, bookUrl, kind?, wordCount?, variable? }
  ├── Book — 书架/阅读完整书籍（tocUrl/origin/durChapterIndex/durChapterPos/readConfig等）
  │   └── BookChapter — 章节实体（url/title/isVolume/bookUrl/index/isVip等）
  ├── SeachBook — 搜索结果（注意命名拼写，比BaseBook多了origin/coverUrl/intro/tocUrl等）
  └── BookProgress — 阅读进度快照（Pick 子集）
```

### 11.2 source.d.ts — Source 类型体系

```
BaseSource { concurrentRate?, loginUrl?, loginUi?, header?, enabledCookieJar?, jsLib? }
  ├── BookSoure — 书源实体（bookSourceUrl主键/ruleSearch/ruleExplore/ruleBookInfo/ruleToc/ruleContent）
  └── RssSource — RSS源实体（sourceUrl主键/ruleArticles/ruleTitle/rulePubDate/sourceIcon等）

Source = BookSoure | RssSource
```

规则子类型：`RuleSearch` 定义为 `{ checkKeyWord?: string; [prop: string]: string }`，其余规则类型已注释为 `{ [prop: string]: string }` 映射。

### 11.3 web.d.ts — Web 阅读配置

```typescript
type webReadConfig = {
  theme: number           // 主题索引（对应 themeConfig.themes 数组）
  font: number            // 字体索引（对应 themeConfig.fonts 数组）
  fontSize: number        // 字体大小
  readWidth: number       // 阅读区域宽度
  infiniteLoading: boolean // 无限加载模式
  customFontName: string  // 自定义字体名
  jumpDuration: number    // 跳转动画时长
  spacing: {
    paragraph: number     // 段落间距
    line: number          // 行间距
    letter: number        // 字间距
  }
}
```

### 11.4 components.d.ts — 自动注册的全局组件（22 个）

由 `unplugin-vue-components` 自动生成。包含 13 个项目组件 + 9 个 Element Plus 组件（`ElButton`/`ElCheckbox`/`ElDialog`/`ElInput` 等）+ `RouterLink`/`RouterView`。

### 11.5 auto-imports.d.ts — 自动导入声明（~55 个）

由 `unplugin-auto-import` 自动生成。包含 Vue（`ref/reactive/computed/watch/onMounted/nextTick/inject/provide` 等）、Vue Router（`useRouter/useRoute/onBeforeRouteLeave` 等）、Pinia（`createPinia/defineStore/storeToRefs` 等）、Element Plus（`ElMessage/ElMessageBox`）、项目 Store（`useBookStore/useSourceStore/useConnectionStore`）。

---

## 12. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架 |
| Vite | 5.x | 构建工具 |
| Vue Router 4 | 4.x | Hash 路由（`createWebHashHistory`） |
| Pinia | 2.x | 状态管理（3 个 Store） |
| Element Plus | 2.x | UI 组件库（暗色模式 CSS 变量） |
| Axios | 1.x | HTTP 请求（120s 超时） |
| WebSocket API | 原生 | 实时搜索和调试通信 |
| `navigator.sendBeacon` | 原生 | 阅读进度可靠发送 |
| `@vueuse/core` | — | `useDark()` 暗色模式管理（SourceEditor.vue） |
| `unplugin-auto-import` | — | 自动导入 Vue/Pinia/Router API，无需手动 import |
| `unplugin-vue-components` | — | 自动注册 Element Plus 和项目组件的全局声明 |
| `vue3-virtual-scroll-list` | — | 源列表和目录的虚拟滚动（SourceList, PopCatalog） |
| `hotkeys-js` | — | ToolBar 快捷键绑定和自定义录制 |

---

## 13. 关键数据流

### 13.1 书架 → 阅读跳转

```
BookShelf.handleBookClick(book)
  → 判断 SeachBook vs Book（'respondTime' in book）
  → SeachBook → API.saveBook() 先加入书架
  → toDetail() → sessionStorage 写入 bookUrl/name/author/chapterIndex/chapterPos/isSeachBook
  → router.push('/chapter')
```

### 13.2 阅读进度保存

```
ChapterContent.onReadedLengthChange → emit('readedLengthChange', index, pos)
  → BookChapter.onReadedLengthChange
    → saveReadingBookProgressToBrowser() — 更新 Pinia + sessionStorage
    → saveBookProgressThrottle() — 60s 节流 → API.saveBookProgressWithBeacon()
```

### 13.3 无限滚动预加载

```
IntersectionObserver 监听底部 loading 哨兵
  → onReachBottom → loadMore()
    → 取 chapterData 最后一章 index
    → 未到目录末尾 → getContent(nextIndex, false) 预加载下一章
    → 追加到 chapterData
```

### 13.4 源编辑器数据流

```
ToolBar.pull() → API.getSources() → store.saveSources(data)
  → 根据 isBookSource 存入 bookSources 或 rssSources（markRaw）

ToolBar.saveSource() → isInvaildSource 校验 → normalizeSource 清空 → API.saveSource → store.saveCurrentSource

ToolBar.undo() → store.editHistoryUndo() → old栈push当前源, new栈pop恢复
```

### 13.5 暗色模式同步

```
main.ts / pages/bookshelf/main.js:
  watch(store.isNight, isNight => {
    isNight ? document.documentElement.classList.add('dark')
            : document.documentElement.classList.remove('dark')
  })

SourceEditor.vue:
  useDark() from @vueuse/core → 自动管理 dark class
```

---

## 14. 代码锚点

| 功能 | 文件 | 行号 |
|------|------|------|
| 根组件 | [App.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/App.vue) | L1-L3 |
| 开发入口 | [main.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/main.ts) | L1-L22 |
| 多入口-书架 | [pages/bookshelf/main.js](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/pages/bookshelf/main.js) | L1-L19 |
| 多入口-源管理 | [pages/source/main.js](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/pages/source/main.js) | L1-L7 |
| 路由总入口 | [router/index.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/router/index.ts) | L1-L15 |
| 书架路由 | [router/bookRouter.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/router/bookRouter.ts) | L4-L13 |
| 源路由 | [router/sourceRouter.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/router/sourceRouter.ts) | L5-L14 |
| 书架页 | [views/BookShelf.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/BookShelf.vue) | L1-L488 |
| 阅读页 | [views/BookChapter.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/BookChapter.vue) | L1-L770 |
| 源编辑器 | [views/SourceEditor.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/views/SourceEditor.vue) | L1-L43 |
| 工具栏 | [components/ToolBar.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/ToolBar.vue) | L1-L303 |
| 源表单 | [components/SourceTabForm.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceTabForm.vue) | L1-L70 |
| 源工具页签 | [components/SourceTabTools.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceTabTools.vue) | L1-L25 |
| 源JSON编辑 | [components/SourceJson.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceJson.vue) | L1-L35 |
| 源调试 | [components/SourceDebug.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceDebug.vue) | L1-L60 |
| 源列表 | [components/SourceList.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceList.vue) | L1-L143 |
| 源列表项 | [components/SourceItem.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceItem.vue) | L1-L55 |
| 源帮助 | [components/SourceHelp.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/SourceHelp.vue) | L1-L60 |
| 正文内容 | [components/ChapterContent.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/ChapterContent.vue) | L1-L173 |
| 弹出目录 | [components/PopCatalog.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/PopCatalog.vue) | L1-L92 |
| 目录项 | [components/CatalogItem.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/CatalogItem.vue) | L1-L33 |
| 阅读设置 | [components/ReadSettings.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/ReadSettings.vue) | L1-L356 |
| 书籍卡片 | [components/BookItems.vue](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/components/BookItems.vue) | L1-L72 |
| 书源配置 | [config/bookSourceEditConfig.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/config/bookSourceEditConfig.ts) | L1-L608 |
| RSS配置 | [config/rssSourceEditConfig.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/config/rssSourceEditConfig.ts) | L1-L277 |
| 主题配置 | [config/themeConfig.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/config/themeConfig.ts) | L1-L74 |
| API 函数 | [api/api.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/api/api.ts) | L1-L226 |
| API 拦截器 | [api/index.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/api/index.ts) | L1-L112 |
| axios 实例 | [api/axios.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/api/axios.ts) | L1-L13 |
| bookStore | [store/bookStore.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/store/bookStore.ts) | L1-L209 |
| sourceStore | [store/sourceStore.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/store/sourceStore.ts) | L1-L133 |
| connectionStore | [store/connectionStore.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/store/connectionStore.ts) | L1-L23 |
| useLoading | [hooks/loading.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/hooks/loading.ts) | L1-L39 |
| jump 插件 | [plugins/jump.js](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/plugins/jump.js) | L1-L190 |
| Book 类型 | [book.d.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/book.d.ts) | L1-L109 |
| Source 类型 | [source.d.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/source.d.ts) | L1-L163 |
| Web 配置类型 | [web.d.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/web.d.ts) | L1-L14 |
| 工具函数 | [utils/utils.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/utils/utils.ts) | L1-L67 |

---

## 15. Vue3 Web 重构方案

> 以下为基于 Legado Android 原生 UI 分析的完整 Vue3 Web 重构方案，与上方现有架构（MPA + Element Plus）不同，本方案采用 SPA + Naive UI 架构。

### 15.1 重构方案与现有架构对比

| 维度 | 现有架构 | 重构方案 |
|------|---------|---------|
| 架构模式 | MPA（双入口 bookshelf/source） | SPA（单入口 + vue-router） |
| UI 库 | Element Plus | Naive UI |
| 路由 | Hash 路由，4条 | Hash 路由，8条（+搜索/详情/阅读器/替换/设置） |
| 状态管理 | 3 Store (book/source/connection) | 5 Store (+reader/config/replace) |
| 阅读器 | 无限滚动 + IntersectionObserver | CSS columns 分页 + 触摸手势 + TTS |
| 主题 | 7主题 + body/content/popup 三区域 | 4预设主题 + CSS 变量系统 |

### 15.2 重构方案子文档

| 子文档 | 核心内容 |
|--------|---------|
| [frontend-components.md](./frontend-components.md) | 路由设计+组件树+页面实现+阅读器核心+移动端适配+主题系统+组件库选择 |
| [frontend-stores.md](./frontend-stores.md) | TypeScript类型定义+5个Pinia Store实现+API调用层+WebSocket封装 |
| 源工具函数 | [utils/souce.ts](file:///f:/myself/github/WeAgentChat/temp/legado/modules/web/src/utils/souce.ts) | L1-L75 |