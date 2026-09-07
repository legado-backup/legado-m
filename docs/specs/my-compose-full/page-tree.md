# 页面树全量清单（我的入口穷尽枚举，2026-09-07）

> 路由权威源：`ui/main/my/MySettingsData.kt` handleSettingsRowClick（L289-341）。穷尽方法：逐层递归全部跳转出口 + 目录类清单交叉比对。档位：C-full=整页 Compose / C-mixed=View+Compose 并存 / C-none=纯 View。

## 一、页面树

```
我的 (MyFragment | C-mixed：ViewBinding 壳 + View 顶栏 + ComposeView MySettingsScreen)
├─ 顶栏：SettingsSearchActivity | C-mixed（复用一级路由）
├─ 顶栏：TextDialog(帮助) | 对话框
├─ 主题模式行：ComposeActionListDialog | 对话框
├─ Web服务行：ComposeActionListDialog | 对话框
├─ 书源管理 BookSourceActivity | C-mixed
│   ├─ BookSourceEditActivity | C-none（CodeView 编辑器）
│   │   ├─ BookSourceDebugActivity | C-none
│   │   ├─ SourceLoginActivity→SourceLoginDialog | C-none/对话框
│   │   ├─ AppLogDialog / VariableDialog | 对话框
│   ├─ BookSourceDebugActivity（直达）| C-none
│   ├─ SourceLoginActivity→SourceLoginDialog | C-none/对话框
│   ├─ GroupManageDialog / SourceGroupFilterDialog / ImportBookSourceDialog / CheckSourceConfig | 对话框
├─ 订阅源管理 RssSourceActivity | C-mixed
│   ├─ RssSourceEditActivity | C-mixed(轻)
│   │   ├─ RssSourceDebugActivity→TextDialog×2 | C-mixed(轻)
│   │   ├─ SourceLoginDialog / AppLogDialog / VariableDialog | 对话框
│   ├─ GroupManageDialog / ImportRssSourceDialog | 对话框
├─ TXT目录规则 TxtTocRuleActivity | C-mixed(轻)
│   ├─ TxtTocRuleEditComposeDialog / ImportTxtTocRuleDialog | 对话框
├─ 替换净化 ReplaceRuleActivity | C-mixed(轻)
│   ├─ ReplaceEditActivity | C-mixed(轻)
│   ├─ GroupManageDialog / ImportReplaceRuleDialog | 对话框
├─ 字典规则 DictRuleActivity | C-mixed(轻)
│   ├─ DictRuleEditDialog / ImportDictRuleDialog / ComposeConfirmDialog | 对话框
├─ 高亮规则 HighlightRuleActivity | C-mixed(轻)
│   ├─ HighlightRuleEditDialog / HighlightRuleGroupManageDialog / HighlightPresetRuleDialog | 对话框
├─ 应用主题 AppearanceKitActivity | C-mixed
│   ├─ AppearanceKitEditActivity | C-mixed
│   └─ PackageSyncTaskDialog | 对话框
├─ 主题设置 ConfigActivity[THEME_CONFIG] | C-mixed 宿主
│   └─ ThemeConfigFragment | C-full
│       ├─ ThemeManageActivity | C-mixed（+FontSelectDialog×2/PackageSyncTaskDialog）
│       ├─ NavigationBarManageActivity | C-mixed（+PackageSyncTaskDialog；alert{}×2 违例）
│       ├─ ConfigActivity[DISCOVERY_SUBSCRIPTION_CONFIG]
│       ├─ TopBarManageActivity | C-mixed（+TopBarEditDialog/PackageSyncTaskDialog）
│       ├─ BookInfoManageActivity | C-mixed（+对话框族）
│       ├─ BubbleManageActivity | C-mixed（+对话框族×8）
│       ├─ ShareNoteTemplateManageActivity | C-mixed（样板页）
│       └─ ConfigActivity[COVER_CONFIG]
├─ 备份与恢复 ConfigActivity[BACKUP_CONFIG]
│   └─ BackupConfigFragment | C-full（+AppLogDialog→TextDialog）
│       ├─ S3ContainerManageActivity | C-mixed
│       └─ LibraryContainerManageActivity | C-mixed
├─ 公网Web访问 RelaySettingsActivity | C-mixed（无应用内出口）
├─ AI设置 ConfigActivity[AI_CONFIG]
│   └─ AiConfigFragment | C-full
│       ├─ AiWorldBookManageActivity | C-mixed(轻)
│       ├─ AiImageGalleryActivity | C-none（+AiImagePreviewDialog）
│       ├─ AiImageProviderManageActivity | C-mixed → AiImageProviderEditActivity | C-mixed
│       ├─ AiProviderManageActivity | C-mixed → AiProviderEditActivity | C-mixed（+对话框族×4）
│       └─ FileManageActivity(AI工作区) | C-mixed(轻)
├─ 自动任务 AutoTaskActivity | C-mixed(轻)
│   ├─ AutoTaskEditActivity | C-mixed(轻)（+SourceLoginDialog/TextDialog）
│   ├─ AppLogDialog / ImportAutoTaskDialog / AutoTaskLogDialog | 对话框
├─ 视频设置 ConfigActivity[VIDEO_PLAYER] → VideoPlayerConfigFragment | C-full（叶子）
├─ 订阅源全局搜索 RssSearchActivity | C-mixed(轻)
│   ├─ RssArticleInfoActivity | C-mixed(轻) 叶子
│   └─ AppLogDialog | 对话框
├─ 精选书架 MyFeatureBooksActivity | C-full
│   └─ VideoPlayerActivity / ReadMangaActivity / ReadBookActivity | 叶子（播放器/漫画/阅读器豁免域）
├─ 书签 AllBookmarkActivity | C-mixed(轻)（+BookmarkDialog）
├─ 阅读记录 ReadRecordActivity | C-mixed（内嵌 ReadRecordScreen）
├─ 其它设置 ConfigActivity[OTHER_CONFIG]
│   └─ OtherConfigFragment | C-full
│       ├─ CheckSourceConfig / DirectLinkUploadConfig | 对话框
│       ├─ ConfigActivity[VIDEO_PLAYER]
│       └─ DebugToolsActivity | C-none 叶子
├─ 精准管理 ConfigActivity[PRECISE_MANAGE]
│   └─ PreciseManageFragment | C-full
│       ├─ UrlRecordActivity | C-mixed(轻)（+FilterSheet/Confirm）
│       ├─ StorageManageActivity | C-mixed(轻) 叶子
│       ├─ CacheManageActivity | C-none（+CacheChapterDialog）
│       ├─ DownloadManageActivity | C-mixed(轻)
│       ├─ FileManageActivity | C-mixed(轻) 叶子
│       └─ LogActivity | C-mixed(轻)
├─ 关于 AboutActivity | C-mixed（AboutFragment=C-full；+UpdateDialog 等）
└─ 子搜索锚点 → ConfigActivity[COVER_CONFIG/WELCOME/...]
    ├─ CoverConfigFragment | C-full（+CoverRuleConfigDialog）
    │   └─ CoverCollectionManageActivity | C-mixed → CoverCollectionDetailActivity | C-none
    └─ WelcomeConfigFragment | C-full（叶子）
```

## 二、孤儿/死代码清单（7 项，随本任务治理）

| 项 | 位置 | 处置建议 |
|----|------|---------|
| AdvancedTitleManageActivity | ui/config/ | 入口在阅读页 TipConfigDialog——纳入 W3 并存页收尾（顶栏统一） |
| ThemeEditorDialogFragment | ui/config/theme/compose/ | 全工程无调用点——死代码删除 |
| DiscoveryConfigFragment | ui/config/ | ConfigTag.DISCOVERY_CONFIG 无启动方——死页删除 |
| SubscriptionConfigFragment | ui/config/ | ConfigTag.SUBSCRIPTION_CONFIG 无启动方——死页删除 |
| CrashLogsDialog | ui/about/ | 入口主界面——不属本任务，登记 |
| ReadRecordComponentConfigDialog | ui/about/ | 入口主界面阅读记录组件——不属本任务，登记 |
| fileManage 死分支路由 | MySettingsData.kt:333 | 无 UI 行触发——路由删除 |

## 三、统计（修订版）

- 一级 Activity 16 + 一级对话框 3
- 二级 Activity 32（含 ConfigActivity 内嵌 Fragment 11，其中 2 个孤儿不可达）
- 三级叶子：阅读器/漫画/播放器（豁免域）+ DebugTools 等
- 对话框类约 40（ComposeDialogFragment 系 + 遗留 View Dialog 系——迁移时统一 ComposeDialogFragment 基线）
- 档位修订：C-full 13 / C-mixed 约 30 / C-none 7（含阅读链 BookSourceEdit/BookSourceDebug/SourceLogin/DebugTools/AiImageGallery/ReadManga/ReadBook）/ 对话框 40
- 豁免域：ReadBookActivity（阅读器）/ReadMangaActivity/VideoPlayerActivity（播放器）/SourceLoginActivity（Transparent 透明主题特殊页）——既定豁免，仅登记
