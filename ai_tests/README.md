# ai_tests — Legado E2E 自动化测试基础设施（V3）

> 自动化端到端测试框架：APK 自动部署 → UI 自动执行 → 8 类证据收集 → 规则判定 → 七件套报告

## 5 分钟上手

### 前置条件

1. MEmu 模拟器已安装（`D:\Program Files\Microvirt\MEmu\`）
2. APK 已构建（`app/build/outputs/apk/app/debug/`），且已配置正式签名（`legado_release.jks` + `local.properties`，详见 [build-apk-guide.md](../docs/project-flow/build-apk-guide.md) 第三章）
3. Python 3.12 + 虚拟环境（`ai_tests/venv/`）

### 快速开始

```bash
# 1. 激活虚拟环境
ai_tests\venv\Scripts\activate

# 2. 全量测试（自动发现 APK + 全部用例）
python ai_tests/run_e2e.py --apk auto --tc all

# 3. 查看报告
# 报告输出到 ai_tests/reports/report_{timestamp}/
# 打开 report.md 查看人读报告
# 打开 summary.txt 查看一行摘要
```

## CLI 参数

### 基础参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--apk` | `auto` | APK 路径（`auto`=自动发现最新 APK） |
| `--tc` | `all` | 用例筛选（`all`/`P0`/`P1`/模块名/`TC-ID`） |
| `--report-dir` | 自动生成 | 报告输出目录 |
| `--no-rules` | 关闭 | 禁用规则判定（仅收集证据） |
| `--keep-device` | 关闭 | 测试完成后保留模拟器运行 |
| `--instance-id` | `0` | MEmu 实例 ID |
| `--init-device` | 关闭 | 强制重新初始化 uiautomator2 |

### V3 新增参数

| 参数 | 说明 | 状态 |
|------|------|------|
| `--diff <git_ref>` | 源码影响分析，自动选复测用例 | ⚠️ M8 未实现，降级为 `--tc all` |
| `--gen-test <Activity>` | 为 Activity 生成 Python 测试骨架 | ⚠️ M9 未实现，仅提示 |
| `--update-source-map` | 重建 source_map.json | ⚠️ M8 未实现，仅提示 |
| `--feedback` | 触发反馈闭环处理 | ⚠️ M16 未实现，仅提示 |
| `--ai-verify` | 报告生成后自动拉起 VL 模型判定 manual 用例并回填 ai_verdict（AI-LLM-Testing） | ✅ 已实现（依赖本地 VL 模型服务在线，不可用时跳过并提示） |

## 用例筛选示例

```bash
# 全量测试
python ai_tests/run_e2e.py --tc all

# 仅 P0 优先级用例
python ai_tests/run_e2e.py --tc P0

# 指定模块（如 F-P0-1 调试工具）
python ai_tests/run_e2e.py --tc F-P0-1

# 单用例
python ai_tests/run_e2e.py --tc TC-F-P0-1-01
```

## V3 双轨调度

V3 引入双轨调度机制：同 TC-ID 时 **Python 轨道优先于 MD 轨道**。

| 轨道 | 来源 | 优先级 | 状态 |
|------|------|--------|------|
| **MD 轨道（A 轨）** | `docs/tests/*.md` + `ai_tests/cases/*/case.md` | 低 | ✅ 已实现（UiExecutor 执行） |
| **Python 轨道（B 轨）** | `ai_tests/cases/*/auto_*.py` | 高 | ⚠️ M9 未实现，降级为 MD 执行 |

调度逻辑（M3 CaseParser 解析阶段处理）：
1. 扫描 `ai_tests/cases/{module}/auto_*.py` 寻找同 TC-ID 的 B 轨用例
2. 若存在 B 轨，则 `track_source="python"`，否则 `track_source="md"`
3. run_e2e.py 执行时检查 `track_source`，B 轨优先执行

> **当前状态**：M9 sourceTestGenerator 未实现，B 轨 Python 用例暂无法自动生成。检测到 `track_source="python"` 时降级为 MD 执行并 warn。M9 实现后，B 轨将自动执行 `auto_*.py`。

## V3 参数示例（降级模式）

```bash
# 源码影响分析（M8 未实现时降级为全量测试）
python ai_tests/run_e2e.py --diff HEAD~1

# 生成测试骨架（M9 未实现时仅提示）
python ai_tests/run_e2e.py --gen-test BookshelfActivity

# 反馈闭环（M16 未实现时仅提示）
python ai_tests/run_e2e.py --feedback
```

## 报告输出

> **目录现状（2026-08-30 如实描述）**：`ai_tests/reports/` 为**平铺证据文件 + `report_{timestamp}/` 目录并存**——根目录散落历史验证截图/UI XML/DB 等证据文件，另有 `bugfix-ui-20260824/`、`dbverify/`、`evidence/`、`session_reset_verify/`、`t_batch/` 等专项子目录；`run_e2e.py` 每次执行生成独立 `report_{timestamp}/` 七件套目录。

执行后生成七件套报告（`ai_tests/reports/report_{timestamp}/`）：

| 文件 | 说明 |
|------|------|
| `report.md` | 人读报告（失败用例置顶 + manual 用例置顶 + 全部用例表 + V3 affected/feedback 节） |
| `report.json` | 机器可读（AI agent 接入，含 evidence_collected/ai_prompt_path/track_source） |
| `manual_cases.md` | manual 用例清单 + AI agent 接入流程 |
| `summary.txt` | 一行摘要（`pass:N/M fail:N manual:N pass_rate:X%`） |
| `affected_modules.json` | V3 受影响模块（`--diff` 时生成） |
| `feedback_suggestions.md` | V3 反馈建议（人读，规则/提示词/陷阱库建议） |
| `feedback_suggestions.json` | V3 反馈建议（机器读，M16 回填） |

### 证据归档

每用例独立目录 `cases/{tc_id}/`，包含 8 类证据：

```
cases/TC-F-P0-1-01/
├── step-01-*.png|xml     # 截图 + UI XML
├── log-slice.txt         # 日志切片
├── activity-stack.txt     # Activity 栈
├── db-state.json         # 数据库状态（MEmu 无 run-at 时降级）
├── prefs-state.json      # SharedPreferences（同上）
├── web-api-resp.json     # Web API 响应（未启动时降级）
├── meminfo.txt           # 内存状态
└── ai-prompt.md          # AI agent 分析提示词（manual 时）
```

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 全部通过 |
| `1` | 部分失败（有 fail 或 manual） |
| `2` | 致命错误（环境/APK/模拟器故障） |

CI/CD 集成示例：

```bash
python ai_tests/run_e2e.py --apk auto --tc all
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✅ 全部通过"
elif [ $exit_code -eq 1 ]; then
    echo "⚠️ 部分失败，查看报告"
else
    echo "❌ 致命错误"
fi
```

## 单元测试（基础设施自测）

覆盖 `ai_tests/tests/` 下测试文件（编排/解析/执行/证据/报告/控制器/取色门禁等层），当前基线 **295 passed**。

```bash
# 项目根目录执行（推荐）
ai_tests\venv\Scripts\python.exe -m pytest ai_tests/tests -q

# 或 ai_tests 目录下执行
cd ai_tests
venv\Scripts\python.exe -m pytest -q
```

- 配置：`ai_tests/pytest.ini`（testpaths + 告警过滤）
- 路径引导：`ai_tests/tests/conftest.py`（自动注入项目根到 sys.path，免设 PYTHONPATH）
- 每个文件也支持直接运行：`python ai_tests/tests/test_run_e2e.py`
- pytest 已加入 `requirements.txt`；新环境安装依赖后即可运行


## 架构概览

```
Layer 3: 编排层（run_e2e.py）
  ↓
Layer 2: 用例与执行层
  M3 用例解析器 → M4 UI 执行器 → M5 证据收集器
  ↓
Layer 1: 基础设施层
  M1 模拟器控制 → M2 APK 部署 → M6 规则分析器 → M7 报告生成器
  ↓
Layer 0: 源码驱动层（V3，阶段 12-13）
  M8 源码影响分析器 → M9 源码→测试生成器
```

## 脚本族索引（ai_tests/scripts/）

> **目录口径（2026-09-01 核定，总线 2.12 产出，B2 L2 模板脚本落位依据）**：
> 1. **落位**：测试辅助/L2 验证脚本统一落 `ai_tests/scripts/`，按族前缀命名（下表）。
> 2. **入库**：`.gitignore` 对 `/ai_tests/scripts/*.py` **默认全部忽略**，仅白名单（`!` 行）固化脚本入库——脚本固化为长期资产时必须同步加白名单行。**当前白名单 4 个（与磁盘现存精确一致）**：`l2_verify_precise_manage.py`（精准管理 L2）/ `verify_no_crash.py`（双包无崩溃）/ `l2_verify_image_enhance_governance.py`（画质增强治理 L2）/ `l2_verify_p0_sandbox_cache.py`（P0 书源沙箱+缓存命名空间 L2，ng-p0-source-security-impl）。
> 3. **登记**：新脚本必须登记 [SOP 固定脚本表](./docs/fixed_test_workflow.md)（SOP 自身维护规则强制），本节族口径随治理状态更新。
> 4. **历史**：治理前 205 个平铺脚本已分批收敛（52 个删于 2026-08-30 ai-test-system-refinement，备份 `bak/ai-test-refinement-20260830/`；其余随后续治理批次移除），下表族前缀为**前瞻口径**，现存实例以上述白名单为准。

> 完整脚本清单以 [SOP 固定脚本表](./docs/fixed_test_workflow.md) 为准，本节仅按族分组给出口径。

| 族 | 前缀 | 用途 |
|------|------|------|
| L2 验证族 | `l2_verify_*` | 功能点 L2 真机验证（视频/订阅/主题/高亮/文件夹等） |
| 模式切换验证族 | `verify_*` | 用户场景回归验证（模式切换/会话重置/无崩溃/嗅探回归等） |
| 导航辅助族 | `nav_*` / `goto_*` | 脱敏导航到目标页面（只输出编号不输出名称） |
| 诊断族 | `diag_*` | 诊断辅助（已于 2026-08-30 ai-test-system-refinement 治理中清理，备份 `bak/ai-test-refinement-20260830/`） |
| AI/VL 族 | `ai_*` / `vl_*` | 本地 VL 模型对截图做目标化视觉判定（截图审查拦截兜底通道） |

## 相关文档

- [设计文档（已归档）](../docs/specs/archive/e2e-automated-testing/design.md)
- [任务清单（已归档）](../docs/specs/archive/e2e-automated-testing/tasks.md)
- [深度分析报告（已归档）](../docs/specs/archive/e2e-automated-testing/ai-testing-research-2026.md)

## V5 订阅源批量优化脚本

> V5 站点攻坚期一次性脚本已于 2026-08-30 ai-test-system-refinement 治理中归档删除（备份 `bak/ai-test-refinement-20260830/`）。
