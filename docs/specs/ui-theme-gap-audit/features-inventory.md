# 功能清单（features-inventory.md）v1

> 设计阶段强制交付物（用户要求"全量先有功能清单/页面清单/流程清单"）。
> 来源：AGENTS.md + docs/INDEX.md + task-navigation.md 14 模块 + AndroidManifest Activity 全集。
> 用途：功能域 → 入口页面 → 主题/样式相关性 → 处置前后涉及的设置项，作为测试用例"功能全覆盖"的对账锚点。
> 结构：L0 功能域（F1-F31） + **P 系列流程级清单（P1-P14 业务流转链，功能趋于稳定期必测）**。
> 状态：v1（新增强制交付物：流程级/场景级清点）。

## 功能域一览

| # | 功能域 | 主要入口/页面 | 与主题设置相关性 | 处置(A1-A8)关联 |
|---|--------|--------------|----------------|----------------|
| F1 | 启动/欢迎 | WelcomeActivity | 欢迎页配色/背景 | A2 A6 |
| F2 | 主框架（5 Tab） | MainActivity（书架/发现/订阅/阅读记录/我的） | 顶栏/底部导航/卡片/搜索框全量 | A1-A8 全部 |
| F3 | 书架管理 | BookshelfFragment + BookshelfManageActivity + BookshelfTagManageActivity | 封面网格/分组标签/文件夹封面 | A1 A3 A7 |
| F4 | 书源搜索 | SearchActivity + SearchModel | 搜索框/结果卡片 | A1 A5 |
| F5 | 阅读核心 | ReadBookActivity + ReadBook.kt（View 红线，只审浮层） | 阅读配色/字号/翻页/浮层弹窗 | A1 A5 A6 |
| F6 | 漫画阅读 | ReadMangaActivity + ReadManga.kt | 画布呈现 | A6 |
| F7 | 音频播放 | AudioPlayActivity + AudioPlay.kt | 播放页配色 | A6 |
| F8 | 书籍详情/信息 | BookInfoActivity + BookInfoComposeActivity + BookInfoEditActivity | 详情卡片/背景图 | A1 A2 A3 |
| F9 | 目录/书签/正文搜索 | TocActivity / AllBookmarkActivity / SearchContentActivity | 列表样式 | A6 |
| F10 | 角色体系（Archive） | BookCharacterManage/Edit/Card/Relation + MyFeatureBooks | 列表卡片/详情 | A1 A6 |
| F11 | 书源管理 | BookSourceActivity + BookSourceEditActivity + BookSourceDebugActivity | S2 管理壳/编辑表单/顶栏 | A1 A3 A7 |
| F12 | 订阅源管理 | RssSourceActivity + RssSourceEditActivity + RssSourceDebugActivity | S2 管理壳/分组文件夹/编辑表单 | A1 A3 A7 |
| F13 | 替换规则/字典/TXT目录/回收站 | ReplaceRuleActivity / ReplaceEditActivity / DictRuleActivity / TxtTocRuleActivity / RecycleBinActivity | 列表/编辑弹层/代码高亮 | A1 A6 |
| F14 | 发现/探索 | ExploreFragment + ExploreShowActivity + DiscoverySuiteManageActivity | 发现源折叠/瀑布流/搜索框 | A1 A3 A7 |
| F15 | 订阅阅读 | RssFragment + RssSortActivity + ReadRssActivity + RssFavoritesActivity + RuleSubActivity | 经典/新版切换/头部标签/文章列表 | A1 A3 A7 |
| F16 | 订阅搜索 | RssSearchActivity + RssArticleInfoActivity | 搜索框/结果卡片/文章详情 | A1 A5 |
| F17 | 视频播放器 | VideoPlayerActivity + VideoPlayer.kt + VideoPlayService | 控制层/倍速/选集弹窗（video-player-theme-unify） | A1 A6 |
| F18 | 图片播放器/画廊 | ImageGalleryActivity + ImageDetailActivity + ImageCropActivity | 画廊/大图/裁剪 | A6 |
| F19 | 下载管理 | DownloadManageActivity + DownloadManageScreen + DownloadService | S2 管理壳/进度/菜单（download-manager-maturity） | A1 A3 |
| F20 | 网址记录/存储/文件管理 | UrlRecordActivity / StorageManageActivity / FileManageActivity + HandleFileActivity | 列表/分页 | A1 A6 |
| F21 | 主题体系（Archive） | ThemeManageActivity + TopBarManageActivity + AppearanceKitActivity/Edit + NavigationBarManageActivity + BubbleManageActivity + BookInfoManageActivity + CoverCollectionManage/Detail + AdvancedTitleManageActivity + ShareNoteTemplateManageActivity | **设置项产生方**（M1-M7 全部） | A1-A8（本体改动） |
| F22 | 导入容器管理 | S3ContainerManageActivity + LibraryContainerManageActivity | 列表/容器卡 | A6 |
| F23 | AI 助手（Archive） | AiChatActivity + AiImageGalleryActivity + AiProviderManage/Edit + AiImageProviderManage/Edit + AiWorldBookManageActivity | 聊天/画廊/提供商表单 | A1 A6 |
| F24 | 自动任务 | AutoTaskActivity + AutoTaskEditActivity | 任务列表/编辑/日志弹框 | A1 A6 |
| F25 | 高亮规则 | HighlightRuleActivity + 高亮三弹框 | 规则列表/弹框（已 Compose 化） | A1 A6 |
| F26 | 朗读配置 | ReadAloudBgmManageActivity + AiReadAloudUsageRecordActivity + SpeakerGroupManageActivity + 阅读菜单按钮 Manage/Edit + 段落规则 Manage/Edit | 列表/表单 | A1 A6 |
| F27 | 设置中心 | ConfigActivity + ConfigFragment 族（主题/封面/欢迎/其他/订阅/发现/备份/AI）+ SettingsSearchActivity | 全部设置项宿主 + GlassTopAppBar | A1-A8（改动宿主） |
| F28 | 调试工具集 | DebugToolsActivity + Encode/HttpDebug/CurlTest/PingTest/RegexTest/TimestampConvert | 工具页头部/输入区（F-P0-1） | A1 A3 |
| F29 | 浏览器/登录 | WebViewActivity + SourceLoginActivity | WebView 容器 | A6 |
| F30 | Web 服务/备份 | WebService + BackupConfigFragment + WebDav | 无 UI（服务） | — |
| F31 | 更新/导入系统 | 更新对话框 + OnLineImportActivity + FileAssociationActivity + QrCodeActivity + 验证码/跳转确认 + 授权 + 文字处理 | 系统层/透明页 | A6 |

## 主题设置项与功能域消费关系（M1-M7 对账锚点）

| 管理面 | 主要消费功能域 |
|--------|---------------|
| M1 主色体系 | F2 F3 F5 F11 F12 F15 F17 F19 F21 F25 F27（近全部） |
| M2 顶栏 | F2 F3 F11 F12 F14 F15 F27 F28（头部页） |
| M3 圆角 | F2 F3 F8 F11 F12 F14 F15 F19 F21 F25 F27 |
| M4 字号 | 全功能域（刻度表） |
| M5 搜索框 | F2 F4 F11 F12 F14 F15 F16 F27 |
| M6 弹框族 | F5 F11 F12 F13 F15 F17 F19 F24 F25 F26 |
| M7 弹层/菜单 | F2 F3 F11 F12 F14 F15 F17 F19 F27 |

> 说明：本表为"应然"关系（设置项改了应作用于哪些域），审计/测试用它对账"实然"（实际生效面），差额即缺口。

## P 系列：流程级/场景级清点（P1-P14，功能流转链全覆盖）

> **为何必要**：页面静态清单只能证明"每页可用"，**流程级清点证明"每个功能流转链的每个环节的样式都一致"**。功能趋稳期，流转链环节（跨页面跳转点、弹框入口、设置项开关、模式切换）正是脱节高发区。每条流程 = 环节链 + 关键页面 + 处置关联 + 脱节风险点，测试用例按"全链穿行"设计。

| # | 流程 | 环节链（页面序列） | 关键处置/设置项 | 脱节风险点（预判） |
|---|------|-------------------|----------------|-------------------|
| P1 | 书架→阅读主流程 | 书架(3形态×分组标签) → 详情(Compose/View 双版) → 目录 → 阅读正文(翻页/配色/字号) → 划线/高亮(三弹框) → 书签 → 朗读 → 正文搜索 → 换源(弹框) → 章节缓存/下载 | A1 A3 A5 A6 | 高亮弹框主题跟随；换源弹框 Base 样式；阅读浮层与正文配色 |
| P2 | 书源管理流程 | 书源列表 → 搜索/过滤 → 导入(在线/本地/文件) → 校验 → 编辑(字段/规则/调试) → 分组/排序 → 回收站 | A1 A3 A6 | 导入弹框家族统一；编辑页字段区 Compose 状态；回收站样式 |
| P3 | 发现/订阅流程 | 发现(经典/现代/瀑布) → 分组/套件 → 详情 → 加入书架 → 全局搜索 | A1 A3 A7 | 3 形态头部/卡片一致；瀑布流圆角 |
| P4 | 订阅源流程 | 订阅页(经典/新版切换×标签/文件夹) → 文章列表(5 样式) → 文章阅读 → 收藏/分享 → 视频/图片内容 → 下载 | A1 A3 A7 | **经典/新版切换残留（回归 bugfix ⑤）**；5 布局圆角；下载入口 |
| P5 | 视频播放流程 | 入口(多源) → 嗅探/线路/选集(弹框) → 播放控制(手势/倍速/选集) → 全屏/浮窗 → 下载 | A1 A6 | 倍速/选集弹窗主题；控制层深色悬浮与主题冲突 |
| P6 | 图片播放流程 | 画廊/大图 → 画布 → 保存/分享 | A6 | 画布配色/大图背景 |
| P7 | 下载/文件流程 | 6 入口 → 任务管理(进行/完成/暂停) → 通知 → 打开/播放/复制路径 → 存储/文件/网址记录 | A1 A3 | 下载卡片/菜单；通知样式 |
| P8 | 主题/外观流程 | 主题管理(应用/编辑/分享) → 顶栏管理 → 外观套件 → 导航栏 → 封面库 → 背景/字号 → 日夜/E-Ink | A1-A8 全部 | **改主色后全 App 生效面**（对账矩阵主战场）；套件切换一致性 |
| P9 | 设置/备份流程 | 设置中心(全部分组) → 备份/恢复 → WebDAV → 覆盖安装 → AI/自动任务/高亮配置 | A6 | 备份页 Compose 化样式；覆盖安装后主题回退 |
| P10 | AI 流程 | 会话 → 角色/世界书/记忆 → 画图 → AI 画廊/图片商配置 | A1 A6 | 聊天气泡；角色/世界书卡片 |
| P11 | 导入/关联流程 | 在线导入/文件关联/分享文本 → 确认/验证码 → 导入(书源/订阅/替换/字典/TTS/主题) → 分组 | A6 | **导入弹框族家族统一（C4 全量）**；透明页呈现 |
| P12 | 自动任务/朗读配置流程 | 任务列表 → 编辑(触发/动作) → 日志；朗读组/引擎/BGM → 阅读朗读 | A1 A6 | 任务日志弹框；BGM 管理列表 |
| P13 | 工具链流程 | 调试工具各页 → 结果 → Web 服务(开关/管理) | A1 A3 | 工具页头部/输入区（F-P0-1） |
| P14 | 阅读记录/统计流程 | 阅读记录(分类/统计组件) → 关于页 | A6 | 统计卡样式；关于页头部 |

## 场景级补充（处置组合场景，覆盖"处置叠加"）

| # | 场景 | 处置组合 | 预期 |
|---|------|---------|------|
| S-P1 | 夜间 + 顶栏配置 + 改封面库 | A6+A3+A1 | 全部联动且互不覆盖 |
| S-P2 | 经典订阅 + 改主色 + 改圆角 | A7+A1+A4 | 经典形态颜色/圆角同步 |
| S-P3 | E-Ink + 背景图 + 沉浸 | A8+A2 | 黑白强制 + 背景图降噪 |
| S-P4 | 覆盖安装（主题包/外观套件在档） | A6(重启) | 主题不丢失 |
| S-P5 | 多个下载任务并发 + 暗色主题 | A6 | 下载页与主题一致 |