# Bug修复批次1 - 任务清单

> 状态: ✅ 分析完成

## 0. 已修复验证通过的BUG（无需操作）

- [x] 0.1 BUG3: CDN 530错误缓存清除不生效 → ✅ RssSourceEditViewModel.kt L114-126 OkHttp Cache evictAll + ACache clear，日志0次530
- [x] 0.2 BUG4: "未找到订阅"提示语需隐藏 → ✅ VideoPlay.kt toast改为AppLog.putWarn，日志0次出现
- [x] 0.3 BUG5(HIDDEN): ExoPlayer LoadControl共享线程错误 → ✅ PlayerInstancePool.kt L97-101 移除LoadControl缓存，7-30日志0次出现
- [x] 0.4 BUG6(HIDDEN): DoH DNS冷启动 → ✅ DohDns熔断机制（30秒冷启动+5分钟禁用+异步预热）正常工作
- [x] 0.5 BUG7(HIDDEN): Cronet降级机制 → ✅ 连续5次降级+5分钟恢复探测机制正常工作
- [x] 0.6 BUG8(HIDDEN): InsetsSource警告 → ⏭️ Android 16系统问题，维持不处理

## 1. 已修复需验证的BUG

- [ ] 1.1 验证BUG1: 图片播放器第一张图被头部遮挡
  - 代码修复已存在：ImageGalleryActivity.kt L341 动态paddingTop + activity_image_gallery.xml clipToPadding=false
  - 用户真机测试仍报出 → 需验证paddingTop计算是否准确
  - 若验证失败 → 优化方案：改用fitsSystemWindows或WindowInsetsListener替代手动计算paddingTop
  - 验证方法：真机打开图片播放器，确认第一张图不被TitleBar遮挡

- [ ] 1.2 验证BUG2: 播放器优化功能5项无UI入口
  - 代码修复已存在：VideoSettingsPanel.kt L334-381 新增5项配置
  - 用户真机测试仍报出 → 需核实layout_video_settings_panel.xml中控件ID与代码一致
  - 验证方法：核实layout XML中所有控件ID与VideoSettingsPanel.kt中findViewById引用一致
  - 若ID不匹配 → 修正XML中控件ID使其与代码一致

## 2. 新发现隐藏BUG修复（P1，7-30日志深度分析）

- [ ] 2.1 修复BUG6-V2: Cronet恢复探测误判导致降级震荡
  - 在CronetInterceptor.kt中：恢复探测改用最近失败过的host（而非随机可达host）
  - 增加观察窗口期：切回Cronet后持续观察30秒，失败率>50%则立即回退OkHttp
  - 增加降级计数器：连续降级超过3次后，恢复探测间隔指数退避（5min→10min→20min）
  - 验证方法：真机测试日志中不再出现5轮降级-恢复-再降级循环

- [ ] 2.2 修复BUG7-V2: DNS negative cache导致已失败host不重试
  - 在OkHttpHelper.kt或自定义Dns类中：失败结果TTL上限30秒，超期强制重试
  - 或在NetworkCallback网络恢复事件中：主动清除DNS negative cache
  - 验证方法：网络恢复后日志中不再出现"negative cache hit"导致的不重试

- [ ] 2.3 修复BUG8-V2: rssRoutes为空解析遗漏
  - 在WebBook.kt或BookContent.kt的getRoutesContentAwait入口：ruleRoutes使用isNullOrBlank()替代!=null
  - 若ruleRoutes为空字符串：直接走默认线路解析逻辑
  - 验证方法：日志中不再出现"routesNull=true, routesSize=0"（应为routesNull=true直接跳过规则解析）

- [ ] 2.4 修复BUG9-V2: DNS解析到0.0.0.0回环超时
  - 在AnalyzeUrl.kt或自定义Dns类中：解析后过滤loopback/linkLocal/anyLocal地址
  - 过滤列表：0.0.0.0、[::]、127.x.x.x、169.254.x.x
  - 若所有结果被过滤：触发重新解析或降级到系统DNS
  - 验证方法：DNS劫持场景下不再出现"Failed to connect to [::]:443"15秒超时

## 3. 真机验证

- [ ] 3.1 编译测试包（io.legado.miss.app.debug）
- [ ] 3.2 L2真机验证：图片播放器第一张图显示正确（BUG1验证）
- [ ] 3.3 L2真机验证：播放器设置面板5项配置可访问且生效（BUG2验证）
- [ ] 3.4 L2真机验证：Cronet降级恢复无震荡循环（BUG6-V2）
- [ ] 3.5 L2真机验证：网络恢复后DNS失败host可重试（BUG7-V2）
- [ ] 3.6 L2真机验证：ruleRoutes为空字符串时视频正常播放（BUG8-V2）
- [ ] 3.7 L2真机验证：DNS劫持回环地址时快速降级不超时（BUG9-V2）

## 4. 文档同步

- [ ] 4.1 更新updateLog.md
- [ ] 4.2 更新docs/INDEX.md
- [ ] 4.3 更新项目记忆ai_memory_main.md
