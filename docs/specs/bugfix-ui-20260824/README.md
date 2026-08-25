# bugfix-ui-20260824「11 项 UI/功能修复」

> 状态：🔄 设计中（检查点1 用户"需调整"，已并入 3 项新增需求，待重新确认）
> 创建：2026-08-24
> 依据：用户 2026-08-24 反馈 8 项 UI/功能问题 + 检查点1 补充 3 项需求

## 功能概述

针对用户 2026-08-24 反馈的 8 项 UI/功能问题逐项修复，覆盖：订阅源列表图片圆角、搜索框样式统一、顶栏管理颜色生效、订阅布局分组模式设置生效、经典订阅切换头部残留、我的页重复入口、关于页软件名、欢迎页文案；并并入检查点1 新增 3 项：前端 UI 规范沉淀、APK 体积精简分析、订阅页分组管理入口。

## 11 项问题清单

| # | 问题 | 根因（已定位） | 修复方向 |
|---|------|---------------|---------|
| ① | 订阅源文章列表图片仅瀑布样式有圆角 | 订阅源文章列表按 articleStyle 切 5 布局：仅瀑布（item_rss_article_3 CardView 12dp）有圆角；列表/单列/双列/三列（item_rss_article/_1/_2/_4 普通 ImageView）无圆角 | 无圆角 4 布局 ImageView 换 FilletImageView（radius 12dp） |
| ② | 搜索框样式不统一 | 订阅经典=SettingsSearchBar（Compose 浅底 40dp）；发现经典=View SearchView；书架/发现现代=MainTopBarView searchEntry | 按 archive 统一搜索框样式 |
| ③ | 顶栏管理颜色头部未生效 | MyFragment 用 TitleBar；ExploreFragment 经典用 TitleBar——均不读 TopBarConfig | 方案待用户决策（ADR-01） |
| ④ | 订阅布局分组模式视图设置不生效 | RssFragment 用 calculateSpanCount（90dp 屏幕自适应）不读 sourceLayout → 网格列数不生效；"分组"文案未叫"文件夹" | spanCount 读 sourceLayout；文案改"文件夹" |
| ⑤ | 经典订阅切回头部标签未销毁 | initComposeTopBar 未清空现代形态 primaryBar/tagsBar | 经典切换时清空标签 |
| ⑥ | 我的-工具与相关文件管理重复入口 | buildSections L460 有 fileManage；精准管理已有文件管理入口 | 删除重复入口 |
| ⑦ | 关于页头部软件名"阅读Archive" | values-zh app_name_sigma="阅读Archive" | 改为"阅读M" |
| ⑧ | 欢迎页默认"阅读 享受美好时光" | values-zh welcome_title="阅读" | 改为"阅读M" |
| ⑨ | archive 迁移接近尾声未沉淀前端 UI 规范子规范 | docs/project-rules/ 下无前端 UI 规范；ui-standards.md 属 ui-redesign-m3 自研 Compose 化旧规范 | 建立 archive 迁移后的前端 UI 规范子规范并登记 |
| ⑩ | debug 包 70+MB 体积 | debug 无 R8 混淆 dex 130MB 未压缩（主因）；Cronet 双 ABI so 10.9MB | 体积构成分析 + 精简方案（ABI/资源/死代码） |
| ⑪ | 订阅页右上角三点菜单无分组管理入口 | RssFragment.showRssMenu 仅有文件夹配置/阅读记录/动态分组/设置 | 加"分组管理"Action → GroupManageDialog |

## 文档索引

- [spec.md](./spec.md) — 需求规格
- [design.md](./design.md) — 技术设计（含 ADR）
- [tasks.md](./tasks.md) — 任务清单
