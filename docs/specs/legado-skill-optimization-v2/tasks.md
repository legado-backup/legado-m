# tasks.md — legado-skill-optimization-v2

> **关联**: [README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)
> **核心创新**: 每条任务必须带"验证证据"字段，未通过验证不得标记 completed

---

## 任务状态图例

- ⬜ pending（未开始）
- 🟡 in_progress（进行中）
- ✅ completed（已完成，附验证证据）
- ⚠️ blocked（阻塞，需说明原因）

---

## Layer A：立即修复（错误知识纠正）

### A1 修复 cf-bypass.md 错误的 loginUrl 建议

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/references/special-scenarios/cf-bypass.md`
- **任务**:
  1. 删除第 35-40 行的 `loginUrl: "@js:java.webView(null, source.sourceUrl, null, false);"` 配置
  2. 替换为正确方案：
     - 说明 loginUrl 必须是普通 URL（不可用 @js: 形式）
     - 用户手动点击登录按钮触发 WebView 加载
     - Cookie 通过 onPageFinished 自动同步到 CookieStore
  3. 修正"执行流程"章节（第 42-46 行）的错误描述
- **验证证据**: Grep `@js:java\.webView\(null` 在 cf-bypass.md 中无命中
- **依赖**: 无

### A2 修复 SKILL.md 陷阱#54

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/SKILL.md`
- **任务**:
  1. 修正第 90 行陷阱#54：
     - 旧：`CF JS Challenge | webView()自动通过（loginUrl中调用）`
     - 新：`CF JS Challenge | loginUrl 不能用 @js:java.webView()！必须是普通 URL，用户手动点击登录后 WebView 自动通过 CF JS Challenge`
  2. 修正第 200 行 Phase 2 步骤4 中的 CF 反爬建议：
     - 旧：`JS Challenge → loginUrl: @js:java.webView(null, source.sourceUrl, null, false);`
     - 新：`JS Challenge → loginUrl 设为首页 URL（普通形式），用户首次使用时点击"登录"按钮触发 WebView 加载`
- **验证证据**: Read SKILL.md 第90行和第200行确认描述已修正
- **依赖**: 无

### A3 修复 SKILL.md:305 源码引用

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/SKILL.md`
- **任务**:
  1. 修正第 305 行附近的 `loginUrl 执行 | SourceLoginDialog.kt`：
     - 改为：`loginUrl 执行 | WebViewLoginFragment.kt (loadUrl方法) + SourceLoginDialog.kt (loginUi非空时分支)`
- **验证证据**: Read SKILL.md 确认引用已修正
- **依赖**: 无

### A4 审查并修复 11 个含错误 @js:loginUrl 模式的文件

- **状态**: ⬜ pending
- **任务**:
  1. Grep 搜索 `loginUrl.*@js:|java\.webView\(null` 命中的所有文件
  2. 逐一审查每个命中位置
  3. 修正错误建议或标注 `> ⚠️ 已知过时：本建议在源码验证下不成立，参见 cf-bypass.md`
  4. 记录每个文件的处理结果到审查清单
- **验证证据**: Grep `loginUrl.*@js:|java\.webView\(null` 命中数 ≤2 且均为"已知过时"标注
- **依赖**: A1（cf-bypass.md 已修复作为参考）

### A5 备份原文件到 .archive/v2-pre-bak/

- **状态**: ⬜ pending
- **任务**: 在改动任何 skill 文件前，先备份原文件到 `.trae/skills/legado-source-creator/.archive/v2-pre-bak-20260717/`
- **验证证据**: LS 确认备份目录存在且包含 cf-bypass.md / SKILL.md / AI_README.md 等
- **依赖**: 无（必须在 A1-A4 之前执行）

---

## Layer B：门禁强化（防止再发生）

### B1 新增 Phase 0 源码验证门禁

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/SKILL.md`
- **任务**:
  1. 在"核心工作流（5阶段闭环）"章节前新增"Phase 0 源码验证门禁"章节
  2. Phase 0 触发条件：涉及以下字段时必须执行
     - loginUrl / loginCheckJs / loginUi
     - webView / startBrowserAwait
     - cookie / CookieStore / CookieManager
     - ruleContent 中涉及视频播放器
  3. Phase 0 执行步骤：
     - Grep Legado 源码定位字段实际使用位置
     - Read 关键源码文件确认实现
     - 在 references 中带 `source_ref:` 字段记录源码位置
  4. Phase 0 失败处理：无法找到源码依据时，禁止写入 references/
- **验证证据**: Read SKILL.md 确认 Phase 0 章节存在且包含触发条件+执行步骤+失败处理
- **依赖**: A2（陷阱#54 已修复）

### B2 降级 JVM 仿真器能力声明

- **状态**: ⬜ pending
- **文件**:
  - `.trae/skills/legado-source-creator/SKILL.md`（第 143-148 行附近）
  - `.trae/skills/legado-source-creator/AI_README.md`（第 37-46 行附近）
  - `.trae/skills/legado-source-creator/references/jvm-infrastructure.md`
- **任务**:
  1. 将"JVM 覆盖率 85-90%"改为"规则引擎层覆盖 85-90%（Rhino JS + jsoup CSS + hutool 加密 + AnalyzeRule）"
  2. 明确"❌ 不覆盖：Android WebView 系统组件 / Activity 生命周期 / Cookie 自动同步 / 真机网络栈"
  3. 涉及 WebView 字段时强制走 Phase 0 + 真机验证
- **验证证据**: Grep `85-90%` 命中位置均带"规则引擎层"限定词
- **依赖**: 无

### B3 references/ 源码锚定字段规范化

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/references/basic-memory-usage.md`
- **任务**:
  1. 在 basic-memory-usage.md 中新增"源码锚定字段规范"章节
  2. 规范要求：涉及 loginUrl/loginCheckJs/webView/cookie 的建议必须带 `source_ref: app/src/.../Xxx.kt#L行号`
  3. 提供标准模板示例
  4. 双写流程更新：先验证源码 → 写 references（带 source_ref）→ 写 basic-memory（带 verified_against_source）
- **验证证据**: Read basic-memory-usage.md 确认章节存在+模板示例
- **依赖**: B1

### B4 强化 Phase 4 源码深挖触发条件

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/SKILL.md`
- **任务**:
  1. 修正 Phase 4 触发条件：
     - 旧：仅"测试失败"时触发
     - 新：以下任一即触发
       - JVM 测试失败
       - 涉及 WebView 字段（即使 JVM 测试通过）
       - 涉及 loginUrl/loginCheckJs/cookie 字段
       - 用户反馈"不工作"
  2. 强化 Phase 4 输出要求：必须输出 `source_ref:` 字段
- **验证证据**: Read SKILL.md Phase 4 章节确认触发条件已扩展
- **依赖**: B1, B2

---

## Layer C：架构瘦身

### C1 合并 cleanup_*.py 脚本

- **状态**: ⬜ pending
- **任务**:
  1. 合并 cleanup_dead_empty.py / cleanup_false_success.py / cleanup_unusable.py / batch_clean_dead_sources.py → `cleanup_sources.py`
  2. 保留各自核心功能为子命令：`cleanup_sources.py dead` / `cleanup_sources.py false-success` / `cleanup_sources.py unusable` / `cleanup_sources.py all`
  3. 删除原文件（已备份在 .archive/v2-pre-bak/scripts/）
- **验证证据**: LS scripts/ 确认 4 个原文件已删除，cleanup_sources.py 存在
- **依赖**: A5

### C2 合并 fix_*.py 脚本

- **状态**: ⬜ pending
- **任务**:
  1. 合并 auto_fix_sources.py / deep_fix_search.py / fix_rule_articles.py / fix_search_failed.py / smart_fix.py / dom_fix.py → `fix_source.py`
  2. 子命令：`fix_source.py auto` / `fix_source.py search` / `fix_source.py articles` / `fix_source.py dom` / `fix_source.py smart`
- **验证证据**: LS scripts/ 确认 6 个原文件已删除，fix_source.py 存在
- **依赖**: A5

### C3 合并 verify_*.py 脚本

- **状态**: ⬜ pending
- **任务**:
  1. 合并 verify-decrypt.py / verify-image.py / verify-selector.py / verify-source.py / quick-verify.py / deep_verify.py → `validate_source.py`
  2. 子命令：`validate_source.py decrypt` / `validate_source.py image` / `validate_source.py selector` / `validate_source.py source` / `validate_source.py quick` / `validate_source.py deep`
- **验证证据**: LS scripts/ 确认 6 个原文件已删除，validate_source.py 存在
- **依赖**: A5

### C4 归档 legado_client 包

- **状态**: ⬜ pending
- **任务**:
  1. 移动 `scripts/legado_client/` 到 `.archive/legado-client-snapshot-20260717/`
  2. 在 scripts/ 下创建 `legado_client/README.md` 指向归档位置
  3. 检查并更新引用 legado_client 的脚本（如 batch_device_debug.py）
- **验证证据**: LS 确认 scripts/legado_client/ 已被 README.md 占位，原内容在 .archive/
- **依赖**: A5
- **⚠️ 风险点**: 需先用 AskUserQuestion 确认用户是否同意归档（用户可能依赖 Web 界面）

### C5 清理 reports/ 历史包袱

- **状态**: ⬜ pending
- **任务**:
  1. 移动 scripts/reports/*.json 到 `.archive/reports-snapshot-20260717/`
  2. 在 scripts/reports/ 下创建 .gitkeep
  3. 更新 .gitignore 排除 reports/*.json
- **验证证据**: LS scripts/reports/ 确认只剩 .gitkeep
- **依赖**: A5

### C6 合并剩余冗余脚本

- **状态**: ⬜ pending
- **任务**:
  1. 合并 batch_optimize.py / batch_device_debug.py / smart_dedup_v3.py / smart_merge_v4.py / deep_analysis.py → `manage_sources.py`
  2. 合并 analyze_site.py / generate-js-doc.py / deep-analyze-js.py → 合并到 create_source.py 或保留独立
  3. 删除 test_*.py / ws_test*.py / device_test.py / device_api_test.py / e2e_test.py（测试类脚本归并到 ai_tests/）
- **验证证据**: `ls scripts/*.py | wc -l` ≤10
- **依赖**: C1, C2, C3

---

## Layer D：经验引擎改造

### D1 清理 basic-memory 中的错误经验笔记

- **状态**: ⬜ pending
- **任务**:
  1. 用 mcp_basic-memory_search_notes 搜索"CF绕过"/"loginUrl webView"
  2. 审查命中笔记内容
  3. 错误笔记调用 mcp_basic-memory_delete_note 删除
  4. 错误笔记修正后重新写入（带 verified_against_source）
- **验证证据**: mcp_basic-memory_search_notes 命中笔记均带 verified_against_source
- **依赖**: A1（cf-bypass.md 已修复作为参考）

### D2 新增"错误经验撤销机制"文档

- **状态**: ⬜ pending
- **文件**: `.trae/skills/legado-source-creator/references/basic-memory-usage.md`
- **任务**:
  1. 新增"错误经验撤销流程"章节：
     - 发现错误经验 → 删除 basic-memory 笔记 → 修正 references/ → 重新写入 basic-memory（带 verified_against_source）
  2. 提供撤销操作示例
- **验证证据**: Read basic-memory-usage.md 确认章节存在
- **依赖**: D1, B3

### D3 增量补全旧 references/ 的 source_ref

- **状态**: ⬜ pending
- **任务**:
  1. Grep references/ 中所有 loginUrl/loginCheckJs/webView/cookie 相关建议
  2. 按引用频率排序
  3. 高频引用的逐条补全 source_ref（Grep 源码验证）
  4. 低频的标注"待补全 source_ref"
- **验证证据**: Grep `source_ref:` 在 references/ 下命中数 ≥ 关键字段建议总数的 50%
- **依赖**: B3

---

## 任务统计

| Layer | 任务数 | 状态 |
|-------|--------|------|
| A 立即修复 | 5 | 全部 pending |
| B 门禁强化 | 4 | 全部 pending |
| C 架构瘦身 | 6 | 全部 pending |
| D 经验引擎 | 3 | 全部 pending |
| **总计** | **18** | **18 pending** |

---

## 检查点

### CP1 设计审查（当前）

在 Layer A 开始实施前，用 AskUserQuestion 让用户审查：
- README.md / spec.md / design.md / tasks.md 是否符合预期
- Layer A-B-C-D 划分是否合理
- ADR 决策是否接受

### CP2 实施审核（Layer A+B 完成后）

- A1-A5 全部 ✅
- B1-B4 全部 ✅
- 验证证据全部通过
- 用 AskUserQuestion 让用户审查实施结果

### CP3 最终验收（全部完成后）

- A/B/C/D 全部 ✅
- 跑一次端到端测试：让 skill 修复一个 CF 站点，验证不再推荐错误建议
- 用 AskUserQuestion 让用户最终验收
