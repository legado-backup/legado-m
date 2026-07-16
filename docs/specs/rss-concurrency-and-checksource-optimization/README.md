# 项目：订阅源解析并发配置化 + 书源/订阅源校验去重优化

## 概述

本项目包含两个相关需求，均围绕订阅源（RssSource）的功能完善：

1. **需求一（解析并发+图片加载并发配置化）**：将 `RssParserByRule.kt` 中硬编码的 `Semaphore(6)` 改为可配置项，支持全局默认值和每源独立配置。同时支持图片加载线程数配置。

2. **需求二（书源校验优化+订阅源校验去重）**：
   - 书源域名校验从 Socket 测试改为走 AnalyzeUrl 真实请求链路
   - 为订阅源新增完整校验功能（列表/搜索/分类/正文 5维度）
   - 一键去重：按域名+type多维度去重，保留维度成功多的源，重复源进回收站

## 状态

🔄 设计中（v4，检查点1已基于review-report.md完成BLK-1~3+ADJ-1~9全部修订）

**前置验证（实施前必须）**：编译测试 GlideExecutor.newSourceExecutor(threadCount: Int) 在 Glide 5.0.5 的可用性。验证失败则需求一降级（仅保留解析并发配置化）。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（4批13节） |

## 核心设计决策

### 需求一
- **双参数分离**：解析并发（默认3）+ 图片加载并发（默认5）独立配置
- **Glide线程池**：通过 `GlideBuilder.setSourceExecutor` 配置（需重启生效）
- **每源配置**：RssSource 新增 `parseConcurrency` 字段（0=使用全局）

### 需求二
- **书源校验复用+优化**：复用现有CheckSourceService.doCheckSource，优化域名校验(Socket→AnalyzeUrl)，不新增独立Service
- **订阅源校验全新新增**：CheckRssSource + CheckRssSourceService + CheckRssSourceConfig
- **域名校验改进**：通过 AnalyzeUrl 发起真实请求校验（支持源URL复杂性）
- **订阅源校验5维度**：域名/列表/搜索/分类/正文
- **多维度去重**：第一维度域名 + 第二维度type（网页/图片/视频）
- **去重后处理**：addGroup("重复源") 标记（可逆）

### 需求三
- **复用废弃weight字段**：BookSource已有weight(值一直为0基本废弃)，RssSource需新增
- **权重算法**：满分100，域名不可达=0分（一票否决）
- **基于分组状态计算**：通过hasGroup反推各维度结果，不修改doCheckSource结构（最小改动）
- **分值分配**：书源(域名20+搜索20+发现15+信息15+目录15+正文15)，订阅源(域名20+列表25+搜索20+分类15+正文20)
- **校验后自动回填**：校验完成立即回填source.weight，BookSourceSort.Weight排序自动生效

## 涉及文件

### 需求一（9文件修改）
- PreferKey.kt、AppConfig.kt、RssSource.kt、appDb.kt、RssParserByRule.kt、LegadoGlideModule.kt、pref_config_other.xml、OtherConfigFragment.kt、strings.xml

### 需求二（10文件：6修改+4新增）
- 修改：CheckSource.kt、CheckSourceService.kt、CheckSourceConfig.kt、dialog_check_source_config.xml、RssSourceActivity.kt、strings.xml
- 新增：CheckRssSource.kt、CheckRssSourceService.kt、CheckRssSourceConfig.kt、菜单资源

### 需求三（6文件：5修改+1新增）
- 新增：SourceWeightCalculator.kt（权重计算器）
- 修改：RssSource.kt（新增weight字段）、DatabaseMigrations.kt（migration_94_95合并weight）、CheckSourceService.kt（回填书源weight）、CheckRssSourceService.kt（回填订阅源weight）、RssSource.kt equal()（加入weight比较）
