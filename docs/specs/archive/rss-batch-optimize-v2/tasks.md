# tasks.md - RSS 订阅源批量优化 v2 任务清单

## 1. 准备工作

- [x] 1.1 需求分析（已完成）
- [x] 1.2 结构分析（已完成 - 222源，主要缺失字段统计）
- [x] 1.3 生成OpenSpec四文档（已完成）
- [ ] 1.4 用户审查设计方案（🛑 强制检查点1 - 用户反馈"需调整"，已根据反馈更新spec/design/tasks，待再次确认）

## 2. 阶段2 预处理

- [ ] 2.1 创建 preprocess_sources_v2.py
  - 识别占位符源（sourceUrl长度<20，68个）
  - 从sourceComment提取候选URL
  - 识别模板源（含{{}}，7个），提取base_url
  - 输出预处理报告（不输出业务字段，仅统计）
- [ ] 2.2 运行预处理，生成预处理后的JSON

## 3. 阶段3 类型识别与分类（新增）

- [ ] 3.1 创建 classify_source_type_v2.py
  - Playwright访问每个源首页
  - DOM特征分析（img/video/nav/article 4维度权重打分）
  - 辅助识别：sourceUrl模板关键词（/video/、/image/、/pic/）
  - 输出：(type, is_navigation, confidence)
  - 脱敏输出：只输出 idx+type+confidence，不输出业务字段
- [ ] 3.2 运行类型识别，生成 type_classification_report.json
- [ ] 3.3 子代理产出验证：Read确认报告存在 + 统计各类型数量

## 4. 阶段4 导航站拆分（新增）

- [ ] 4.1 创建 split_navigation_source_v2.py
  - 对 is_navigation=true 的源提取所有子站链接
  - 去重+过滤无效链接
  - Playwright 访问每个子站首页，复用阶段3类型识别
  - 对图片站/视频站拆分为独立子源
  - 边界：单导航站最多拆分20个子源，置信度<0.4跳过
  - 父源标记 nav_parent=true + enabled=false
- [ ] 4.2 运行导航站拆分，生成 navigation_split_report.json
- [ ] 4.3 子代理产出验证：Read确认拆分报告 + 统计拆分出的子源数量

## 5. 阶段5 Playwright批量字段补全

- [ ] 5.1 创建 batch_optimize_v2.py（基于v1扩展）
  - 输入：预处理后JSON + 类型识别结果 + 拆分子源
  - Playwright逐个访问源首页（headless + stealth脚本）
  - 必填字段：sourceIcon/searchUrl/ruleArticles/ruleTitle/ruleLink/ruleImage
  - 推荐字段：sortUrl/ruleNextPage/rulePubDate/ruleContent
  - 字段补全策略矩阵（11字段，见design.md §11）
  - 失败不中断，记录到报告
  - 输出：优化后JSON + 优化报告
- [ ] 5.2 运行批量优化（预计74-90分钟，222+子源）
- [ ] 5.3 子代理产出验证：Read确认优化后JSON存在 + 11字段覆盖率提升

## 6. 阶段6 字段合法性后置校验

- [ ] 6.1 创建 post_validate_v2.py（复用v1逻辑+扩展必填校验）
  - 修复 ruleNextPage='page' 等无效值
  - 修复 searchUrl='None' 等无效值
  - 修复 Python None 序列化污染
  - 必填字段缺失兜底（sourceIcon=/favicon.ico, searchUrl=Google site:搜索）
  - 输出修复统计
- [ ] 6.2 运行后置校验

## 7. 阶段7 失败源深度重试 + 域名迁移 + 反爬配置

- [ ] 7.1 创建 deep_retry_v2.py（复用v1的14种技术手段）
  - 4种UA + HTTP方法 + Wayback + HTTP/1.1 + HTTP降级 + 跟随重定向 + 长 timeout
  - requests + Session + Playwright + 移动UA + 端口组合 + 60s超时 + Wayback直接访问
  - 按失败原因精准应对
- [ ] 7.2 运行深度重试，标记truly_dead源
- [ ] 7.3 创建 migrate_domain_v2.py（复用v1的5步闭环）
  - 识别"备用域名/最新域名获取地址"提示
  - 5步闭环迁移
- [ ] 7.4 运行域名迁移
- [ ] 7.5 创建 add_login_config_v2.py（复用v1）
  - 反爬源配置 loginUrl=sourceUrl + enabledCookieJar=true
  - 标记user_optional_login
- [ ] 7.6 运行反爬配置

## 8. 阶段8 图片源/视频源ruleContent设计（新增）

- [ ] 8.1 创建 design_rule_content_v2.py
  - 图片源(type=1)：根据DOM特征选择模板A/B/C/D
  - 视频源(type=2)：根据DOM特征选择模板V1/V2/V3或空（依赖嗅探器）
  - 适配PhotoDialog调用链（Rss.getContent + NetworkUtils.getAbsoluteURL）
  - 适配VideoPlayerActivity（内置嗅探器优先）
- [ ] 8.2 运行ruleContent设计
- [ ] 8.3 子代理产出验证：Read确认ruleContent覆盖率 + 模板分布统计

## 9. 阶段9 JSON类型修复 + 导入验证 + skill反哺

- [ ] 9.1 运行 fix_json_boolean_v2.py（复用v1）
  - boolean字段 1/0 → true/false
- [ ] 9.2 导入完整版JSON到模拟器（import_rss_source.py）
  - 含残留源清理（避免sourceUrl变化导致旧源残留）
- [ ] 9.3 运行4场景验证（verify_rss_scenarios_v2.py）
  - 列表加载（含图片显示验证）
  - 搜索
  - 分类
  - 下一页
- [ ] 9.4 生成精简版JSON（移除truly_dead+nav_parent禁用源）
- [ ] 9.5 导入精简版JSON到模拟器，再次验证
- [ ] 9.6 🛑 强制检查点2：用户审核实施结果

## 10. 阶段10 skill反哺

- [ ] 10.1 分析本次发现的新陷阱
- [ ] 10.2 更新 batch-optimization-patterns.md
  - 新增陷阱16：占位符源处理（68个sourceUrl长度<20的场景）
  - 新增陷阱17：模板源处理（含{{}}的7个源）
  - 新增陷阱18：大规模批量优化性能策略（222源vs65源）
  - 新增陷阱19：类型识别DOM特征权重打分算法
  - 新增陷阱20：导航站拆分边界条件（最多20子源+父源禁用）
  - 新增陷阱21：图片源ruleContent 4模板选择策略
  - 新增陷阱22：视频源ruleContent优先嗅探器策略
- [ ] 10.3 子代理产出验证：Read确认陷阱16-22已添加

## 11. 最终验收

- [ ] 11.1 生成最终诊断汇总报告（final_summary_v2.py）
- [ ] 11.2 持久化用户决策到项目记忆
- [ ] 11.3 更新 docs/INDEX.md（移动到已完成）
- [ ] 11.4 更新 README.md 状态为 "✅ 已完成"
- [ ] 11.5 🛑 强制检查点3：用户最终验收

## AOAdapt 日志

（实施过程中记录）
