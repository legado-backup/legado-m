# Spec: Python 客户端测试校验流程优化

> **状态**：🔄 设计中
> **创建日期**：2026-06-21

---

## Intent

优化 Python 客户端的测试校验流程，使 AI 在使用 legado-source-creator Skill 生成/优化书源和订阅源后，能够快速完成测试校验，减少对开源阅读源码的依赖。

**核心目标**：
1. 预校验前置：在 JAR 测试前用 Python 快速校验源规则语法和字段完整性，减少无效 JAR 调用
2. 错误诊断增强：JAR 失败时自动诊断错误类型并生成修复建议，AI 无需查阅源码即可修复
3. 经验闭环自动化：测试前自动检索历史经验，测试后半自动沉淀新经验
4. 用户交互最小化：需要用户介入时提供标准化指引，自动化率 > 70%

---

## Scope

### 核心范围

| 模块 | 现状 | 优化目标 |
|------|------|---------|
| **source_validator** | 不存在 | 新建：源字段完整性预校验（必填字段/推荐字段/字段格式） |
| **rule_precheck** | 不存在 | 新建：规则语法预检查（CSS/XPath/JSONPath/Regex/JS 语法） |
| **debug_runner** | 已存在 | 优化：集成预校验 + 降级路径 + 错误诊断闭环 |
| **error_diagnoser** | 已存在 | 优化：扩充错误类型 + 对接 auto_fixer 自动修复 |
| **experience_manager** | 已存在 | 优化：半自动经验写入 + 冲突解决器 |
| **双客户端整合** | tools/ + legado_client/ 并存 | 明确职责边界 + 统一调用入口 |

### 不在范围内

- JAR 仿真服务端的修复（由 simulation-fidelity-95 负责）
- Legado 源码修改（客户端只调用 JAR，不直接修改源码）
- 新增 Python 依赖（复用现有依赖，不引入新框架）

---

## Requirements

### REQ-01: source_validator 预校验模块

**需求**：新建 `scripts/legado_client/analyzer/source_validator.py`，在 JAR 测试前校验源字段完整性。

**校验内容**：
- BookSource 必填字段：bookSourceName、bookSourceUrl、bookSourceType、searchUrl、ruleSearch
- RssSource 必填字段：sourceName、sourceUrl、sourceType、ruleArticles
- 推荐字段检查：bookSourceGroup、bookSourceComment、loginUrl、loginUi
- 字段格式校验：URL 格式、规则类型（CSS/XPath/JSONPath/Regex/JS）前缀合法性
- 字段冲突检测：searchUrl 为空但 ruleSearch 非空、loginUrl 非空但 loginUi 为空

**输出格式**：
```json
{
  "valid": true/false,
  "errors": [{"field": "bookSourceUrl", "issue": "URL格式错误", "fix": "检查URL协议和域名"}],
  "warnings": [{"field": "bookSourceGroup", "issue": "未设置分组", "fix": "建议设置分组便于管理"}]
}
```

### REQ-02: rule_precheck 规则语法预检查

**需求**：新建 `scripts/legado_client/analyzer/rule_precheck.py`，在 JAR 测试前校验规则语法。

**校验内容**：
- CSS 选择器语法：`@CSS:` 前缀的规则，用 soupsieve 校验语法
- XPath 语法：`@XPath:` 前缀的规则，用 lxml 校验语法
- JSONPath 语法：`@json:` 前缀的规则，用 jsonpath-ng 校验语法
- 正则语法：`<js>` / `<regex>` 包裹的规则，用 re 校验语法
- JS 语法：`@js:` / `<js>` 前缀的规则，用简单的括号匹配 + 关键字检查（不执行 JS）
- 规则类型混合检查：同一规则串中多种类型前缀的合法性

**输出格式**：
```json
{
  "valid": true/false,
  "errors": [{"rule": "ruleSearch.name", "type": "CSS", "issue": "选择器语法错误：缺少闭合括号", "fix": "检查CSS选择器语法"}],
  "warnings": [{"rule": "ruleContent.content", "type": "JS", "issue": "JS代码较长，建议拆分为jsLib", "fix": "将公共JS函数提取到jsLib"}]
}
```

### REQ-03: debug_runner 集成预校验

**需求**：在 `debug_runner.py` 的 `run()` 入口添加预校验步骤。

**流程调整**：
```
run() 入口
  ├→ 1. 解析 source_obj（现有）
  ├→ 2. source_validator 校验字段完整性（新增）
  │    └→ 失败：返回错误，不调用 JAR
  ├→ 3. rule_precheck 校验规则语法（新增）
  │    └→ 失败：返回错误，不调用 JAR
  ├→ 4. experience_manager 检索历史经验（现有，优化为自动检索）
  ├→ 5. RuleEngineClient 调用 JAR 执行调试（现有）
  │    └→ JAR 不可用：降级到 Python 模式（现有降级路径）
  ├→ 6. error_diagnoser 诊断错误（现有，扩充错误类型）
  │    └→ 可自动修复：auto_fixer 自动修复后重试（现有，优化为循环最多3次）
  │    └→ 需用户介入：user_interaction 生成交互请求（现有）
  └→ 7. experience_manager 输出待写入经验（现有，优化为半自动写入）
```

### REQ-04: error_diagnoser 错误类型扩充

**需求**：扩充 error_diagnoser 的错误类型识别能力。

**新增错误类型**（在现有12种基础上）：
- 预校验错误：字段缺失、规则语法错误（来自 source_validator + rule_precheck）
- JAR 通信错误：JAR 进程崩溃、超时、端口占用
- 仿真端差异错误：JAR 行为与真机不一致（来自 simulation-fidelity-95 的 GAP 报告）
- 网站结构变化错误：选择器返回空但网站 HTML 结构已变化

**修复建议生成**：
- 每种错误类型对应至少1条修复建议
- 修复建议包含：错误描述、可能原因、修复方法、参考文档链接

### REQ-05: experience_manager 半自动经验写入

**需求**：优化 experience_manager 的经验写入流程，从手动写入改为半自动写入。

**半自动流程**：
1. 测试完成后，experience_manager 自动提取经验要素（网站特征、错误类型、修复方法、规则模式）
2. 生成经验 JSON 草稿，写入 `experience/pending/` 目录
3. AI 审核草稿（可选）：AI 检查经验准确性和完整性
4. 审核通过后，写入 basic-memory（通过 MCP）或 references/（通过文件写入）

**冲突解决**：
- 同一网站特征有多条经验时，用 conflict_resolver 按置信度0.5+时效性0.3+覆盖度0.2评分选优
- 过期经验（超过6个月未命中）自动降级

### REQ-06: 双客户端职责边界明确

**需求**：明确 tools/ 和 legado_client/ 的职责边界。

**职责划分**：

| 模块 | 归属 | 职责 | 调用方式 |
|------|------|------|---------|
| source_validator | legado_client/analyzer/ | 源字段完整性校验 | debug_runner 内部调用 |
| rule_precheck | legado_client/analyzer/ | 规则语法校验 | debug_runner 内部调用 |
| debug_runner | legado_client/client/ | 核心调试流程 | debug-source.py CLI 入口 |
| error_diagnoser | legado_client/analyzer/ | 错误诊断 | debug_runner 内部调用 |
| auto_fixer | tools/ | 自动修复 | debug_runner 通过 degradation_chain 调用 |
| experience_manager | legado_client/experience/ | 经验管理 | debug_runner 内部调用 |
| obstacle_resolver | tools/ | 障碍解析（登录/CF/验证码） | debug_runner 通过 degradation_chain 调用 |
| user_interaction | legado_client/client/ | 用户交互 | debug_runner 内部调用 |
| confidence_evaluator | legado_client/analyzer/ | 可信度评估 | debug_runner 内部调用 |
| source_navigation | legado_client/analyzer/ | 源码导航 | debug_runner 内部调用 |
| parse_strategy | legado_client/analyzer/ | 解析策略选择 | debug_runner 内部调用 |
| batch_runner | legado_client/client/ | 批量测试 | batch-test CLI 入口 |
| rule_engine_client | legado_client/client/ | JAR 通信 | debug_runner/batch_runner 内部调用 |
| webview_handler | legado_client/client/ | WebView 委托 | debug_runner 内部调用 |

**原则**：
- legado_client/ 是核心包，包含调试流程必需的模块
- tools/ 是辅助包，包含可选的增强模块（可通过 degradation_chain 按需调用）
- tools/ 中的模块不直接被 CLI 入口调用，必须通过 legado_client/ 间接调用

---

## Scenarios

### Scenario 1: 预校验拦截无效源

**前提**：AI 生成的 BookSource 缺少 bookSourceUrl 字段

**流程**：
1. debug_runner.run() 被调用
2. source_validator 校验字段完整性 → 发现 bookSourceUrl 为空
3. 返回错误：`{"valid": false, "errors": [{"field": "bookSourceUrl", "issue": "必填字段为空"}]}`
4. 不调用 JAR，直接返回错误

**验证**：预校验 < 1 秒，错误信息清晰可操作

### Scenario 2: 规则语法错误预检查

**前提**：AI 生成的 ruleSearch.name 规则为 `@CSS:div.class@tag.name`，CSS 语法错误

**流程**：
1. debug_runner.run() 被调用
2. source_validator 校验通过（字段完整）
3. rule_precheck 校验规则语法 → 发现 CSS 选择器语法错误
4. 返回错误：`{"valid": false, "errors": [{"rule": "ruleSearch.name", "type": "CSS", "issue": "选择器语法错误"}]}`
5. 不调用 JAR，直接返回错误

**验证**：预校验 < 2 秒，错误定位到具体规则字段

### Scenario 3: JAR 调试成功

**前提**：预校验通过，JAR 可用

**流程**：
1. debug_runner.run() 被调用
2. source_validator + rule_precheck 预校验通过
3. experience_manager 检索历史经验（命中：该网站有 CF 破盾经验）
4. RuleEngineClient 调用 JAR 执行调试 → 成功
5. confidence_evaluator 评估可信度 → 高可信
6. experience_manager 输出经验草稿到 pending/

**验证**：全流程 < 30 秒，可信度评估准确

### Scenario 4: JAR 调试失败 + 自动修复

**前提**：预校验通过，JAR 调试失败（CSS 选择器未匹配）

**流程**：
1. debug_runner.run() 被调用
2. 预校验通过
3. RuleEngineClient 调用 JAR → 失败（选择器未匹配）
4. error_diagnoser 诊断错误 → CSS 选择器未匹配
5. auto_fixer 自动修复 → 分析网站 HTML，重新生成选择器
6. 重新调用 JAR → 成功
7. experience_manager 输出经验草稿

**验证**：自动修复成功率 > 50%，修复后调试通过

### Scenario 5: JAR 不可用 + 降级到 Python 模式

**前提**：JAR 进程崩溃或端口占用

**流程**：
1. debug_runner.run() 被调用
2. 预校验通过
3. RuleEngineClient 调用 JAR → 连接失败
4. 降级到 Python 模式（使用 requests + BeautifulSoup4 执行简化调试）
5. 返回中可信度结果（标注"Python 模式，建议用 JAR 复验"）

**验证**：降级路径正常工作，结果标注清晰

### Scenario 6: 需要用户介入（登录场景）

**前提**：网站需要登录，AI 无法自动完成

**流程**：
1. debug_runner.run() 被调用
2. 预校验通过
3. RuleEngineClient 调用 JAR → 失败（需要登录）
4. error_diagnoser 诊断 → 需要登录
5. obstacle_resolver 尝试自动辅助 → 失败（验证码无法自动识别）
6. user_interaction 生成标准化交互请求
7. AI 将交互请求呈现给用户

**验证**：交互请求包含登录URL、所需信息、操作指引

### Scenario 7: 经验半自动写入

**前提**：调试成功，发现新的网站特征模式

**流程**：
1. debug_runner.run() 完成
2. experience_manager 自动提取经验要素
3. 生成经验 JSON 草稿到 `experience/pending/`
4. AI 审核草稿（可选）
5. 审核通过后写入 basic-memory

**验证**：经验草稿格式正确，basic-memory 写入成功

---

## Approach

### 策略1: 预校验前置（减少无效 JAR 调用）

在 debug_runner 入口添加 source_validator + rule_precheck，拦截字段缺失和语法错误的源，避免无效 JAR 调用。

**收益**：预计减少 20-30% 的无效 JAR 调用（字段缺失和语法错误是最常见的失败原因）

### 策略2: 错误诊断闭环（减少源码查阅）

扩充 error_diagnoser 错误类型，对接 auto_fixer 自动修复，AI 无需查阅 Legado 源码即可修复常见错误。

**收益**：预计 50% 的错误可自动修复，30% 有明确修复建议，20% 需用户介入

### 策略3: 经验半自动写入（减少手动记录）

experience_manager 自动提取经验要素，生成草稿，AI 审核后写入 basic-memory。

**收益**：经验写入从全手动改为半自动，预计节省 80% 的经验记录时间

### 策略4: 双客户端职责明确（减少混乱）

明确 tools/ 和 legado_client/ 的职责边界，tools/ 只包含可选辅助模块，legado_client/ 包含核心调试模块。

**收益**：代码结构清晰，新模块归属明确
