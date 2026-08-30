# Bug修复批次1 - 2026-07-30 真机测试问题修复

> 状态: ✅ 分析完成

## Intent

基于用户真机测试发现的5个表面BUG和日志深度分析发现的3个隐藏BUG，以及7-30日志深度分析新发现的4个隐藏BUG，进行全面修复，确保正式包（v3.26.072917）的核心功能可用性。

## Scope

### In Scope

#### 原有BUG（8个）
- BUG1: 图片播放器第一张图被TitleBar遮挡（RecyclerView未适配状态栏）——⚠️代码已修复但用户仍报出，需验证优化
- BUG2: 播放器优化功能5项无UI入口（首帧预加载/智能缓冲/错误提示/播放历史/自动重连）——⚠️代码已修复但用户仍报出，需验证控件ID
- BUG3: CDN 530错误后清除cookie不生效（多层缓存未同步清除）——✅已修复验证通过
- BUG4: 视频订阅源"未找到订阅"提示语需隐藏——✅已修复验证通过
- BUG5(HIDDEN): ExoPlayer LoadControl共享线程错误——✅已修复验证通过
- BUG6(HIDDEN): DoH DNS冷启动全链路失败——✅机制已完善，无需额外修改
- BUG7(HIDDEN): Cronet协议错误降级不彻底——✅机制已完善，但新发现BUG6-V2需优化
- BUG8(HIDDEN): InsetsSource警告——⏭️维持不处理（Android 16系统问题）

#### 新发现隐藏BUG（4个，7-30日志深度分析）
- BUG6-V2(HIDDEN): Cronet恢复探测误判导致降级震荡（5轮降级-恢复-再降级循环）
- BUG7-V2(HIDDEN): DNS negative cache导致已失败host不重试（网络恢复后仍使用缓存失败结果）
- BUG8-V2(HIDDEN): rssRoutes为空解析遗漏（ruleRoutes空字符串被判断为非null但解析0条线路）
- BUG9-V2(HIDDEN): DNS解析到0.0.0.0回环超时（DNS劫持导致连接localhost:443超时15秒）

### Out of Scope
- 订阅源规则优化（属于legado-source-creator skill范畴）
- 新功能开发（仅修复现有BUG）
- 其他版本兼容性问题

## Approach

### Selected Approach

**增量修复策略**：在现有代码基础上最小化修改，每个BUG独立修复，互不影响。

1. BUG3/4/5：已修复验证通过，无需操作
2. BUG1/2：代码已修复但用户仍报出，需验证修复效果并可能优化
3. BUG6/7原有机制已完善，无需额外修改
4. BUG8：Android 16系统问题，维持不处理
5. BUG6-V2：优化Cronet恢复探测逻辑（改用失败host+观察窗口期+指数退避）
6. BUG7-V2：优化DNS negative cache（失败结果短TTL+网络恢复清除缓存）
7. BUG8-V2：增加ruleRoutes空白校验（isNullOrBlank替代!=null）
8. BUG9-V2：DNS结果过滤回环地址（0.0.0.0/[::]/127.x.x.x）

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 大规模重构 | 对播放器和网络层进行全面重构 | 风险高、影响范围大、回归测试困难 |
| 只修表面BUG | 只修BUG1-4，不改隐藏BUG | 隐藏BUG（特别是BUG5）严重影响用户体验，视频播放完全失败 |
| 升级ExoPlayer到最新版 | 通过升级解决LoadControl共享问题 | 项目锁定特定ExoPlayer版本，升级可能引入不兼容变更 |
| 禁用Cronet | 彻底禁用Cronet只用OkHttp | 损失Cronet性能优势（HTTP/3/QUIC），且部分源在Cronet下表现更好 |

### Drawbacks

- BUG6-V2修复可能延长Cronet恢复时间（需等失败host确实恢复），但避免反复震荡
- BUG7-V2修复增加少量DNS重试开销，但避免网络恢复后长时间不可用
- BUG9-V2修复可能误过滤极少数合法本地服务（实际场景几乎不存在）
- BUG8维持不处理，Android 16 MIUI的InsetsSource警告可能持续出现

### Prior Art

- ExoPlayer LoadControl共享问题：ExoPlayer官方文档明确说明"Players that share the same LoadControl must share the same playback thread"
- DoH冷启动失败：已知问题，App冷启动时网络栈未就绪导致DoH解析全部失败
- CDN 530错误缓存：OkHttp默认缓存策略不区分5xx错误响应，需显式配置
- DNS negative cache：OkHttp/DnsJava对失败结果有缓存TTL，是已知行为
- DNS劫持到0.0.0.0：常见DNS劫持手段，业界通用的防御方式是过滤回环/不可路由地址

## Requirements

### REQ-01: 图片播放器头部遮挡修复
- ImageGalleryActivity的RecyclerView必须设置clipToPadding=false和paddingTop适配状态栏高度
- 第一张图的顶部不得被TitleBar遮挡
- **补充**：若手动计算paddingTop不可靠，改用fitsSystemWindows或WindowInsetsListener

### REQ-02: 播放器优化功能UI入口补齐
- 在现有VideoSettingsPanel（视频右侧下方设置BottomSheet）的initSettings中新增5项配置
- 不新增全局设置入口，复用播放器内已有设置面板（用户决策：播放器已有两个设置入口，不再新增）
- 新增4个CheckBox：首帧预加载/播放历史/播放错误提示/自动重连
- 新增1个Spinner：缓冲策略(激进/平衡/保守)
- **补充**：需核实layout_video_settings_panel.xml中所有控件ID与代码中findViewById引用一致

### REQ-03: CDN错误后缓存清除不彻底修复
- RssSourceEditViewModel的"清除"功能必须同时清理：OkHttp DiskCache、ACache内存缓存
- 清除后必须验证缓存确实被清理
- **状态**：✅已实现验证通过

### REQ-04: "未找到订阅"提示语优化
- VideoPlay.kt中两处"未找到订阅"toast在正常滑动退出场景下应静默处理，不显示toast
- **状态**：✅已实现验证通过

### REQ-05: ExoPlayer LoadControl共享线程错误修复
- 每个ExoPlayer实例独立创建LoadControl，不共享
- 修复后视频播放不再出现IllegalStateException
- **状态**：✅已实现验证通过

### REQ-06: DoH DNS冷启动优化
- 冷启动时如果3个DoH服务器全部失败，立即降级到系统DNS
- 降级后5分钟内不重试DoH
- **状态**：✅机制已完善，无需额外修改

### REQ-07: Cronet协议错误降级优化
- Cronet连续协议错误达阈值后，应完全降级到OkHttp
- 降级后不应继续发送Cronet请求
- **状态**：✅机制已完善，但新发现恢复探测误判问题（REQ-08）

### REQ-08: Cronet恢复探测防震荡优化
- 恢复探测必须使用最近失败过的host，而非随机可达host
- 切回Cronet后必须有观察窗口期（如30秒），窗口内失败率超阈值立即回退OkHttp
- 连续降级超过M次后，恢复探测间隔必须指数退避
- 目标：消除5轮降级-恢复-再降级震荡循环

### REQ-09: DNS negative cache短TTL
- DNS失败结果缓存TTL上限30秒，超期后强制重试DNS解析
- 网络恢复（NetworkCallback检测）时主动清除DNS negative cache
- 目标：网络恢复后已失败host可自动重试，不再因缓存失败结果而不重试

### REQ-10: rssRoutes空白校验
- getRoutesContentAwait入口使用isNullOrBlank()替代!=null判断ruleRoutes
- ruleRoutes为空字符串时直接走默认线路解析逻辑
- 目标：ruleRoutes为空字符串时不再进入无效规则解析流程

### REQ-11: DNS回环地址过滤
- 自定义Dns实现中，解析后检查每个InetAddress，过滤loopback/linkLocal/anyLocal地址
- 过滤地址包括：0.0.0.0、[::]、127.x.x.x、169.254.x.x等
- 若所有DNS结果均被过滤，触发重新解析或降级到系统DNS
- 目标：DNS劫持将域名解析到回环地址时，不再等待15秒超时，快速降级

## Scenarios

### Scenario 1: 图片播放器打开后第一张图显示正确
- 前置条件：用户在订阅源文章中点击图片
- 操作：进入图片播放器
- 预期：第一张图完整显示，不被TitleBar遮挡

### Scenario 2: 播放器设置面板可访问5项新增配置
- 前置条件：用户在视频播放器中
- 操作：点击右侧下方设置按钮，打开VideoSettingsPanel
- 预期：在设置面板中可以看到首帧预加载/缓冲策略/播放历史/播放错误提示/自动重连5项配置

### Scenario 3: CDN 530错误后清除缓存生效
- 前置条件：某订阅源图片获取返回530错误
- 操作：用户在订阅源右上角三点菜单中点击"清除"
- 预期：再次访问时重新请求而非使用缓存错误响应

### Scenario 4: 视频播放器滑动退出无多余提示
- 前置条件：用户在内置视频播放器中
- 操作：一直下拉后右滑退出
- 预期：退出过程中不显示"未找到订阅"toast

### Scenario 5: 视频播放不再因LoadControl共享失败
- 前置条件：用户点击视频播放
- 操作：切换到下一个视频
- 预期：ExoPlayer不再抛出IllegalStateException，视频正常播放

### Scenario 6: 冷启动网络请求快速响应
- 前置条件：App冷启动
- 操作：立即访问订阅源列表
- 预期：DoH失败后快速降级系统DNS，列表在3秒内加载

### Scenario 7: Cronet降级后不产生震荡循环
- 前置条件：Cronet因协议错误降级到OkHttp
- 操作：5分钟后恢复探测
- 预期：恢复探测使用失败过的host测试；切回Cronet后有30秒观察窗口；窗口内失败则立即回退；不会出现5轮降级-恢复-再降级循环

### Scenario 8: 网络恢复后DNS失败结果可重试
- 前置条件：某host DNS解析失败被缓存（negative cache）
- 操作：网络恢复后再次请求该host
- 预期：失败缓存TTL≤30秒，超期后重新DNS解析；或网络恢复事件触发清除negative cache

### Scenario 9: ruleRoutes为空字符串时正常播放
- 前置条件：某视频源ruleRoutes字段为空字符串（非null）
- 操作：播放该源视频
- 预期：直接走默认线路解析逻辑，不进入无效规则解析流程

### Scenario 10: DNS劫持解析到回环地址时快速降级
- 前置条件：DNS劫持将某域名解析到0.0.0.0或[::]
- 操作：请求该域名
- 预期：过滤回环地址后降级到系统DNS重新解析，不等待15秒超时
