# 合并裁决单：cronet-global-enable / network-perf-stability / thread-pool-audit × video-sniff 4.8c 开关双逻辑

> **总线任务**：master-track-orchestration tasks 2.11（2.11.1 触点清单对照 + 2.11.2 合并裁决）
> **裁决日期**：2026-09-01 ｜ **性质**：纯文档裁决，零代码改动
> **裁决原则**：以当前代码实际实现为权威基准；video-sniff 4.8c 已实施且与代码一致，以其表述为开关双逻辑唯一权威口径；其余 spec 陈旧描述标注归一注记；未实施且与已实现逻辑冲突的条目标注"冻结待裁决"，不改其 tasks 勾选。

---

## 一、代码权威事实（2026-09-01 实测锚点）

| # | 事实 | 锚点 |
|---|------|------|
| F1 | 用户开关 `AppConfig.isCronet`（PreferKey.cronet）**默认 false**，仅控制 OkHttp builder 是否装配 CronetInterceptor（爬取链路） | `AppConfig.kt:65`、`HttpHelper.kt:180-189` |
| F2 | 视频链路 `cronetDataFactory` **无条件装配**（cronetEngine 非空即优先 Cronet、失败回退 OkHttp），不受 isCronet 控制 | `ExoPlayerHelper.kt:1028-1032`（4.8c 澄清注释已固化） |
| F3 | 爬取链路自动降级熔断已完整实现：`DEGRADE_THRESHOLD=5`（连续 5 次协议错误→会话内降级 OkHttp）+ 启动宽限 300ms + half-open 恢复探测（5min 放行/连续 2 次成功切回）+ 震荡抑制（30s 内再降级延长 15min）+ HTTP/2 协议错误降级缩短 1min + 证书错误独立去重 | `CronetInterceptor.kt:23-70`（演进自 app-stability-round2 P2-1 / T4.3 / N-P1-1 / BUG6-V2 / P1-2） |
| F4 | OkHttp 连接池现状 = `ConnectionPool(128, 5, TimeUnit.MINUTES)` | `HttpHelper.kt:102` |
| F5 | 线程数配置现状：`searchThreadCount` 默认 32、coerceIn(1,128)；`updateCacheThreadCount` 默认 16、coerceIn(1,256) | `AppConfig.kt:2874-2884` |
| F6 | video-sniff Phase 0 钳制已落地：WebViewPool `coerceAtMost(15)`；CacheBookService `minOf(updateCacheThreadCount, 128)` | `WebViewPool.kt:61`、`CacheBookService.kt:46` |
| F7 | Cronet 版本现状 = **500.0.1**（CronetMainVersion=500.0.0.0） | `gradle.properties:53-54` |
| F8 | `CronetCoroutineInterceptor` 存在但**未在 HttpHelper builder 装配**（装配的是同步版 CronetInterceptor） | `CronetCoroutineInterceptor.kt:24`、`HttpHelper.kt:182` |
| F9 | 视频链路强制 HTTP/1.1 专用 client（videoStreamClient）规避 HTTP/2 协议错误，与爬取链路降级机制正交 | `HttpHelper.kt:240-244` |

## 二、4.8c 开关双逻辑权威口径（基准条目）

**video-sniff-403-and-rss-classic-fix tasks 4.8c**（已实施 ✅ Level1，纯注释零行为）：

> cronet 开关两条逻辑梳理（Z7）：①用户开关（AppConfig.isCronet，PreferKey.cronet 默认 false）仅控制 OkHttp builder 是否装配 CronetInterceptor（爬取链路）；②视频链路 cronetDataFactory 无条件装配不受该开关控制。两条逻辑独立，互不联动。

配套口径：design.md Z7（现状盘点表）+ F-07（双"Cronet 默认"消解——"默认启用"仅指视频链路）+ spec.md R-P1-7（视频链路 Cronet 保留主网络栈不回退 OkHttp，Cookie 断链修复=Cronet 链路补注入；DohDns 不废弃）。

## 三、触点对照清单（2.11.1）

### 域 A：Cronet 网络开关/降级开关

| 触点 | spec 条目 | 条目描述 | 与代码现状关系 | 判定 |
|------|----------|---------|--------------|------|
| A1 | video-sniff tasks **4.8c**（Z7） | 开关双逻辑梳理，纯注释固化 ExoPlayerHelper L1028 | 与 F1/F2 一致 | **基准（权威）** |
| A2 | video-sniff design **Z7 / F-07** | 双"Cronet 默认"消解，"默认启用"仅指视频链路 | 与 F1/F2 一致 | 互补，并入基准 |
| A3 | video-sniff spec **R-P1-7**（tasks 2.8a ✅） | 视频链路 Cronet 保留主栈不回退 OkHttp；preResolveDns 改 DohDns | 已实施 | 互补 |
| A4 | cronet-global-enable **REQ-01**（P0） | `isCronet` 默认值改 true | **与 F1 冲突（代码默认 false）**，该 spec 状态"🔄 设计中"未进入实施 | **冻结待裁决** |
| A5 | cronet-global-enable **REQ-03**（P0） | 降级链 Cronet→fallback→OkHttp + JNI 崩溃监控；"保留现有连续 5 次协议错误降级" | 阈值 5 与 F3 一致；但 F3 实现已远超条目描述（探测/迟滞/震荡抑制/HTTP2 分级均未提及）；JNI 崩溃自动降级未见对应实现 | 陈旧描述，归一注记（以 F3 为权威） |
| A6 | cronet-global-enable **Scenario 2/3** | install 失败回退 / 用户关闭 isCronet 回退纯 OkHttp | 与 F1 一致（爬取链路）；未提视频链路无条件装配（F2） | 部分陈旧，归一注记 |
| A7 | network-perf-stability **P2-2 Cronet 熔断器**（评估未实施） | "自实现熔断需充分测试" | **已陈旧**：熔断器已随 CronetInterceptor 完整实现（F3），评估前提已消失 | 归一销项注记 |
| A8 | network-perf-stability **P2-3 启用 Cronet 协程拦截器**（评估未实施） | 理由=协程版 runBlocking | 与 F8 一致（仍未装配，评估项仍有效） | 保留待评估，无冲突 |
| A9 | network-perf-stability **F-P1-6**（tasks 26.5 ✅） | Cronet 128→149 升级 | 已实施，但版本口径已演进至 500.0.1（F7） | 版本口径陈旧，归一注记 |
| A10 | cronet-global-enable 头注 | "当前 150.0.7871.128 已稳定运行" | 与 F7 不符 | 版本口径陈旧，归一注记 |
| A11 | cronet-global-enable **REQ-06/REQ-07** | 性能监控 / ProGuard+JNI 崩溃监控 | 未实施，无代码冲突；REQ-07 引用"Cronet 149+ ProGuard 铁证"版本口径随 A10 一并陈旧 | 未实施不冲突，版本口径随 A10 归一 |

### 域 B：连接池（线程池 × 网络交叉点）

| 触点 | spec 条目 | 条目描述 | 与代码现状关系 | 判定 |
|------|----------|---------|--------------|------|
| B1 | network-perf-stability **C3**（tasks 17.x ✅） | ConnectionPool(50, 5, MINUTES) | 已实施后被覆盖：现状 128（F4，video-sniff R-P0-6） | 已归一（128 为权威），注记演进链 |
| B2 | video-sniff spec **R-P0-6**（Phase 0） | HttpHelper ConnectionPool 50→128 | 与 F4 一致 | 实施权威 |
| B3 | thread-pool-audit **R1.3 / Scenario 3** | 审查 ConnectionPool(50,5,MINUTES) 匹配度 | 审查基线数字陈旧（50→128） | 归一注记（基线数字更新），与总线 3.6 线程钳制定稿交叉引用 |

### 域 C：线程池开关（用户配置项）

| 触点 | spec 条目 | 条目描述 | 与代码现状关系 | 判定 |
|------|----------|---------|--------------|------|
| C1 | thread-pool-audit **R1.1 / 审查清单 #2-#10** | 8 个 FixedThreadPool 共用 searchThreadCount/updateCacheThreadCount | 与 F5 一致（配置项名/默认值一致） | 一致，互补 |
| C2 | video-sniff spec **R-P0-3** | 更新和缓存线程数上限 64→256（UI max + coerceIn(1,256)） | 与 F5 一致（已实施） | 实施权威 |
| C3 | video-sniff spec **R-P0-4** | WebViewPool coerceAtMost(15) | 与 F6 一致（已实施） | 实施权威 |
| C4 | video-sniff spec **R-P0-5** | CacheBookService/ImageCanvasViewModel min(n,128) | CacheBookService 已实施（F6，写法 minOf）；ImageCanvasViewModel 未逐一验证 | CacheBookService 权威；ImageCanvasViewModel 留总线 3.6 定稿核验 |
| C5 | thread-pool-audit **R4.1/R4.2** | 过大 OOM 风险 / 上限保护审查维度 | 与 C2-C4 互补（audit 提供审查框架，video-sniff 提供实施事实） | 互补，无冲突 |
| C6 | thread-pool-audit **R1.5 / Scenario 5** | DispatchersMonitor recordLog 开关 | 与 4.8c 无交集 | 正交，不动 |
| C7 | 总线 tasks **3.6** | thread-pool-audit 与 video-sniff 线程钳制定稿（W2 首项） | 本裁决不替代 3.6：3.6 负责"钳制参数定稿"，本裁决负责"开关/降级逻辑归一" | 交叉引用，边界声明 |

## 四、裁决结论（2.11.2）

**裁决 R1（开关双逻辑，唯一权威口径）**：以 video-sniff 4.8c / design Z7 / F-07 表述为唯一权威——
- 爬取链路：`AppConfig.isCronet`（默认 false）控制 OkHttp builder 装配 CronetInterceptor；其内含自动降级熔断（F3 全参数以 CronetInterceptor.kt 实测为准）。
- 视频链路：cronetDataFactory 无条件装配，不受 isCronet 控制；Cronet 不可用回退 OkHttp；视频链路不回退 OkHttp 主栈（R-P1-7）。
- 两逻辑独立不联动，任何 spec 不得再引入第三种"默认启用"表述。

**裁决 R2（cronet-global-enable REQ-01）**：**冻结待裁决**。理由：未实施（代码默认 false）+ 与已固化的 4.8c 口径冲突（该 REQ 将制造第三种"默认"语义）+ 母 spec 状态"🔄 设计中"未进入实施。解冻条件：作为独立产品决策重新评审（默认启用 Cronet 爬取链路是否收回），评审前禁止任何实施引用；其 tasks 勾选状态不动。

**裁决 R3（降级机制描述归一）**：所有 spec 中关于"连续 5 次协议错误降级 OkHttp"的描述，一律归一为 F3 完整口径（阈值 5 + 宽限 300ms + half-open 探测 5min/连续 2 次成功 + 震荡抑制 15min + HTTP/2 分级 1min + 证书错误独立去重）。cronet-global-enable REQ-03、network-perf-stability P2-2 均按此归一。

**裁决 R4（连接池数值归一）**：连接池权威值 = `ConnectionPool(128, 5, MINUTES)`（F4）。演进链：原版默认 5 → network-perf-stability C3 实施 50 → video-sniff R-P0-6 调整 128。network-perf-stability C3 与 thread-pool-audit R1.3/Scenario 3 标注"基线已演进至 128，以本裁决为权威"。

**裁决 R5（Cronet 版本口径归一）**：版本权威 = `gradle.properties`（当前 500.0.1）。凡 spec 中出现 128.x/149.x/150.x 历史版本表述，均为时点快照，以 gradle.properties 实时值为准（该值随自动化升级链演进，文档禁止硬编码快照）。

**裁决 R6（线程池开关边界）**：thread-pool-audit 为审查型框架 spec，与 video-sniff R-P0-3~5 是"审查框架 × 实施事实"互补关系，无冲突；钳制参数终值定稿归总线 3.6（含 ImageCanvasViewModel min(n,128) 核验），本裁决不越界代裁。

**裁决 R7（P2-3 协程拦截器）**：保留待评估状态（CronetCoroutineInterceptor 存在未装配，F8），与代码无冲突，不归一不冻结。

## 五、各 spec 归一注记要求（落盘动作清单）

> 本裁决单不改各 spec tasks 勾选；以下注记由各 spec 后续收口时落盘（或随总线 3.6 一并执行）。

| spec | 注记落点 | 注记内容 |
|------|---------|---------|
| cronet-global-enable-20260731 | spec.md REQ-01 处 | 「冻结待裁决（总线 2.11.2 裁决 R2）：本条目未实施且与 video-sniff 4.8c 已固化口径冲突，重新评审前禁止实施引用」 |
| cronet-global-enable-20260731 | spec.md REQ-03 处 | 「降级机制以 CronetInterceptor.kt 实测口径为权威（总线 2.11.2 裁决 R3），本条目"连续 5 次协议错误降级"仅为演进起点描述」 |
| cronet-global-enable-20260731 | spec.md 头注版本处 | 「Cronet 版本以 gradle.properties 实时值为权威，历史版本号为时点快照（裁决 R5）」 |
| network-perf-stability | spec.md P2-2 处 | 「已销项：熔断器已随 CronetInterceptor 实现（app-stability-round2→T4.3→N-P1-1→P1-2 演进链），评估前提消失（裁决 R3）」 |
| network-perf-stability | spec.md C3 处 | 「已归一：连接池实施值 50 → 现为 128（video-sniff R-P0-6 覆盖），以 128 为权威（裁决 R4）」 |
| network-perf-stability | spec.md F-P1-6 处 | 「版本口径演进：149 → 现为 500.0.1（gradle.properties 权威，裁决 R5）」 |
| thread-pool-audit | spec.md R1.3 / Scenario 3 处 | 「审查基线数字更新：ConnectionPool 50→128（video-sniff R-P0-6），重审时以 128 为输入（裁决 R4）；钳制定稿归总线 3.6（裁决 R6）」 |
| video-sniff-403-and-rss-classic-fix | 无需注记 | 本 spec 即基准，4.8c/Z7/F-07/R-P1-7/R-P0-3~6 全部维持原状 |

## 六、与总线其他任务的边界声明

- **总线 3.6（线程钳制定稿）**：本裁决仅做"开关/降级逻辑 + 连接池数值"归一；线程钳制参数终值（含 ImageCanvasViewModel min(n,128) 核验、thread-pool-split-config 衔接）仍归 3.6，两任务互不替代。
- **总线 8.4.2（灰度/观察开关登记）**：F3 熔断机制为自动行为无用户开关；isCronet 为既有用户开关，无需新登记。
- **video-sniff 后续阶段（4.8e/Phase 4 等）**：不触碰本裁决口径；若未来实施 REQ-01 解冻（isCronet 默认翻转），须先修订 4.8c 注释与 design F-07，保持"两逻辑独立性"表述不破。

## 七、证据文件清单

- 代码：`app/src/main/java/io/legado/app/help/config/AppConfig.kt`（:65, :2874-2884）、`help/http/HttpHelper.kt`（:102, :180-189, :240-244）、`help/exoplayer/ExoPlayerHelper.kt`（:1028-1032）、`lib/cronet/CronetInterceptor.kt`（:23-70）、`lib/cronet/CronetCoroutineInterceptor.kt`（:24）、`help/webView/WebViewPool.kt`（:61）、`service/CacheBookService.kt`（:46）、`gradle.properties`（:53-54）
- 文档：`docs/specs/video-sniff-403-and-rss-classic-fix/`（tasks 4.8c :67、spec R-P1-7/R-P0-3~6、design Z7/F-07）、`docs/specs/cronet-global-enable-20260731/spec.md`（REQ-01/03/06/07、Scenario 2/3）、`docs/specs/network-perf-stability/spec.md` + `tasks.md`（C3/17.x、P2-2/28.2、P2-3/28.3、F-P1-6/26.5）、`docs/specs/thread-pool-audit/spec.md`（R1.3/R1.5/R4、Scenario 3/5、审查清单）
