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

## 源码锚定字段规范（v2 新增，强制执行）

> **根因**（2026-07-17 v2）：原 cf-bypass.md 推荐 `loginUrl: @js:java.webView(null, source.sourceUrl, null, false);` 被源码证伪——`WebViewLoginFragment.loadUrl()` 不识别 `@js:` 形式。错误经验一旦写入会反复强化，必须在写入前拦截。
> **本规范是 Phase 0 源码验证门禁的 L2/L3 落地执行细则**（Phase 0 总纲见 SKILL.md）。

### 触发字段（任一命中即必须执行源码锚定）

| 字段/方法 | 触发理由 |
|-----------|---------|
| `loginUrl` / `loginCheckJs` / `loginUi` | WebView/SourceLoginDialog 加载逻辑分支多，经验易错 |
| `webView` / `startBrowserAwait` / `startBrowser` | 涉及 Android 系统组件，JVM 仿真不覆盖 |
| `cookie` / `CookieStore` / `CookieManager` | 自动同步机制复杂（onPageFinished 触发） |
| `ruleContent` 中涉及视频播放器配置 | ExoPlayer 防盗链/Referer 注入逻辑分散 |
| `header` 中 `@js:` 形式 | `{{baseUrl}}` 等模板变量在 header 中不替换（陷阱#75） |

### references/ 写入要求（L2）

涉及上述触发字段的建议，**必须**在文件中带 `source_ref:` 字段记录源码位置：

```
source_ref: app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt#L123-L145
```

格式规范：
- 路径相对于项目根目录（`app/src/main/java/...`）
- 行号格式 `#L起-止`（范围）或 `#L123`（单行）
- 多处源码依据用多个 `source_ref:` 行

**标准模板示例**（references/special-scenarios/cf-bypass.md 中的写法）：

```markdown
## CF JS Challenge 绕过方案

**loginUrl 配置**：
- ✅ 正确：`"loginUrl": "https://example.com/"`（普通 URL）
- ❌ 错误：`"loginUrl": "@js:java.webView(null, source.sourceUrl, null, false);"`

source_ref: app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt#L67-L89
source_ref: app/src/main/java/io/legado/app/ui/login/SourceLoginDialog.kt#L45-L60
```

### basic-memory 写入要求（L3）

涉及触发字段的笔记，**必须**在 metadata 中带 `verified_against_source:` 字段：

```python
mcp_basic-memory_write_note(
    title="经验: CF JS Challenge 绕过",
    content="...",
    directory="experiences/url-network/",
    project="legado",
    note_type="experience",
    tags=["cf","cloudflare","webview"],
    metadata={
        "source_doc": "references/special-scenarios/cf-bypass.md",
        "source_sync_date": "2026-07-17",
        "sync_status": "synced",
        "verified_against_source": "app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt#L67-L89",
        "verified_date": "2026-07-17"
    }
)
```

### 双写流程更新（v2 强制顺序）

原 3 步流程升级为 4 步（涉及触发字段时）：

```
步骤0（新增，仅触发字段时）：Phase 0 源码验证
  - Grep Legado 源码定位字段实际使用位置
  - Read 关键源码文件确认实现
  - 无法找到源码依据 → 禁止写入 references/ 和 basic-memory
  - 通过 → 进入步骤1

步骤1：更新 Skill 文档（权威源，references/ 下的文件）
  - 涉及触发字段时必须带 source_ref: 字段

步骤2：写 basic-memory（索引层）
  - 先搜索是否已有同类笔记
  - 涉及触发字段时必须带 verified_against_source: 字段

步骤3：标记 sync_status（根据双写结果，见一致性规则）
```

### 反模式（禁止）

- ❌ 不带 `source_ref:` 就在 references/ 中写 loginUrl/loginCheckJs/webView 建议
- ❌ 不带 `verified_against_source:` 就在 basic-memory 中写触发字段相关笔记
- ❌ 凭"经验"或"记忆"写入触发字段建议（必须以源码为准）
- ❌ 引用其他 AI 生成文档作为依据（L4 Legado 源码是唯一真相）

### 拒绝写入清单（自检）

写入前自问 3 个问题：
1. 这条建议是否涉及触发字段？→ 是 → 必须执行 Phase 0
2. 是否已 Grep + Read 源码确认？→ 否 → 禁止写入
3. references/basic-memory 是否带源码锚定字段？→ 否 → 补齐再写入

---

## 错误经验撤销流程（v2 新增，D2）

> **背景**（2026-07-17 v2）：发现已写入 basic-memory/references 的经验被源码验证证伪时（如 cf-bypass.md 的 `loginUrl: @js:java.webView()` 建议），必须执行撤销流程，避免错误经验继续被 Phase 1 搜索命中反向强化。

### 触发条件（任一即触发撤销流程）

1. **源码验证证伪**：Grep+Read Legado 源码后，发现已写入的建议与源码实现不符
2. **真机测试失败**：用户反馈按建议配置后源不工作，且源码验证确认建议错误
3. **Legado 版本升级**：字段处理逻辑变更导致旧建议失效

### 撤销流程（5 步强制）

```
步骤1：源码验证确认错误
  - Grep Legado 源码定位字段实际使用位置
  - Read 关键源码文件确认实现
  - 记录 source_ref: app/src/.../Xxx.kt#L行号

步骤2：删除 basic-memory 错误笔记
  - mcp_basic-memory_search_notes 搜索错误关键词定位笔记
  - mcp_basic-memory_read_note 确认错误内容
  - mcp_basic-memory_delete_note(identifier="错误笔记permalink", project="legado")

步骤3：修正 references/ 中的错误建议
  - Edit references/ 下对应文件
  - 删除错误建议，替换为正确方案
  - 必须带 source_ref: 字段记录源码依据

步骤4：重新写入 basic-memory 修正版
  - mcp_basic-memory_write_note 写入修正版
  - 必须带 metadata:
      verified_against_source: "app/src/.../Xxx.kt#L行号"
      verified_date: "YYYY-MM-DD"
      sync_status: "synced"
  - tags 中加 "v2-corrected" 标识

步骤5：验证搜索确认无残留
  - mcp_basic-memory_search_notes 搜索错误关键词
  - 确认命中笔记均为修正版（带 v2-corrected 标签）或不含错误建议
```

### 标准模板（撤销操作示例）

```python
# 步骤2：删除错误笔记
mcp_basic-memory_delete_note(
    identifier="legado/experiences/错误经验标题",
    project="legado"
)

# 步骤4：写入修正版
mcp_basic-memory_write_note(
    title="错误经验标题（v2修正版）",
    content="""# 标题（v2 修正版）

> ⚠️ v2 修正（YYYY-MM-DD）：原经验推荐 XXX 是**错误的**！
> 源码验证证明 YYY。

## 正确方案
...""",
    directory="experiences/",
    project="legado",
    note_type="experience",
    tags=["...", "v2-corrected"],
    metadata={
        "source_doc": "references/xxx.md",
        "source_sync_date": "YYYY-MM-DD",
        "sync_status": "synced",
        "verified_against_source": "app/src/.../Xxx.kt#L行号",
        "verified_date": "YYYY-MM-DD"
    },
    overwrite=True
)
```

### 实际案例（cf-bypass loginUrl 错误撤销，2026-07-17）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 源码验证 | Read WebViewLoginFragment.kt loadUrl() | 确认不识别 @js: 形式 |
| 2 删除错误笔记 | delete_note × 3（阶段10验证/Skill HTML增强/loginUrl是JS代码） | 3 条错误笔记已删除 |
| 3 修正 references | Edit cf-bypass.md（Layer A1） | loginUrl 改为普通 URL |
| 4 重写修正版 | write_note × 3（带 verified_against_source + v2-corrected） | 3 条修正版已写入 |
| 5 验证搜索 | search_notes "loginUrl @js:java.webView" | 命中均为修正版，无错误残留 |

### 反模式（禁止）

- ❌ 发现错误经验后不删除，只在 references 修正（basic-memory 仍会命中错误版本）
- ❌ 删除后不重新写入修正版（经验丢失，无法复用）
- ❌ 重写修正版不带 verified_against_source（无法溯源验证）
- ❌ 不做验证搜索（无法确认错误经验已清理干净）

---

## 双写一致性规则

| 场景 | 处理 |
|------|------|
| Skill文档+basic-memory 都成功 | sync_status: "synced" |
| Skill文档成功，basic-memory失败 | sync_status: "pending"，后续补写 |
| Skill文档失败 | **不写basic-memory**（避免索引层比权威源更新） |
| 两处不一致 | 以Skill文档为准，basic-memory标记 sync_status: "conflict" |
| **涉及触发字段但未带 source_ref/verified_against_source**（v2 新增） | **拒绝写入**，回到 Phase 0 补源码验证 |
