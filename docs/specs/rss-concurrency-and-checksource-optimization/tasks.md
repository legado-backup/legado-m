# 任务清单：订阅源解析并发配置化 + 书源/订阅源校验去重优化

## 第一批：需求一 - 解析并发 + 图片加载并发配置化

### 1. 配置基础设施
- [x] 1.1 PreferKey.kt 新增 `rssParseConcurrency` 和 `imageLoadConcurrency` 常量
- [x] 1.2 AppConfig.kt 新增 `rssParseConcurrency`（默认3）和 `imageLoadConcurrency`（默认5）属性
- [x] 1.3 strings.xml 新增字符串资源（标题+摘要）

### 2. 解析并发配置化
- [x] 2.1 RssSource.kt 新增 `parseConcurrency: Int = 0` 字段（同时新增 `weight: Int = 0` 字段，需求三合并迁移）
      同时新增 hasGroup() + removeInvalidGroups() 方法（BLK-6修复，参考BookSource实现）
- [x] 2.2 数据库迁移 94→95（ADJ-2 三处必改，合并需求一parseConcurrency + 需求三weight）
- [x] 2.3 RssParserByRule.kt L86 `Semaphore(6)` 改为读取配置parseConcurrency（源级优先>全局配置默认3）
- [x] 2.4 RssSourceEditActivity 编辑界面新增parseConcurrency配置项（ADJ-1 必须）
      ✅ equal() 方法已更新（BLK-7修复完成）：
      - RssSource.equal() 新增 `&& parseConcurrency == source.parseConcurrency && weight == source.weight`
      - BookSource.equal() 新增 `&& weight == source.weight`
      ✅ RssSourceEditActivity 编辑界面已补充parseConcurrency配置项

### 3. 图片加载并发配置化
- [x] 3.1 LegadoGlideModule.kt applyOptions 新增 `builder.setSourceExecutor(GlideExecutor.newSourceExecutor(AppConfig.imageLoadConcurrency))`
- [x] 3.2 【阻断验证 BLK-3】编译测试 GlideExecutor.newSourceExecutor(threadCount: Int) 在 Glide 5.0.5 可用性 ✅ 已解决
  - 验证结果：GlideExecutor在Glide 5.0.5中存在，但包路径从`com.bumptech.glide.GlideExecutor`变更为`com.bumptech.glide.load.engine.executor.GlideExecutor`
  - 验证方式：编译通过BUILD SUCCESSFUL，GlideExecutor.newSourceExecutor(threadCount, name, strategy) API签名不变
  - 实施完成：已用runCatching包裹失败降级到Glide默认线程数

### 4. 配置UI
- [x] 4.1 pref_config_other.xml 在threadCount后新增两个Preference项（rssParseConcurrency/imageLoadConcurrency）
- [x] 4.2 OtherConfigFragment.kt onPreferenceTreeClick 新增两个NumberPickerDialog处理
- [x] 4.3 OtherConfigFragment.kt onSharedPreferenceChanged 新增摘要更新
- [x] 4.4 OtherConfigFragment.kt onCreatePreferences 新增摘要初始化
- [x] 4.5 图片并发修改后提示用户需重启App生效

### 5. 验证
- [x] 5.1 编译验证（BUILD SUCCESSFUL）
- [ ] 5.2 L1验证：设置解析并发=3，确认RssParserByRule使用Semaphore(3)（运行时验证，待用户实测）
- [ ] 5.3 L1验证：设置图片并发=5，重启后确认Glide使用5线程（运行时验证，待用户实测）

## 第二批：需求二 - 书源域名校验优化

### 6. 书源域名校验优化
- [x] 6.1 CheckSource.kt 新增 `domainCheckMode` 配置（0=Socket快速, 1=AnalyzeUrl真实请求, 默认1）+ putConfig 保存
- [x] 6.2 CheckSourceService.kt doCheckSource 域名校验分支：if domainCheckMode==1 用AnalyzeUrl（新增 checkDomainReachable 方法），else保留Socket（isDomainReachable）
- [x] 6.3 dialog_check_source_config.xml 新增 RadioGroup（domain_check_mode_group + rb_socket + rb_analyze_url，visibility跟随check_domain）
- [x] 6.4 CheckSourceConfig.kt 新增 RadioGroup 交互逻辑（初始化读取domainCheckMode + onClick切换可见性 + tvOk保存选中值）
- [x] 6.5 strings.xml 新增 domain_check_socket / domain_check_analyze_url 字符串
- [x] 6.6 验证AnalyzeUrl对复杂源URL的处理（jslib/注释/#规避/空格）（代码层面已实现，运行时验证待用户实测）

### 7. 验证
- [x] 7.1 编译验证（BUILD SUCCESSFUL）
- [ ] 7.2 L2验证：书源校验域名可达性走AnalyzeUrl真实请求（运行时验证，待用户实测）
- [ ] 7.3 L2验证：复杂源URL（含jslib）域名校验正确（运行时验证，待用户实测）

## 第三批：需求二 - 订阅源校验+去重

### 8. 订阅源校验配置
- [x] 8.1 新增 CheckRssSource.kt（object，参考CheckSource）含5维度配置+去重配置
- [x] 8.2 新增 CheckRssSourceConfig.kt（DialogFragment，参考CheckSourceConfig）UI配置
- [x] 8.3 strings.xml 新增订阅源校验相关字符串

### 9. 订阅源校验Service
- [x] 9.0 RssSource.kt 新增方法（BLK-1 + BLK-2 + BLK-6 + BLK-8 整改完成）：
  - (a) `hasGroup(group: String): Boolean`：判断是否包含指定分组（参考 BookSource.kt L188-193，BLK-6修复）
  - (b) `removeInvalidGroups()`：移除校验产生的失效分组（含"失效"/"校验超时"/"重复源"），参考 BookSource.kt L195-197 + L222-226
  - (c) `getSortList()`：解析sortUrl返回分类列表 - **改为使用已有扩展函数 `RssSource.sortUrls()`**（RssSourceExtensions.kt L17，suspend函数，内部用runScriptWithContext+evalJS解析分类）。BLK-8修复：移除冗余的getSortList方法，直接使用现有扩展函数
- [x] 9.1 新增 CheckRssSourceService.kt（参考CheckSourceService）
- [x] 9.2 实现 check(ids) → onEachParallel → checkRssSource → doCheckRssSource
- [x] 9.3 doCheckRssSource 实现5维度校验（域名/列表/搜索/分类/正文）
- [x] 9.4 校验结果记录成功维度数
- [x] 9.5 校验结果回写（addGroup/removeGroup/respondTime）

### 10. 去重逻辑（复用域名校验结果）
- [x] 10.1 定义 CheckResult 数据类（source + successCount + realDomain）
- [x] 10.2 doCheckRssSource 域名校验时记录 realDomain（从AnalyzeUrl.url提取host）
- [x] 10.3 域名校验关闭时，如启用去重则单独构造AnalyzeUrl提取域名（不发起请求）
- [x] 10.4 实现 dedupSources(results: List<CheckResult>) 按realDomain+type多维度去重
- [x] 10.5 去重后addGroup("重复源")标记

### 11. 订阅源校验入口（UI）
- [x] 11.1 EventBus.kt 新增 CHECK_RSS_SOURCE / CHECK_RSS_SOURCE_DONE 常量
- [x] 11.2 NotificationId.kt 新增 CheckRssSourceService = 110
- [x] 11.3 rss_source_sel.xml 新增 menu_check_rss_source 菜单项
- [x] 11.4 RssSourceActivity.kt 新增 checkRssSource() 方法（菜单处理+搜索关键词对话框+启动Service）

## 第四批：需求三 - 权重算法回填

### 12. SourceWeightCalculator 实现
- [x] 12.1 新增 SourceWeightCalculator.kt（object单例）
  - 书源6维度分值常量（DOMAIN=20, SEARCH=20, DISCOVERY=15, INFO=15, CATEGORY=15, CONTENT=15）
  - 订阅源5维度分值常量（DOMAIN=20, ARTICLES=25, SEARCH=20, SORT=15, CONTENT=20）
- [x] 12.2 实现 calculateBookWeightFromGroups(source: BookSource, domainCheckEnabled: Boolean): Int
  - 基于hasGroup反推各维度状态，域名失效直接0分
  - 校验关闭的维度按满分计入（不扣分）
- [x] 12.3 实现 calculateRssWeightFromGroups(source: RssSource, domainCheckEnabled: Boolean): Int
  - 基于hasGroup反推5维度状态，域名失效直接0分

### 13. 权重回填集成
- [x] 13.1 CheckSourceService.kt doCheckSource 末尾（getInvalidGroupNames前）回填 weight
  - 调用 SourceWeightCalculator.calculateBookWeightFromGroups(source, CheckSource.checkDomain)
  - 域名校验失败时已有 source.weight = 0 并 throw（不进入回填）
- [x] 13.2 CheckRssSourceService.kt doCheckRssSource return前回填 weight
  - 调用 SourceWeightCalculator.calculateRssWeightFromGroups(source, CheckRssSource.checkDomain)
  - 域名校验失败时已有 source.weight = 0 并 throw（不进入回填）

### 14. 编译验证
- [x] 14.1 编译验证（BUILD SUCCESSFUL in 1m 25s）

## 第五批：文档同步

### 15. 文档同步
- [x] 15.1 updateLog.md 新增 2026/07/15 更新日志（基于真实代码变更提炼）
- [x] 15.2 tasks.md 更新所有任务状态为完成
- [x] 15.3 project_memory.md 追加本次任务的决策记录
- [ ] 15.4 INDEX.md 检查是否需要更新（可选）

## 总结

### 已完成
- 需求一：订阅源解析并发配置化 + 图片加载并发配置化（3+5默认值，可在设置中调整）
- 需求二：书源域名校验优化（Socket/AnalyzeUrl双模式） + 订阅源校验完整实现（5维度+去重）
- 需求三：权重算法回填（书源6维度+订阅源5维度，满分100，域名不可达0分）
- 数据库迁移 94→95 完成
- 编译验证 BUILD SUCCESSFUL

### 待用户实测
- L1/L2 运行时验证（设置生效确认）
- E2E 端到端测试（校验流程实际运行）
