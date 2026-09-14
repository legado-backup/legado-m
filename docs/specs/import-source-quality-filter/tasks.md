# tasks：导入源质量过滤与公共源质量校验组件

## 1. 准备工作

- [ ] 1.1 核实依赖锚点：ImportRssSourceDialog 实际文件名；两个 ImportViewModel 同 URL 去重现状；CheckRssSourceService 首入口采集与首屏渲染探测签名；video 型书源 WebBook 零规则分支（WebBook.kt L307-313）；体检结果页复用 AppManagementScaffold 可行性；AppManagementAction/MenuAction 透传规范（iconRes 铁律）；**AnalyzeUrl 探测请求 HEAD 支持与响应体截断能力（S4）**；**DohDns 内网地址过滤策略复用形态（S1，CheckSourceService.kt L166-177 裸 Socket 无拦截实证）**；Debug.startChecking/getRespondTime 计时链（A2-①）
  - 验证标准：锚点均有文件+行号结论，design.md File Changes 如有出入回改
- [ ] 1.2 备份将修改的存量文件到 bak 目录
  - 验证标准：bak 文件与源文件一致

## 2. 核心实现

### 2A 公共组件层

- [x] 2.1 新增 `model/SourceQualityChecker.kt`：从 CheckSourceService/CheckRssSourceService 平移探测逻辑（checkBook/isDomainReachable/checkDomainReachable/异常分类/订阅源四维/首屏渲染分支），封装 SourceQualityReport（字段级定义见 design.md A4 节：dimensions 三态 Map/suspect 五类/failureKind/deterministicFail/score/coverage）+ 会话级基础设施（Semaphore/host 域名缓存/URL 去重/同 host 试采限额/withTimeoutOrNull/ProbeOptions 参数类）+ **内网地址探测跳过（S1：字面回环/私有/169.254 → suspect 标注不请求）** + **探测请求 HEAD 优先与 2MB 截断（S4）** + **断网预检短路（攻击6+v4 二轮修正：系统状态+实测探针双信源，确认断网→全部未测存疑放行+toast 告知；网络正常不得误短路）** + **结论缓存复用（攻击7+v4 二轮修正：键含 url+档位+深度+schemaVersion，TTL 24h，命中校验档位匹配）** + ensureActive 防取消误判（A2-③）
  - Action: 编译通过；RSS 段冗余代码/同 host 限额接线/deterministicFail 判定等 6 处编译期修正
  - Observation: AOAdapt①-S4 原"HEAD 优先+2MB 截断"需动公共网络路径（AnalyzeUrl/SourceNetworkClient）回归风险大，改以 options.timeout 硬控替代（超时取消约束内存），HEAD/截断留扩展路径；AOAdapt②-RSS webview 型"首屏渲染探测"实现需引入 BackstageWebView 复杂渲染链，改以全维度 NOT_CHECKED+suspect(WEB_VIEW) 放行替代（design 模板表 FIRST_SCREEN 维度保留，实现标注）
  - Adapt: S4/webview 两处实施简化已在 design.md 登记路径，不改变判定规则表语义
  - 验证标准：编译通过 ✓；零写库副作用 ✓（Grep 无 dao 调用）；无 import service 包 ✓；网络调用点可注入替换 ✓
- [x] 2.2 新增 `model/SourceQualityScorer.kt`：形态模板表（**数据化 List<DimTemplate>**，A7；书源 4 模板/订阅源 3 模板）+ 归一化计分 + 覆盖度 + suspect 五类判定（登录/jsLib/源变量/useWebView/内网地址）+ 用户层四态映射（可用/失效/存疑/未测）
  - 验证标准：编译通过 ✓；模板表与 design.md 一致 ✓；file/video/纯发现/webview 型不被维度歧视（单测断言）✓
- [x] 2.4 新增 `model/ImportCheck.kt` 配置单例（enabled 默认 false/depth 三档 L1/L2/L3 默认 L2/strictness 宽松默认/高级折叠项 concurrency 8/timeout 10s/retry true；putConfig 持久化；映射 ProbeOptions 预设，探测字段不独立定义，AD-09）
  - 验证标准：编译通过 ✓；键名前缀 importCheck* 无冲突 ✓
- [x] 2.5 单元测试：判定规则表三档×七类证据（含 suspect 强制放行、换词重试、存疑放行）+ 评分 v2（形态模板不歧视/归一化/覆盖度/三态/四态映射）+ L1 静态规则（含 RSS webview 不误杀）+ 内网地址 suspect 标注（S1）
  - 验证标准：`./gradlew testAppDebugUnitTest --tests SourceQualityFilterTest` **25 用例 0 失败 0 错误** ✓（报告 app/build/test-results/testAppDebugUnitTest）

### 2B 导入场景接线

- [x] 2.6 新增 `ui/config/ImportCheckConfigDialog.kt` 设置弹框（P1 收敛：总开关+校验深度三选一+严格度三选一附白话说明（P6）+高级折叠区；UI 走 ui-standards 组件族基线）
  - 验证标准：编译通过 ✓；待真机验证配置读写（L2）
- [x] 2.7 书源/订阅源管理菜单接入"导入校验设置"入口（BookSourceActivity/RssSourceActivity pageMenuActions）
  - 验证标准：编译通过 ✓；待真机验证菜单可见可打开（L2）
- [x] 2.8 ImportBookSourceViewModel + ImportBookSourceDialog 接线：L1 即时标记 FILTERED；importSelect 接 L2/L3（进度→档位判定→通过集落库→过滤集复核）；dialog 增 FILTERED 态（**白话原因+得分**，注释类字段截断 50 字符，S5）、进度、复核弹框（全选恢复二次确认 P3 / 恢复两式：正常导入或导入后自动禁用 P8 / 复制被过滤源列表兜底）、**校验中返回键确认框（直接取消/停止校验并导入已通过源，P2）**、**长集合（>200 勾选）分批落库每 50 条一批+进度标注已导入数（v4 二轮 ProcessDeath 补强）**、导入弹框内"导入校验"快捷开关（P1）
  - Action: 校验并发由 SourceQualitySession.semaphore 限流；cancelCheck(landPassed) 支持半程落库；复核弹层 FilteredReviewSheet 抽独立文件两链路共用
  - Observation: AOAdapt④-"导入弹框内快捷开关"未实现：ImportSourceSheet 为 8 个导入弹框共享组件，加开关需改公共契约影响面大；设置弹框三项式已足够轻量，快捷开关留真机反馈后迭代
  - 验证标准：编译通过 ✓；关闭开关流程零差异（importSelect 原路径保留）✓；待真机 L2
- [x] 2.9 ImportRssSourceViewModel + ImportRssSourceDialog 同构接线（FilteredReviewSheet 抽独立文件共用）
  - 验证标准：同 2.8（编译通过 ✓；待真机 L2）
- [x] 2.10 落库与 toast 汇总（导入 N 过滤 M）；18+ 过滤先于质量校验（SourceHelp.insertBookSource 内 18+ 分组先执行）
  - 验证标准：编译通过 ✓；待真机 L2

### 2C 体检场景

- [x] 2.11 书源/订阅源管理菜单"质量体检"入口（与"校验"命名差异化，P7）+ 范围选择弹框（选中源/当前分组/全部）+ 首次打开一句话分工说明（AOAdapt③：RSS 侧范围简化为 全部/选中源，分组范围留迭代）
  - 验证标准：编译通过 ✓；待真机 L2
- [x] 2.12 新增体检会话单例 QualityCheckSession（**按源类型书源/订阅源分会话** A5；应用级 Job/结果 Map/进度 StateFlow；覆盖前先 cancel 旧 Job 再清结果；重进页面恢复）+ 体检结果页（Compose）：**四态白话标签筛选（可用/失效/存疑/未测）+ 低分口径筛选（score<60 无 Fail）**+ 得分排序 + 覆盖度收进行内 + suspect 标注 + 注释截断 50 字符（S5）+ 多选操作栏 + **禁用主按钮/删除需自动 JSON 备份到用户目录并在确认框明示路径（P4/S6）** + 删除后列表即时刷新；Manifest 注册
  - 验证标准：编译通过 ✓；待真机 L2（零写库 Grep 证据：会话类仅 deleteSelected/disableSelected 两个显式写库点；切页/重进校验不中断；双类型同时体检互不覆盖；删除备份文件可导入回滚）
- [x] 2.13 体检结果页顶栏/图标/取色走 ui-standards 单源体系（TopBarConfig/actionIconSize，防图标规范回归）
  - 验证标准：编译通过 ✓；待真机目检（L2）
- [x] 2.14 `CheckSourceService`/`CheckRssSourceService` 等价重构：探测段改调公共组件（**逐项核对 design.md AD-08 防走样清单 6 点**：respondTime 计时时序/failureKind 映射分组/ensureActive/超时按原值参数化/双层限流注入/写库副作用归属注释），分组写库/通知/去重/dedupSources 保留原地
  - Action: 最小等价重构落地——两服务的 isDomainReachable/checkDomainReachable 函数体委托 SourceQualityChecker 同名方法（Socket 1.6s/AnalyzeUrl 真实请求），服务传原超时值（30s/CheckRssSource.timeout）保持行为（防走样④）；checkBook 保留服务侧（依赖 CheckSource.checkInfo 等开关配置）；分组写库/通知/respondTime 计时（Debug.startChecking L184→getRespondTime L163）不动（防走样①②③⑤⑥）
  - Observation: checkBook 带 CheckSource 开关逻辑与组件 probeBookDetail 职责不同，强迁会破坏服务行为，保留是有意分层
  - 验证标准：编译通过 ✓；待真机回归（3.5 对照基线）

## 3. 验证测试（真机，测试包 io.legado.miss.app.debug）

- [x] 3.1 导入过滤功能验证（L2 自动化：ai_tests/scripts/l2_verify_import_check.py + l2_assert_import_check_db.py）
  - Action: 本地 HTTP 混合集合（QC_OK_1 正常/QC_BROKEN 残缺/QC_SUSPECT_VAR 变量依赖/QC_DEAD 不可达）SAF 文件导入
  - Observation: **已实证**：①菜单/设置弹框可达+开关开启持久化（重开弹框深度选项可见）②导入列表 L1 静态过滤生效——"已过滤"徽标出现、QC_BROKEN 标记、FILTERED 数量=1（仅结构残缺）③全程 FATAL=0；**AOAdapt⑤-发现并修复真实 UI bug**：设置弹框内容过高把确认按钮推出屏外（900px 屏），heightIn 300dp 修复；**AOAdapt⑥-未闭环**：导入→L2 联网校验→复核窗口→落库链路的 UI 自动化受 Compose dump idle 限制（导入按钮定位失败），DB 断言脚本已备（l2_assert_import_check_db.py）待人工点一次导入即出结果
  - 验证标准：核心过滤 UI 实证 ✓；落库链路待人工验收（验收清单见下）
- [ ] 3.2 误伤专项（suspect 源放行/标准档过滤）：代码层单测已覆盖（25 用例），真机场景待人工验收
- [ ] 3.3 千条集合性能：待人工验收（大集合建议快速模式提示已实现）
- [ ] 3.4 存量体检验证：体检入口/范围弹框/结果页可达已实证（T3-pre 过），结果页筛选/删除备份待人工验收
- [ ] 3.5 现有校验功能回归：等价重构仅域名探测委托（行为保持），待人工回归
- [ ] 3.6 订阅源链路同构验证：代码同构+编译过，待人工验收
- [ ] 3.7 回归验证：校验关闭行为不变（importSelect 原路径零改动）✓代码层；全量 E2E 待跑
- [ ] 3.8 **人工验收清单**（模拟器已装 091317 包）：①设置弹框开启开关→网络导入 yckceo 集合→观察"已过滤"标记与复核窗口→"仍要导入"恢复→toast 汇总 ②书源管理菜单"源质量体检"→全部源→结果页四态筛选/禁用/删除备份 ③现有"校验"按钮回归 ④订阅源管理同构验证
- [x] 3.9 **goal 6aa66d48：真机反馈修复+社区合集 E2E**（2026-09-13）
  - Action: 用户真机反馈 5 项（样式丑/万条慢/无暂停/删除反馈不清/备份位置）全部修复：结果页重写接 AppManagementScaffold 管理族、QualityCheckSession 暂停/断点续跑、删除反馈闭环（URL 键+toast 备份路径）、备份目录改 Backup.backupPath/quality_backup；并发/超时/重试从高级折叠区**平铺为显式配置项**（用户裁决：配置项不该折叠隐藏）
  - Observation: yckceo 社区合集（id/293）实测 913 条：896 有搜索/593 有发现/15 条搜索发现均无（L1 过滤目标）/165 条登录依赖（suspect 放行）——真实数据画像与设计预期吻合
  - Adapt: 社区合集 E2E 驱动脚本 qc_community_e2e.py（进度轮询/复核窗口截图/DB 断言）
  - 验证标准：E2E 全流程 PASS（见运行输出）

## 4. 文档收尾

- [ ] 4.1 基于 git diff 更新 app/src/main/assets/updateLog.md（编译前完成）
- [ ] 4.2 文档同步：docs/INDEX.md 状态流转；docs/project-flow/architecture/rule-engine.md 如涉及校验链路描述则更新；无接口/实体文档需同步则注明
- [ ] 4.3 Grep 确认无临时调试日志残留（android.util.Log.d/e；诊断日志铁律除外），附 Grep 证据
- [ ] 4.4 issues-found.md 记录真机问题与耗时基线
- [ ] 4.5 经验沉淀 ai_memory_main.md（公共组件剥离模式/形态模板评分经验）
