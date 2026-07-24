# Tasks: 日志规范全面审查与补全完善

> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)
>
> 任务编排原则：准备 → 规范审查 → 源码补全 → 脚本新增 → 验证 → 文档同步。
> 源码修改遵循 logging_rules.md 的三层日志体系（AppLog/DebugLog/LogUtils），禁止使用 android.util.Log。

---

## 1. 准备工作

- [ ] 1.1 确认需求范围（日志规范审查 + 源码日志补全 + ai_tests 脚本新增）
- [ ] 1.2 阅读日志相关源码（AppLog.kt / LogUtils.kt / DebugLog.kt），明确三层日志体系职责
- [ ] 1.3 阅读现有日志规范（logging_rules.md / logging-during-refactoring.md），建立现状基线
- [ ] 1.4 分析 ai_tests 现有日志获取方式（evidence_collector.py / swipe_test_log.py），识别能力缺口

## 2. 日志规范审查与优化

- [ ] 2.1 审查 logging_rules.md 的合理性（三层体系 / 标签约定 / 使用规则）
- [ ] 2.2 审查 logging-during-refactoring.md 的合理性（10 类必加日志场景）
- [ ] 2.3 定义统一模块 Tag 命名规范（WebBook / AnalyzeRule / HttpHelper / DownloadService 等）
- [ ] 2.4 增加"关键操作成功 / 失败"日志记录要求
- [ ] 2.5 增加 ai_tests 可用 Tag 约定（便于按 tag 过滤文件日志）
- [ ] 2.6 更新 logging_rules.md
- [ ] 2.7 更新 logging-during-refactoring.md

## 2A. AppLog 增强（putDebugWithTag 方法）

- [ ] 2A.1 在 AppLog.kt 中新增 7 个模块 Tag 常量（TAG_WEB_BOOK / TAG_ANALYZE / TAG_HTTP / TAG_WEB_VIEW / TAG_DATA / TAG_RSS / TAG_CONTENT）
- [ ] 2A.2 在 AppLog.kt 中新增 `putDebugWithTag(tag, message, throwable, level)` 方法，recordLog 守卫（关闭时直接 return 零开销）
- [ ] 2A.3 验证 putDebugWithTag 在 recordLog 关闭时确实零开销（无文件写入、无内存操作）

## 3. WebBook 模块日志补全

- [ ] 3.1 BookInfo.kt：补全 5 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)` 调用
- [ ] 3.2 BookList.kt：补全 5 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)` 调用
- [ ] 3.3 WebBook.kt：补全 8 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)` 调用（已有 2 处，需补 8 处）

## 4. 规则引擎模块日志补全

- [ ] 4.1 AnalyzeByJSonPath.kt：补全 3 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_ANALYZE, ...)` 调用
- [ ] 4.2 AnalyzeUrl.kt：补全 1 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_ANALYZE, ...)` 调用

## 5. 网络请求模块日志补全

- [ ] 5.1 SSLHelper.kt：补全 5 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_HTTP, ...)` 调用
- [ ] 5.2 OkHttpExceptionInterceptor.kt：补全 2 处 catch 块的 `AppLog.putDebugWithTag(AppLog.TAG_HTTP, ...)` 调用
- [ ] 5.3 评估 ObsoleteUrlFactory.kt（15 个 catch，遗留代码，低优先级）
- [ ] 5.4 评估 StrResponse.kt（1 个 catch，低优先级）

## 6. 数据层日志补全评估

- [ ] 6.1 评估 AppDatabase.kt 的 1 处 catch 是否需要补全
- [ ] 6.2 评估 BaseSource.kt 的 3 处 catch 是否需要补全
- [ ] 6.3 评估 BookChapter.kt 的 3 处 catch 是否需要补全
- [ ] 6.4 评估 ReplaceRule.kt 的 1 处 catch 是否需要补全

## 6A. RSS 子模块日志补全

- [ ] 6A.1 Rss.kt：补全 catch 块日志 + RSS 源请求/解析/文章获取的成功/失败日志（使用 TAG_RSS）
- [ ] 6A.2 RssParserByRule.kt：补全 RSS 规则解析的成功/失败日志 + 1 处 catch 日志缺失
- [ ] 6A.3 RssSearchModel.kt：补全 RSS 搜索的成功/失败日志

## 6B. 内容处理模块日志评估

- [ ] 6B.1 评估 ContentProcessor.kt 的关键操作成功/失败日志（正文获取/替换/简繁/分段/图片解密）
- [ ] 6B.2 评估 BookHelp.kt 的关键操作成功/失败日志
- [ ] 6B.3 补全内容处理模块缺失的关键操作日志（使用 TAG_CONTENT）

## 7. 关键操作成功/失败日志补全（维度2）

- [ ] 7.0 WebBook 模块：补全约22处关键操作成功/失败日志（搜索/详情/目录/正文/发现页的开始/成功/失败）
- [ ] 7.1 规则引擎模块：补全 JS 执行/CSS/XPath/JSONPath/正则解析的成功/失败日志
- [ ] 7.2 网络请求模块：补全 HTTP 请求/响应/重试/SSL 的成功/失败日志
- [ ] 7.3 RSS 子模块：补全 RSS 源请求/解析/文章获取的成功/失败日志（与 6A 合并执行）

## 7A. 关键参数日志补全（维度3）

- [ ] 7A.1 WebBook 模块：补全约10处关键参数日志（URL构建/规则解析结果/响应状态码）
- [ ] 7A.2 规则引擎模块：补全规则表达式/解析结果/URL变量替换的参数日志
- [ ] 7A.3 网络请求模块：补全请求URL(路径模式化)/响应状态码/Cookie操作的参数日志
- [ ] 7A.4 RSS 子模块：补全 RSS 源URL/解析结果的参数日志

## 8. ai_tests 日志获取脚本新增

- [ ] 8.1 新增 collect_app_log.py：通用日志获取脚本
  - [ ] 8.1.1 支持按模块 tag 过滤 logcat（如 WebBook:D / AnalyzeRule:D / HttpHelper:D）
  - [ ] 8.1.2 支持 adb pull 获取 AppLog 文件日志（externalCacheDir/logs/）
  - [ ] 8.1.3 支持日志异常提取（FATAL / ANR / CRASH / Exception）
- [ ] 8.2 更新 fixed_test_workflow.md 添加新脚本使用说明

## 9. 验证

- [ ] 9.1 编译验证（确认无编译错误）
- [ ] 9.2 Grep 验证（确认所有修改文件中 AppLog.putDebugWithTag 调用确实存在）
- [ ] 9.3 日志规范文档验证（确认更新内容存在）
- [ ] 9.4 ai_tests 脚本验证（确认脚本可运行）
- [ ] 9.5 recordLog 关闭时零开销验证（确认 putDebugWithTag 在 recordLog=false 时不执行任何操作）

## 10. 文档同步

- [ ] 10.1 更新 docs/INDEX.md（添加新规范条目 / 链接）
- [ ] 10.2 确认 docs/project-rules/logging_rules.md 已同步更新（与 2.6 一致）
- [ ] 10.3 确认 docs/project-rules/logging-during-refactoring.md 已同步更新（与 2.7 一致）
- [ ] 10.4 确认 ai_tests/docs/fixed_test_workflow.md 已同步更新（与 8.2 一致）
