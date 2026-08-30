# spec.md — TVBox/影视仓播放源转化 legado 订阅源

> 状态：✅ 已实施（七批次转化完成，最终可用订阅源 40 个，归档于 `temp/rss/rss_sources_final.json`）

---

## 实施结果汇总（基于真实真机验证）

> **本节为实施结果反馈**，与下方设计阶段内容形成对照。真实转化率远低于设计阶段预估，原因详见"实施结果分析"。

### 最终可用订阅源

| 批次 | 输入源类型 | 输入数量 | 完整通过数量 | 通过率 | 备注 |
|------|-----------|---------|------------|-------|------|
| batch1 | dzhipy drpy 源 | 10 | 1（博看听书） | 10% | 9 个失败（域名失效3 / 网站改版1 / 服务器关闭1 / drpy JS规则不兼容1 / HTTP不通3） |
| batch2 | dzhipy 源深度验证 | 9（host 可达） | 0 | 0% | 9 个 host 可达源全部播放失败（SPA站点 / 网盘资源站 / 域名劫持 / 反爬拦截 / CSP源无JS / 路径404 / 域名改用途） |
| batch3 | TVBox 源仓库 CMS 采集源 | 6（API 可达） | 6 | 100% | 6 个源全部完整通过（分类加载 + 列表数据 + 详情页播放 + 搜索功能） |
| batch4 | TVBox 源仓库 CMS 采集源 | 28 | 17 | 61% | 9 个直接通过 + 8 个修复后通过（NoVPStarted 修复，isUrl=true 陷阱）；1 个 WARN（搜索接口异常） |
| batch5 | TVBox 源仓库 CMS 采集源 | 15（API 可达） | 5 | 33% | 8 个通过验证，3 个去重，新增 5 个（6 个仓库 840 个 sites 筛选 29 个 CMS 源） |
| batch6 | TVBox 源仓库 CMS 采集源 | 22 | 7 | 32% | 3 个首次通过 + 5 个二次验证通过（uiautomator 精准点击）；1 个去重，新增 7 个 |
| batch7 | 网络搜索 CMS 采集站 | 4 | 4 | 100% | 4/4 全部通过（网络搜索 CMS 采集站） |
| **合计** | - | - | **40** | - | 博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源 |

### 实施结果分析

| 阶段 | 设计预估 | 实际结果 | 偏差原因 |
|------|---------|---------|---------|
| drpy 源转化率 | 30-50% | 10%（1/10） | dzhipy 源大部分失效（域名失效 / 网站改版 / 服务器关闭），drpy JS 规则与 legado 引擎兼容性差 |
| csp_XXX 跳过 | 39 个全部跳过 | 39 个全部跳过 | 设计预估与实际一致 |
| type=1/8 处理 | 单独处理 | 实际未实施 | 实施重心转向 TVBox 源仓库 CMS 采集源 |
| **CMS 采集源转化**（设计阶段未预估） | 未预估 | **batch3 100%（6/6） + batch4 61%（17/28） + batch5 33%（5/15） + batch6 32%（7/22） + batch7 100%（4/4）** | TVBox 源仓库中 type=1 且 api 为 CMS 格式路径的源是最佳转化目标，API 标准、格式统一、成功率高；batch4 发现 isUrl=true 陷阱并修复（§13.10）；batch5-7 发现 uiautomator 精准点击验证方法（§13.11） |

### 转化策略修订（基于实施结果）

| 优先级 | 源类型 | 转化路径 | 实际成功率 | 备注 |
|--------|-------|---------|-----------|------|
| **P0（最高）** | TVBox 源仓库 CMS 采集源（type=1 + api 为 `/api.php/provide/vod/` 格式路径） | 直接套用 CMS 采集源转化模板（详见 design.md §13），含 isUrl=true 陷阱修复（§13.10）+ uiautomator 精准点击验证（§13.11） | batch3 100% + batch4 61% + batch5 33% + batch6 32% + batch7 100% | API 标准、格式统一、成功率高 |
| P1（备选） | dzhipy drpy 源 | Skill 4 阶段闭环转化 | 10% | 失效源多，drpy JS 规则兼容性差 |
| P2（跳过） | csp_XXX 源 | 跳过 | 0% | 依赖 spider.jar 字节码 |

### 归档文件

- **最终可用订阅源**：`temp/rss/rss_sources_final.json`（40 个完整通过的 RssSource JSON）
- **batch3 CMS 采集源筛选结果**：从 3 个 TVBox 源仓库获取 234+49 个 sites，筛选 type=1 且 api 为 CMS 格式路径的源 14 个，其中 6 个 API 可达且完整通过
- **batch4 CMS 采集源筛选结果**：从 TVBox 源仓库获取 28 个 CMS 采集源，9 个直接通过 + 8 个 NoVPStarted 修复后通过（isUrl=true 陷阱修复），1 个 WARN（搜索接口异常），合计 17 个完整通过
- **batch5 CMS 采集源筛选结果**：从 6 个 TVBox 源仓库获取 840 个 sites，筛选 29 个 CMS 源，15 个 API 可达，8 个通过验证，3 个去重后新增 5 个可用源
- **batch6 CMS 采集源筛选结果**：22 个 CMS 源，首次 3 个通过 + 二次验证 5 个通过（uiautomator 精准点击），1 个去重后新增 7 个可用源
- **batch7 CMS 采集源筛选结果**：网络搜索 CMS 采集站 4 个，4/4 全部通过，新增 4 个可用源

---

## Intent

影视仓（FongMi/TV）与 legado（阅读M）是两个独立的规则引擎生态。影视仓使用 `Site` bean 描述播放源，依赖 jar 爬虫、CSP 接口、采集站私有 API 协议与 drpy 框架；legado 使用 `RssSource` 描述订阅源，依赖 CSS/JSONPath/XPath/正则/JS 五种解析规则。两套源格式互不兼容，用户无法直接在 legado 中复用影视仓生态积累的播放源。

本规格采用 **Legado Source Creator Skill 批量转化方案**：以 Skill 的 4 阶段闭环工作流（Phase1 分析 → Phase2 生成+校验 → Phase3 真机验证 → Phase4 自动修复）为核心，将影视仓 Site 播放源转化为 legado RssSource 订阅源 JSON。**不修改任何 legado 源码**，不开发新功能/新文件，不引入运行时依赖。csp_XXX 类型因 spider.jar 重度混淆且 ext 配置非爬虫规则一律跳过。

**实施后转化策略修订**：设计阶段预估 drpy 源转化率 30-50%，实际真机验证仅 10%（域名失效 / 网站改版 / 服务器关闭 / drpy JS 规则兼容性差）。实施中发现 **TVBox 源仓库的 CMS 采集源**（type=1 + api 为 `/api.php/provide/vod/` 格式路径）是最佳转化目标，batch3 成功率 100%（6/6），batch4 成功率 61%（17/28，含 isUrl=true 陷阱修复），batch5-7 继续扩展（batch5 33% 5/15 + batch6 32% 7/22 + batch7 100% 4/4，含 uiautomator 精准点击验证）。最终可用订阅源 40 个（博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源），归档于 `temp/rss/rss_sources_final.json`。详见上方"实施结果汇总"。

---

## 数据源分析（基于 dzhipy index.json 真实数据）

### 数据源入口

| 项 | 值 |
|----|----|
| 入口配置文件 | `dzhipy` 的 `index.json`（用户提供 URL：`/path/to/index.json` 模式，GitLab raw 形式） |
| Site 总量 | 435 个 |
| 数据形态 | 单一 JSON 文件含 sites 数组 |

### Site 类型分布

| Site.type | 含义 | 数量 | 占比 | 转化可行性 |
|-----------|------|------|------|-----------|
| 3 | 爬虫jar / CSP 接口 / drpy | 433 | 99.5% | drpy 子类型可转化（394 个），csp_XXX 跳过（39 个） |
| 1 | JSON 解析 | 1 | 0.2% | 单独处理（API 类型，ext=null） |
| 8 | 待确认含义 | 1 | 0.2% | 单独处理（api=null, ext=null，待确认） |
| **合计** | - | **435** | 100% | - |

> 注：本次数据**没有 type=0（采集站 API）和 type=4（正则）** Site，与旧版 lmw.json 数据分布不同。

### type=3 细分（主导类型，433 个）

| 子类型 | 数量 | 占比（type=3 内） | api 字段特征 | ext 字段特征 | 转化可行性 |
|--------|------|------------------|------------|------------|-----------|
| 声明式 drpy Site | 394 | 90.99% | `drpy2.min.js` | JS 文件路径（base64+gzip / base64 纯编码 / AES 加密） | 可转化 |
| csp_XXX 接口 | 39 | 9.01% | `csp_XXX`（36 个唯一类名） | 依赖 spider.jar | 不可转化 |

### drpy 类型深度分析（394 个，占总量 90.6%）

#### JS 脚本编码方式（5 样本分析 + 全量统计修订）

> **修订说明（基于实际解密尝试）**：原"疑似 AES 加密"已通过实际解密尝试确认为 AES-128-CBC-PKCS7 加密，密钥从 drpy2.js 框架源码提取。全量统计：13/392 = 3.3% 的 drpy JS 文件为 AES 加密。

| 编码方式 | 样本数（5样本） | 全量统计 | 识别特征 | 处理策略 |
|---------|--------|---------|---------|---------|
| base64 + gzip 编码 | 2/5 | - | 解码后以 `H4sI` 开头（gzip 魔数） | base64 解码 → gzip 解压 → 明文 JS |
| base64 纯编码 | 1/5 | - | 解码后为合法 JS 语法 | base64 解码 → 明文 JS |
| AES 加密（已确认） | 2/5 | 13/392（3.3%） | 类型A：`h36A5I5KdeB29zb3` 前缀 + base64；类型B：纯 base64 无前缀 | 使用从 drpy2.js 提取的密钥解密（详见 AES 加密实际解密结论） |
| 明文 | 0/5 | - | - | - |

#### AES 加密实际解密结论（基于真实解密尝试）

> **修订说明（基于用户第四次确认反馈）**：原描述"尝试常见密钥解密，失败则降级跳过"已替换为实际解密尝试的结论。

| 分析项 | 结论 |
|--------|------|
| **加密算法** | AES-128-CBC-PKCS7（已确认） |
| **密钥来源** | 从 drpy2.js 框架源码中提取（两组密钥：Hex 格式 16 字节 + Utf8 格式 16 字节） |
| **密钥派生方式** | `CryptoJS.enc.Hex.parse(硬编码值)` 和 `CryptoJS.enc.Utf8.parse(硬编码值)` |
| **加密流程** | 明文 JS → AES-128-CBC 加密 → PKCS7 填充 → [前缀 +] Base64 编码 |
| **加密前缀** | 类型A：`h36A5I5KdeB29zb3`（2 个文件）；类型B：纯 base64 无前缀（11 个文件） |
| **解密成功率** | 4/13 = 30.8%（使用 Hex 密钥组） |
| **解密后内容** | 合法 JS 规则代码，含 `var rule = {...}` 结构，含 title/host/url/searchUrl 等字段 |
| **失败原因** | 9 个解密失败文件中：7 个因 base64 解码后长度非 16 倍数；2 个因 padding 错误（可能使用不同编码方式或额外处理如 gzip 压缩后再加密） |
| **总加密文件数** | 13/392 = 3.3%（drpy_js/ 目录） |
| **处理策略** | Python 脚本使用从 drpy2.js 提取的两组密钥尝试 AES-128-CBC-PKCS7 解密；解密成功的按明文 JS 流程继续转化；解密失败的降级跳过 |

> **安全要求**：密钥值完全隐藏为 `***`，只保留长度（16 字节）；不输出密钥明文；解密日志只记录成功/失败和技术原因。

#### drpy rule 对象字段分析

- **实测字段数**：25 个不同字段
- **高频字段**：`title` / `host` / `filter_url` / `searchUrl` / `filter` / `lazy`
- **drpy2.min.js 框架访问的 rule 字段**：47 个（含完整字段集）
- **rule 对象完整字段清单**（25 实测 + 框架支持）：
  `title` / `host` / `homeUrl` / `detailUrl` / `searchUrl` / `url` / `filterable` / `filter_url` / `filter` / `filter_def` / `headers` / `timeout` / `class_name` / `class_url` / `limit` / `multi` / `searchable` / `play_parse` / `lazy` / `推荐` / `一级` / `二级` / `搜索` / `预处理` / `double`

#### drpy2.min.js 框架结构

- **函数数量**：88 个
- **依赖库**：8 个（`cheerio` / `crypto-js` / `jsencrypt` / `node-rsa` / `pako` / `json5` / `jinja` / `gbk`）
- **ES6 模块问题**：drpy2.min.js 使用 `import` / `export` 语法，legado Rhino 1.8.1 不支持 ES6 模块
- **处理策略**：在 Skill Phase 1/2 阶段静态提取 rule 对象，剥离框架依赖，不引入运行时框架

#### legado 内置 JS 加解密工具（用户反馈）

legado 内置 JS 加解密工具，可通过 `<js>` 标签调用。对于 AES 加密的 JS 脚本（AES-128-CBC-PKCS7），Python 脚本在 Phase 1 阶段使用从 drpy2.js 框架源码提取的密钥解密（成功率约 30.8%），不依赖 legado 运行时解密。

### csp_XXX 类型深度分析（39 个，占总量 9.0%）

#### csp_XXX 类名分布

- 36 个唯一 csp_类名（部分类名对应多个 Site）

#### spider.jar 深度分析结论

| 分析项 | 结论 |
|--------|------|
| Spider 类总数 | 196 个（132 主类 + 64 内部类） |
| 混淆程度 | 65%（86/132 主类）被重度混淆（Lv3：逐字节 `aput-byte` 构造加密数组） |
| 配置传入方式 | 通过 `init(Context, String)` 方法运行时传入，不嵌入 DEX |
| DEX 内容 | 仅包含解析逻辑和少量硬编码 API 路径（如 `/api/fs/get` 等 AList 类路径） |
| 静态分析可行性 | **无法完全还原 csp_XXX 爬虫逻辑** |

#### ext 配置文件分析结论

| 配置文件 | 内容类型 | 说明 |
|---------|---------|------|
| 配置 1.json | `filter_config` | 筛选器配置 |
| 配置 2.json | `empty` | 空对象 |
| 配置 3.json | `pan_config` | 网盘配置（29 个字段：token / oauth / quark / uc / thunder / pikpak 等） |
| 配置 4.json | `filter_config` | 筛选器配置 |
| 配置 5.json | 获取失败 | 外部 URL |

**核心结论**：ext 配置只是网盘运行时配置和 UI 筛选器，**不是爬虫解析规则**。

#### csp_XXX 转化可行性

csp_XXX 类型无法通过 ext 配置直接转化为 legado RssSource，爬虫逻辑在 spider.jar Java 代码中（且 65% 重度混淆）。**一律跳过**。

### 关键障碍

1. **drpy2.min.js 框架使用 ES6 import/export**：legado Rhino 1.8.1 不支持 ES6 模块语法，需在 Skill 转化阶段提取 rule 对象并剥离框架依赖。
2. **csp_XXX 依赖 spider.jar**：核心逻辑封装在 spider.jar 字节码中，65% 重度混淆，ext 配置非爬虫规则，无法通过配置转化。
3. **部分 drpy JS 脚本加密**：全量统计 13/392（3.3%）为 AES-128-CBC-PKCS7 加密，密钥从 drpy2.js 框架源码提取（两组：Hex 格式 16 字节 + Utf8 格式 16 字节）。实际解密成功率 4/13 = 30.8%（使用 Hex 密钥组）；9 个解密失败文件中 7 个因 base64 解码后长度非 16 倍数、2 个因 padding 错误。解密失败的降级跳过。

---

## Scope

### 做什么（In Scope）

1. **使用 Skill 分析 drpy JS 脚本结构**：批量获取 394 个 drpy Site 的 ext JS 脚本，识别编码方式（base64+gzip / base64 纯编码 / AES 加密）。
2. **解码 JS 脚本**：对 base64+gzip 编码执行 base64 解码 + gzip 解压；对 base64 纯编码执行 base64 解码；对 AES 加密（AES-128-CBC-PKCS7）使用从 drpy2.js 框架源码提取的两组密钥尝试解密，解密成功率约 30.8%，无法解密的降级跳过。
3. **提取 rule 对象**：从解码后的 JS 中提取 drpy rule 对象（25 实测字段 + 框架支持 47 字段），剥离 drpy2.min.js 框架依赖。
4. **字段映射**：基于真实 25 字段分析，将 drpy rule 对象字段映射为 legado RssSource 字段（见字段映射表）。
5. **使用 Skill Phase 2 生成 + 校验**：使用 Legado Source Creator Skill Phase 2 生成 RssSource JSON，执行 sanitize 处理与 MandatoryFieldValidator 校验。
6. **使用 Skill Phase 3 真机验证**：使用 Skill Phase 3 在真机/模拟器上验证转化后源的可用性（列表加载、搜索、播放地址解析）。
7. **使用 Skill Phase 4 自动修复**：对 Phase 3 验证失败的源，使用 Skill Phase 4 自动修复规则。
8. **type=1 单独处理**：1 个 type=1 Site（API 类型，ext=null）单独使用 Skill 转化。
9. **type=8 单独处理**：1 个 type=8 Site（api=null, ext=null，待确认含义）单独分析后决定转化策略。
10. **输出安全**：所有转化日志、降级标注、报告均不输出源名称/域名/URL 业务数据，用代号（源[N] / 站点A / 站点B）替代，路径模式化（`/path/{id}`）。
11. **TVBox 源仓库 CMS 采集源转化**（实施阶段新增）：从 TVBox 源仓库获取 sites 数组，筛选 type=1 且 api 为 CMS 格式路径（如 `/api.php/provide/vod/`）的源，套用 CMS 采集源转化模板（详见 design.md §13），含 isUrl=true 陷阱修复（§13.10）+ uiautomator 精准点击验证（§13.11），通过 Skill Phase 2/3/4 完成校验与真机验证。此为实施阶段发现的最佳转化路径，batch3 成功率 100%（6/6），batch4 成功率 61%（17/28，含 isUrl=true 陷阱修复），batch5-7 继续扩展（batch5 33% 5/15 + batch6 32% 7/22 + batch7 100% 4/4，含 uiautomator 精准点击验证）。
12. **归档最终可用源**：将通过真机验证的 40 个 RssSource JSON 归档到 `temp/rss/rss_sources_final.json`。

### 不做什么（Out of Scope）

1. **不修改任何 legado 源码**：不新增 Kotlin 文件，不修改现有源码，不引入新依赖。
2. **不开发新功能/新文件**：不实现 TvBoxSourceConverter object/类/方法，不新增 UI 集成入口，不编写单元测试。
3. **不引入 drpy2.min.js 框架运行时依赖**：仅在 Skill 转化阶段静态分析 rule 对象，不在 legado 运行时引入框架。
4. **不逆向 spider.jar 的 Java 代码**：csp_XXX 类型一律跳过，不反编译/重写 spider.jar。
5. **csp_XXX 类型跳过**：39 个 csp_XXX Site 不转化，记录到跳过列表（用源[N]代号）。
6. **反向转化**：不支持 legado RssSource 转回影视仓 Site。
7. **登录态迁移**：不直接迁移影视仓侧的登录 cookie/token；若源涉及登录，通过 JS 自动登录方案获取 cookie（详见"JS 自动登录获取 cookie 方案"），**禁止让用户手动登录**。
8. **采集站私有 API 协议实现**：type=1 Site 仅按通用 JSON 接口模板生成规则，不实现完整采集协议。

---

## Approach

### Selected Approach

采用 **Legado Source Creator Skill 4 阶段闭环工作流**：

#### Phase 1：分析

1. 读取 dzhipy index.json，遍历 435 个 Site。
2. 按 type 分类：type=3（433 个）→ 细分 drpy（394 个）/ csp_XXX（39 个）；type=1（1 个）；type=8（1 个）。
3. 对 394 个 drpy Site 批量获取 ext 指向的 JS 脚本内容。
4. 识别每个 JS 脚本的编码方式（base64+gzip / base64 纯编码 / AES 加密，全量统计 13/392 = 3.3%）。
5. 解码 JS 脚本，提取 drpy rule 对象，分析 25 字段分布。
6. csp_XXX（39 个）直接标记跳过。

#### Phase 2：生成 + 校验

1. 基于 drpy rule 对象字段映射表，将 rule 字段映射为 RssSource 字段。
2. 选择器语法转换：drpy 选择器（CSS / XPath / 正则 / JSONPath）→ legado 选择器语法。
3. 使用 Legado Source Creator Skill 生成 RssSource JSON。
4. 执行 sanitize 处理（清理非法字段、规范化格式）。
5. 执行 MandatoryFieldValidator 校验（12 个必填字段：sourceName / sourceUrl / sourceIcon / sourceComment / searchUrl / sortUrl / ruleArticles / ruleNextArticles / ruleTitle / rulePubDate / ruleImage / ruleLink；正文必填：ruleContent；固定字段：type=2 / articleStyle=2）。
6. 对 AES 加密的 JS，Python 脚本在 Phase 1 阶段已使用从 drpy2.js 提取的两组密钥尝试 AES-128-CBC-PKCS7 解密（成功率约 30.8%）；解密成功的按明文 JS 流程继续，解密失败的降级跳过。
7. type=1 Site 单独使用 Skill 转化（通用 JSON 模板 + JSONPath）。
8. type=8 Site 单独分析后决定策略。

#### Phase 3：真机验证

1. 使用 Skill Phase 3 在真机/模拟器上导入转化后的 RssSource JSON。
2. 验证每个源的：列表加载、搜索功能、播放地址解析。
3. 记录验证结果（用源[N]代号），失败的源进入 Phase 4。

#### Phase 4：自动修复

1. 对 Phase 3 验证失败的源，使用 Skill Phase 4 自动修复规则。
2. 修复后重新执行 Phase 3 验证。
3. 仍失败的源标注降级说明，保留原始规则供用户手动修正。

#### 降级标注

所有降级项写入 `sourceComment`，格式：`// 降级说明: xxx | 已知上限: xxx | 升级路径: xxx`。

### drpy rule → legado RssSource 字段映射表（基于真实 25 字段分析 + 12 必填字段扩充）

> **字段级别说明**：MANDATORY=必填（缺失校验失败）/ FIXED=固定值 / OPTIONAL=可选。基于用户第四次确认反馈，12 个必填字段全部提升为 MANDATORY。

| drpy rule 字段 | legado RssSource 字段 | 字段级别 | 映射说明 |
|---------------|----------------------|---------|---------|
| Site.icon / drpy 无 | `sourceIcon` | MANDATORY | 直映 Site.icon（缺失时填占位符，标注降级说明） |
| `title` | `sourceName` | MANDATORY | 直映 |
| `host` | `sourceUrl` | MANDATORY | 直映（冲突时追加 Site.key 后缀），PK |
| -（降级标注专用） | `sourceComment` | MANDATORY | 用于写入降级说明、登录状态、已知上限等信息；无降级时填空字符串 |
| `searchUrl` | `searchUrl` | MANDATORY | 直映（需转换搜索参数占位符） |
| `class_name` / `class_url` | `sortUrl` | MANDATORY | 按 `分类名::url` 格式拼接（缺失时填占位分类） |
| `推荐` / `一级` | `ruleArticles` | MANDATORY | 选择器语法转换（首页推荐 + 一级分类列表规则合并） |
| `url`（分页 URL） | `ruleNextArticles` | MANDATORY | 选择器语法转换（下一页列表规则，drpy 的 url 字段映射） |
| `一级`（标题部分） | `ruleTitle` | MANDATORY | 选择器语法转换（标题规则） |
| -（drpy 无直接对应） | `rulePubDate` | MANDATORY | 发布日期规则；drpy 无直接字段时填占位规则并标注降级 |
| `一级`（图片部分） | `ruleImage` | MANDATORY | 选择器语法转换（图片规则） |
| `detailUrl` / `一级`（链接部分） | `ruleLink` | MANDATORY | 选择器语法转换（详情页链接规则） |
| `二级` | `ruleContent` | MANDATORY | 选择器语法转换（详情页解析规则，含视频播放地址） |
| `lazy` | `ruleContent` 内 JS | MANDATORY（嵌入） | 懒加载解析逻辑，通过 `<js>` 标签调用，嵌入 ruleContent |
| -（固定） | `type` | FIXED | 固定为 2（视频类型） |
| -（固定） | `articleStyle` | FIXED | 固定为 2（视频列表样式） |
| `homeUrl` | `singleUrl` | OPTIONAL | 直映（如存在） |
| `headers` | `header` | OPTIONAL | Map → JSON 字符串 |
| `filter_url` | `sortUrl` 拼接 | OPTIONAL（嵌入） | 筛选器 URL 参数拼接（嵌入 sortUrl） |
| `filter` | `sortUrl` 扩展 | OPTIONAL（嵌入） | 筛选器定义（需转换为 legado 筛选器格式） |
| `filter_def` | `sortUrl` 扩展 | OPTIONAL（嵌入） | 默认筛选值 |
| `play_parse` | `enableJs` | OPTIONAL | true → enableJs=true |
| `timeout` | `loadWithBaseUrl` 相关 | OPTIONAL | 超时设置映射 |
| `searchable` | `enabled` | OPTIONAL | 0→false, 1→true, 2→false |
| `预处理` | `ruleArticles` 前置 JS | OPTIONAL（嵌入） | 预处理脚本，通过 `<js>` 标签调用 |
| `multi` / `double` | `articleStyle` 辅助 | OPTIONAL（参考） | 是否多线路/二级页面，参考映射到列表样式（固定为 2 时忽略） |
| Site.key | `customOrder` | OPTIONAL | 排序字段 |
| `limit` / `filterable` | - | 不映射 | legado 无对应字段 |

#### drpy2.min.js 框架访问的 47 个 rule 字段说明

drpy2.min.js 框架在运行时会访问 47 个 rule 字段（含上述 25 实测字段 + 22 个框架扩展字段）。转化时仅需映射实测出现的 25 字段，框架扩展字段（未在样本中出现）不映射。

#### legado 内置 JS 加解密工具使用说明（基于实际密钥的解密方案）

> **修订说明（基于用户第四次确认反馈）**：原"尝试常见密钥解密"已替换为使用从 drpy2.js 框架源码提取的实际密钥的解密方案。

对于 AES 加密的 drpy JS 脚本（AES-128-CBC-PKCS7），Python 脚本在 Phase 1 解码阶段使用从 drpy2.js 框架源码提取的两组密钥尝试解密：

1. **密钥组1（Hex 格式，16 字节）**：`CryptoJS.enc.Hex.parse(***)` 派生，成功率 30.8%
2. **密钥组2（Utf8 格式，16 字节）**：`CryptoJS.enc.Utf8.parse(***)` 派生，作为备选

解密成功后得到的明文 JS 含 `var rule = {...}` 结构，按场景 2 流程继续转化。解密失败的降级跳过。

**Python 解密流程**（密钥值完全隐藏为 `***`）：

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64

# 密钥从 drpy2.js 框架源码提取（完全隐藏，只保留长度）
KEY_HEX = b'***'  # 16 字节，Hex 格式
KEY_UTF8 = b'***'  # 16 字节，Utf8 格式
PREFIX_A = 'h36A5I5KdeB29zb3'  # 类型A前缀

def try_aes_decrypt(encrypted_b64: str) -> str:
    """尝试使用从 drpy2.js 提取的两组密钥解密"""
    # 剥离类型A前缀
    if encrypted_b64.startswith(PREFIX_A):
        encrypted_b64 = encrypted_b64[len(PREFIX_A):]
    encrypted_bytes = base64.b64decode(encrypted_b64)
    # 长度必须为16倍数
    if len(encrypted_bytes) % 16 != 0:
        return None
    # 尝试两组密钥
    for key in [KEY_HEX, KEY_UTF8]:
        try:
            cipher = AES.new(key, AES.MODE_CBC, key)  # IV=KEY（drpy2.js 框架默认）
            decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            result = decrypted.decode('utf-8')
            if 'var rule' in result:
                return result
        except Exception:
            continue
    return None
```

> **安全要求**：密钥值完全隐藏为 `***`，只保留长度（16 字节）；不输出密钥明文；解密日志只记录成功/失败和技术原因（长度非16倍数/padding 错误）。

### JS 自动登录获取 cookie 方案

> **修订说明（基于用户第四次确认反馈）**：用户要求"如果涉及到登录，要通过 JS 的方式自动登录获取 cookie，别让用户登录"。本节描述自动登录方案，**禁止让用户手动登录**。

#### 登录场景识别

Python 脚本在 Phase 1 分析阶段识别 drpy rule 对象中是否存在登录相关配置：

| drpy rule 字段 | 用途 | 识别方式 |
|----------------|------|---------|
| `headers` 中的 `Cookie` / `Authorization` | 已有登录态 | 检查 headers 字段是否含 Cookie/Authorization 键 |
| `login_url` | 登录端点 | 检查 rule 对象是否含 login_url 字段 |
| `login_method` | 登录方法（GET/POST） | 检查 rule 对象是否含 login_method 字段 |
| `login_headers` | 登录请求头 | 检查 rule 对象是否含 login_headers 字段 |
| ext 配置中的登录凭据 | 用户名/密码/token | 检查 ext 复合结构是否含凭据字段 |

**识别结论**：
- 若检测到上述任一字段 → 标记为"涉及登录"，启用 JS 自动登录方案
- 若未检测到 → 不涉及登录，跳过本方案

#### JS 自动登录实现方案

在生成的 RssSource 中，通过 `<js>` 标签实现自动登录，登录流程嵌入到 `header` 字段的 JS 规则中：

1. **检测 cookie 是否过期**：检查现有 cookie 是否存在且未过期
2. **发送登录请求**：通过 `http.post()` 发送登录请求（POST 用户名/密码到登录端点）
3. **提取响应中的 cookie/token**：从登录响应中提取 Set-Cookie 或 token 字段
4. **注入到后续请求的 header 中**：将 cookie/token 注入到所有后续请求的 header

**登录凭据来源**：
- 优先从 drpy rule 对象的 `login_url` / `login_headers` 字段提取
- 其次从 ext 复合配置中提取
- **禁止让用户手动登录**：所有登录逻辑通过 JS 自动完成

#### JS 自动登录代码模板（示例模式，不含真实凭据）

```javascript
@js:
// 检测cookie是否过期
var cookie = getCookie("session_key");
if (!cookie || isExpired(cookie)) {
    // 自动登录获取cookie
    var loginUrl = "***";  // 站点A登录端点（凭据完全隐藏）
    var loginData = "***";  // 登录凭据（从drpy rule提取，不输出明文）
    var resp = http.post(loginUrl, loginData);
    cookie = extractCookie(resp);
    setCookie("session_key", cookie);
}
// 注入cookie到请求头
header["Cookie"] = cookie;
```

> **安全要求**：登录端点 URL 用代号替代（站点A登录端点）；登录凭据（用户名/密码/token）在输出中完全隐藏为 `***`；cookie 内容只记录长度和是否成功，不引用完整值。

#### 登录降级策略

| 场景 | 降级处理 | sourceComment 标注 |
|------|---------|-------------------|
| drpy rule 中无登录凭据 | 标注降级说明，跳过自动登录 | `// 降级说明: 需要登录但无凭据 | 已知上限: 已跳过 | 升级路径: 手动配置登录凭据` |
| 自动登录失败（网络错误） | 标注降级说明，跳过该源 | `// 降级说明: 自动登录失败（网络错误） | 已知上限: 已跳过 | 升级路径: 检查登录端点可达性` |
| 自动登录失败（凭据错误） | 标注降级说明，跳过该源 | `// 降级说明: 自动登录失败（凭据错误） | 已知上限: 已跳过 | 升级路径: 检查登录凭据` |
| 自动登录成功 | 注入 cookie 到 header，继续转化 | sourceComment 写入 `// 登录状态: 自动登录成功（cookie长度=N）` |

#### 安全要求

1. **登录凭据完全隐藏**：用户名/密码/token 在所有输出中完全隐藏为 `***`
2. **cookie 内容脱敏**：只记录长度和是否成功，不引用完整 cookie 值
3. **登录端点代号化**：用"站点A登录端点"替代真实 URL
4. **不输出原始登录响应**：只输出技术结论（成功/失败、cookie 长度）

### Alternatives Considered

| # | 替代方案 | 描述 | 否决理由 |
|---|---------|------|---------|
| A1 | 开发新功能（Kotlin object + 14 个新文件 + UI 集成） | 在 legado 源码中实现 TvBoxSourceConverter | 违反"不修改源码"约束；维护成本高；破坏 legado 单一规则引擎架构；已有 Skill 可复用 |
| A2 | 运行时桥接方案 | 在 legado 运行时内嵌影视仓 Spider 加载器与 drpy2.min.js 框架 | 引入影视仓 jar 与 ES6 模块依赖；rhino 1.8.1 不支持 ES6 import/export；维护成本高 |
| A3 | 在线服务方案 | 搭建后端转化服务，legado 客户端请求服务获取转化结果 | 引入服务端依赖，破坏 legado 离线优先架构；用户源数据涉及隐私不应上传 |
| A4 | 手动改写方案 | 提供映射文档，用户手动改写每个源 | 批量场景下（394 个 drpy Site）人工成本不可接受；无法保证一致性 |
| A5 | 全量 csp_XXX 反编译 | 反编译 spider.jar 还原 csp_XXX 逻辑 | 法律风险；spider.jar 65% 重度混淆；ext 配置非爬虫规则；维护成本极高 |

### Drawbacks

1. **csp_XXX 跳过损失**：39 个 csp_XXX Site（9.0%）一律跳过，无法转化。
2. **加密 JS 解密有限**：全量统计 13/392（3.3%）为 AES-128-CBC-PKCS7 加密，使用从 drpy2.js 提取的密钥解密成功率仅 30.8%（4/13），9 个解密失败的对应 Site 降级跳过（7 个因长度非 16 倍数、2 个因 padding 错误）。
3. **drpy 选择器兼容性**：drpy rule 对象的选择器语法与 legado 不完全兼容，部分选择器无法转换，需 Phase 4 自动修复或用户手动修正。
4. **type=8 含义待确认**：1 个 type=8 Site（api=null, ext=null）含义待确认，可能无法转化。
5. **无运行时校验（Phase 2 阶段）**：Skill Phase 2 生成阶段不发起网络请求，需 Phase 3 真机验证才能确认规则可用性。

### Prior Art

- Legado Source Creator Skill 的 4 阶段闭环工作流（Phase1 分析 → Phase2 生成+校验 → Phase3 真机验证 → Phase4 自动修复）
- legado 现有的书源/订阅源导入逻辑（`BookSource.kt` / `RssSource.kt` 的 GSON 序列化）
- legado `RssSourceExtensions.kt` 的 sortUrl 解析格式（`分类名::url` 分割）
- legado 内置 JS 加解密工具（通过 `<js>` 标签调用）
- drpy2.min.js 框架的 rule 对象规范（静态分析，不引入运行时依赖）

---

## Requirements

### 功能需求

#### 数据源分析需求（使用 Skill 完成）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-DS1 | 使用 Skill 读取 dzhipy index.json，解析并遍历所有 435 个 Site | P0 |
| R-DS2 | 使用 Skill 按 type 分类 Site：type=3（433 个）/ type=1（1 个）/ type=8（1 个） | P0 |
| R-DS3 | 使用 Skill 对 type=3 细分：drpy（394 个，api=drpy2.min.js）/ csp_XXX（39 个，api=csp_XXX） | P0 |
| R-DS4 | 使用 Skill 批量获取 394 个 drpy Site 的 ext JS 脚本内容 | P0 |
| R-DS5 | 使用 Skill 识别每个 JS 脚本的编码方式（base64+gzip / base64 纯编码 / AES 加密） | P0 |

#### drpy JS 解码与 rule 提取需求（使用 Skill 完成）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-DR1 | 使用 Skill 对 base64+gzip 编码执行 base64 解码 + gzip 解压，得到明文 JS | P0 |
| R-DR2 | 使用 Skill 对 base64 纯编码执行 base64 解码，得到明文 JS | P0 |
| R-DR3 | 使用 Skill 对 AES 加密 JS 使用从 drpy2.js 提取的两组密钥（Hex 格式 16 字节 + Utf8 格式 16 字节）尝试 AES-128-CBC-PKCS7 解密；解密成功率约 30.8%，无法解密的降级跳过 | P1 |
| R-DR4 | 使用 Skill 从解码后的 JS 中提取 drpy rule 对象（25 实测字段），剥离 drpy2.min.js 框架依赖 | P0 |
| R-DR5 | 解码失败的源记录到降级跳过列表（用源[N]代号），不中断整体流程 | P0 |

#### 字段映射需求（使用 Skill 完成）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-DM1 | 使用 Skill 按 drpy rule → RssSource 字段映射表完成字段映射：title→sourceName, host→sourceUrl, searchUrl→searchUrl | P0 |
| R-DM2 | 使用 Skill 完成字段映射：推荐/一级→ruleArticles, 二级→ruleContent（含 lazy 懒加载，通过 `<js>` 标签调用） | P0 |
| R-DM3 | 使用 Skill 完成字段映射：class_name/class_url→sortUrl（按 `分类名::url` 格式拼接） | P1 |
| R-DM4 | 使用 Skill 完成字段映射：headers→header（Map→JSON 字符串） | P1 |
| R-DM5 | 使用 Skill 完成字段映射：play_parse→enableJs（true→enableJs=true） | P1 |
| R-DM6 | 使用 Skill 固定字段：type=2（视频类型），articleStyle=2（视频列表样式） | P0 |

#### 选择器语法转换需求（使用 Skill 完成）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-S1 | 使用 Skill 完成 drpy CSS 选择器 → legado CSS 选择器转换（大部分兼容，部分需调整） | P0 |
| R-S2 | 使用 Skill 完成 drpy XPath → legado XPath 转换（基本兼容） | P1 |
| R-S3 | 使用 Skill 完成 drpy 正则 → legado 正则转换（基本兼容，需注意捕获组差异） | P1 |
| R-S4 | 使用 Skill 完成 drpy JSONPath → legado JSONPath 转换（基本兼容） | P1 |
| R-S5 | 选择器转换失败的条目标注降级说明，不中断整体转化 | P0 |

#### Skill 4 阶段闭环工作流需求

| ID | 需求 | 优先级 |
|----|------|--------|
| R-SK1 | 使用 Skill Phase 1 完成数据源分析与 drpy JS 脚本结构分析 | P0 |
| R-SK2 | 使用 Skill Phase 2 完成 RssSource JSON 生成 + sanitize 处理 + MandatoryFieldValidator 校验 | P0 |
| R-SK3 | 使用 Skill Phase 3 完成真机验证（列表加载、搜索、播放地址解析） | P0 |
| R-SK4 | 使用 Skill Phase 4 完成自动修复（对 Phase 3 验证失败的源修复规则并重新验证） | P1 |
| R-SK5 | 单个 Site 转化失败不中断整体流程，记录错误继续（用源[N]代号） | P0 |
| R-SK6 | 转化阶段同批内 sourceUrl 冲突时追加 Site.key 后缀；导入阶段与已有源冲突时跳过并记录日志 | P0 |

#### 特殊类型处理需求

| ID | 需求 | 优先级 |
|----|------|--------|
| R-ST1 | csp_XXX 类型（39 个）一律跳过，记录到跳过列表（用源[N]代号），标注"依赖 spider.jar 无法转化" | P0 |
| R-ST2 | type=1 Site（1 个，API 类型，ext=null）单独使用 Skill 转化（通用 JSON 模板 + JSONPath） | P1 |
| R-ST3 | type=8 Site（1 个，api=null, ext=null）单独分析后决定转化策略 | P2 |

#### TVBox 源仓库 CMS 采集源转化需求（实施阶段新增）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-CMS1 | 从 TVBox 源仓库获取 sites 数组（多个仓库合并去重） | P0 |
| R-CMS2 | 筛选 type=1 且 api 为 CMS 格式路径（如 `/api.php/provide/vod/`）的源 | P0 |
| R-CMS3 | 套用 CMS 采集源转化模板生成 RssSource JSON（详见 design.md §13） | P0 |
| R-CMS4 | 处理 baseUrl 陷阱：ruleContent JS 中用 `rssArticle.origin.split("?")[0]` 代替 `baseUrl`（详见 design.md §13.2） | P0 |
| R-CMS5 | 处理多线路格式：vod_play_url 用 `$$$` 分隔多线路，先 `split('$$$')` 取第一线路，再 `split('#')` 分隔集数（详见 design.md §13.3） | P0 |
| R-CMS6 | 处理 API 间歇性：部分分类返回空列表（bodyLen=81），需尝试多个分类找到有数据的分类（详见 design.md §13.4） | P1 |
| R-CMS7 | 对 API 不可达的源降级跳过，记录到跳过列表（用源[N]代号） | P0 |
| R-CMS8 | 归档最终可用源到 `temp/rss/rss_sources_final.json` | P0 |
| R-CMS9 | 处理 isUrl=true 陷阱：`RssParserByRule.kt:175` 中 `isUrl=true` 会把 vod_id 转换为完整 URL，导致 ruleContent JS 构造的详情页 API URL 错误；修复方案为 ruleContent JS 开头添加 ID 提取逻辑（从含 `/` 或 `?` 的 link 中提取纯数字 vod_id），详见 design.md §13.10 | P0 |

#### 登录处理需求（基于用户第四次确认反馈新增）

| ID | 需求 | 优先级 |
|----|------|--------|
| R-LG1 | Python 脚本在 Phase 1 分析阶段识别 drpy rule 对象中是否存在登录相关字段（headers 中的 Cookie/Authorization、login_url、login_method、login_headers、ext 凭据） | P0 |
| R-LG2 | 涉及登录的源，在生成的 RssSource 中通过 `<js>` 标签实现自动登录：检测 cookie 过期 → 发送登录请求 → 提取 cookie/token → 注入 header | P0 |
| R-LG3 | 登录凭据来源：优先从 drpy rule 的 login_url/login_headers 提取，其次从 ext 配置提取；**禁止让用户手动登录** | P0 |
| R-LG4 | 登录降级处理：无凭据/登录失败时标注降级说明到 sourceComment，不中断整体流程 | P1 |
| R-LG5 | 登录安全要求：凭据完全隐藏为 `***`，cookie 只记录长度和是否成功，登录端点用代号（站点A登录端点） | P0 |

#### 降级与冲突需求

| ID | 需求 | 优先级 |
|----|------|--------|
| R-DG1 | 降级标注写入 sourceComment，格式：`// 降级说明: xxx | 已知上限: xxx | 升级路径: xxx` | P1 |
| R-DG2 | csp_XXX 跳过的源记录到跳过列表，标注"依赖 spider.jar 无法转化" | P0 |
| R-DG3 | 加密 JS 无法解密的源记录到降级跳过列表，标注"加密 JS 无法解密" | P1 |
| R-DG4 | 选择器转换失败的条目标注降级说明，保留原始选择器供用户手动修正 | P1 |

#### RssSource 字段完整覆盖需求

> **修订说明（基于用户第四次确认反馈）**：必填字段从原 6 个扩充至 12 个，全部提升为 MANDATORY。ruleContent 作为正文规则（视频播放地址解析）仍保留为 MANDATORY，固定字段 type=2 / articleStyle=2 保留。

**字段级别定义**：

| 级别 | 含义 | 字段列表 |
|------|------|---------|
| **MANDATORY（12个必填）** | 转化后源必须存在，缺失则 MandatoryFieldValidator 校验失败 | sourceName / sourceUrl / sourceIcon / sourceComment / searchUrl / sortUrl / ruleArticles / ruleNextArticles / ruleTitle / rulePubDate / ruleImage / ruleLink |
| **MANDATORY（正文）** | 正文规则字段，视频播放地址解析必需 | ruleContent |
| **FIXED（固定值）** | 固定字段，不可省略 | type=2（视频类型）/ articleStyle=2（视频列表样式） |
| **OPTIONAL（可选）** | 建议覆盖，缺失不影响校验通过 | header / enableJs / loadWithBaseUrl / singleUrl / customOrder |

| ID | 需求 | 优先级 |
|----|------|--------|
| R-RC1 | 转化后源必须覆盖基础必填字段（MANDATORY，6个）：sourceName / sourceUrl / sourceIcon / sourceComment / searchUrl / sortUrl | P0 |
| R-RC2 | 转化后源必须覆盖规则必填字段（MANDATORY，6个）：ruleArticles / ruleNextArticles / ruleTitle / rulePubDate / ruleImage / ruleLink | P0 |
| R-RC3 | 转化后源必须覆盖正文规则字段（MANDATORY）：ruleContent；以及固定字段 type=2 / articleStyle=2 | P0 |
| R-RC4 | 转化后源建议覆盖可选字段（OPTIONAL）：header / enableJs / loadWithBaseUrl / singleUrl / customOrder | P1 |

### 非功能需求

| ID | 需求 | 说明 |
|----|------|------|
| N1 | 输出安全 | 所有转化日志、降级标注、报告均不输出源名称/域名/URL 业务数据，用代号（源[N] / 站点A / 站点B）替代；路径模式化（`/path/{id}`）；敏感字段（token/cookie/password/key/secret/auth）完全隐藏为 `***` |
| N2 | 不修改源码 | 整个转化流程不修改任何 legado 源码，不新增 Kotlin 文件，不引入新依赖 |
| N3 | 不升级锁定版本 | 不升级 jsoup（1.16.2）/ rhino（1.8.1）/ hutool（5.8.22）锁定版本 |
| N4 | 不引入运行时框架 | 不在 legado 运行时引入 drpy2.min.js 框架，仅静态分析 rule 对象 |
| N5 | 健壮性 | 单个源解析失败不中断整体流程；加密 JS 解码失败降级跳过；选择器转换失败保留原始选择器 |
| N6 | 性能 | 435 个 Site 批量转化在合理时间内完成，内存占用可控 |

---

## Scenarios

### 场景 1：批量导入 dzhipy 配置

用户持有 dzhipy 的 index.json（含 435 个 Site），希望批量转化为 legado 订阅源。使用 Skill Phase 1 读取 index.json，按 type 分类：type=3（433 个）→ 细分 drpy（394 个）/ csp_XXX（39 个）；type=1（1 个）；type=8（1 个）。对 394 个 drpy Site 批量获取 ext JS 脚本，识别编码方式。csp_XXX（39 个）直接标记跳过。最终输出约 394 个 RssSource JSON + 跳过列表（39 个 csp_XXX + 加密 JS 无法解密的源）+ 转化报告（用源[N]代号）。用户将输出 JSON 导入 legado 订阅源管理。

### 场景 2：drpy 转化（base64+gzip 解码 → rule 提取 → 字段映射）

用户有一个 type=3 声明式 drpy 的 Site，api=drpy2.min.js，ext 为 base64+gzip 编码的 JS 文件路径。Skill 获取 ext 指向的 JS 文件内容，base64 解码后识别 `H4sI` 开头（gzip 魔数），执行 gzip 解压得到明文 JS。从明文 JS 中提取 drpy rule 对象（含 title/host/searchUrl/推荐/一级/二级/class_name/class_url/headers/play_parse/lazy 等 25 字段），剥离 drpy2.min.js 框架依赖。按字段映射表将 rule 对象映射到 RssSource，选择器语法转换器将 drpy 选择器转换为 legado 选择器。使用 Skill Phase 2 生成 RssSource JSON，执行 sanitize + MandatoryFieldValidator 校验。转化后源可在 legado 中加载列表、搜索并解析播放地址。

### 场景 3：加密 JS 处理（AES-128-CBC-PKCS7 加密，使用实际密钥解密或降级跳过）

用户有一个 type=3 声明式 drpy 的 Site，ext 为 AES 加密的 base64。Skill base64 解码后识别为两种类型：类型A 以 `h36A5I5KdeB29zb3` 前缀开头（剥离前缀后为 base64 密文）；类型B 为纯 base64 无前缀。Skill 使用从 drpy2.js 框架源码提取的两组密钥（Hex 格式 16 字节 + Utf8 格式 16 字节）尝试 AES-128-CBC-PKCS7 解密：先尝试 Hex 密钥组，失败再尝试 Utf8 密钥组。若解密成功（得到含 `var rule = {...}` 结构的合法 JS），按场景 2 流程继续转化；若解密失败（base64 解码后长度非 16 倍数或 padding 错误），记录到降级跳过列表（用源[N]代号），在 sourceComment 写入 `// 降级说明: AES 加密 JS 解密失败（长度非16倍数/padding错误） | 已知上限: 已跳过 | 升级路径: 手动解密后重试转化`。整体解密成功率约 30.8%（4/13）。

### 场景 4：csp_XXX 跳过（spider.jar 重度混淆，ext 非爬虫规则）

用户有一个 type=3 csp_XXX 的 Site，api=csp_AppYsV4，依赖 spider.jar。Skill 识别为 csp_XXX 子类型，直接跳过转化并记录到跳过列表（用源[N]代号），在 sourceComment 写入 `// 降级说明: csp_XXX 依赖 spider.jar 无法转化（65% 重度混淆，ext 配置非爬虫规则） | 已知上限: 已跳过 | 升级路径: 寻找等效的声明式 drpy 源或采集 API 源`。用户在转化报告中看到该源在跳过列表中。

### 场景 5：type=1 单独处理（API 类型）

用户有一个 type=1 的 Site（API 类型，ext=null），api 为采集站接口地址。Skill 单独处理该 Site，套用通用 JSON 接口模板（列表 JSONPath `$.list`、标题 `vod_name`、链接 `vod_id`、搜索 `?wd={{key}}`、正文 `vod_play_url`），生成对应规则，在 sourceComment 标注 `// 降级说明: type=1 API 类型使用通用模板 | 已知上限: 字段路径可能不匹配 | 升级路径: 手动校验字段映射`。用户导入后需校验字段是否匹配实际接口。

### 场景 6：type=8 单独处理（待确认含义）

用户有一个 type=8 的 Site（api=null, ext=null），含义待确认。Skill 单独分析该 Site 后决定转化策略。若无法确认含义或无法转化，记录到跳过列表（用源[N]代号），在 sourceComment 标注 `// 降级说明: type=8 含义待确认，无法转化 | 已知上限: 已跳过 | 升级路径: 确认 type=8 含义后重试`。

### 场景 7：冲突与错误处理

用户批量导入时，第 17 个 Site 的 sourceUrl 与已转化源重复，第 23 个 Site 的 base64 解码失败，第 45 个 Site 的选择器转换失败。Skill 对第 17 个追加 Site.key 后缀保证 sourceUrl 唯一性并记录日志（用源[17]代号），对第 23 个捕获异常记录错误继续，对第 45 个选择器转换失败的条目标注降级说明并保留原始选择器。最终输出有效源 + 跳过列表 + 失败列表 + 转化成功率统计。整体流程不中断。

### 场景 8：Skill Phase 3 真机验证 + Phase 4 自动修复

用户将 Skill Phase 2 生成的 RssSource JSON 导入真机/模拟器，使用 Skill Phase 3 验证每个源的列表加载、搜索、播放地址解析。第 12 个源列表加载失败，第 28 个源搜索功能失败。Skill Phase 4 对失败的源自动修复规则（如调整选择器、修正 URL 拼接），修复后重新执行 Phase 3 验证。第 12 个源修复成功，第 28 个源修复后仍失败，标注降级说明保留原始规则供用户手动修正。所有验证结果用源[N]代号记录，不输出源名称/域名/URL。

### 场景 9：选择器语法转换

用户有一个 drpy 源，其 rule 对象的 `一级` 字段使用 CSS 选择器 `.list-item>a.title`，`二级` 字段使用 XPath `//video/@src`。Skill 的选择器语法转换器将 CSS 选择器直接保留（legado CSS 兼容），将 XPath 选择器也保留（legado XPath 兼容），生成 ruleArticles=`.list-item>a.title`、ruleContent=`//video/@src`。部分不兼容的选择器（如 drpy 特有的 `@json:$.data.list` 语法）标注降级说明并保留原始选择器供用户手动修正。

### 场景 10：TVBox 源仓库 CMS 采集源转化（实施阶段验证通过的最佳路径）

用户从 TVBox 源仓库获取 sites 数组（234+49 个 sites），筛选 type=1 且 api 为 CMS 格式路径（如 `/api.php/provide/vod/`）的源。Skill 套用 CMS 采集源转化模板生成 RssSource JSON：sortUrl 按分类列表拼接、ruleArticles 用 JSONPath `$.list` 提取列表、ruleContent 用 JS 解析 vod_play_url 多线路格式（`$$$` 分隔线路、`#` 分隔集数）。

**batch3**：6 个源 API 可达，全部完整通过真机验证（分类加载 + 列表数据 + 详情页播放 + 搜索功能）。转化过程中需处理 baseUrl 陷阱（用 `rssArticle.origin.split("?")[0]` 代替 `baseUrl`）和 API 间歇性（部分分类返回空列表，需尝试多个分类）。

**batch4**：28 个 CMS 采集源中 9 个直接通过，10 个出现 NoVPStarted（播放器未启动）。根因分析发现 `RssParserByRule.kt:175` 中 `isUrl=true` 会把 vod_id 转换为完整 URL，导致 ruleContent JS 构造的详情页 API URL 错误。修复方案为 ruleContent JS 开头添加 ID 提取逻辑（从含 `/` 或 `?` 的 link 中提取纯数字 vod_id），修复后 9/10 通过（90%），1 个 WARN（搜索接口异常，非 ruleContent 问题）。同时修复 6 个源 sortUrl 第一个分类返回空列表（bodyLen=81）的问题。

**batch5**：从 6 个 TVBox 源仓库获取 840 个 sites，筛选 29 个 CMS 源，15 个 API 可达，8 个通过验证，3 个去重后新增 5 个可用源。

**batch6**：22 个 CMS 源，首次验证仅 3 个通过（固定坐标点击不精确），改用 uiautomator dump + XML 解析精准定位列表项元素坐标后，二次验证 5 个通过，1 个去重后新增 7 个可用源。同时发现 LoadMoreView（FooterView）会被误认为列表项，需检查子节点 resource-id 排除。

**batch7**：网络搜索 CMS 采集站 4 个，4/4 全部通过，新增 4 个可用源。

最终 40 个可用源（博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源）归档到 `temp/rss/rss_sources_final.json`。
