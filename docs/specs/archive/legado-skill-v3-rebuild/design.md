# legado-source-creator Skill v3 全面重构 - Design

> 本文档定义 v3 全面重构的技术方案和架构决策（ADR）。

## 1. 架构决策（ADR）

### ADR-1: 归档策略——不删除，归档到 archive 目录

**决策**：所有砍掉的功能和脚本归档到 `.trae/skills/legado-source-creator-archive/`，保留 30 天回退窗口。

**理由**：
- 用户可能依赖某个被砍掉的功能
- 归档而非删除降低风险
- 30 天后用户未提出回退需求，再彻底删除

**实现**：
```
.trae/skills/legado-source-creator-archive/
  README.md                            # 归档说明（含归档日期+回退方法）
  web/                                  # Vue3 前端（从 legado_client/web/ 移动）
  storage/                              # 数据库存储层（从 legado_client/storage/ 移动）
  alembic/                              # Alembic 迁移（从 scripts/alembic/ 移动）
  server/                               # FastAPI 服务（从 legado_client/server/ 移动）
  device/                               # 设备管理（从 legado_client/device/ 移动）
  oneoff-scripts/                       # 一次性脚本（从 scripts/ 根目录的83%脚本移动）
  unused-tools/                         # 无关辅助工具（11个中无关的）
```

**归档清单**（一次性脚本，按子代理报告）：
- cleanup×6（cleanup_rss.py / cleanup_rss_remaining.py / cleanup_unusable.py / cleanup_dead_empty.py / cleanup_false_success.py / batch_clean_dead_sources.py）
- test×8（test-real-biquge.py / test-rss-single.py / ws_test.py / ws_test2.py / ws_quick_test.py / device_test.py / device_api_test.py / e2e_test.py / find_accessible_js_sources.py / test_site_access.py / test_toc_analysis.py / verify_accessible_sources.py / verify_qidian_full.py / quick-test-sources.py）
- fix×6（fix_rule_articles.py / fix_search_failed.py / deep_fix_search.py / smart_fix.py / dom_fix.py / retest_timeout.py）
- verify×6（verify-source.py / verify-decrypt.py / verify-image.py / verify-selector.py / quick-verify.py / find_legado.py / verify-source.py 等，保留9个核心，其余归档）
- deep×4（deep-analyze-js.py / deep_analysis.py / deep_verify.py / deep-analyze-js.py）
- batch×3（batch_device_debug.py / batch_optimize.py / concurrent_test.py）
- smart×3（smart_dedup_v3.py / smart_merge_v4.py / smart_fix.py）
- 其他一次性（analyze_site.py / auto_fix_sources.py / batch_clean_dead_sources.py / check_counts.py / check_device.py / cross_feed_search.py / debug-single.py / diagnose-failures.py / final_verify.py / generate-js-doc.py / quick-verify.py / run-full-regression.py / setup.py / smart_dedup_v3.py 等）

### ADR-2: 流程精简策略——3 阶段替代 6 阶段

**决策**：把 6 阶段闭环（Phase 0-5）+ 任务后审计，精简为 3 阶段闭环。

**理由**：
- 6 阶段流程过重，AI 容易在中途"思考上限"
- 81 条陷阱实际命中率仅 37%，大量低频陷阱无价值
- 强制 PHASE_X_COMPLETE 标记增加 token 消耗无实际收益
- 双写规范过度工程化

**新流程**：
```
Phase 1: 分析网站（5个步骤）
  1.1 curl/Playwright 获取 HTML
  1.2 判断类型（HTML/JSON/SPA/RSS）
  1.3 检测特殊场景（CF/登录/加密/视频）
  1.4 触发字段时强制源码验证（保留Phase 0核心思想）
  1.5 输出 [分析完成] 简要标记（非强制完整检查清单）

Phase 2: 生成规则（4个步骤）
  2.1 按类型套模板（书源5组规则/订阅源扁平字段）
  2.2 处理特殊场景（CF/登录/加密/视频）
  2.3 输出 JSON 到 output/
  2.4 预校验字段完整性和规则语法（保留source_validator+rule_precheck）

Phase 3: 真机验证（强制，4个步骤）
  3.1 import_rss_source.py 导入到真机
  3.2 真机加载验证（列表+播放/正文）
  3.3 失败 → 回 Phase 2 修复（最多重试3次）
  3.4 成功 → 写入 basic-memory 经验（简化双写：只写basic-memory，不强制更新Skill文档）
```

**保留**：
- Phase 0 核心思想（触发字段强制源码验证）
- source_validator + rule_precheck 预校验
- basic-memory 经验反哺（简化）

**移除**：
- 强制 `[PHASE_X_COMPLETE]` 输出标记（改为简要 [分析完成] / [生成完成] / [验证完成]）
- 任务后审计（legado-workflow-auditor）
- 4 级可信度分层 → 2 级（已验证/需真机验证）
- 复杂的双写规范
- 代码进化机制（保留单点修复）

### ADR-3: JVM 降级策略——可选调试工具

**决策**：JVM 降级为可选工具，默认走真机 E2E 验证。

**理由**：
- JVM 85-90% 覆盖率但不覆盖 WebView/Cookie/Activity（恰好出错最多）
- 上轮 None 序列化 bug JVM 测不出来
- 维护 96 个未实现函数 mock 负担重

**实现**：
- SKILL.md 移除"首选 JVM 仿真"表述
- mock-unimplemented-functions.md 标注"JVM 可选，不再强制维护"
- 保留 legado-jvm/build/libs/legado-jvm.jar + tools/rule_engine_client.py + tools/jvm_helpers.py
- debug-source.py 默认走 Python 模式（移除 JVM 优先逻辑）
- JVM 仅作为"调试复杂 JS"的可选工具（如加密解密、复杂规则）

### ADR-4: E2E 测试设计

**决策**：新增 `ai_tests/scripts/skill_e2e_test.py` 端到端测试。

**实现**：
```python
# ai_tests/scripts/skill_e2e_test.py
"""
skill E2E 测试：AI 生成源 → 真机导入 → 真机加载验证

用法：
  python ai_tests/scripts/skill_e2e_test.py --url {目标站点URL} [--type rss|book]

流程：
  1. 调用 skill 生成源 JSON（通过 debug-source.py 或直接构造）
  2. 编译+安装 APK（quick_build_install.py）
  3. 导入源到真机（import_rss_source.py）
  4. 真机加载验证（l2_verify_video_player.py）
  5. 输出验证报告

验证项：
  - 列表加载成功（条目数 ≥5）
  - 播放/正文加载成功
  - 无 ReferenceError / NullPointerException
  - DB 中字段无字符串 "None"
"""
```

**修复 None 序列化 bug**：
- 找到 skill 生成源 JSON 的代码位置（可能是 experience_manager.py / debug_runner.py / 生成模板）
- 所有 None 值字段必须输出为空字符串 "" 或不输出该字段
- 增加 JSON 序列化的 None 处理单元测试

**测试断言自动同步机制**：
- 新增 `scripts/check_test_sync.py`：检查代码改动是否同步改测试
- 任何 .py 代码改动必须同时改对应的 test_*.py
- CI 或 pre-commit 钩子拦截不同步的改动

### ADR-5: 文档合并策略

**决策**：references/ 合并去重，从 85 文档减少到 ≤25 文档。

**合并方案**：
| 主题 | 当前 | 合并后 |
|------|------|--------|
| CF 盾绕过 | cf-bypass.md / cf-shield-pattern.md / site-features/cf-shield-pattern.md | cf-bypass.md（合并3→1） |
| 加密/解密 | encryption.md / crypto-patterns.md / crypto-traps.md / crypto_analyzer.py 参考 | encryption.md（合并4→1） |
| RSS 源 | rss-basic.md / rss-advanced.md / rss-core-diff.md / rss-advanced.md | rss-basic.md + rss-advanced.md（合并4→2） |
| 视频播放 | video-audio.md / auto-video-player.md / hls-player.md / inject-video-player.md / templates/ | video-audio.md（合并5→1） |
| JS 陷阱 | rhino-js-traps.md / common-traps.md / rule-js-patterns.md / url-js-patterns.md / method-frequency.md | js-traps.md + js-patterns.md（合并5+→2） |
| 验证码 | captcha.md / search-advanced.md 部分 | captcha.md（合并2→1） |

**SKILL.md 精简方案**：
- 当前 738 行 → 目标 <200 行
- 保留：核心流程（3阶段）+ 精选20陷阱 + 核心脚本表 + 触发字段源码验证
- 移除：能力边界声明 / 经验引擎详细规范 / 代码进化机制详细流程 / 任务后审计 / 辅助工具清单 / Python客户端3.0新功能 / WebSocket调试API速查 / 批量操作工具清单

**AI_README.md 处理**：
- 删除 AI_README.md
- 有用的内容（脚本使用指南）合并到 SKILL.md 的"核心脚本表"
- 其余内容归档

### ADR-6: None 序列化 bug 修复方案

**决策**：找到 skill 生成源 JSON 的代码位置，修复 None 值处理。

**根因**：
- skill v2 生成源 JSON 时，Python 的 None 被错误序列化为字符串 "None"
- 字段 loginCheckJs 和 sortUrl 值为字符串 "None"
- Rss.kt:64 检查 `!checkJs.isNullOrBlank()` → 字符串 "None" 非空 → 当作 JS 执行 → ReferenceError

**修复方案**：
- 找到生成源 JSON 的代码（可能是 experience_manager.write_pending / debug_runner / 模板）
- 在 JSON 序列化前过滤 None 值：
  ```python
  def sanitize_source_json(source_dict):
      """过滤 None 值，避免序列化为字符串 'None'"""
      return {k: ('' if v is None else v) for k, v in source_dict.items()}
  ```
- 或在 json.dumps 时使用 `ensure_ascii=False, default=lambda x: '' if x is None else str(x)`
- 增加单元测试覆盖

## 2. 实施顺序

按依赖关系排序：

```
Step 1: 创建归档目录 + 归档无关功能（AC-1 部分）
  ↓
Step 2: 归档一次性脚本（AC-1 部分）
  ↓
Step 3: 修复 None 序列化 bug（AC-4 部分）
  ↓
Step 4: 新增 skill_e2e_test.py（AC-4 部分）
  ↓
Step 5: 合并 references/ 重复文档（AC-5 部分）
  ↓
Step 6: 精简 SKILL.md + 删除 AI_README.md（AC-2 + AC-3 + AC-5）
  ↓
Step 7: 真机 E2E 验证（AC-6 最终验收）
```

## 3. 风险与缓解（详细）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 归档破坏现有 skill 功能 | 中 | 高 | 在新分支重构 + 归档后立即测试核心功能 |
| SKILL.md 精简后 AI 缺少关键信息 | 低 | 中 | 保留精选20陷阱 + 把详细陷阱迁到 references/ |
| E2E 测试环境不稳定 | 中 | 中 | E2E 测试包含重试机制 + 失败时输出详细日志 |
| None 序列化 bug 修复不完整 | 低 | 高 | 增加单元测试覆盖 + 真机 E2E 验证 |
| references/ 合并后内容丢失 | 低 | 中 | 合并前备份 + 合并后人工审查关键内容 |
