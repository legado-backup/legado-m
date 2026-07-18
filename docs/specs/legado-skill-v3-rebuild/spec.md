# legado-source-creator Skill v3 全面重构 - Spec

> 本文档定义 v3 全面重构的需求、验收标准和证据链。

## 1. 需求

### 1.1 功能需求

#### FR-1 职责收敛：skill 重新聚焦核心目标

**需求**：skill 重新聚焦"生成可用源 JSON"核心目标，砍掉所有与核心目标无关的功能。

**实现**：
- 砍掉 Web 管理界面（legado_client/web/ Vue3 前端）
- 砍掉数据库存储层（legado_client/storage/ + alembic/ + MySQL/Alembic 迁移）
- 砍掉 FastAPI 服务（legado_client/server/）
- 砍掉设备管理 + Legado HTTP/WebSocket 代理（legado_client/device/ + server/routes/legado_proxy.py）
- 砍掉批量清理脚本（batch_*.py / cleanup_*.py / dead-sources 相关）
- 砍掉无关辅助工具（11个中无关的）
- 砍掉 100+ 一次性脚本（保留9个核心）
- **归档而非删除**：所有砍掉的功能归档到 `.trae/skills/legado-source-creator-archive/` 保留 30 天回退窗口

**保留**：
- SKILL.md（精简后）
- 9 个核心脚本：debug-source.py / verify-source.py / verify-selector.py / verify-decrypt.py / verify-image.py / analyze_site.py / quick-verify.py / html_fetcher.py / fetch_html.py
- references/（合并去重后约 20 个文档）
- templates/（视频播放器模板）
- test-data/（测试数据）
- 必要的工具模块（legado_client/utils/ + analyzer/auto_fixer.py + analyzer/error_diagnoser.py + analyzer/source_validator.py + analyzer/rule_precheck.py + client/debug_runner.py + client/rule_engine_client.py + experience/experience_manager.py）

#### FR-2 流程精简：6 阶段 → 3 阶段

**需求**：把过度工程化的 6 阶段闭环（Phase 0-5）+ 任务后审计，精简为 3 阶段闭环。

**当前流程**（删除）：
```
Phase 0 源码验证门禁
Phase 1 经验优先（search_notes + 陷阱速查 + references查阅）
Phase 2 构建规则（知识库强制查阅 + 网站分析 + 规则构建 + 预校验）
Phase 3 测试驱动（静态扫描 + debug-source.py + 可信度分层）
Phase 4 源码深挖（强制触发3类场景 + 工具辅助）
Phase 5 经验反哺 + 代码进化（双写规范 + 写basic-memory + 进化沉淀）
任务后审计（调用 legado-workflow-auditor）
```

**新流程**：
```
Phase 1: 分析网站
  - curl/Playwright 获取 HTML
  - 判断类型（HTML/JSON/SPA/RSS）
  - 检测特殊场景（CF/登录/加密等）
  - 触发字段时强制源码验证（保留Phase 0核心思想）

Phase 2: 生成规则
  - 按类型套模板（书源5组规则/订阅源扁平字段）
  - 处理特殊场景（CF/登录/加密/视频）
  - 输出 JSON 到 output/
  - 预校验字段完整性和规则语法

Phase 3: 真机验证（强制）
  - import_rss_source.py 导入到真机
  - 真机加载验证（列表+播放/正文）
  - 失败 → 回 Phase 2 修复
  - 成功 → 写入 basic-memory 经验（保留经验反哺）
```

**移除**：
- 81 条陷阱 → 精选 20 条最高频
- 强制 `[PHASE_X_COMPLETE]` 输出标记
- 复杂的双写规范（保留"先更新Skill文档再写basic-memory"原则，但简化流程）
- 任务后审计（legado-workflow-auditor 不再强制调用）
- 代码进化机制（保留JAR但简化）
- 可信度分层（4级可信度）→ 简化为"已验证/需真机验证"2级

#### FR-3 JVM 仿真降级为可选

**需求**：默认不依赖 JVM 仿真，直接走真机 E2E 验证。

**当前**（修改）：
- skill 文档标榜"首选 JVM 仿真"
- 维护 mock-unimplemented-functions.md 96 个未实现函数
- 代码进化机制复杂

**新策略**：
- JVM 降级为可选工具，仅调试复杂 JS 时使用
- 默认走"生成→真机导入验证"的端到端测试
- 保留 legado-jvm/build/libs/legado-jvm.jar + tools/rule_engine_client.py + tools/jvm_helpers.py
- 简化 mock-unimplemented-functions.md，标注"JVM 可选"
- 移除"代码进化机制"复杂流程，保留单点修复

#### FR-4 补端到端集成测试

**需求**：新增"AI 生成源 → 真机导入 → 真机加载"的自动化 E2E 测试。

**实现**：
- 新增 `ai_tests/scripts/skill_e2e_test.py`：
  - 输入：目标站点 URL
  - 输出：AI 生成源 JSON → 真机导入 → 真机加载验证报告
  - 验证项：列表加载、播放/正文加载、无 ReferenceError
- 修复 Python None 序列化 bug：
  - skill 生成源 JSON 的代码中，所有 None 值字段必须输出为空字符串或不输出该字段
  - 增加 JSON 序列化的 None 处理单元测试
- 增加"测试断言与代码实现自动同步"机制：
  - 任何代码改动必须同时改测试（通过 CI 或脚本检查）
  - 避免 v2 修复后断言未同步的问题

#### FR-5 文档瘦身

**需求**：精简文档，让 AI 聚焦核心信息。

**当前**：
- SKILL.md 738 行（自述 488 行）
- AI_README.md 348 行
- references/ 85 个文档，13,881 行
- 重复主题：CF（3个）/加密（4个）/RSS（4个）/视频（5个）/JS陷阱（5+个）/验证码（2个）

**新文档**：
- SKILL.md 精简到 <200 行（核心流程+精选20陷阱+核心脚本表）
- AI_README.md 合并到 SKILL.md（删除 AI_README.md）
- references/ 合并去重后约 20 个文档（合并CF→1/加密→1/RSS→2/视频→1/JS陷阱→2）
- references/_INDEX.md 重写为简洁索引

### 1.2 非功能需求

#### NFR-1 可维护性
- 代码与文档严格同步（任何代码改动必须同时改文档和测试）
- 不允许"SKILL.md 引用不存在的脚本"
- 一次性脚本必须有"删除日期"标注

#### NFR-2 可用性
- AI 生成源 JSON 后，**无需手动修补 DB 即可真机加载成功**（开箱即用率 ≥90%）
- 流程精简后，AI 生成一个源的总 token 消耗减少 ≥50%

#### NFR-3 回退性
- 所有砍掉的功能归档到 `.trae/skills/legado-source-creator-archive/` 保留 30 天
- 30 天后用户未提出回退需求，再彻底删除

## 2. 验收标准

### AC-1 职责收敛
- [ ] scripts/ 目录 .py 文件数从 116 减少到 ≤25（核心9个 + 必要模块~16个）
- [ ] legado_client/web/ / legado_client/storage/ / legado_client/server/ / legado_client/device/ 归档
- [ ] alembic/ 归档
- [ ] batch_*.py / cleanup_*.py / dead-sources 相关脚本归档
- [ ] 11 个辅助工具中无关的归档（保留 auto_fixer/error_diagnoser/source_validator/rule_precheck/experience_manager）
- [ ] 归档目录 `.trae/skills/legado-source-creator-archive/` 存在
- [ ] SKILL.md 不再引用归档功能

### AC-2 流程精简
- [ ] SKILL.md 流程章节从 6 阶段改为 3 阶段
- [ ] 陷阱速查表从 81 条精简到 ≤20 条（精选高频）
- [ ] 移除强制 `[PHASE_X_COMPLETE]` 输出标记
- [ ] 移除任务后审计（legado-workflow-auditor 调用）
- [ ] 可信度分层从 4 级简化为 2 级（已验证/需真机验证）

### AC-3 JVM 降级可选
- [ ] SKILL.md 移除"首选 JVM 仿真"表述
- [ ] JVM 标注为"可选调试工具"
- [ ] mock-unimplemented-functions.md 标注"JVM 可选，不再强制维护"
- [ ] 代码进化机制简化为单点修复

### AC-4 E2E 测试
- [ ] 新增 `ai_tests/scripts/skill_e2e_test.py`
- [ ] 修复 Python None 序列化 bug（增加单元测试覆盖）
- [ ] E2E 测试能自动验证"AI生成源→真机导入→真机加载"
- [ ] E2E 测试报告包含：列表加载成功/失败、播放/正文加载成功/失败、错误码

### AC-5 文档瘦身
- [ ] SKILL.md 行数 ≤200 行
- [ ] AI_README.md 删除（内容合并到 SKILL.md）
- [ ] references/ 文档数从 85 减少到 ≤25
- [ ] references/ 总行数从 13,881 减少到 ≤6,000
- [ ] 重复主题合并（CF 3→1/加密 4→1/RSS 4→2/视频 5→1/JS陷阱 5+→2）

### AC-6 真机 E2E 验证（最终验收）
- [ ] AI 通过 v3 skill 生成一个订阅源 JSON
- [ ] 导入真机后无需手动修补 DB
- [ ] 真机加载列表成功（条目数 ≥5）
- [ ] 真机播放/正文加载成功
- [ ] 无 ReferenceError / NullPointerException 等错误
- [ ] 整个流程无需用户介入

## 3. 证据链

每个验收标准的验证方法：

| AC | 验证方法 | 工具 |
|----|---------|------|
| AC-1 | Grep scripts/ 目录文件数 + LS 确认归档目录存在 | Glob + LS |
| AC-2 | Read SKILL.md 流程章节 + Grep "PHASE_X_COMPLETE" 确认已移除 | Read + Grep |
| AC-3 | Grep SKILL.md "首选 JVM" 确认已移除 + Read mock-unimplemented-functions.md 标注 | Grep + Read |
| AC-4 | 运行 `python ai_tests/scripts/skill_e2e_test.py --url {测试URL}` + 检查报告 | RunCommand |
| AC-5 | Read SKILL.md 行数 + Glob references/ 文件数 + Grep 计算总行数 | Read + Glob + Grep |
| AC-6 | 完整真机 E2E 验证流程（编译→安装→导入→加载→播放） | quick_build_install.py + import_rss_source.py + l2_verify_video_player.py |

## 4. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 砍掉功能后用户依赖某个功能 | 中 | 归档而非删除，保留 30 天回退窗口 |
| 精简流程后 AI 缺少深度陷阱知识 | 低 | 把详细陷阱迁到 references/，SKILL.md 只保留索引 |
| JVM 降级后调试能力下降 | 低 | JVM 仍可用，只是不作为"首选" |
| 真机 E2E 测试环境不稳定 | 中 | E2E 测试包含重试机制 + 失败时输出详细日志 |
| 重构期间影响现有 skill 可用性 | 中 | 在新分支上重构，不影响 master 分支的现有 skill |

## 5. 不在范围

- 不重写 legado-jvm Kotlin 源码（保留现有 JAR）
- 不修改 Legado Android 应用源码
- 不修改 basic-memory MCP 工具
- 不修改 ai_tests 现有脚本（仅新增 skill_e2e_test.py）
- 不修改 v2 已修复的 cf-bypass 修复（保留正确性）
