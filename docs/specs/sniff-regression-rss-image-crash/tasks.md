# Tasks: 嗅探回归与图片订阅源崩溃取证修复

## 1. 准备工作

- [x] 1.1 备份 WebViewPool.kt 到 bak 目录 ✅（bak/sniff-regression-20260830/WebViewPool.kt.bak）
- [x] 1.2 复核 `bbc9d0a89` diff 与重构前基线实现，确认全局判断的正确写法 ✅（git show 已复核：分层前为单池全局判断；回灌设计定稿为"启动时 crash 文件内容分块写入 appLog"，crash 文件本身由 CrashHandler 同步落盘最可靠，appLog 是用户现有导出流程必含文件）

## 2. 核心实现

- [x] 2.1 WebViewPool.kt：`release()` `pauseTimers()` 守卫改为"跨全部 scope 的 inUsePool 全局为空"（新增 isGlobalIdle()；resettingPool 不计入——被释放实例已在该池且仅加载空白页，冻结无害，保持与分层前语义等价）
- [x] 2.2 WebViewPool.kt：`acquire()` 改为无条件 `resumeTimers()`
- [x] 2.3 取证增强：CrashHandler.readLatestCrashLog() + MainActivity.notifyAppCrash 启动回灌（CrashReport tag 分块 1800 字符，绕开 AppLog 2000 截断；DEBUG 包同样回灌）
- [x] 2.4 基于 git diff 更新 updateLog.md ✅（仅登记本任务 2 条，工作区混有并行会话在途变更未纳入）

## 3. 验证

- [x] 3.1 编译门禁：BUILD SUCCESSFUL ✅（build-legado.bat 4m5s，测试包 legado_miss_app_3.26.083010.apk；临时诊断版增量编译 2m35s 亦过；最终干净包重打中）
- [x] 3.2 真机 L2 场景 S1 ✅：verify_rss_sniff_after_download.py 全场景 3/3 PASS（A 首次嗅探命中+嗅探链路 AppLog 标记 PASS / E 会话复用再嗅探 PASS / 无崩溃 / 无解析错误；MEmu SDK28 实机）
- [x] 3.3 场景 S2/S3 ⚠️ Level2：release 全局空闲守卫为分层前语义的代码等价还原（单点判断+全局遍历），S1 通过佐证无冻结回归；pauseTimers 保留路径未单独构造观测（机制确定性高，登记为⚠️）
- [x] 3.4 真机 L2 场景 S4 ✅：伪造 15KB 崩溃文件+appCrash=true → 启动后 appLog 出现 9 个 CrashReport 分块 + 伪造栈 200 帧完整回灌（recordLog 开启通道）；recordLog 关闭时走 logcat ERROR 通道
- [x] 3.5 移除所有临时验证日志 ✅（MainActivity TEMP-DIAG 3 处 + android.util.Log import 已移除，Grep 0 残留；模拟器伪造 crash 文件已删）
- [x] 3.6 文档同步 ✅（task-navigation.md WebViewPool 锚点修正 help/webView/ 路径；issues-found.md 登记 IF-01 destroyScope 风险 / IF-02 取证闭环；INDEX.md 状态流转）

## AOAdapt 日志

- [x] 2.3/3.4 取证增强
  - Action: 初版用 `am crash` 制造真崩溃
  - Observation: MEmu 上 `am crash` 命中 `chrome:sandboxed_process0`（WebView 沙箱进程）而非主进程，且 crash 文件在 externalCacheDir 非 /data/data
  - Adapt: 改用 root 直写伪造 crash 文件 + local.xml 置 appCrash=true 的等价路径，走真实回灌代码
- [x] 3.4 回灌观测
  - Action: 设 flag 后启动抓 logcat -s CrashReport
  - Observation: 两次均"flag 被消费但无任何输出"，误判回灌未执行
  - Adapt: 根因=recordLog 关闭时回灌只走 Log.e（tag 非类名路径），且 logcat 主缓冲 15 秒被刷滚驱逐；开启 recordLog 后文件通道实测 9 分块+200 帧完整回灌 PASS。教训：logcat 验证必须考虑缓冲滚动，文件通道（recordLog）才是确定性观测面
- [x] 环境事故（已修复+如实报告）
  - Action: PowerShell `>` 重定向拉取 shared_prefs 文件
  - Observation: 拉取即损坏（51 字节），并已把损坏内容回写到模拟器 `<pkg>_preferences.xml`（默认 SharedPreferences），导致模拟器默认 prefs 设置丢失（重置为空）
  - Adapt: base64 通道安全写回合法 XML；local.xml（appCrash 所在）全程未受损；影响范围=测试模拟器默认 prefs（已置 recordLog=true 供后续测试复用）。与既有教训"git show > file 重定向毁文件（PowerShell 管道）"同类，后期统一沉淀"adb 输出落盘必须走 base64/exec-out"

## 4. Phase B：图片订阅源崩溃定向防御（验收后 goal 续跑，审计驱动）

- [x] 4.1 子代理静态审计图片浏览链路（6 高风险点 H1-H6 + 中低风险清单），结论=OOM 静默击杀链（H1+H2+H3+H5）最吻合"真机 256MB heap 崩溃且无 FATAL"特征；H4 与 crash-2026-07-26 同型守卫缺失
- [x] 4.2 H4 修复：ImageDetailAdapter.onViewRecycled 补 Activity 销毁守卫（Glide.with destroyed activity，与 ImageCanvasAdapter.isGlideUsable 对齐）
- [x] 4.3 H6 修复：ActivityExtensions.showDialogFragment 非 RESUMED 态兜底 showAllowingStateLoss（onStop 后弹框 IllegalStateException → 全局收益）
- [x] 4.4 H1 修复：ImageCanvasAdapter.loadIntoPhotoView 小内存设备（heap≤320MB）解码高度收敛到屏高（25MB→6MB 每张，布局不变）
- [x] 4.5 H3 修复：OkHttpStreamFetcher 小内存设备 >10MB 图片跳过解密透传（readBytes 双份 byte[] 峰值规避）
- [x] 4.6 H2/H5 登记不修（横向模式 override 与 GLOBAL 池上限，改动面大需真机 meminfo 数据支撑，挂回灌栈后随根因修复一并评估）；模拟器无图片源+heap 不匹配，运行时复现不可行（取证回灌通道已就绪）
- [x] 4.7 updateLog ✅ / 编译门禁 ✅（BUILD SUCCESSFUL 1m26s；H6 修正 AOAdapt：showAllowingStateLoss 在当前 androidx.fragment 版本不可解析 → 改 commitAllowingStateLoss 等价写法）/ L2 冒烟 ✅（verify_no_crash 083011 装机二轮重启崩溃模式全零）/ INDEX-README 状态流转 ✅

## 5. Phase C：图片订阅源崩溃真实根因复现+修复（goal 续跑第二轮）

- [x] 5.1 自建最小图片源复现环境（纯 python PNG 生成器+本地 HTTP 服务+adb reverse+测试源 JSON+RssSortActivity 确定性 extras 入口），沉淀固化脚本 l2_verify_image_gallery.py（图片链路首个 L2 资产）
- [x] 5.2 **崩溃真实复现**：进入图集页瞬间 FATAL IndexOutOfBoundsException（RecyclerView Inconsistency detected，ImageCanvasAdapter），修复前 2 跑 1 崩——与用户"浏览图片订阅源崩溃"同型，用户真机 heap 256MB 加剧触发概率
- [x] 5.3 **H7 根因修复**：[ImageCanvasViewModel.loadArticleInternal] appendItems 在 execute(IO 线程) 同步更新数据源而 notify 在主线程 onSuccess——窗口期布局读到"已变大未通知"的 itemCount（旧注释"同一主线程消息"假设错误，append 不在主线程）；修复=数据源追加全部移入主线程 onSuccess，与 notify 同消息完成
- [x] 5.4 修复验证：编译门禁 BUILD SUCCESSFUL 1m43s；修复后连续 3 轮 L2 全绿（T1 进入图集页/T2 文章解析+4 图真实下载/T3 滑动浏览 FATAL=0 前台存活）
- [x] 5.5 真实崩溃栈回灌实证：12:08 真实崩溃产生 crash-2026-08-30-12-08-14-*.log → 下次启动回灌 appLog（CrashReport 3 分块含 IndexOutOfBounds 真实栈）——取证链路在真实崩溃上闭环
- [x] 5.6 AOAdapt：①导航偶发失败（列表刷新吞 tap/StaleObjectException）→ 点击-验证-重试闭环；②T2 图片请求 0 → 文章 body 按 link 缓存+Glide 磁盘缓存命中 → 图片与文章 link 加时间戳 cache-buster；③sed 破坏 local.xml XML → App 解析失败静默回退空表并覆写丢键 → 沉淀 repair_local_prefs.py 修复脚本 + SOP 铁律强化
- [ ] 5.7 updateLog 补条目 ✅ / 重打测试包 / INDEX-README-issues-found-SOP 同步 / 记忆更新
