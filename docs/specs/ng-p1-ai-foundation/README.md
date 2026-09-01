# ng P1 AI 地基 — 实施 spec（轻量执行账本）

> **权威账本**：[P1-ai-foundation.md](../ng-benchmark-analysis/migration-designs/P1-ai-foundation.md)（第三轮深化实施级设计，含 §4.2 J1-J9 注入点、§6 DDL、§10 T1-T11 实施顺序、§9 测试设计）。本 README **不复制设计内容**，只登记占号结论、执行清单进度与实施期注意事项。
> **总线任务**：master-track tasks 3.2（W2）。**分支**：feat/master-track-waves。
> **建立**：2026-09-01（总线 3.2.1）。

---

## 1 占号结论（db-version-registry 联动）

| 项 | 状态 |
|---|---|
| 基线复核 | `AppDatabase.kt:126 version = 109`（video-sniff 4.8e 已实占，schemas/109.json 已导出）✓ 2026-09-01 实测 |
| P1 规划号 | v109（分册标题口径，已被 4.8e 抢占） |
| **P1 实施号** | **顺延 v110**（registry 预占行已登记；依据 AD-02 先合先得规则） |
| 占号状态 | **预占（顺延 v110）→ DB 实施（T7）时实占**；3.2.1 阶段不动 AppDatabase |

**T7 实占步骤（DB 实施会话执行）**：
1. `AppDatabase.kt` `version = 109 → 110`；`@Database` entities 追加 `AiChatSession` / `AiChatMessageNode`（注意实体命名，规避与 `ui.main.ai.AiChatMessage` 撞名）/ `AiCompactionRecord` 三实体 + `aiChatDao` 注册；
2. `DatabaseMigrations.kt` 追加 `migration_109_110`（分册 §6.2 草案，起点号按 registry 铁律以实施时 version-1 为准）：3 表 DDL 全列显式 defaultValue（与 `@ColumnInfo(defaultValue=...)` 逐列一致）+ OQ-7 旧 `aiChatSessionList` JSON 一次性导入器（上限 100 条，runCatching 兜底，成功后旧 key 冻结只读不删）；
3. 编译产出 `app/schemas/110.json` → diff 审查逐列一致后随代码一并提交（迁移审计物）；
4. 遵循 `docs/project-flow/database/database-migration-safety.md`：只增不改不删；`fallbackToDestructiveMigrationFrom(false, 1..9)` 仅覆盖 v1-9 远古链（AppDatabase.kt:118 实测），v109→v110 主线为手动 Migration，无破坏性回退路径 ✓；
5. 真机覆盖安装验证（R5，测试包 `io.legado.miss.app.debug`）。

**并行会话冲突登记**（⚠️ 工作区改动清单：App.kt / AnalyzeRule.kt / AnalyzeUrl.kt / MoreConfigDialog.kt / BottomWebViewDialog.kt / AGENTS.md / quick_build_install.py / RssFragment.kt）：`AppDatabase.kt` 不在清单内，T7 可直接实施；若实施日清单更新包含 AppDatabase.kt / DatabaseMigrations.kt，则登记等待。

## 2 执行清单（子任务账本 = P1 分册）

| 任务 | 内容 | 状态 |
|---|---|---|
| 3.2.1 | 本 spec 另立 + registry 占号留痕 | ✅ 2026-09-01 |
| 3.2.2 | 密钥防线四层先落地（P2 前置，分册 §4.6/D15） | ✅ 2026-09-01（见 §3） |
| 3.2.3 | 分册补注"AiChatService 冻结=不修改既有方法，新增方法不受限"（C4 衔接） | ✅ 2026-09-01（已写入分册 §3.4） |
| T1-T11 | P1 全量实施（provider 子包 / Config v2 / Store / 3 Provider / AiManager+Registry / DB v110 / compress 4 类 / UI 增量 / L3 真机） | ⬜ 按 P1 分册 §10 依赖图推进，双门禁=每步「编译通过+对应单测绿」 |

## 3 密钥防线四层实施记录（3.2.2 已落地部分）

以分册 §4.6 实际设计为准（传输记录层/静态存储层/应用日志层/外发出口层）：

| 层 | 设计 | 状态 | 落点 |
|---|---|---|---|
| ① 传输记录层 | NetworkLog `sensitiveHeaderNames` 补 `x-goog-api-key`（A1-4 HIGH） | ✅ 已落地 | `NetworkLog.kt:36`；单测 `NetworkLogTest.formatHeaders_redactsGeminiApiKeyHeader`（双大小写形态断言；归属自 AiProviderHttpProtocolTest 前移至既有测试类，该类属 T1 尚不存在） |
| ② 静态存储层 | `aiProviderList` 备份 AES 加密（A1-1/A1-2 HIGH，复用 webDavPassword 先例，防双实现漂移） | ✅ 已落地 | `BackupAES.sensitivePrefKeys` 单一权威源（新增 companion）；`Backup.kt` 本地/WebDav 导出、`Restore.kt` 导入（对称解密+明文回退，回退判断泛化为当前 key）、`BackupController.kt` Web 导出三处接入；**Web 端点缺 `keyIsNotIgnore` 过滤的不一致缺口同步补齐** |
| ③ 应用日志层 | AppLog 禁 raw/禁 apiKey（J9/E18） | ✅ 规范约束（无代码改动） | T1+ 新增代码遵守 logging_rules；AppLog.TAG_AI 随 T1 落地 |
| ④ 外发出口层 | P2 MCP Sanitizer | ⬜ P2 落地 | P2 分册；①层已使 P2 前本地抓包记录不含密钥 |

## 4 实施期注意事项（后续会话必读）

1. **编译门禁**：`$env:GRADLE_USER_HOME="F:\gh"; .\gradlew compileAppDebugKotlin`（`assembleAppDebug` 产出 schema json）；构建后 `.\stop-daemons.bat` 清场（门禁 §6）。
2. **Room schema**：kapt/ksp 编译产出 `app/schemas/110.json`，与代码同批提交。
3. **updateLog**：AI 地基基础设施（provider 层/压缩/DB/防线）用户不可见→不追加；T10 UI 增量（协议下拉/测试连接/预设导入）为用户可见功能→届时按 version-delivery-sync 追加。
4. **真机测试包**：`io.legado.miss.app.debug`（代码优化任务，禁用正式包）。
5. **规范回灌**（分册 §10 末段）：T 系列完成后执行 ① sanitize 双闸→checkstyle_rules、② runCatchingSql 收敛→database-migration-safety、③ CancellationException rethrow→exception_rules 三项回灌。
6. **测试**：单测 6 类 37 方法（分册 §9，JVM）；L2 脚本 `ai_tests/scripts/l2_verify_ai_provider.py`（预登记名）；L3 三轮真机（迁移覆盖装/预设导入测试连接/压缩审计）。
