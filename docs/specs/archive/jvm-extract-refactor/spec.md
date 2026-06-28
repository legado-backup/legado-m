# Spec: JVM 仿真服务端架构重构

## 1. Intent（意图）

将当前「从零重写」的 JVM 仿真服务端（MinimalMockJsExtensions/MockSymmetricCrypto 等）替换为「从 Legado 真机源码直接抽取」的架构，消除因臆测导致的反复 bug，合并 4 个 JAR 为 1 个，解决性能问题，并实际优化用户提供的真实源。

## 2. Scope（范围）

### 2.1 涉及的 Legado 核心类（14 个）

| 类名 | 源码路径 | Android 依赖等级 | 抽取策略 |
|------|---------|----------------|---------|
| RuleDataInterface | `model/analyzeRule/RuleDataInterface.kt` | A | 直接复制 |
| RuleAnalyzer | `model/analyzeRule/RuleAnalyzer.kt` | A | 直接复制 |
| RuleData | `model/analyzeRule/RuleData.kt` | A | 替换 GSON 引用 |
| CustomUrl | `model/analyzeRule/CustomUrl.kt` | A | 替换 GSON 引用 |
| AnalyzeByJSoup | `model/analyzeRule/AnalyzeByJSoup.kt` | B | 删 @Keep |
| AnalyzeByJSonPath | `model/analyzeRule/AnalyzeByJSonPath.kt` | B | 删 @Keep |
| AnalyzeByRegex | `model/analyzeRule/AnalyzeByRegex.kt` | B | 删 @Keep |
| QueryTTF | `model/analyzeRule/QueryTTF.java` | B | 删 @Keep |
| AnalyzeByXPath | `model/analyzeRule/AnalyzeByXPath.kt` | C | 替换 TextUtils |
| AnalyzeRule | `model/analyzeRule/AnalyzeRule.kt` | D | 抽象 JsExtensions 接口 |
| AnalyzeUrl | `model/analyzeRule/AnalyzeUrl.kt` | D | 移除 Glide/ExoPlayer |
| JsExtensions | `help/JsExtensions.kt` | D | 拆分接口+实现 |
| BookSource | `data/entities/BookSource.kt` | D | 移除 Room/Parcelize |
| RssSource | `data/entities/RssSource.kt` | D | 移除 Room/Parcelize |

> **⚠️ 隐藏继承链**：BookSource/RssSource 通过 `BaseSource`（`interface BaseSource : JsExtensions`）间接继承 JsExtensions。BaseSource 有 77 个 import 语句，是最大的隐藏依赖链。抽取时移除 `: BaseSource` 继承，改为独立 POJO。JsExtensions 方法由 JsExtensionsStub 在 AnalyzeRule/AnalyzeUrl 中注入。

### 2.2 不在范围内（但需在 Debugger 中内联实现）

- Legado 的 UI 层（Activity/Fragment/ViewModel）
- Legado 的数据库层（Room DAO/Repository）
- Legado 的服务层（Service/Receiver）
- Legado 的渲染层（WebView/RecyclerView）
- **执行流程层**（WebBook/Rss/BookList/BookInfo/BookChapterList/BookContent/RssParserByRule）：不抽取到新模块，但在 RssSourceDebugger/BookSourceDebugger 中需内联复现其核心调用链（AnalyzeUrl 构造请求 → getStrResponse → loginCheckJs → AnalyzeRule 解析）
- **BaseSource 接口**：不抽取，BookSource/RssSource 移除继承

### 2.3 依赖版本锁定

| 依赖 | 版本 | 锁定原因 |
|------|------|---------|
| jsoup | 1.16.2 | jsoup#2017 破坏性变更 |
| rhino | 1.8.1 | Android 6 以下兼容 |
| hutool-crypto | 5.8.22 | 书源加解密依赖 |
| gson | 2.13.2 | JSON 序列化 |
| okhttp | 5.3.2 | HTTP 客户端 |
| json-path | 2.10.0 | JSONPath 解析 |
| JsoupXpath | 2.5.3 | XPath 解析 |
| commons-text | 1.13.1 | HTML 实体反转 |

## 3. Approach（方法）

### 3.1 核心策略：抽取而非重写

```
当前架构（错误）：
  MinimalMockJsExtensions → 猜测 Legado 行为 → 从零实现 → Bug 层出不穷

目标架构（正确）：
  Legado 源码 → 移除 Android 依赖 → 保留核心逻辑 → 单 JAR 打包
```

> **🔴 源码参照声明**：本次改造的最核心流程以及代码参照对象一定是 Legado 开源阅读的源码。所有抽取逻辑必须来自 `app/src/main/java/io/legado/app/` 下的真机源码，禁止任何形式的臆测或从零重写。每个任务必须标注源码参照路径（格式见 design.md 第7.2节）。

### 3.2 降级能力边界

JsExtensionsStub 的降级方法有以下能力边界，Skill 和 Python 客户端必须适配：

| 能力 | 真机行为 | Stub 降级 | 影响场景 |
|------|---------|---------|---------|
| **WebView** | 执行 JS 动态加载 | HTTP+正则，无法执行 JS | PJAX 站点、m3u8 提取 |
| **startBrowser** | 弹出浏览器人工验证 | 抛异常，不可用 | CF 盾、验证码 |
| **getVerificationCode** | 弹出验证码图片 | 抛异常，不可用 | 搜索验证码 |
| **openVideoPlayer** | 打开内置播放器 | 抛异常，不可用 | 视频播放 |
| **CookieStore** | 持久化存储 | 内存实现，重启丢失 | Cookie 依赖场景 |
| **文件操作** | appCtx.externalCache | 临时目录 | 文件读写 |
| **androidId** | 设备唯一 ID | 固定值 | 设备识别 |
| **getWebViewUA** | 真实 UA | 固定 UA | UA 检测 |

> **关键限制**：Stub 降级意味着依赖 WebView/startBrowser/getVerificationCode 的源在 JVM 环境中不可用，需用户真机处理。这部分源约占 10-15%，需在 Skill 中明确标注。

### 3.3 五阶段流水线

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
抽取A/B/C级  抽取D级    合并单JAR   性能优化    真实源优化
(9个类)     (5个类)   (fat JAR)  (批处理)    (修复源JSON)
```

### 3.4 JsExtensions 接口拆分策略

JsExtensions 是最大的障碍（直接依赖 Activity/WebView/Context）。拆分方案：

```
JsExtensions（真机）
├── JsExtensionsInterface（JVM 接口，纯逻辑）
│   ├── 加解密方法（AES/DES/RSA/Base64...）
│   ├── HTTP 方法（get/post/ajax...）
│   ├── 规则方法（getString/getStringList...）
│   ├── Cookie 方法（getCookie/getCookieMap...）
│   └── 工具方法（base64Decode/base64Encode/htmlEncode...）
├── JsExtensionsStub（JVM 实现，WebView 等降级为 HTTP）
└── JsExtensionsAndroid（Android 实现，保留真机行为）
```

## 4. Requirements（需求）

### FR-1: A/B/C 级类抽取（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-1.1 | 直接复制 RuleDataInterface/RuleAnalyzer | 编译通过，零修改 |
| FR-1.2 | 替换 RuleData/CustomUrl 中的 GSON 引用 | 用 `Gson()` 直接替代 `GSON` 单例 |
| FR-1.3 | 删除 AnalyzeByJSoup/AnalyzeByJSonPath/AnalyzeByRegex/QueryTTF 的 @Keep 注解 | 编译通过 |
| FR-1.4 | 替换 AnalyzeByXPath 的 TextUtils.join | 用 Kotlin `joinToString()` 替代（源码 L138: `TextUtils.join("\n", it)`） |
| FR-1.5 | 验证：A/B/C 级 9 个类全部编译通过 | `gradlew compileKotlin` 成功 |

### FR-2: D 级类抽取 — 数据模型（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-2.1 | 移除 BookSource 的 Room 注解（@Entity/@PrimaryKey/@ColumnInfo/@TypeConverters） | 改为纯 POJO data class |
| FR-2.2 | 移除 BookSource 的 Parcelize | 改为 `Serializable`（Java io，非 kotlinx.serialization） |
| FR-2.3 | 移除 RssSource 的 Room 注解 + Parcelize | 同上 |
| FR-2.4 | 移除 BookSource/RssSource 的 TextUtils 依赖 | 用 Kotlin `isBlank()` 替代 |
| FR-2.4b | 移除 BookSource/RssSource 的 `: BaseSource` 继承 | 改为独立 POJO，不继承 JsExtensions |
| FR-2.5 | 验证：BookSource/RssSource 可被 Gson 正确序列化/反序列化 | JSON → 对象 → JSON 往返一致 |

### FR-3: D 级类抽取 — JsExtensions 接口拆分（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-3.1 | 创建 JsExtensionsInterface 接口，包含所有非 UI 方法签名 | 接口编译通过 |
| FR-3.2 | 创建 JsExtensionsStub 实现，WebView 类方法降级为 HTTP 请求 | `webViewGetSource` 用 okhttp+正则替代 |
| FR-3.3 | JsExtensionsStub 的 `startBrowserAwait`/`getVerificationCode` 标记为不可用 | 抛 NoStackTraceException，提示需真机处理（与 design.md 6.1 一致） |
| FR-3.4 | 移除 JsExtensions 中的 Activity/Context/UI 依赖 | 无 `android.*` import |
| FR-3.5 | 验证：JS 规则中 `java.xxx()` 调用全部能路由到 Stub 实现 | 单元测试覆盖 |

### FR-4: D 级类抽取 — AnalyzeRule（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-4.1 | 移除 AnalyzeRule 的 TextUtils 依赖 | 用 Kotlin 替代 |
| FR-4.2 | 将 AnalyzeRule 对 JsExtensions 的引用改为 JsExtensionsInterface | 编译通过 |
| FR-4.3 | 将 AnalyzeRule 对 CacheManager 的引用改为接口 | 创建 CacheManagerInterface |
| FR-4.4 | 将 AnalyzeRule 对 NetworkUtils 的引用改为 JVM 兼容实现 | 创建 NetworkUtilsStub |
| FR-4.5 | 验证：AnalyzeRule 能正确解析 CSS/XPath/JSONPath/Regex/JS 五种规则 | 单元测试覆盖 |

### FR-5: D 级类抽取 — AnalyzeUrl（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-5.1 | 移除 AnalyzeUrl 的 Glide 依赖（GlideUrl/GlideHeaders） | 删除相关 import 和方法 |
| FR-5.2 | 移除 AnalyzeUrl 的 ExoPlayer 依赖（MediaItem） | 删除相关 import 和方法 |
| FR-5.3 | 替换 AnalyzeUrl 的 `android.util.Base64` | 用 `java.util.Base64` 替代 |
| FR-5.4 | 将 AnalyzeUrl 对 CookieStore 的引用改为接口 | 创建 CookieStoreInterface |
| FR-5.5 | 验证：AnalyzeUrl 能正确构造 URL（含 `{{page}}`/`@js:`/header/body） | 单元测试覆盖 |

### FR-6: 合并单 JAR（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-6.1 | 创建新的 Gradle 模块 `.trae/skills/legado-source-creator/tools/legado-jvm/` | 模块结构完整 |
| FR-6.2 | 将所有抽取的类放入新模块 | 14 个核心类 + 接口 + Stub |
| FR-6.3 | 配置 fat JAR 打包（shadow plugin 或 fatJar task） | `gradlew fatJar` 生成单个 JAR |
| FR-6.4 | 保留 stdin/stdout JSON 协议兼容 | debug-source.py 无需大改 |
| FR-6.5 | 删除旧的 MVP1-4 目录（或标记为 deprecated） | 旧代码不再使用 |

### FR-7: 批处理模式（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-7.1 | 实现 `batch` 命令：一次接收多个源 JSON，顺序处理 | 输入 JSON 数组，输出结果数组 |
| FR-7.2 | JVM 启动一次处理所有源，不重复启动 | 7 个源总耗时 <15 秒（当前 30+ 秒） |
| FR-7.3 | 保留单源 `debugRssSource`/`debugBookSource` 命令兼容 | 单源调用行为不变 |

### FR-8: 真实源优化（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-8.1 | 用新 JAR 重新测试全部 7 个真实 RSS 源 + 1 个书源 | 输出测试报告 |
| FR-8.2 | 对测试失败的源，分析根因并修复源 JSON 规则 | 修复后的源通过测试 |
| FR-8.3 | 对正文为空的源（acgfta/611371056），分析是否可优化规则 | 输出优化建议或修复规则 |
| FR-8.4 | 对 mjv006（网站反爬），输出用户操作建议 | 标记为需用户介入 |
| FR-8.5 | 验证：优化后的真实源通过率 >85% | 7/8 源通过 |

### FR-9: 源码验证流程（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-9.1 | 每个抽取的类必须先阅读 Legado 源码再动手 | 提交时附源码路径引用 |
| FR-9.2 | 抽取后的类与源码 diff 仅包含 Android 依赖移除 | diff 不含逻辑变更 |
| FR-9.3 | 对关键方法（getString/getStringList/getElements/getStrResponse）做行为对比测试 | 同输入 → 同输出 |

### FR-10: Python 客户端全面适配（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-10.1 | 适配 debug-source.py：JAR 路径 + batch 模式 + 错误处理 | 能正确调用新 JAR |
| FR-10.2 | 适配 test_all_sources.py / quick-verify.py / deep-verify.py | 验证逻辑适配新 JAR 输出 |
| FR-10.3 | 适配 classify-and-fix.py / auto_fixer.py / degradation_chain.py | 修复逻辑适配新 JAR 行为 |
| FR-10.4 | 适配 site_type_detector.py / obstacle_resolver.py / error_translator.py | 与新 JAR 的 CookieStore/NetworkUtils 对齐 |
| FR-10.5 | 验证：所有 Python 脚本能正确调用新 JAR 并解析输出 | 无兼容性错误 |

### FR-11: Skill 适配性改造（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-11.1 | 更新 SKILL.md：JAR 路径 + 架构描述 + 批处理说明 + 5 阶段工作流 | SKILL.md <500 行，与实际一致 |
| FR-11.2 | 更新 AI_README.md：JAR 路径 + 验证脚本清单 + 架构说明 | 与实际一致 |
| FR-11.3 | 更新 references/ 目录：规则语法/URL模板/实体字段/示例源 | 与抽取后的 AnalyzeRule/AnalyzeUrl 行为一致 |
| FR-11.4 | 更新 troubleshooting/ 79 条陷阱：移除已修复陷阱 + 新增 Stub 降级陷阱 | 陷阱清单与新 JAR 行为一致 |
| FR-11.5 | 更新 js-extensions/ 和 js-patterns/：标注 Stub 完整实现 vs 降级方法 | 每个方法有实现状态标注 |
| FR-11.6 | 更新经验教训：basic-memory 标注旧经验过时 + 写入新架构经验 | 新旧经验有明确区分 |
| FR-11.7 | 更新验证脚本（verify-*.py / analyze-*.py）：JAR 路径 + 行为适配 | 所有脚本能正确调用新 JAR |

### FR-12: 大规模真实源测试（P0）

| ID | 需求 | 验收标准 |
|----|------|---------|
| FR-12.1 | 创建 large-scale-test.py：科学抽样 + 批处理测试 + 结果分类 | 脚本可运行 |
| FR-12.2 | 从 temp/book/ 25 个文件（23,881 源）抽样 200 个书源测试 | 书源通过率 >70% |
| FR-12.3 | 从 temp/rss/ 22 个文件（2,702 源）抽样 100 个订阅源测试 | 订阅源通过率 >75% |
| FR-12.4 | 分析失败源：区分 Bug/规则错误/仿真差距/需用户介入 | 每个失败源有分类和修复建议 |
| FR-12.5 | 对 Bug 类问题修复 JAR 代码，回归验证 | 修复后通过率提升 |
| FR-12.6 | 生成大规模测试报告 + 经验反哺 basic-memory + references/ | 报告输出，经验写入 |

## 5. Scenarios（场景）

### 场景 1: A/B/C 级类直接抽取

**输入**：Legado 源码 `model/analyzeRule/AnalyzeByJSoup.kt`
**流程**：
1. 阅读 AnalyzeByJSoup.kt 源码
2. 复制到 `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/model/analyzeRule/AnalyzeByJSoup.kt`
3. 删除 `import androidx.annotation.Keep`
4. 删除 `@Keep` 注解
5. 编译验证
**验收**：编译通过，行为与源码一致

### 场景 2: JsExtensions 接口拆分

**输入**：Legado 源码 `help/JsExtensions.kt`（500+ 行）
**流程**：
1. 阅读 JsExtensions.kt 源码，分类所有方法
2. 创建 `JsExtensionsInterface.kt` 接口，包含所有非 UI 方法签名
3. 创建 `JsExtensionsStub.kt` 实现，WebView 类方法降级为 HTTP
4. AnalyzeRule/AnalyzeUrl 引用改为 JsExtensionsInterface
**验收**：JS 规则中 `java.xxx()` 调用全部能路由到 Stub

### 场景 3: 批处理模式

**输入**：7 个 RSS 源 JSON 文件
**流程**：
1. JVM 启动一次
2. 读取 `batch` 命令，包含 7 个源 JSON 数组
3. 顺序处理每个源，输出结果数组
4. JVM 退出
**验收**：总耗时 <15 秒（当前 30+ 秒）

### 场景 4: 真实源优化 — mjv006

**输入**：`output/rss/mjv006-video-source.json`
**流程**：
1. 用新 JAR 测试 mjv006
2. 网站返回占位页（2318 字节）
3. 分析：网站反爬检测，非代码 bug
4. 输出用户操作建议：需用户提供 Cookie 或使用真机 WebView
**验收**：标记为需用户介入，附操作建议

### 场景 5: 真实源优化 — acgfta 正文为空

**输入**：`output/rss/acgfta-anime-source.json`
**流程**：
1. 用新 JAR 测试 acgfta
2. 列表解析通过，正文为空（WebView 依赖）
3. 分析 ruleContent 中的 `webViewGetSource` 调用
4. 尝试优化：用 HTTP 请求 + 正则提取 m3u8 URL
5. 如果 HTTP 方式无法获取，标记为需用户介入
**验收**：输出优化建议或修复后的规则

### 场景 6: 源码行为对比测试

**输入**：AnalyzeRule.getString 方法
**流程**：
1. 从 Legado 源码阅读 getString 方法逻辑
2. 抽取到 JVM 模块
3. 编写对比测试：同输入 HTML + 同规则 → 对比输出
4. 如果输出不一致，分析差异并修复
**验收**：抽取后的 getString 与源码行为 100% 一致

## 6. 验收标准

### 功能验收

- [ ] FR-1.5 A/B/C 级 9 个类全部编译通过
- [ ] FR-2.5 BookSource/RssSource 可被 Gson 正确序列化/反序列化
- [ ] FR-3.5 JS 规则中 `java.xxx()` 调用全部能路由到 Stub 实现
- [ ] FR-4.5 AnalyzeRule 能正确解析 CSS/XPath/JSONPath/Regex/JS 五种规则
- [ ] FR-5.5 AnalyzeUrl 能正确构造 URL（含 `{{page}}`/`@js:`/header/body）
- [ ] FR-6.3 `gradlew fatJar` 生成单个 JAR
- [ ] FR-7.2 7 个源总耗时 <15 秒
- [ ] FR-8.5 优化后的真实源通过率 >85%
- [ ] FR-9.2 抽取后的类与源码 diff 仅包含 Android 依赖移除
- [ ] FR-10.5 所有 Python 脚本能正确调用新 JAR 并解析输出
- [ ] FR-11.1 SKILL.md <500 行，与实际架构一致
- [ ] FR-11.4 troubleshooting 79 条陷阱与新 JAR 行为一致
- [ ] FR-11.6 basic-memory 新旧经验有明确区分
- [ ] FR-12.2 书源大规模测试通过率 >70%（200 个抽样）
- [ ] FR-12.3 订阅源大规模测试通过率 >75%（100 个抽样）

### 非功能验收

- [ ] 单 JAR 文件大小 <15MB
- [ ] JVM 启动时间 <2 秒
- [ ] 抽取后的代码与 Legado 源码逻辑一致率 >95%
- [ ] 无 MinimalMockJsExtensions/MockSymmetricCrypto 等自造类
- [ ] 旧 MVP1-4 目录标记为 deprecated
- [ ] debug-source.py 协议向后兼容
