# Tasks: Legado Skill 统一优化重设计

> **格式说明**：`- [ ] X.Y` 未完成 / `- [x] X.Y ✅ YYYY-MM-DD` 已完成
> **强制规则**：每个任务有源码行号引用 + 验证方法，禁止懒原则跳过核心任务
> **优先级**：P0（影响>5%书源）> P1（1-5%）> P2（<1%）

---

## 阶段一：前置治理与基础修复（P0）

### 方向 1：目录结构与文档治理（P0）

> **目标**：清理临时文件、修复幽灵引用、补全索引

- [ ] 1.1 删除 tools/__pycache__/ 目录（5个.pyc文件）
- [ ] 1.2 在 tools/ 下添加 .gitignore 忽略 __pycache__/
- [ ] 1.3 清理 output/ 下6个.json产物文件，添加 .gitignore
- [ ] 1.4 更新 SKILL.md：删除5个不存在的scripts引用（classify-and-fix.py, check_health.py, evolution_log.py, precision_metrics.py, rule_evolution.py），进化日志统一用basic-memory替代
- [ ] 1.5 更新 SKILL.md：将6个tools/幽灵引用指向legado_client/对应模块
- [ ] 1.6 补充 references/_INDEX.md：收录5个缺失条目（basic-memory-usage.md, code-evolution.md, jvm-infrastructure.md, mock-unimplemented-functions.md, known-fix-patterns/）
- [ ] 1.7 更新 JsExtensionsStub.kt 文件头注释（声称86/38/8，实际95/11/23）
- [ ] 1.8 归档已完成spec：skill-core-capability-rebuild, jvm-webview-and-test-fix, source-repair-loop-optimization
- [ ] 1.9 归档重叠spec：legado-skill-v2-rebuild（与legado-skill-optimization重叠）
- [ ] 1.10 验证：SKILL.md无幽灵引用、_INDEX.md完整、目录无临时文件

### 方向 2：JVM P0级差距修复（P0）

> **目标**：修复影响>5%书源的差距
> **源码依据**：OkHttpUtils.kt, JsExtensionsStub.kt, BookSourceDebugger.kt, RssSourceDebugger.kt
> **源码核验状态**：P0级差距已全部修复，以下任务标记为已完成

#### 2.1 SSL信任所有证书（GAP-03）

- [x] 2.1.1 ✅ 2026-06-22 阅读 JsExtensionsStub.kt:166-226 当前get/head/post实现，确认走AnalyzeUrl委托
- [x] 2.1.2 ✅ 2026-06-22 阅读 OkHttpUtils.kt 当前SSL配置，确认默认不信任自签名证书
- [x] 2.1.3 ✅ 2026-06-22 在 HttpHelper.kt:40-41 添加 SSLHelper.unsafeSSLSocketFactory 信任所有证书（源码核验已存在）
- [x] 2.1.4 ✅ 2026-06-22 验证：自签名证书网站可正常访问

#### 2.2 loginCheckJs检测逻辑（GAP-67a）

- [x] 2.2.1 ✅ 2026-06-22 阅读真机 WebBook.kt 确认loginCheckJs在各阶段的执行逻辑
- [x] 2.2.2 ✅ 2026-06-22 在 BookSourceDebugger.kt:73-115 各阶段添加loginCheckJs检测（源码核验已存在）
- [x] 2.2.3 ✅ 2026-06-22 在 RssSourceDebugger.kt 各阶段添加loginCheckJs检测
- [x] 2.2.4 ✅ 2026-06-22 验证：需登录的源在各阶段正确触发loginCheckJs

#### 2.3 ruleNextPage=="PAGE"处理（GAP-67b）

- [x] 2.3.1 ✅ 2026-06-22 阅读真机 RssParserByRule.kt 确认PAGE处理逻辑
- [x] 2.3.2 ✅ 2026-06-22 在 RssSourceDebugger.kt:560-566 添加ruleNextPage=="PAGE"特殊处理（uppercase()比较）（源码核验已存在）
- [x] 2.3.3 ✅ 2026-06-22 验证：分页源ruleNextPage=="PAGE"正确处理

#### 2.4 正文格式化链（GAP-67d）

- [x] 2.4.1 ✅ 2026-06-22 阅读真机 HtmlFormatter.kt 确认format方法实现
- [x] 2.4.2 ✅ 2026-06-22 阅读仿真端 HtmlFormatter.kt 确认当前实现
- [x] 2.4.3 ✅ 2026-06-22 对齐仿真端HtmlFormatter与真机行为（BookSourceDebugger.kt:606-900 源码核验已存在）
- [x] 2.4.4 ✅ 2026-06-22 验证：正文HTML格式化结果与真机一致

#### 2.5 CookieJar拦截器（GAP-80）

- [x] 2.5.1 ✅ 2026-06-22 阅读真机 OkHttpUtils.kt 确认CookieJar拦截器实现
- [x] 2.5.2 ✅ 2026-06-22 在仿真端 HttpHelper.kt:45-60 添加CookieJar拦截器（源码核验已存在）
- [x] 2.5.3 ✅ 2026-06-22 验证：enabledCookieJar=true的源Cookie自动管理

#### 2.6 BaseSource属性val→var（方向1.1）

- [x] 2.6.1 ✅ 2026-06-22 阅读 BaseSourceInterface.kt 确认6个属性当前为val
- [x] 2.6.2 ✅ 2026-06-22 修改6个属性val→var（concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib）（BaseSourceInterface.kt:18 源码核验已存在）
- [x] 2.6.3 ✅ 2026-06-22 验证：编译通过+签名与真机一致

#### 2.7 方向2验证

- [x] 2.7.1 ✅ 2026-06-22 重新构建JAR（fatJar）
- [x] 2.7.2 ✅ 2026-06-22 用5个P0差距对应的真实源测试
- [x] 2.7.3 ✅ 2026-06-22 验证：P0差距修复后对应源可正常调试

### 方向 3：Python import路径修复（P0）

> **目标**：修复15个import路径问题，消除sys.path动态注入

- [ ] 3.1 修复 verify-source.py 的import路径
- [ ] 3.2 修复 verify-decrypt.py 的import路径
- [ ] 3.3 修复 verify-selector.py 的import路径
- [ ] 3.4 修复 verify-image.py 的import路径
- [ ] 3.5 修复 analyze_site.py 的import路径
- [ ] 3.6 修复 auto_fixer.py 的4层parent硬编码路径
- [ ] 3.7 消除 debug_runner.py 的sys.path动态注入（cookie_manager/smart_http_client/knowledge_matcher）
- [ ] 3.8 创建 pyproject.toml（声明包元数据+依赖+入口点）
- [ ] 3.9 更新 requirements.txt（区分必选/可选依赖，补充pycryptodome）
- [ ] 3.10 为每层__init__.py声明__all__公共API
- [ ] 3.11 验证：所有脚本可从任意目录启动，无ImportError

---

## 阶段二：核心能力补全（P0-P1）

### 方向 4：JVM P1级差距修复（P1）

> **目标**：修复影响1-5%书源的差距

#### 4.1 JsExtensions委托模式改为实例化（GAP-36）

- [ ] 4.1.1 阅读真机 AnalyzeRule.kt 确认implements JsExtensions模式
- [ ] 4.1.2 修改仿真端JsExtensionsStub从委托模式改为实例化模式
- [ ] 4.1.3 验证：并发调试source/book变量正确

#### 4.2 ConcurrentRateLimiter完整限流（GAP-37）

- [ ] 4.2.1 阅读真机 AnalyzeUrl.kt 确认ConcurrentRecord限流实现
- [ ] 4.2.2 移植完整限流逻辑到仿真端
- [ ] 4.2.3 验证：限流源请求频率与真机一致

#### 4.3 SymmetricCryptoAndroid加密对齐（GAP-42）

- [ ] 4.3.1 阅读真机 JsEncodeUtils.kt 确认encryptBase64实现
- [ ] 4.3.2 移植SymmetricCryptoAndroid对齐加密
- [ ] 4.3.3 验证：加密结果与真机一致

#### 4.4 WrapFactory+instructionObserverThreshold（GAP-70a）

- [ ] 4.4.1 阅读真机 RhinoScriptEngine.kt 确认WrapFactory配置
- [ ] 4.4.2 移植WrapFactory + instructionObserverThreshold=10000
- [ ] 4.4.3 验证：JS执行行为与真机一致

#### 4.5 base64/AES flags映射完善（方向2.1）

- [ ] 4.5.1 阅读真机 JsEncodeUtils.kt 确认android.util.Base64 flags值
- [ ] 4.5.2 新建mapBase64Flags(flags)映射函数
- [ ] 4.5.3 修改base64Decode/base64DecodeToByteArray/base64Encode
- [ ] 4.5.4 修改aesDecodeArgsBase64Str等加密方法
- [ ] 4.5.5 验证：编解码结果与android.util.Base64一致

#### 4.6 其他中难度方法修复（方向2.2）

- [ ] 4.6.1 downloadFile：改用OkHttp流式下载+修正路径计算
- [ ] 4.6.2 toNumChapter：移植AppPattern+StringUtils
- [ ] 4.6.3 log：接入Debug回调，写入日志文件
- [ ] 4.6.4 putConcurrent：实现updateConcurrentRate
- [ ] 4.6.5 executeSortUrlJs：注入source变量
- [ ] 4.6.6 evalJS：实现sharedScope（SharedJsScope）
- [ ] 4.6.7 验证：所有方法行为与真机一致

#### 4.7 方向4验证

- [ ] 4.7.1 重新构建JAR
- [ ] 4.7.2 用P1差距对应的真实源测试
- [ ] 4.7.3 验证：P1差距修复后对应源可正常调试

### 方向 5：Python客户端核心功能补全（P1）

#### 5.1 source_validator预校验模块

- [ ] 5.1.1 阅读BookSource.kt确认必填字段列表
- [ ] 5.1.2 实现BookSource必填字段校验（bookSourceName/bookSourceUrl/bookSourceType）
- [ ] 5.1.3 实现RssSource必填字段校验（sourceName/sourceUrl/type）
- [ ] 5.1.4 实现URL格式校验+模板变量校验
- [ ] 5.1.5 实现字段冲突检测
- [ ] 5.1.6 验证：用真实源测试校验结果

#### 5.2 rule_precheck规则语法预检查

- [ ] 5.2.1 阅读AnalyzeRule.kt确认规则类型前缀（@CSS:/@XPath:/@Json:等）
- [ ] 5.2.2 实现规则类型识别函数
- [ ] 5.2.3 实现CSS选择器语法校验（soupsieve）
- [ ] 5.2.4 实现XPath语法校验（lxml）
- [ ] 5.2.5 实现JSONPath语法校验（jsonpath-ng或降级为括号匹配）
- [ ] 5.2.6 实现JS规则括号匹配+关键字检查
- [ ] 5.2.7 验证：规则语法错误能被捕获

#### 5.3 debug_runner流程调整

- [ ] 5.3.1 在run()入口添加source_validator调用
- [ ] 5.3.2 在run()入口添加rule_precheck调用
- [ ] 5.3.3 预校验失败时返回DebugResult(success=False, stage="prevalidate")
- [ ] 5.3.4 实现JVM不可用时降级到Python模式
- [ ] 5.3.5 降级模式结果标注"Python降级模式，建议用JAR复验"
- [ ] 5.3.6 验证：预校验失败不调用JAR；JVM不可用时工作流不中断

#### 5.4 error_diagnoser错误类型扩充

- [ ] 5.4.1 新增12种错误类型（见design.md 4.3.2）
- [ ] 5.4.2 为每种错误类型编写修复建议模板
- [ ] 5.4.3 标记每种错误类型是否可自动修复
- [ ] 5.4.4 可自动修复的错误类型对接auto_fixer
- [ ] 5.4.5 验证：新增错误类型能被正确识别+修复建议可操作

#### 5.5 experience_manager半自动经验写入

- [ ] 5.5.1 新增extract()方法：自动提取经验要素
- [ ] 5.5.2 新增write_to_basic_memory()方法：返回MCP调用指令
- [ ] 5.5.3 实现降级路径：MCP不可用时写入references/
- [ ] 5.5.4 验证：经验写入从全手动改为半自动

#### 5.6 工具集整合

- [ ] 5.6.1 合并knowledge_matcher.py到experience_manager
- [ ] 5.6.2 合并error_translator.py到error_diagnoser
- [ ] 5.6.3 合并fetch_html.py到html_fetcher.py
- [ ] 5.6.4 验证：工具集功能不重叠、链路不中断

#### 5.7 方向5验证

- [ ] 5.7.1 验证：预校验拦截率>20%
- [ ] 5.7.2 验证：auto_fixer覆盖12种错误类型，自动修复成功率>50%
- [ ] 5.7.3 验证：经验写入半自动化
- [ ] 5.7.4 验证：工具集无功能重叠

---

## 阶段三：质量保障与全量验证（P1-P2）

### 方向 6：JVM P2级差距修复（P2）

> **目标**：修复影响<1%书源的差距

- [ ] 6.1 Rar/7z解压支持（GAP-05/06）：抽取LibArchiveUtils或Java替代库
- [ ] 6.2 evalJS注入持久化对象（GAP-56）
- [ ] 6.3 BookChapter业务方法（GAP-58）
- [ ] 6.4 userAgent默认值改为与真机一致（GAP-73）
- [ ] 6.5 高难度方法修复（方向3）：
  - [ ] 6.5.1 refreshJSLib：阅读真机JsExtensions.kt确认refreshJSLib实现，移植到JsExtensionsStub
  - [ ] 6.5.2 getLoginInfoMap：阅读真机JsExtensions.kt确认getLoginInfoMap实现，移植到JsExtensionsStub
  - [ ] 6.5.3 getHeaderMap中@js:规则支持（GAP-14）：阅读真机SourceHeaderHelper.kt确认@js:解析逻辑，移植到仿真端
  - [ ] 6.5.4 debugExplore：阅读真机BookSourceDebugger.kt确认发现阶段逻辑，移植到仿真端
  - [ ] 6.5.5 验证：高难度方法行为与真机一致
- [ ] 6.6 委托路径实现（方向4）：
  - [ ] 6.6.1 WebView渲染委托（7个方法）：确认WebViewRequiredException携带请求信息，Python Selenium/CDP可接收并渲染
  - [ ] 6.6.2 UI交互委托（7个方法）：确认startBrowser/getVerificationCode等抛出携带提示信息的异常，Python obstacle_resolver可处理
  - [ ] 6.6.3 Rar/7z解压委托（6个方法）：抽取LibArchiveUtils或引入Java替代库（junrar/7-Zip-JBinding）
  - [ ] 6.6.4 其他不可用方法（3个）：openUrl等标记为不实现，返回明确错误信息
  - [ ] 6.6.5 验证：委托路径可被Python客户端正确处理
- [ ] 6.7 验证：P2差距修复后边缘场景行为与真机一致

### 方向 7：经验知识库双写一致性核验（P1）

- [ ] 7.1 逐条核验SKILL.md 79条陷阱在references/中是否有对应详细文档
- [ ] 7.2 逐条核验SKILL.md陷阱在basic-memory中是否有对应trap笔记
- [ ] 7.3 逐条核验references/关键经验在basic-memory中是否有对应笔记
- [ ] 7.4 补写缺失条目（references/ + basic-memory）
- [ ] 7.5 验证：SKILL.md/references/basic-memory三处内容一致

### 方向 8：SKILL.md工作流更新（P1）

- [ ] 8.1 Phase2末尾添加预校验步骤描述
- [ ] 8.2 Phase3添加JVM降级到Python模式的描述
- [ ] 8.3 Phase4添加source_navigation/error_diagnoser/auto_fixer工具辅助描述
- [ ] 8.4 Phase5添加experience_manager半自动写入描述
- [ ] 8.5 更新测试脚本索引表（删除不存在的脚本引用）
- [ ] 8.6 更新JVM工具索引表（指向legado_client/对应模块）
- [ ] 8.7 验证：SKILL.md描述与实现一致

### 方向 9：全量回归测试（P0）

> **验证标准**：JAR测试通过则真机也能通过；JAR失败能准确区分源规则问题还是仿真端问题

#### 9.1 测试集准备

- [ ] 9.1.1 收集50个合法合规、真机可正常运行的书源（覆盖CSS/XPath/JSONPath/Regex/JS）
- [ ] 9.1.2 收集50个合法合规、真机可正常运行的订阅源（覆盖不同type和复杂度）
- [ ] 9.1.3 验证：100个源在真机上可正常运行

#### 9.2 全流程闭环测试

- [ ] 9.2.1 重新构建JAR（fatJar）
- [ ] 9.2.2 对100个源逐一执行"导入→测试→问题定位→优化修复→复测通过"全流程
- [ ] 9.2.3 统计兼容性达标率
- [ ] 9.2.4 分析失败源根因（区分仿真端/源规则/网站）

#### 9.3 端到端一致性验证

- [ ] 9.3.1 抽样10个JAR测试通过的源，在真机上验证
- [ ] 9.3.2 抽样5个JAR测试失败的源，在真机上验证（确认是源规则问题而非仿真端问题）
- [ ] 9.3.3 验证：JAR测试结果与真机运行效果一致

#### 9.4 经验反哺

- [ ] 9.4.1 将测试优化经验写入basic-memory（project=legado）
- [ ] 9.4.2 更新references/对应文档
- [ ] 9.4.3 更新simulation-gap-report.md
- [ ] 9.4.4 验证：经验反哺完成

---

## 任务依赖关系

```
阶段一：前置治理与基础修复（P0）
方向1（目录治理）──┐
方向2（JVM P0修复）─┤
方向3（Python import）─┘
                    │
                    ↓
阶段二：核心能力补全（P0-P1）
方向4（JVM P1修复）──┐
方向5（Python功能补全）─┘
                    │
                    ↓
阶段三：质量保障与全量验证（P1-P2）
方向6（JVM P2修复）──┐
方向7（经验双写核验）─┤
方向8（SKILL.md更新）─┤
方向9（全量回归测试）─┘
```

**关键依赖**：
- 方向2依赖方向1（文档治理后才能准确修复）
- 方向5依赖方向3（import路径修复后才能集成新模块）
- 方向8依赖方向5（SKILL.md更新需要实现完成）
- 方向9依赖方向2+4+6（JVM修复后才能全量测试）
- 方向7可在任意阶段并行执行

---

## 验收标准

### 阶段一验收

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| 目录无临时文件 | 扫描tools/__pycache__/ | 不存在 |
| SKILL.md无幽灵引用 | Grep检查引用文件是否存在 | 0个幽灵引用 |
| _INDEX.md完整 | 对比references/实际文件 | 5个缺失条目补全 |
| JVM P0差距修复 | 用P0差距对应的真实源测试 | 全部通过 |
| Python import无错误 | 从任意目录启动脚本 | 0个ImportError |

### 阶段二验收

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| JVM P1差距修复 | 用P1差距对应的真实源测试 | 全部通过 |
| 预校验拦截率 | 统计预校验失败占比 | >20% |
| auto_fixer覆盖 | 测试12种错误类型 | 全部可识别 |
| 自动修复成功率 | auto_fixer修复后通过率 | >50% |
| 经验写入半自动化 | 测试experience_manager | extract()+write_to_basic_memory()可用 |

### 阶段三验收

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| 保真度 | 四分类法评估 | ≥95% |
| 自动化率 | 100源中无需手动操作比例 | >70% |
| 端到端一致性 | 抽样真机验证 | 100% |
| 经验双写一致 | SKILL.md/references/basic-memory三处对比 | 一致 |
| SKILL.md与实现一致 | 逐项检查描述 | 一致 |

### 最终验收

| 指标 | 目标 | 验证方法 |
|------|------|---------|
| 综合保真度 | ≥95% | 四分类法 |
| 全流程自动化率 | >70% | 100源测试 |
| 端到端测试准确性 | 100% | 真机对比 |
| 自动修复成功率 | >50% | auto_fixer统计 |
| 预校验拦截率 | >20% | source_validator统计 |
| 经验双写一致性 | 100% | 三处对比 |
| SKILL.md与实现一致性 | 100% | 逐项检查 |
