# 书源/订阅源一键互转 - 需求规格

> 状态: 设计中（V9）

## Intent

用户在前端（书源管理/订阅源管理页面）可以通过一键操作将书源转换为订阅源，或将订阅源转换为书源。转换过程中复用可映射的字段和规则，对无法映射的字段给出明确提示。

## Scope

### In Scope
- 书源→订阅源转换：基础字段+搜索/发现规则映射为列表规则
- 订阅源→书源转换：基础字段+列表规则映射为搜索/发现规则
- 转换预览：展示映射关系和丢失字段的提示
- 类型映射：bookSourceType ↔ RssSource.type 的对应关系
- 100%互转：通过12个改动（9个源码改动+1个转换逻辑改动+1个过滤改动+1个运行时降级改动）实现所有字段完整转换
- 运行时流程衔接：BookInfoRule.tocUrl指向sortUrl页面+TocRule.nextTocUrl分页映射（V7新增CRITICAL）
- 副文/歌词/弹幕支持：ContentRule.subContent↔RssSource.ruleSubContent双向映射（V8新增MAJOR）
- 作者信息支持：BookListRule.author↔RssSource.ruleAuthor双向映射（V8新增MAJOR）
- URL过滤支持：RssSource.contentWhitelist/contentBlacklist↔ContentRule双向映射（V8新增MAJOR）
- 视频R5降级：BookSource视频播放分支content为空时R5自动提取（V9新增CRITICAL）
- WebView资源嗅探：ContentRule.sourceRegex↔RssSource.ruleSourceRegex双向映射（V9新增MAJOR）
- 图片显示样式：ContentRule.imageStyle↔RssSource.ruleImageStyle双向映射（V9新增MINOR）

### Out of Scope
- 不新增统一源类型（保持两个独立实体）
- 不处理数据库表合并（保持bookSource和rssSources独立表）

## Approach

### Selected Approach

**100%互转+预览确认**：

1. 转换器（SourceConverter）在两个方向上建立字段映射表
2. 12个改动确保所有不可弥补项变为可弥补（imageDecode/routeRule/ruleWebJs/ruleNextContentUrl/ruleReplaceRegex/BookInfoRule+TocRule联合生成/ruleSubContent/ruleAuthor/contentWhitelist+contentBlacklist/R5降级/ruleSourceRegex/ruleImageStyle）
3. 转换前展示预览对话框，列出可映射字段和已通过JS/源码弥补的字段
4. 用户确认后执行转换，生成目标源实体并写入数据库
5. 保留原始源不做删除，转换结果作为新源添加

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 无损转换（无源码改动） | 保证所有字段完美映射 | 两端数据结构差异大，需3个源码改动才能实现100%互转 |
| 统一源类型 | 合并BookSource和RssSource为一个实体 | 需要重写整个解析引擎，改动范围巨大，风险高 |
| 后端转换服务 | 在服务端做转换 | 不需要网络，纯本地操作更合理 |

## Requirements

### REQ-01: 书源→订阅源转换
- 将BookSource的基础字段映射到RssSource对应字段
- 将SearchRule.bookList/ExploreRule.bookList映射为ruleArticles
- 将SearchRule.name/bookUrl/coverUrl/intro映射为ruleTitle/ruleLink/ruleImage/ruleDescription
- 将ContentRule.content映射为ruleContent
- 将exploreUrl映射为sortUrl
- bookSourceType映射为RssSource.type(0→0, 1→0, 2→1, 4→2)
- ContentRule.imageDecode映射为RssSource.imageDecode（源码改动1）
- ContentRule.webJs映射为RssSource.ruleWebJs（源码改动3）
- ContentRule.nextContentUrl映射为RssSource.ruleNextContentUrl（源码改动4，V7修正：非ruleNextPage）
- ContentRule.replaceRegex映射为RssSource.ruleReplaceRegex（源码改动5）
- TocRule.nextTocUrl映射为RssSource.ruleNextPage（V7新增：目录分页=列表分页）
- ContentRule.subContent映射为RssSource.ruleSubContent（源码改动7，V8新增：副文/歌词/弹幕）
- SearchRule/ExploreRule.author映射为RssSource.ruleAuthor（源码改动8，V8新增：作者信息）
- ContentRule.contentWhitelist映射为RssSource.contentWhitelist（源码改动9，V8新增：URL白名单）
- ContentRule.contentBlacklist映射为RssSource.contentBlacklist（源码改动9，V8新增：URL黑名单）
- ContentRule.sourceRegex映射为RssSource.ruleSourceRegex（源码改动11，V9新增：WebView资源嗅探）
- ContentRule.imageStyle映射为RssSource.ruleImageStyle（源码改动12，V9新增：图片显示样式）
- BookSource视频播放分支content为空时触发R5自动提取（源码改动10，V9新增：视频降级机制）
- TocRule/BookInfoRule/ReviewRule等无对应字段，在预览中标记为"不影响订阅源功能"

### REQ-02: 订阅源→书源转换
- 将RssSource的基础字段映射到BookSource对应字段
- 将ruleArticles映射为SearchRule.bookList
- 将ruleTitle/ruleLink/ruleImage/ruleDescription映射为SearchRule.name/bookUrl/coverUrl/intro
- 将ruleContent映射为ContentRule.content
- 将sortUrl映射为exploreUrl
- RssSource.type映射为bookSourceType(0→0, 1→2, 2→4)
- RssSource.imageDecode映射为ContentRule.imageDecode（源码改动1）
- RssSource.ruleRoutes映射为ContentRule.routeRule（源码改动2）
- RssSource.ruleEpisodes映射为ContentRule.routeContentRule（源码改动2）
- RssSource.ruleNextContentUrl映射为ContentRule.nextContentUrl（源码改动4反向映射）
- RssSource.ruleReplaceRegex映射为ContentRule.replaceRegex（源码改动5反向映射）
- 智能生成TocRule（ruleArticles→chapterList, ruleTitle→chapterName, ruleLink→chapterUrl, ruleNextPage→nextTocUrl）
- 智能生成BookInfoRule（tocUrl指向sortUrl页面, name=ruleTitle, coverUrl=ruleImage, intro=ruleDescription）（V7改动6新增CRITICAL）
- RssSource.ruleNextPage映射为TocRule.nextTocUrl（V7修正：列表分页→目录分页）
- RssSource.ruleNextContentUrl映射为ContentRule.nextContentUrl（源码改动4反向映射）
- RssSource.ruleSubContent映射为ContentRule.subContent（源码改动7反向映射，V8新增）
- RssSource.ruleAuthor映射为SearchRule.author+ExploreRule.author（源码改动8反向映射，V8新增）
- RssSource.contentWhitelist映射为ContentRule.contentWhitelist（源码改动9反向映射，V8新增）
- RssSource.contentBlacklist映射为ContentRule.contentBlacklist（源码改动9反向映射，V8新增）
- RssSource.ruleSourceRegex映射为ContentRule.sourceRegex（源码改动11反向映射，V9新增）
- RssSource.ruleImageStyle映射为ContentRule.imageStyle（源码改动12反向映射，V9新增）

### REQ-03: 转换预览确认
- 转换前弹出预览对话框，展示：
  - 可映射字段数量和列表
  - 将丢失的字段列表
  - 需手动补充的规则提示
- 用户确认后才执行转换

### REQ-04: UI入口
- 书源管理页面：长按/菜单添加"转为订阅源"选项
- 订阅源管理页面：长按/菜单添加"转为书源"选项
- 支持批量转换（多选后批量操作）

## Scenarios

### Scenario 1: 将书源转为订阅源
- 前置条件：用户在书源管理页面
- 操作：长按某个书源→选择"转为订阅源"→预览映射→确认→生成订阅源
- 预期：订阅源列表出现新源，基础信息和部分规则可用，目录/详情规则丢失需手动补充

### Scenario 2: 将视频订阅源转为书源
- 前置条件：用户在订阅源管理页面，有一个type=2的视频订阅源
- 操作：长按→选择"转为书源"→预览映射→确认→生成书源(bookSourceType=4)
- 预期：书源列表出现新的视频书源，多线路/多集通过routeRule+routeContentRule支持

### Scenario 3: 批量转换
- 前置条件：用户在书源管理页面
- 操作：多选5个书源→批量"转为订阅源"→逐个预览→确认→批量生成
- 预期：5个新订阅源被添加到订阅源列表
