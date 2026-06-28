# JVM 仿真服务端：WebView 支持 + 测试有效性修复 + 债务清理

> **状态**：🔄 设计中
> **前置项目**：[jvm-extract-refactor](../jvm-extract-refactor/)（已完成）
> **创建日期**：2026-06-20

---

## 功能概述

jvm-extract-refactor 项目完成了从 Legado 源码抽取核心类的架构重构，但在深度核查中发现三个严重问题：

1. **测试有效性缺陷**：`debug()` 方法吞掉所有异常，batch 模式只检查"是否抛异常"而非"是否获取到有效数据"，导致"100%通过率"是假象
2. **WebView 完全不可用**：`BackstageWebView` 直接抛 `UnsupportedOperationException`，任何需要 JS 渲染的源在仿真环境中无法测试
3. **代码/文档债务**：5 个 `nul` 文件、10+ 临时测试脚本、24 个 temp-analysis 文档未清理

本项目修复这三个问题，使仿真工具链真正可用于 Skill 的端到端书源/订阅源验证。

---

## 核心能力

| 能力 | 当前状态 | 目标状态 |
|------|---------|---------|
| 测试有效性校验 | ❌ 只检查是否抛异常 | ✅ 检查文章列表非空、正文长度>0、标题非空 |
| WebView JS 渲染 | ❌ 直接抛异常 | ✅ Python客户端+Selenium 委托渲染 |
| `@webjs:` 规则支持 | ❌ 直接抛异常 | ✅ Python客户端执行JS后回传 |
| 登录/验证码场景 | ❌ 直接抛异常 | ✅ 标记需用户介入 + 诊断信息 |
| 临时文件清理 | ❌ 5个nul+10+脚本+24文档 | ✅ 清理完成 |
| 经验教训提取 | ❌ 太浅（只记bug修复） | ✅ 可指导后续书源创建的模式 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术方案：WebView委托协议 + 测试有效性校验 + 清理清单 |
| [tasks.md](./tasks.md) | 任务清单（3个方向并行） |

---

## 验收标准

1. **测试有效性**：batch 结果中 `success=true` 的源必须有 `articleCount>0` 或 `contentLength>0`，空数据不算成功
2. **WebView 支持**：需要 webView 的源能通过 Python客户端+Selenium 获取渲染后 HTML，并传回 JAR 解析
3. **债务清理**：0 个 `nul` 文件、临时脚本归档或删除、temp-analysis 文档评估保留/删除
4. **经验教训**：从测试中提取可指导后续书源创建的模式（网站特征→规则类型→常见陷阱）
