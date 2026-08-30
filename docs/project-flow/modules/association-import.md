# 关联导入体系

> `ui/association/` 包——外部内容（URL/文件/分享文本）导入 App 的对话框与路由体系。
> **实测规模**：36 文件 5489 行，行数均基于源码实测。

## 1. 功能定位

关联导入是"外部 → 书架/配置"的统一入口层：Deep Link、文件关联、系统分享最终都路由到本包。每类资源对应一个 `ImportXxxDialog`（Compose DialogFragment）+ 配套 ViewModel，下载与解析由独立组件承担。

## 2. 目录结构（按职责分组，括号内为实测行数）

| 分组 | 文件（行数） |
|------|------|
| 入口 Activity | OnLineImportActivity（355，URL 导入宿主）、FileAssociationActivity（243，文件关联）、OpenUrlConfirmActivity（20） |
| 导入对话框 ×10 | ImportBookSource（260）/ ImportRssSource（232）/ ImportReplaceRule（212）/ ImportTxtTocRule（169）/ ImportHttpTts（168）/ ImportDictRule（166）/ ImportTheme（155）/ ImportRedTheme（119）/ ParagraphRuleOnlineImport（148）/ OpenUrlConfirm（168） |
| 配套 ViewModel | ImportBookSourceViewModel（210）、ImportRssSourceViewModel（184）、ImportReplaceRuleViewModel（134）等 10 个同名 ViewModel，另含 FileAssociationViewModel（104）、OnLineImportViewModel（104）、OpenUrlConfirmViewModel（35） |
| 书架/验证 | AddToBookshelfDialog（241）、VerificationCodeDialog（248）/ VerificationCodeActivity（24）/ VerificationCodeViewModel（30） |
| 在线导入支撑 | OnlineImportDownloader（294，远程下载）、OnlinePackageImportRoute（44，路由分发）、ImportResponseLimits（21，响应限制）、ImportDialogComponents（111，共用 UI 组件）、ShibbolethDialogExtensions（51） |
| 段落规则包 | ParagraphRulePackageImporter（123）、ParagraphRulePackageParser（152）、ParagraphRulePackageModels（27） |

## 3. 关联导入流程

- **路由分发**：URL Scheme/分享文本进入后按内容特征分发到对应 `ImportXxxDialog`；本地文件经 `FileAssociationActivity` 按扩展名分发（书籍 → 阅读链路，规则 → 对应导入对话框）。
- **对话框 + ViewModel 配对**：每个 ImportDialog 配套 ViewModel 承担解析与入库，对话框仅负责展示选择。
- **在线导入链路**：`OnLineImportActivity` → `OnlineImportDownloader` 下载 → `OnlinePackageImportRoute` 分发 → 具体 Importer 入库；`ImportResponseLimits` 约束响应体，防止超大 payload。
- **导入去重与保留策略**：以源 URL 为唯一键，`importKeepName/importKeepGroup/importKeepEnable` 策略在 ViewModel 内合并字段（详见 [source-management.md](./source-management.md) §4）。

## 4. ParagraphRule 智能分段规则包

- **解析器**：`ParagraphRulePackageParser`（object，实测 152 行）
- **包格式常量**：`FORMAT = "legado.paragraph-rules"`（L12）、`SCHEMA_VERSION = 1`（L13）、`MAX_RULES = 256`（L14）
- **资源限制**（L15-18）：`MAX_SCRIPT_CHARS = 1MB`（script/jsLib/loginUi/loginUrl 共用）、`MAX_VARS_PER_RULE = 256`、`MAX_VAR_NAME_CHARS = 200`、`MAX_VAR_VALUE_CHARS = 65536`
- **三种输入形态**（parseElement L30-47）：JSON 数组（逐条规则）/ 包封套对象（format + schemaVersion + rules，逐项校验 L49-79）/ 单规则对象
- **校验规则**（validateRule L112-142）：名称非空且限长；script 必填；loginUrl 按 JS 校验而非 URL（因 `BaseSource.getLoginJs()` 会将其作为 JavaScript 执行）；变量名/值禁含 `\u0000`；exportId 限长且禁控制符
- **exportId 字段**（L71-75、L128-133）：包内条目可选携带，空串归一为 null；长度不得超过规则名上限且禁含 ISO 控制符
- **失败表现**：所有校验失败均抛 `IOException`（消息即原因），由 `ParagraphRulePackageImporter`（123 行）承接解析结果并入库

## 5. 调试入口

- 导入链路日志统一走 `AppLog.put()`，失败原因随异常消息输出，按源 key 打 tag
- `ImportResponseLimits`（21 行）：响应体大小/条数上限，超大 payload 直接拒绝——导入"无响应"先查此限制
- 真机自动化：`ai_tests/scripts/import_rss_source.py`（固定脚本入口）可复现订阅源导入链路
- 验证码场景：`VerificationCodeDialog`（248 行）人工输入验证码 → `SourceVerificationHelp` 唤醒阻塞线程（见 source-management.md §3）
- 离线复现：书源管理界面分享/导出 JSON 后可重新导入，用于对比导入前后差异（导出途径见 source-management.md §5）
- 三段定位法：`OnLineImportActivity` 是否命中路由 → `OnlineImportDownloader` 下载是否成功 → 具体 ViewModel 入库日志，逐段缩小范围
- 体量 Top3（实测）：OnLineImportActivity（355）、OnlineImportDownloader（294）、ImportBookSourceDialog（260）——排障优先关注

## 关联文档

- Deep Link 注册表见 [intent-deep-links.md](../architecture/intent-deep-links.md)；书源导入导出全链路见 [source-management.md](./source-management.md)。
