# ai_tests/cases 用例库总索引

> **V3 双轨用例库**：本目录存放第二波/第三波覆盖新增的测试用例 MD 文件。
> 第一波存量用例保留在 `docs/tests/`（不迁移，保持向后兼容）。
> 同 TC-ID 时 B 轨 Python 用例（`auto_{tc_id}.py`）优先于 A 轨 MD 用例。

## 三波覆盖进度

| 波次 | 范围 | 状态 | 用例数 | 说明 |
|------|------|------|-------|------|
| **第一波** | `docs/tests/*.md` 存量用例 | 🔄 字段补全中 | 208 | V3 源码溯源字段（关联源码/关联 Activity）补全 |
| **第二波** | `ai_tests/cases/*/*.md` 核心模块矩阵 | ⏳ 待编写 | 35 | 调试工具 5 + 书架 8 + 书源管理 10 + 阅读 12 |
| **第三波** | Bug 反向补充 | ⏳ 待启动 | 按需 | 基于 E5 实测发现的 Bug 反向补充用例 |

## 目录结构

```
ai_tests/cases/
├── _index.md                          # 本文件（总索引）
├── F-P0-1-debug-tools/                # 调试工具扩展用例（第二波）
│   └── case.md
├── F-P0-5-bookshelf/                  # 书架管理用例（第二波）
│   └── case.md
├── F-P0-6-source-manage/              # 书源管理用例（第二波）
│   └── case.md
├── F-P0-7-reading/                    # 阅读用例（第二波）
│   └── case.md
└── auto_*.py                          # B 轨 Python 用例（M9 生成 + AI 补全）
```

## 第二波覆盖计划（35 份新用例）

| 模块 | 优先级 | 用例数 | 模块编号 | 主要 Activity | 状态 |
|------|-------|-------|---------|--------------|------|
| 调试工具 | P0 | 5 | F-P0-1 | DebugToolsActivity | ⏳ |
| 书架管理 | P0 | 8 | F-P0-5 | BookshelfActivity / BookshelfManageActivity | ⏳ |
| 书源管理 | P0 | 10 | F-P0-6 | BookSourceActivity / SourceEditActivity | ⏳ |
| 阅读 | P0 | 12 | F-P0-7 | ReadBookActivity / ReadActivity | ⏳ |

## V3 双轨调度规则

| 场景 | A 轨（MD） | B 轨（Python） | 实际执行 |
|------|-----------|---------------|---------|
| 仅 MD | ✅ 存在 | ❌ 不存在 | MD 执行 |
| 仅 Python | ❌ 不存在 | ✅ 存在 | Python 执行 |
| MD + Python 同 TC-ID | ✅ 存在 | ✅ 存在 | **Python 优先** |
| Python 失败 | ✅ 存在 | ✅ 失败 | 降级 MD 执行（DUAL_TRACK_FALLBACK_TO_MD=True） |

## V3 源码溯源字段（强制）

每个 TC 用例必须包含以下字段（M3 CaseParser 解析）：

```markdown
## TC-XXX-NN：标题

**关联源码**：XXXActivity.kt
**关联 Activity**：XXXActivity

**测试步骤**：
1. xxx

**预期结果**：
- ✅ xxx
```

字段缺失时，`gen_module_matrix.py` 会标记为缺失项，覆盖率报告会显示。

## 维护规则

1. **新增用例**：放入 `ai_tests/cases/{module}/case.md`，命名遵循 `{模块编号}-{功能名}/case.md`
2. **B 轨 Python 用例**：通过 `run_e2e.py --gen-test {ActivityName}` 生成骨架，AI 补全业务逻辑
3. **覆盖率检查**：每次新增用例后运行 `python ai_tests/scripts/gen_module_matrix.py` 验证字段完整性
4. **存量用例补全**：第一波存量用例（`docs/tests/*.md`）逐步补全 V3 字段，不迁移文件

## 相关文档

- [核心模块矩阵报告](../docs/module_matrix.md) — 自动生成，覆盖率统计
- [测试用例设计指南](../../docs/project-rules/test-case-design-guide.md) — S14 子规范
- [M3 用例解析器源码](../lib/case_parser.py) — 字段解析逻辑
- [M9 源码→测试生成器](../lib/source_test_generator.py) — B 轨 Python 用例生成
