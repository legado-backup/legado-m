# 真机测试计划：rss-concurrency-and-checksource-optimization

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **状态**：🔄 设计中
> **关联文档**：[rss-concurrency-and-checksource-optimization](../rss-concurrency-and-checksource-optimization/README.md)
> **创建时间**：2026-07-15

## 功能概述

针对 `rss-concurrency-and-checksource-optimization` 的所有变更功能项（24项）进行真机端到端测试，验证：
1. 并发配置化（rssParseConcurrency + imageLoadConcurrency）的UI显示和修改生效
2. domainCheckMode 选择项的UI交互（勾选"域名"CheckBox才显示RadioGroup）
3. 书源/订阅源校验执行（用真实书源数据）
4. CheckSourceService/CheckRssSourceService 启动
5. SourceWeightCalculator 权重计算+回填
6. 深度分析 logcat 日志确认校验流程正确
7. 测试经验和教训沉淀到 ai_tests/docs/

## 核心能力

- **真实数据测试**：使用模拟器中已导入的真实书源/订阅源数据
- **深度日志分析**：logcat 抓取 CheckSourceService/CheckRssSourceService/SourceWeightCalculator 相关日志
- **数据库验证**：pull DB 查询 weight 字段是否回填
- **UI交互验证**：domainCheckMode RadioGroup 需勾选"域名"CheckBox才显示
- **经验沉淀**：测试中的 bug 修复和测试方法论沉淀到 ai_tests/docs/

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 测试需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 测试技术方案（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 测试任务清单 |

## 测试环境

- **设备**：MEmu 模拟器（127.0.0.1:21503）
- **包名**：io.legado.app.debug
- **ADB**：D:/Program Files/Microvirt/MEmu/adb.exe
- **Python**：ai_tests/venv/Scripts/python.exe
- **真实数据**：用户已导入真实书源到模拟器（temp/output/book/groups/ 150+ JSON）
