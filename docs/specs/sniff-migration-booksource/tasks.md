# Tasks: 嗅探与滑动切换能力迁移至书源

## 1. 准备工作

- [ ] 1.1 阅读 `help/image/ImageUrlExtractor.kt` 与 `help/image/ImageSnifferWebView.kt` 现有实现（嗅探入口 WebViewPool、IMAGE_SOURCE_REGEX、timeout 8000L、IMAGE_SNIFF_JS 5 路 hook 注入方式与入参耦合点）
- [ ] 1.2 阅读 `model/ReadManga.kt` 静态解析（getManageChapter L599-632，BookHelp.flowImages 取 img 标签，返回 0 图的场景）与章节加载（moveToNextChapter/moveToPrevChapter L274-321 当前行为）
- [ ] 1.3 阅读 `help/video/VideoUrlExtractor.kt` R5 嗅探链（extractPrecise→extractWithWebView→extractByRegex 三级递进，R5_TIMEOUT=6000L/R5_DELAY_TIME=1000L，见 L47-48）及其与 ImageSnifferWebView 的关系
- [ ] 1.4 阅读 `model/VideoPlay.kt` 书源分支 L607-669（当前 (source as BookSource)→WebBook.getContent→URL 直连播放，无嗅探）与 RSS 分支对比（RSS 视频直链、书源返回播放页的场景差异）
- [ ] 1.5 阅读 `ui/video/VideoPlayerActivity.kt` 滑动逻辑（L424 isSinglePage=book!=null||singleUrl、L432 isUserInputEnabled=!isSinglePage）与 VideoPagerAdapter 切换机制
- [ ] 1.6 阅读入口分发 3 处：`utils/ContextExtensions.kt:66-81`、`utils/FragmentExtensions.kt:94-109`、`ui/book/BookInfoActivity.kt:1093-1117`（isVideo→VideoPlayerActivity；isImage→ReadMangaActivity）确认 bookSourceType 分发条件

## 2. 核心实现：图片嗅探→图片书源

- [ ] 2.1 ImageUrlExtractor 入参解耦/重载（支持传入书源场景所需上下文，静态解析 + 嗅探两条路径复用，保持 RSS 图片调用不受影响）
- [ ] 2.2 `model/ReadManga.kt` getManageChapter 静态解析（flowImages 取 img 标签）结果为 0 张图时接入 ImageSnifferWebView 嗅探兜底（sniffImageUrls()，WebViewPool，IMAGE_SOURCE_REGEX，timeout 8000L）
- [ ] 2.3 实现嗅探失败兜底处理（无图/超时返回空列表并走原有错误提示，不阻塞正常章节加载）
- [ ] 2.4 实现嗅探结果去重与顺序稳定（URL 去重、按出现顺序保留，避免重复加载与顺序抖动）

## 3. 核心实现：视频嗅探→视频书源

- [ ] 3.1 VideoUrlExtractor 入参解耦/重载（支持传入书源场景参数，R5 嗅探链复用，保持 RSS 视频解析不受影响）
- [ ] 3.2 `model/VideoPlay.kt` 书源分支（L607-669）接入 R5 嗅探链（extractPrecise→extractWithWebView→extractByRegex，R5_TIMEOUT=6000L），解决 ruleContent 返回播放页而非直链时的播放
- [ ] 3.3 实现嗅探失败降级：R5 链无结果时回退当前 WebBook.getContent + URL 直接播放
- [ ] 3.4 保持视频 MPD（自适应流）特殊处理不变，嗅探链与 MPD 分支共存互不影响

## 4. 核心实现：上下滑动切换上/下集

- [ ] 4.1 视频书源放开滑动：`ui/video/VideoPlayerActivity.kt` 修改 isUserInputEnabled（L432 放开书源模式的上下滑动手势，L424 isSinglePage=book!=null||singleUrl 判定适配）与多页驱动
- [ ] 4.2 用 episodes(BookChapter) 列表驱动多页，VideoPagerAdapter 按集索引切页（onPageSelected 回调）
- [ ] 4.3 实现 onPageSelected 回调 `model/VideoPlay.kt` upDurIndex（更新当前集）
- [ ] 4.4 图片书源章节滑动：`model/ReadManga.kt` moveToNextChapter/moveToPrevChapter（L274-321）增加章节滚动加载（参考 `ui/image/ImageCanvasViewModel` 滚动加载模式）
- [ ] 4.5 实现上下集预加载（滑动时预取相邻章节内容，减少断载等待）
- [ ] 4.6 边界处理（首章/末章的不可再滑动限制与提示，越界保护）

## 5. 验证

> 前置：先读 `ai_tests/docs/fixed_test_workflow.md`；用 `ai_tests\venv\Scripts\python.exe`（禁止公共 Python）；真机测试包固定为 `io.legado.miss.app.debug`，同一模拟器不混用多个包。

- [ ] 5.1 编译通过（./gradlew assembleAppDebug）
- [ ] 5.2 真机 L2 验证：图片书源（bookSourceType=2）章节静态解析返回 0 图时触发 ImageSnifferWebView 嗅探兜底，图片正常展示
- [ ] 5.3 真机 L2 验证：视频书源（bookSourceType=4）ruleContent 返回播放页时 R5 嗅探链（extractPrecise→extractWithWebView→extractByRegex）成功提取直链并播放
- [ ] 5.4 真机 L2 验证：视频书源上下滑动切换上/下集（episodes 驱动，onPageSelected 触发 upDurIndex，切换自动加载）
- [ ] 5.5 真机 L2 验证：图片书源滑动切换章节（滚动加载/预加载，末章边界无崩溃）
- [ ] 5.6 真机 L2 验证：嗅探失败降级场景（视频嗅探失败走直连播放、漫画 0 图错误提示，均不崩溃）
- [ ] 5.7 真机 L2 回归：RSS 图片/视频（原有直连链路）不受影响，行为与迁移前一致

## 6. 文档同步

- [ ] 6.1 更新 `app/src/main/assets/updateLog.md`（编译前基于 git diff 分析真实代码变更，追加在 `## cronet版本:` 之后、已有条目之前）
- [ ] 6.2 若改动模块结构则更新 `docs/project-flow/task-navigation.md`（图片/视频模块新增嗅探与滑动锚点）
- [ ] 6.3 更新 `docs/INDEX.md`（任务状态与已完成功能同步）
- [ ] 6.4 在 `issues-found.md` 记录本次真机测试发现的问题
- [ ] 6.5 更新 `.trae/memory/ai_memory_main.md`（记忆权威源，任务结论沉淀）

## AOAdapt 日志

> 在实施过程中按 Action/Observation/Adapt 三行格式记录遇到的问题及调整。

（待实施时填写）