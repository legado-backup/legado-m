# 线程池配置全面审查 - 任务清单

> 任务目标：对 Legado 项目中所有线程池配置点进行全面审查，识别泄漏风险、性能瓶颈与默认值合理性问题，输出优化建议并按用户确认实施。

---

## 1. 准备工作
- [x] 1.1 确认审查范围（已完成需求分析，见 spec.md）
- [x] 1.2 阅读相关源码（已完成调研：ExecutorService.kt/Coroutine.kt/DispatchersMonitor.kt等13个配置点）
- [x] 1.3 创建 docs/specs/thread-pool-audit/ 四文档目录（已完成）
- [x] 1.4 设计审查完成（用户2026-07-26压缩恢复后确认继续审查）

## 2. FixedThreadPool 创建点审查（8个业务线程池）
- [x] 2.1 审查 CheckSourceService.kt:66（书源校验，searchThreadCount，Service销毁关闭）✅ 子代理1完成
- [x] 2.2 审查 CheckRssSourceService.kt:63（RSS源校验，searchThreadCount，Service销毁关闭）✅ 子代理1完成
- [x] 2.3 审查 CacheBookService.kt:46（缓存下载，updateCacheThreadCount，Service销毁关闭）✅ 子代理1完成（识别 P0-3 关闭顺序问题）
- [x] 2.4 审查 MainViewModel.kt:54/92（目录更新，updateCacheThreadCount，可重建upPool）✅ 子代理1完成（识别 P0-1/P0-2 拆分+@Volatile 问题）
- [x] 2.5 审查 SearchModel.kt:59（书源搜索，searchThreadCount，搜索结束关闭）✅ 子代理1完成
- [x] 2.6 审查 RssSearchModel.kt:110（RSS搜索，searchThreadCount，搜索结束关闭）✅ 子代理1完成（设计最优范式）
- [x] 2.7 审查 ChangeCoverViewModel.kt:101（换封面，searchThreadCount，ViewModel销毁关闭）✅ 子代理1完成
- [x] 2.8 审查 ChangeBookSourceViewModel.kt:167（换源，searchThreadCount，ViewModel销毁关闭）✅ 子代理1完成

## 3. Dispatchers 与协程审查
- [x] 3.1 审查 Dispatchers.IO 使用情况（20+处，默认64线程上限）✅ 子代理2完成（50文件54+处）
- [x] 3.2 审查 Coroutine.kt 自定义协程（默认Dispatchers.IO，CancellationException守卫）✅ 子代理2完成（识别 P0-5/P0-6 scope+executeContext 问题）
- [x] 3.3 审查 DispatchersMonitor.kt（单线程监控，仅recordLog=true时生效）✅ 子代理2完成（识别 P1-6/P1-7/P1-8 监控问题）
- [x] 3.4 评估 Dispatchers.IO 与业务FixedThreadPool的资源竞争 ✅ 子代理2完成（量化分析 290+ 线程最坏场景）

## 4. 其他线程池审查
- [x] 4.1 审查 ExecutorService.kt globalExecutor（单线程，lazy未关闭，用途明确化）✅ 子代理3完成（3 个调用点：Bitmap回收/日志写入/启动清理）
- [x] 4.2 审查 HttpHelper.kt:101 OkHttp连接池（50连接5分钟超时，合理性评估）✅ 子代理3完成（量化分析+Cronet隔离确认）

## 5. 问题识别与优化建议
- [x] 5.1 识别线程池泄漏风险（未关闭的线程池）✅ 7项泄漏风险（L-1~L-7）
- [x] 5.2 识别性能瓶颈（过小/过大的线程池）✅ 10项性能瓶颈（B-1~B-10）
- [x] 5.3 评估线程池大小默认值合理性（searchThreadCount=32, updateCacheThreadCount=16）✅ 6项默认值评估
- [x] 5.4 提出优化建议（含优先级：P0必须/P1建议/P2可选）✅ P0 6项 + P1 16项 + P2 13项 = 35项

## 6. 审查报告生成
- [x] 6.1 汇总审查发现，生成审查报告 ✅ audit-report.md 已生成
- [x] 6.2 标注优化建议的优先级和实施难度 ✅ 含实施成本评估+回归风险评估
- [x] 6.3 提交用户审查（检查点2）✅ 等待用户审核

## 7. 优化实施（待用户确认范围后执行）
- [ ] 7.1 实施P0级优化（必须）— 6项
- [ ] 7.2 实施P1级优化（建议）— 16项
- [ ] 7.3 实施P2级优化（可选）— 13项

## 8. 验证与收尾（如有代码变更）
- [ ] 8.1 编译验证（如有代码变更）
- [ ] 8.2 真机测试（如有代码变更）
- [ ] 8.3 更新文档（updateLog.md等）
- [ ] 8.4 更新 tasks.md 全部标记完成

---

## AOAdapt 日志（实施过程记录）

### [2026-07-26 压缩恢复后] 审查执行阶段
- 执行项：3 个子代理并行审查（FixedThreadPool 8 点 + Dispatchers 4 项 + globalExecutor/OkHttp 2 项）
- 发现：13 项配置点共识别 P0 6 项 + P1 16 项 + P2 13 项优化建议
- 决策：整合为 audit-report.md，按 P0/P1/P2 分级，含实施优先级与回归风险评估
- 验证：审查报告覆盖 13 项配置点，每点覆盖 7 个维度，无违禁词，仅引用技术字段
