# 全局思考检查清单

> 改动功能前的强制门禁，防止"改 A 功能导致 B 功能 BUG"。在 OpenSpec 步骤1（需求分析）必须填写此清单，未填写不得进入步骤2。

## 触发场景

- 任何涉及3+文件改动的功能优化/新增
- 任何涉及数据库 schema 变更的任务
- 任何涉及多场景交互的功能（如菜单在书源/订阅源/RSS 三个场景）
- 任何涉及字段回填的功能
- 任何涉及 UI 组件新增/迁移的任务

## 检查清单（6维度）

### 1. 前端入口盘点

| 问题 | 说明 |
|------|------|
| 功能有几个入口？ | 列出所有入口位置（Activity/Fragment/Dialog） |
| 入口在哪？ | 精确到文件+行号 |
| 入口改动影响哪些？ | 评估每个入口的改动范围 |

**反模式**：迁移抖音风格重构时只改了 VideoPlayerActivity 的菜单，遗漏了订阅源场景的 `menu_rss_refresh` 和 `menu_browser_open` 菜单项（Issue-3）。

### 2. 后端接口影响

| 问题 | 说明 |
|------|------|
| 动了哪些接口？ | 列出所有被修改的方法/接口 |
| 接口被哪些功能调用？ | 评估调用方是否受影响 |

**反模式**：修改 `CheckSourceService.doCheckSource` 时未评估对校验速度的影响，导致 domainCheckMode 默认值改变后校验变慢（rss-concurrency Issue-7）。

### 3. 数据库改动评估

| 问题 | 说明 |
|------|------|
| 是否改 schema？ | 实体字段新增/删除/类型变更 |
| 是否改 @DatabaseView？ | view SQL 修改必须在 migration 中 DROP+CREATE 重建 |
| migration 是否需要重建 view？ | 修改实体字段必须同步 ALTER TABLE + view 重建 |
| 覆盖安装是否兼容？ | version 必须递增，旧版本覆盖升级必须成功 |

**反模式**：migration_95_96 只 ALTER TABLE 加 lastHost 字段，没有 DROP+CREATE 重建 book_sources_part view，导致覆盖安装触发 IllegalStateException（Issue-1）。

**强制规则**：详见 [database-migration-safety.md](./database-migration-safety.md)。

### 4. 覆盖安装兼容性

| 问题 | 说明 |
|------|------|
| migration 是否可回退？ | Room migration 不可逆，version 已升不会重跑 |
| version 是否递增？ | 必须递增，不可降级 |
| 旧版本覆盖升级是否成功？ | 必须真机验证从旧版本覆盖升级 |

**反模式**：数据库升级导致覆盖安装失败，给用户方案是"卸载重装"，这是规避问题不是解决问题（Issue-1）。

### 5. 使用场景盘点

| 问题 | 说明 |
|------|------|
| 功能在哪些场景使用？ | 如菜单在书源/订阅源/RSS 三个场景 |
| 每个场景的入口都改了吗？ | 逐场景核对，不可遗漏 |

**反模式**：改播放器菜单只考虑视频播放场景，遗漏订阅源 RSS 场景的刷新和浏览器打开菜单项（Issue-3）。

### 6. 回填点盘点

| 问题 | 说明 |
|------|------|
| 新增字段在哪些点回填？ | 必须覆盖真实使用/调试/校验三层 |
| 每层的回填点都列出了吗？ | WebBook/Rss/Debug/CheckSource 全部列出 |

**反模式**：lastHost 字段只在校验层回填（3处），缺失真实使用层（WebBook/Rss）和调试层（Debug），导致字段"有等于没有"（Issue-8）。

## 通用规则（基于本次错误沉淀）

### G1: 新增数据字段必须完成全链路

新增字段时必须同步完成「模型定义 + UI 控件 + Activity 绑定 + 加载/保存逻辑」全链路，不可只改模型不改 UI。

**反模式**：RssSource 已有 `parseConcurrency` 字段，但 `activity_rss_source_edit.xml` 未添加配置控件，`RssSourceEditActivity` 未绑定字段，导致用户找不到配置入口（Issue-5）。

### G2: 新建 UI 组件禁止硬编码颜色

新建 UI 组件时禁止硬编码颜色（如 `#E6121212`），必须使用 `?attr/*` 或 `@color/*` 引用主题色，保证跟随 DayNight 主题切换。

**反模式**：`VideoSettingsPanel` 在 `bg_settings_panel.xml`/`bg_panel_button.xml`/`styles.xml`/`layout_video_settings_panel.xml` 中硬编码9处颜色，整套样式固定暗色，不跟随 DayNight 主题，在亮色主题下与整体风格冲突（Issue-6）。

**正面做法**：
- `bg_settings_panel.xml` 用 `?attr/colorBackground`
- `bg_panel_button.xml` 用 `?attr/colorControlHighlight`
- textColor 用 `?attr/textColorPrimary`

### G3: 迁移/重构功能时必须盘点所有使用场景的菜单项

迁移或重构功能时必须盘点该功能所有使用场景的菜单项，避免遗漏场景。

**反模式**：迁移抖音风格重构时 `video_play.xml` 被精简但遗漏了订阅源场景的 `menu_rss_refresh` 和 `menu_browser_open` 菜单项（Issue-3）。

### G4: DialogFragment/BottomSheetDialogFragment 主题适配

DialogFragment/BottomSheetDialogFragment 在应用级暗色主题下必须用 ThemeStore 动态设置颜色，不能依赖 @color/* 资源引用。

**根因**：应用通过 setTheme 设置暗色主题时，不会激活 values-night 资源限定符，@color/background_card、@color/primaryText、@color/secondaryText 仍返回浅色值。

**正面做法**：
- sheet 背景用 GradientDrawable+ThemeStore.backgroundColor() 动态设置
- TextView 颜色递归遍历 View 树用 ThemeStore.textColorPrimary()/textColorSecondary() 设置

**反模式**：HighlightStyleDialog 和 HighlightRuleEditDialog 依赖 @color/* 资源引用，暗色主题下显示白乎乎一片（Issue-17/17B）。

## 强制门禁

OpenSpec 步骤1（需求分析）必须填写此清单，未填写不得进入步骤2（任务分解）。

填写格式：
```
## 全局思考检查清单
- 前端入口：[入口1, 入口2, ...]
- 后端接口：[接口1, 接口2, ...]
- 数据库改动：[是/否，详情]
- 覆盖安装：[兼容/不兼容，详情]
- 使用场景：[场景1, 场景2, ...]
- 回填点：[点1, 点2, ...]
```
