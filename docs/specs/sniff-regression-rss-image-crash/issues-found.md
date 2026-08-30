# Issues Found: 嗅探回归与图片订阅源崩溃取证修复

## IF-01: destroyScope 会销毁 inUsePool 中的活动 WebView（登记不修，AD-03）

- **来源**：`bbc9d0a89`（08-19 WebView 池分层重构）伴生风险
- **现象**：`WebViewPool.destroyScope(DISCOVERY/RSS)` 销毁 idlePool + **inUsePool** + resettingPool 全部实例；ExploreShowActivity onDestroy、RssFragment onPause 延迟 30s / onDestroyView 都会调用。若销毁时 scope 内仍有进行中的请求（含可能触发嗅探链的场景），请求直接中断
- **症状特征**："订阅/发现页偶发加载失败"
- **处置**：本次不修（改动面与风险独立，需单独真机评估）；嗅探回归修复（isGlobalIdle 守卫）可独立归因验证
- **修复方向**：destroyScope 仅清 idlePool + resettingPool，inUsePool 实例标记 pendingDestroy 待释放时销毁；或销毁前检查 inUsePool 非空则延后
- **状态**：已登记，待排期

## IF-02: 图片订阅源浏览崩溃（根因已实锤修复，2026-08-30 Phase C）

- **来源**：用户反馈"浏览图片订阅源崩溃"，logs.zip 无崩溃栈（取证侧已闭环：CrashReport 启动回灌）
- **根因（模拟器真实复现实锤 2026-08-30 12:08）**：`ImageCanvasViewModel.loadArticleInternal` 在 execute(IO 线程) 内 `ImagePlay.appendItems` 同步更新数据源，而 `notifyItemRangeInserted` 在主线程 onSuccess 才发生——窗口期 RecyclerView 布局读到"数据源已变大但未通知"的 itemCount → FATAL `IndexOutOfBoundsException: Inconsistency detected. Invalid view holder adapter position`（进入图集页瞬间触发，无需滑动；修复前 2 跑 1 崩）。旧注释"append 与 notify 同一主线程消息"假设错误（append 不在主线程）
- **修复**：数据源追加（divider/items/loadedArticleIndices）全部移入主线程 onSuccess，与 notify 同一主线程消息内完成；连续 3 轮 L2 全绿（T1 进入/T2 内容解析+4 图下载/T3 滑动 FATAL=0）
- **配套**：Phase B 四项定向防御（H4/H6/H1/H3）继续保留（覆盖同链路其他崩溃类）；H2/H5（横向模式叠加内存/WebView 池上限）待真机 meminfo 数据后评估
- **复现资产**：ai_tests/scripts/l2_verify_image_gallery.py（自建最小图片源+本地 HTTP+确定性入口，图片链路首个固化 L2）
- **状态**：根因已修复并验证闭环
