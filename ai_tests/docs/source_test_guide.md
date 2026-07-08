# M9 源码→测试生成器使用指南（B 轨 Python 用例生成）

> 阶段 19.2 / 子规范 S19：教 AI 用 M9 `SourceTestGenerator` 生成 B 轨 Python 测试骨架，并补全业务逻辑。
> 关联源码：`ai_tests/lib/source_test_generator.py`、`ai_tests/templates/auto_test_template.j2`。

## 1. 概述

M9 `SourceTestGenerator` 基于 Activity 源码静态分析，生成 Python 测试骨架（B 轨），供 M3 双轨调度识别。

**职责**：
- 读取 Activity 源码（`app/src/main/java/io/legado/app/` 下的 `*Activity.kt`）
- 提取 UI 元素：`setContentView` / `findViewById` / `R.id.xxx` / `binding.xxx` / `startActivity` 跳转
- 解析 `AndroidManifest.xml` 确认 Activity 已注册
- 渲染 Jinja2 模板（`auto_test_template.j2`），输出 Python 骨架
- TC-ID 自动分配：基于 module 前缀 + 现有最大编号 +1

**输出示例**：

```
ai_tests/cases/F-P0-1/auto_tc_f_p0_1_auto_001.py
```

## 2. 生成命令

### 2.1 通过 run_e2e.py 触发（推荐入口）

```bash
python ai_tests/run_e2e.py --gen-test BookshelfActivity
```

> **当前状态**：`run_e2e.py` 中 `--gen-test` 参数当前为**降级提示**（阶段 13 未完成编排层接入），会打印警告并退出码 0。M9 模块本身已完整实现，可直接通过模块入口调用（见 2.2）。

### 2.2 直接调用 M9 模块（当前可用方式）

```bash
python -m ai_tests.lib.source_test_generator BookshelfActivity [module]
```

- 第一个参数：Activity 类名（如 `BookshelfActivity`、`DebugToolsActivity`）
- 第二个参数（可选）：模块名（如 `F-P0-1`），省略时自动推断

### 2.3 模块自动推断规则

`module` 省略时，M9 从 `source_map.json` 查找该 Activity 关联的第一个 TC-ID，提取模块前缀：

| source_map 中 Activity 的首个 tc_id | 推断的 module |
|--------------------------------------|---------------|
| `TC-F-P0-1-01` | `F-P0-1` |
| `TC-F-P0-2-03` | `F-P0-2` |
| 无关联 TC-ID / source_map 不存在 | `auto`（降级） |

> 若 `source_map.json` 不存在或 Activity 无关联 TC-ID，模块推断降级为 `auto`，输出到 `ai_tests/cases/auto/`。请先运行 `python ai_tests/run_e2e.py --update-source-map` 确保 source_map 最新。

## 3. 输出路径与命名规范

### 3.1 输出路径

```
ai_tests/cases/{module}/auto_{tc_id_lower_with_underscores}.py
```

| module | 输出目录 |
|--------|---------|
| `F-P0-1` | `ai_tests/cases/F-P0-1/` |
| `auto`（降级） | `ai_tests/cases/auto/` |

### 3.2 TC-ID 编号规则

**TC-ID 格式**（大写连字符）：

```
TC-{module}-auto-{NNN}
```

- `{module}`：模块名（如 `F-P0-1`）
- `{NNN}`：三位数字序号，基于该 module 目录下现有 `auto_*.py` 文件的最大编号 +1

**文件名格式**（小写下划线）：

```
auto_{tc_id.lower().replace('-', '_')}.py
```

| TC-ID | 文件名 |
|-------|--------|
| `TC-F-P0-1-auto-001` | `auto_tc_f_p0_1_auto_001.py` |
| `TC-F-P0-2-auto-003` | `auto_tc_f_p0_2_auto_003.py` |

> **命名规则来源**：M3 `_find_python_track` 规则 1（文件名匹配）。文件名必须严格遵循此规则，否则 M3 双轨调度无法识别 B 轨用例。

## 4. 文件头部规范

生成的骨架文件头部必须包含 `# @tc_id:` 注释，作为 M3 兜底识别依据（当文件名匹配失败时的回退识别机制）：

```python
# @tc_id: TC-F-P0-1-auto-001
# @module: F-P0-1
# @activity: BookshelfActivity
# @generated_at: 2026-07-08T10:30:00
# @source: app/src/main/java/io/legado/app/ui/book/BookshelfActivity.kt
"""TC-F-P0-1-auto-001: BookshelfActivity 自动生成骨架"""
```

> AI 补全骨架时**不得删除** `# @tc_id:` 注释行，否则 M3 双轨调度可能无法识别该 B 轨用例。

## 5. am start 命令规范

生成的骨架中 `am start` 命令使用**完整类名**（源码包名，非应用包名）：

```bash
am start -n io.legado.app.debug/io.legado.app.ui.book.BookshelfActivity
```

| 部分 | 值 | 说明 |
|------|----|------|
| 应用包名（`-n` 前半） | `io.legado.app.debug` | 受 `applicationIdSuffix` 影响，debug 构建带 `.debug` 后缀 |
| Activity 类名（`-n` 后半） | `io.legado.app.ui.book.BookshelfActivity` | 源码包名，不受 suffix 影响 |

**完整类名计算逻辑**（M9 `_render_skeleton` 第 272-281 行）：

```
source_root 相对路径 → 替换分隔符为点 → 拼接 io.legado.app. 前缀
```

例如 `ui/book/BookshelfActivity.kt` → `io.legado.app.ui.book.BookshelfActivity`。

> **简化说明**：假设 `source_root` 是 `io.legado.app/`，前缀固定为 `io.legado.app` | 已知上限：`source_root` 改变时需同步 | 升级路径：从源码 `package` 声明动态提取（V4）。

## 6. B 轨补全规范（任务 19.4）

生成的骨架含 `TODO` 标记，AI **必须补全后才能纳入回归**。未补全的骨架不应提交到 `ai_tests/cases/` 或被 M3 调度执行。

### 6.1 必须补全的 TODO 类别

| TODO 类别 | 说明 | 补全要求 |
|-----------|------|---------|
| **步骤** | `# TODO: 补全测试步骤` | 基于 Activity 业务逻辑编写 u2 操作步骤（click/input/wait_element/scroll/back） |
| **断言** | `# TODO: 补全断言` | 编写预期校验（display/no_crash/result_contains/rule_match/db_state 等 8 种类型） |
| **证据收集点** | `# TODO: 标记证据收集点` | 在关键步骤后标记 8 类证据收集（logcat/ui_xml/screenshot/activity_stack/db_state/prefs_state/web_api/meminfo） |

### 6.2 补全流程

1. 运行 M9 生成骨架：`python -m ai_tests.lib.source_test_generator BookshelfActivity`
2. 打开生成的 `auto_*.py` 文件
3. 查找所有 `# TODO` 标记
4. 参考 Activity 源码和 `docs/tests/*.md` 中同模块的 A 轨 MD 用例，补全步骤/断言/证据收集点
5. 删除所有 `# TODO` 标记（补全完成后不应残留）
6. 手动运行验证：`python ai_tests/run_e2e.py --tc {tc_id}`
7. 验证通过后纳入回归套件

### 6.3 补全质量要求

- 每个生成的骨架至少包含 1 个断言（`no_crash` 是最低要求）
- 涉及 UI 交互的用例必须收集 `screenshot` + `ui_xml` 证据
- 涉及书源/数据操作的用例必须收集 `db_state` 证据
- 步骤必须基于 Activity 真实业务逻辑，不得照搬模板占位符

## 7. 简化折中说明

| 折中点 | 已知上限 | 升级路径 |
|--------|---------|---------|
| viewBinding 仅提取 `binding.xxx` 引用名 | 不解析 Binding 类生成的 View 类型 | V4 基于 Kotlin 语法树分析 |
| Compose 场景输出降级 | `setContent{}` 仅作 UI 组件标记，不提取 Composable 函数 | V4 接入 Compose 语义分析 |
| `click_targets` 跨行正则匹配 | 复杂跳转逻辑可能漏匹配 | V4 基于 AST 分析 |
| `_locate_activity` 仅匹配文件名 | 同名 Activity 在不同包命中第一个 | V4 基于 `package` 声明精确匹配 |
| Manifest 解析仅提取类名 | 不解析完整包路径，alias Activity 不解析 | V4 基于 XML 解析器 |

### Compose 场景降级说明

当 Activity 使用 Jetpack Compose（`setContent { ... }`）而非传统 View 体系时：
- M9 仅在 `ui_components` 中标记 `setContent{}`，**不提取 Composable 函数名**
- 生成的骨架中 `view_ids` 为空，`binding_ids` 为空
- AI 补全时需手动基于 Composable 函数编写 `wait_element` 步骤（u2 对 Compose 支持有限，建议降级为 `screenshot` + `result_contains` 断言）

## 8. 相关文档

- 设计文档：`docs/specs/e2e-automated-testing/design.md` 1.3.9 节（M9 设计）
- source_map.json 维护：`ai_tests/docs/source_impact_guide.md`
- 测试用例设计指南：`docs/project-rules/test-case-design-guide.md`（任务 18，含双轨制规则）
- 模板文件：`ai_tests/templates/auto_test_template.j2`
- 源码实现：`ai_tests/lib/source_test_generator.py`
