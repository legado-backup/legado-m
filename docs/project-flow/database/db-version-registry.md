# 数据库版本占号权威源（db-version-registry）

> 建立依据：master-track-orchestration AD-02（2026-08-31）。本文件是跨 spec DB 版本占号的**唯一权威源**。
> 建立时基线：AppDatabase.kt 实测 `version = 109`（video-sniff 4.8e 方案 A 已落地 v109，migration_108_109 已合入）。

## 占号规则（铁律）

1. **占号 ≠ 写死版本号**：任何含 DB 变更的分期，实施时以 `AppDatabase.kt` 实际 `version + 1` 为准，禁止在实施 spec 中写死设计期规划号
2. **先合先得**：先落地合入的分期占用下一个版本号，后来者自适应顺延（本规则已在 video-sniff 4.8e 实占 v109 时生效）
3. **强制查表**：各分期实施 spec 开工前（总线 R7 门禁）必须查本表占号，占号后回写状态
4. **回退联动**：分期回退时同步回滚占号状态，并重算依赖分期的顺延号（tasks 8.4.4）
5. **审批**：单人场景执行者自批+回执留痕，检查点抽查

## 占号表

| 期名 | 触发条件 | 实施时 version 基线 | 迁移内容 | 占号状态 |
|------|---------|-------------------|---------|---------|
| video-sniff 4.8e（V 轨） | 用户裁决方案 A（PlayHistory 主键加 rssSourceId） | v108 → v109（已落地） | migration_108_109 playHistories 表重建 | **已实占 v109**（2026-08-31 已合入，schemas/109.json 已导出） |
| ng P1 AI 地基 | P1 实施 spec 开工（W2） | 实施时实际值 +1（规划 v109 → **顺延 v110**） | 3 新表（ai_chat_sessions/ai_chat_messages/ai_compaction_records）+ 108→109 旧 JSON 一次性导入器顺延 | 预占（顺延 v110） |
| ng P3 多角色听书 | P3 实施 spec 开工（W4，前置 P0 合入+DD3 评审） | 实施时实际值 +1（规划 v110 → **顺延 v111**） | 6 新表（workProfiles/workCharacters/workTtsCastRoles/workTtsBindings/ttsVoices/ttsEngineRuntime，FK 级联） | 预占（顺延 v111） |
| B-C2 多媒体插入 | C2 实施 spec 开工（W3，前置 OQ-1 裁决） | 实施时实际值 +1 | 1 新表（book_illustrations 媒体锚点） | 预占（实施时占号） |
| B-C3 合集书架 | C3 实施 spec 开工（W5，前置 B2 样板冻结） | 实施时实际值 +1 | 4 新表（BookCollection 四表+DAO） | 预占（实施时占号） |
| C4 AI 净化 | C4 一期实施（W5） | 无 schema 变更（SHA-256 指纹进现有 ReplaceRule 体系） | 无 migration | 无需占号 |
| ng P2 MCP | P2 实施 spec 开工（W3） | 无 schema 变更（仅 SP 5 键+SearchBookDao @Query，免 migration） | 无 migration | 无需占号 |

## 变更记录

- 2026-08-31：本文件建立；v109 实占条目（video-sniff 4.8e）登记；ng P1/P3/B-C2/B-C3 预占（tasks 1.2 核销）
- 2026-09-01：总线 3.2.1 完成——P1 实施 spec 另立（`docs/specs/ng-p1-ai-foundation/README.md`），复核 v109 实占基线（AppDatabase version=109 实测一致）；P1 维持"预占（顺延 v110）"，T7 DB 实施时实占（步骤清单见该 spec §1）
