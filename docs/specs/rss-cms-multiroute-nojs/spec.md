# Spec: rss-cms-multiroute-nojs

> 功能名：rss-cms-multiroute-nojs（视频订阅源多线路多集零 JS 解析增强 + CMS 采集书源转化）
> 状态：📝 设计阶段（OpenSpec 四文档之一：proposal.md / design.md / spec.md / tasks.md）
> 关联先例：`docs/specs/archive/tvbox-source-converter/spec.md`、`docs/specs/rss-video-player-enhancement/design.md`

---

## Intent

### 用户意图（为什么做）

1. **书源 JS 重**：现有 MacCMS 聚合采集书源（13 资源站菜单切换）的多线路（ruleRoutes）/多集（ruleEpisodes）解析内嵌 JS 脚本，JS 执行重、调试难、失败难定位，违背"统一解析层"的长期维护诉求。
2. **解析层不统一**：视频订阅源的多线路多集链路本可完全走 AnalyzeRule.getString() 统一解析层，无需 JS 特例。
3. **CMS 分隔格式不识别**：MacCMS 标准 `vod_play_url` 采用 `$$$` 分线路 / `#` 分集 / `$` 分名址（`集名$URL#集名$URL$$$...`）格式，当前解析层只支持多行 URL 集数格式，不识别该分隔格式 → 需解析层原生增强，一次增强所有 CMS 采集订阅源受益。

### 源码验证结论（本次设计的事实基础）

| 结论 | 源码锚点 | 含义 |
|------|---------|------|
| ruleRoutes/ruleEpisodes 均走 getString() 统一解析层 | Rss.kt #L179、#L232 | 零 JS 可行，链路无需改 |
| `{{...}}` 大括号模板已支持，`$.` 开头内容被 isRule() 判定为子规则递归执行 | AnalyzeRule.kt #L740-L757、#L783-L788 | `{{$.xxx}}` 语法无需改 AnalyzeRule，只需真机确认 |
| `{routeIndex}` / `{routeIndex+1}` 占位符机制已有（先替换占位符再 getString） | Rss.kt #L221-L236 | 规则层可直接用 routeIndex 正则选线路 |
| replaceRegex 语法 `rule##regex##replacement[##first]` 已有 | AnalyzeRule.kt #L770-L780 | 线路名/线路段正则提取无需新语法 |
| 真正缺口：parseEpisodesByLines 只支持多行 URL | Rss.kt #L277-L288 | 唯一需要改代码的点（单函数增强） |

### 转化目标

MacCMS 聚合采集书源（loginUi 菜单切 13 站）→ 视频订阅源**每站一源**。首个目标：量子站（代号 **站点A**，其 API 域名在本文档统一以 `{站点A-API域名}` 占位符表示）。站点A验证通过后，其余 12 站另行确认批量转化（见 Out of Scope）。

### MacCMS API 契约（站点A）

| 接口 | 路径模式 | 关键字段 |
|------|---------|---------|
| 分类 | `/api.php/provide/vod` | `class` 数组（type_id/type_name，本次静态枚举进 sortUrl） |
| 列表 | `?ac=detail&pg={page}&t={type_id}` | list 数组：vod_id / vod_name / vod_pic / vod_remarks |
| 详情 | `?ac=detail&ids={vod_id}` | vod_play_from（`$$$` 分线路名）、vod_play_url（`$$$` 分线路、`#` 分集、`$` 分名址） |
| 搜索 | `?ac=detail&wd={key}` | 同列表结构 |

---

## Scope

### In Scope

1. **大括号模板支持确认**：ruleRoutes/ruleEpisodes 中 `{{$.xxx}}` 模板语法的真机验证（不改 AnalyzeRule，仅验证既有能力）。
2. **解析层增强**：Rss.kt parseEpisodesByLines 增强——识别 `#` 分集 + `$` 分名址（`名$URL`），title 缺省时回退"第N集"；保持旧多行 URL 行为不变。
3. **站点A订阅源 JSON 生成**：ruleRoutes/ruleEpisodes 零 JS 规则（replaceRegex + `{routeIndex}` 占位符正则选线路）、ruleLink 大括号模板、searchUrl、静态 sortUrl 分类枚举。
4. **真机 L2 验证**：分类 → 列表 → 详情多线路 → 切线路 → 集数 → 播放全链路，加旧格式回归测试。

### Out of Scope

| 项 | 理由 |
|----|------|
| AnalyzeRule 通用解析层改动 | 大括号模板与 isRule 子规则递归已支持，无需改动；侵入通用层影响书源/订阅源全部链路，风险大 |
| sortUrl 动态分类 | 分类 Tab 渲染先于请求（"鸡生蛋"架构限制），本次静态枚举；动态化可另立项 |
| 中文线路名映射 | m3u8/bilibili 等英文标识保持原样显示 |
| 付费平台线路解析接口能力 | bilibili/qq 等付费平台线路无解析接口拦截能力，仅 m3u8 直链线路可用 |
| 弹幕（subContent） | 与多线路多集解析无耦合，另行立项 |
| 其余 12 个资源站批量转化 | 站点A验证通过后另行确认，避免批量返工 |

---

## Approach

### Selected Approach

**数据规范化层（主链路）+ 列表范式升级（对齐书源目录）+ 兜底链路，全链路零 JS**：

1. **数据规范化层（主链路）**：Rss.kt 新增 `normalizeMacCmsBody`——详情响应 JSON 含 `vod_play_from`/`vod_play_url` 且带 `$$$` 时，增量注入结构化 `routes: [{name, episodes:[{title,url}]}]`（原字段不动，非 JSON/无特征零侵入，item 已有 routes 时跳过），2 处 `setContent` 调用点前透明生效。
2. **ruleRoutes 列表范式**：`getStringList` 优先取线路名列表，标准写法 `$.routes[*].name`；空时回落 `getString`+`\n` 分割（旧源兼容）。
3. **ruleEpisodes 列表范式**：标准写法 `$.routes[{routeIndex}].episodes`——`{routeIndex}` 占位符对五种模式透明生效，结果 JSON 数组 `[{"title","url"}]` 由 `parseEpisodesResult` 既有 JSON 分支直接消费，title/url 用源数据。
4. **兜底链路**（规范化层不触发的异常数据）：`parseEpisodesResult` 加 routeIndex 参数，结果非 JSON 数组且含 `$$$` 时隐式分组取第 N 组（越界取首组记 AppLog）+ `parseEpisodesByLines` CMS 段解析增强（`#` 分集、`$` limit=2 拆名址、缺名"第N集"、旧纯 URL 行兼容）。
5. **L2 高级可选写法（降级保留非推荐）**：正则选段 `$.list[0].vod_play_url##(?:.*?\$\$\$){routeIndex}(.*?)(?:\$\$\$.*)?$##$1`；线路名兜底写法 `$.list[0].vod_play_from##\$\$\$##\n`（成对 `##` 分段）。
6. **ruleLink（详情链接）**：`{{$.vod_id}}` 大括号模板构造绝对 URL（`/api.php/provide/vod?ac=detail&ids={{$.vod_id}}`，域名占位符）。

**理由**：
- 开发者零负担：源规则纯 JSONPath 随意写，MacCMS 扁平格式适配全部沉淀规范化层与解析层（用户 2026-08-31 检查点意见采纳）。
- 范式同构：与书源目录 chapterList/chapterName 同心智，会写目录就会写多线路多集（用户 2026-08-31 二次意见采纳）。
- 统一解析层：所有 MacCMS 采集订阅源一次受益，后续 12 站转化零增量解析代码。
- 机制最小变更：规范化层 2 处 setContent 调用点接入 + parseEpisodesResult 加 routeIndex 参数（2 处调用点已持有该值）+ parseEpisodesByLines 增强，不动 AnalyzeRule、数据库。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| ruleRoutes/ruleEpisodes 内嵌 JS（照抄原书源） | 用户明确要求不用 JS；多集环境 JS 可行但违背统一解析层诉求 |
| 扩展 AnalyzeRule 新增 CMS 分隔符语法 | 侵入通用解析层影响书源/订阅源全部链路，风险大收益小 |
| ruleEpisodes 全线路串联透传到播放层、播放层按 routeIndex 过滤 | 串联数据冗余，播放器职责越界（格式知识泄漏到播放层）；改为**解析层内部**隐式分组选段（已采纳为 L1 主策略） |
| sortUrl 动态分类（先请求再渲染） | 改变分类导航架构（Tab 渲染先于请求的鸡生蛋设计），风险大，可另立项 |
| 仅正则 replaceRegex 把 `#$` 全转行、不加解析层增强 | replaceRegex 只有一层替换，名$址格式无法拆出 title/url，播放列表质量差 |
| 保持单字符串范式（`getString`+`\n` 分割）不变 | 列表规则（`$.xxx[*].name`）会 toString 失效，与书源目录心智割裂，用户明确否决 |

### Drawbacks（已知缺点 + 接受理由）

| # | 缺点 | 接受理由 |
|---|------|---------|
| 1 | routes 为规范化层隐式契约，与源自带 routes 字段冲突会被跳过规范化 | 注入前检测已存在则跳过并记日志；L2 显式写法可绕开 |
| 2 | 线路名保持英文标识（m3u8/bilibili 等）无中文映射 | 一层 replaceRegex 无法多对多映射，显示影响小 |
| 3 | 付费平台线路（bilibili/qq 等）无解析接口拦截能力，仅 m3u8 直链线路可用 | MacCMS 采集站主流即 m3u8 直链 |
| 4 | URL 含 `#`/`$`/`$$$` 特殊字符时解析受限 | MacCMS m3u8 直链基本不含；解析容错+日志 |
| 5 | sortUrl 静态分类，站点分类变更需更新源 | 分类相对稳定 |

### Prior Art

| 文档 | 可复用经验 |
|------|-----------|
| `docs/specs/archive/tvbox-source-converter/spec.md` | CMS 采集源转化先例，isUrl/baseUrl 陷阱经验 |
| `docs/specs/rss-video-player-enhancement/design.md` | 多线路多集按需采集架构 |
| `docs/project-flow/modules/rss-subsystem.md` | RSS 子系统架构 |

---

## Requirements

> 编号 R1-R8，每条含验收标准；R1-R7 全部通过 + R8 回归通过 = 验收完成。

### R1 ruleRoutes/ruleEpisodes 支持 `{{$.xxx}}` 大括号模板

- **内容**：订阅源规则中使用 `{{$.vod_id}}` 等 JSONPath 大括号模板，由既有 AnalyzeRule 链路处理（#L740-L757 模板 + isRule() #L783-L788 子规则递归）。
- **验收标准**：真机确认模板渲染结果与原书源 JS 等价实现一致（ruleLink 拼接、ruleRoutes/ruleEpisodes 字段提取均正确）。

### R2 数据规范化层 + 兜底解析

- **内容**：①数据规范化层 `normalizeMacCmsBody` 增量注入 routes——原字段不动、非 JSON/无特征零侵入判定、item 已有 routes 字段时跳过并记 AppLog；②兜底链路：`parseEpisodesResult` 加 routeIndex 参数，结果非 JSON 数组且含 `$$$` 时隐式分组取第 N 组（0-based，越界取首组并记 AppLog）+ `parseEpisodesByLines` CMS 段解析增强。
- **验收标准**：①规范化前后原规则取数不变（原字段保留）；②item 已有 routes 字段时跳过规范化不覆盖；③含 `$$$` 串各 routeIndex 选段正确且互不串线。

### R3 ruleRoutes/ruleEpisodes 列表范式（对齐书源目录）

- **内容**：ruleRoutes 标准写法 `$.routes[*].name`（getStringList 优先+回落）；ruleEpisodes 标准写法 `$.routes[{routeIndex}].episodes`——`{routeIndex}` 占位符对 JSONPath/CSS/XPath/JS/正则五种模式透明生效（Rss.kt #L221-L236）。
- **验收标准**：`$.routes[*].name` 列表规则可用（getStringList 优先+回落均正确）；`$.routes[{routeIndex}].episodes` 各 routeIndex 正确互不串线、越界兜底不崩溃（取首组记 AppLog）；五种模式随意写确认。

### R4 ruleRoutes 列表范式回落写法兼容

- **内容**：旧写法 `$.list[0].vod_play_from##\$\$\$##\n` 在 getStringList 回落路径下仍正确（回归保护）。
- **验收标准**：新旧两种写法（`$.routes[*].name` 列表范式 / `$.list[0].vod_play_from##\$\$\$##\n` 回落写法）线路 Tab 一致（英文标识原样显示，不做中文映射）。

### R5 ruleLink 用大括号模板构造绝对详情 URL

- **内容**：`{{$.vod_id}}` 模板拼接 `/api.php/provide/vod?ac=detail&ids={{$.vod_id}}`（域名占位符）。
- **验收标准**：列表点开影片跳转到正确详情，详情字段（vod_name/vod_pic/vod_remarks/vod_play_from/vod_play_url）完整解析。

### R6 搜索功能可用

- **内容**：searchUrl 指向 `?ac=detail&wd={key}` 路径模式，配套搜索列表/详情规则字段。
- **验收标准**：真机搜索关键词返回结果列表，可点开进入详情并播放。

### R7 分类静态枚举可用，全链路真机通过

- **内容**：sortUrl 静态枚举站点A当前分类（type_id/type_name）；分类 → 列表 → 详情 → 播放 L2 全链路。
- **验收标准**：L2 验证脚本全链路通过，翻页正常，播放起播成功。

### R8 不回归现有功能

- **内容**：parseEpisodesByLines 增强不破坏既有集数格式——原多行 URL 格式、JSON 数组集数格式仍正常。
- **验收标准**：用既有正常订阅源（非 CMS 分隔格式）跑回归用例，集数列表与播放与升级前一致。

---

## Scenarios

### S1 分类浏览列表

- **Given**：站点A订阅源已导入且 API 可达
- **When**：进入订阅源，浏览静态分类 Tab 并打开某分类列表
- **Then**：列表按 `?ac=detail&pg={page}&t={type_id}` 路径模式请求并渲染，标题/封面/备注正常，翻页正常

### S2 点开影片多线路采集 + 第一线路集数

- **Given**：列表中某影片 vod_play_from 含 2 个以上线路（`$$$` 分隔）、vod_play_url 含对应多线路集数
- **When**：点开影片
- **Then**：详情页渲染 N 个线路 Tab（顺序与 `$$$` 分段一致），默认第一线路（routeIndex=0），集数列表由第一线路 `名$URL#名$URL` 拆分，title 显示集名

### S3 切换线路按需采集集数

- **Given**：已在某影片详情页，第一线路集数已渲染
- **When**：点击第 2 线路 Tab
- **Then**：ruleEpisodes 以 routeIndex=1 正则选出第二线路段并重新解析集数，按需采集架构下不重复请求网络，集数与第一线路互不串线

### S4 搜索

- **Given**：订阅源搜索规则配置完整
- **When**：在订阅源内搜索某影片名关键词
- **Then**：按 `?ac=detail&wd={key}` 路径模式请求，返回结果列表，点开可进入详情并播放

### S5 旧格式回归（多行 URL 集数源仍正常）

- **Given**：存量订阅源使用多行 URL / JSON 数组集数格式（非 CMS 分隔格式）
- **When**：打开其详情页并解析集数
- **Then**：parseEpisodesByLines 走原有分支行为不变，集数列表与升级前一致，无回归

### S6 单线路边界

- **Given**：某影片 vod_play_from 仅一个线路（无 `$$$` 分隔）
- **When**：打开详情页
- **Then**：只显示一个线路 Tab，ruleEpisodes 正则对无 `$$$` 文本命中第一线路段，集数正常

### S7 title 缺省回退

- **Given**：某线路 vod_play_url 片段为纯 URL（无 `名$` 前缀）
- **When**：解析集数
- **Then**：title 回退为"第N集"，URL 正常，播放可用
