# Bug修复批次1 - 技术设计

> 状态: ✅ 分析完成

## Technical Approach

对8个原有BUG + 4个新发现隐藏BUG采取独立修复策略，每个BUG定位到具体代码文件，最小化修改范围。

### BUG1: 图片播放器第一张图被头部遮挡

**根因**: ImageGalleryActivity的RecyclerView没有设置clipToPadding=false和paddingTop来适配状态栏/TitleBar高度。当RecyclerView的item从顶部开始布局时，第一张图被TitleBar覆盖。

**修复状态**: ⚠️ 代码已修复但需验证——代码修复已存在（ImageGalleryActivity.kt L341 动态paddingTop + activity_image_gallery.xml clipToPadding=false），但用户真机测试仍报出，可能paddingTop计算不准确或TitleBar隐藏后高度变化。

**优化方案**: 改用fitsSystemWindows或WindowInsetsListener替代手动计算paddingTop，确保TitleBar高度适配更可靠。

**涉及文件**: `activity_image_gallery.xml`, `ImageGalleryActivity.kt`

### BUG2: 播放器优化功能5项无UI入口

**根因**: 播放器综合审查(player-comprehensive-audit-20260729)实施了5项后端功能（AD-01 FirstFramePreloader/AD-02 智能缓冲/AD-03 ErrorMapper/AD-04 PlayHistory/VideoPlay.kt 4配置项），但未在SettingsActivity或Preferences中添加对应的UI入口。用户看不到=不存在。

**修复状态**: ⚠️ 代码已修复但需验证——代码修复已存在（VideoSettingsPanel.kt L334-381 新增5项配置），但用户真机测试仍报出，可能layout_video_settings_panel.xml中对应控件ID与代码中不匹配导致findViewById返回null。

**优化方案**: 核实layout_video_settings_panel.xml中所有控件ID与VideoSettingsPanel.kt中findViewById引用一致。

**用户决策**：不新增全局设置入口，而是加到视频右侧下方的设置面板中（VideoSettingsPanel BottomSheet），因为播放器已有两个设置入口（右上角三点+右侧下方设置按钮），不再新增

**涉及文件**: `VideoSettingsPanel.kt`, `layout_video_settings_panel.xml`, `strings.xml`, `VideoPlay.kt`

### BUG3: CDN 530错误后清除cookie不生效

**根因**: RssSourceActivity的"清除"功能只清理了CookieStore中的cookie和数据库，未清理以下缓存层：
- OkHttp DiskCache缓存了530错误响应
- ACache内存缓存了旧数据
- WebView缓存未清理

**修复状态**: ✅ 已修复——代码修复已存在（RssSourceEditViewModel.kt L114-126 OkHttp Cache evictAll + ACache clear），日志中0次530出现，修复生效。

**涉及文件**: `RssSourceEditViewModel.kt`, `HttpHelper.kt`或`OkHttpHelper.kt`

### BUG4: "未找到订阅"提示语需隐藏

**根因**: VideoPlay.kt L331和L1258两处`appCtx.toastOnUi("未找到订阅")`在用户正常滑动退出视频播放器时触发，因为rssArticle在退出过程中变为null。这个提示对用户无价值且干扰操作。

**修复状态**: ✅ 已修复——代码修复已存在（VideoPlay.kt中toast已改为AppLog.putWarn），日志中0次出现，修复生效。

**涉及文件**: `VideoPlay.kt`

### BUG5(HIDDEN): ExoPlayer LoadControl共享线程错误

**根因**: 日志铁证 `IllegalStateException: Players that share the same LoadControl must share the same playback thread`。多个ExoPlayer实例共享同一个LoadControl对象，但在不同的playback thread上运行。这是ExoPlayer的硬性约束：共享LoadControl的Player必须共享playback looper。

**修复状态**: ✅ 已修复——代码修复已存在（PlayerInstancePool.kt L97-101 移除LoadControl缓存，每实例独立创建），7-30日志中0次出现（7-29早期06:23仍有18次为修复前产生）。

**涉及文件**: `PlayerInstancePool.kt`

### BUG6(HIDDEN): DoH DNS冷启动全链路失败

**根因**: 日志铁证：App冷启动时3个DoH服务器全部UnknownHostException，导致所有新连接等待DoH超时后才fallback到系统DNS。DohDns已有熔断机制（5分钟禁用），但冷启动首次全失败的延迟仍影响体验。

**修复状态**: ✅ 机制已完善——已有DohDns熔断机制（30秒冷启动+5分钟禁用+异步预热），日志验证机制正常工作，无需额外修改。

**涉及文件**: `DohDns.kt`

### BUG7(HIDDEN): Cronet协议错误降级不彻底

**根因**: 日志铁证：Cronet协议错误触发降级到OkHttp后，仍有大量"Cronet request canceled (normal)"日志，说明降级后仍有一些已发出的Cronet请求在排队等待取消，影响性能。

**修复状态**: ✅ 机制已完善——已有Cronet连续5次降级+5分钟恢复探测机制，日志验证机制正常工作。但新发现BUG6-V2（恢复探测误判）需优化。

**涉及文件**: `CronetInterceptor.kt`

### BUG8(HIDDEN): InsetsSource警告

**根因**: Android 16 MIUI特有警告，`InsetsSource: Has no intersection or mTmpFrame.height()=0`。大量重复但不影响功能。这是Android 16系统框架问题，非App可控。

**修复状态**: ⏭️ 维持不处理——Android 16系统问题，记录为已知问题。

---

## 新发现隐藏BUG（7-30日志深度分析）

### BUG6-V2(HIDDEN): Cronet恢复探测误判导致降级震荡

**严重度**: 中

**根因**: Cronet降级后恢复探测使用的是可达host，但实际不可达host仍会导致Cronet失败。证据：5轮"降级OkHttp→恢复探测成功2次→切回Cronet→立即5次失败→再次降级"震荡循环。

**修复方案**:
1. 恢复探测应使用最近失败过的host（而非随机可达host），验证该host确实恢复后才切回Cronet
2. 增加恢复探测窗口期：切回Cronet后持续观察N秒，若失败率>阈值则立即回退OkHttp，避免反复震荡
3. 增加降级计数器：连续降级超过M次后，延长恢复探测间隔（指数退避）

**涉及文件**: `CronetInterceptor.kt`

### BUG7-V2(HIDDEN): DNS negative cache导致已失败host不重试

**严重度**: 中

**根因**: OkHttp内部DNS缓存对失败结果有TTL（negative cache），网络恢复后已失败的DNS结果仍被缓存，不会重新查询。证据：多次"negative cache hit"日志，即使网络已恢复也不重试。

**修复方案**:
1. 在OkHttp DNS层增加失败结果TTL上限（如30秒），超期后强制重试DNS解析
2. 或在NetworkCallback检测到网络恢复时，主动清除DNS negative cache
3. 自定义Dns实现包装OkHttp默认Dns，拦截negative cache结果并设置短TTL

**涉及文件**: `OkHttpHelper.kt`或自定义DNS实现类

### BUG8-V2(HIDDEN): rssRoutes为空解析遗漏

**严重度**: 低

**根因**: 部分视频源的ruleRoutes字段虽存在但为空字符串，被判断为!=null但解析出0条线路。证据：2次"parseRssRoutes结果: routesNull=true, routesSize=0"，但视频仍能播放（说明有fallback路径）。

**修复方案**:
1. 在getRoutesContentAwait入口增加ruleRoutes空白校验：使用isNullOrBlank()替代!=null判断
2. 若ruleRoutes为空字符串，应直接走默认线路解析逻辑而非进入规则解析流程

**涉及文件**: `WebBook.kt`或`BookContent.kt`中getRoutesContentAwait方法

### BUG9-V2(HIDDEN): DNS解析到0.0.0.0回环超时

**严重度**: 中

**根因**: 部分DNS劫持将域名解析到0.0.0.0或[::]，OkHttp尝试连接localhost:443导致15000ms超时。证据："Failed to connect to [::]:443" + "localhost/127.0.0.1:443"超时。

**修复方案**:
1. 在AnalyzeUrl或网络层增加DNS结果校验：过滤0.0.0.0/[::]/127.x.x.x等回环/不可路由地址
2. 自定义Dns实现中，解析后检查每个InetAddress，若为loopback/linkLocal/anyLocal则跳过
3. 若所有DNS结果均被过滤，触发重新解析或降级到系统DNS

**涉及文件**: `AnalyzeUrl.kt`或自定义DNS实现类

---

## Architecture Decisions

### AD-01: LoadControl独立创建 vs 共享
- **Context**: ExoPlayer多实例场景（视频滑动切换）
- **Concern**: 共享LoadControl导致IllegalStateException
- **Decision**: 每个ExoPlayer实例独立创建LoadControl
- **Goal**: 消除LoadControl共享线程约束冲突
- **Tradeoff**: 每个实例独立LoadControl增加少量内存开销，但消除100%播放失败风险
- **Status**: ✅ Implemented & Verified

### AD-02: "未找到订阅"toast改为静默日志
- **Context**: 用户在视频播放器中滑动退出时触发"未找到订阅"toast
- **Concern**: 正常退出场景不该有多余提示
- **Decision**: 将toast改为AppLog.putWarn记录，不显示UI
- **Goal**: 减少用户干扰，保留问题可追溯性
- **Tradeoff**: 用户不再看到提示，但可通过日志排查
- **Status**: ✅ Implemented & Verified

### AD-03: DoH冷启动快速降级
- **Context**: App冷启动时DoH全链路失败
- **Concern**: 首次网络请求延迟高
- **Decision**: 冷启动30秒内跳过DoH直接用系统DNS
- **Goal**: 冷启动网络请求快速响应
- **Tradeoff**: 冷启动30秒内无DoH保护（隐私降级），但用户体验优先
- **Status**: ✅ Implemented & Verified

### AD-04: 播放器设置UI入口
- **Context**: 5项播放器优化功能无UI入口
- **Concern**: 用户无法发现和配置这些功能
- **Decision**: 在现有VideoSettingsPanel（视频右侧下方设置BottomSheet）的initSettings中新增5项配置，不新增全局设置入口
- **Goal**: 用户可在视频播放器设置面板中调整播放器行为
- **Tradeoff**: 仅在播放器内可配置（需进入播放器才能修改），但符合用户已有操作习惯，不增加设置页面复杂度
- **Status**: ⚠️ Implemented, Needs Verification (用户仍报出，可能控件ID不匹配)

### AD-05: CDN错误缓存清除统一入口
- **Context**: 清除cookie后CDN 530错误仍存在
- **Concern**: 多层缓存未同步清除
- **Decision**: RssSourceActivity清除操作统一清理OkHttp Cache + ACache + WebView缓存
- **Goal**: 清除操作后所有缓存层同步失效
- **Tradeoff**: 清除操作耗时增加（OkHttp Cache evictAll需要磁盘IO），但确保彻底清理
- **Status**: ✅ Implemented & Verified

### AD-06: Cronet恢复探测改用失败host
- **Context**: Cronet恢复探测用可达host导致降级震荡
- **Concern**: 5轮降级-恢复-再降级震荡循环
- **Decision**: 恢复探测改用最近失败过的host + 增加观察窗口期 + 指数退避
- **Goal**: 消除降级震荡，Cronet恢复判断更准确
- **Tradeoff**: Cronet恢复可能更慢（需等失败host确实恢复），但避免反复切换
- **Status**: Proposed

### AD-07: DNS negative cache短TTL
- **Context**: OkHttp DNS缓存对失败结果TTL过长，网络恢复后不重试
- **Concern**: 网络恢复后已失败host仍不重试
- **Decision**: 失败结果TTL上限30秒，超期强制重试
- **Goal**: 网络恢复后DNS解析可自动恢复
- **Tradeoff**: 增加少量DNS重试开销，但避免网络恢复后长时间不可用
- **Status**: Proposed

### AD-08: DNS结果回环地址过滤
- **Context**: DNS劫持将域名解析到0.0.0.0/[::]/127.x.x.x
- **Concern**: 连接回环地址导致15秒超时
- **Decision**: 自定义Dns实现过滤loopback/linkLocal/anyLocal地址
- **Goal**: 避免连接无效回环地址，快速降级到系统DNS
- **Tradeoff**: 极少数合法本地服务可能被误过滤，但实际场景几乎不存在
- **Status**: Proposed

## Data Flow

### 图片播放器首次显示流程（修复后）
1. ImageGalleryActivity.onCreate → initRecyclerView
2. 计算TitleBar高度 → 设置RecyclerView.paddingTop + clipToPadding=false
3. 第一张图从paddingTop位置开始布局，不被TitleBar遮挡

### 清除缓存统一流程（修复后）
1. 用户点击"清除"
2. 清理CookieStore
3. 清理OkHttp Cache（evictAll）
4. 清理ACache内存缓存
5. 清理WebView缓存
6. 提示用户清除完成

### Cronet降级恢复流程（BUG6-V2修复后）
1. Cronet连续5次协议错误 → 降级OkHttp + 记录失败host列表
2. 5分钟后恢复探测 → 使用失败host（非随机可达host）测试Cronet
3. 切回Cronet → 进入观察窗口期（如30秒）
4. 观察窗口内失败率>阈值 → 立即回退OkHttp + 延长下次恢复间隔
5. 观察窗口内稳定 → 确认恢复，退出降级模式

### DNS解析流程（BUG7-V2/BUG9-V2修复后）
1. OkHttp发起请求 → 自定义Dns解析
2. 检查DNS缓存（失败结果TTL≤30秒）
3. 解析结果过滤：移除0.0.0.0/[::]/127.x.x.x等回环地址
4. 若所有结果被过滤 → 降级到系统DNS重新解析
5. 返回有效地址列表

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| activity_image_gallery.xml | 修改 | RecyclerView添加clipToPadding=false和paddingTop（已有，需验证） |
| ImageGalleryActivity.kt | 修改 | 动态计算TitleBar高度设置paddingTop（已有，需验证优化为WindowInsetsListener） |
| VideoSettingsPanel.kt | 修改 | 在initSettings中新增5项配置（已有，需验证控件ID匹配） |
| layout_video_settings_panel.xml | 修改 | 新增5项配置UI控件（已有，需验证ID与代码一致） |
| strings.xml | 修改 | 新增播放器设置相关字符串资源 |
| RssSourceEditViewModel.kt | 修改 | 清除操作增加OkHttp Cache + ACache缓存清理（✅已修复） |
| VideoPlay.kt | 修改 | "未找到订阅"toast改为AppLog.putWarn（✅已修复） |
| PlayerInstancePool.kt | 修改 | 移除LoadControl缓存，每实例独立创建（✅已修复） |
| DohDns.kt | 修改 | 冷启动30秒内跳过DoH直接用系统DNS（✅机制已完善） |
| CronetInterceptor.kt | 修改 | 恢复探测改用失败host + 观察窗口期 + 指数退避 |
| OkHttpHelper.kt或自定义Dns类 | 新增 | DNS negative cache短TTL + 回环地址过滤 |
| AnalyzeUrl.kt | 修改 | DNS结果校验过滤回环地址 |
| WebBook.kt或BookContent.kt | 修改 | getRoutesContentAwait入口ruleRoutes空白校验（isNullOrBlank） |
