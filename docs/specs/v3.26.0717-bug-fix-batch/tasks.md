# Tasks - v3.26.0717 真机测试 Bug 批量修复

## 1. 准备工作

- [x] 1.1 确认日志分析结果（已解压，崩溃根因已定位 ConcurrentModificationException）
- [x] 1.2 阅读相关源码（已完成 6 个问题的代码定位）
- [x] 1.3 创建 issues-found.md 问题追踪文档

## 2. 问题 3 修复：替换规则崩溃（最高优先级）

- [x] 2.1 修复 `ReadBook.kt:ruleMatchesOfChapter` 添加本地副本 `val rulesSnapshot = highlightRules.toList()`
  - Action: 待执行
  - Observation: 待观察
  - Adapt: 待调整
- [x] 2.2 验证修复不影响高亮规则加载和缓存逻辑
- [x] 2.3 编译验证

## 3. 问题 1 修复：订阅源解析并发显示

- [x] 3.1 修改 `RssSourceEditActivity.kt` 显示逻辑：parseConcurrency=0 时显示系统配置值并标注"（继承全局）"
- [x] 3.2 保留单源配置保存能力
- [x] 3.3 编译验证

## 4. 问题 4 修复：其他设置并发数显示

- [x] 4.1 修改 `strings.xml` 新增带占位符的字符串模板（rss_parse_concurrency_summary_value / image_load_concurrency_summary_value）
- [x] 4.2 修改 `OtherConfigFragment.kt:upPreferenceSummary` 使用带值的字符串模板
- [x] 4.3 编译验证

## 5. 问题 5 修复：域名分组/排序/反序

- [x] 5.1 修复 `BookSourceActivity.kt:getSourceHost` 异常 URL 处理（http/https 协议名过滤为 "#"）
- [x] 5.2 修改域名分组排序逻辑：同组内按 weight 降序
- [x] 5.3 修改域名分组排序逻辑：支持 sortAscending 反序
- [x] 5.4 验证搜索过滤后域名分组不混入未过滤项
- [x] 5.5 编译验证

## 6. 问题 2 修复：高亮颜色选择器主题适配

- [x] 6.1 创建暗色主题 ContextWrapper 包装 ColorPickerDialog
- [x] 6.2 修改 `HighlightRuleEditDialog.kt:createColorPickerDialog` 使用包装后的 Context
- [x] 6.3 编译验证
- [x] 6.4 真机验证：暗色主题下预设色块正常显示

## 7. 问题 6 评估：书源/订阅源视图布局差异

- [x] 7.1 读取 BookSourceAdapterCompact/Grid 布局 XML
- [x] 7.2 读取书架 BooksAdapterListByGrid 布局 XML
- [x] 7.3 对比字段、间距、字号、图标位置差异
- [x] 7.4 列出差异清单
- [x] 7.5 用 AskUserQuestion 向用户确认是否需要修复（按差异清单逐项确认）

## 8. 综合验证

- [x] 8.1 全量编译 `./gradlew assembleAppDebug`
- [x] 8.2 安装到模拟器（127.0.0.1:21503）
- [x] 8.3 编写真机测试清单（按 S1-S5 场景）
- [x] 8.4 用 AskUserQuestion 通知用户进行 Phase 11 真机测试

## 9. 文档同步

- [x] 9.1 编译前更新 `app/src/main/assets/updateLog.md`
- [x] 9.2 更新 `docs/INDEX.md` spec 状态
- [x] 9.3 更新 `docs/specs/v3.26.0717-bug-fix-batch/issues-found.md` 修复状态
- [x] 9.4 评估是否需要更新子规范（如 global-thinking-checklist.md）
- [x] 9.5 写入项目记忆：本次修复的关键决策

## 10. 收尾沉淀

- [x] 10.1 反思本次修复是否有需要沉淀的工作方法
- [x] 10.2 检查"任务完成前强制检查清单"7 项
- [x] 10.3 用 AskUserQuestion 请求用户最终验收
