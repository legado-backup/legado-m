# spec.md — E2E UI 执行器加固

## Intent

修复 V3 UI 执行器（M4 `ui_executor.py`）三个实测缺陷，使 E2E 测试基础设施能为 AI 自主开发闭环提供**可靠的真机验证能力**——AI 为用户开发新功能时，能自己跑测试、自己验收、失败时自己定位修复，不依赖人工调试。

## Scope

### In Scope（V3 MVP 实施）

| 编号 | 缺陷 | 修复 |
|------|------|------|
| D1 | click 找不到长列表元素（需滚动） | click 加"滚动查找"能力 |
| D2 | 自愈误重启 atx-agent | 区分"元素未找到"vs"App 崩溃" |
| D3 | 步骤失败后污染后续证据 | 失败后跳过后续步骤 |

### Out of Scope（V4 蓝图，本 spec 仅设计不实施）

- 源码驱动测试用例自动生成（pref XML / menu XML / Manifest 分析器）
- 新功能开发强制触发钩子（git hook / OpenSpec 步骤嵌入）
- 测试流程问题沉淀与重用机制
- textContains/descContains 模糊匹配
- u2 UiSelector2 多条件 OR 查询

## Approach

### 主方案：固化层 ui_executor.py 三项加固

**D1 click 滚动查找**：
- click 方法加 `scroll_search=True` 参数（默认 True）
- `_get_element` 找不到元素时，调用新方法 `_scroll_find` 在当前页面滚动 N 次（默认 5）找
- 滚动查找找到就返回元素，找不到返回 None
- 滚动查找可被 `scroll_search=False` 禁用（如已确定元素在当前视口）

**D2 自愈区分**：
- 自愈前先 `app_current` 检测：
  - App 在前台 + 正确 Activity → 元素未找到 → 重试（不重启 atx）
  - App 不在前台 / Activity 异常 → App 崩溃 → 重启 App
- 完全去掉"重启 atx-agent"逻辑（atx 不是问题根源）

**D3 失败跳过**：
- execute_step 加 `skip_remaining` 状态
- 某步失败后，后续步骤标记 `SKIPPED`（verdict=skip），不执行动作
- SKIPPED 步骤仍收集前置截图（证明页面状态）

### Alternatives Considered

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| 显式 scroll 步骤（用例写 scroll down） | 不动固化层 | 依赖设备分辨率、漏写滚动、换设备失效（已实测） | ❌ 已证脆弱 |
| 源码驱动计算滚动次数 | 最准 | 需新 XML 分析器，实现复杂 | ⏳ V4 |
| click 滚动查找（主方案） | 通用、设备无关、所有用例受益 | 固化层修改需 OpenSpec；可能误滚 | ✅ 采纳 |

### Drawbacks

1. **滚动查找增加单步耗时**：最坏情况 5 次滚动 × 1s/次 = 5s。可接受（真机测试非毫秒级场景）。
2. **可能误滚到错误区域**：滚动查找假设元素在当前页面下方。若元素在上方（需 scroll up），5 次 down 找不到。V4 增强：双向滚动查找。
3. **SKIPPED 步骤无动作证据**：仅前置截图，无 after。可接受（失败已由前一步证明）。

## Requirements

### R1: click 滚动查找

- R1.1: click(target, timeout=10, scroll_search=True) 默认开启滚动查找
- R1.2: 滚动查找在 `_get_element` 失败后触发，滚动 N 次（默认 5，config 可配）
- R1.3: 每次滚动后 0.3s 等待界面刷新，再检测元素
- R1.4: 滚动查找找到元素返回，找不到返回 None（click 返回 False）
- R1.5: scroll_search=False 时退化为当前行为（仅等待，不滚动）
- R1.6: 滚动查找不影响 input_text / wait_element（仅 click 受益）

### R2: 自愈区分

- R2.1: 自愈前调用 `self.d.app_current()` 检测 App 状态
- R2.2: App 在前台 + Activity 含 `io.legado.app` → 判定"元素未找到"→ 重试（不重启）
- R2.3: App 不在前台 / Activity 异常 / app_current 抛异常 → 判定"App 崩溃"→ 重启 App
- R2.4: 完全移除 `self.memu.restart_atx_agent()` 调用（atx 不是问题根源）
- R2.5: 重启 App 后重新走 dismiss_dialogs → 重试当前步骤

### R3: 失败跳过

- R3.1: execute_step 返回 `success=False` 时，调用方（run_e2e）将后续步骤标记 SKIPPED
- R3.2: SKIPPED 步骤不执行 `_dispatch_action`，直接返回 `success=False, error="SKIPPED (前置步骤失败)"`
- R3.3: SKIPPED 步骤仍收集前置截图（证明页面停在前一步状态）
- R3.4: 跳过逻辑放在 run_e2e 编排层（不改固化层 execute_step 签名）

## Scenarios

### S1: click 滚动查找成功（正常用例）

**前置**：App 在"我的"页面，"其它设置"在页面底部不可见
**步骤**：click("其它设置")
**预期**：
- _get_element 初次查找返回 None
- 触发 _scroll_find，滚动 1-2 次后"其它设置"可见
- 返回元素，click 成功
- 日志记录"scroll_find: 找到元素 其它设置 (滚动 2 次)"

### S2: click 滚动查找失败（异常用例）

**前置**：App 在"书架"页面，点击"调试工具"（不在书架页面）
**步骤**：click("调试工具", scroll_search=True)
**预期**：
- _get_element 初次查找返回 None
- _scroll_find 滚动 5 次仍未找到
- 返回 None，click 返回 False
- 日志记录"scroll_find: 未找到元素 调试工具 (滚动 5 次)"

### S3: 自愈区分 - 元素未找到（正常用例）

**前置**：App 在前台，Activity=MainActivity
**步骤**：click("不存在的元素")
**预期**：
- click 失败，触发自愈
- app_current 检测：App 在前台，Activity 正常
- 判定"元素未找到"，不重启 atx，不重启 App
- 重试 1 次后仍失败，标记步骤失败
- 日志记录"自愈：元素未找到，重试（不重启）"

### S4: 自愈区分 - App 崩溃（异常用例）

**前置**：App 刚崩溃，回到桌面
**步骤**：click("我的")
**预期**：
- click 失败，触发自愈
- app_current 检测：App 不在前台 / Activity 异常
- 判定"App 崩溃"，重启 App（memu.start_app）
- 重新 dismiss_dialogs → 重试当前步骤
- 日志记录"自愈：App 崩溃，已重启 App"

### S5: 失败跳过（边界用例）

**前置**：TC-F-P0-1-01 执行中，步骤 2 click("其它设置") 失败
**预期**：
- 步骤 2 返回 success=False
- run_e2e 标记步骤 3-12 为 SKIPPED
- SKIPPED 步骤仅收集前置截图，不执行动作
- 报告 verdict=skip，error="SKIPPED (前置步骤 2 失败)"
- pass_rate 计算排除 SKIPPED 步骤

### S6: 完整导航成功（集成用例）

**前置**：App 在主页
**步骤**：TC-F-P0-1-01 完整 12 步
**预期**：
- 步骤 1 click("我的") → 成功（content-desc 回退）
- 步骤 2 click("其它设置") → 滚动查找成功
- 步骤 3-6 scroll down → 成功
- 步骤 7 click("调试工具") → 滚动查找成功
- 步骤 8 click("编码转换") → 成功
- 步骤 9-12 → 成功
- pass_rate=100%
