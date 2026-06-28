# basic-memory 完整操作规范

> 本文档从 SKILL.md 拆分，包含 basic-memory MCP 的详细操作规范。模板（write_note 模板、执行证据模板）保留在 SKILL.md 中供 AI 直接复制使用。

---

## 核心定位

basic-memory 是经验索引层（L3），存储陷阱/模式/经验的摘要+指针。完整内容在 L2（references/）。

**权威源规则**：Skill文档 > references/ > basic-memory。

**双写规范**：SKILL.md 陷阱速查表中的每条陷阱，basic-memory 中必须有对应的 trap 笔记。references/ 中的关键经验，basic-memory 中必须有对应的 experience/pattern 笔记。如果发现缺失，必须补写。

---

## MCP 工具调用规范

**所有 basic-memory 操作必须指定 `project="legado"`**，否则会写入默认项目。

| 操作 | MCP 工具 | 必填参数 |
|------|---------|---------|
| 搜索经验 | `mcp_basic-memory_search_notes` | `query`, `search_type="hybrid"`, `project="legado"` |
| 读取笔记 | `mcp_basic-memory_read_note` | `identifier`(标题或permalink), `project="legado"` |
| 写入笔记 | `mcp_basic-memory_write_note` | `title`, `content`, `directory`, `project="legado"`, `note_type`, `tags` |
| 编辑笔记 | `mcp_basic-memory_edit_note` | `identifier`, `operation`, `content`, `project="legado"` |
| 列出目录 | `mcp_basic-memory_list_directory` | `dir_name`, `project="legado"` |
| 构建上下文 | `mcp_basic-memory_build_context` | `url="memory://{permalink}"`, `project="legado"` |

---

## L3 目录结构

```
legado/                          # project="legado"
├── traps/                       # 陷阱索引
│   ├── js-rhino/                # JS/Rhino 陷阱
│   ├── source-type/             # 源类型陷阱
│   ├── crypto/                  # 加密陷阱
│   ├── url-network/             # URL/网络陷阱
│   └── html-css/                # HTML/CSS 陷阱
├── patterns/                    # 成功模式
│   ├── crypto/                  # 加密模式
│   └── templates/               # 配置模板
├── experiences/                 # 网站特征→经验
│   └── encryption/              # 加密经验
├── verifications/               # 源码验证结论
├── execution-logs/              # Phase 执行证据
├── test-reports/                # 测试报告
└── cases/                       # 实战案例
```

---

## 笔记类型体系

| note_type | directory | 用途 | tags 示例 |
|-----------|-----------|------|----------|
| `trap` | `traps/{category}/` | 陷阱命中记录 | `["rhino","es5"]` |
| `pattern` | `patterns/{category}/` | 成功模式/代码模板 | `["crypto","aes-cbc"]` |
| `experience` | `experiences/{category}/` | 网站特征→经验 | `["wordpress","mirages"]` |
| `verification` | `verifications/` | 源码验证结论 | `["rss-source","field"]` |
| `execution-log` | `execution-logs/` | Phase 执行证据 | `["phase-1","91dasj"]` |
| `test-report` | `test-reports/` | 测试报告 | `["verify-source","51rb5"]` |
| `audit-report` | `audit-reports/` | 审计报告 | `["audit","{源名称}"]` |
| `case` | `cases/` | 实战案例 | `["rss","video","maccms"]` |

---

## Phase 1 搜索策略

```
最小必执行（1次调用）：
  mcp_basic-memory_search_notes(
      query="网站技术特征关键词",    # 如 "苹果CMS 视频播放 player_aaaa"
      search_type="hybrid",         # 向量+文本混合搜索
      project="legado",
      page_size=10
  )

推荐增强（根据第一轮结果决定）：
  第二轮 tags 精确过滤：
    mcp_basic-memory_search_notes(
        query="视频播放",
        tags=["maccms","video"],
        project="legado"
    )

  第三轮 知识图谱遍历（找到相关经验后）：
    mcp_basic-memory_build_context(
        url="memory://patterns/苹果CMS V10 player_aaaa 视频提取模式",
        depth=2,
        max_related=20,
        project="legado"
    )

降级路径（basic-memory MCP 不可用时，三步统一）：
  1. 检测不可用：调用 mcp_basic-memory_search_notes，若抛出异常或超时，判定为不可用
  2. Grep references/ 替代：Grep(pattern="关键词", path=".trae/skills/legado-source-creator/references/")
     或直接读取相关 _index.md：Read(file_path=".trae/skills/legado-source-creator/references/troubleshooting/_index.md")
  3. 标记待验证：在输出中标记"需 basic-memory 验证"，后续可用时补查
```

---

## Phase 5 反哺写入策略（3 步简化）

```
步骤1：更新 Skill 文档（权威源，references/ 下的文件）
步骤2：写 basic-memory（索引层）
  - 先搜索是否已有同类笔记：mcp_basic-memory_search_notes(query="同类经验关键词", project="legado")
  - 找到 → mcp_basic-memory_edit_note(identifier="已有笔记标题", operation="append", content="新经验")
  - 未找到 → mcp_basic-memory_write_note（见 SKILL.md 中的 write_note 模板）
步骤3：标记 sync_status（根据双写结果，见一致性规则）
```

---

## 双写一致性规则

| 场景 | 处理 |
|------|------|
| Skill文档+basic-memory 都成功 | sync_status: "synced" |
| Skill文档成功，basic-memory失败 | sync_status: "pending"，后续补写 |
| Skill文档失败 | **不写basic-memory**（避免索引层比权威源更新） |
| 两处不一致 | 以Skill文档为准，basic-memory标记 sync_status: "conflict" |
