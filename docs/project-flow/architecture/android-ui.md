# Android UI 层架构

> **核心问题**：200+ 个 Activity/Fragment/Widget 如何组织？导航链路怎样流转？
> **答案**：MainActivity(ViewPager+底部Nav) → 四大TabFragment → 二级 Activity → 三级 Dialog。阅读界面为独立 Activity 全屏栈。

---

## 1. 主框架：MainActivity + 底部导航

```
MainActivity (VMBaseActivity)
├── ViewPager (offscreenPageLimit=3)
│   ├── Tab 0: BookshelfFragment1/2  — 书架（双样式切换）
│   ├── Tab 1: ExploreFragment       — 发现（可选隐藏）
│   ├── Tab 2: RssFragment           — RSS订阅（可选隐藏）
│   └── Tab 3: MyFragment            — 我的配置
└── BottomNavigationView
    ├── menu_bookshelf
    ├── menu_discovery (AppConfig.showDiscovery 控制显隐)
    ├── menu_rss       (AppConfig.showRSS 控制显隐)
    └── menu_my_config
```

### 关键设计决策

| 决策 | 位置 | 说明 |
|------|------|------|
| ViewPager + FragmentStatePagerAdapter | [MainActivity.kt:L441](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L441) | `BEHAVIOR_RESUME_ONLY_CURRENT_FRAGMENT`，非当前 Fragment 不 resume |
| 书架双样式切换 | [MainActivity.kt:L424-L429](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L424) | `AppConfig.bookGroupStyle == 1 ? BookshelfFragment2 : BookshelfFragment1` |
| 底部菜单动态显示 | [MainActivity.kt:L386-L406](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L386) | `showDiscovery/showRSS` 控制 "发现"/"RSS" Tab 可见性 |
| 默认首页 | [MainActivity.kt:L408-L421](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L408) | `AppConfig.defaultHomePage` 支持 bookshelf/explore/rss/my |
| 双击退出 | [MainActivity.kt:L101-L121](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L101) | 2000ms 内双击返回退出；若朗读暂停则直接 finish，否则 moveTaskToBack |
| 书架重复点击回顶 | [MainActivity.kt:L172-L189](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L172) | 300ms 内再次选中 → `gotoTop()` |

### 启动流程

[MainActivity.kt:L124-L153](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/MainActivity.kt#L124)
```
onPostCreate
    ├── privacyPolicy()          — 隐私协议确认
    ├── upVersion()              — 版本更新检查/帮助文档
    ├── setLocalPassword()       — 首次设置本地密码
    ├── notifyAppCrash()         — 崩溃日志通知
    ├── backupSync()             — WebDAV 备份同步
    ├── viewModel.ruleSubsUp()   — 延迟1s自动更新书源
    ├── viewModel.upAllBookToc() — 延迟2s自动更新书籍目录
    └── viewModel.postLoad()     — 延迟3s后台加载
```

---

## 2. 活动（Activity）体系

### 书架模块

| Activity | 文件 | 功能 |
|----------|------|------|
| MainActivity | `ui/main/MainActivity.kt` | 主界面容器 |
| BookInfoActivity | `ui/book/info/BookInfoActivity.kt` | 书籍详情：信息/目录/书源管理 |
| BookChangeSourceActivity | `ui/book/change/BookChangeSourceActivity.kt` | 换源界面 |
| ImportBookActivity | `ui/book/import/local/ImportBookActivity.kt` | 本地书导入 |
| ImportBookWebActivity | `ui/book/import/web/ImportBookWebActivity.kt` | 网络书导入 |

### 阅读模块

| Activity | 文件 | 功能 |
|----------|------|------|
| BaseReadBookActivity | `ui/book/read/BaseReadBookActivity.kt` | 阅读抽象基类，负责屏幕方向/刘海适配/亮屏/翻页动画/按键翻页等通用功能 |
| ReadBookActivity | `ui/book/read/ReadBookActivity.kt` | 文字阅读核心，全屏沉浸式，16个接口实现 |
| ReadMangaActivity | `ui/book/read/ReadMangaActivity.kt` | 漫画阅读 |
| ReadAloudActivity | `ui/book/read/ReadAloudActivity.kt` | 朗读控制面板 |

### 搜索/发现模块

| Activity | 文件 | 功能 |
|----------|------|------|
| SearchActivity | `ui/book/search/SearchActivity.kt` | 搜索入口 + 搜索结果展示 |
| SearchBookActivity | `ui/book/searchContent/SearchBookActivity.kt` | 全文检索 |
| ExploreActivity | `ui/book/explore/ExploreActivity.kt` | 发现详情 |

### 书源/RSS 管理

| Activity | 文件 | 功能 |
|----------|------|------|
| BookSourceActivity | `ui/book/source/manage/BookSourceActivity.kt` | 书源列表管理 |
| BookSourceEditActivity | `ui/book/source/edit/BookSourceEditActivity.kt` | 书源可视化编辑 |
| RssSourceActivity | `ui/rss/source/manage/RssSourceActivity.kt` | RSS 源管理 |
| RssSourceEditActivity | `ui/rss/source/edit/RssSourceEditActivity.kt` | RSS 源编辑 |
| RssArticlesActivity | `ui/rss/article/RssArticlesActivity.kt` | RSS 文章列表容器 |
| RssSortActivity | `ui/rss/article/RssSortActivity.kt` | RSS 多源分组排序 |
| ReadRssActivity | `ui/rss/read/ReadRssActivity.kt` | RSS 文章阅读（WebView + JS注入） |
| RssFavoritesActivity | `ui/rss/favorites/RssFavoritesActivity.kt` | RSS 收藏文章 |
| RuleSubActivity | `ui/rss/subscription/RuleSubActivity.kt` | RSS 规则订阅入口 |

### 配置/替换/工具

| Activity | 文件 | 功能 |
|----------|------|------|
| ConfigActivity | `ui/config/ConfigActivity.kt` | 全局设置 |
| ReplaceRuleActivity | `ui/replace/ReplaceRuleActivity.kt` | 替换规则管理 |
| DictRuleActivity | `ui/dict/DictRuleActivity.kt` | 字典规则 |
| TTSEditActivity | `ui/tts/TTSEditActivity.kt` | TTS 配置编辑 |
| FileManageActivity | `ui/file/FileManageActivity.kt` | 文件管理 |

### 辅助模块

| Activity | 文件 | 功能 |
|----------|------|------|
| LoginActivity | `ui/login/LoginActivity.kt` | 登录/密码验证 |
| FontActivity | `ui/font/FontActivity.kt` | 字体管理 |
| AboutActivity | `ui/about/AboutActivity.kt` | 关于页面 |
| QrCodeActivity | `ui/qrcode/QrCodeActivity.kt` | 二维码/文件传输 |
| BrowserActivity | `ui/browser/BrowserActivity.kt` | 内置浏览器 |
| CodeActivity | `ui/code/CodeActivity.kt` | 代码编辑器 |
| CacheActivity | `ui/cache/CacheActivity.kt` | 缓存管理 |
| AssociationActivity | `ui/association/AssociationActivity.kt` | 关联导入(书源/RSS/替换) |
| VideoPlayActivity | `ui/video/VideoPlayActivity.kt` | 视频播放 |

---

## 3. Fragment 体系

### 书架 Fragment

```
BaseBookshelfFragment              — 书架基类（排序/分组/长按菜单/拖拽）
├── BookshelfFragment1             — 样式1：普通列表/网格
└── BookshelfFragment2             — 样式2：按分组折叠展示
```

核心行为：
- 长按书籍 → 弹出操作菜单（置顶/删除/换源/详情/缓存/导出）
- 下拉刷新 → 触发搜索线程池更新所有已收藏书籍
- 分组拖拽 → DragSortRecyclerView 实现
- 排序模式：按更新时间/按书名/按作者/按阅读进度/自定义排序

### 我的 (MyFragment)

展示配置入口：
- 书源管理 / RSS管理 / 替换规则
- 备份与恢复 / WebDAV 设置
- 主题设置 / 阅读设置 / TTS 设置
- 缓存与下载管理 / 关于

### RSS 文章流 (RssArticlesFragment + 5种Adapter)

**文件**：[RssArticlesFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/article/RssArticlesFragment.kt)

RSS 文章流是仅次于书架的第二复杂 Fragment，支持 5 种文章展示样式：

| Adapter | 样式 | 布局 |
|---------|------|------|
| `BaseRssArticlesAdapter<VB>` | 抽象基类 | 继承 `RecyclerAdapter<RssArticle, VB>` |
| `RssArticlesAdapter` (样式0) | 列表+缩略图 | LinearLayoutManager |
| `RssArticlesAdapter2` (样式2) | 网格2列 | GridLayoutManager(span=2) |
| `RssArticlesAdapter3` (样式3) | 瀑布流 | StaggeredGridLayoutManager(横屏3列/竖屏2列) |
| `RssArticlesAdapter4` (样式4) | 网格3列 | GridLayoutManager(span=3) |

核心功能：
- `sortName/sortUrl/searchKey` 通过 Bundle 传入，Room Flow `flowByOriginSort()` 监听数据变化
- DiffUtil 按 `link` 判断同一项，`title/image/read` 判断内容变化
- `isPreload=true` 时所有页面在后台加载，支持分页加载 `scrollToBottom() → loadMore()`
- 点击文章 → `ReadRssActivity`（WebView + JS注入，支持黑白名单过滤/Cookie管理/全屏视频/朗读）

**ReadRssActivity** ([ReadRssActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt))：
- WebView 池化复用（`WebViewPool.acquire(this)`）
- JS 接口注入（java/source/cache 对象）供书源规则使用
- `shouldInterceptRequest` 实现 preloadJs 注入和黑白名单 URL 过滤
- 返回键智能处理：全屏→WebView历史栈后退（跳过多刷新页）→退出

---

## 4. Widget 自定义控件体系

`ui/widget/` 下 30+ 自定义控件，核心分类：

| 类别 | 控件 | 用途 |
|------|------|------|
| **对话框** | `WaitDialog` / `TextDialog` / `RequestDialog` / `ModifyDialog` | 等待/文本展示/请求确认/修改 |
| **文本** | `BadgeView` / `UnderLineTextView` / `ExplosionTextView` | 角标/下划线/展开文本 |
| **图片** | `CoverImageView` / `PhotoView` / `RoundedRectImageView` | 封面/图片查看/圆角图 |
| **进度/滑块** | `VerticalSeekBar` / `NumberPicker` / `TouchSeekBar` | 垂直滑动条/数字选择/触控滑块 |
| **列表** | `FastScroller` / `DragSortRecyclerView` / `SwipeRecyclerView` | 快速滚动/拖拽排序/侧滑 |
| **弹窗** | `BottomDialog` / `BottomMenu` / `SourceEditDialog` | 底部弹窗/菜单/书源编辑 |
| **复选框** | `SmoothCheckBox` | 动画复选框 |
| **导航** | `PageNumberView` / `BatteryView` | 页码显示/电池电量 |
| **输入** | `CodeEditor` / `FontPicker` | 代码编辑器/字体选择 |
| **WebView** | `AndroidBug5497Workaround` / `WebDialog` | WebView 键盘修复/网页弹窗 |

---

## 5. Theme & 主题系统

```
ThemeConfig.getTheme()
├── EInk 模式  (AppConfig.isEInkMode → themeMode == "3")
├── Dark 深色   (AppConfig.isNightTheme → themeMode == "2")
└── Light 浅色  (默认/跟随系统 → themeMode == "0" or "1")
```

主题切换流程：[ThemeConfig.kt:L69-L73](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/ThemeConfig.kt#L69)
```
applyDayNight()
├── applyTheme()         — 切换 ThemeStore 主题
├── initNightMode()      — AppCompatDelegate 日夜间
├── BookCover.upDefaultCover() — 更新默认封面
└── postEvent(RECREATE)  — 通知 MainActivity 重建
```

**EInk 模式特殊处理**：
- 所有动画禁用 / elevation = 0
- BottomNavigationView 使用特殊底边框 drawable
- 界面极简化，去除阴影和过渡动画

---

## 6. Base 基类体系

```mermaid
classDiagram
    class BaseActivity
    class VMBaseActivity
    class ReadBookActivity
    class BookSourceActivity
    class MainActivity
    class RSSActivity
    class SettingsActivity
    BaseActivity <|-- VMBaseActivity
    VMBaseActivity <|-- ReadBookActivity
    VMBaseActivity <|-- BookSourceActivity
    VMBaseActivity <|-- MainActivity
    VMBaseActivity <|-- RSSActivity
    VMBaseActivity <|-- SettingsActivity
```

```
BaseActivity             — 最基础 Activity（Lifecycle + CoroutineScope）
├── VMBaseActivity<B,VM> — ViewBinding + ViewModel 泛型封装
│   ├── MainActivity
│   ├── BaseReadBookActivity  — 阅读抽象基类（屏幕方向/刘海适配/亮屏/翻页动画）
│   │   ├── ReadBookActivity  — 文字阅读核心，全屏沉浸式
│   │   └── ReadMangaActivity — 漫画阅读
│   └── ...
└── ...
```

`VMBaseActivity` 提供：
- `val binding` — 自动 ViewBinding 绑定
- `val viewModel` — 自动 ViewModel 懒加载
- `observeLiveBus()` — LiveData/EventBus 观察注册点

---

## 7. 阅读界面架构 (VMBaseActivity → BaseReadBookActivity → ReadBookActivity)

阅读界面是项目中最复杂的 Activity，通过 BaseReadBookActivity 抽象基类（负责屏幕方向设置/刘海屏适配/亮屏控制/翻页动画选择/按键翻页等通用阅读功能）统一管理文字阅读和漫画阅读的公共行为：

```
ReadBookActivity
├── ReadBook (全局单例, model/)
│   ├── 三种模式: 文字/漫画/音频  (ReadBook/ReadManga/AudioPlay)
│   ├── 三章缓存: prevChapter / curChapter / nextChapter
│   └── 触摸事件 → 9宫格区域映射 clickActionTL/TC/TR/ML/MC/MR/BL/BC/BR
├── PageView (自定义 View)
│   ├── 翻页动画: PageAnim 枚举 (覆盖/滑动/仿真/无)
│   ├── 排版引擎: ReadBookConfig.Config (行距/段距/字体/背景/页边距)
│   └── 分页计算: 基于屏幕尺寸 + Config 实时计算
├── ReadMenu (顶部/底部弹出菜单)
│   ├── 目录/书签/换源/朗读/设置/缓存/下载
│   └── 亮度调节/字体缩放/翻页动画切换
└── ReadAloudDialog (朗读控制浮窗)
```

```mermaid
graph TB
    RBA[ReadBookActivity] --> RB[ReadBook 全局单例]
    RBA --> PV[PageView 自定义View]
    RBA --> RM[ReadMenu 菜单覆盖层]
    RBA --> RAD[ReadAloudDialog 朗读控制]

    RB --> MODE{三种模式}
    MODE -->|文字| TEXT[TextRead]
    MODE -->|漫画| MANGA[ReadManga]
    MODE -->|音频| AUDIO[AudioPlay]
    RB --> CACHE[三章缓存<br/>prev/cur/next]
    RB --> TOUCH[9宫格触摸映射]

    PV --> ANIM[翻页动画 PageAnim]
    ANIM --> COVER[覆盖]
    ANIM --> SLIDE[滑动]
    ANIM --> SIM[仿真]
    ANIM --> NONE[无动画]
    PV --> LAYOUT[排版引擎<br/>ReadBookConfig]
    PV --> PAGE[分页计算]

    RM --> TB[TitleBar<br/>书名/章节/书源]
    RM --> BM[BottomMenu<br/>FAB+SeekBar+功能栏]
    BM --> FAB1[fabSearch 全文搜索]
    BM --> FAB2[fabAutoPage 自动翻页]
    BM --> FAB3[fabReplaceRule 替换]
    BM --> FAB4[fabNightTheme 夜间]
    BM --> CATALOG[目录/书签/换源/朗读/设置]
```

**9宫格触摸区域**：[AppConfig.kt:L38-L46](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/AppConfig.kt#L38)
```
┌─────────┬─────────┬─────────┐
│ clickTL │ clickTC │ clickTR │   0=菜单  1=下一页  2=上一页
├─────────┼─────────┼─────────┤   可自定义每个区域行为
│ clickML │ clickMC │ clickMR │   若全部设为非0则自动恢复中间区域为菜单
├─────────┼─────────┼─────────┤
│ clickBL │ clickBC │ clickBR │
└─────────┴─────────┴─────────┘
```

---

## 8. 导航链路总览

```
应用启动
    │
    ├── 首次启动 → 隐私协议 → 帮助文档(MD) → 设置密码 → MainActivity
    ├── 版本更新 → 更新日志(MD) → MainActivity
    └── 正常启动 → MainActivity
                        │
        ┌───────────────┼───────────────────┐
        ▼               ▼                   ▼
    书架Tab         发现Tab             我的Tab
    │               │                   │
    ├─点击书籍       ├─搜索结果           ├─书源管理
    │  └─BookInfo   │  └─BookInfo      ├─RSS管理
    │     ├─开始阅读  │     └─ReadBook   ├─替换规则
    │     │  └─ReadBookActivity        ├─备份恢复
    │     ├─换源                        ├─主题设置
    │     ├─缓存                        ├─WebDAV
    │     └─导出                        └─...
    ├─长按书籍 → 操作菜单
    ├─下拉刷新 → 全局更新
    └─搜索按钮 → SearchActivity
                     │
                     ├─搜索结果 → BookInfo → ReadBook
                     ├─全文检索 → SearchBookActivity
                     └─发现详情 → ExploreActivity
```

```mermaid
flowchart TB
    START[应用启动] --> FIRST{首次?}
    FIRST -->|是| PRIVACY[隐私协议] --> HELP[帮助文档MD] --> PWD[设置密码] --> MAIN
    FIRST -->|更新| CHANGELOG[更新日志MD] --> MAIN
    FIRST -->|正常| MAIN[MainActivity]

    MAIN --> BOOK_SHELF[书架Tab]
    MAIN --> EXPLORE[发现Tab]
    MAIN --> RSS_TAB[RSS Tab]
    MAIN --> MY[我的Tab]

    BOOK_SHELF -->|点击书籍| BOOK_INFO[BookInfoActivity]
    BOOK_SHELF -->|搜索按钮| SEARCH[SearchActivity]
    BOOK_SHELF -->|长按| OPS[操作菜单]

    BOOK_INFO -->|阅读| READ[ReadBookActivity]
    BOOK_INFO -->|漫画| MANGA[ReadMangaActivity]
    BOOK_INFO -->|换源| CHANGE_SRC[ChangeBookSourceDialog]
    BOOK_INFO -->|缓存| CACHE_DL[缓存下载]

    EXPLORE -->|搜索结果| BOOK_INFO
    SEARCH -->|结果点击| BOOK_INFO
    SEARCH -->|全文检索| SEARCH_BOOK[SearchBookActivity]

    MY --> SRC_MGR[书源管理]
    MY --> RSS_MGR[RSS管理]
    MY --> BACKUP[备份恢复]
    MY --> THEME[主题设置]
    MY --> WEBDAV[WebDAV设置]
```

---

## 9. 核心页面布局与交互详解

### 9.1 书架页面 (BookshelfFragment1/2)

**布局**：
```
+-------------------------------------------+
| TitleBar (搜索按钮/排序/更多)               |
+-------------------------------------------+
|                                            |
| SwipeRefreshLayout                         |
|  +-- RecyclerView                          |
|       样式1: GridLayoutManager(3列)        |
|       样式2: 分组折叠 + GridLayoutManager  |
|                                            |
+-------------------------------------------+
```

**状态变量**：
| 变量 | 类型 | 用途 |
|------|------|------|
| books | List<Book> | 当前书籍列表 |
| sort | Int | 排序模式 |
| isSearch | Boolean | 是否搜索模式 |

**交互**：长按→操作菜单(置顶/删除/换源/详情/缓存/导出)；下拉刷新→全局搜索更新；分组拖拽→DragSortRecyclerView

### 9.2 搜索页面 (SearchActivity)

**布局**：
```
+-------------------------------------------+
|  TitleBar + SearchView                     |
+-------------------------------------------+
|  RefreshProgressBar                        |
+-------------------------------------------+
|  A) 搜索结果: RecyclerView + SearchAdapter |
|  B) 输入帮助:                              |
|     书架书籍(FlexboxLayout+BookAdapter)    |
|     搜索历史(FlexboxLayout+HistoryKeyAdapter)|
+-------------------------------------------+
|  FAB (搜索开始/停止)                       |
+-------------------------------------------+
```

**状态变量**：
| 变量 | 类型 | 用途 |
|------|------|------|
| groups | List<String>? | 书源分组 |
| isManualStopSearch | Boolean | 是否手动停止 |
| precisionSearchMenuItem | MenuItem? | 精准搜索 |

**ViewModel LiveData**：
| LiveData | 用途 |
|----------|------|
| isSearchLiveData | 搜索进行中 |
| searchBookLiveData | 搜索结果 |
| upAdapterLiveData | Adapter局部刷新 |
| searchFinishLiveData | 搜索结束 |
| searchScope.stateLiveData | 搜索范围 |

**交互流程**：
1. SearchView提交 → viewModel.search(key)
2. 搜索文本变化 → stop() + upHistory(newText)
3. 搜索范围选择 → menu_group_1/2 → searchScope.update/remove
4. FAB → 搜索中stop(); 未搜索search("")
5. 结果点击 → BookInfoActivity
6. 历史关键字点击 → 直接搜索或补全
7. 滚动到底部 → 自动加载更多

### 9.3 书籍详情页面 (BookInfoActivity)

**布局**：
```
+-------------------------------------------+
|  bg_book (模糊封面背景)                    |
|  +-- vw_bg (半透明遮罩)                    |
|  |   +-- TitleBar (Dark主题)               |
|  |   +-- SwipeRefreshLayout                |
|  |       +-- NestedScrollView              |
|  |           ArcView (弧形顶部)            |
|  |           CardView > CoverImageView     |
|  |           tv_name (书名,居中)            |
|  |           lb_kind (分类标签)             |
|  |           tv_author / tv_origin         |
|  |           tv_lasted (最新章)             |
|  |           tv_group (分组)               |
|  |           tv_toc (目录进度)              |
|  |           tv_intro_container (简介)     |
|  +-- fl_action (底部操作)                  |
|      [tv_shelf: 加入/移出书架]             |
|      [tv_read: 阅读]                       |
+-------------------------------------------+
```

**状态变量**：
| 变量 | 类型 | 用途 |
|------|------|------|
| chapterChanged | Boolean | 章节变更 |
| pooledWebView | PooledWebView? | WebView池 |
| initIntroView | Boolean | 简介是否初始化 |

**ViewModel LiveData**：
| LiveData | 用途 |
|----------|------|
| bookData | 当前书籍 |
| chapterListData | 章节列表 |
| waitDialogData | 等待对话框 |
| actionLive | 操作指令 |

**交互**：
- tvRead → 按bookType分发AudioPlay/VideoPlayer/ReadManga/ReadBook
- tvShelf → 已加入:删除确认; 未加入:添加书架
- tvChangeSource → ChangeBookSourceDialog
- ivCover click → ChangeCoverDialog; long → PhotoDialog
- 简介支持四种模式: `<useweb>`/`<usehtml>`/`<md>`/纯文本

**菜单**：16项(menu_custom_btn, menu_edit, menu_share_it, menu_refresh, menu_login, menu_top, menu_set_source_variable, menu_set_book_variable, menu_copy_book_url, menu_copy_toc_url, menu_can_update, menu_clear_cache, menu_log, menu_split_long_chapter, menu_delete_alert, menu_upload)

### 9.4 阅读界面 (ReadBookActivity)

**布局**：
```
FrameLayout
 +-- ReadView (全屏阅读视图, 自定义View)
 +-- View (text_menu_position, 不可见锚点)
 +-- ImageView (cursor_left, 文本选择左光标)
 +-- ImageView (cursor_right, 文本选择右光标)
 +-- ReadMenu (阅读菜单覆盖层, 默认gone)
 |    +-- vwMenuBg (点击关闭菜单背景)
 |    +-- TitleBar (书名/章节名/书源操作/自定义按钮)
 |    +-- bottomMenu (ConstraintLayout)
 |         +-- fabSearch / fabAutoPage / fabReplaceRule / fabNightTheme
 |         +-- tvPre / tvNext (上一章/下一章)
 |         +-- seekReadPage (进度SeekBar)
 |         +-- llCatalog / llReadAloud / llFont / llSetting
 |         +-- llBrightness (亮度控制条)
 +-- SearchMenu (全文搜索菜单, 默认gone)
 +-- View (navigation_bar, 底部导航栏占位)
```

**状态变量**：
| 变量 | 类型 | 用途 |
|------|------|------|
| isInitFinish | Boolean | 数据初始化完成 |
| menuLayoutIsVisible | Boolean | 菜单可见 |
| isAutoPage | Boolean | 自动翻页 |
| isScroll | Boolean | 滚动模式 |
| isShowingSearchResult | Boolean | 全文搜索结果模式 |
| isSelectingSearchResult | Boolean | 选择搜索结果 |
| bookChanged | Boolean | 书籍变更 |
| pageChanged | Boolean | 页面变更 |
| confirmRestoreProcess | Boolean? | 恢复进度确认 |
| searchContentQuery | String | 搜索关键词 |
| searchResultList | List<SearchResult>? | 搜索结果 |
| searchResultIndex | Int | 当前搜索索引 |

**翻页交互 (5种)**：
1. 触摸翻页: ReadView.OnTouchEvent → pageDelegate.turnPage()
2. 音量键: VOLUME_UP/DOWN → volumeKeyPage()
3. 键盘: PAGE_UP/DOWN/SPACE → handleKeyPage()
4. 鼠标滚轮: SCROLL → mouseWheelPage()
5. 自动翻页: autoPage() → readView.autoPager.start()

**菜单显示/隐藏**：
点击屏幕中央 → showActionMenu()
  → 朗读中 → showReadAloudDialog()
  → 自动翻页 → AutoReadDialog
  → 全文搜索中 → searchMenu.runMenuIn()
  → 否则 → readMenu.runMenuIn() (TitleBar下滑 + 底栏上滑)

**文本选择交互**：
长按文字 → ContentTextView选中 → cursorLeft/cursorRight显示
拖拽光标 → selectStartMove/selectEndMove
松手 → TextActionMenu (朗读/书签/替换/全文搜索/字典)

**事件总线观察**：
- TIME_CHANGED / BATTERY_CHANGED → 更新时间/电量
- UP_CONFIG(array) → 更新配置(0=系统UI, 1=背景, 2=样式, 3=透明度, 4=翻页灵敏度, 5=重载内容, 6=更新内容...)
- ALOUD_STATE → 朗读状态变化
- TTS_PROGRESS → TTS进度
- SEARCH_RESULT → 搜索结果
- REFRESH_BOOK_CONTENT / REFRESH_BOOK_TOC → JS触发刷新

### 9.5 书源管理页面 (BookSourceActivity)

**布局**：
```
+-------------------------------------------+
|  TitleBar + SearchView                     |
+-------------------------------------------+
|  FastScrollRecyclerView                    |
|    LinearLayoutManager                     |
|    BookSourceAdapter                       |
|    DragSelectTouchHelper (滑动多选)        |
|    ItemTouchHelper (拖拽排序)              |
+-------------------------------------------+
|  SelectActionBar                           |
|  [全选/反选] [删除] [启用/禁用/校验/...]   |
+-------------------------------------------+
```

**状态变量**：
| 变量 | 类型 | 用途 |
|------|------|------|
| sort | BookSourceSort | 排序模式(Default/Weight/Name/Url/Update/Respond/Enable) |
| sortAscending | Boolean | 升序/降序 |
| groups | LinkedHashSet<String> | 书源分组 |
| groupSourcesByDomain | Boolean | 按域名分组 |
| snackBar | Snackbar? | 校验提示 |

**搜索关键字**：支持"启用/禁用/需登录/无分组/启用发现/禁用发现/group:xxx"

**批量操作**：启用/禁用/发现/校验/置顶/置底/加分组/移分组/导出/分享

### 9.6 书源编辑页面 (BookSourceEditActivity)

**布局**：
```
+-------------------------------------------+
|  TitleBar ("编辑书源")                     |
+-------------------------------------------+
|  HorizontalScrollView (配置行)             |
|  [Spinner:类型] [启用] [发现] [Cookie]     |
|  [事件监听] [自定义按钮]                   |
+-------------------------------------------+
|  TabLayout (6个Tab)                        |
|  [基本] [搜索] [发现] [详情] [目录] [正文] |
+-------------------------------------------+
|  RecyclerView (动态EditEntity列表)          |
+-------------------------------------------+
```

**6个Tab编辑项**：
| Tab | 编辑项数 | 关键字段 |
|-----|---------|---------|
| 基本 | 13 | bookSourceUrl, bookSourceName, bookSourceGroup, loginUrl, loginUi, loginCheckJs, coverDecodeJs, bookUrlPattern, header, variableComment, concurrentRate, jsLib |
| 搜索 | 11 | searchUrl, checkKeyWord, bookList, name, author, kind, wordCount, lastChapter, intro, coverUrl, bookUrl |
| 发现 | 10 | exploreUrl, bookList, name, author, kind, wordCount, lastChapter, intro, coverUrl, bookUrl |
| 详情 | 11 | init, name, author, kind, wordCount, lastChapter, intro, coverUrl, tocUrl, canReName, downloadUrls |
| 目录 | 10 | preUpdateJs, chapterList, chapterName, chapterUrl, formatJs, isVolume, updateTime, isVip, isPay, nextTocUrl |
| 正文 | 11 | content, nextContentUrl, subContent, replaceRegex, title, sourceRegex, imageStyle, imageDecode, webJs, payAction, callBackJs |

**交互**：Tab切换→RecyclerView的EditEntity切换；保存→getSource()收集→viewModel.save()；调试→先保存→BookSourceDebugActivity；全屏编辑→CodeEditActivity；键盘工具→KeyboardToolPop(URL参数/教程/正则/文件)

### 9.7 RSS订阅源页面 (RssSortActivity)

**布局**：
```
+-------------------------------------------+
|  TitleBar                                  |
+-------------------------------------------+
|  LinearLayout (tabs_container, 动态多行标签)|
|  每行: HorizontalScrollView > TextView标签  |
|  (<=10:1行, <=20:2行, >20:3行)            |
+-------------------------------------------+
|  ViewPager                                 |
|  +-- RssArticlesFragment (每分类一个)      |
+-------------------------------------------+
```

**5种文章样式**：
| style | Adapter | LayoutManager | 说明 |
|-------|---------|---------------|------|
| 0 | RssArticlesAdapter | LinearLayoutManager | 标题+日期(左) + 缩略图(右110x68) |
| 1 | RssArticlesAdapter1 | LinearLayoutManager | 大图(220dp高) + 标题 + 日期 |
| 2 | RssArticlesAdapter2 | GridLayoutManager(2列) | 双列卡片 |
| 3 | RssArticlesAdapter3 | StaggeredGridLayoutManager(竖2/横3) | 瀑布流CardView |
| 4 | RssArticlesAdapter4 | GridLayoutManager(3列) | 三列紧凑 |

切换：菜单 menu_switch_layout → articleStyle循环0→1→2→3→4→0

### 9.8 RSS文章阅读页面 (ReadRssActivity)

**布局**：
```
FrameLayout
 +-- ConstraintLayout (主视图)
 |    +-- TitleBar
 |    +-- FrameLayout (web_view_container, WebView)
 |    +-- RefreshProgressBar (1dp进度条)
 +-- FrameLayout (custom_web_view, 全屏视频)
```

**内容加载三路分发**：
1. 有link+有description → contentLiveData → loadDataWithBaseURL
2. 有link+有ruleContent → Rss.getContent() → contentLiveData
3. 有link+无ruleContent → urlLiveData → loadUrl
4. 有startHtml → htmlLiveData → loadDataWithBaseURL

**WebView交互**：长按图片→保存；URL跳转→shouldOverrideUrlLoading JS；黑白名单→shouldInterceptRequest过滤；JS注入→preloadJs；全屏视频→customWebView覆盖

**返回导航**：全屏→关闭视频；WebView可后退→智能计算后退步数(跳过刷新重复)；无法后退→finish()

### 9.9 配置页面 (ConfigActivity)

**布局**：简单容器，通过configTag动态加载Fragment

**Fragment路由表**：
| configTag | Fragment | 功能 |
|-----------|----------|------|
| OTHER_CONFIG | OtherConfigFragment | 其他设置 |
| THEME_CONFIG | ThemeConfigFragment | 主题设置 |
| BACKUP_CONFIG | BackupConfigFragment | 备份设置 |
| COVER_CONFIG | CoverConfigFragment | 封面设置 |
| WELCOME_CONFIG | WelcomeConfigFragment | 欢迎页设置 |

### 9.10 换源对话框 (ChangeBookSourceDialog)

**布局**：
```
+-------------------------------------------+
|  Toolbar (书名/作者 + 菜单)                |
+-------------------------------------------+
|  RefreshProgressBar                        |
+-------------------------------------------+
|  FastScrollRecyclerView                    |
|    ChangeBookSourceAdapter                 |
+-------------------------------------------+
|  ll_bottom_bar                             |
|  [当前源/进度] [跳顶部] [跳底部]          |
+-------------------------------------------+
```

**交互**：换源→changeTo()→类型确认→viewModel.getToc()→callBack.changeTo()；搜索控制→startOrStopSearch()；分组切换→AppConfig.searchGroup变更；滚动定位→scrollToDurSource()

---

## 10. 页面交互流程图

### 10.1 阅读界面状态流转

```
[阅读中]
  │
  ├── 点击屏幕中央 ─→ [菜单可见]
  │     ├── TitleBar: 书名/章节/书源操作/自定义按钮
  │     ├── 目录 → TocDialog
  │     ├── 朗读 → ReadAloudDialog
  │     ├── 排版 → ReadStyleDialog
  │     ├── 设置 → ReadBookConfigFragment
  │     ├── FAB搜索 → SearchMenu
  │     ├── FAB自动翻页 → AutoReadDialog
  │     ├── FAB替换 → ReplaceRuleDialog
  │     ├── FAB夜间 → 切换夜间模式
  │     └── 点击空白 → 返回[阅读中]
  │
  ├── 长按文字 ─→ [文本选择]
  │     ├── 朗读选中
  │     ├── 添加书签
  │     ├── 替换规则
  │     ├── 全文搜索
  │     └── 字典查询
  │
  ├── 音量键 ─→ 翻页
  ├── 自动翻页 ─→ 定时翻页
  └── 返回键 ─→ finish()
```

```mermaid
stateDiagram-v2
    [*] --> 阅读中

    阅读中 --> 菜单可见 : 点击屏幕中央
    阅读中 --> 文本选择 : 长按文字
    阅读中 --> 翻页 : 音量键/触摸翻页
    阅读中 --> 自动翻页 : 开启自动翻页
    阅读中 --> [*] : 返回键

    菜单可见 --> 目录 : 目录按钮
    菜单可见 --> 朗读控制 : 朗读按钮
    菜单可见 --> 排版设置 : 排版按钮
    菜单可见 --> 阅读设置 : 设置按钮
    菜单可见 --> 全文搜索 : FAB搜索
    菜单可见 --> 自动翻页设置 : FAB自动翻页
    菜单可见 --> 替换规则 : FAB替换
    菜单可见 --> 阅读中 : 点击空白区域
    菜单可见 --> 夜间模式切换 : FAB夜间

    目录 --> 阅读中 : 选择章节
    朗读控制 --> 阅读中 : 关闭
    排版设置 --> 阅读中 : 关闭
    阅读设置 --> 阅读中 : 关闭
    全文搜索 --> 阅读中 : 关闭
    夜间模式切换 --> 阅读中 : 自动

    文本选择 --> 朗读选中 : 朗读
    文本选择 --> 添加书签 : 书签
    文本选择 --> 替换规则 : 替换
    文本选择 --> 全文搜索 : 搜索
    文本选择 --> 字典查询 : 字典
    文本选择 --> 阅读中 : 取消选择

    自动翻页 --> 阅读中 : 停止自动翻页
    自动翻页设置 --> 阅读中 : 关闭
```

### 10.2 搜索→详情→阅读 完整流程

```
SearchActivity
  │
  ├── 输入关键词 → 搜索 → searchBookLiveData
  │     ├── 结果点击 → BookInfoActivity
  │     │     ├── tvRead → ReadBookActivity / ReadMangaActivity / AudioPlayActivity
  │     │     ├── tvShelf → 加入/移出书架
  │     │     ├── tvChangeSource → ChangeBookSourceDialog
  │     │     └── ivCover → ChangeCoverDialog
  │     │
  │     └── 长按结果 → 快速加入书架
  │
  └── 搜索范围 → menu_group → 分组筛选
```

```mermaid
sequenceDiagram
    participant U as 用户
    participant SA as SearchActivity
    participant VM as SearchViewModel
    participant BIA as BookInfoActivity
    participant RBA as ReadBookActivity

    U->>SA: 输入关键词
    SA->>VM: search(key)
    VM->>VM: 遍历书源并发搜索
    VM-->>SA: searchBookLiveData 更新
    SA->>SA: SearchAdapter 展示结果

    U->>SA: 点击搜索结果
    SA->>BIA: startActivity(book)
    BIA->>BIA: 加载书籍详情+目录

    U->>BIA: 点击阅读
    alt 文字书
        BIA->>RBA: ReadBookActivity
    else 漫画
        BIA->>RBA: ReadMangaActivity
    else 有声书
        BIA->>RBA: AudioPlayActivity
    end

    U->>BIA: 点击换源
    BIA->>BIA: ChangeBookSourceDialog

    U->>BIA: 点击加入书架
    BIA->>BIA: saveBook / deleteBook
```