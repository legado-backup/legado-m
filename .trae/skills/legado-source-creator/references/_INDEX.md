# Legado Source Creator - 参考文档索引

> 按用途快速定位所需文档。标注适用范围：书源 / 订阅源 / 通用。
> 大文件已拆分为子目录，先读子目录的 `_index.md` 速查索引，再按需读取子文档。

## 核心文档（必读，未拆分）

| 文档 | 适用范围 | 用途 | 何时查阅 |
|------|----------|------|----------|
| [rule-syntax.md](./rule-syntax.md) | 书源 + 订阅源 | Legado规则语法核心：CSS/JSONPath/XPath/Regex/JS五种解析模式、规则前缀、组合规则(&&/\|\|/%%)、属性后缀(@text/@href等) | 创建任何源的第一步，理解规则怎么写 |
| [url-template.md](./url-template.md) | 书源 + 订阅源 | URL模板语法：searchUrl/exploreUrl/sourceUrl的构造方法、POST请求配置、模板变量({{key}}/{{page}}) | 构造搜索URL、发现URL、订阅源URL |
| [booksource-schema.md](./booksource-schema.md) | 书源 + 订阅源 | BookSource/RssSource实体完整字段定义 | 检查字段定义时 |
| [examples.md](./examples.md) | 书源 + 订阅源 | 完整书源/订阅源JSON示例 | 需要参考时 |

## 拆分文档（先读 _index.md 速查索引）

| 目录 | 原文件行数 | 拆分后子文档数 | 用途 |
|------|-----------|--------------|------|
| [troubleshooting/](./troubleshooting/_index.md) | 1181行 | 6个子文档 + 索引 | 常见陷阱与故障排除 |
| [js-extensions/](./js-extensions/_index.md) | 1209行 | 11个子文档 + 索引 | JS扩展函数完整参考 |
| [js-patterns/](./js-patterns/_index.md) | 710行 | 11个子文档 + 索引 | JS模式参考手册 |
| [special-scenarios/](./special-scenarios/_index.md) | 781行 | 14个子文档 + 索引 | 登录/验证码/加密/视频/WebSocket调试等特殊场景 |
| [source-analysis/](./source-analysis/_index.md) | — | 6个子文档 + 索引 | Legado源码深度分析验证 |
| [site-features/](./site-features/_INDEX.md) | — | 4个子文档 + 索引 | 真实源验证积累的高频问题模式与修复方案 |
| [rule-construction-guide/](./rule-construction-guide/_index.md) | — | 3个子文档 + 索引 | Phase 2 规则构建：解析方式决策树+字段填写模板+网站类型策略 |

### cms-samples/（CMS 样本库）
标准 CMS 模板 HTML 样本 + 选择器映射，用于 CF 保护网站的选择器验证。

| 文件 | 说明 |
|------|------|
| cms-samples/_INDEX.md | 样本库索引 |
| cms-samples/maccms-v10/ | 苹果CMS V10 样本（list/detail/search/play + selectors.json） |
| cms-samples/maccms-x10/ | 苹果CMS X10 样本（list/detail/search/play + selectors.json） |

## 按任务类型索引

### 创建书源

| 文档 | 用途 | 重点 |
|------|------|------|
| [rule-syntax.md](./rule-syntax.md) | 规则语法 | 全部 |
| [booksource-schema.md](./booksource-schema.md) | BookSource实体字段定义 | 5组规则字段 |
| [special-scenarios/](./special-scenarios/_index.md) | 特殊场景处理 | 先读索引，按需查登录/加密/视频子文档 |
| [examples.md](./examples.md) | 示例源分析 | 书源部分 |
| [js-patterns/](./js-patterns/_index.md) | JS技巧大全 | 先读索引，按需查对应子文档 |

### 创建订阅源

| 文档 | 用途 | 重点 |
|------|------|------|
| [rule-syntax.md](./rule-syntax.md) | 规则语法 | 全部 |
| [special-scenarios/rss-basic.md](./special-scenarios/rss-basic.md) | RSS基础 | 订阅源创建流程 |
| [special-scenarios/rss-advanced.md](./special-scenarios/rss-advanced.md) | RSS高级 | HLS/iframe/多集视频 |
| [examples.md](./examples.md) | 示例源分析 | 订阅源部分 |
| [js-patterns/master-analysis.md](./js-patterns/master-analysis.md) | 订阅源JS技巧 | 第十三章 |

### 编写JS规则

| 文档 | 用途 | 重点 |
|------|------|------|
| [js-patterns/](./js-patterns/_index.md) | JS技巧大全 | 先读索引，按功能定位子文档 |
| [js-extensions/](./js-extensions/_index.md) | JS扩展函数参考 | 先读索引，按函数名定位子文档 |

### 修复/调试问题

| 文档 | 用途 | 重点 |
|------|------|------|
| [troubleshooting/](./troubleshooting/_index.md) | 常见问题和修复方案 | 先读索引，按关键词定位子文档 |
| [special-scenarios/anti-crawl.md](./special-scenarios/anti-crawl.md) | 反爬/CF处理 | 403/Cookie/登录 |

## 自进化指引

> 当完成书源/订阅源创建或修复后，需要将新经验更新到对应子文档。
> **查询时用"按任务类型索引"，写入时用本指引。**

| 新经验类型 | 追加到 | 说明 |
|-----------|--------|------|
| 新的反爬/获取问题 | troubleshooting/html-fetch-traps.md | 获取失败的诊断和绕过方法 |
| 新的加密/解密**陷阱** | troubleshooting/crypto-traps.md | 导致错误的用法（如API不兼容、Padding错误） |
| 新的Rhino/JS语法问题 | troubleshooting/rhino-js-traps.md | Rhino引擎限制和兼容性问题 |
| 新的源类型/NPE/搜索问题 | troubleshooting/source-type-traps.md | 源配置字段导致的运行时错误 |
| 新的分析技巧 | troubleshooting/analysis-best-practices.md | 网站分析流程和字段配置经验 |
| 新的修复案例 | troubleshooting/community-fix-experience.md | 实际修复的完整案例记录 |
| 新的JS函数用法 | js-extensions/ 对应子文档（先查 _index.md） | 按函数类别定位子文档 |
| 新的JS模式/技巧 | js-patterns/ 对应子文档（先查 _index.md） | 按功能类别定位子文档 |
| 新的登录/验证码方案 | special-scenarios/login.md 或 captcha.md | 登录和验证码处理方案 |
| 新的加密认证**方案** | special-scenarios/encryption.md | 成功的加密/签名实现方案（陷阱归 troubleshooting） |
| 新的加密图片**方案** | special-scenarios/encrypted-images.md | 成功的图片解密模板（陷阱归 troubleshooting） |
| 新的视频/音频方案 | special-scenarios/video-audio.md | 播放地址提取和播放器配置 |
| 新的反爬/CF**方案** | special-scenarios/anti-crawl.md | 主动绕过方案（诊断归 troubleshooting） |
| 新的WebSocket/真机调试经验 | special-scenarios/websocket-debug.md | WebSocket调试协议、端口、陷阱 |
| 新的批量校验/死源清理经验 | SKILL.md "能力边界"章节 + basic-memory | 批量校验模式、死源清理流程、前端一键清理 |
| 新的RSS订阅源方案 | special-scenarios/rss-basic.md 或 rss-advanced.md | 基础归 basic，高级归 advanced |
| 新的CMS样本 | cms-samples/ 对应子目录 | 新增CMS模板HTML样本+选择器映射 |
| 新的源码分析验证 | source-analysis/ 对应子文档 | Legado源码深度分析结论 |
| 新的真实源验证经验 | site-features/ 对应子文档 | 真实源验证发现的高频问题模式与修复方案 |

**⚠️ 追加前必须检查**：读取对应子目录的 `_index.md`，确认新经验属于哪个子文档的覆盖范围，避免重复创建。
**⚠️ 陷阱 vs 方案**：导致错误/报错的用法 → troubleshooting/；成功的实现方案 → special-scenarios/。
