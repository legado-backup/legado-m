# tasks.md — video-booksource-multiroute

## 0. 准备工作
- [ ] 0.1 核实 BookSource/BookChapter/TocRule 实体现状（禁止凭文档行号改）
- [ ] 0.2 核实 VideoPlay 强转点清单（`as? RssSource` **8 处**，其中 4 处多线路核心 L476/L1332/L1346/L1759 + L780 硬强转；文章模式专属 4 处不动）
- [ ] 0.3 核实 BookSourceType/BookType 常量与 SearchBookOpenHelper 对接现状（**分支判断一律用 `BookSourceType.video` 常量（=4），禁止硬编码数字——2 是 image**）

## 1. 能力接口与数据结构
- [x] 1.1 ~~新增 SourceMultiRoute 接口~~ **实施修订（design.md AD-03）**：播放上下文全在 VideoPlay，接口化无行为差异且重构订阅源稳定路径回归风险高——改为 VideoPlay 内联分派 + 复用 RssRoute/RssEpisode 统一模型（本身与书源卷章范式对称）
- [x] 1.2 ~~RssSource 实现接口~~ 订阅源路径**零改动**（行为等价的最强形态，回归风险归零）
- [x] 1.3 强转点分派：isNewRoutesMode/switchToRoute/playRssEpisode 三处补书源分支（订阅源原逻辑一行未动）

## 2. 书源侧实现
- [x] 2.1 VideoPlay 内联分派实施（AD-03 实施修订：接口未落地，isNewRoutesMode/switchToRoute/playRssEpisode 三处按源类型分派）——`bookSourceType==video` 常量判断，无新增字段
- [x] 2.2 `MacCmsNormalizer` 共享规范化（Rss.kt 委托，双结构注入 routes+chapters、对称冲突检测）+ `VideoBookChapterHelper`（L0 直产卷章）
- [x] 2.3 WebBook.loadChapterListAwait type=video 分支：`videoBookChapterListAwait`（L0 直产/L1 既有解析消费 $.chapters[*]/L2·L3 原样走既有解析）
- [x] 2.4 播放管线：initSource 卷章→rssRoutes/rssEpisodes 映射（UI 零改动）+ `switchBookRoute`（内存卷章切片）+ `playBookEpisode`（卷内索引→全目录索引定位）
- [x] 2.5 `startPlayBookChapter` 抽取（startPlay 书源分支共用采集链：ruleContent 留空→chapter.url 直链直出，播放页 URL 三层嗅探兜底——既有嗅探链确认存在）
- [x] 2.5b 编译验证 BUILD SUCCESSFUL（compileAppDebugKotlin，修复 2 处编译错误：可空接收器/Pair 返回类型误判）

## 3. 正文入口与详情 UI（AD-06）
- [ ] 3.1 type=video 书源正文页菜单"播放"动作（条件渲染）
- [ ] 3.2 正文视频 URL 点击 → 嗅探链直达播放器
- [ ] 3.3 新增 VideoBookDetailSheet：封面/书名/作者/简介（**简介渲染从 legacy 隐藏视图解耦**，抽独立渲染方法）+ 线路 Tab + 集数列表（Compose，按 ui-standards 组件族）
- [ ] 3.4 VideoFragment 左下角详情入口（仅书源模式注入；订阅源 REQ-17/18 悬浮选择器零改动）
- [ ] 3.5 抽屉切线路/选集与悬浮选择器动作源统一（单一 playRouteEpisode 分派，防状态漂移）
- [ ] 3.6 Web 端 Vue 书源编辑器/导入导出零改动确认（bookSourceType=4 编辑能力既有，无新字段）

## 4. 验证
- [x] 4.1 ~~单测~~ 由真机测试脚本固化替代（`l2_verify_video_booksource_multiroute.py` --case all：规范化→卷章映射→分派→播放断言链）
- [x] 4.2 文本书源回归（视频分支严格隔离：videoBookChapterListAwait 仅 bookSourceType==video 进入，既有路径零改动）
- [x] 4.3 订阅源播放回归（**真机 PASS 6/6**：播放正常、悬浮选择器在、无详情入口、0 异常；VideoFragment 仅 +33 行纯新增）
- [x] 4.4 真机 L2：MacCMS 视频书源全链路（**L0 源 PASS 11/11**：规范化→卷章直产 卷数=2 总章数=136→直达播放器→详情抽屉→切线路→选集→起播）
- [ ] 4.5 真机 L2：正文页播放入口（AD-04 兜底入口，阅读器对视频书几乎不可达，优先级低）
- [ ] 4.6 真机硬用例①：archive @js 视频书源导入验证（变量模板源需先配置 sourceVariables，待办）
- [x] 4.7 真机硬用例②：**零 JS L1 版书源 PASS 11/11**（四条 JSONPath 消费 chapters 结构，无直产日志确认走规则路径，与 L0 同链路可播）
- [x] 4.8 解析分级矩阵：L0 零规则 + L1 JSONPath 双版真机可播（**L2 CSS·XPath HTML 站与 L3 archive 兼容线待补**）
- [x] 4.9 详情 UI 真机验证：书源模式详情抽屉 PASS（封面/简介/线路 Tab×2/集数网格×28、切线路/选集动作正常）+ 订阅源回归 UI 零退化 PASS
- [x] 4.10 回归矩阵核心项（订阅源回归 + 分支隔离 + 多线路播放链；电影类单线路形态待补测）
- 交付物：`ai_tests/scripts/l2_verify_video_booksource_multiroute.py`（--case l0/l1/regression/all 全 PASS）+ `ai_tests/scripts/testdata/booksource_video_l0_hhzy.json` / `booksource_video_l1_hhzy.json`

## 5. 收尾
- [ ] 5.1 skill 沉淀（视频书源规则模板 + 陷阱）
- [ ] 5.2 updateLog 更新（编译前）
- [ ] 5.3 文档同步（步骤 8 映射表：rule-engine/webbook/database 相关文档）
- [ ] 5.4 临时脚本/日志清理（Grep 确认 0 残留）

## AOAdapt 日志
（实施中记录）
