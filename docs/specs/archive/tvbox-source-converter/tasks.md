# tasks.md — TVBox/影视仓播放源转化 legado 订阅源

> 状态：✅ 已实施（七批次转化完成，最终可用订阅源 40 个，归档于 `temp/rss/rss_sources_final.json`）
> 方向：使用 Legado Source Creator Skill 批量转化，**不允许动源码**
> 格式：`- [ ] X.Y` 任务清单

---

## 0. 实施记录汇总（七批次转化）

### batch1：dzhipy drpy 源转化（10 个源）

- [x] 0.1 获取 dzhipy drpy 源 10 个，执行 Skill 4 阶段闭环转化
- [x] 0.2 真机验证结果：1 个完整通过（博看听书：分类显示 + 列表数据 24 项 + 详情页播放 + 搜索功能 4 项结果）
- [x] 0.3 9 个失败源降级处理（域名失效 3 / 网站改版 1 / 服务器关闭 1 / drpy JS 规则不兼容 1 / HTTP 不通 3）

### batch2：dzhipy 源深度验证（435 个源）

- [x] 0.4 深度验证 435 个 dzhipy 源的可达性（51 个 gitlab 仓库可达，22 个 HTTP 200，9 个 host 可达）
- [x] 0.5 9 个 host 可达源全部播放失败原因分析（SPA 站点 / 网盘资源站 / 域名劫持 / 反爬拦截 / CSP 源无 JS / 路径 404 / 域名改用途）

### batch3：TVBox 源仓库 CMS 采集源转化（最佳转化路径）

- [x] 0.6 从 3 个 TVBox 源仓库获取 sites 数组（234 + 49 个 sites）
- [x] 0.7 筛选 type=1 且 api 为 CMS 格式路径的源 14 个
- [x] 0.8 验证 API 可达性：6 个源 API 可达
- [x] 0.9 6 个源全部完整通过真机验证（分类加载 + 列表数据 + 详情页播放 + 搜索功能）
  - 源[1]：8 分类 / 15 列表项 / 播放成功（直接通过）
  - 源[2]：5 分类 / 12 列表项 / 播放成功（直接通过）
  - 源[3]：23 分类 / 2 列表项 / 播放成功（修复后通过）
  - 源[4]：24 分类 / 3 列表项 / 播放成功（修复后通过）
  - 源[5]：23 分类 / 1 列表项 / 播放成功（修复后通过，Tab1 有数据）
  - 源[6]：22 分类 / 4 列表项 / 播放成功（修复后通过，Tab4 有数据）

### batch4：CMS 采集源批量扩展与 NoVPStarted 修复

- [x] 0.12 从 TVBox 源仓库获取 28 个 CMS 采集源，执行 Skill 4 阶段闭环转化
- [x] 0.13 真机验证结果：9 个完整通过，10 个 NoVPStarted（播放器未启动），9 个其他状态
- [x] 0.14 根因分析：`RssParserByRule.kt:175` 中 `isUrl=true` 把 vod_id 转换为完整 URL，导致 ruleContent JS 构造的详情页 API URL 错误
- [x] 0.15 修复方案：ruleContent JS 开头添加 ID 提取逻辑（从可能被转换为完整 URL 的 rssArticle.link 中提取纯数字 vod_id）
- [x] 0.16 sortUrl 修复：6 个源的第一个分类返回空列表（bodyLen=81），删除空分类后验证通过
- [x] 0.17 修复后验证结果：8 个有 sortUrl 的源全部 PASS（100%），1 个搜索型源 PASS（源[13]），1 个搜索型源 WARN（源[22]搜索接口异常），总通过率 9/10（90%）
- [x] 0.18 总可用源从 16 个增加到 24 个（batch4 新增 8 个修复通过的源）

### 归档任务

- [x] 0.10 归档最终可用订阅源到 `temp/rss/rss_sources_final.json`（40 个：博看听书 + 6 个 batch3 CMS 采集源 + 17 个 batch4 CMS 采集源 + 5 个 batch5 CMS 采集源 + 7 个 batch6 CMS 采集源 + 4 个 batch7 CMS 采集源）
- [x] 0.11 记录关键技术发现（baseUrl 陷阱 / 多线路格式 / API 间歇性 / TVBox 源筛选策略 / drpy 源失效原因 / CMS 采集源最佳转化目标 / isUrl=true 陷阱与修复 / dzhipy 433/435 drpy 不可转化 / uiautomator 精准点击 / articleStyle=2 网格布局 / LoadMoreView 误识别，详见 §13.18-13.21）

---

## 1. 准备工作

- [x] 1.1 确认需求范围（使用 Skill 将影视仓播放源转化为 legado 视频订阅源，不动源码）
- [x] 1.2 确认 dzhipy index.json 数据结构（435 个 Site: drpy394 + csp_XXX39 + type=1/8 各 1）
- [x] 1.3 确认 Legado Source Creator Skill v4 工作流（4 阶段闭环）
- [x] 1.4 确认 RssSource 必填字段清单（12个必填字段：sourceName/sourceUrl/sourceIcon/sourceComment/searchUrl/sortUrl/ruleArticles/ruleNextArticles/ruleTitle/rulePubDate/ruleImage/ruleLink + 固定字段 type=2/articleStyle=2）

## 2. 数据源分析（已完成）

- [x] 2.1 获取 dzhipy index.json 并分类统计（435 个 Site）
- [x] 2.2 type 分布统计（type=3:433, type=1:1, type=8:1）
- [x] 2.3 api 分类统计（drpy:394, csp_XXX:39, http_url:1, None:1）
- [x] 2.4 ext 字段类型分布统计
- [x] 2.5 spider.jar 深度反编译分析（196 个 Spider 类，65% 重度混淆）
- [x] 2.6 csp_XXX ext 配置文件分析（5 个 JSON 配置，非爬虫规则）
- [x] 2.7 drpy JS 脚本编码方式分析（base64+gzip / 纯 base64 / AES 加密）
- [x] 2.8 drpy rule 对象字段分析（25 个不同字段）
- [x] 2.9 drpy2.min.js 框架分析（88 函数，8 依赖库，47 个 rule 字段）

## 3. drpy 类型批量转化（核心任务，batch1 已完成）

- [x] 3.1 编写 Python 脚本批量获取 394 个 drpy Site 的 ext JS 脚本
- [x] 3.2 实现 JS 脚本解码（base64+gzip: b64decode+gzip.decompress / 纯 base64: b64decode / AES 加密: 使用从 drpy2.js 框架提取的实际密钥（AES-128-CBC-PKCS7））
- [x] 3.3 实现 rule 对象提取（从解码后的 JS 中提取 rule 对象字面量）
- [x] 3.4 实现 drpy rule → legado RssSource 字段映射
  * title→sourceName, host→sourceUrl, searchUrl→searchUrl
  * 推荐/一级→ruleArticles, 二级→ruleContent（含 lazy）
  * class_name/class_url→sortUrl, headers→header
  * play_parse→enableJs, 固定 type=2/articleStyle=2
- [x] 3.5 实现选择器语法转换（@css: / @xpath: / @json: / @regex: 前缀去除）
- [x] 3.6 处理加密 JS 脚本（AES-128-CBC-PKCS7 已确认可解密，密钥从 drpy2.js 框架提取，4/13 样本成功解密，9个失败文件降级跳过）
- [x] 3.7 生成 RssSource JSON 数组（sanitize_source_json 过滤 None 值）
- [x] 3.8 MandatoryFieldValidator 校验（strict_recommended=True）
- [x] 3.10 识别 drpy rule 中的登录配置（login_url/login_headers/headers中的Cookie）
- [x] 3.11 实现 JS 自动登录获取 cookie 方案（通过 `<js>` 标签自动登录，禁止用户手动登录）
- [x] 3.12 实现登录降级策略（无凭据/登录失败时标注降级说明到 sourceComment）

> **batch1 实施结果**：10 个 drpy 源中仅 1 个（博看听书）完整通过真机验证，9 个失败（域名失效 3 / 网站改版 1 / 服务器关闭 1 / drpy JS 规则不兼容 1 / HTTP 不通 3）。drpy 源实际成功率 10%，远低于设计预估 30-50%。

## 4. csp_XXX 类型处理（已完成）

- [x] 4.1 确认 csp_XXX 类型跳过策略（39 个 Site，spider.jar 65% 重度混淆，ext 非爬虫规则）
- [x] 4.2 生成跳过列表（记录 csp_ 类名 + 跳过原因，不含源名称/域名）

## 5. type=1/8 单独处理（已被 CMS 采集源转化方案替代）

- [x] 5.1 分析 type=1 Site（1 个，api=http_url, ext=null）
- [x] 5.2 分析 type=8 Site（1 个，api=null, ext=null）
- [x] 5.3 制定 type=1/8 转化方案（如可行）

> **实施结果**：type=1/8 单独处理方案已被 batch3 的 CMS 采集源转化方案替代。CMS 采集源（type=1 + api 为 CMS 格式路径）实际成功率 100%（6/6），远优于 type=1/8 单独处理方案。

## 6. Skill Phase 2: 生成 + 校验（已完成）

- [x] 6.1 对生成的 RssSource JSON 执行 sanitize_source_json（过滤 None 值）
- [x] 6.2 执行 validate_source 校验（source_type='rss', strict_recommended=True）
- [x] 6.3 修复 CRITICAL/MANDATORY/RECOMMENDED 缺失字段
- [x] 6.4 输出校验通过的 RssSource JSON 数组

## 7. Skill Phase 3: 真机验证（已完成）

- [x] 7.1 编译 + 安装 legado APK 到真机/模拟器
- [x] 7.2 导入生成的 RssSource JSON 到 legado（import_rss_source.py）
- [x] 7.3 L2 验证视频播放器（l2_verify_video_player.py）
- [x] 7.4 验证列表加载 / 搜索 / 播放功能
- [x] 7.5 日志分析（Grep 过滤技术关键词，只输出错误码/异常类型）

## 8. Skill Phase 4: 自动修复循环（已完成）

- [x] 8.1 对验证失败的源执行 auto_fixer_loop（max_attempts=3）
- [x] 8.2 记录修复轨迹（fix_history）
- [x] 8.3 输出最终成功/失败统计

> **Phase 4 修复结果**：batch3 中源[3]/源[4]/源[5]/源[6] 经自动修复后通过验证（baseUrl 陷阱修复 + 多线路格式处理 + API 间歇性分类切换）。

## 9. 输出安全与合规（已完成）

- [x] 9.1 确认所有输出不包含源名称/域名/URL（用源[N]代号）
- [x] 9.2 确认 sourceComment 降级标注不含业务数据
- [x] 9.3 确认日志只输出技术信息（错误码/异常类型/调用栈）
- [x] 9.4 确认登录凭据完全隐藏为***（用户名/密码/token/cookie 只记录长度和是否成功）

## 10. 文档与交付（进行中）

- [x] 10.1 更新 docs/specs/tvbox-source-converter/ 四文档状态（设计中 → 已实现）
- [ ] 10.2 记录经验到 basic-memory（关键决策/文件路径/任务状态）
- [ ] 10.3 完成任务前逐项核对强制检查清单

## 11. CMS 采集源转化（实施阶段新增，最佳转化路径）

- [x] 11.1 从 3 个 TVBox 源仓库获取 sites 数组（234 + 49 个 sites）
- [x] 11.2 筛选 type=1 且 api 为 CMS 格式路径（`/api.php/provide/vod/`）的源 14 个
- [x] 11.3 验证 API 可达性（14 个中 6 个可达）
- [x] 11.4 套用 CMS 采集源转化模板生成 RssSource JSON（详见 design.md §13）
- [x] 11.5 处理 baseUrl 陷阱（ruleContent JS 中用 `rssArticle.origin.split("?")[0]` 代替 `baseUrl`）
- [x] 11.6 处理多线路格式（vod_play_url 用 `$$$` 分隔线路，`#` 分隔集数，`$` 分隔名称与 URL）
- [x] 11.7 处理 API 间歇性（部分分类返回空列表 bodyLen=81，尝试多个分类找到有数据的分类）
- [x] 11.8 6 个源全部完整通过真机验证（分类加载 + 列表数据 + 详情页播放 + 搜索功能）
- [x] 11.9 归档最终可用源到 `temp/rss/rss_sources_final.json`（24 个：博看听书 + 6 个 batch3 CMS 采集源 + 17 个 batch4 CMS 采集源）

## 12. batch4 NoVPStarted 源修复（CMS 采集源批量修复）

- [x] 12.1 batch4 真机验证：28 个 CMS 采集源中 9 个完整通过，10 个 NoVPStarted（播放器未启动），9 个其他状态
- [x] 12.2 根因分析：定位 `RssParserByRule.kt:175` 中 `isUrl=true` 把 vod_id 转换为完整 URL，导致 ruleContent JS 构造的详情页 API URL 错误
- [x] 12.3 修复方案：ruleContent JS 开头添加 ID 提取逻辑（从可能被转换为完整 URL 的 rssArticle.link 中提取纯数字 vod_id）
  - 若 `rssArticle.link` 含 `/`，取最后一段 `/` 之后的内容作为 vod_id
  - 若 `rssArticle.link` 含 `?`，截取 `?` 之前的内容
- [x] 12.4 sortUrl 修复：6 个源的第一个分类返回空列表（bodyLen=81），删除空分类后验证通过
- [x] 12.5 验证结果：8 个有 sortUrl 的源全部 PASS（100%），1 个搜索型源 PASS（源[13]），1 个搜索型源 WARN（源[22]搜索接口异常）
- [x] 12.6 总通过率：9/10（90%），新增可用源 8 个
- [x] 12.7 总可用源更新：从 16 个增加到 24 个（batch1 1 + batch3 6 + batch4 17）
- [x] 12.8 归档修复后的源到 `temp/rss/rss_sources_final.json`（24 个完整通过的 RssSource JSON）
- [x] 12.9 更新 design.md §13.10 isUrl=true 陷阱与修复章节
- [x] 12.10 更新 README.md / spec.md / tasks.md 四文档同步

## 13. batch5-7 CMS 采集源扩展（总可用源从 24 个增加到 40 个）

> **实施阶段扩展**：batch5-7 继续从 TVBox 源仓库和网络搜索扩展 CMS 采集源，新增 16 个可用源，总可用源从 24 个增加到 40 个。关键技术发现：dzhipy 433/435 是 drpy 不可转化、uiautomator 精准点击、articleStyle=2 网格布局、LoadMoreView 误识别。

### batch5：TVBox 源仓库大规模筛选（8 个通过验证，5 个新增可用）

- [x] 13.1 从 6 个 TVBox 源仓库获取 840 个 sites
- [x] 13.2 筛选 type=1 且 api 为 CMS 格式路径（`/api.php/provide/vod/`）的源 29 个
- [x] 13.3 验证 API 可达性：29 个中 15 个可达
- [x] 13.4 套用 CMS 采集源转化模板（含 §13.10 isUrl=true 陷阱修复）
- [x] 13.5 真机验证：15 个可达源中 8 个完整通过（分类加载 + 列表数据 + 详情页播放 + 搜索功能）
- [x] 13.6 去重处理：8 个通过验证的源中 3 个与 batch3/batch4 已有源重复（sourceUrl 相同），去重后新增 5 个可用源

### batch6：uiautomator 精准点击验证（8 个通过验证，7 个新增可用）

- [x] 13.7 输入 22 个 CMS 源，执行首次真机验证
- [x] 13.8 首次验证结果：仅 3 个通过，19 个失败（大部分失败原因为"列表项点击位置不精确导致进入错误页面或未触发点击"）
- [x] 13.9 根因分析：固定坐标点击（`adb shell input tap x y`）在 articleStyle=2 网格布局下无法精确定位列表项位置
- [x] 13.10 二次验证方案：改用 uiautomator dump 获取 UI 层次结构 XML，解析 XML 精准定位列表项元素坐标，对每个列表项执行精准点击
- [x] 13.11 二次验证结果：5 个源通过验证（首次因点击位置不精确失败的源在精准点击后通过）
- [x] 13.12 去重处理：8 个通过验证的源中 1 个与 batch5 已有源重复，去重后新增 7 个可用源

### batch7：网络搜索 CMS 采集站（4/4 全部通过）

- [x] 13.13 网络搜索 CMS 采集站（搜索关键词为技术性关键词，非源名称）
- [x] 13.14 获取 4 个 CMS 采集站 API 端点
- [x] 13.15 验证 API 可达性：4 个全部可达
- [x] 13.16 套用 CMS 采集源转化模板（含 §13.10 isUrl=true 陷阱修复）
- [x] 13.17 真机验证：4 个全部完整通过（分类加载 + 列表数据 + 详情页播放 + 搜索功能）

### batch5-7 关键技术发现

- [x] 13.18 关键技术发现 #8：dzhipy 源仓库 433/435 是 drpy 不可转化（435 个源中 433 个是 type=3 drpy 源，实际成功率仅 10%；CMS 采集源应从 TVBox 源仓库和网络搜索获取）
- [x] 13.19 关键技术发现 #9：uiautomator 精准点击（固定坐标点击不精确导致验证失败，改用 uiautomator dump + XML 解析精准定位 UI 元素）
- [x] 13.20 关键技术发现 #10：articleStyle=2 网格布局列表项定位（网格布局列表项位置动态变化，需通过 uiautomator dump 精确获取，不能简单用固定坐标）
- [x] 13.21 关键技术发现 #11：LoadMoreView 误识别（RecyclerView 中的 LoadMoreView/FooterView 会被误认为列表项，需检查子节点 resource-id 排除）

### batch5-7 归档与文档同步

- [x] 13.22 总可用源更新：从 24 个增加到 40 个（batch1 1 + batch3 6 + batch4 17 + batch5 5 + batch6 7 + batch7 4）
- [x] 13.23 归档扩展后的源到 `temp/rss/rss_sources_final.json`（40 个完整通过的 RssSource JSON）
- [x] 13.24 更新 design.md §13.11 batch5-7 CMS 采集源扩展章节
- [x] 13.25 更新 README.md / spec.md / tasks.md 四文档同步
