# 测试规格：rss-concurrency-and-checksource-optimization 真机测试

## Intent

验证 `rss-concurrency-and-checksource-optimization` 的所有变更功能项（24项）在真实设备上按预期工作，发现设计文档中未发现的问题，并将测试经验沉淀到 ai_tests/docs/。

## Scope

### 包含

- **第一批（并发配置化）**：rssParseConcurrency + imageLoadConcurrency 的UI显示、修改生效、SharedPreferences 持久化
- **第二批（书源域名校验优化）**：domainCheckMode RadioGroup 交互（勾选"域名"CheckBox才显示）、Socket/AnalyzeUrl 双模式切换
- **第三批（订阅源校验+去重）**：CheckRssSourceService 启动、5维度校验执行、去重逻辑
- **第四批（权重算法回填）**：SourceWeightCalculator 计算结果、weight 字段回填到数据库
- **可能影响的功能**：书源/订阅源管理菜单、BookSourceSort.Weight 排序、RssParserByRule 解析并发、Glide 图片加载并发
- **深度日志分析**：logcat 抓取 CheckSourceService/CheckRssSourceService/SourceWeightCalculator 相关日志
- **经验沉淀**：测试中的 bug 修复和测试方法论沉淀到 ai_tests/docs/feature_test_lessons.md

### 不包含

- 不重复已 PASS 的测试1/2（并发配置项显示已验证）
- 不重复导入书源（用户已导入真实书源到模拟器）
- 不测试与本次优化无关的既有功能

## Approach

### Selected Approach

**分层真机测试方案**：6个测试场景，从UI层→Service层→数据层逐层深入，每个场景配合 logcat 日志深度分析。

**理由**：
1. UI层验证配置项显示和交互（快速发现问题）
2. Service层验证校验执行和Service启动（核心功能）
3. 数据层验证 weight 回填（最终结果确认）
4. logcat 日志分析补充运行时行为确认（深度验证）

### Alternatives Considered

| 方案 | 优点 | 缺点 | 否决理由 |
|------|------|------|---------|
| 纯UI自动化测试 | 快速、可视化 | 无法验证Service层和数据层 | 覆盖度不足 |
| 纯logcat日志分析 | 深度运行时行为 | 无法验证UI交互 | 缺少用户视角 |
| 纯数据库查询验证 | 直接验证结果 | 无法定位问题根因 | 缺少过程验证 |
| **分层综合测试（选定）** | UI+Service+数据+日志全覆盖 | 测试时间较长 | 覆盖度最完整，符合用户"真真正正测试"要求 |

### Drawbacks

- **测试时间较长**：6个场景+日志分析，预计需要20-30分钟
- **依赖真实数据**：需要用户已导入真实书源（已满足）
- **UI自动化可能不稳定**：uiautomator2 在某些场景可能超时，需要重试机制

### Prior Art

- `ai_tests/scripts/verify_all_features.py` v3 已验证了测试1/2 PASS，但测试3 FAIL（domainCheckMode需勾选域名）、测试4-6 SKIP（无真实数据）
- `ai_tests/scripts/import_rss_source.py` 提供了 pull/push DB + WAL 模式处理逻辑
- `ai_tests/docs/fixed_test_workflow.md` 定义了固定测试流程SOP

## Requirements

### REQ-1: 并发配置UI验证（已PASS，补充验证修改生效）
- REQ-1.1: "其他设置"页面显示 "RSS parse concurrency" 和 "Image load concurrency" 配置项
- REQ-1.2: 点击配置项弹出 NumberPickerDialog，可修改值
- REQ-1.3: 修改后 SharedPreferences 中 rssParseConcurrency/imageLoadConcurrency 值更新

### REQ-2: domainCheckMode 交互验证（修复测试3 FAIL）
- REQ-2.1: "校验设置"对话框显示 6个校验项目CheckBox（域名/搜索/发现/详情/目录/正文）
- REQ-2.2: **勾选"域名"CheckBox后，domain_check_mode_group RadioGroup 变为可见**
- REQ-2.3: RadioGroup 包含 "Socket quick check" 和 "Analyze rule real request" 两个 RadioButton
- REQ-2.4: 切换 RadioButton 后点击"确认"保存 domainCheckMode 配置

### REQ-3: 书源校验执行验证（用真实书源数据）
- REQ-3.1: 书源管理列表有真实书源数据（用户已导入）
- REQ-3.2: 长按进入选择模式后，菜单显示"校验"项
- REQ-3.3: 点击"校验"后 CheckSourceService 启动（logcat 验证）
- REQ-3.4: 校验执行无崩溃（AndroidRuntime:E 无 FATAL）
- REQ-3.5: 校验完成后 weight 字段回填到 book_sources 表

### REQ-4: 订阅源校验执行验证（用真实订阅源数据）
- REQ-4.1: 订阅源管理列表有真实订阅源数据（用户已导入或导入默认）
- REQ-4.2: 长按进入选择模式后，菜单显示"校验"项
- REQ-4.3: 点击"校验"后 CheckRssSourceService 启动（logcat 验证，关键验证点）
- REQ-4.4: 校验执行无崩溃（AndroidRuntime:E 无 FATAL）
- REQ-4.5: 校验完成后 weight 字段回填到 rss_sources 表

### REQ-5: 深度日志分析
- REQ-5.1: logcat 含 CheckSourceService 启动日志
- REQ-5.2: logcat 含 CheckRssSourceService 启动日志（关键，之前未验证）
- REQ-5.3: logcat 含 SourceWeightCalculator 计算日志
- REQ-5.4: logcat 含 weight 回填日志

### REQ-6: 数据库 weight 字段验证
- REQ-6.1: pull legado.db 到本地
- REQ-6.2: 查询 book_sources.weight 字段有非零值
- REQ-6.3: 查询 rss_sources.weight 字段有非零值

### REQ-7: 经验沉淀
- REQ-7.1: 测试 bug 修复（Python or陷阱、英文关键词、domainCheckMode需勾选域名）沉淀到 ai_tests/docs/feature_test_lessons.md
- REQ-7.2: 测试方法论沉淀（分层测试、logcat分析、DB验证）

## Scenarios

### Scenario-1: 并发配置修改生效（补充测试1）
1. 进入"其他设置"页面
2. 滚动到 "RSS parse concurrency" 配置项
3. 点击弹出 NumberPickerDialog，修改值为 8
4. 点击"确认"
5. 查询 SharedPreferences 确认 rssParseConcurrency=8

### Scenario-2: domainCheckMode 交互（修复测试3）
1. 进入"其他设置"页面
2. 滚动到"校验设置"配置项
3. 点击弹出校验设置对话框
4. **勾选"域名"CheckBox**（关键步骤，之前遗漏）
5. 确认 domain_check_mode_group RadioGroup 变为可见
6. 确认包含 "Socket quick check" 和 "Analyze rule real request" 两个 RadioButton
7. 切换到 "Socket quick check"
8. 点击"确认"保存

### Scenario-3: 书源校验执行（真实数据）
1. 进入书源管理
2. 确认列表有真实书源数据
3. 长按第一项进入选择模式
4. 全选
5. 点击菜单"校验"项
6. 等待校验执行（最多 90 秒）
7. 分析 logcat 确认 CheckSourceService 启动
8. 确认无崩溃
9. 查询数据库 weight 字段回填

### Scenario-4: 订阅源校验执行（真实数据）
1. 进入订阅源管理
2. 确认列表有真实订阅源数据
3. 长按第一项进入选择模式
4. 全选
5. 点击菜单"校验"项
6. 等待校验执行（最多 90 秒）
7. 分析 logcat 确认 CheckRssSourceService 启动（关键验证点）
8. 确认无崩溃
9. 查询数据库 weight 字段回填

### Scenario-5: 深度日志分析
1. 抓取校验执行期间的完整 logcat
2. 过滤 CheckSourceService 相关日志
3. 过滤 CheckRssSourceService 相关日志
4. 过滤 SourceWeightCalculator 相关日志
5. 过滤 weight 回填相关日志
6. 确认所有关键日志都存在

### Scenario-6: 数据库 weight 验证
1. pull legado.db 到本地（含 WAL/SHM 处理）
2. 用 Python sqlite3 查询 book_sources.weight
3. 用 Python sqlite3 查询 rss_sources.weight
4. 确认有非零值（校验成功的源 weight > 0）
