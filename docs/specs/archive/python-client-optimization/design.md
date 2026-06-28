# Design: Python 客户端测试校验流程优化

> **状态**：🔄 设计中
> **创建日期**：2026-06-21

---

## Technical Approach

### 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    legado-source-creator Skill                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              debug_runner.run() 核心调试流程                 │   │
│  │                                                             │   │
│  │  1. 解析 source_obj                                         │   │
│  │  2. source_validator 校验字段完整性 ──→ 失败：返回错误       │   │
│  │  3. rule_precheck 校验规则语法 ──→ 失败：返回错误           │   │
│  │  4. experience_manager 检索历史经验                         │   │
│  │  5. RuleEngineClient 调用 JAR ──→ 失败：降级 Python 模式   │   │
│  │  6. error_diagnoser 诊断错误                                │   │
│  │     ├→ 可自动修复：auto_fixer 修复后重试（最多3次）        │   │
│  │     └→ 需用户介入：user_interaction 生成交互请求            │   │
│  │  7. confidence_evaluator 评估可信度                         │   │
│  │  8. experience_manager 输出经验草稿到 pending/              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                  │                                   │
│                    ┌─────────────┴──────────────┐                  │
│                    │                            │                  │
│              ┌─────┴─────┐              ┌────────┴────────┐         │
│              │ tools/    │              │ legado_client/  │         │
│              │ 辅助模块   │              │ 核心模块         │         │
│              │ (可选)    │              │ (必需)          │         │
│              └───────────┘              └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. source_validator 预校验模块

### 1.1 文件位置

`scripts/legado_client/analyzer/source_validator.py`

### 1.2 校验规则

#### BookSource 必填字段

| 字段 | 校验规则 | 错误级别 |
|------|---------|---------|
| bookSourceName | 非空 | ERROR |
| bookSourceUrl | 非空 + URL格式合法 | ERROR |
| bookSourceType | 0/1/2/3（文本/音频/图片/文件） | ERROR |
| searchUrl | 非空（除非 enabledExplore=true 且 searchUrl 可选） | ERROR |
| ruleSearch.bookList | 非空 | ERROR |
| ruleSearch.name | 非空 | ERROR |
| ruleSearch.author | 推荐非空 | WARN |
| ruleSearch.bookUrl | 非空 | ERROR |

#### RssSource 必填字段

| 字段 | 校验规则 | 错误级别 |
|------|---------|---------|
| sourceName | 非空 | ERROR |
| sourceUrl | 非空 + URL格式合法 | ERROR |
| sourceType | 0/1（RSS/自定义） | ERROR |
| ruleArticles | 非空 | ERROR |

#### 字段冲突检测

| 冲突 | 校验规则 | 错误级别 |
|------|---------|---------|
| searchUrl 为空但 ruleSearch 非空 | 搜索规则存在但无搜索URL | ERROR |
| loginUrl 非空但 loginUi 为空 | 登录URL存在但无登录界面配置 | WARN |
| bookSourceType=3（文件）但 ruleBookInfo 为空 | 文件类型源缺少详情规则 | WARN |

### 1.3 接口设计

```python
class SourceValidator:
    def __init__(self, source_obj: dict, source_type: str):
        self.source = source_obj
        self.source_type = source_type  # "book" or "rss"
        self.errors = []
        self.warnings = []

    def validate(self) -> dict:
        """执行全部校验，返回结果"""
        if self.source_type == "book":
            self._validate_book_source()
        else:
            self._validate_rss_source()
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }

    def _validate_book_source(self):
        """校验 BookSource 字段"""
        # 简化说明：逐字段校验 | 已知上限：不支持自定义校验规则 | 升级路径：支持插件化校验规则
        pass

    def _validate_rss_source(self):
        """校验 RssSource 字段"""
        pass
```

---

## 2. rule_precheck 规则语法预检查

### 2.1 文件位置

`scripts/legado_client/analyzer/rule_precheck.py`

### 2.2 规则类型识别

Legado 规则支持5种解析方式，通过前缀识别：

| 前缀 | 类型 | Python 校验库 |
|------|------|--------------|
| `@CSS:` | CSS 选择器 | soupsieve（已安装） |
| `@XPath:` | XPath | lxml（已安装） |
| `@json:` | JSONPath | jsonpath-ng（需安装） |
| `<js>` / `@js:` | JavaScript | 括号匹配 + 关键字检查（不执行） |
| `<regex>` | 正则表达式 | re（标准库） |
| 无前缀 | 默认 CSS（jsoup 语法） | soupsieve |

### 2.3 校验逻辑

```python
class RulePrecheck:
    def __init__(self, source_obj: dict, source_type: str):
        self.source = source_obj
        self.source_type = source_type
        self.errors = []
        self.warnings = []

    def precheck(self) -> dict:
        """执行全部规则语法校验"""
        rules = self._extract_all_rules()
        for rule_path, rule_value, rule_type in rules:
            self._check_single_rule(rule_path, rule_value, rule_type)
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }

    def _extract_all_rules(self) -> list:
        """从源对象中提取所有规则字段"""
        # 简化说明：遍历 source_obj 中的 rule* 字段 | 已知上限：不支持嵌套规则 | 升级路径：支持递归提取
        pass

    def _check_single_rule(self, rule_path: str, rule_value: str, rule_type: str):
        """校验单个规则的语法"""
        # 简化说明：按规则类型分发到对应校验器 | 已知上限：JS只做语法检查不执行 | 升级路径：接入Rhino做JS语法校验
        pass
```

### 2.4 规则提取范围

#### BookSource 规则字段

```
ruleSearch.bookList / ruleSearch.name / ruleSearch.author / ruleSearch.bookUrl
ruleBookInfo.init / ruleBookInfo.name / ruleBookInfo.author / ruleBookInfo.intro
ruleBookInfo.tocUrl / ruleBookInfo.coverUrl / ruleBookInfo.kind / ruleBookInfo.lastChapter
ruleToc.chapterList / ruleToc.chapterName / ruleToc.chapterUrl / ruleToc.nextTocUrl
ruleContent.content / ruleContent.nextContentUrl / ruleContent.replaceRegex
```

#### RssSource 规则字段

```
ruleArticles / ruleTitle / ruleLink / ruleImage / ruleDescription / ruleContent
```

---

## 3. debug_runner 流程调整

### 3.1 调整后的 run() 流程

```python
def run(source_path: str, key: str = None, **kwargs) -> DebugResult:
    """核心调试流程入口"""
    # 1. 解析 source_obj
    source_obj = _load_source(source_path)
    source_type = _detect_source_type(source_obj)

    # 2. 预校验：字段完整性（新增）
    validator = SourceValidator(source_obj, source_type)
    result = validator.validate()
    if not result["valid"]:
        return DebugResult(success=False, stage="prevalidate",
                          errors=result["errors"], warnings=result["warnings"])

    # 3. 预校验：规则语法（新增）
    prechecker = RulePrecheck(source_obj, source_type)
    result = prechecker.precheck()
    if not result["valid"]:
        return DebugResult(success=False, stage="precheck",
                          errors=result["errors"], warnings=result["warnings"])

    # 4. 检索历史经验
    experience = experience_manager.search(source_obj, source_type)

    # 5. 调用 JAR 执行调试
    try:
        jar_result = rule_engine_client.debug(source_obj, key)
    except JARUnavailableError:
        # 降级到 Python 模式
        jar_result = _python_fallback_debug(source_obj, key)
        jar_result.degraded = True

    # 6. 错误诊断 + 自动修复
    if not jar_result.success:
        diagnosis = error_diagnoser.diagnose(jar_result.error, source_obj, source_type)
        if diagnosis.auto_fixable:
            for attempt in range(3):
                fixed_source = auto_fixer.fix(source_obj, diagnosis)
                jar_result = rule_engine_client.debug(fixed_source, key)
                if jar_result.success:
                    break
                diagnosis = error_diagnoser.diagnose(jar_result.error, fixed_source, source_type)
        elif diagnosis.need_user:
            interaction = user_interaction.create_request(diagnosis)
            return DebugResult(success=False, stage="debug",
                              need_user=True, interaction=interaction)

    # 7. 可信度评估
    confidence = confidence_evaluator.evaluate(jar_result, source_type)

    # 8. 经验输出
    experience_manager.output_draft(source_obj, source_type, jar_result, confidence)

    return DebugResult(
        success=jar_result.success,
        stage="complete",
        confidence=confidence,
        degraded=jar_result.degraded
    )
```

### 3.2 降级路径

当 JAR 不可用时，降级到 Python 模式：

| 阶段 | JAR 模式 | Python 降级模式 |
|------|---------|----------------|
| 搜索 | RuleEngineClient → JAR | requests + BeautifulSoup4 |
| 详情 | RuleEngineClient → JAR | requests + BeautifulSoup4 |
| 目录 | RuleEngineClient → JAR | 不支持（返回中可信度） |
| 正文 | RuleEngineClient → JAR | 不支持（返回中可信度） |

**降级限制**：
- Python 降级模式只支持搜索和详情阶段
- 不支持 JS 规则执行（Rhino 引擎在 JAR 中）
- 不支持加密解密（hutool 在 JAR 中）
- 结果标注"Python 降级模式，建议用 JAR 复验"

---

## 4. error_diagnoser 错误类型扩充

### 4.1 错误类型分类

| 类别 | 错误类型 | 识别方式 | 修复建议 |
|------|---------|---------|---------|
| **预校验** | 字段缺失 | source_validator 输出 | 补充缺失字段 |
| **预校验** | 规则语法错误 | rule_precheck 输出 | 修正规则语法 |
| **JAR通信** | JAR进程崩溃 | ConnectionRefusedError | 检查JAR是否启动 |
| **JAR通信** | JAR超时 | TimeoutError | 检查网络或增加超时 |
| **JAR通信** | 端口占用 | OSError | 检查端口占用情况 |
| **规则执行** | CSS选择器未匹配 | JAR返回空结果 | 重新分析网站HTML结构 |
| **规则执行** | XPath未匹配 | JAR返回空结果 | 重新分析网站HTML结构 |
| **规则执行** | JS执行错误 | JAR返回JS异常 | 检查JS语法和变量 |
| **规则执行** | 加密解密失败 | JAR返回解密错误 | 检查加密参数和密钥 |
| **网络** | HTTP 403 | JAR返回403 | 网站反爬，需添加Header |
| **网络** | HTTP 404 | JAR返回404 | URL错误或网站改版 |
| **网络** | SSL证书错误 | JAR返回SSL异常 | 网站证书问题 |
| **网站** | 需要登录 | JAR返回登录页面 | 需要用户提供登录信息 |
| **网站** | CF防护 | JAR返回CF挑战页面 | 需要用户破盾或使用cloudscraper |
| **网站** | 验证码 | JAR返回验证码页面 | 需要用户输入验证码 |
| **仿真端** | 行为不一致 | 对比真机结果 | 检查simulation-gap-report.md |

### 4.2 修复建议生成

每种错误类型对应修复建议模板：

```python
REPAIR_TEMPLATES = {
    "css_selector_empty": {
        "description": "CSS选择器未匹配到任何元素",
        "possible_causes": [
            "选择器语法错误",
            "网站HTML结构已变化",
            "页面需要JS渲染"
        ],
        "repair_methods": [
            "用浏览器F12检查页面HTML结构",
            "重新编写CSS选择器",
            "如果是SPA页面，需要WebView渲染"
        ],
        "auto_fixable": True,
        "auto_fix_method": "auto_fixer.rewrite_css_selector"
    },
    # ... 其他错误类型
}
```

---

## 5. experience_manager 半自动经验写入

### 5.1 经验要素自动提取

测试完成后，experience_manager 自动从调试结果中提取以下经验要素：

| 要素 | 提取来源 | 示例 |
|------|---------|------|
| 网站特征 | source_obj + URL | "使用Nuxt.js SSR框架" |
| 错误类型 | error_diagnoser 输出 | "CSS选择器未匹配" |
| 修复方法 | auto_fixer 输出 | "改用首页URL替代/?page=路径" |
| 规则模式 | source_obj 中的规则 | "@CSS:.article-list .item" |
| 网站类型 | parse_strategy 输出 | "HTML静态网站" |
| 可信度 | confidence_evaluator 输出 | 0.92（高可信） |

### 5.2 经验草稿格式

```json
{
  "website_features": {
    "url": "https://example.com",
    "framework": "Nuxt.js",
    "anti_crawl": "CF Challenge",
    "encoding": "UTF-8"
  },
  "error_pattern": {
    "type": "css_selector_empty",
    "stage": "search",
    "selector": ".old-class"
  },
  "repair_method": {
    "method": "rewrite_css_selector",
    "new_selector": ".new-class",
    "reason": "网站改版，class名变化"
  },
  "rule_pattern": {
    "search_url": "https://example.com/search?q={{key}}",
    "rule_search_name": "@CSS:.new-class .title"
  },
  "confidence": 0.92,
  "timestamp": "2026-06-21T10:30:00",
  "status": "pending"
}
```

### 5.3 半自动写入流程

```
测试完成
  ├→ 1. experience_manager.extract() 提取经验要素
  ├→ 2. 生成 JSON 草稿到 experience/pending/
  ├→ 3. AI 审核草稿（可选，默认跳过）
  │    └→ 审核不通过：标记为 rejected，不写入
  ├→ 4. 审核通过（或跳过审核）
  │    ├→ 4a. 写入 basic-memory（通过 MCP search_notes/write_note）
  │    └→ 4b. 写入 references/（通过文件写入，降级路径）
  └→ 5. conflict_resolver 检查冲突
       └→ 有冲突：按置信度+时效性+覆盖度评分选优
```

---

## 6. 5 阶段工作流调整

### 6.1 Phase 2 预校验（新增）

在 Phase 2（构建规则）完成后，立即执行预校验：

```
Phase 2: 构建规则
  ├→ 知识库查阅
  ├→ 分析网站类型
  ├→ 构建搜索/详情/目录/正文规则
  ├→ 处理特殊场景
  └→ 【新增】预校验
       ├→ source_validator 校验字段完整性
       └→ rule_precheck 校验规则语法
            └→ 失败：返回 Phase 2 重新构建
```

### 6.2 Phase 3 降级路径（优化）

```
Phase 3: 测试驱动
  ├→ 静态陷阱扫描
  ├→ 运行测试脚本
  │    ├→ JVM优先（RuleEngineClient → JAR）
  │    └→ 【优化】JVM不可用时降级到 Python 模式
  │         ├→ requests + BeautifulSoup4 执行简化调试
  │         └→ 标注"Python降级模式，建议用JAR复验"
  ├→ 错误诊断
  │    ├→ 【优化】扩充错误类型（预校验/JAR通信/仿真端差异）
  │    └→ 可自动修复：auto_fixer 修复后重试（最多3次）
  └→ 可信度分层
       ├→ 高可信：JAR通过
       ├→ 中可信：JAR失败但Python降级通过
       └→ 需真机：JAR和Python都失败
```

### 6.3 Phase 4 工具辅助（优化）

```
Phase 4: 源码深挖（测试失败时）
  ├→ 【优化】source_navigation 自动导航到源码位置
  │    └→ 错误类型 → 源码文件和行号映射
  ├→ 【优化】error_diagnoser 提供修复建议
  │    └→ 不再需要AI手动查阅源码
  ├→ 【优化】auto_fixer 自动修复常见错误
  │    └→ CSS选择器重写 / URL修正 / 规则语法修正
  └→ 回到 Phase 3 重测
```

### 6.4 Phase 5 半自动经验写入（优化）

```
Phase 5: 经验反哺 + 代码进化
  ├→ 回顾新问题
  ├→ 验证（每条经验必须去源码核实）
  ├→ 【优化】文档反哺（半自动）
  │    ├→ experience_manager 自动提取经验要素
  │    ├→ 生成草稿到 pending/
  │    ├→ AI 审核（可选）
  │    └→ 写入 basic-memory / references/
  └→ 代码进化
       └→ Phase 3/4 识别仿真端差异 → 更新 simulation-gap-report.md
```

---

## Data Flow

```
用户输入网站URL
  ↓
AI 使用 Skill 生成 BookSource/RssSource JSON
  ↓
Phase 2: 构建规则 + 预校验（source_validator + rule_precheck）
  ↓ 预校验通过
Phase 3: 测试驱动（JAR优先，降级Python）
  ↓ JAR调试
  ├→ 成功：confidence_evaluator 评估可信度
  └→ 失败：error_diagnoser 诊断
       ├→ 可自动修复：auto_fixer 修复 → 重试（最多3次）
       └→ 需用户介入：user_interaction 生成交互请求
  ↓
Phase 5: 经验反哺（半自动写入 basic-memory）
  ↓
输出最终源 + 测试报告 + 经验草稿
```

---

## File Changes

### 新增文件

| 文件 | 功能 |
|------|------|
| `scripts/legado_client/analyzer/source_validator.py` | 源字段完整性预校验 |
| `scripts/legado_client/analyzer/rule_precheck.py` | 规则语法预检查 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `scripts/legado_client/client/debug_runner.py` | run() 入口添加预校验步骤 + 降级路径优化 |
| `scripts/legado_client/analyzer/error_diagnoser.py` | 扩充错误类型 + 对接 auto_fixer |
| `scripts/legado_client/experience/experience_manager.py` | 半自动经验写入 + 草稿生成 |
| `.trae/skills/legado-source-creator/SKILL.md` | 5阶段工作流调整（Phase 2预校验 + Phase 3降级 + Phase 4工具 + Phase 5半自动） |

---

## Architecture Decisions

### AD-01: 预校验用 Python 而非 JAR

**决策**：预校验（source_validator + rule_precheck）用 Python 实现，不调用 JAR。

**理由**：
1. 预校验是纯语法检查，不需要执行规则引擎
2. Python 启动快（< 1秒），JAR 启动慢（3-5秒）
3. 预校验失败时不需要 JAR 的错误诊断能力
4. 减少 JAR 调用次数，降低 JAR 进程管理开销

### AD-02: 规则语法校验不执行 JS

**决策**：rule_precheck 对 JS 规则只做语法检查（括号匹配 + 关键字检查），不执行 JS。

**理由**：
1. JS 执行需要 Rhino 引擎（在 JAR 中），Python 端无法执行
2. 语法检查能拦截 80% 的 JS 规则错误（括号不匹配、关键字拼写错误）
3. 剩余 20% 的运行时错误由 JAR 调试阶段捕获
4. 避免在 Python 端引入 Rhino 依赖

### AD-03: 降级模式只支持搜索和详情

**决策**：Python 降级模式只支持搜索和详情阶段，不支持目录和正文。

**理由**：
1. 搜索和详情是单次 HTTP 请求 + 解析，Python 可用 requests + BeautifulSoup4 实现
2. 目录和正文涉及分页、JS 执行、加密解密，Python 端无法完整实现
3. 降级模式的目的是"快速验证源是否可用"，不是"完整调试"
4. 降级模式结果标注"建议用 JAR 复验"

### AD-04: 经验草稿默认跳过 AI 审核

**决策**：经验草稿默认跳过 AI 审核，直接写入 basic-memory。

**理由**：
1. AI 审核增加流程耗时，且大部分经验草稿是准确的
2. 经验冲突由 conflict_resolver 自动解决
3. 错误经验会被时效性降级（6个月未命中自动降级）
4. 如需审核，AI 可在 Phase 5 手动触发

### AD-05: tools/ 模块通过 degradation_chain 间接调用

**决策**：tools/ 中的模块（auto_fixer、obstacle_resolver 等）不直接被 CLI 入口调用，必须通过 legado_client/ 中的 degradation_chain 间接调用。

**理由**：
1. tools/ 是可选辅助模块，不应成为核心流程的直接依赖
2. degradation_chain 提供统一的降级路径管理（auto_solve → cookie_import → manual_guide → mark_unverifiable）
3. 避免 CLI 入口直接依赖 tools/，保持核心流程的独立性
4. tools/ 模块缺失时，degradation_chain 可降级到下一方案

---

## Risk Assessment

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| soupsieve 不支持 jsoup 扩展语法 | 中 | 中 | 预校验只检查标准 CSS 语法，jsoup 扩展语法由 JAR 调试捕获 |
| jsonpath-ng 未安装 | 低 | 低 | rule_precheck 对 JSONPath 规则降级为括号匹配检查 |
| 预校验误报（合法规则被标记为错误） | 中 | 高 | 预校验只检查明确错误的语法，对模糊语法只发 WARN |
| auto_fixer 修复成功率低 | 中 | 中 | 修复失败后降级到用户交互，不阻塞流程 |
| experience_manager 草稿质量差 | 低 | 中 | conflict_resolver 自动解决冲突 + 时效性降级 |
| 降级模式结果不准确 | 中 | 高 | 降级模式结果标注"建议用 JAR 复验" |
