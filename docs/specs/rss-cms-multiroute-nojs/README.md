# rss-cms-multiroute-nojs：视频订阅源多线路多集零JS解析增强 + CMS采集书源转化

> 状态：✅ 已完成（2026-09-01 用户最终验收）

## 功能概述

本功能围绕视频订阅源对接 MacCMS 聚合采集站，解决两个核心问题：一是确认视频订阅源 `ruleRoutes`（多线路规则）/ `ruleEpisodes`（多集规则）对 `{{$.xxx}}` 大括号模板语法的支持情况；二是将 MacCMS 聚合采集书源（原依赖约 40 行 JS 解析多线路多集）转化为纯规则的视频订阅源，多线路多集解析全部走统一解析层，不使用任何 JS。

背景：MacCMS 采集站的 `vod_play_url` 字段采用分隔符格式 `集名$URL#集名$URL$$$...`（`$$$` 分线路、`#` 分集、`$` 分名址），当前解析层 `parseEpisodesByLines`（`app/src/main/java/io/legado/app/model/rss/Rss.kt` L277-L288）只支持多行 URL，不识别该分隔格式，导致原书源必须内嵌大段 JS。经源码验证，`ruleRoutes`/`ruleEpisodes` 均走 `AnalyzeRule.getString()`（`Rss.kt` L179/L232），`{{...}}` 在 `AnalyzeRule.kt` L740-L757 处理，内容以 `$.` 开头时被 `isRule()`（L783-L788）判定为子规则递归执行——大括号模板语法已天然支持，真正缺口仅在 CMS 分隔格式解析。本次在解析层原生补齐该能力后，所有 CMS 类订阅源统一受益。

变更范围：`app/src/main/java/io/legado/app/model/rss/Rss.kt`（`parseEpisodesByLines` 增强）、新增订阅源 JSON、本目录四文档（README/spec/design/tasks）、`docs/INDEX.md`。

## 核心能力

- **大括号模板语法支持确认**：`ruleRoutes`/`ruleEpisodes` 经 `AnalyzeRule.getString()` 解析，`{{$.xxx}}` 模板由 `isRule()` 判定为子规则递归执行，语法已支持、无需新增实现。
- **数据规范化层（主链路）**：MacCMS 扁平播放字段自动增量注入结构化 routes JSON，规则引擎面对的永远是结构化数据。
- **ruleRoutes / ruleEpisodes 零 JS 规则**：多线路多集全部用纯规则表达；`ruleContent` 留空，走 type=2 多线路模式。
- **列表范式对齐书源目录**：`ruleRoutes` 用 `$.routes[*].name`、`ruleEpisodes` 用 `$.routes[{routeIndex}].episodes`，与 chapterList/chapterName 同心智五种模式随意写；`{routeIndex}` 占位符全模式透明；旧写法回落兼容。
- **搜索支持**：`searchUrl` 支持 `{{page}}` / `{{key}}` 模板参数，直接对接 MacCMS `provide/vod` 采集接口。
- **每站一源转化策略**：聚合站书源靠 loginUi 菜单切换 13 个资源站，订阅源无此机制，改为每个资源站独立一个订阅源；先以量子站验证后批量推广。

## 文档索引

- [spec.md](./spec.md) —— 需求规格（目标、场景、验收标准）
- [design.md](./design.md) —— 技术设计（解析层增强方案、规则设计、转化方案）
- [tasks.md](./tasks.md) —— 实施任务清单

## 关键设计决策速览

1. **复用现有解析链**：`{{$.xxx}}` 大括号模板经 `isRule()` 判定为子规则递归执行，语法零改动直接可用。
2. **增强点收敛在解析层**：CMS 分隔格式（`$$$` / `#` / `$`）支持落在 `parseEpisodesByLines` 统一增强，而非单源硬编码。
3. **大括号模板拼接详情 URL**：`ruleLink` 使用 `https://{站点A-API域名}/api.php/provide/vod?ac=detail&ids={{$.vod_id}}` 动态拼详情地址。
4. **列表范式对齐书源目录（v3）**：规范化层注入结构化 routes 后，`ruleRoutes` 写 `$.routes[*].name`、`ruleEpisodes` 写 `$.routes[{routeIndex}].episodes`，与书源目录 chapterList/chapterName 同心智、五种模式随意写；旧写法（`##\$\$\$##\n` 转行、L2 正则选段）经回落/兜底路径兼容。
5. **静态分类 + 每站一源**：分类字段不走解析层（鸡生蛋设计），`sortUrl` 采用静态分类枚举（实施时拉取 API 取真实 class）；聚合站无菜单切站机制，每站一源、量子站先行验证。
