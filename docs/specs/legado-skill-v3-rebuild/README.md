# legado-source-creator Skill v3 全面重构

> 本目录是 legado-source-creator skill 的 v3 全面重构 OpenSpec 文档。
> **触发原因**：用户对 v2 优化效果极度不满，要求深度分析根因和优化方向，并选择"全面重构"。

## 文档导航

| 文档 | 内容 | 状态 |
|------|------|------|
| [README.md](./README.md) | 入口+背景+目标+范围（本文件） | ✅ |
| [spec.md](./spec.md) | 需求+验收标准+证据链 | 待用户确认 |
| design.md | 技术方案+架构决策 | 待 spec 确认后写 |
| tasks.md | 任务清单 | 待 design 确认后写 |

## 背景

### 用户痛点（原话）

> "我非常不满意生成书源订阅源skill干活！你需要深度分析一下为什么，如何优化"

### 上轮真机验证暴露的问题

1. **Python None → 字符串 "None" 序列化 bug**：skill v2 生成源 JSON 时把 Python None 错误序列化为字符串 "None"，导致 Rss.kt:64 把 "None" 当 JS 执行，触发 ReferenceError
2. **v2 修复后测试断言未同步**：5 处 test_auto_fixer.py 断言 + 1 处自检断言遗漏
3. **真机验证靠子代理手动修补 DB**：skill 不能"开箱即用"

### 深度诊断（5 大根因）

详见 [../../temp-analysis/skill_root_cause_diagnosis.md](../../temp-analysis/skill_root_cause_diagnosis.md)

1. **职责膨胀失控**【最严重】skill 变成全栈管理系统（Vue3+MySQL+FastAPI+设备管理+批量清理+11工具+100+脚本）
2. **流程过度工程化** 6 阶段闭环 + 81 条陷阱（实际 52 条缺口 29）+ 强制 PHASE_X_COMPLETE + 双写规范 + 任务后审计
3. **JVM 仿真价值不匹配** 85-90% 覆盖率但不覆盖 WebView/Cookie/Activity（恰好出错最多）
4. **代码与文档严重脱节** SKILL.md 自述 488 实际 738 行；None 序列化 bug 不在任何陷阱列表
5. **缺乏端到端集成测试** 有 12 个单元测试，但缺"AI生成源→真机导入→真机加载"E2E测试

### 子代理精确统计证据

| 报告 | 关键指标 |
|------|---------|
| [scripts_bloat_report.md](../../temp-analysis/scripts_bloat_report.md) | 116 个 .py 文件 / ~30k 行 / 83.3% 一次性脚本 / 11 组重复 / 4 个被引用脚本不存在 |
| [references_bloat_report.md](../../temp-analysis/references_bloat_report.md) | 85 个 .md 文件 / ~14k 行 / 高频陷阱仅 37% / 真机场景命中率 15% / 39% 重复主题 |

## v3 重构目标

### 核心目标

**让 skill 重新聚焦"生成可用源 JSON"核心目标，让 AI 生成源"开箱即用率 ≥90%"**

### 5 个优化方向（用户已选"全面重构"）

| # | 方向 | 当前状态 | 目标状态 |
|---|------|---------|---------|
| 1 | 职责收敛 | 116 脚本+Web界面+数据库+CLI+设备管理+11工具 | ~20 核心脚本，砍掉无关功能 |
| 2 | 流程精简 | 6 阶段闭环+81 陷阱+PHASE_X_COMPLETE+双写+审计 | 3 阶段（分析→生成→真机验证）+ 20 精选陷阱 |
| 3 | JVM 降级可选 | 默认"首选 JVM 仿真" | 默认走真机 E2E，JVM 仅调试复杂 JS 时可选 |
| 4 | 补 E2E 测试 | 12 个单元测试，无 E2E | 新增"AI生成源→真机导入→真机加载"E2E + 修 None 序列化 bug |
| 5 | 文档瘦身 | SKILL.md 738 行 + AI_README.md 348 行 + references/ 85 文档 | SKILL.md <200 行 + references/ ~20 文档 |

## 范围

### IN SCOPE（v3 重构范围）

- `.trae/skills/legado-source-creator/SKILL.md` 主文档精简
- `.trae/skills/legado-source-creator/AI_README.md` 合并到 SKILL.md
- `.trae/skills/legado-source-creator/scripts/` 砍掉无关脚本（保留9个核心）
- `.trae/skills/legado-source-creator/references/` 合并去重
- `.trae/skills/legado-source-creator/templates/` 保留
- `.trae/skills/legado-source-creator/test-data/` 保留
- 修复 Python None 序列化 bug
- 新增 E2E 测试（AI生成源→真机导入→真机加载）

### OUT OF SCOPE（不在本次范围）

- 砍掉的功能不删除，而是**归档**到 `.trae/skills/legado-source-creator-archive/` 保留 30 天回退窗口
  - Web 管理界面（legado_client/web/）
  - 数据库存储层（legado_client/storage/ + alembic/）
  - FastAPI 服务（legado_client/server/）
  - 设备管理 + Legado HTTP/WebSocket 代理（legado_client/device/ + legado_client/server/routes/legado_proxy.py）
  - 批量清理脚本（batch_*.py / cleanup_*.py）
  - 11 个辅助工具中无关的（obstacle_resolver/crypto_analyzer/interactive_guide/cookie_manager/smart_http_client/knowledge_matcher/degradation_chain/workflow_timer/error_translator/user_action_minimizer）

## 验收标准

详见 [spec.md](./spec.md)

## 实施流程

按 OpenSpec 工作流：

1. **Spec 阶段**：写 spec.md（需求+验收+证据链）→ NotifyUser 让用户确认 ✅
2. **Plan 阶段**：写 design.md（技术方案+架构决策）→ NotifyUser 让用户确认
3. **Tasks 阶段**：写 tasks.md（任务清单）→ NotifyUser 让用户确认
4. **实施阶段**：按 tasks.md 实施 → 每阶段构建验证 → 完成后真机 E2E 验证
