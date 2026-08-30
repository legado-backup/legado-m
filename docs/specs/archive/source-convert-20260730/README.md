# 书源/订阅源一键互转功能

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 状态: 设计中（V9 - R5降级/sourceRegex/音频评级3项CRITICAL补充版）

## 功能概述

在前端提供书源(BookSource)与订阅源(RssSource)的一键互转功能，用户可方便地将一种源转换为另一种格式，复用已有的规则配置。通过12个改动（9个源码改动+1个转换逻辑改动+1个过滤改动+1个运行时降级改动）实现运行时行为级别的100%互转，所有新增字段默认null不影响现有功能。

## 核心能力

- **书源→订阅源**：将书源的搜索/发现规则映射为订阅源的列表规则，提取封面/标题/链接等字段
- **订阅源→书源**：将订阅源的列表规则映射为书源的搜索/发现规则，保留可复用的解析规则，**智能生成BookInfoRule+TocRule解决致命缺陷**
- **100%互转**：12个改动消除所有"不可弥补项"、"运行时行为差异"、"运行时流程衔接"、"功能性字段缺失"和"运行时流程降级"问题，确保转换后源完全可用
- **字段映射透明**：转换过程中清晰展示哪些字段可直接映射、哪些已通过源码改动弥补
- **预览确认**：转换前展示映射预览+可用性评估+弥补提示，用户确认后才执行写入

## 可行性评估

### 结论

**通过12个改动实现7个方向的接近100%互转**（音频方向因RssSource无音频类型为架构限制）：

| 转换方向 | 原始可用性 | V7可用性 | V8可用性 | V9可用性 | 关键改进 |
|---------|----------|---------|---------|---------|---------|
| 书源→订阅源(文本) | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | subContent+author+分页+替换+sourceRegex |
| 书源→订阅源(图片) | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | imageDecode+副文+分页+替换 |
| 书源→订阅源(视频) | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | webJs+副文+分页+替换+**R5降级(V9)** |
| 书源→订阅源(音频) | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★★☆ | **V9修正：RssSource无音频类型，AudioPlay仅支持BookSource** |
| 订阅源→书源(文本) | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤 |
| 订阅源→书源(图片) | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤 |
| 订阅源→书源(视频) | ★☆☆☆☆ | ★★★★★ | ★★★★★ | ★★★★★ | author+URL过滤+routeRule+**R5降级(V9)** |

**十二大核心改进**：
1. **智能TocRule生成**（订阅源→书源）：ruleArticles→chapterList, ruleTitle→chapterName, ruleLink→chapterUrl 智能构造TocRule
2. **imageDecode源码弥补**：RssSource新增imageDecode字段+ImageUtils支持内容图片解密
3. **webJs源码弥补**：RssSource新增ruleWebJs+Rss.kt传jsStr参数，仅1行改动
4. **视频多线路源码弥补**：ContentRule新增routeRule+routeContentRule，VideoPlay支持BookSource多线路
5. **运行时行为弥补**：RssSource新增ruleNextContentUrl(分页)+ruleReplaceRegex(替换)，在Rss.kt中增加分页循环和内容替换
6. **运行时流程衔接弥补**：智能BookInfoRule+TocRule联合生成，BookInfoRule.tocUrl指向sortUrl页面
7. **副文/歌词/弹幕弥补（V8）**：RssSource新增ruleSubContent+Rss.kt追加副文，解决音频源歌词、视频源弹幕丢失问题
8. **作者信息弥补（V8）**：RssSource新增ruleAuthor+RssParserByRule解析，解决双向转换作者信息丢失问题
9. **URL过滤弥补（V8）**：ContentRule新增contentWhitelist/contentBlacklist+BookContent过滤，解决订阅源→书源URL过滤丢失问题
10. **视频R5降级弥补（V9）**：BookSource视频播放分支content为空时R5自动提取，解决无ruleContent的视频源转换后无法播放
11. **sourceRegex弥补（V9）**：RssSource新增ruleSourceRegex+Rss.kt传sourceRegex参数，解决WebView资源嗅探功能丢失
12. **imageStyle弥补（V9）**：RssSource新增ruleImageStyle，确保图片显示样式双向映射完整

> **V9关键发现**：V8版遗漏了3个运行时流程级问题——①BookSource视频播放路径无R5降级机制（content为空时抛异常，而RssSource有完整R5自动提取流程）②ContentRule.sourceRegex未映射（WebView资源嗅探，音频源核心功能）③音频源评级虚高（RssSource无音频类型，AudioPlay仅支持BookSource，音频播放体验丢失）。V9通过改动10/11/12全部弥补前两项，第三项为架构限制。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格 |
| [design.md](./design.md) | 技术设计 |
| [tasks.md](./tasks.md) | 任务清单 |
