# tasks：书架刷新转圈卡死修复

## 0. Delta 轮（2026-09-05 第二轮反馈：双转圈 + 源仓库导入无响应）
- [x] 0.1 fragment_bookshelf2.xml 删外层 SwipeRefreshLayout（零引用无复位层，双转圈根因）（验证：布局无 swiperefreshlayout，单层化注释在位）✅
- [x] 0.2 ImportBookSourceViewModel sourceUrls 合集分支改限流并行+progressLiveData 进度+失败聚合（验证：rg 标记 9 处在位）✅
- [x] 0.3 ImportRssSourceViewModel 同型改造（验证：rg 标记 8 处在位）✅
- [x] 0.4 进度 UI：两 Dialog 桥接 progressState + 进度挂 sheetTitle（"导入书源 · 获取中 x/y…"），strings import_fetching_progress（默认+zh）✅
- [x] 0.5 ImportSourceSheet 保持 git 原始版零改动（规避拉锯）✅
- [x] 0.6 编译打包 legado_miss_app_3.26.090513.apk（L1）✅
- [x] 0.7 L2 真机验收：文件夹布局下拉仅一个转圈且松手即收（✅ 用户已确认转圈解决）；yckceo 合集导入显示"获取中 x/y"进度
- [x] 0.8 大合集卡死真凶二段修复：comparisonSource 逐条 DB 查询（4MB 合集数千条 Room 事务，数十秒）→ 分批 500 批量 IN 查询（BookSourceDao.getBookSourceParts 新增 / RssSourceDao.getRssSources 复用）
  - AOAdapt: Action=用户反馈 4MB 合集仍卡住 | Observation=下载/解析非瓶颈，comparisonSource 逐条查询是真凶 | Adapt=批量 IN 查询+内存 map 匹配
- [x] 0.9 解析层真凶三段修复（GSON 严格布尔）：模拟器复现实锤 `IllegalStateException: Expected a boolean but was NUMBER at $[0].enabled`——第三方合集以 0/1 数字表达布尔字段，Gson 默认 BOOLEAN 适配器整包拒绝且失败无 UI 提示 → INITIAL_GSON 注册 BooleanJsonDeserializer（primitive+boxed 双注册，兼容 0/1/"true"）；干净包冒烟实测 10MB/4000 条 **4 秒全链路出列表**、crash 0
  - AOAdapt: Action=用户指令"自己去源仓库试" | Observation=scheme 复现 90s 卡死+诊断日志锁定解析层 | Adapt=GSON 宽松布尔+移除诊断日志清零+干净包 090515 冒烟 PASS
- [x] 0.10 归档 docs/specs/archive/2026-09-05-bookshelf-refresh-spinner-fix/
  - AOAdapt: Action=4 轮编译失败拉锯误判为 IDE 还原 | Observation=重启后仍"还原"实为自身并行 Edit 竞态（同文件 3 Edit 并行，后写者基于旧快照覆盖）| Adapt=同文件 Edit 严格串行+逐个 rg 验证后编译通过；教训与 AGENTS.md"6个并行Edit竞态"铁律完全吻合，热点文件操作必须串行
- [x] 0.11 网络层真凶四段修复（真机 timeout）：用户真机 yckceo 合集 timeout+原版 5s 对照 → 模拟器 TCP 取证铁证 `SYN_SENT 到被墙 IP 段`——DoH 公共解析器无 CDN 调度把重定向域名解析到不可达 IP 打爆 callTimeout，叠加 Cronet 拦截器风险 → 新增 plainImportClient（剔除 CronetInterceptor + 强制 Dns.SYSTEM），书源/订阅源导入 fetch 全部切换；yckceo 真实合集 1262（4.5MB/482 条）模拟器实测 90s 卡死 → **7s PASS** crash=0（包 legado_miss_app_3.26.090517.apk）
  - AOAdapt: Action=用户验收时反馈真机 timeout 且怀疑未下载 | Observation=纯净客户端仍卡→排除 Cronet 单因素；/proc/net/tcp6 抓到 SYN_SENT 被墙 IP | Adapt=系统 DNS 对齐原版运营商调度，一次修复两处叠加根因

## 1. 核心实现（首轮：触发即收圈）
- [x] 1.1 BookshelfScreen.kt：SwipeRefreshContainer 的 setOnRefreshListener 改为触发即收圈（`swipeRefresh.isRefreshing = false` 后调 currentOnRefresh()），移除 isRefreshing 参数与 trackedIsRefreshing 修复③（验证标准：listener 内第一行为收圈语句）✅ rg 复核 0 残留
- [x] 1.2 BookshelfFragment1.kt：删除 refreshing/refreshResetJob/复位协程 + onFragmentCreated 重挂逻辑 + import 清理（验证标准：文件内无 refreshing state 残留）✅ rg 复核 0 残留
- [x] 1.3 BookshelfFragment2.kt：同 1.2（验证标准：同上）✅ rg 复核 0 残留

## 2. 验证
- [x] 2.1 编译验证：`build-legado.bat` 打包成功，产出 legado_miss_app_3.26.090419.apk（L1）
- [ ] 2.2 真机/模拟器 L2：文件夹内下拉刷新 → 转圈松手即收；切订阅/我的返回 → 无残留转圈（L2，留用户真机验收）

## 3. 收尾
- [x] 3.1 updateLog.md 基于实际 diff 更新（L8 条目改写为最终方案描述）
- [x] 3.2 文档同步：README 状态流转；无其他关联文档需同步
- [ ] 3.3 归档至 docs/specs/archive/（验收通过后）
