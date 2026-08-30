# 关联导入体系

> `ui/association/` 包——外部内容（URL/文件/分享文本）导入 App 的对话框与路由体系。

## 概述

关联导入是"外部 → 书架/配置"的统一入口层：Deep Link、文件关联、系统分享最终都路由到本包。每类资源对应一个 `ImportXxxDialog`（Compose DialogFragment）+ 配套 ViewModel，下载与解析由独立组件承担。

## 核心类清单

| 类名 | 路径（ui/association/ 下） | 职责 |
|------|------|------|
| ImportBookSourceDialog | ImportBookSourceDialog.kt | 书源批量导入对话框 |
| ImportReplaceRuleDialog | ImportReplaceRuleDialog.kt | 替换规则导入对话框 |
| ImportRssSourceDialog | ImportRssSourceDialog.kt | 订阅源导入对话框 |
| ImportThemeDialog | ImportThemeDialog.kt | 主题导入对话框 |
| ImportDictRuleDialog | ImportDictRuleDialog.kt | 字典规则导入对话框 |
| ImportHttpTtsDialog | ImportHttpTtsDialog.kt | 在线 TTS 引擎导入对话框 |
| ImportTxtTocRuleDialog | ImportTxtTocRuleDialog.kt | TXT 目录规则导入对话框 |
| ImportRedThemeDialog | ImportRedThemeDialog.kt | 红色主题等特殊主题导入对话框 |
| ParagraphRuleOnlineImportDialog | ParagraphRuleOnlineImportDialog.kt | 段落规则在线导入对话框 |
| OnLineImportActivity | OnLineImportActivity.kt | URL 导入入口 Activity（`/import` 链路宿主） |
| FileAssociationActivity | FileAssociationActivity.kt | 本地文件关联入口（打开本地书/规则文件） |
| OpenUrlConfirmDialog / OpenUrlConfirmActivity | OpenUrlConfirmDialog.kt / OpenUrlConfirmActivity.kt | 外部 URL 打开前确认 |
| VerificationCodeDialog / VerificationCodeActivity | VerificationCodeDialog.kt / VerificationCodeActivity.kt | 验证码输入（源登录/访问校验） |
| AddToBookshelfDialog | AddToBookshelfDialog.kt | 分享/URL 加入书架确认 |
| ImportDialogComponents | ImportDialogComponents.kt | 各 ImportDialog 共用 UI 组件 |
| OnlineImportDownloader | OnlineImportDownloader.kt | 远程导入内容下载 |
| OnlinePackageImportRoute | OnlinePackageImportRoute.kt | 在线导入包路由分发 |
| ParagraphRulePackageImporter / PackageParser / PackageModels | ParagraphRulePackageImporter.kt 等 | 段落规则包导入/解析/数据模型 |
| ImportResponseLimits | ImportResponseLimits.kt | 导入响应大小/条数限制 |

## 关键机制

- **路由分发**：URL Scheme/分享文本进入后按内容特征分发到对应 `ImportXxxDialog`；本地文件经 `FileAssociationActivity` 按扩展名分发（书籍 → 阅读链路，规则 → 对应导入对话框）。
- **对话框 + ViewModel 配对**：每个 ImportDialog 配套 `ImportXxxViewModel` 承担解析与入库，对话框仅负责展示选择。
- **在线导入链路**：`OnLineImportActivity` → `OnlineImportDownloader` 下载 → `OnlinePackageImportRoute` 分发 → 具体 Importer 入库；`ImportResponseLimits` 约束响应体，防止超大 payload。
- **关联文档**：Deep Link 注册表见 [intent-deep-links.md](../architecture/intent-deep-links.md)；书源导入导出全链路见 [source-management.md](./source-management.md)。
