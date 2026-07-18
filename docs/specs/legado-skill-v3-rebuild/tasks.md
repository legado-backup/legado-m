# legado-source-creator Skill v3 全面重构 - Tasks

> 本文档定义 v3 全面重构的任务清单，按依赖关系排序。

## 任务总览

| 阶段 | 任务数 | 说明 |
|------|--------|------|
| Step 1 归档 | T1-T3 | 创建归档目录 + 归档无关功能 + 归档一次性脚本 |
| Step 2 修复 | T4-T5 | 修复 None 序列化 bug + 新增 E2E 测试 |
| Step 3 文档 | T6-T8 | 合并 references/ + 精简 SKILL.md + 删除 AI_README.md |
| Step 4 验证 | T9 | 真机 E2E 验证 |

## Step 1: 归档（AC-1）

### T1: 创建归档目录结构和归档说明

**输入**：无
**输出**：
- `.trae/skills/legado-source-creator-archive/` 目录
- `.trae/skills/legado-source-creator-archive/README.md`（归档说明：归档日期+回退方法+保留30天）

**实现**：
1. 创建 `.trae/skills/legado-source-creator-archive/` 目录
2. 创建子目录：web/ storage/ alembic/ server/ device/ oneoff-scripts/ unused-tools/
3. 写 README.md 说明归档原因、归档日期（2026-07-17）、30天后清理、回退方法

**验收**：LS 确认目录结构存在

### T2: 归档无关功能模块

**输入**：T1 完成
**输出**：
- 归档 `legado_client/web/` → archive/web/
- 归档 `legado_client/storage/` → archive/storage/
- 归档 `legado_client/server/` → archive/server/
- 归档 `legado_client/device/` → archive/device/
- 归档 `scripts/alembic/` → archive/alembic/
- 归档 `scripts/legado_client/fetcher/` 中的批量相关 → archive/oneoff-scripts/
- 归档无关辅助工具（11个中9个）→ archive/unused-tools/

**保留**：
- legado_client/utils/（HTML获取等基础工具）
- legado_client/analyzer/（auto_fixer/error_diagnoser/source_validator/rule_precheck/confidence_evaluator/parse_strategy/source_navigation/jar_optimizer）
- legado_client/client/（debug_runner/debug_orchestrator/rule_engine_client/debug_result/obstacle_resolver/webview_handler/user_interaction/interactive_guide/batch_runner）
- legado_client/delegate/（ocr_delegate/webview_delegate）
- legado_client/experience/（experience_manager/conflict_resolver）
- legado_client/tests/（保留）
- legado_client/__init__.py / __main__.py / cli.py（精简后保留）

**实现**：
1. 用 RunCommand `Move-Item` 批量移动（PowerShell）
2. 移动后用 Grep 确认无引用断裂
3. 修复 SKILL.md 中对归档模块的引用

**验收**：
- LS 确认归档目录包含原模块
- Grep 确认保留模块无断裂引用
- 运行 `python -c "from legado_client.cli import main"` 不报 ImportError

### T3: 归档一次性脚本

**输入**：T2 完成
**输出**：
- 归档 scripts/ 根目录 83% 一次性脚本 → archive/oneoff-scripts/

**保留 9 个核心脚本**（在 scripts/ 根目录）：
- debug-source.py
- verify-source.py
- verify-selector.py
- verify-decrypt.py
- verify-image.py
- analyze_site.py
- quick-verify.py
- requirements.txt / setup.py / setup_venv.bat / setup_venv.sh / start.bat / start.sh / .env.example / .gitignore（基础文件）
- docker-compose.yml（如有需要保留）

**归档清单**（一次性脚本）：
cleanup_rss.py / cleanup_rss_remaining.py / cleanup_unusable.py / cleanup_dead_empty.py / cleanup_false_success.py / batch_clean_dead_sources.py / test-real-biquge.py / test-rss-single.py / ws_test.py / ws_test2.py / ws_quick_test.py / device_test.py / device_api_test.py / e2e_test.py / find_accessible_js_sources.py / test_site_access.py / test_toc_analysis.py / verify_accessible_sources.py / verify_qidian_full.py / quick-test-sources.py / fix_rule_articles.py / fix_search_failed.py / deep_fix_search.py / smart_fix.py / dom_fix.py / retest_timeout.py / deep-analyze-js.py / deep_analysis.py / deep_verify.py / batch_device_debug.py / batch_optimize.py / concurrent_test.py / smart_dedup_v3.py / smart_merge_v4.py / auto_fix_sources.py / check_counts.py / check_device.py / cross_feed_search.py / debug-single.py / diagnose-failures.py / final_verify.py / generate-js-doc.py / run-full-regression.py / cross_feed_search.py / dedup-v3 相关 / cleanup 相关 / find_legado.py / alter_columns.py / audit_quality.py 等

**实现**：
1. 列出所有归档脚本（用 Glob `scripts/*.py` 然后筛选）
2. 批量 Move-Item 到 archive/oneoff-scripts/
3. 检查保留的9个核心脚本依赖是否断裂
4. 修复 SKILL.md 中对归档脚本的引用

**验收**：
- Glob 确认 scripts/ 根目录只剩9个核心脚本+基础文件
- 运行 `python scripts/debug-source.py --help` 不报错

## Step 2: 修复（AC-4）

### T4: 修复 Python None 序列化 bug

**输入**：T1-T3 完成
**输出**：
- 找到生成源 JSON 的代码位置
- 修复 None 值处理
- 增加单元测试覆盖

**实现**：
1. Grep 搜索生成源 JSON 的代码：`json.dumps` / `source.*json` / `rss.*source` 在 legado_client/ 下
2. 找到生成 RssSource JSON 的代码位置
3. 添加 None 值过滤：
   ```python
   def sanitize_source_json(source_dict):
       """过滤 None 值，避免序列化为字符串 'None'"""
       return {k: ('' if v is None else v) for k, v in source_dict.items() if v is not None}
   ```
4. 或在 json.dumps 时使用：
   ```python
   json.dumps(source_dict, ensure_ascii=False, default=lambda x: '' if x is None else str(x))
   ```
5. 增加单元测试 `test_sanitize_source_json`：
   - 测试 None 值被过滤
   - 测试空字符串保留
   - 测试正常值保留
6. 在 test_auto_fixer.py 或新建 test_source_serializer.py 中添加测试

**验收**：
- 单元测试通过
- 生成的 JSON 中无字符串 "None"

### T5: 新增 skill_e2e_test.py

**输入**：T4 完成
**输出**：
- `ai_tests/scripts/skill_e2e_test.py` 新文件
- E2E 测试能验证"AI生成源→真机导入→真机加载"

**实现**：
1. 参考 fixed_test_workflow.md SOP
2. 脚本结构：
   ```python
   """
   skill E2E 测试：AI 生成源 → 真机导入 → 真机加载验证

   用法：
     python ai_tests/scripts/skill_e2e_test.py --url {URL} [--type rss|book] [--source-name {name}]

   流程：
     1. 调用 skill 生成源 JSON（通过 debug-source.py 或直接构造）
     2. 编译+安装 APK（调用 quick_build_install.py）
     3. 导入源到真机（调用 import_rss_source.py）
     4. 真机加载验证（调用 l2_verify_video_player.py）
     5. 输出验证报告
   """
   import argparse
   import subprocess
   import json
   from pathlib import Path

   # 复用 ai_tests/config.py 常量
   import sys
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
   from config import ADB_PATH, MEMUC_PATH, MEMU_ADB_HOST

   def generate_source_json(url, source_type='rss', source_name='e2e_test'):
       """调用 skill 生成源 JSON"""
       # 调用 debug-source.py 或直接构造源 JSON
       ...

   def import_to_device(json_path):
       """调用 import_rss_source.py 导入到真机"""
       ...

   def verify_load(source_name):
       """真机加载验证"""
       ...

   def main():
       parser = argparse.ArgumentParser()
       parser.add_argument('--url', required=True, help='目标站点URL')
       parser.add_argument('--type', default='rss', choices=['rss', 'book'])
       parser.add_argument('--source-name', default='e2e_test')
       args = parser.parse_args()

       # 1. 生成源 JSON
       json_path = generate_source_json(args.url, args.type, args.source_name)

       # 2. 检查 JSON 无 "None" 字符串
       with open(json_path) as f:
           content = f.read()
       if '"None"' in content:
           print('[FAIL] JSON 含字符串 "None"')
           return 1

       # 3. 导入到真机
       import_to_device(json_path)

       # 4. 真机加载验证
       result = verify_load(args.source_name)

       # 5. 输出报告
       print(json.dumps(result, indent=2, ensure_ascii=False))
       return 0 if result['success'] else 1

   if __name__ == '__main__':
       sys.exit(main())
   ```
3. 实现各函数
4. 测试运行：`python ai_tests/scripts/skill_e2e_test.py --url {测试URL}`

**验收**：
- 脚本能运行
- 报告包含：列表加载成功/失败、播放/正文加载成功/失败、错误码

## Step 3: 文档（AC-2 + AC-3 + AC-5）

### T6: 合并 references/ 重复文档

**输入**：T1-T5 完成
**输出**：
- references/ 文档数从 85 减少到 ≤25
- 重复主题合并

**合并方案**：
1. CF 盾绕过 3→1：
   - 合并 `references/special-scenarios/cf-bypass.md` + `references/site-features/cf-shield-pattern.md` + `references/source-analysis/cf-bypass-source.md`
   - 输出：`references/special-scenarios/cf-bypass.md`（合并版）
2. 加密/解密 4→1：
   - 合并 `references/special-scenarios/encryption.md` + `references/js-patterns/crypto-patterns.md` + `references/troubleshooting/crypto-traps.md` + `references/js-extensions/crypto-encoding.md`
   - 输出：`references/special-scenarios/encryption.md`（合并版）
3. RSS 源 4→2：
   - 合并 `rss-basic.md` + `rss-core-diff.md` → `rss-basic.md`
   - 合并 `rss-advanced.md` + `rss-advanced.md`（去重）→ `rss-advanced.md`
4. 视频播放 5→1：
   - 合并 `video-audio.md` + `auto-video-player.md` + `hls-player.md` + `inject-video-player.md`
   - 输出：`references/special-scenarios/video-audio.md`（合并版）
5. JS 陷阱 5+→2：
   - 合并 `rhino-js-traps.md` + `common-traps.md` → `js-traps.md`
   - 合并 `rule-js-patterns.md` + `url-js-patterns.md` + `method-frequency.md` → `js-patterns.md`
6. 验证码 2→1：
   - 合并 `captcha.md` + `search-advanced.md` 验证码部分 → `captcha.md`

**实现**：
1. 对每个主题，先读取所有源文档
2. 合并去重（保留有用内容，删除冗余）
3. 写入新文档
4. 删除原重复文档
5. 更新 references/_INDEX.md 索引

**验收**：
- Glob 确认 references/ 文档数 ≤25
- Grep 计算总行数 ≤6,000

### T7: 精简 SKILL.md

**输入**：T1-T6 完成
**输出**：
- SKILL.md 行数 ≤200 行
- 流程从 6 阶段改为 3 阶段
- 陷阱速查表精简到 ≤20 条
- 移除强制 PHASE_X_COMPLETE
- JVM 标注为可选

**实现**：
1. 重写 SKILL.md，结构：
   ```
   # Legado 书源/订阅源智能创建器（v3）
   ---
   ## 触发条件（5条）
   ## 源类型快速决策（书源/订阅源）
   ## 陷阱速查表（精选20条）
     A. JS/Rhino（5条）
     B. 源类型/字段（5条）
     C. URL/网络（5条）
     D. 高频陷阱补充（5条）
   ## 3阶段工作流
     Phase 1: 分析网站
     Phase 2: 生成规则
     Phase 3: 真机验证（强制）
   ## 触发字段源码验证（保留Phase 0核心思想）
   ## 核心脚本表（9个）
   ## 参考文档索引（精简）
   ```
2. 移除章节：
   - L3 经验引擎详细规范（保留简化版）
   - JVM 测试基础设施详细声明
   - Phase 0-5 6阶段闭环
   - 任务后审计
   - 与其他 Skill 的关系
   - 订阅源核心差异（合并到 Phase 2）
   - 修复请求流程
   - 输出目录
   - 参考文档索引（精简保留）
   - 测试脚本表（精简保留）
   - JVM 工具
   - 辅助工具（11个）
   - Python 客户端 3.0 新功能
   - 不实现清单
   - 能力边界
   - 批量操作工具清单
   - 经验引擎详细规范
   - WebSocket 调试 API 速查
3. 移除强制 `[PHASE1_COMPLETE]` 等标记
4. 移除"首选 JVM 仿真"表述，改为"JVM 可选"

**验收**：
- Read SKILL.md 确认行数 ≤200
- Grep "PHASE.*COMPLETE" 确认已移除
- Grep "首选.*JVM" 确认已移除

### T8: 删除 AI_README.md

**输入**：T7 完成
**输出**：
- AI_README.md 删除
- 有用内容已合并到 SKILL.md

**实现**：
1. 读取 AI_README.md 的有用内容（脚本使用指南）
2. 合并到 SKILL.md 的"核心脚本表"
3. DeleteFile AI_README.md

**验收**：
- LS 确认 AI_README.md 已删除
- SKILL.md 包含原 AI_README.md 的脚本使用指南

## Step 4: 验证（AC-6 最终验收）

### T9: 真机 E2E 验证

**输入**：T1-T8 完成
**输出**：
- 完整真机 E2E 验证报告
- AC-6 全部通过

**实现**：
1. 编译+安装 APK：`python ai_tests/scripts/quick_build_install.py`
2. AI 通过 v3 skill 生成一个订阅源 JSON（指定站点）
3. 检查 JSON 无字符串 "None"
4. 导入到真机：`python ai_tests/scripts/import_rss_source.py {json_path}`
5. 真机加载验证：`python ai_tests/scripts/l2_verify_video_player.py --scenario all`
6. 日志分析：`python ai_tests/scripts/swipe_test_log.py analyze`
7. 输出验证报告：
   - 列表加载成功（条目数 ≥5）
   - 播放/正文加载成功
   - 无 ReferenceError / NullPointerException
   - 整个流程无需用户介入

**验收**（AC-6 全部通过）：
- [ ] AI 通过 v3 skill 生成一个订阅源 JSON
- [ ] 导入真机后无需手动修补 DB
- [ ] 真机加载列表成功（条目数 ≥5）
- [ ] 真机播放/正文加载成功
- [ ] 无 ReferenceError / NullPointerException 等错误
- [ ] 整个流程无需用户介入

## 任务依赖关系

```
T1 (创建归档目录)
  ↓
T2 (归档无关功能) ──── T3 (归档一次性脚本)
  ↓                       ↓
T4 (修复 None bug) ─── T5 (新增 E2E 测试)
  ↓                       ↓
T6 (合并 references/) ─── T7 (精简 SKILL.md) ─── T8 (删除 AI_README.md)
                                                ↓
                                            T9 (真机 E2E 验证)
```

## 风险与缓解

| 任务 | 风险 | 缓解 |
|------|------|------|
| T2-T3 归档 | 引用断裂 | Grep 检查 + 修复 SKILL.md 引用 |
| T4 修复 None bug | 修复不完整 | 增加单元测试 + E2E 验证 |
| T5 E2E 测试 | 测试环境不稳定 | 重试机制 + 详细日志 |
| T6 合并 references/ | 内容丢失 | 合并前备份 + 人工审查 |
| T7 精简 SKILL.md | 关键信息丢失 | 保留精选20陷阱 + 详细陷阱迁到 references/ |
| T9 真机 E2E | 真机环境不稳定 | 重试机制 + 失败时输出详细日志 |
