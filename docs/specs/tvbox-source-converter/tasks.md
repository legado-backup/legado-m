# tasks.md — TVBox/影视仓播放源转化 legado 订阅源

> 状态：🔄 设计中
> 格式：`- [ ] X.Y` 任务清单

---

## 1. 准备工作

- [ ] 1.1 确认需求范围（影视仓 Site → legado RssSource 单向转化）
- [ ] 1.2 阅读 Site.java 源码，确认字段定义与 type 语义
- [ ] 1.3 阅读 RssSource.kt 源码，确认字段定义与 type 语义
- [ ] 1.4 阅读 RssSourceExtensions.kt，确认 sortUrl 解析格式（`分类名::url`）
- [ ] 1.5 阅读 WebBook.kt / BookSource.kt，确认规则体系与架构约束
- [ ] 1.6 确认编码规范（Coroutine.async 链式 / kotlin.runCatching / AppLog.put）

## 2. 数据结构设计

- [ ] 2.1 设计 TvBoxConvertResult 数据类（成功列表 / 跳过列表 / 失败列表）
- [ ] 2.2 定义 Site 输入 DTO（纯字段，不引入影视仓依赖）
- [ ] 2.3 定义字段映射表（Site 字段 → RssSource 字段）
- [ ] 2.4 定义类型适配表（Site.type 0-4 → RssSource.type + 规则集）

## 3. 核心实现

- [ ] 3.1 实现 TvBoxSourceConverter object 主入口（convert 批量 / convertSite 单源）
- [ ] 3.2 实现 TVBox JSON 解析（提取 sites 数组，异常捕获）
- [ ] 3.3 实现 TvBoxSiteMapper 字段映射器（key/name/header 直映）
- [ ] 3.4 实现 Site.header(Map) → RssSource.header(JSON) 序列化
- [ ] 3.5 实现 Site.categories → RssSource.sortUrl 拼接（`分类名::url` 格式）
- [ ] 3.6 实现 searchable → enabled 映射

## 4. 类型分派与规则生成

- [ ] 4.1 实现 TvBoxRuleDispatcher 按 Site.type 分派
- [ ] 4.2 实现 type=0 采集API 通用 JSON 模板规则生成
- [ ] 4.3 实现 type=1 JSON 类型 JSONPath 规则生成
- [ ] 4.4 实现 type=2 jar 爬虫降级（singleUrl=true + 嗅探配置 + 降级标注）
- [ ] 4.5 实现 type=3 XPath 类型规则生成
- [ ] 4.6 实现 type=4 正则类型规则生成
- [ ] 4.7 实现 TvBoxRuleTemplates 模板集合（五套模板常量）

## 5. 降级与冲突处理

- [ ] 5.1 实现降级标注写入 sourceComment（格式：`// 降级说明: xxx | 已知上限: xxx | 升级路径: xxx`）
- [ ] 5.2 实现 sourceUrl 冲突检测（跳过 + 记录源[N]代号）
- [ ] 5.3 实现单源转化异常捕获（不中断批量流程，记录失败源[N]）
- [ ] 5.4 实现转化报告生成（成功数 / 跳过数 / 失败数 + 代号列表）

## 6. 输出安全与合规

- [ ] 6.1 确认日志与报告不输出源名称/域名/URL（统一用源[N]代号）
- [ ] 6.2 确认 sourceComment 降级标注不含业务数据（只含技术说明）
- [ ] 6.3 确认异常堆栈过滤业务字段（仅输出异常类型与字段名）

## 7. 单元测试

- [ ] 7.1 测试字段直映（key→sourceUrl, name→sourceName, header Map→JSON）
- [ ] 7.2 测试 type=0 采集API 模板规则生成
- [ ] 7.3 测试 type=1 JSON 规则生成
- [ ] 7.4 测试 type=2 jar 降级（singleUrl=true + 嗅探 + sourceComment 标注）
- [ ] 7.5 测试 type=3 XPath 规则生成
- [ ] 7.6 测试 type=4 正则规则生成
- [ ] 7.7 测试 categories → sortUrl 拼接格式
- [ ] 7.8 测试 sourceUrl 冲突跳过逻辑
- [ ] 7.9 测试单源异常不中断批量流程
- [ ] 7.10 测试空 sites 数组与字段缺失的健壮性

## 8. 集成与验证

- [ ] 8.1 编写集成测试：输入示例 TVBox JSON，输出 RssSource JSON 数组
- [ ] 8.2 验证转化后 JSON 可被 legado RssSource 反序列化
- [ ] 8.3 验证转化后源的 sortUrl 格式符合 RssSourceExtensions 解析要求
- [ ] 8.4 验证降级标注格式符合编码哲学规范
- [ ] 8.5 验证输出安全（日志/报告无业务数据泄漏）

## 9. 文档与交付

- [ ] 9.1 更新 docs/specs/tvbox-source-converter/ 四文档状态（设计中 → 已实现）
- [ ] 9.2 在 docs/INDEX.md 添加本规格文档索引
- [ ] 9.3 更新 assets/updateLog.md（基于真实代码变更分析）
- [ ] 9.4 记录经验到 basic-memory（关键决策 / 文件路径 / 任务状态）
- [ ] 9.5 完成任务前逐项核对强制检查清单（无违禁词 / 无调试日志 / updateLog 已更新）
