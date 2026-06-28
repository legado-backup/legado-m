# Tasks: Python 客户端测试校验流程优化

> **格式说明**：`- [ ] X.Y` 未完成 / `- [x] X.Y ✅ YYYY-MM-DD` 已完成
> **创建日期**：2026-06-21

---

## 方向 1：source_validator 预校验模块（新建）

> **目标**：新建源字段完整性预校验模块
> **源码依据**：`BookSource.kt` / `RssSource.kt` 字段定义

### 1.1 BookSource 字段校验

- [ ] 1.1.1 阅读 `BookSource.kt` 确认必填字段列表
- [ ] 1.1.2 实现 BookSource 必填字段校验（bookSourceName/bookSourceUrl/bookSourceType/searchUrl/ruleSearch）
- [ ] 1.1.3 实现 BookSource 推荐字段校验（bookSourceGroup/bookSourceComment/loginUrl/loginUi）
- [ ] 1.1.4 实现 BookSource 字段冲突检测（searchUrl为空但ruleSearch非空等）
- [ ] 1.1.5 验证：用真实 BookSource 测试校验结果

### 1.2 RssSource 字段校验

- [ ] 1.2.1 阅读 `RssSource.kt` 确认必填字段列表
- [ ] 1.2.2 实现 RssSource 必填字段校验（sourceName/sourceUrl/sourceType/ruleArticles）
- [ ] 1.2.3 实现 RssSource 字段冲突检测
- [ ] 1.2.4 验证：用真实 RssSource 测试校验结果

### 1.3 URL 格式校验

- [ ] 1.3.1 实现 URL 格式校验（协议+域名合法性）
- [ ] 1.3.2 实现 URL 模板变量校验（{{key}}/{{page}} 等变量合法性）
- [ ] 1.3.3 验证：URL 格式校验准确

---

## 方向 2：rule_precheck 规则语法预检查（新建）

> **目标**：新建规则语法预检查模块
> **源码依据**：`AnalyzeRule.kt` 规则类型识别逻辑

### 2.1 规则类型识别

- [ ] 2.1.1 阅读 `AnalyzeRule.kt` 确认5种规则类型前缀（@CSS:/@XPath:/@json:/<js>/@js:/<regex>）
- [ ] 2.1.2 实现规则类型识别函数（从规则字符串中识别类型）
- [ ] 2.1.3 验证：5种规则类型正确识别

### 2.2 CSS 选择器语法校验

- [ ] 2.2.1 用 soupsieve 校验 `@CSS:` 前缀规则语法
- [ ] 2.2.2 处理 jsoup 扩展语法（降级为 WARN，不报 ERROR）
- [ ] 2.2.3 验证：CSS 选择器语法错误能被捕获

### 2.3 XPath 语法校验

- [ ] 2.3.1 用 lxml 校验 `@XPath:` 前缀规则语法
- [ ] 2.3.2 验证：XPath 语法错误能被捕获

### 2.4 JSONPath 语法校验

- [ ] 2.4.1 检查 jsonpath-ng 是否已安装，未安装则降级为括号匹配检查
- [ ] 2.4.2 用 jsonpath-ng 校验 `@json:` 前缀规则语法
- [ ] 2.4.3 验证：JSONPath 语法错误能被捕获

### 2.5 JS 规则语法检查

- [ ] 2.5.1 实现 JS 规则括号匹配检查（()/{}/[]）
- [ ] 2.5.2 实现 JS 关键字检查（function/return/var/let/const 等）
- [ ] 2.5.3 验证：JS 语法错误能被捕获（不执行 JS）

### 2.6 正则语法校验

- [ ] 2.6.1 用 re 模块校验 `<regex>` 包裹的规则语法
- [ ] 2.6.2 验证：正则语法错误能被捕获

### 2.7 规则提取

- [ ] 2.7.1 实现 BookSource 规则字段提取（ruleSearch/ruleBookInfo/ruleToc/ruleContent）
- [ ] 2.7.2 实现 RssSource 规则字段提取（ruleArticles/ruleTitle/ruleLink/ruleImage/ruleContent）
- [ ] 2.7.3 验证：所有规则字段被正确提取

---

## 方向 3：debug_runner 流程调整（修改）

> **目标**：在 debug_runner.run() 入口添加预校验步骤
> **源码依据**：现有 `debug_runner.py`

### 3.1 集成预校验

- [ ] 3.1.1 在 run() 入口添加 source_validator 调用
- [ ] 3.1.2 在 run() 入口添加 rule_precheck 调用
- [ ] 3.1.3 预校验失败时返回 DebugResult(success=False, stage="prevalidate"/"precheck")
- [ ] 3.1.4 验证：预校验失败时不调用 JAR

### 3.2 降级路径优化

- [ ] 3.2.1 实现 JAR 不可用时降级到 Python 模式（requests + BeautifulSoup4）
- [ ] 3.2.2 降级模式只支持搜索和详情阶段
- [ ] 3.2.3 降级模式结果标注"Python降级模式，建议用JAR复验"
- [ ] 3.2.4 验证：降级路径正常工作

### 3.3 错误诊断闭环

- [ ] 3.3.1 JAR 失败时调用 error_diagnoser 诊断
- [ ] 3.3.2 可自动修复时调用 auto_fixer 修复后重试（最多3次）
- [ ] 3.3.3 需用户介入时调用 user_interaction 生成交互请求
- [ ] 3.3.4 验证：错误诊断闭环正常工作

---

## 方向 4：error_diagnoser 错误类型扩充（修改）

> **目标**：扩充错误类型识别能力
> **源码依据**：现有 `error_diagnoser.py`

### 4.1 新增错误类型

- [ ] 4.1.1 新增预校验错误类型（字段缺失/规则语法错误）
- [ ] 4.1.2 新增 JAR 通信错误类型（进程崩溃/超时/端口占用）
- [ ] 4.1.3 新增仿真端差异错误类型（行为不一致）
- [ ] 4.1.4 新增网站结构变化错误类型（选择器返回空但HTML已变化）
- [ ] 4.1.5 验证：新增错误类型能被正确识别

### 4.2 修复建议模板

- [ ] 4.2.1 为每种错误类型编写修复建议模板
- [ ] 4.2.2 修复建议包含：错误描述/可能原因/修复方法/参考文档链接
- [ ] 4.2.3 验证：修复建议清晰可操作

### 4.3 对接 auto_fixer

- [ ] 4.3.1 标记每种错误类型是否可自动修复
- [ ] 4.3.2 可自动修复的错误类型对接 auto_fixer 修复方法
- [ ] 4.3.3 验证：auto_fixer 能根据错误类型选择修复方法

---

## 方向 5：experience_manager 半自动经验写入（修改）

> **目标**：优化经验写入流程，从手动改为半自动
> **源码依据**：现有 `experience_manager.py`

### 5.1 经验要素自动提取

- [ ] 5.1.1 实现网站特征提取（URL/框架/反爬/编码）
- [ ] 5.1.2 实现错误模式提取（类型/阶段/选择器）
- [ ] 5.1.3 实现修复方法提取（方法/新选择器/原因）
- [ ] 5.1.4 实现规则模式提取（searchUrl/rule*字段）
- [ ] 5.1.5 验证：经验要素被正确提取

### 5.2 经验草稿生成

- [ ] 5.2.1 实现经验草稿 JSON 格式生成
- [ ] 5.2.2 草稿写入 experience/pending/ 目录
- [ ] 5.2.3 验证：草稿格式正确

### 5.3 半自动写入流程

- [ ] 5.3.1 实现 AI 审核接口（可选，默认跳过）
- [ ] 5.3.2 实现写入 basic-memory（通过 MCP）
- [ ] 5.3.3 实现写入 references/（降级路径，通过文件写入）
- [ ] 5.3.4 实现 conflict_resolver 冲突检测和解决
- [ ] 5.3.5 验证：半自动写入流程正常工作

---

## 方向 6：SKILL.md 5 阶段工作流调整（修改）

> **目标**：更新 SKILL.md 中的 5 阶段工作流描述
> **源码依据**：现有 `SKILL.md`

### 6.1 Phase 2 预校验

- [ ] 6.1.1 在 Phase 2 末尾添加预校验步骤描述
- [ ] 6.1.2 添加 source_validator + rule_precheck 调用说明
- [ ] 6.1.3 预校验失败时返回 Phase 2 重新构建的流程描述
- [ ] 6.1.4 验证：Phase 2 描述与实现一致

### 6.2 Phase 3 降级路径

- [ ] 6.2.1 添加 JVM 不可用时降级到 Python 模式的描述
- [ ] 6.2.2 添加降级模式限制说明（只支持搜索和详情）
- [ ] 6.2.3 添加降级模式结果标注说明
- [ ] 6.2.4 验证：Phase 3 降级路径描述与实现一致

### 6.3 Phase 4 工具辅助

- [ ] 6.3.1 添加 source_navigation 自动导航描述
- [ ] 6.3.2 添加 error_diagnoser 修复建议描述
- [ ] 6.3.3 添加 auto_fixer 自动修复描述
- [ ] 6.3.4 验证：Phase 4 工具辅助描述与实现一致

### 6.4 Phase 5 半自动经验写入

- [ ] 6.4.1 添加 experience_manager 半自动写入描述
- [ ] 6.4.2 添加经验草稿生成和审核流程描述
- [ ] 6.4.3 添加 conflict_resolver 冲突解决描述
- [ ] 6.4.4 验证：Phase 5 半自动经验写入描述与实现一致

---

## 任务依赖关系

```
方向 1（source_validator）──┐
方向 2（rule_precheck）─────┤
                           ├──→ 方向 3（debug_runner 集成）
                           │         │
方向 4（error_diagnoser）───┤         │
方向 5（experience_manager）─┤         │
                           │         │
                           ├──→ 方向 6（SKILL.md 更新）
```

**关键依赖**：
- 方向 3 依赖方向 1 + 2（预校验模块必须先实现）
- 方向 3 依赖方向 4（错误诊断闭环需要 error_diagnoser 扩充）
- 方向 3 依赖方向 5（经验写入需要 experience_manager 优化）
- 方向 6 依赖方向 1-5 全部完成（SKILL.md 描述需要与实现一致）

---

## 验收标准

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| source_validator 预校验 | 用真实源测试字段校验 | ✅ 字段缺失/冲突能被捕获 |
| rule_precheck 规则语法校验 | 用真实源测试规则语法校验 | ✅ 5种规则类型语法错误能被捕获 |
| debug_runner 预校验集成 | 预校验失败时不调用 JAR | ✅ 预校验 < 3秒 |
| debug_runner 降级路径 | JAR 不可用时降级到 Python 模式 | ✅ 搜索和详情可执行 |
| error_diagnoser 错误类型扩充 | 新增错误类型能被识别 | ✅ 16种错误类型覆盖 |
| error_diagnoser 修复建议 | 每种错误类型有修复建议 | ✅ 修复建议清晰可操作 |
| experience_manager 半自动写入 | 测试后自动生成经验草稿 | ✅ 草稿格式正确 |
| experience_manager 冲突解决 | 同一网站多条经验按评分选优 | ✅ 冲突自动解决 |
| SKILL.md 5阶段工作流 | Phase 2-5 描述与实现一致 | ✅ 文档与代码一致 |
| **自动化率** | **100个真实源测试** | **> 70% 无需手动操作** |
| **预校验拦截率** | **预校验失败的源占比** | **> 20% 无效JAR调用被拦截** |
| **自动修复成功率** | **auto_fixer 修复后通过率** | **> 50%** |
