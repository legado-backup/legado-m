# spec.md — TVBox/影视仓播放源转化 legado 订阅源

> 状态：🔄 设计中

---

## Intent

影视仓（FongMi/TV）与 legado（阅读M）是两个独立的规则引擎生态。影视仓使用 `Site` bean 描述播放源，依赖 jar 爬虫、采集站私有 API 协议；legado 使用 `RssSource` 描述订阅源，依赖 CSS/JSONPath/XPath/正则/JS 五种解析规则。两套源格式互不兼容，用户无法直接在 legado 中复用影视仓生态积累的播放源。

本功能旨在提供一个**单向转化器**，将影视仓 Site 播放源转化为 legado RssSource 订阅源，降低跨生态迁移成本。转化器不追求 100% 等价还原（jar 爬虫等能力无法等价映射），而是通过明确的降级策略，使转化后的源在 legado 中"可用"，并保留足够信息供用户手动精修。

---

## Scope

### 做什么（In Scope）

1. **字段映射**：将 Site 的核心字段（key/name/api/header/categories/searchable 等）映射到 RssSource 对应字段。
2. **类型适配**：将 Site.type(0=采集API/1=JSON/2=爬虫jar/3=XPath/4=正则) 适配到 legado 规则体系与 RssSource.type(0网页/1图片/2视频)。
3. **规则降级**：对 jar 爬虫、采集站私有 API 提供降级策略（API 直调 / WebView 嗅探），并在 sourceComment 标注降级说明。
4. **批量导入**：解析 TVBox JSON 配置文件（含 `sites` 数组），批量输出 legado 订阅源 JSON 数组。
5. **兼容性验证**：转化后的源需在 legado 中可加载列表、可搜索、可解析正文（视频类按 RssSource.type=2 处理）。
6. **冲突处理**：sourceUrl 唯一性冲突时，按 Site.key 优先、重复跳过并记录日志。

### 不做什么（Out of Scope）

1. **反向转化**：不支持 legado RssSource 转回影视仓 Site。
2. **jar 爬虫等价还原**：不反编译/重写 jar 包，jar 爬虫一律降级处理。
3. **采集站私有 API 协议实现**：不实现影视仓采集站 API 的完整协议（如 Maccms/CMS 采集协议），仅按通用 JSON 接口模板生成规则，需用户校验。
4. **登录态迁移**：不迁移影视仓侧的登录 cookie/token，仅迁移 loginUrl 元信息。
5. **UI 集成**：本规格仅定义转化逻辑与数据契约，不含 legado 内的导入 UI（UI 集成另行立项）。
6. **视频播放器适配**：不修改 legado 视频播放器，依赖现有 RssSource.type=2 的播放链路。

---

## Approach

### Selected Approach

采用**"字段直映 + 类型分派 + 规则模板 + 降级标注"**的离线转化方案：

1. **字段直映**：对语义一致的字段直接映射（key→sourceUrl, name→sourceName, header→header）。
2. **类型分派**：按 Site.type 分派到不同的规则生成器：
   - type=0（采集API）→ 生成通用 JSON 接口模板规则（JSONPath），标注需校验
   - type=1（JSON）→ 生成 JSONPath 规则
   - type=2（爬虫jar）→ 降级为 WebView 嗅探（singleUrl=true + 嗅探配置），标注降级
   - type=3（XPath）→ 生成 XPath 规则
   - type=4（正则）→ 生成正则规则
3. **规则模板**：为 type=0 采集站 API 预置通用模板（列表/搜索/详情），基于站点 api 字段推导。
4. **降级标注**：所有降级项写入 `sourceComment`，格式 `// 降级说明: xxx | 已知上限: xxx | 升级路径: xxx`，符合编码哲学规范。
5. **离线批处理**：转化器以独立工具形式存在（Kotlin object），输入 JSON 文本，输出 JSON 文本，不依赖 Android 运行时。

### Alternatives Considered

| # | 替代方案 | 描述 | 否决理由 |
|---|---------|------|---------|
| A1 | 运行时桥接方案 | 在 legado 运行时内嵌影视仓 Spider 加载器，直接调用 jar 爬虫 | 引入影视仓 jar 依赖，破坏 legado 单一规则引擎架构；rhino 1.8.1 锁定与影视仓爬虫 SDK 可能冲突；维护成本高 |
| A2 | 双向同步方案 | 建立影视仓 Site ↔ legado RssSource 双向同步，保持两侧源一致 | 反向转化无实际需求；双向同步引入冲突解决复杂度；违反"只做必须做的"原则 |
| A3 | 在线服务方案 | 搭建后端转化服务，legado 客户端请求服务获取转化结果 | 引入服务端依赖，破坏 legado 离线优先架构；增加运维成本；用户源数据涉及隐私不应上传 |
| A4 | 手动改写方案 | 提供映射文档，用户手动改写每个源 | 批量场景下人工成本不可接受；无法保证一致性 |

### Drawbacks

1. **降级损失**：jar 爬虫降级为嗅探后，部分站点的列表/搜索能力会失效，需用户手动补规则。
2. **采集站 API 模板覆盖有限**：type=0 采集站 API 协议多样（Maccms/CMS/自定义），通用模板无法覆盖所有变体，部分源需手动校验。
3. **无运行时校验**：离线转化阶段不发起网络请求，无法验证转化后规则的真实可用性，需依赖导入后的 legado 源校验功能。
4. **字段语义偏差**：Site.api 在不同 type 下语义不同（采集API地址/爬虫入口/网页入口），映射到 sourceUrl 时可能不准确，需按 type 分派不同映射策略。

### Prior Art

- legado 现有的书源导入/导出逻辑（`BookSource.kt` 的 GSON 序列化）
- legado `RssSourceExtensions.kt` 的 sortUrl 解析格式（`分类名::url` 分割）
- 影视仓 `Site.objectFrom()` 的 JSON 解析与 UrlUtil.convert 处理

---

## Requirements

### 功能需求

| ID | 需求 | 优先级 |
|----|------|--------|
| R1 | 转化器接受 TVBox JSON 配置文本（含 sites 数组），输出 legado RssSource JSON 数组 | P0 |
| R2 | 字段映射：Site.key→RssSource.sourceUrl，Site.name→RssSource.sourceName | P0 |
| R3 | 字段映射：Site.header(Map)→RssSource.header(JSON 字符串) | P0 |
| R4 | 类型适配：Site.type=1(JSON)/3(XPath)/4(正则) 生成对应规则 | P0 |
| R5 | 类型降级：Site.type=2(jar) 降级为 WebView 嗅探，标注降级说明 | P0 |
| R6 | 类型适配：Site.type=0(采集API) 生成通用 JSON 接口模板规则 | P1 |
| R7 | 字段映射：Site.categories→RssSource.sortUrl（按 `分类名::url` 格式拼接） | P1 |
| R8 | 冲突处理：sourceUrl 重复时跳过并记录日志，不覆盖已有源 | P0 |
| R9 | 降级标注：所有降级项写入 sourceComment，格式遵循编码哲学规范 | P1 |
| R10 | 转化后源的 RssSource.type 按视频类设置为 2 | P0 |
| R11 | 转化器以 Kotlin object 实现，不依赖 Android 运行时，可单元测试 | P1 |
| R12 | 批量场景下单个源转化失败不中断整体流程，记录错误继续 | P0 |

### 非功能需求

| ID | 需求 | 说明 |
|----|------|------|
| N1 | 输出安全 | 转化日志与降级标注不输出源名称/域名/URL 业务数据，用代号替代 |
| N2 | 健壮性 | 入参校验（空 sites 数组、字段缺失）、异常捕获（单个源解析失败不中断）、资源释放 |
| N3 | 可测试性 | 核心映射逻辑为纯函数，可脱离 Android 环境单测 |
| N4 | 遵循代码风格 | 协程用 Coroutine.async 链式封装；错误用 kotlin.runCatching；日志用 AppLog.put |

---

## Scenarios

### 场景 1：批量导入 TVBox 配置

用户持有一份 TVBox JSON 配置文件（内含 50 个 site），希望批量转化为 legado 订阅源。用户将配置文本喂给转化器，转化器逐个解析 site，按 type 分派规则生成器，输出 50 个 RssSource JSON。其中 type=2 的 jar 爬虫源被降级为嗅探并标注，type=0 的采集站源使用通用模板并标注"需校验"。最终用户将输出 JSON 导入 legado 订阅源管理。

### 场景 2：XPath 类型源转化

用户有一个 type=3（XPath）的 site，其 api 指向某网页，categories 含若干分类。转化器将 Site.api 映射为 sourceUrl，按 XPath 规则模板生成 ruleArticles/ruleTitle/ruleLink，将 categories 拼接为 sortUrl（`分类名::url` 格式），header 直映。转化后源可在 legado 中加载分类列表并解析条目。

### 场景 3：jar 爬虫降级处理

用户有一个 type=2（爬虫jar）的 site，依赖特定 jar 包实现列表与搜索。转化器无法还原 jar 逻辑，将该源降级为 singleUrl=true 模式 + WebView 嗅探配置，在 sourceComment 写入 `// 降级说明: jar爬虫无法等价转化，已降级为嗅探 | 已知上限: 列表/搜索可能失效 | 升级路径: 手动编写规则或使用采集API类型`。用户导入后该源可嗅探播放，但列表/搜索需手动补规则。

### 场景 4：冲突与错误处理

用户批量导入时，第 17 个 site 的 key 与已转化源重复，第 23 个 site 的 JSON 字段缺失导致解析异常。转化器对第 17 个跳过并记录日志（用源[17]代号），对第 23 个捕获异常记录错误继续，最终输出 48 个有效源 + 2 条错误日志。整体流程不中断。

### 场景 5：采集站 API 模板生成

用户有一个 type=0（采集API）的 site，api 为采集站接口地址。转化器识别为采集站类型，套用通用 JSON 接口模板（列表 JSONPath `$.list`、标题 `$.name`、链接 `$.id`、搜索 `?wd={{key}}`），生成对应规则，在 sourceComment 标注 `// 降级说明: 采集站API协议未识别，使用通用模板 | 已知上限: 字段路径可能不匹配 | 升级路径: 手动校验字段映射`。用户导入后需校验字段是否匹配实际接口。
