# TVBox/影视仓播放源转化 legado 订阅源

> 使用 Legado Source Creator Skill 将 dzhipy 播放源（Site JSON 格式）转化为 legado（阅读M）的订阅源（RssSource JSON 格式），**不修改 legado 源码**。

**状态**：✅ 已实施（七批次转化完成，最终可用订阅源 40 个，归档于 `temp/rss/rss_sources_final.json`）

---

## 实施结果摘要

| 批次 | 输入源类型 | 输入数量 | 完整通过 | 通过率 | 备注 |
|------|-----------|---------|---------|-------|------|
| batch1 | dzhipy drpy 源 | 10 | 1 | 10% | 仅博看听书通过，9 个失败（域名失效/网站改版/服务器关闭/drpy JS 不兼容/HTTP 不通） |
| batch2 | dzhipy 源深度验证 | 9（host 可达） | 0 | 0% | 9 个 host 可达源全部播放失败（SPA/网盘/劫持/反爬/CSP 无 JS/404/改用途） |
| batch3 | TVBox 源仓库 CMS 采集源 | 6（API 可达） | 6 | 100% | 6 个源全部完整通过（分类+列表+播放+搜索） |
| batch4 | TVBox 源仓库 CMS 采集源 | 28 | 17 | 61% | 9 个完整通过 + 8 个修复后通过（NoVPStarted 修复，isUrl=true 陷阱）；1 个 WARN（搜索接口异常） |
| batch5 | TVBox 源仓库 CMS 采集源 | 15（API 可达） | 5 | 33% | 8 个通过验证，3 个去重，新增 5 个（6 个仓库 840 个 sites 筛选 29 个 CMS 源） |
| batch6 | TVBox 源仓库 CMS 采集源 | 22 | 7 | 32% | 3 个首次通过 + 5 个二次验证通过（uiautomator 精准点击）；1 个去重，新增 7 个 |
| batch7 | 网络搜索 CMS 采集站 | 4 | 4 | 100% | 4/4 全部通过（网络搜索 CMS 采集站） |
| **合计** | - | - | **40** | - | 博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源 |

**归档文件**：`temp/rss/rss_sources_final.json`（40 个完整通过的 RssSource JSON）

---

## 功能概述

影视仓与 legado 是两个独立的规则引擎生态，源格式互不兼容。本方案使用 **Legado Source Creator Skill** 将 dzhipy 的 `Site` bean（站点播放源）转化为 legado 的 `RssSource`（订阅源 JSON），使原属影视仓生态的播放源能在 legado 中以订阅源形式加载、浏览与播放。

**核心原则**：**不允许动源码**。全部转化工作通过 Skill 的 4 阶段闭环工作流完成。

### 核心能力

- **Python 分析脚本**：批量获取、解码、提取 dzhipy Site 的 drpy JS 脚本
- **CMS 采集源转化模板**（实施阶段新增，最佳转化路径）：从 TVBox 源仓库筛选 type=1 + CMS 格式路径源，套用标准化转化模板
- **Skill 4 阶段闭环**：
  - Phase 1：分析（Playwright + JS 解码 / CMS 源筛选）
  - Phase 2：生成 + 校验（sanitize + MandatoryFieldValidator）
  - Phase 3：真机验证（编译 + 安装 + 导入 + L2 验证）
  - Phase 4：自动修复（基于验证结果迭代）

**实施后转化率**：
- drpy 源：10%（1/10，远低于设计预估 30-50%）
- **CMS 采集源：最佳转化目标（batch3 100% 6/6 + batch4 61% 17/28 + batch5 33% 5/15 + batch6 32% 7/22 + batch7 100% 4/4）**
- 最终可用订阅源：40 个（博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源）

---

## 数据源深度分析（真实数据）

### 数据源入口

- **入口配置文件**：`dzhipy/index.json`（用户提供）
- **入口 URL 数量**：1 个 dzhipy 源配置入口
- **Site 总量**：435 个

### Site 总量与类型分布

| Site.type | 含义 | 数量 | 占比 | 转化可行性 |
|-----------|------|------|------|-----------|
| 3 | 爬虫jar / CSP 接口 | 433 | 99.5% | drpy 子类型可转化，csp_XXX 不可转化 |
| 1 | JSON 解析 | 1 | 0.2% | 可转化（单独处理） |
| 8 | 其他 | 1 | 0.2% | 可转化（单独处理） |

### type=3 细分分析（主导类型，99.5%）

type=3 内部存在两种截然不同的子类型：

| 子类型 | 数量 | 占比 | 转化可行性 |
|--------|------|------|-----------|
| 声明式 drpy Site | 394 | 90.6%（占总量） | 可转化（base64/gzip 解码 + rule 对象提取 + 选择器转换） |
| csp_XXX 接口 | 39 | 9.0%（占总量） | 不可转化（依赖 spider.jar 字节码，ext 非爬虫规则） |

**drpy rule 对象关键字段**（共 25 个字段，从解码后 JS 中提取）：
`title` / `host` / `homeUrl` / `detailUrl` / `searchUrl` / `url` / `filterable` / `filter_url` / `filter` / `filter_def` / `headers` / `timeout` / `class_name` / `class_url` / `limit` / `multi` / `searchable` / `play_parse` / `lazy` / `推荐` / `一级` / `二级` / `搜索` 等

### drpy JS 脚本编码方式分析（5 个样本）

| 编码方式 | 占比 | 特征 | 处理策略 |
|---------|------|------|---------|
| base64 + gzip 编码 | 2/5 | `H4sI` 开头 | gzip 解压 + base64 解码 |
| base64 纯编码 | 1/5 | 标准 base64 字符集 | 直接 base64 解码 |
| AES-128-CBC 加密 | 13/392(3.3%) | ***（16字节特征前缀）或纯base64 | AES-128-CBC-PKCS7 解密（密钥从 drpy2.js 框架提取，4/13 成功解密） |
| 明文 | 0/5 | - | - |

**用户反馈**：legado 内置 JS 加解密工具，可通过 JS 标签调用。AES 加密脚本的解密已在 Skill Phase 1 中实际尝试：AES-128-CBC-PKCS7 算法，密钥从 drpy2.js 框架源码提取（Hex 格式 + Utf8 格式两组，16字节），4/13 加密样本成功解密为合法 JS 规则代码。

### csp_XXX 不可转化原因（深度分析）

| 维度 | 说明 |
|------|------|
| spider.jar 规模 | 共 196 个 Spider 类 |
| 混淆程度 | 65%（86/132 主类）为重度混淆 |
| 配置加载方式 | 通过 `init()` 运行时传入，不嵌入 DEX |
| ext 配置性质 | 仅网盘配置（token/oauth）和 UI 筛选器，**非爬虫规则** |
| 静态分析可行性 | 无法通过静态分析还原爬虫逻辑 |

---

## 核心能力

| 能力 | 说明 |
|------|------|
| Skill 4 阶段闭环 | Phase1 分析（Playwright + JS 解码） → Phase2 生成 + 校验（sanitize + MandatoryFieldValidator） → Phase3 真机验证 → Phase4 自动修复 |
| drpy JS 解码 | base64 + gzip 解码 / 纯 base64 解码 / AES-128-CBC-PKCS7 解密（密钥从 drpy2.js 框架提取，30.8% 成功率） |
| rule 对象提取 | 从解码后 JS 中提取 25 个 rule 字段，映射为 legado RssSource 字段 |
| 字段映射 | drpy rule（title/host/searchUrl/一级/二级/class_name/class_url/headers/lazy） → RssSource（sourceName/sourceUrl/searchUrl/ruleArticles/ruleContent/sortUrl/header） |
| 选择器转换 | drpy 选择器（`@css:`/`@xpath:`/`@json:`/`@regex:`） → legado 选择器（去前缀） |
| 批量处理 | Python 脚本批量获取 394 个 drpy Site 的 JS 脚本，解码 + 提取 + 映射 + 生成 JSON |
| 真机验证 | Skill Phase 3：编译 + 安装 + 导入 + L2 验证 |
| JS 自动登录 | 通过 `<js>` 标签实现自动登录获取 cookie，禁止用户手动登录；登录凭据从 drpy rule 提取；无凭据/失败时降级跳过 |

---

## 转化策略

### 总体策略（实施后修订，按优先级差异化处理）

| 优先级 | 子类型 | 数量 | 转化路径 | 实际成功率 | 备注 |
|--------|--------|------|---------|-----------|------|
| **P0（最高）** | TVBox 源仓库 CMS 采集源（type=1 + api 为 CMS 格式路径） | batch3 14(6可达) + batch4 28 + batch5 15 + batch6 22 + batch7 4 | 套用 CMS 采集源转化模板（详见 design.md §13），含 isUrl=true 陷阱修复（§13.10）+ uiautomator 精准点击验证（§13.11） | **batch3 100%(6/6) + batch4 61%(17/28) + batch5 33%(5/15) + batch6 32%(7/22) + batch7 100%(4/4)** | API 标准、格式统一、成功率高 |
| P1（备选） | drpy 类型 | 394 | 使用 Skill 批量转化（base64/gzip 解码 → rule 提取 → 字段映射 → 选择器转换） | 10%（1/10） | 失效源多，drpy JS 规则兼容性差 |
| P2（跳过） | csp_XXX 类型 | 39 | **跳过**（spider.jar 65% 重度混淆，ext 非爬虫规则） | 0% | 依赖 spider.jar 字节码 |

**实施后整体转化率**：40 个可用订阅源（博看听书 + 6 个 batch3 + 17 个 batch4 + 5 个 batch5 + 7 个 batch6 + 4 个 batch7 CMS 采集源）

### drpy 类型转化流程（Skill 4 阶段闭环）

1. **Phase 1 - 分析**：
   - Python 脚本批量获取 394 个 drpy Site 的 ext 字段（JS 脚本路径或内联 JS）
   - 识别编码方式（gzip+base64 / 纯 base64 / AES 加密）
   - 解码 JS 脚本（加密脚本尝试调用 legado 内置 JS 加解密工具）
   - 从解码后 JS 中提取 25 个 rule 字段

2. **Phase 2 - 生成 + 校验**：
   - 按"drpy rule → RssSource 字段映射表"映射字段
   - 选择器转换（去 `@css:`/`@xpath:`/`@json:`/`@regex:` 前缀）
   - sanitize 清洗（去除无效字段、规范 URL）
   - MandatoryFieldValidator 校验必填字段（sourceUrl / sourceName / ruleArticles / ruleContent 等）

3. **Phase 3 - 真机验证**：
   - 编译 legado APK + 安装到真机/模拟器
   - 导入生成的 RssSource JSON
   - L2 验证（列表加载 / 搜索 / 正文解析）

4. **Phase 4 - 自动修复**：
   - 基于真机验证失败结果，自动修复规则
   - 迭代 Phase 2-3 直至通过

### 登录处理策略

- **登录场景识别**：drpy rule 中的 login_url/login_headers/headers.Cookie
- **JS 自动登录流程**：检测cookie过期 → 发送登录请求 → 提取cookie → 注入header
- **降级策略**：无凭据/登录失败标注降级说明到 sourceComment
- **安全要求**：凭据完全隐藏为***

### csp_XXX 类型不可转化说明

- **spider.jar 规模**：196 个 Spider 类，65%（86/132 主类）重度混淆
- **配置加载方式**：通过 `init()` 运行时传入，不嵌入 DEX
- **ext 配置性质**：仅网盘配置（token/oauth）和 UI 筛选器，**不是爬虫规则**
- **结论**：静态分析无法还原爬虫逻辑，明确跳过并记录到跳过列表

### CMS 采集源转化流程（实施阶段新增，最佳转化路径）

1. **源筛选**：
   - 从 TVBox 源仓库获取 sites 数组（234 + 49 个 sites）
   - 筛选 type=1 且 api 为 CMS 格式路径（`/api.php/provide/vod/`）的源 14 个
   - 验证 API 可达性，14 个中 6 个可达

2. **套用转化模板**（详见 design.md §13）：
   - sortUrl：按分类列表拼接 `分类名::{{api}}?ac=list&t={{分类ID}}`
   - ruleArticles：JSONPath `$.list`
   - ruleContent：JS 解析 vod_play_url 多线路格式
   - searchUrl：`{{api}}?wd={{searchKey}}`

3. **关键技术处理**：
   - **baseUrl 陷阱**：ruleContent JS 中用 `rssArticle.origin.split("?")[0]` 代替 `baseUrl`
   - **多线路格式**：vod_play_url 用 `$$$` 分隔线路，`#` 分隔集数，`$` 分隔名称与 URL
   - **API 间歇性**：部分分类返回空列表（bodyLen=81），需尝试多个分类
   - **isUrl=true 陷阱（batch4 新增）**：`RssParserByRule.kt:175` 中 `isUrl=true` 把 vod_id 转换为完整 URL，ruleContent JS 开头需添加 ID 提取逻辑（详见 design.md §13.10）

4. **真机验证**：
   - batch3：6 个源全部完整通过（100%）
   - batch4：28 个源中 17 个完整通过（9 直接通过 + 8 修复后通过），1 个 WARN（搜索接口异常）

### 关键技术发现（实施阶段总结）

| # | 发现 | 说明 |
|---|------|------|
| 1 | baseUrl 陷阱 | rssArticle.link=vod_id（纯数字），baseUrl 拼接错误，需用 rssArticle.origin.split("?")[0] 代替 |
| 2 | 多线路格式 | vod_play_url 用 `$$$` 分隔线路，`#` 分隔集数，`$` 分隔名称与 URL |
| 3 | API 间歇性 | 部分分类返回空列表（bodyLen=81），需尝试多个分类 |
| 4 | TVBox 源仓库无 type=0 源 | type=1 + CMS 格式路径源可替代 type=0 源 |
| 5 | drpy 源大部分失效 | dzhipy 435 个源中仅 9 个 host 可达，且播放全部失败 |
| 6 | CMS 采集源是最佳转化目标 | API 标准、格式统一、成功率高 |
| 7 | isUrl=true 陷阱（batch4 新增） | `RssParserByRule.kt:175` 中 `isUrl=true` 把 vod_id 转换为完整 URL，导致 ruleContent JS 构造的详情页 API URL 错误；修复方案为 JS 开头添加 ID 提取逻辑（详见 design.md §13.10） |
| 8 | dzhipy 433/435 是 drpy 不可转化（batch5-7 新增） | dzhipy 435 个源中 433 个是 type=3（drpy 源），实际成功率仅 10%；CMS 采集源应从 TVBox 源仓库和网络搜索获取（详见 design.md §13.11.5） |
| 9 | uiautomator 精准点击（batch5-7 新增） | 固定坐标点击不精确导致验证失败，改用 uiautomator dump + XML 解析精准定位 UI 元素（详见 design.md §13.11.6） |
| 10 | articleStyle=2 网格布局列表项定位（batch5-7 新增） | 网格布局列表项位置动态变化，需通过 uiautomator dump 精确获取，不能简单用固定坐标（详见 design.md §13.11.7） |
| 11 | LoadMoreView 误识别（batch5-7 新增） | RecyclerView 中的 LoadMoreView（FooterView）会被误认为列表项，需检查子节点 resource-id 排除（详见 design.md §13.11.8） |

---

## drpy rule 对象 → legado RssSource 字段映射表

| drpy rule 字段 | legado RssSource 字段 | 说明 |
|----------------|----------------------|------|
| title | sourceName | 源名称 |
| host | sourceUrl | 源地址（PK） |
| searchUrl | searchUrl | 搜索 URL |
| 推荐 / 一级 | ruleArticles | 列表规则（视频条目） |
| 二级 | ruleContent | 正文规则（视频播放地址，含 lazy 懒加载） |
| 搜索 | searchUrl（搜索规则部分） | 搜索规则 |
| class_name / class_url | sortUrl | 分类 URL（按 `分类名::url` 格式拼接） |
| headers | header | 请求头（Map → JSON 字符串） |
| play_parse | enableJs | 启用 JS（true → enableJs=true） |
| lazy | ruleContent 的 lazy 配置 | 懒加载解析（嵌入 ruleContent） |
| -（固定） | type | 固定为 2（视频类型） |
| -（固定） | articleStyle | 固定为 2（视频列表样式） |

---

## legado RssSource 关键字段覆盖清单

Skill 生成的 RssSource JSON 必须完整覆盖以下字段：

| 字段 | 必填 | 来源 | 说明 |
|------|------|------|------|
| sourceUrl | 是 | drpy.host | PK，源地址 |
| sourceName | 是 | drpy.title | 源名称 |
| sourceIcon | 是 | Site.icon | 源图标 |
| header | 否 | drpy.headers | 请求头（JSON 字符串） |
| sortUrl | 是 | drpy.class_name + class_url | 分类 URL |
| singleUrl | 否 | csp_XXX 降级时设 true（本方案跳过 csp_XXX，一般不设） | 单 URL 模式 |
| articleStyle | 是 | 固定 2 | 视频列表样式 |
| ruleArticles | 是 | drpy.推荐 + 一级 | 列表规则 |
| ruleTitle | 是 | drpy.一级 标题部分 | 标题规则 |
| ruleLink | 是 | drpy.一级 链接部分 | 链接规则 |
| ruleContent | 是 | drpy.二级 | 正文规则（含 lazy） |
| ruleImage | 是 | drpy.一级 图片部分 | 图片规则 |
| ruleNextPage | 是 | drpy.一级 翻页部分 | 下一页规则 |
| enableJs | 否 | drpy.play_parse=true 时设 true | 启用 JS |
| loadWithBaseUrl | 否 | 嗅探降级时设 true | 加载 baseUrl |
| type | 是 | 固定 2 | 视频类型 |
| searchUrl | 是 | drpy.searchUrl | 搜索 URL |
| customOrder | 否 | Site.key（用于排序） | 自定义排序 |
| sourceComment | 是 | 降级标注/登录说明 | 降级说明 |
| ruleNextArticles | 是 | drpy.一级 翻页部分 | 下一页规则（对应 ruleNextPage） |
| rulePubDate | 是 | drpy.一级 日期部分 | 发布日期规则 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（方向 / 数据源 / Scope / Requirements / Scenarios） |
| [design.md](./design.md) | 技术设计（Skill 工作流 / drpy 解码 / 字段映射 / ADR） |
| [tasks.md](./tasks.md) | 实施任务清单（10 章节，Skill 4 阶段闭环任务） |

---

## 参考源码

| 来源 | 文件 | 用途 |
|------|------|------|
| Legado Source Creator Skill v4 | `.trae/skills/legado-source-creator/SKILL.md` | 4 阶段闭环工作流主规范（分析 / 生成 + 校验 / 真机验证 / 自动修复） |
| legado | `RssSource.kt` | 输出源实体类（字段定义参考） |
| legado | `RssSourceExtensions.kt` | sortUrl 解析逻辑参考 |
| legado | `WebBook.kt` | 网络请求层架构参考 |
| legado | `BookSource.kt` | 字段结构参考 |
| ai_tests | `ai_tests/scripts/` | 真机验证脚本（quick_build_install.py / import_rss_source.py / l2_verify_video_player.py 等） |

---

## 使用说明

### 导入最终可用订阅源

将归档文件 `temp/rss/rss_sources_final.json` 导入 legado 订阅源管理：

```bash
# 使用 ai_tests 脚本导入
python ai_tests/scripts/import_rss_source.py temp/rss/rss_sources_final.json
```

### 验证导入结果

导入后可使用 L2 验证脚本验证视频播放器功能：

```bash
# L2 验证视频播放器
python ai_tests/scripts/l2_verify_video_player.py
```

### 归档文件内容

`temp/rss/rss_sources_final.json` 包含 40 个完整通过的 RssSource JSON：

| 源代号 | 来源 | 验证状态 | 备注 |
|--------|------|---------|------|
| 博看听书 | batch1 drpy 源 | ✅ 完整通过 | 24 列表项 |
| 源[1]-源[6] | batch3 CMS 采集源 | ✅ 完整通过 | 6 个源（分类+列表+播放+搜索全通过） |
| 源[7]-源[15] | batch4 CMS 采集源 | ✅ 完整通过 | 9 个源直接通过（分类+列表+播放+搜索全通过） |
| 源[16]-源[23] | batch4 CMS 采集源 | ✅ 修复后通过 | 8 个源经 isUrl=true 陷阱修复后通过（详见 design.md §13.10） |
| 源[24]-源[28] | batch5 CMS 采集源 | ✅ 完整通过 | 5 个源（8 个通过验证，3 个去重；6 个仓库 840 个 sites 筛选） |
| 源[29]-源[35] | batch6 CMS 采集源 | ✅ 完整通过 | 7 个源（3 个首次通过 + 5 个 uiautomator 精准点击二次验证通过，1 个去重） |
| 源[36]-源[39] | batch7 CMS 采集源 | ✅ 完整通过 | 4 个源（网络搜索 CMS 采集站，4/4 全部通过） |

### 后续扩展

如需扩展可用源数量，建议：
1. **优先扩展 CMS 采集源**：从更多 TVBox 源仓库筛选 type=1 + CMS 格式路径源，套用转化模板
2. **定期验证源可用性**：CMS 采集源可能因 API 变更失效，需定期真机验证
3. **drpy 源作为备选**：drpy 源成功率低（10%），仅在 CMS 采集源不足时尝试

---

## 输出安全声明

本文档及配套 spec/design/tasks 文档仅包含技术分析（字段名、类型、方法签名、架构设计、数量统计），不包含任何源名称、域名、URL、cookie 等业务数据。示例中出现的站点统一以代号（站点A/B/C、源[N]）或路径模式（`/path/{id}`）表示。真实数据分析中的入口配置文件名 `dzhipy/index.json` 仅作技术引用，不含业务数据。
