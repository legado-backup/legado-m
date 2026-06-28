# spec.md — legado-source-creator Skill 改进

> **状态**：🔄 设计中 | **创建日期**：2026-06-03

---

## 1. Intent（意图）

### 为什么做这件事？

我们的 `legado-source-creator` Skill 在"知识准确性"、"JS 深度分析"、"订阅源支持"、"CF 反爬"、"自进化"方面有显著优势，但在与「阅读Skill (legado-book-source-tamer)」的深度对比中，发现了 **两个最严重的空白**和**多个高优先级缺失**：

1. **Default 语法体系完全缺失** — `class.名称@text` / `tag.div.-1@html` / `id.content@html` / `[0:10]` / `[-1:0]` / `[!0:-1]` 等 Legado 原生简写语法，社区源大量使用，我们完全没覆盖
2. **全局对象 API 完全缺失** — `book.durChapterTitle` / `chapter.url` / `source.getLoginHeader()` / `cookie.getKey()` / `cache.putFile()` 等几十个属性和方法，我们只提到了变量名

此外还缺失：53 个 JS 扩展方法、搜索/详情/目录/正文高级实战技巧、编码处理完整指南、4 条新 Rhino 陷阱等。

### 解决什么问题？

- AI 使用我们的 Skill 创建书源时，无法编写 Default 语法规则（社区源最常用的语法）
- AI 无法在 JS 中访问 book/chapter/source/cookie/cache 对象的属性和方法
- AI 缺少高级实战技巧（Cookie 清理搜索超时、正文去章节名、目录排序等）
- AI 缺少编码处理的系统化指引
- AI 缺少新发现的 Rhino 陷阱防护

---

## 2. Scope（范围）

### 做什么

| 类别 | 新增项数 | 需源码验证 |
|------|---------|-----------|
| Default 语法体系 | ~15 条规则 | 6 项 |
| 全局对象 API | ~30 个属性/方法 | 6 项 |
| JS 扩展方法补充 | ~25 个方法（高+中优先级） | 8 项 |
| 搜索高级技巧 | ~6 种模式 | 3 项 |
| 详情/目录/正文高级技巧 | ~20 种模式 | 部分需验证 |
| 编码处理完整指南 | ~10 条规则 | 3 项 |
| 动态加载系统化 | ~8 条规则 | 1 项 |
| 登录系统 API 补充 | ~10 个方法 | 2 项 |
| 新 Rhino 陷阱 | ~4 条 | 3 项 |
| 正则模式分类 | ~5 条规则 | 2 项 |
| 变量系统补充 | ~8 条规则 | 2 项 |
| HTML 分析检查清单 | ~4 页检查清单 | 无 |
| SKILL.md 流程优化 | ~3 项改进 | 无 |
| **合计** | **~137 条** | **~30 项需验证** |

### 不做什么

- **不学习**阅读Skill 的话术规范、emoji 格式、Python 工具代码嵌入、LangChain 工具体系
- **不采纳**未经验证的阅读Skill 经验（已发现多处不准确声明）
- **不采纳**未经源码确认+测试验证的经验（我们的项目是 lyc 魔改版 `gitee.com/lyc486/legado`，所有功能以该版本源码为准）
- **不增加** SKILL.md 体积（新增内容优先放入 references/ 子文档）
- **不改变**现有的源码验证机制和自进化流程（这是我们的核心优势）

### 影响哪些模块

| 模块 | 影响 |
|------|------|
| `.trae/skills/legado-source-creator/SKILL.md` | 流程优化：增加必读参考文档步骤、编码检测前置、强制获取原始 HTML |
| `.trae/skills/legado-source-creator/references/rule-syntax.md` | 新增 Default 语法章节、正则模式分类、变量系统补充、nextContentUrl 判断规则 |
| `.trae/skills/legado-source-creator/references/js-extensions/` | 新增 global-objects.md、补充各子文档方法 |
| `.trae/skills/legado-source-creator/references/special-scenarios/` | 新增 search-advanced.md、content-advanced.md、toc-advanced.md、encoding-guide.md、advanced-patterns.md |
| `.trae/skills/legado-source-creator/references/troubleshooting/` | 新增 diagnosis-flow.md、DOM vs 原始 HTML 差异表 |
| `.trae/skills/legado-source-creator/references/source-analysis/` | 新增 9 个验证文档 |
| `AGENTS.md` | 陷阱清单新增 4 条 |

---

## 3. Approach（方法）

### 技术方向

采用**"源码确认 + 测试验证"**的三阶段流水线：

```
Phase 1: 源码确认 + 测试验证 → Phase 2: 文档改进 → Phase 3: SKILL.md 流程优化
```

**Phase 1（源码确认 + 测试验证）**是核心铁律：来自阅读Skill 的 36 项经验，每项必须经过两步验证：
1. **源码确认**：在 lyc 魔改版源码（`gitee.com/lyc486/legado`）中核实方法/字段/语法的存在
2. **测试验证**：编写测试方法（Python 脚本或 Rhino JAR）进行实际测试，只有测试通过才认为合规

验证结果写入 `references/source-analysis/` 对应文档，**测试不通过的经验不写入正式文档**。

### 方案选择

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| A. 直接采纳阅读Skill经验 | 快速 | 引入错误知识（已发现多处不准确） | ❌ |
| B. 全部源码验证后采纳 | 准确 | 耗时 | ✅ |
| C. 高优先级验证+低优先级直接采纳 | 平衡 | 低优先级仍可能引入错误 | ❌ |

选择方案 B：全部源码确认+测试验证后采纳。理由：阅读Skill 已发现多处不准确声明（如声称 `:first-child` 不可用但实际 `@css:` 下可用），任何未验证的经验都可能误导 AI。只有源码确认存在且测试通过的经验才能写入我们的 skill 文档。

---

## 4. Requirements（需求）

### R1: Default 语法体系文档

- R1.1: 记录 `class.名称@text` → `.名称@text` 简写规则
- R1.2: 记录 `tag.名称.位置@提取类型` 语法
- R1.3: 记录 `id.名称@提取类型` → `#名称` 简写规则
- R1.4: 记录数组/区间写法 `[0:10]`/`[-1:0]`/`[!0:-1]`
- R1.5: 记录属性选择器高级用法 `[^=/$=/~=]`
- R1.6: 记录 `@` 连接可用空格替代
- R1.7: 记录 `text.文本` 格式
- R1.8: 记录选择器优先级 `#id > .class > tag > [attr=value] > :nth-child(2)`
- **前置条件**：验证 V3/V4/V12-V16（Default 语法解析逻辑）

### R2: 全局对象 API 文档

- R2.1: 记录 book 对象完整属性列表 + `putVariable/getVariable`
- R2.2: 记录 chapter 对象完整属性列表 + `putVariable/getVariable/putLyric/putImgUrl/update()`
- R2.3: 记录 source 对象完整方法 + 登录头/登录信息管理
- R2.4: 记录 cookie 对象完整方法
- R2.5: 记录 cache 对象完整方法
- R2.6: 记录全局变量列表（src/title/nextChapterUrl/rssArticle）
- **前置条件**：验证 V31-V36（全局对象方法存在性）

### R3: 变量系统完整说明

- R3.1: 记录 `@put/@get` vs `java.put/java.get` 区别
- R3.2: 记录 JS 中无法使用 `@get` 的限制
- R3.3: 记录 `{{java.get()}}` 模板调用方式
- R3.4: 记录 `@@` 跨栏目取值语法
- R3.5: 记录 `@put` 中 JSONPath 不需加引号的规则
- **前置条件**：验证 V8/V9

### R4: 搜索高级技巧文档

- R4.1: Cookie 清理解决搜索30秒超时
- R4.2: 搜索重定向处理
- R4.3: 繁体字搜索编码处理
- R4.4: 搜索地址变动动态获取
- R4.5: 分页 URL 不同写法
- R4.6: 多个搜索列表处理
- **前置条件**：验证 V21-V23

### R5: 详情/目录/正文高级技巧文档

- R5.1: URL 拼接三种方式（`##^##`/`##$##`/`@js:`）
- R5.2: 目录排序三种方法
- R5.3: 目录与详情页合一处理
- R5.4: 正文去章节名/去重复段落/段落拼接
- R5.5: 正文图片修改 headers
- R5.6: 漫画源/听书源正文规则

### R6: 编码处理完整指南

- R6.1: 编码判断三步法
- R6.2: charset 参数位置规则
- R6.3: `java.encodeURI()`/`java.utf8ToGbk()` 使用
- R6.4: GBK 兼容性说明
- **前置条件**：验证 V18-V20/V22-V23

### R7: 动态加载处理系统化

- R7.1: 四种 webView 启用方式
- R7.2: webJs 必须有返回值的限制
- R7.3: sourceRegex 嗅探完整流程
- **前置条件**：验证 V10

### R8: 登录系统 API 补充

- R8.1: loginCheckJs 专用函数（initUrl/getHeaderMap/getStrResponse/getResponse）
- R8.2: source 对象登录头/登录信息管理
- R8.3: CloudFlare 验证处理模式
- R8.4: loginUi 用户界面
- **前置条件**：验证 V29-V30/V34

### R9: HTML 分析检查清单

- R9.1: 搜索页/详情页/目录页/正文页字段完整性检查清单
- R9.2: 编码检测步骤
- R9.3: 浏览器 DOM vs 原始 HTML 差异表

### R10: nextContentUrl 判断规则

- R10.1: 三种场景判断规则（真下一章/同章分页/模糊按钮）
- R10.2: URL 对比法
- R10.3: select 下拉菜单分页处理
- **前置条件**：验证 V1/V2

### R11: 正则表达式三种用法分类

- R11.1: 删除匹配 `##正则`
- R11.2: 替换匹配 `##正则##替换`
- R11.3: 捕获组提取 `##正则(组)##$1`
- R11.4: OnlyOne 模式 `###` 结尾
- R11.5: AllInOne 模式 `:` 开头
- **前置条件**：验证 V6/V7

### R12: 新增 Rhino 陷阱

- R12.1: Rhino `const` 块级作用域问题
- R12.2: JSON.stringify 中变量类型问题
- R12.3: webJs 必须有返回值
- R12.4: select 下拉菜单分页陷阱
- **前置条件**：验证 V10/V11

### R13: JS 扩展方法补充

- R13.1: 高优先级方法：ajaxAll/createAsymmetricCrypto/queryTTF/replaceFont/getVerificationCode/strToBytes/bytesToStr/s2t/t2s/encodeURI/utf8ToGbk
- R13.2: 中优先级方法：webViewGetOverrideUrl/webViewGetSource/startBrowser/ajax(url,timeout)/timeFormat/timeFormatUTC
- **前置条件**：验证 V21-V28

### R14: 高级功能模式库

- R14.1: jsLib 使用规范
- R14.2: 多接口切换模式
- R14.3: 数据压缩（LZString）模式
- R14.4: 源变量控制模式
- R14.5: 图片解密完整流程

### R15: SKILL.md 流程优化

- R15.1: 在工作流程中增加"必读参考文档"步骤
- R15.2: 强制编码检测前置
- R15.3: 强制先获取原始 HTML

### R16: 订阅源浏览器内 API 文档（新增）

- R16.1: 记录预注入 JS 规则（`window.ajaxAwait`/`window.java` 等挂载方式）
- R16.2: 记录浏览器内异步函数（`ajaxAwait`/`connectAwait`/`getAwait`/`postAwait`/`webViewAwait`/`webViewGetSourceAwait`/`decryptStrAwait`/`encryptBase64Await`/`downloadFileAwait`/`readTxtFileAwait`/`importScriptAwait`/`getStringAwait`）
- R16.3: 记录 `source.login()`/`source.getLoginInfo()` 浏览器内同步调用
- **前置条件**：验证 RssJsExtensions.kt 中这些方法的存在性

### R17: 实体字段补充（新增）

- R17.1: 记录 `coverDecodeJs` 封面解密字段（BookSource 实体独立字段）
- R17.2: 记录 `imageDecode` 正文图片解密字段（ruleContent 子字段）
- R17.3: 记录发现页（sortUrl）JSON 数组配置方法（含样式控制）
- **前置条件**：验证 BookSource.kt / ContentRule.kt 中这些字段的存在性

### R18: 实战技巧细化补充（新增）

- R18.1: 阅读云（sososhu.com）验证绕过三种方法
- R18.2: 目录乱序排序完整解决方案（文本数字/属性ID/data-id 三种方法含代码）
- R18.3: 图片/正文下一页的 8 种实现模式
- R18.4: 正文去章节名的 5 种写法及适用场景
- R18.5: 搜索重定向处理的 4 种写法
- R18.6: 搜索地址变动动态获取的 2 种方法
- R18.7: 分页 URL 不同写法的 4 种模式
- R18.8: 多个搜索列表处理的 2 种方法
- R18.9: URL 拼接的 6 种方式
- R18.10: 封面 URL 通过 ID 计算拼接的 2 种写法
- R18.11: onclick 属性章节 URL 处理
- R18.12: `@textNodes` 提取类型说明
- R18.13: `[property$=xxx]` 属性选择器高频用法
- R18.14: Default 语法 vs `@css:` 前缀下伪类选择器可用性差异
- R18.15: `@put` 在 JSON 规则中的完整写法示例
- R18.16: `@@` 跨栏目取值的多种用法
- **前置条件**：部分需源码确认+测试验证

### R19: 已有知识文档化（新增）

- R19.1: 将 AGENTS.md 陷阱 #18（`java.post()` headers NativeObject→Map 失败）同步到 troubleshooting 文档
- R19.2: 补充 `java.ajax()` POST URL 格式的完整说明到 network.md
- R19.3: 补充 `java.log()`/`java.logType()` 调试方法到 utils.md
- R19.4: 补充 `java.md5Encode16()` 取中间16位 MD5 到 crypto-encoding.md
- R19.5: 补充 `java.getSource()`/`java.toNumChapter()`/`java.toURL()`/`java.randomUUID()`/`java.androidId()` 辅助方法到 utils.md
- R19.6: 补充 `java.htmlFormat()` 到 utils.md
- R19.7: 补充 `java.importScript()` 到 advanced.md
- R19.8: 补充 `java.cacheFile()`/`java.downloadFile()` 等文件操作方法到 file-operations.md
- R19.9: 补充 `java.toast()`/`java.longToast()` 到 ui-interaction.md
- R19.10: 补充 `java.digestHex()`/`java.digestBase64Str()`/`java.HMacBase64()`/`java.createSign()` 到 crypto-encoding.md
- R19.11: loginCheckJs 必须返回 result 否则 NPE 崩溃（已有陷阱，需文档化）
- **前置条件**：每项需在 lyc 魔改版源码中确认存在性

---

## 5. Scenarios（场景）

### 正常流程

1. AI 接到书源创建任务
2. AI 读取 SKILL.md，按流程先读参考文档
3. AI 使用 Default 语法编写搜索规则（`.book-item@text`）
4. AI 在 JS 中使用 `book.durChapterTitle` 获取当前阅读章节
5. AI 使用 `cookie.removeCookie()` 解决搜索超时
6. AI 使用正文去章节名正则 `##{{chapter.title}}`
7. AI 使用编码检测步骤处理 GBK 网站
8. 自测通过，交付

### 异常流程

1. 阅读Skill 声称 `:first-child` 不可用 → 我们验证后发现 `@css:` 前缀下可用 → 正确记录差异
2. 阅读Skill 声称 `source.put/get` 键值对存在 → 在 lyc 魔改版源码中确认存在 → 测试通过后采纳
3. 阅读Skill 声称 `java.utf8ToGbk()` 存在 → 源码确认不存在 → 不采纳
4. 源码确认存在但测试不通过 → 记录为已知限制，不写入正式文档

### 边界条件

- 验证项在当前 lyc 魔改版中不存在但在旧版本中存在 → 标注版本差异
- 验证项的签名与阅读Skill 描述不一致 → 以 lyc 魔改版源码为准
- 同一功能有多种实现方式 → 记录所有方式并标注推荐用法
- 源码确认存在但无法编写有效测试 → 标注为"待验证"，不写入正式文档
