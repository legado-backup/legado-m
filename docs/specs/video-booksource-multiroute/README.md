# README.md — video-booksource-multiroute

## 功能概述

让内置视频播放器兼容"视频书源"（用书源规则表达的视频内容）：在不修改书源现有字段解析逻辑的前提下，将多线路多集映射到书源既有字段体系（ruleToc/ruleContent），使视频书源获得与视频订阅源一致的多线路/多集/直链优先/嗅探兜底播放体验。

## 核心能力

1. **字段映射（不新增书源字段）**：多集 → `ruleToc`（目录）、视频地址 → `ruleContent`（正文）、多线路 → 目录卷结构（isVolume 卷=线路）；订阅源新增字段 ruleRoutes/ruleEpisodes **不进入** BookSource（用户裁决 2026-09-02）
2. **解析分级标准 L0-L3**（用户裁决：五类解析全支持，JS 为最后手段）：L0 零规则（MacCMS 自动规范化）/ L1 四条 JSONPath（`$.chapters[*]`，推荐标准写法）/ L2 CSS·XPath·正则（HTML 站）/ L3 JS（archive 兼容线）
3. **管线复用**：播放管线对视频书源复用订阅源已验证的 routes 规范化 + 按需采集 + direct-route-first 机制
4. **正文嗅探**：视频书源正文为播放页 URL 或空时，走既有三层嗅探链（直链优先，嗅探兜底）；ruleContent 五类解析任选
5. **正文入口**：视频书源正文页（阅读器）提供视频播放入口
6. **兼容底线**：archive 视频书源（@js 写法）导入必须可用（真机硬用例）

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术方案/ADR/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 |

## 状态标记

🔄 设计中
