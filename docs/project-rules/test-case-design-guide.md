# 子规范 S14：测试用例设计指南（V3 双轨 + 源码溯源）

> **定位**：定义测试用例 MD 模板、步骤语义化、预期类型、双轨制、源码溯源字段。
> **引用关系**：本规范被 [AGENTS.md](../../AGENTS.md) "🔴🔴 强制规则：AI 自动端到端测试" 引用。
> **配套规范**：[S13 AI 自动测试工作流](./ai_e2e_testing_workflow.md)（5.5.1~5.5.8 流程）。
> **实现依据**：[ai_tests/lib/case_parser.py](../../ai_tests/lib/case_parser.py)（M3 解析器，本规范与其严格对齐）。

---

## 一、测试用例 MD 模板（七段）

每个测试用例必须包含以下七段（段标题用 `**段名**：` 格式，CaseParser SECTION_RE 匹配）：

```markdown
## TC-{模块}-{编号}：{标题}（{用例类型}）

**前置条件**：
- 条件1
- 条件2

**关联源码**：XxxActivity.kt, XxxHelper.kt
**关联 Activity**：XxxActivity（完整类名 io.legado.app.ui.xxx.XxxActivity）

**测试步骤**：
1. 步骤1（含中文动作关键词）
2. 步骤2

**预期结果**：
- ✅ 预期1（含中文预期关键词）
- ✅ 预期2
```

### 段落说明

| 段 | 必填 | CaseParser 字段 | 说明 |
|----|------|----------------|------|
| TC 头部 | ✅ | tc_id, title, case_type | `## TC-XXX：标题（类型）`，正则 `^#{2,3}\s+(TC-[A-Za-z0-9\-]+)\s*[:：]\s*(.+)` |
| 前置条件 | ✅ | prerequisites | `**前置条件**：` 或 `**前置资源**：[AI自备]/[用户必供]/[共享]` |
| **关联源码** | ✅ V3 | related_source | `**关联源码**：XxxActivity.kt`（多个逗号分隔） |
| **关联 Activity** | ✅ V3 | related_activity | `**关联 Activity**：XxxActivity`（无则填"无（纯 Service/工具类）"） |
| 测试步骤 | ✅ | steps[] | `**测试步骤**：` + `1. xxx` 数字列表 |
| 预期结果 | ✅ | expects[] | `**预期结果**：` + `- ✅ xxx` 列表 |

### 用例类型

| 类型 | 说明 |
|------|------|
| 正常用例 | 主流程验证 |
| 边界用例 | 边界值/空值/极值 |
| 异常用例 | 非法输入/异常场景 |
| 端到端用例 | 全流程集成 |
| 性能验证 | 性能指标 |

---

## 二、步骤语义化关键词（6 类原子动作）

CaseParser `_classify_action` 将步骤文本映射到 6 类原子动作。写步骤时**必须**包含下表关键词，否则默认 `assert`。

| 动作 | 中文关键词 | 说明 | 目标提取 |
|------|-----------|------|---------|
| `click` | 选择目标 / 选择 / 点击 / 按下 / tap / 打开 / 进入 / 找到 / 复制 / 触发 / 切换 / 安装 / 运行 | 点击元素 | 关键词后的内容 |
| `input` | 输入 / 填写 | 输入文本 | 引号内内容作为 value |
| `wait_element` | 等待 | 等待元素出现 | 关键词后的内容 |
| `scroll` | 滑动 / 滚动 | 滚动列表 | 关键词后的内容 |
| `back` | 返回 / press_back | 返回上一页 | — |
| `assert` | 观察 / 查看 / 验证 / （默认） | 断言验证 | 整行作为 target |

### 步骤书写规范

```markdown
**测试步骤**：
1. 进入书架页面              → action=click, target=书架页面
2. 点击"搜索"按钮            → action=click, target="搜索"按钮
3. 输入"斗破苍穹"            → action=input, value=斗破苍穹
4. 等待搜索结果列表出现       → action=wait_element, target=搜索结果列表出现
5. 滑动到列表底部            → action=scroll, target=列表底部
6. 返回书架                  → action=back
7. 验证书架显示导入的书籍     → action=assert, target=书架显示导入的书籍
```

### input 动作的 value 提取

CaseParser 从引号（`"` `'` `` ` ``）内提取 input 值：

```
输入"斗破苍穹"  → value="斗破苍穹"
填写 'user@example.com' → value="user@example.com"
```

---

## 三、预期类型枚举（8 种）

CaseParser `_classify_expect` 将预期文本映射到 8 种预期类型。**按顺序匹配**（no_crash 最优先），首个命中关键词决定类型。

| 预期类型 | 中文关键词 | 说明 |
|---------|-----------|------|
| `no_crash` | 不崩溃 / 无崩溃 / 不ANR / 无ANR / 无异常 / 不出现 | 不崩溃验证（最优先匹配） |
| `log_clean` | BUILD SUCCESSFUL / 无错误 / 无异常日志 / 日志 | 日志洁净验证 |
| `db_state` | 进度 / 保存 / 数据 | 数据库状态验证 |
| `prefs_state` | 配置 | SharedPreferences 状态验证 |
| `web_api` | API / 接口 | Web API 调用验证 |
| `page_jump` | URL / 跳转 / 打开 | 页面跳转验证 |
| `element_visible` | 显示 / 可见 / 出现 / 高亮 | 元素可见性验证 |
| `manual` | （无关键词匹配时默认） | 需 AI agent 介入判定 |

### 预期书写规范

```markdown
**预期结果**：
- ✅ 不崩溃（无 FATAL EXCEPTION）          → expect_type=no_crash
- ✅ 显示搜索结果列表                       → expect_type=element_visible
- ✅ 跳转到书籍详情页                       → expect_type=page_jump
- ✅ 阅读进度保存到数据库                   → expect_type=db_state
- ✅ 配置项已持久化                         → expect_type=prefs_state
- ✅ Web API 返回正确 JSON                  → expect_type=web_api
```

### 匹配顺序说明

`no_crash` 最优先（含"不出现"也算 no_crash）。若预期同时含"显示"和"不崩溃"，类型为 `no_crash`（先匹配）。写预期时优先把"不崩溃"类放前面。

---

## 四、V3 双轨制规则

### 4.1 A 轨 MD 用例（可读性）

- 位置：`docs/tests/*.md`（存量）或 `ai_tests/cases/{module}/case.md`（V3 新增）
- 格式：上述七段 MD 模板
- 用途：人类可读 + CaseParser 解析为结构化 TestCase

### 4.2 B 轨 Python 用例（精准性）

- 位置：`ai_tests/cases/auto/auto_{tc_id}.py`
- 命名规则：`auto_{tc_id.lower().replace('-','_')}.py`
  - 示例：`TC-F-P0-1-auto-001` → `auto_tc_f_p0_1_auto_001.py`
- TC-ID 编号：`TC-{module}-auto-{NNN}`（大写连字符）
- 文件头部：`# @tc_id: {tc_id}` 注释（M3 兜底识别）
- 生成方式：`python ai_tests/run_e2e.py --gen-test {Activity名}`
- 生成器：M9 source_test_generator（读取 Activity 源码 → 生成骨架含 TODO 标记）

### 4.3 双轨调度规则

| 情况 | 调度行为 |
|------|---------|
| 仅 MD | 执行 MD 用例（A 轨） |
| 仅 Python | 执行 Python 用例（B 轨） |
| 同 TC-ID（MD + Python） | **Python 优先**（`config.DUAL_TRACK_PYTHON_PRIORITY`） |
| Python 失败 | 降级执行 MD（`config.DUAL_TRACK_FALLBACK_TO_MD`） |

详见 [ai_tests/docs/source_test_guide.md](../../ai_tests/docs/source_test_guide.md)（M9 生成指南）。

---

## 五、V3 源码溯源字段（强制）

### 5.1 **关联源码**（强制）

格式：`**关联源码**：XxxActivity.kt, XxxHelper.kt`

- 多个文件逗号分隔
- 用源码文件名（不含完整路径）
- 纯 Service/工具类无对应 Activity 时，仍填写源码文件（如 `OkHttp.kt, ConnectionPool.kt`）

### 5.2 **关联 Activity**（强制）

格式：`**关联 Activity**：XxxActivity`

- 用 Activity 类名（如 `BookshelfActivity`）
- 完整类名格式：`io.legado.app.ui.xxx.XxxActivity`（用于 source_map.json 映射）
- **纯 Service/工具类无 Activity 时**：填 `无（纯 Service/工具类）`

### 5.3 覆盖率检查

运行 `python ai_tests/scripts/gen_module_matrix.py` 生成覆盖率报告：

- 全覆盖：所有用例含 V3 字段 → 退出码 0
- 部分覆盖：有用例缺字段 → 退出码 1，报告缺失明细
- 无用例：退出码 2

报告位置：`ai_tests/docs/module_matrix.md`

---

## 六、完整示例（3 个）

### 示例 1：正常用例（编码转换工具）

```markdown
## TC-F-P0-1-01：编码转换工具（正常用例）

**前置条件**：
- 安装新构建 APK
- 进入调试工具页面

**关联源码**：DebugToolsActivity.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入调试工具页面
2. 点击"编码转换"选项
3. 输入"hello world"
4. 点击"转换"按钮

**预期结果**：
- ✅ 显示编码转换结果
- ✅ 不崩溃
```

### 示例 2：边界用例（HTTP 工具空 URL）

```markdown
## TC-F-P0-1-02：HTTP 工具空 URL（边界用例）

**前置条件**：
- 安装新构建 APK
- 进入调试工具页面

**关联源码**：DebugToolsActivity.kt, HttpTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入调试工具页面
2. 点击"HTTP 测试"选项
3. 清空 URL 输入框
4. 点击"发送"按钮

**预期结果**：
- ✅ 不崩溃
- ✅ 显示错误提示"URL 不能为空"
- ✅ 无异常日志
```

### 示例 3：异常用例（断网场景）

```markdown
## TC-F-P0-2-01：书源搜索断网场景（异常用例）

**前置条件**：
- 安装新构建 APK
- 导入一个书源
- 断开网络（飞行模式）

**关联源码**：BookSourceActivity.kt, BookSourceAdapter.kt
**关联 Activity**：BookSourceActivity

**测试步骤**：
1. 进入书源列表
2. 点击书源的"搜索"按钮
3. 等待搜索结果（应超时失败）

**预期结果**：
- ✅ 不崩溃
- ✅ 显示网络错误提示
- ✅ 无 FATAL EXCEPTION
```

---

## 七、相关文档

| 文档 | 说明 |
|------|------|
| [S13 AI 自动测试工作流](./ai_e2e_testing_workflow.md) | 5.5.1~5.5.8 强制流程 |
| [ai_tests/docs/source_test_guide.md](../../ai_tests/docs/source_test_guide.md) | M9 B 轨 Python 用例生成 |
| [ai_tests/lib/case_parser.py](../../ai_tests/lib/case_parser.py) | M3 解析器（本规范实现依据） |
| [ai_tests/scripts/gen_module_matrix.py](../../ai_tests/scripts/gen_module_matrix.py) | 覆盖率检查 |
