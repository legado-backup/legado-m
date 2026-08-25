# bugfix-ui-20260824 需求规格

## Intent

用户 2026-08-24 反馈 8 项 UI/功能问题，涉及订阅列表、搜索框、顶栏、订阅布局、订阅形态切换、我的页、软件名、欢迎页。目标：逐项定位根因并修复，保持与 archive 视觉/行为对齐，同时保留本项目特有增强。检查点1 补充 3 项：前端 UI 规范沉淀、APK 体积精简、订阅页分组管理入口。

## Scope

**做**：
1. 订阅源/书源/文件夹列表图片统一四角圆弧
2. 搜索框样式统一（订阅/发现/书架/书源管理）
3. 顶栏管理（TopBarConfig）设置颜色后"我的"页头部 + "发现经典"头部生效
4. 订阅布局弹框分组模式（文件夹）下网格列数设置生效；"分组"文案改"文件夹"
5. 经典订阅切换回后头部标签销毁（不残留新版标签）
6. 我的-工具与相关移除重复"文件管理"入口
7. 关于页头部软件名"阅读Archive"→"阅读M"
8. 欢迎页标题"阅读"→"阅读M"
9. 将 archive 迁移后的前端 UI 规范沉淀为子规范（docs/project-rules/）并登记
10. 分析 debug 包体积构成，输出精简方案（ABI/资源/死代码）
11. 订阅页右上角三点菜单加"分组管理"入口

**不做**：
- 不重做订阅/发现页面整体架构
- 不修改视频播放器手势交互体系
- 不触碰数据库结构与迁移
- 不做大版本 APK 精简重构（仅分析与可低成本执行的瘦身项）

**影响模块**：`ui/main/rss/RssFragment`、`ui/main/my/MyFragment`、`ui/main/explore/ExploreFragment`、`ui/widget/MainTopBarView`、`ui/adapter/SourceFolderAdapter`、`ui/book/source/manage/BookSourceScreen`、`ui/rss/source/manage/GroupManageDialog`、`res/values*/strings.xml`、`res/layout/*`、`docs/project-rules/`、`gradle/*`（如 ABI 拆分）。

## Approach

### Selected Approach

逐项最小改动修复，11 项独立推进。核心策略：
- 配置生效类（①④）：让列表渲染读取 `AppConfig.sourceLayout` 等既有配置，而非硬编码自适应
- 顶栏统一类（③）：按用户决策（ADR-01）选择改造方案
- 状态清理类（⑤）：复用 MainTopBarView 既有清空 API
- 文案类（⑦⑧）：strings.xml 值修正
- 入口恢复类（⑪）：复用既有 GroupManageDialog（RssSourceActivity 已用）
- 规范沉淀类（⑨）：基于 archive 迁移后实际 UI 架构建子规范文档
- 体积优化类（⑩）：APK 构成分析 → 输出精简方案 → 低成本项落地

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 重写订阅/发现页为纯 Compose 全新架构 | 工作量大、回归风险高，与"最小改动修复"目标冲突 |
| 顶栏全面统一为 MainTopBarView（含所有子页面） | 影响面过大，仅本次反馈的主界面头部纳入范围 |
| 移除旧 FileManageActivity 功能 | 精准管理等处仍复用，仅移除重复入口 |
| debug 包强制开 R8 | debug 需可调试性，不采用；体积优化以 release 与 ABI/资源为主 |

### Drawbacks

- 任务①/②依赖用户真机确认具体指代界面，若判断偏差需二次调整
- 任务③若选通用 TitleBar 改造，影响面较广需回归验证
- 任务⑩体积精简可能影响 ABI 兼容性（如去 armeabi-v7a 老设备不可用），需权衡

### Requirements

- R1 订阅源文章列表在"列表/单列/双列/三列"布局下图片展示四角圆弧（瀑布已有，补齐其余 4 种）
- R2 订阅头部搜索框与发现/书架/书源管理搜索框样式统一
- R3 顶栏管理设置颜色后"我的"页头部生效
- R4 顶栏管理设置颜色后"发现经典"头部生效
- R5 订阅布局弹框"展示模式=分组（文件夹）"时网格列数设置（如 3 列）实际生效
- R6 订阅布局弹框"分组"文案改为"文件夹"
- R7 新版订阅切回经典订阅后，头部不残留新版标签（primaryBar/tagsBar 清空）
- R8 我的-工具与相关移除"文件管理"重复入口
- R9 关于页头部软件名显示"阅读M"
- R10 欢迎页标题显示"阅读M 享受美好时光"
- R11 建立 archive 迁移后的前端 UI 规范子规范（docs/project-rules/）并登记 INDEX.md + AGENTS.md 子规范加载表
- R12 输出 debug/release 包体积构成分析报告 + 可落地精简项（ABI 拆分/资源/死代码）
- R13 订阅页右上角三点菜单含"分组管理"入口，点击打开订阅源分组管理（GroupManageDialog）

### Scenarios

**正常**：订阅布局弹框选分组模式+网格3列 → 文件夹目录按 3 列展示；新版→经典切换 → 头部标签即时销毁；顶栏管理设色 → 我的/发现经典头部即时换色；订阅页三点菜单 → 分组管理 → 增删改分组即时生效。

**异常**：sourceLayout 非网格值（0 列表/1 紧凑）时订阅源无列表语义 → 回退屏幕自适应列数；分组管理 Dialog 在无分组数据时空态正常。

**边界**：搜索框统一后各页面 placeholder/搜索行为不变；移除重复入口不影响精准管理文件管理功能；ABI 拆分后仅保留 arm64 时老 32 位设备不可用（需用户确认）。
