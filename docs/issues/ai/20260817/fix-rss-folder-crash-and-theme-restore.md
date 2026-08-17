# 2026-08-17 真机回归三连修：订阅源文件夹布局闪退 / 编辑页保存失效 / 备份恢复主题缩水

> 背景：真机覆盖安装 3.26.081615 包后反馈三类严重回归。本文档记录根因分析、已落地的修复内容与待完成验证项。
> 状态：三项修复已编码完成、`compileAppDebugKotlin` + `assembleAppDebug` 编译通过、APK `3.26.081709` 已打包（未安装验证）。

---

## 一、问题清单总览

| # | 用户症状 | 根因状态 | 修复状态 |
|---|---------|---------|---------|
| 1 | 订阅源切"文件夹"布局直接闪退 `android.view.InflateException: Binary XML file line #47` | 已实锤 | 已修复，待 E2E |
| 2 | 编辑订阅源：左上角返回弹窗"保存"点了没反应；右上角菜单保存才生效 | 已实锤 | 已修复，待 E2E |
| 2b | 老软件备份 zip 恢复后，视频/图片源变"网页"分类，不进内置播放器 | 静态排查未复现根因 | 待实测（见四.1） |
| 3 | 主题"沉浸式操作栏"开关不生效；备份恢复后主题列表 17 个→4 个 | 17→4 已实锤；沉浸式待实测 | 17→4 已修复；沉浸式待实测（见四.2） |

---

## 二、根因分析

### 问题 1：文件夹布局 InflateException（必崩）

**根因**：`app/src/main/res/layout/item_source_folder_grid.xml`（发现页/订阅源主页文件夹卡片）误用了 **Material3 专属主题属性**：

- `android:background="?attr/colorSurfaceContainerHigh"`（元素第 38 行附近）
- `app:tint="?attr/colorOnSurfaceVariant"`（元素第 61 行附近）

而应用 View 体系 Activity 的主题基类是 `Base.AppTheme`（`values/styles.xml:32`，parent=`Theme.AppCompat.DayNight.NoActionBar`）——**不是 Material3 主题**，这两个属性在该主题下无值。运行时 `LayoutInflater` 解析属性抛 `UnsupportedOperationException: Failed to resolve attribute`，包装成 `InflateException: Binary XML file line #N`（真机包该布局版本中失败元素落在第 47 行，与用户报错吻合）。

**引入路径**：081615 构建对应 updateLog 08/16 条目"发现/订阅源文件夹支持自定义封面，卡片样式与书架分组卡片完全一致"——对齐书架分组卡片（Compose/M3 环境）时，把 M3 主题属性直接带进了 View 体系 XML。发现页一切换"分组样式=Folder"即触发，100% 复现；模拟器未暴露仅因没人切过该样式。

### 问题 2：编辑页返回弹窗"保存"无响应

**根因**：提交 `5f5652dbc`（08/16 Compose 迁移批量推进）改造 `RssSourceEditActivity` 后，`finish()` 覆写中的退出确认弹窗：

```kotlin
positiveButton(R.string.yes)          // ← 空 lambda：点"是"不保存、不退出、弹窗关闭
negativeButton(R.string.no) { super.finish() }
```

左上角返回按钮 `onNavClick = { finish() }` 与系统返回键均走此路径。对照右上角菜单"保存"直接调 `viewModel.save()` 正常——与用户描述"必须点右上角三个点里面的保存才生效"完全吻合。

### 问题 3：备份恢复后主题列表 17→4

**根因**（三个环节叠加）：

1. 备份侧 `Backup.kt:499` 会把当前完整主题列表写入 zip 的 `themeConfig.json`；
2. 恢复侧 `Restore.kt:214` 用 zip 里的文件**整体覆盖**本地 `themeConfig.json`——用户的 zip 产自老版本软件（内置主题仅 4 个的时代），覆盖后本地文件只剩 4 个主题；
3. `ThemeConfig.configList` 是 `by lazy` 单例，重启后从该文件初始化 → 列表定格 4 个。而本应补回内置主题的 `DefaultData.importDefaultThemeConfigs()`（`addNewConfigs` 语义：仅新增、同名不覆盖）**全工程无任何调用点（死代码）**，新版 17 个内置主题（默认/典雅蓝/…/暗夜墨绿）永远补不回来。

### 问题 2b：恢复后类型丢失/内置播放器失效（未实锤，已排除项）

以下环节静态排查均正常，暂未找到回归点：

- `RssSource.type` 字段自初始提交即存在，字段名/含义未变，Gson 反序列化不丢字段；`Restore.kt` 的 `rssSources.json → insert` 链路本轮未改动；
- `@array/rss_type`（网页 0/图片 1/视频 2）未变过；
- `ReadRss.readRss` 路由完整：`rssSource.type==2 → VideoPlayerActivity`、`==1 → ImageGalleryActivity`；调用方 `RssArticlesFragment:309` 正确传入 `activityViewModel.rssSource`；
- DB 迁移 103→104 仅新增 `source_group_covers` 表，不动 `rssSources` 表。

**待办**：需要用户的老备份 zip 样本，或在模拟器导入 type=1/2 源全流程实测（导入→类型分组→点文章→播放器路由），见四.1。

### 问题 3a：沉浸式操作栏开关不生效（未实锤，已排除项）

设置链路静态完整：`ThemeConfigScreen` 开关 → `putPrefBoolean` + `postEvent(RECREATE)` → `BaseActivity` 统一订阅（recreate 或豁免页刷系统栏）→ `setupSystemBar()` 读 `AppConfig.isTransparentStatusBar`。`ThemeStore.statusBarColor` 本轮未改动。需实测复现定位（重点观察：`ConfigActivity` 的 `recreateOnThemeChange=false` 豁免路径、设置宿主页自身状态栏是否刷新），见四.2。

---

## 三、已落地修复（编译通过，APK 3.26.081709）

### 修复 1：布局去 M3 属性 + Adapter 运行时注入（对齐 View 体系惯例）

| 文件 | 变更 |
|------|------|
| `app/src/main/res/layout/item_source_folder_grid.xml` | 删除 `?attr/colorSurfaceContainerHigh`（background）与 `?attr/colorOnSurfaceVariant`（app:tint）两处引用，加注释说明"页面主题为 AppCompat，禁用 M3 属性" |
| `app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt` | `getViewBinding()` 创建卡片时注入：封面占位底色 = `ThemeStore.backgroundColor` 向黑/白微混（`ColorUtils.blendARGB`，亮色向黑 6%、暗色向白 8%，等价 M3 surfaceContainerHigh 的层次感）；文件夹图标 tint = `secondaryTextColor`（onSurfaceVariant 的 View 体系等价）。颜色跟随用户主题/日夜切换，视觉语义与原设计一致 |

### 修复 2：编辑页退出弹窗"保存并退出"

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` | `positiveButton(R.string.yes) { viewModel.save(source) { super.finish() } }`——保存成功后 `super.finish()`（跳过覆写的 `finish()`，避免二次弹窗；`viewModel.save` 内部已同步 `rssSource = source`） |

### 修复 3：恢复主题后合并补齐内置主题

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/help/storage/Restore.kt` | 恢复主题配置块在 `ThemeConfig.upConfig()` 后追加 `DefaultData.importDefaultThemeConfigs()`（激活原死代码）：仅新增、同名不覆盖——zip 中的自定义主题完整保留，17 个内置主题全部补回并落盘；新增 `import io.legado.app.help.DefaultData` |

### 配套

- `app/src/main/assets/updateLog.md`：已按版本交付同步规范追加 **2026/08/17 三条修复记录**（文件夹布局闪退/编辑页保存/主题恢复缩水）。

---

## 四、待完成事项

1. **E2E 验证（模拟器 127.0.0.1:21503，装 3.26.081709 测试包 `io.legado.miss.app.debug`）**
   - [ ] 发现页 → 布局配置 → 分组样式切"Folder"：不崩，卡片正常渲染（底色/图标/圆角，日夜主题下各看一眼）
   - [ ] 订阅源编辑页：修改名称/类型 → 左上角返回 → 弹窗选"是"→ 保存并退出生效；选"否"→ 直接退出不保存
   - [ ] 构造 4 主题版 `themeConfig.json` 的备份 zip → 恢复 → 主题列表 ≥17 且 zip 内自定义主题保留
   - [ ] **问题 2b 复现尝试**：导入 type=1/2 的订阅源 json → 类型分组正确 → 点文章分别走图片库/视频播放器；若不复现，向用户索取老备份 zip 原件再测
   - [ ] **问题 3a 复现尝试**：主题设置 → 切"沉浸式状态栏/导航栏"开关 → 观察各页面系统栏变化；若不复现，向用户确认"不生效"的具体页面与现象
2. **真机验证**：用户真机覆盖安装 3.26.081709 包，回归三个症状
3. **真机崩溃日志取证（如仍闪退）**：App 内置 CrashHandler 会把完整堆栈写到 `/sdcard/Android/data/io.legado.miss.app.debug/cache/crash/`（7 天自动清理）或用户配置的备份目录 `crash/` 子目录，文件管理器取出即可，无需 adb
4. **收尾沉淀**：验证通过后更新 `issues-found.md`、任务 INDEX、`ai_memory_main.md`；如 2b/3a 实测复现，回填根因与修复方案到本文档

---

## 五、经验教训（供后续 Compose/M3 迁移参考）

- **M3 主题属性（`?attr/colorSurface*`、`?attr/colorOn*Variant` 等）只能用于 Material3 主题环境**。本项目 View 体系 Activity 全部基于 `Theme.AppCompat.DayNight.NoActionBar`，View XML 里引用 M3 属性 = 运行时必崩（编译期不报错）；View 体系的主题色一律走 `lib/theme` 扩展（`primaryColor`/`backgroundColor`/`secondaryTextColor`…）运行时注入
- Compose 页（`LegadoTheme` 内）才可用 M3 ColorScheme 槽位；跨体系"视觉对齐"时只对齐数值/比例，不搬运属性引用
- 迁移顶栏/对话框时，注意原 View 体系交互里隐含的**业务钩子**（如本例：`finish()` 覆写里的未保存检测+保存动作），迁移后必须逐条核对行为等价
- 备份恢复"整体覆盖型"配置文件（themeConfig.json 等）在跨版本恢复时会**降级**新版本内置数据，恢复后必须跑一遍"内置默认合并补齐"（`addNewConfigs` 语义）
