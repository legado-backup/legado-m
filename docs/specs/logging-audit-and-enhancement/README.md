# 日志规范全面审查与补全完善

> 状态标记：✅ 实施完成，真机验证通过

## 功能概述

全面审查 Legado 项目的日志规范和日志覆盖情况，站在"AI 通过 ai_tests 获取日志发现问题"的角度，识别日志缺失的关键节点，补全核心模块的日志记录，优化日志规范文档。

核心目标：让异常不再被静默吞掉，让 ai_tests 能够通过统一模块 tag 过滤获取关键操作的成功/失败日志，从而在真机测试中快速定位问题。

## 核心能力

1. 审查现有日志规范（`logging_rules.md` + `logging-during-refactoring.md`）的合理性
2. 识别核心模块（WebBook/规则引擎/网络层/数据层）的日志缺失
3. 补全 catch 块中的 `AppLog.putDebugWithTag` 调用（recordLog 守卫，关闭时零开销，异常不再被静默吞掉）
4. 添加关键操作的成功/失败日志（使用统一模块 tag，便于 ai_tests 过滤）
5. 优化日志规范，增加 ai_tests 可用 tag 约定
6. 新增 ai_tests 通用日志获取脚本

## 关键发现（需求分析结果）

| 模块 | catch 块数 | AppLog 调用数 | 异常无日志占比 | 说明 |
|------|-----------|--------------|----------------|------|
| WebBook | 20 | 2 | 90% | 大量异常被静默吞掉 |
| 规则引擎 | 5 | 3 | 40% | 部分异常无日志 |
| 网络请求 | 34 | 18 | 47% | 近半异常无日志 |
| Service 层 | 23 | 69 | 覆盖充分 | 日志覆盖良好 |
| 数据层 | 8 | 18（13 个在 migrations 中） | 部分缺失 | migrations 之外覆盖不足 |

补充发现：
- ai_tests 只能获取 logcat 日志，`AppLog.put` 在 release 包中不输出到 logcat
- 缺少统一的按模块 tag 过滤的日志获取脚本

## 三层日志体系

| 层 | 文件 | 输出渠道 | 控制条件 |
|----|------|---------|---------|
| AppLog | `constant/AppLog.kt` | 内存日志 + 文件日志 + logcat | 始终输出 |
| LogUtils | `utils/LogUtils.kt` | 文件日志 | Level 由 `recordLog` 控制 |
| DebugLog | `utils/DebugLog.kt` | 纯 logcat | 仅 `BuildConfig.DEBUG` 时输出 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Architecture Decisions/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单 |

## 状态标记

✅ 实施完成（三个包编译通过 + 真机验证日志正确记录）
