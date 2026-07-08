# source_map.json 维护指南（M8 源码影响分析器输入）

> 阶段 19.1 / 子规范 S18：教 AI 维护 M8 `SourceImpactAnalyzer` 的输入文件 `source_map.json`。
> 关联源码：`ai_tests/lib/source_impact_analyzer.py`、`ai_tests/config.py`（`SOURCE_MAP_PATH`）。

## 1. 概述

`source_map.json` 是 M8 源码影响分析器的核心输入，记录 **Activity → TC-ID** 的映射关系，以及 Activity 之间的静态调用图（callers）。

**作用**：当源码发生变更时，M8 执行 `git diff --name-only <git_ref>` 取得改动文件列表，反向追溯受影响的 Activity（向上追溯 2 层调用链），再查 `source_map.json` 中该 Activity 关联的 TC-ID，输出 `recommended_rerun`（建议复测的用例 ID 列表）。

**数据流**：

```
git diff --name-only <git_ref>
    → _reverse_trace() 向上追溯 2 层找到调用方 Activity
    → _lookup_related_tc_ids() 查 source_map 关联 TC-ID
    → 输出 {changed_files, affected_activities, related_tc_ids, recommended_rerun}
```

## 2. 文件位置

| 项 | 值 |
|----|----|
| 文件路径 | `ai_tests/lib/source_map.json` |
| 配置常量 | `config.SOURCE_MAP_PATH`（`ai_tests/config.py` 第 37 行） |
| 格式 | JSON UTF-8（`ensure_ascii=False, indent=2`） |
| 生成方式 | M8 `build_source_map()` 自动扫描 + 持久化 |

## 3. 数据结构示例

> **重要**：实现版采用**扁平结构**（以 Activity 类名作 key），而非设计文档原稿的 `{mappings: {path: {...}}}` 结构。详见 design.md ADR-AD-16「source_map.json 结构扁平化」决策。

```json
{
  "version": "1.0",
  "generated_at": "2026-07-08T10:30:00.123456",
  "activities": {
    "BookSourceActivity": {
      "path": "app/src/main/java/io/legado/app/ui/book/source/BookSourceActivity.kt",
      "callers": ["MainActivity", "ConfigActivity"],
      "ui_components": ["R.id.recycler_view", "R.id.fab", "R.layout.activity_book_source"],
      "tc_ids": ["TC-F-P0-2-01", "TC-F-P0-2-02"]
    },
    "DebugToolsActivity": {
      "path": "app/src/main/java/io/legado/app/ui/association/debug/DebugToolsActivity.kt",
      "callers": ["MainActivity"],
      "ui_components": ["R.id.btn_encode_convert", "R.id.btn_http_test"],
      "tc_ids": ["TC-F-P0-1-01", "TC-F-P0-1-02"]
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | source_map 版本（当前 `1.0`，常量 `SOURCE_MAP_VERSION`） |
| `generated_at` | string | ISO 8601 时间戳（`build_source_map()` 执行时刻） |
| `activities` | object | Activity 映射表，key 为 Activity 类名（如 `BookSourceActivity`） |
| `activities[name].path` | string | Activity 源码相对项目根的路径 |
| `activities[name].callers` | string[] | 调用方 Activity 类名列表（grep 静态扫描，向上追溯依据） |
| `activities[name].ui_components` | string[] | UI 组件引用（`R.id.xxx` / `R.layout.xxx` / `setContent{}`） |
| `activities[name].tc_ids` | string[] | 关联的 TC-ID 列表（从 `docs/tests/*.md` 和 `ai_tests/cases/*.md` 扫描） |

### unknown_bindings 字段（设计预留，当前未生成）

设计文档预留了 `unknown_bindings` 字段，用于记录无法自动映射的 binding 引用（如反射加载场景）。**当前 M8 实现尚未生成此字段**（反射场景罕见，V4 再补）。维护流程中 AI 可手动检查未被自动映射的 Activity。

```json
"unknown_bindings": [
  {"file": "service/BookLoader.kt", "note": "uses reflection to load BookChapter"}
]
```

## 4. 维护流程（任务 19.3）

### 步骤 1：新增 Activity 后运行扫描

新增 Activity 或改动 `docs/tests/*.md` 用例关联后，运行：

```bash
python ai_tests/run_e2e.py --update-source-map
```

该命令调用 `SourceImpactAnalyzer.build_source_map()`，执行以下动作：
1. 扫描 `SOURCE_ROOT`（`app/src/main/java/io/legado/app/`）下所有 `*Activity.kt`（排除 `Base`/`VMBase` 前缀的基类）
2. 对每个 Activity 提取 `ui_components`、`callers`、`tc_ids`
3. 持久化到 `ai_tests/lib/source_map.json`（覆盖写）
4. 输出统计：`N 个 Activity，M 个关联 TC-ID`

> **耗时参考**：56 个 Activity × grep 全源码约 5-10 秒（实测规模：56 Activity / 23 唯一调用方 / 39 关联 TC-ID）。

### 步骤 2：AI 审阅 unknown_bindings / 遗漏映射

扫描完成后，AI 应检查：
- 新增的 Activity 是否出现在 `activities` 字典中（若缺失，检查源码文件名是否以 `Activity.kt` 结尾、是否被 `Base`/`VMBase` 前缀排除）
- 新增的 Activity 的 `tc_ids` 是否为空（为空表示 `docs/tests/*.md` 中未出现该 Activity 名，需补充用例的「关联 Activity」字段）
- `callers` 是否合理（grep 字符串匹配会误报注释中的引用，已知上限，V4 基于 AST 分析修正）

### 步骤 3：手动补充 mappings

若自动扫描遗漏（如 Activity 通过反射启动、`tc_ids` 未关联），AI 手动编辑 `source_map.json`：
- 在 `activities` 字典中新增/补充对应 Activity 的 `tc_ids` 数组
- 补充后无需重新运行 `--update-source-map`（手动编辑优先于自动覆盖）

> **注意**：再次运行 `--update-source-map` 会覆盖手动编辑。若需保留手动映射，避免频繁重建；或在 `docs/tests/*.md` 中补充「关联 Activity」字段，使自动扫描能正确关联。

## 5. 触发命令汇总

| 命令 | 作用 | 退出码 |
|------|------|--------|
| `python ai_tests/run_e2e.py --update-source-map` | 重建 source_map.json 后退出 | 0=成功，2=失败 |
| `python ai_tests/run_e2e.py --diff HEAD~1` | 分析 git diff 影响的 TC-ID（读取 source_map.json） | 0=成功 |
| `python -m ai_tests.lib.source_impact_analyzer HEAD~1` | 直接调用 M8 模块自检（构建 + 分析） | 0=成功 |

## 6. 注意事项

### 6.1 applicationIdSuffix 导致类名歧义

Legado debug 构建使用 `applicationIdSuffix ".debug"`（`config.py` 第 23 行 `BUILD_TYPE = "debug"`），导致应用包名为 `io.legado.app.debug`。但 **Activity 类名不受 applicationIdSuffix 影响**，始终为 `io.legado.app.ui.xxx.XxxActivity`（源码包名）。

`source_map.json` 中 `activities` 的 key 是 **Activity 类名**（如 `BookSourceActivity`），不含包名前缀，无歧义。但在以下场景需用完整类名：
- `am start` 命令启动 Activity：`am start -n io.legado.app.debug/io.legado.app.ui.book.source.BookSourceActivity`（应用包名用 debug 后缀，Activity 类名用源码包名）
- M9 生成测试骨架时计算 `full_activity_class`（见 `source_test_guide.md`）

### 6.2 source_map.json 过期风险

`source_map.json` 是快照式产物，新增 Activity 后未重建会导致 M8 影响分析遗漏。规避方式：代码变更后运行 `--update-source-map`（此陷阱已记录在 `known_issues.md`）。

### 6.3 反向追溯深度限制

M8 反向追溯最大 2 层（`MAX_REVERSE_TRACE_DEPTH = 2`）：Activity → 直接调用方 → 间接调用方。超过 2 层会引入大量噪声（如 `MainActivity` 被几乎所有 Activity 引用）。如需更深追溯，修改 `source_impact_analyzer.py` 中该常量（V4 改为可配置）。

### 6.4 简化折中说明

| 折中点 | 已知上限 | 升级路径 |
|--------|---------|---------|
| `_find_callers` 全文 grep 类名字符串 | 会误报注释中的引用 | V4 基于 AST 分析 |
| `_reverse_trace` 基于文件名 stem 匹配 | 同名文件在不同包会冲突 | V4 基于完整路径匹配 |
| `unknown_bindings` 未实现 | 反射场景无法映射 | V4 补充反射检测 |
| `--diff` 与 `--tc` 互斥未做冲突检测 | 同时传参时优先 `--diff` | V4 加冲突校验 |

## 7. 相关文档

- 设计文档：`docs/specs/e2e-automated-testing/design.md` 1.3.8 节（M8 设计）
- M9 测试生成指南：`ai_tests/docs/source_test_guide.md`
- 已知陷阱：`ai_tests/docs/known_issues.md`（含 source_map.json 过期陷阱）
- 源码实现：`ai_tests/lib/source_impact_analyzer.py`
