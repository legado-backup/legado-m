# Skill HTML 获取能力增强

> 状态：🔄 设计中
> 创建日期：2026-06-14
> 优先级：P0

## 功能概述

增强 `legado-source-creator` Skill 的 HTML 获取能力和 CF 绕过能力，解决"CF 保护网站无法获取 HTML → 选择器只能猜测 → 大量低可信项需真机验证"的系统性问题。

## 核心能力

| 能力 | 说明 | 覆盖率提升 |
|------|------|-----------|
| **L0: CF JS Challenge 自动绕过** | `webView()` 自动通过 CF JS Challenge，Cookie 自动同步到 CookieStore；Turnstile 降级到 `startBrowserAwait()` | CF网站从不可用到可用 |
| **L1: HTML 获取回退链** | curl → Wayback Machine → CMS 样本库 → Google Cache → Playwright | 流程规范化 |
| **L2: CMS 样本库** | Top 5 CMS 标准HTML样本 + 选择器映射（来源于 GitHub 开源模板） | 60%→85% |
| **L3: Playwright 集成** | 浏览器自动化获取渲染后HTML + Cookie 导出 | →95% |
| **L4: JVM Cookie 注入** | CF Cookie 注入 JVM 仿真器，ajax() 请求可信度提升 | +3% |

## CF 盾深度分析

| CF 验证类型 | 自动绕过 | 方案 | 原理 |
|------------|---------|------|------|
| JS Challenge（5秒盾） | ✅ | `webView()` 自动通过 | WebView是真实浏览器引擎，执行CF JS→Cookie自动同步 |
| Managed Challenge (Turnstile) | ❌ | `startBrowserAwait()` 手动通过 | Turnstile检测自动化工具，需真实用户交互 |
| Interactive Challenge | ❌ | `startBrowserAwait()` 手动通过 | 需人工识别验证码 |

**纯Rhino JS无法破除CF盾**：CF验证JS高度混淆+依赖浏览器环境+检测浏览器指纹，Rhino不具备DOM/BOM/Canvas等API。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（含L0-L4完整需求+7个场景） |
| [design.md](./design.md) | 技术设计（含CF绕过方案+回退链+CMS样本库+7个架构决策） |
| [tasks.md](./tasks.md) | 任务清单（12个分组60+个任务项） |

## 问题背景

优化"优质资源(1080zyk)"订阅源时，5/9 个规则字段标记为"低可信需真机验证"，根因是 Cloudflare 拦截了 curl 请求，无法获取实际 HTML 结构。JVM MVP2 已支持 jsoup CSS 选择器验证，但缺少 HTML 输入。

## 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| CF JS Challenge 网站 | 需用户手动通过 | webView() 自动通过 |
| CF 保护网站低可信项 | 5/9 (56%) | ≤2/9 (≤22%) |
| 选择器验证覆盖率 | 0%（无HTML输入） | 85%+（CMS样本+Playwright） |
| 需真机验证项 | 5项 | ≤2项 |

## 回测验证闭环

> 不经过实际验证的优化=虚假优化。用"优质资源(1080zyk)"订阅源回测验证优化效果。

| 验证步骤 | 命令 | 预期结果 |
|---------|------|---------|
| 更新源配置 | 修改loginUrl为webView() | CF JS Challenge自动通过 |
| HTML获取验证 | `html_fetcher.py --url URL` | Wayback或CMS样本获取成功 |
| CMS样本验证 | `verify-selector.py --sample` | 6个选择器验证通过 |
| JVM MVP2验证 | `deep-verify.py --source` | 低可信项≤2个 |
| CF绕过验证 | 检查loginUrl/loginCheckJs | 配置格式正确 |
| 输出验证报告 | 对比优化前后 | 低可信项从5降到≤2 |
