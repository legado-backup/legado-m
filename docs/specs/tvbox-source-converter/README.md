# TVBox/影视仓播放源转化 legado 订阅源

> 将影视仓（FongMi/TV）的播放源（Site JSON 格式）转化为 legado（阅读M）的订阅源（RssSource 格式）。

**状态**：🔄 设计中

---

## 功能概述

影视仓与 legado 是两个独立的规则引擎生态，源格式互不兼容。本功能提供单向转化器，将影视仓的 `Site` bean（站点播放源）转化为 legado 的 `RssSource`（订阅源），使原属影视仓生态的播放源能在 legado 中以订阅源形式加载、浏览与播放。

转化器聚焦于"字段映射 + 类型适配 + 规则降级"，对影视仓生态中无法直接等价映射的能力（如 jar 爬虫、采集站私有 API 协议）提供明确的降级策略，并在源注释中标注降级信息，便于用户后续手动修正。

---

## 核心能力

| 能力 | 说明 |
|------|------|
| 字段映射 | 将 Site 的 key/name/api/header/categories 等字段映射到 RssSource 对应字段 |
| 类型适配 | 将 Site.type(0-4) 适配到 legado 规则体系（CSS/JSONPath/XPath/正则/JS）与 RssSource.type(0网页/1图片/2视频) |
| 规则降级 | 对无法直接转化的 jar 爬虫、采集站私有 API，降级为 API 直调或 WebView 嗅探，并标注降级说明 |
| 批量处理 | 支持从 TVBox JSON 配置文件（含 sites 数组）批量导入，输出 legado 订阅源 JSON 数组 |
| 兼容输出 | 转化后的源需在 legado 中可正常加载列表、执行搜索、解析正文 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（字段映射表/ADR 决策/数据流图/文件变更） |
| [tasks.md](./tasks.md) | 实施任务清单（分阶段 `- [ ] X.Y` 格式） |

---

## 参考源码

| 来源 | 文件 | 用途 |
|------|------|------|
| 影视仓 | `Site.java`（forks-comparison/TV-fongmi） | 输入源 bean 定义 |
| legado | `RssSource.kt` | 输出源实体类 |
| legado | `RssSourceExtensions.kt` | sortUrl 解析逻辑参考 |
| legado | `WebBook.kt` | 网络请求层架构参考 |
| legado | `BookSource.kt` | 字段结构参考 |

---

## 输出安全声明

本文档及配套 spec/design/tasks 文档仅包含技术分析（字段名、类型、方法签名、架构设计），不包含任何源名称、域名、URL、cookie 等业务数据。示例中出现的站点统一以代号（站点A/B/C）或路径模式（`/path/{id}`）表示。
