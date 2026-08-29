# 页面清单（pages-inventory.md）v2 — 分层清点模型

> 设计阶段强制交付物（用户要求"全量先有功能清单/页面清单"）。
> 本版引入**分层清点模型**，覆盖全部 UI 呈现单位（2026-08-26 清点补齐，含 Screen/布局层）。

## 0. 覆盖单位总量（分层统计）

| 层 | 清点源 | 数量 | 说明 |
|----|--------|------|------|
| L0 功能域 | 功能分析 | 31 域 | features-inventory.md |
| L1 Activity | AndroidManifest | 98 | 禁用 Launcher1-7 剔除 |
| L2 Fragment | *Fragment.kt + class 声明 | 25 | 含书架 style1/2、5 主 Tab、设置 Fragment 族 |
| L3 Compose Screen/Route | *Screen.kt / *Route.kt | 61 | Compose 独立页面单位（本版新增） |
| L4 弹框/底部弹层 | *Dialog*.kt + *Sheet*.kt | 130+ | Base/Compose 两大家族并存 |
| L5 View 布局 XML | res/layout/*.xml | 208 | activity 64 / fragment 8 / item 56 / dialog 43 / view 21 / popup 5 / switch 4 / video 3 / widget 2 / 其它 2 |
| L6 设置项 | PreferKey / ThemeConfig / TopBarConfig | ~68+（Archive） | task 1.1 提取（management-surface.md） |

> **页面单位合计 = L1+L2+L3 = 184**；连同弹框/弹层（L4 130+）与布局（L5 208）为交互呈现全量。
> ui 目录 Kotlin 文件共 **673**（含 ViewModel/Adapter/纯逻辑，剔除后为 UI 呈现文件）；全 App Kotlin 1440。
> 清点源脚本：Glob `*Fragment.kt`/`*Screen.kt`/`*Route.kt`/`*Dialog*.kt` + `Get-ChildItem res/layout`（前缀分类）。

## A. Activity 全集（L1，N=105，禁用 7 剔除后 = 98）

### A1. 启动/欢迎/入口
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| WelcomeActivity | F1 启动 | S3 | Compose（WelcomeScreen） | 配色/背景 | 首启 |
| QrCodeActivity | F31 二维码 | S3 | View | 扫描框 | |

### A2. 主框架/主界面
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| MainActivity | F2 主框架 | S1 | 混合（5 Tab：书架/发现/订阅/阅读记录/我的） | 顶栏/底部导航/标签/搜索框全量 | 核心 |

### A3. 阅读/书籍
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| ReadBookActivity | F5 阅读 | S5 | View（红线） | 阅读配色/浮层弹窗 | 只审浮层 |
| ReadMangaActivity | F6 漫画 | S5 | View | 画布 | |
| BookInfoActivity | F8 详情 | S4 | View | 详情卡片/背景图 | |
| BookInfoComposeActivity | F8 详情 | S4 | Compose（沉浸式） | 详情卡片/背景图 | 新 |
| BookInfoEditActivity | F8 信息编辑 | S3 | View | 表单 | |
| AudioPlayActivity | F7 音频 | S3 | View | 播放页 | |
| TocActivity | F9 目录 | S2 | View | 列表 | |
| AllBookmarkActivity | F9 书签 | S2 | View | 列表 | |
| SearchContentActivity | F9 正文搜索 | S2 | View | 列表/输入 | |
| BookshelfManageActivity | F3 书架管理 | S2 | View | 列表/分组 | |
| MyFeatureBooksActivity | F10 特色书籍 | S2 | Compose | 列表 | |
| BookCharacterManageActivity | F10 角色管理 | S2 | Compose | 列表 | |
| BookCharacterEditActivity | F10 角色编辑 | S3 | Compose | 表单 | |
| BookCharacterCardActivity | F10 角色卡片 | S4 | Compose | 卡片 | |
| BookCharacterRelationActivity | F10 角色关系 | S4 | Compose | 关系图 | |

### A4. 阅读配置（朗读/段落/菜单按钮）
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| ParagraphRuleManageActivity | F26 | S2 | Compose | 列表 | |
| ParagraphRuleEditActivity | F26 | S3 | Compose | 表单 | |
| ReadMenuButtonManageActivity | F26 | S2 | Compose | 列表 | |
| ReadMenuCustomButtonEditActivity | F26 | S3 | Compose | 表单 | |
| SpeakerGroupManageActivity | F26 | S2 | Compose | 列表 | |
| ReadAloudBgmManageActivity | F26 | S2 | Compose | 列表 | |
| AiReadAloudUsageRecordActivity | F26 | S2 | Compose | 列表 | |

### A5. 搜索/导入
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| SearchActivity | F4 搜索 | S2 | View | 搜索框/结果卡 | 书源搜索 |
| ImportBookActivity | F31 导入书籍 | S2 | View | 列表 | |
| RemoteBookActivity | F31 添加远程 | S2 | View | 列表 | |

### A6. 书源/订阅源/规则管理
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| BookSourceActivity | F11 书源管理 | S2 | 混合（BookSourceScreen 部分 Compose） | 管理壳/顶栏/分组/搜索框 | 样板页 |
| BookSourceEditActivity | F11 书源编辑 | S3 | 混合（Compose 字段区→正在迁移） | 编辑表单 | WIP |
| BookSourceDebugActivity | F11 书源调试 | S3 | View | 表单/日志 | |
| RssSourceActivity | F12 订阅源管理 | S2 | 混合 | 管理壳/分组文件夹/搜索框 | |
| RssSourceEditActivity | F12 订阅源编辑 | S3 | 混合 | 编辑表单 | |
| RssSourceDebugActivity | F12 订阅源调试 | S3 | View | 表单/日志 | |
| ReplaceRuleActivity | F13 替换规则 | S2 | View | 列表 | |
| ReplaceEditActivity | F13 替换编辑 | S3 | View | 表单 | |
| TxtTocRuleActivity | F13 TXT目录 | S2 | View | 列表 | |
| DictRuleActivity | F13 字典管理 | S2 | View | 列表 | |
| CodeEditActivity | F13 代码编辑 | S3 | View | 代码高亮/输入 | |
| RecycleBinActivity | F13 回收站 | S2 | View | 列表 | |

### A7. 发现/书架标签
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| ExploreShowActivity | F14 发现详情 | S2 | View | 列表 | |
| DiscoverySuiteManageActivity | F14 套件管理 | S2 | Compose | 列表 | Archive |
| BookshelfTagManageActivity | F3 书架标签 | S2 | Compose | 标签列表 | |

### A8. 订阅/RSS 阅读
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| RuleSubActivity | F15 规则订阅 | S2 | View | 列表 | |
| RssSortActivity | F15 RSS条目 | S2 | View | 文章列表（5 布局） | 圆角回归点 |
| RssSearchActivity | F16 订阅搜索 | S2 | Compose（RssSearchViewModel） | 搜索框/结果 | |
| RssArticleInfoActivity | F16 文章详情 | S4 | Compose | 文章详情/头部 | |
| ReadRssActivity | F15 RSS阅读 | S3 | 混合（View+WebView） | 阅读/工具条 | |
| RssFavoritesActivity | F15 Rss收藏 | S2 | View | 列表 | |

### A9. 播放器/图片
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| VideoPlayerActivity | F17 视频 | S3 | View（GSY/Exo）+ Compose 弹层 | 控制层/倍速/选集弹窗 | video-player-theme-unify 点 |
| ImageGalleryActivity | F18 图片浏览器 | S3 | View（ViewPager2） | 画廊 | |
| ImageDetailActivity | F18 大图 | S3 | View | 大图/背景 | |
| ImageCropActivity | F18 图片裁剪 | S3 | View | 裁剪框 | |

### A10. 下载/网址记录/存储/文件
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| DownloadManageActivity | F19 下载 | S2 | Compose（DownloadManageScreen） | 管理壳/进度/菜单 | |
| UrlRecordActivity | F20 网址记录 | S2 | View | 列表/过滤 | |
| StorageManageActivity | F20 存储 | S2 | View | 列表/进度 | |
| FileManageActivity | F20 文件 | S2 | View | 列表 | |
| HandleFileActivity | F20 选文件 | SYS | View（Transparent） | — | 系统层 |

### A11. 主题体系（设置项产生方，Archive）
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| ThemeManageActivity | F21 | S2 | Compose | 主题列表/色板/背景/字号 | |
| TopBarManageActivity | F21 | S2 | Compose | 顶栏配置包 | |
| AppearanceKitActivity | F21 | S2 | Compose | 外观套件列表 | |
| AppearanceKitEditActivity | F21 | S3 | Compose | 套件编辑 | |
| NavigationBarManageActivity | F21 | S2 | Compose | 导航栏图标包 | |
| BubbleManageActivity | F21 | S2 | Compose | 气泡管理 | |
| BookInfoManageActivity | F21 | S2 | Compose | 书籍信息背景 | |
| CoverCollectionManageActivity | F21 | S2 | Compose | 封面收藏库 | |
| CoverCollectionDetailActivity | F21 | S4 | Compose | 封面详情 | |
| AdvancedTitleManageActivity | F21 | S2 | Compose | 高级标题（Lottie） | |
| ShareNoteTemplateManageActivity | F21 | S2 | Compose | 分享模板 | |

### A12. 容器管理（导入）
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| S3ContainerManageActivity | F22 | S2 | Compose | 列表 | |
| LibraryContainerManageActivity | F22 | S2 | Compose | 列表 | |
| RelaySettingsActivity | F22 | S3 | Compose | 设置表 | 加密通道 |

### A13. AI（Archive）
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| AiChatActivity | F23 | S3 | Compose | 聊天页/输入/消息气泡 | |
| AiImageGalleryActivity | F23 | S3 | Compose | 画廊 | |
| AiProviderManageActivity | F23 | S2 | Compose | 提供商列表 | |
| AiProviderEditActivity | F23 | S3 | Compose | 提供商表单 | |
| AiImageProviderManageActivity | F23 | S2 | Compose | 图片提供商列表 | |
| AiImageProviderEditActivity | F23 | S3 | Compose | 图片提供商表单 | |
| AiWorldBookManageActivity | F23 | S2 | Compose | 画世界管理 | |

### A14. 调试工具
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| DebugToolsActivity | F28 | S2 | View | 工具列表 | |
| EncodeToolsActivity | F28 | S3 | View | 编码区 | |
| HttpDebugActivity | F28 | S3 | View | 请求区/结果 | |
| CurlTestActivity | F28 | S3 | View | 命令行区 | |
| PingTestActivity | F28 | S3 | View | 结果区 | |
| RegexTestActivity | F28 | S3 | View | 正则区 | |
| TimestampConvertActivity | F28 | S3 | View | 时间戳区 | |

### A15. 自动任务/高亮
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| AutoTaskActivity | F24 | S2 | Compose | 任务列表/日志弹框 | |
| AutoTaskEditActivity | F24 | S3 | Compose | 任务编辑 | |
| HighlightRuleActivity | F25 | S2 | Compose | 规则列表/三弹框 | |

### A16. 我的/设置/关于
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| ConfigActivity | F27 设置中心 | S2 | Compose（ConfigFragment 族） | GlassTopAppBar/设置项宿主 | 设置入口 |
| SettingsSearchActivity | F27 设置搜索 | S2 | Compose（MySettingsScreen） | 全屏搜索 | |
| AboutActivity | F16 关于 | S2 | View | 头部/列表 | |
| ReadRecordActivity | F16 阅读记录 | S2 | View | 头部/列表 | |

### A17. 缓存
| Activity | 功能域 | 骨架 | 技术栈(粗) | 主题维度 | 备注 |
|----------|--------|------|-----------|---------|------|
| CacheActivity | 缓存列表 | S2 | Compose（CacheScreen） | 管理壳/下载子菜单/分组 | 已 Compose 化 |
| CacheManageActivity | 缓存管理 | S2 | View | 列表 | |

### A18. 系统/透明页（仅审计头部与弹层呈现，不入用例主集）
| Activity | 功能域 | 备注 |
|----------|--------|------|
| WelcomeActivity 已在 A1 | | |
| SharedReceiverActivity | F31 | Transparent |
| OnLineImportActivity | F31 | Transparent 一键导入 |
| VerificationCodeActivity | F31 | Transparent 验证码 |
| OpenUrlConfirmActivity | F31 | Transparent 跳转确认 |
| FileAssociationActivity | F31 | Transparent 打开文件 |
| SourceLoginActivity | F31 | Transparent 书源登录 |
| PermissionActivity | F31 | 授权界面 |
| ImageCropActivity | F18 | 裁剪（已列 A9 保留两处一致） |

## A9. Compose Screen / Route 全集（L3，61 个页面单位，2026-08-26 清点）

> Compose 独立页面单位（多由 Activity/Fragment 承载组合，仍是独立 UI 呈现单位，逐页审计/用例）。

| Screen/Route | 承载 | 功能域 | 说明 |
|--------------|------|--------|------|
| WelcomeScreen | WelcomeActivity | F1 | 欢迎页 |
| BookshelfScreen | BookshelfFragment* | F3 | 书架 Compose 呈现 |
| ExploreModernListScreen | ExploreFragment | F14 | 发现现代列表 |
| DiscoverySuiteHomeScreen | DiscoverySuiteManageActivity | F14 | 套件首页 |
| RssSourceScreen | RssSourceActivity | F12 | 订阅源管理 |
| BookSourceScreen | BookSourceActivity | F11 | 书源管理 |
| DownloadManageScreen | DownloadManageActivity | F19 | 下载管理 |
| CacheScreen | CacheActivity | 缓存 | 缓存列表 |
| MySettingsScreen | SettingsSearchActivity | F27 | 设置搜索 |
| ReplaceRuleScreen | ReplaceRuleActivity | F13 | 替换规则 |
| ExploreShowComposeScreen | ExploreShowActivity | F14 | 发现详情 |
| RuleSubScreen | RuleSubActivity | F15 | 规则订阅 |
| AdvancedTitleManageScreen | AdvancedTitleManageActivity | F21 | 高级标题 |
| TocComposeScreen | TocActivity | F9 | 目录 |
| SearchInputHelpScreen | SearchActivity | F4 | 搜索输入帮助 |
| SearchResultScreen | SearchActivity | F4 | 搜索结果 |
| BookshelfTagManageScreen | BookshelfTagManageActivity | F3 | 书架标签 |
| SettingSpecScreen | ConfigActivity | F27 | 设置规格 |
| ShareNoteTemplateManageScreen | ShareNoteTemplateManageActivity | F21 | 分享模板 |
| S3ContainerManageScreen | S3ContainerManageActivity | F22 | 容器管理 |
| LibraryContainerManageScreen | LibraryContainerManageActivity | F22 | 容器管理 |
| CoverCollectionManageScreen | CoverCollectionManageActivity | F21 | 封面收藏 |
| BubbleManageScreen | BubbleManageActivity | F21 | 气泡 |
| BookInfoManageScreen | BookInfoManageActivity | F21 | 书籍信息背景 |
| AiProviderEditScreen | AiProviderEditActivity | F23 | AI 提供商 |
| AiImageProviderManageScreen | AiImageProviderManageActivity | F23 | 图片提供商 |
| AiImageProviderEditScreen | AiImageProviderEditActivity | F23 | 图片提供商编辑 |
| AiWorldBookManageScreen | AiWorldBookManageActivity | F23 | 画世界 |
| AiChatScreen | AiChatActivity | F23 | AI 聊天 |
| HttpDebugScreen | HttpDebugActivity | F28 | HTTP 调试 |
| TimestampConvertScreen | TimestampConvertActivity | F28 | 时间戳 |
| RegexTestScreen | RegexTestActivity | F28 | 正则 |
| PingTestScreen | PingTestActivity | F28 | Ping |
| CurlTestScreen | CurlTestActivity | F28 | Curl |
| EncodeToolsScreen | EncodeToolsActivity | F28 | 编码转换 |
| DebugToolsScreen | DebugToolsActivity | F28 | 调试工具 |
| UrlRecordScreen | UrlRecordActivity | F20 | 网址记录 |
| AutoTaskScreen | AutoTaskActivity | F24 | 自动任务 |
| AutoTaskEditScreen | AutoTaskEditActivity | F24 | 任务编辑 |
| TxtTocRuleScreen | TxtTocRuleActivity | F13 | TXT 目录 |
| ImportBookScreen | ImportBookActivity | F31 | 导入书籍 |
| AllBookmarkScreen | AllBookmarkActivity | F9 | 书签 |
| HighlightRuleScreen | HighlightRuleActivity | F25 | 高亮规则 |
| DictRuleScreen | DictRuleActivity | F13 | 字典 |
| StorageManageScreen | StorageManageActivity | F20 | 存储管理 |
| ReadRecordScreen | ReadRecordActivity | F16 | 阅读记录 |
| PreciseManageScreen | PreciseManageFragment | F20 | 精准管理 |
| RecycleBinScreen | RecycleBinActivity | F13 | 回收站 |
| FileManageScreen | FileManageActivity | F20 | 文件管理 |
| BookInfoEditScreen | BookInfoEditActivity | F8 | 书籍信息编辑 |
| BookInfoComposeRoute | BookInfoComposeActivity | F8 | 书籍详情（沉浸） |
| OnlinePackageImportRoute | OnLineImportActivity | F31 | 在线包导入 |

> 其余 Screen 以目录归属（`ui/**/*Screen.kt` 全量 61 由审计脚本拉取，以上列出主要项；`config/compose/` 设置规格族并入 SettingSpec 类）。

## B. Fragment 全集（L2，25 类，2026-08-26 清点补齐）

> 技术栈列待 task 1.5/2.0 源码核验。

| Fragment | 功能域 | 承载页/布局 | 说明 |
|----------|--------|------------|------|
| BaseBookshelfFragment(-abstract) | F3 | fragment_bookshelf* | 书架基类（样式/分组切换基底） |
| style1/BookshelfFragment1 | F3 | fragment_bookshelf1 | 书架样式 1 |
| style2/BookshelfFragment2 | F3 | fragment_bookshelf2 | 书架样式 2 |
| ExploreFragment | F14 | fragment_explore | 发现 tab（经典/现代双形态 + 瀑布） |
| RssFragment | F15 | fragment_rss | 订阅 tab（经典/新版切换主战场） |
| ReadRecordFragment | F16 | activity_read_record | 阅读记录 tab |
| MyFragment | F15→我的 | fragment_my_config | 我的 tab（Compose 三级布局 + MainTopBarView） |
| RssArticlesFragment | F15 | fragment_rss_articles | 订阅文章列表（5 样式 adapter 切换，圆角点） |
| RssFavoritesFragment | F15 | fragment_rss_articles | Rss 收藏列表 |
| VideoFragment | F17 | 视频播放器页 | ViewPager2 竖滑 + 下载按钮 |
| AboutFragment | 关于 | activity_about | 关于页 |
| BackupConfigFragment | F27 备份 | 设置 | 备份恢复 |
| ComposeSettingFragment | F27 备份 | 设置 | 备份页新版 Compose |
| OtherConfigFragment | F27 | 设置 | 其他设置 |
| WelcomeConfigFragment | F27 | 设置 | 欢迎设置 |
| CoverConfigFragment | F27 | 设置 | 封面设置 |
| ThemeConfigFragment | F21 | 设置 | 主题设置（ConfigActivity 内） |
| SubscriptionConfigFragment | F27 | 设置 | 订阅设置 |
| DiscoverySubscriptionConfigFragment | F27 | 设置 | 订阅配置（Archive 新增） |
| DiscoveryConfigFragment | F27 | 设置 | 发现设置 |
| AiConfigFragment | F23/F27 | 设置 | AI 设置 |
| PreciseManageFragment | F20 | 精准管理 | 网址/存储/下载/文件聚合 |
| WebViewLoginFragment | F29 | 登录 | WebView 登录承载 |
| QrCodeFragment | F31 | 扫码 | QR 承载 |

## C. 弹框/底部弹层全集（130+ 文件，2026-08-26 清点补齐）

> 两大家族并存（**这是"弹框多风格"问题核心**）：
> - **ComposeDialogFragment 族**（新基线，M6 应然）：`ComposeDialogFragment` + `AppComposeDialogs` + `ComposeDialogAdapters` + `ComposeChoiceListDialog` + `GroupManageComposeDialog` + `ImportSourceSheet` 等
> - **BaseDialogFragment 族**（旧 View，M6 残留候选）：`ui/widget/dialog/*` + 各功能域 `BaseDialogFragment(R.layout.dialog_*)`
> 家族归属逐文件核验（Grep `: BaseDialogFragment\(|: ComposeDialogFragment\(`）→ 残留清单进入问题清单 v0。

### C1. 基础组件弹框/弹层（ui/widget/）
| 文件 | 家族 | 说明 |
|------|------|------|
| dialog/TextDialog | Base | 纯文本/Markdown（旧） |
| dialog/WaitDialog | Base | 等待 |
| dialog/VariableDialog | Base | 变量编辑 |
| dialog/UrlOptionDialog | Base | URL 选项 |
| dialog/PhotoDialog | Base | 图片预览 |
| dialog/CodeDialog | Base | 代码展示 |
| dialog/BottomWebViewDialog | Base | 底部 WebView |
| number/NumberPickerDialog | Base | 数字选择 |
| SourceSelectDialog | Base | 源选择 |
| components/ConfirmDialog / AppConfirmDialog / SingleChoiceDialog / AppEditDialog / AppTextDialog | Compose(components) | 通用对话框族 |
| components/AppModalBottomSheet / AppMenuSheet / AppDropdownMenu / MenuLayer | Compose(components) | 底部弹层/菜单族 |
| components/ColorPickerSheet / ImportSourceSheet / BookTocBookmarkSheet / HighlightStyleSheet | Compose(components) | 专用弹层 |
| compose/ComposeDialogFragment / AppComposeDialogs / ComposeDialogAdapters / ComposeChoiceListDialog / GroupManageComposeDialog | Compose(compose) | 对话框家族基座 |

### C2. 阅读核心/设置弹框（ui/book/read/）
| 文件 | 家族 | 说明 |
|------|------|------|
| HighlightStyleDialog 等（read/ 顶层 8 个） | 核验 | 选择网络搜索/引擎管理/选区图片/生效替换/内容编辑/气泡快切/分享模板 |
| config/MoreConfigDialog ReadStyleDialog ReadAloudDialog ReadAloudConfigDialog PageKeyDialog PaddingConfigDialog BgTextConfigDialog AutoReadDialog AdvancedTitleConfigDialog ClickActionConfigDialog ContentSelectMenuConfigDialog TipConfigDialog SpeakerGroupManageDialog SpeakEngineDialog ReaderDialogWindow ParagraphRuleQuickDialog HttpTtsEditDialog | 核验 | 阅读设置弹框族（20 个） |

### C3. 书籍功能弹框（ui/book/）
| 文件 | 家族 | 说明 |
|------|------|------|
| bookmark/BookmarkDialog | Compose | 书签 |
| changesource/ChangeBookSourceDialog ChangeChapterSourceDialog ChangeSourceDialogTheme | Base | 换源三件 |
| manage/SourcePickerDialog | Base | 源选择 |
| search/SearchScopeDialog | Compose | 搜索范围 |
| cache/CacheChapterDialog | 核验 | 缓存章节 |
| changecover/ChangeCoverDialog | Base | 换封面 |
| import/remote/ServerConfigDialog ServersDialog | Base | 远程服务器 |
| toc/rule/TxtTocRuleDialog TxtTocRuleEditDialog TxtTocRuleEditComposeDialog | Base/Compose 双版 | TXT 目录规则（新旧并存） |
| group/GroupManageDialog GroupSelectDialog GroupEditDialog | Compose | 分组族 |
| source/manage/GroupManageDialog | Compose | 书源分组 |
| manga/config/MangaFooterSettingDialog MangaEpaperDialog MangaColorFilterDialog | 核验 | 漫画设置 |
| audio/config/AudioSkipCredits | Compose | 音频跳过片头尾 |

### C4. 导入系（ui/association/，13+）
ImportBookSourceDialog / ImportRssSourceDialog / ImportThemeDialog / ImportTxtTocRuleDialog / ImportHttpTtsDialog / ImportDictRuleDialog / ImportReplaceRuleDialog / ImportRedThemeDialog / ParagraphRuleOnlineImportDialog / AddToBookshelfDialog / VerificationCodeDialog / OpenUrlConfirmDialog / ImportDialogComponents / ShibbolethDialogExtensions —— 家族多为 ComposeDialogFragment（ComposeDialogAdapters 入口），逐个核验

### C5. 规则管理弹框
RuleSubEditComposeDialog（订阅规则）/ DictDialog(Dialog_list)+DictRuleEditDialog / SourceFolderConfigDialog / rss/source/manage/GroupManageDialog / replace/GroupManageDialog / rss/article/ReadRecordDialog / rss/favorites/RssFavoritesDialog / rss/search/ChangeRssArticleSourceDialog / font/FontSelectDialog

### C6. 高亮/自动任务
highlight/edit/HighlightRuleEditDialog + HighlightRuleGroupManageDialog + HighlightPresetRuleDialog（已 Compose 化 ✅）/ autoTask/AutoTaskLogDialog + ImportAutoTaskDialog（已 Compose 化 ✅）

### C7. 配置管理（ui/config/）
CoverRuleConfigDialog / TopBarEditDialog / PackageSyncTaskDialog / BubbleEditDialog / CheckSourceConfig / DirectLinkUploadConfig（多 ComposeDialogFragment）
  
### C8. 工具/编辑器/系统
code/config/SettingsDialog + ChangeThemeDialog / video/config/SettingsDialog / file/FilePickerDialog / login/SourceLoginDialog / main/bookshelf/BookshelfConfigDialog / main/ai/compose/AiToolPreviewDialog + AiImagePreviewDialog / about/{UpdateDialog, AppLogDialog, CrashLogsDialog, ReadRecordComponentConfigDialog}（AppLog/CrashLogs 为 BaseDialogFragment 残留）

## C9. View 布局 XML 全集（L5，208 个，2026-08-26 分类统计）

> 前缀分类即审计分组：每类用统一判据扫描，避免逐个文件登记。

| 前缀 | 数量 | 语义 | 审计判据 |
|------|------|------|---------|
| activity_ | 64 | View 页面主布局 | C1/C2/C3/C4（硬编码颜色/圆角/字号） |
| fragment_ | 8 | View Fragment 主布局 | 同上 |
| item_ | 56 | 列表/条目项布局 | C1-C4 + 图片圆角（FilletImageView 12dp） |
| dialog_ | 43 | View 弹框布局（BaseDialogFragment 侧） | C1-C4 + 圆角/宽度风 |
| view_ | 21 | 复用组件布局（TitleBar/Search/Icon 等） | C1-C4 + 组件口径 |
| popup_ | 5 | 风格化弹层（PopupAction 等） | C1-C3 + 菜单风格（M7） |
| switch_/speed_/video_/widget_/floating_ | 11 | 播放器/浮窗专用（倍速/选集/控制器） | C1-C4 + video-player-theme-unify |
| **合计** | **208** | | |

## D. 待补清单（task 1.5/2.0 执行）

- [x] Activity 全集（Manifest，98 有效）
- [x] Fragment 全集（25 类，B 节）
- [x] Compose Screen/Route 全集（61，A9 节）
- [x] 弹框/底部弹层全集（130+ 文件，C 节）
- [x] View 布局 XML 分类总量（208，C9 节）
- [ ] 每页技术栈源码核验（v0 为粗分类）
- [ ] 弹框家族逐文件核验（Base vs Compose，C1-C8 标记）
- [ ] L6 设置项全集（PreferKey/ThemeConfig/TopBarConfig → management-surface.md，task 1.1）

## E. 页面覆盖矩阵（页面 × 样式维度，task 2.0/3.0 逐格推进）

| 页面 | 头部 | 三点菜单 | 弹框 | 底部弹层 | 列表卡片 | 搜索框 | 空态 | 主题联动 | 处置前后 | 覆盖状态 |
|------|------|---------|------|---------|---------|--------|------|---------|---------|---------|
| （每个页面一行，task 2.0 起填写：未审/已审无缺口/已审有缺口(Cx)/无法触达+原因） | | | | | | | | | | | |