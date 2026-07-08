# design.md — E2E UI 执行器加固技术设计

## Technical Approach

### 整体架构

```
run_e2e.py (编排层)
  ├─ _expand_path_steps()  [已有]
  ├─ _should_skip_after_failure()  [新增 R3]  ← 编排层跳过逻辑
  └─ 调用 UiExecutor.execute_step()
                ↓
ai_tests/lib/ui_executor.py (固化层 M4)
  ├─ click(target, scroll_search=True)  [修改 R1]  ← 加滚动查找
  │   └─ _get_element()  [修改]
  │       └─ _scroll_find()  [新增 R1]  ← 滚动 N 次找元素
  ├─ _self_heal()  [重构 R2]  ← 区分元素未找到 vs App崩溃
  │   └─ _detect_app_state()  [新增 R2]
  └─ execute_step()  [不变]  ← 跳过逻辑放编排层
```

### D1: click 滚动查找

#### 数据流

```
click(target, timeout=10, scroll_search=True)
  → _get_element(target, timeout)
    → 初次等待元素 (timeout)
    → 找到? 返回元素
    → 未找到 + scroll_search=True?
      → _scroll_find(target, max_scrolls=5)
        → for i in range(5):
          → d.swipe_ext("down", scale=0.5)
          → time.sleep(0.3)
          → d(text=target).exists(0.5) 或 d(description=target).exists(0.5)?
            → 找到? 返回元素
        → 未找到? 返回 None
    → 未找到 + scroll_search=False? 返回 None
```

#### 关键决策

**为什么放固化层而非编排层？**
- 滚动查找是 click 的通用能力，所有用例受益
- 编排层做需要改 case_parser/Step 结构，侵入性大
- 固化层做只改 click 方法签名，向后兼容（scroll_search 默认 True）

**为什么默认 5 次滚动？**
- 实测"其它设置"页面"调试工具"需滚动 4 次可见
- "我的"页面"其它设置"需滚动 1-2 次可见
- 5 次覆盖大多数 PreferenceScreen 长度
- 可通过 config.SCROLL_SEARCH_MAX 配置

**为什么不双向滚动？**
- V3 MVP 简化，假设元素在下方（大多数场景成立）
- V4 增强：先 down 找 N 次，再 up 找 N 次

### D2: 自愈区分

#### 数据流

```
步骤失败 (success=False)
  → _self_heal(step)
    → _detect_app_state()
      → app = self.d.app_current()
      → 检测: app['package'] == 'io.legado.app.debug'?
      → 检测: 'io.legado.app' in app.get('activity', '')?
    → 状态判定:
      → App 正常 → "元素未找到" → 重试（不重启）
      → App 异常/崩溃 → "App崩溃" → 重启 App
    → 重启 App:
      → self.memu.start_app()  (重启)
      → time.sleep(3)
      → self.dismiss_dialogs()  (重新关阻塞屏幕)
      → 重试当前步骤
```

#### 关键决策

**为什么完全去掉重启 atx-agent？**
- 实测 atx-agent 从不是问题根源（content-desc/路径才是）
- 重启 atx 浪费 30s + 掩盖真问题
- app_current 检测足以区分场景

**为什么 app_current 检测而非更复杂的健康检查？**
- app_current 是 u2 最轻量 API
- 能区分"App 在前台"vs"App 崩溃回桌面"
- 复杂健康检查（如检测特定 Activity）耦合度高

### D3: 失败跳过

#### 数据流（编排层）

```
run_e2e.py:
  for step in steps:
    if skip_remaining:
      result = {success: False, error: "SKIPPED (前置步骤失败)", verdict: "skip"}
      收集前置截图
      continue
    result = executor.execute_step(step, ...)
    if not result['success']:
      skip_remaining = True
      logger.warning(f"步骤 {i} 失败，后续步骤标记 SKIPPED")
```

#### 关键决策

**为什么放编排层而非固化层？**
- execute_step 是单步执行，不该感知"后续步骤"
- 编排层（run_e2e）负责步骤编排，跳过逻辑天然属于这里
- 不改固化层 execute_step 签名，向后兼容

## Architecture Decisions (ADR)

### ADR1: 滚动查找放固化层 click 方法

**Context**: click 找不到长列表元素，需滚动查找
**Decision**: 放固化层 ui_executor.click，加 scroll_search 参数
**Consequences**:
- ✅ 所有用例自动受益
- ✅ 向后兼容（默认 True，可关闭）
- ⚠️ 固化层修改需 OpenSpec 合规（本 spec 即合规文档）

### ADR2: 自愈完全去掉重启 atx-agent

**Context**: atx 从不是问题根源，重启浪费 30s + 掩盖问题
**Decision**: 移除 restart_atx_agent 调用，改用 app_current 检测
**Consequences**:
- ✅ 自愈准确（区分元素未找到 vs App崩溃）
- ✅ 节省 30s/次误重启
- ⚠️ 失去 atx-agent 真故障容错（罕见，可手动重启）

### ADR3: 失败跳过放编排层

**Context**: 步骤失败后后续在错误页面执行
**Decision**: 跳过逻辑放 run_e2e 编排层，不改 execute_step 签名
**Consequences**:
- ✅ 固化层 execute_step 保持单步职责
- ✅ 编排层控制流程清晰
- ⚠️ SKIPPED 步骤证据较少（仅前置截图）

## Data Flow

### 完整步骤执行流程（修复后）

```
run_e2e.py:
  skip_remaining = False
  for i, step in enumerate(steps):
    if skip_remaining:
      生成 SKIPPED result（仅前置截图）
      continue
    result = executor.execute_step(step, ...)
    if not result['success']:
      skip_remaining = True

ui_executor.execute_step():
  → dismiss_dialogs() (循环)
  → 前置截图+XML
  → _dispatch_action(step)
    → click(target, scroll_search=True)
      → _get_element(target)
        → 初次等待 → 找到? 返回
        → _scroll_find(target, 5)  ← R1 新增
      → el.click()
    → 失败?
      → _self_heal(step)  ← R2 重构
        → _detect_app_state()
        → 元素未找到 → 重试
        → App崩溃 → 重启 App → 重试
  → 后置截图+XML
  → 返回 result
```

## File Changes

### 修改

| 文件 | 变更 | 说明 |
|------|------|------|
| `ai_tests/lib/ui_executor.py` | click 加 scroll_search + _scroll_find；_self_heal 重构；_detect_app_state 新增 | 固化层 M4 |
| `ai_tests/config.py` | 加 SCROLL_SEARCH_MAX=5, SCROLL_SEARCH_INTERVAL=0.3 | 固化层 config |
| `ai_tests/run_e2e.py` | _should_skip_after_failure + 跳过逻辑 | 编排层 |
| `ai_tests/tests/test_ui_executor.py` | 补充滚动查找/自愈/跳过测试 | 单元测试 |
| `ai_tests/docs/known_issues.md` | 沉淀"显式 scroll 脆弱性"+"自愈误重启 atx"教训 | 陷阱库 |

### 不变

- `ai_tests/lib/case_parser.py` — 不改 Step 结构
- `ai_tests/lib/evidence_collector.py` — 不改证据收集
- `ai_tests/lib/rule_analyzer.py` — verdict 规则不变（SKIPPED 复用 manual 规则）

## V4 蓝图（AI 自主开发闭环）

> 本 spec 不实施，仅设计。

### 蓝图定位

E2E 测试基础设施是**给 AI 自己用的工具**。AI 为用户开发新功能时：

```
新功能需求
  → 设计文档 (OpenSpec)
  → 实施 (步骤5)
  → [步骤5.5] 真机验证 (本基础设施)
    → 源码影响分析 (--diff HEAD~1)
    → 受影响用例识别 (source_map)
    → 用例过时检测 + 自动重新生成 (源码驱动)
    → 真机执行受影响用例
    → 快速回归抽样未受影响用例
    → 出报告 (五件套)
  → 验收 (检查点3)
  → 失败?
    → 功能Bug → 修复 → 重测
    → 流程Bug → 修复 → 沉淀到 known_issues
```

### V4 增强项

#### V4-1: 源码驱动测试用例自动生成

**当前缺口**：M9 source_test_generator 只分析 Activity 源码，不分析 preference XML / menu XML / Manifest

**V4 设计**：
- PreferenceXMLAnalyzer: 解析 `res/xml/pref_*.xml`，生成"导航到每个 preference + 可见性断言"用例
- MenuXMLAnalyzer: 解析 `res/menu/*.xml`，生成"每个 menu item 点击"用例
- ManifestActivityAnalyzer: 解析 `AndroidManifest.xml`，生成"每个 Activity 启动可达性"用例

**价值**：从源码变更自动生成测试，不依赖人工写用例

#### V4-2: 用例过时检测

**当前缺口**：源码变了，用例不会自动标记过时

**V4 设计**：
- git diff 对比变更文件 vs 用例引用的源码（关联源码字段）
- preference key 变了 / Activity 删了 / menu id 变了 → 标记用例过时
- 过时用例触发 V4-1 重新生成

#### V4-3: 新功能开发强制触发钩子

**当前缺口**：不绑定 git hook 或 OpenSpec 流程

**V4 设计**：
- OpenSpec 步骤 5（实施）完成后，自动触发步骤 5.5（AI E2E 测试）
- git pre-commit hook：检测到源码变更 → 提示跑 `run_e2e.py --diff HEAD`
- AGENTS.md 强制规则：新功能开发必须跑 5.5，禁止跳过

#### V4-4: 测试流程问题沉淀机制

**当前缺口**：流程问题修复后不沉淀，下次重复踩坑

**V4 设计**：
- `ai_tests/docs/known_issues.md` 主动追加（已有机制，需强化）
- `ai_tests/docs/regression_history.md` 记录回归历史
- 测试失败时自动匹配 known_issues，给出修复建议
- 修复后自动追加新陷阱到 known_issues

#### V4-5: 通用 UI 探查工具

**当前缺口**：AI 临时写 _tmp_*.py 探查 UI，不复用

**V4 设计**：
- `ai_tests/tools/ui_explorer.py`: 通用 UI 探查工具
  - connect() / navigate(path) / scroll_find(target) / click_and_dump(target)
  - 供 AI 在新功能开发时调用，快速验证 UI 结构
- 沉淀探查模式，避免重复造轮子

### V4 验收标准

- AI 改源码后，能自动跑受影响用例，pass_rate > 70%
- 用例过时自动检测 + 重新生成
- 流程问题修复后沉淀到 known_issues，下次自动匹配
- AI 临时探查用 ui_explorer.py，不写 _tmp 脚本
