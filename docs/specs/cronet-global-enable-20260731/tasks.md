# Cronet 默认自动启用与扩展使用 - 任务清单

> 状态：🔄 设计中
> 创建日期：2026-07-31
> 关联文档：README.md / spec.md / design.md / [可行性研究报告](../../research/cronet-default-enable-feasibility-report.md)
> Spec ID：cronet-global-enable-20260731

## 任务执行说明

- 每个任务下预留 AOAdapt 日志位置（Action / Observation / Adapt）
- 任务完成需在 AOAdapt 区记录执行动作、观察结果、调整说明
- 任务状态标记：`- [ ]` 未完成 / `- [x]` 已完成
- 阶段完成后需进行构建复验，禁止跨阶段并行
- 涉及代码变更的任务必须使用测试包真机验证（包名：io.legado.miss.app.debug）
- ProGuard 验证必须使用正式包真机测试（包名：io.legado.miss.app.release）
- 输出安全：AOAdapt 只记录技术结论（错误码/异常类型/调用栈），禁止记录业务数据

## 1. 阶段一：基础设施搭建（P0）

- [ ] 1.1 读取研究报告和当前 Cronet 架构源码
  - 范围：CronetHelper / CronetInterceptor / ExoPlayerHelper / DohDns / HttpHelper / AppConfig
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.2 备份待修改文件到 .bak 目录
  - 范围：AppConfig.kt / HttpHelper.kt / proguard-rules.pro / build.gradle
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.3 isCronet 默认值改为 true（AppConfig.kt）
  - 说明：将 isCronet 默认值从 false 改为 true，保留开关用于紧急关闭
  - 注意：需检查所有读取 isCronet 的位置，确保默认值变更后行为一致
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.4 评估引入 CronetTransportForOkHttp 桥接层（添加 cronet-okhttp 依赖，P1 可选优化）
  - 依赖：`com.google.net.cronet:cronet-okhttp`
  - 评估点：与现有 CronetInterceptor 的集成度差异、兼容性、代码改动量（源码核实：CronetInterceptor 已通过 proceedWithCronet→cronetEngine.newUrlRequestBuilder 获得完整 Cronet 能力，桥接层为可选优化非必须迁移）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.5 完善降级链（Cronet→fallback→OkHttp）
  - 目标链：Cronet（动态下载 SO）→ cronet-fallback → OkHttp（项目实际用动态下载方案，非 play-services 也非 embedded）
  - 现状：已有连续 5 次协议错误降级 OkHttp 机制
  - 扩展：补充 JNI 崩溃（SIGABRT）自动降级
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.6 配置 ProGuard 规则（补充 cronet-okhttp keep 规则）
  - 规则：`-keep class org.chromium.** { *; }` + `-keep class com.google.net.cronet.** { *; }` + `-keepclassmembers class * { native <methods>; }`
  - 铁证：Cronet 149+ ProGuard 规则缺失导致 release 包订阅源列表加载失败
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 1.7 Cronet 引擎配置优化（连接迁移+DNS选项+QUIC hints）
  - 配置项：enableQuic(true) + enableHttp2(true) + enableBrotli(true) + ConnectionMigrationOptions + DnsOptions
  - 参考研究报告附录：CronetEngine.Builder 推荐配置
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 2. 阶段二：核心网络层接入（P1）

- [ ] 2.1 评估 CronetTransportForOkHttp 作为可选优化（P1，非必须迁移）
  - 评估点：是否用 callFactory=CronetTransport.newFactory(cronetEngine) 提升集成度（源码核实：CronetInterceptor 已通过 cronetEngine.newUrlRequestBuilder 获得完整 Cronet 能力，桥接层主要提升 OkHttp 调度/连接池与 Cronet 的集成度）
  - 优势：桥接层提升 OkHttp 调度与 Cronet 集成度（CronetInterceptor 已获得完整 Cronet 能力，桥接层非必须迁移）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.2 书源抓取请求走 Cronet（验证反爬+弱网收益）
  - 验证点：TLS 指纹接近 Chrome、QUIC 弱网延迟降低 50%、吞吐量提升 50%
  - 影响：所有走 okHttpClient 的请求（34 个文件使用）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.3 HttpURLConnection 替换为 OkHttp 桥接
  - 路径：HttpURLConnection → OkHttp（okhttp-urlconnection 适配）→ Cronet（CronetTransport）
  - 注意：CronetLoader.kt L335 的 SO 文件下载不能用 Cronet（避免循环依赖）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.4 编译测试包验证（io.legado.miss.app.debug）
  - 命令：使用 ai_tests/scripts/quick_build_install.py
  - 验证点：编译通过、安装成功、L1 验证通过
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.5 真机测试 QUIC 连接+TLS 指纹+弱网表现
  - 测试项：QUIC 连接（adb logcat -s Cronet*,Quic*）、TLS 指纹（对比抓取成功率）、弱网表现（模拟器限速）
  - 包名：io.legado.miss.app.debug（测试包，debug 构建，含调试日志+未混淆）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 2.6 编译正式包+mapping.txt 检查（io.legado.miss.app.release）
  - 验证点：ProGuard 规则完整性、mapping.txt 中 Cronet 类未被混淆、release 包功能正常
  - 包名：io.legado.miss.app.release（正式包，release 构建，含 ProGuard 混淆+正式签名）
  - 铁证：Cronet 149+ ProGuard 规则缺失导致 release 包订阅源列表加载失败
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 3. 阶段三：扩展场景接入（P2-P3）

- [ ] 3.1 Glide 图片加载接入 Cronet（P2）
  - 路径：Glide → OkHttp（callFactory=CronetTransport.newFactory(cronetEngine)）→ Cronet
  - 现状：通过 okHttpClientManga 间接接入，评估是否直接接入
  - 收益：图片加载获得 QUIC/Brotli/连接迁移能力
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 3.2 文件上传/下载接入 Cronet（P3）
  - 上传：Cronet 的 UploadDataProvider 流式上传，支持大文件分块
  - 下载：Cronet 的 UrlRequest.Callback.onReadCompleted() 流式读取
  - 优势：QUIC 连接迁移使移动网络下大文件下载更稳定（WiFi→4G 不中断）
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 3.3 验证扩展场景功能正常
  - 验证点：Glide 图片加载正常、文件上传/下载功能正常、无回归问题
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 4. 阶段四：监控与调优

- [ ] 4.1 性能监控（Cronet vs OkHttp 对比）
  - 监控项：连接成功率、延迟分布、TLS 握手耗时、QUIC 协议协商成功率
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 4.2 崩溃监控（JNI SIGABRT 告警+自动降级）
  - 监控项：JNI 崩溃（SIGABRT）频率、自动降级触发次数、降级后恢复情况
  - 机制：崩溃告警 + 自动回退 OkHttp
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 4.3 参数调优（idle timeout/max concurrent streams/连接迁移）
  - 调优项：idle_connection_timeout_seconds（平衡保活与电量）、max_concurrent_streams（根据设备性能）、enableDefaultNetworkMigration
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 4.4 灰度发布评估
  - 策略：按用户比例开启 Cronet，监控关键指标后全量
  - 指标：连接成功率、延迟分布、崩溃率、用户反馈
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 5. 文档同步

- [ ] 5.1 更新 updateLog.md
  - 要求：基于真实代码变更分析生成，禁止文字合并已有条目
  - 面向用户：通俗语言描述可感知变化，不暴露内部技术术语
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 5.2 更新 docs/INDEX.md
  - 要求：同步新增/变更文档的索引条目
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 5.3 更新项目记忆
  - 路径：.trae/memory/ai_memory_main.md
  - 要求：记录关键决策、文件路径、任务状态、设计文档路径
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

- [ ] 5.4 沉淀经验到子规范
  - 范围：Cronet 集成经验、ProGuard 规则、降级机制、性能调优参数
  - 目标：避免重复踩坑，为后续网络层优化提供参考
  - AOAdapt:
    - Action:
    - Observation:
    - Adapt:

## 阶段交付检查清单

每阶段完成后需逐项核对：

| 检查项 | 说明 |
|--------|------|
| 调试日志已清理 | Grep 确认无 android.util.Log.d/e 残留 |
| updateLog 已更新 | 基于真实代码变更分析生成 |
| 文档同步已检查 | INDEX/project_memory 是否最新 |
| 构建复验通过 | 每阶段结束重新构建验证 |
| 真机验证通过 | 测试包真机验证关键场景 |
| ProGuard 验证（涉及混淆时） | release 包真机测试 + mapping.txt 检查 |
| AOAdapt 日志已记录 | 每个任务记录执行动作、观察结果、调整说明 |

## 任务依赖关系

- 阶段一（基础设施搭建）为前置依赖，必须先完成
- 阶段二（核心网络层接入）依赖阶段一完成
- 阶段三（扩展场景接入）依赖阶段二完成（核心网络层稳定后再扩展）
- 阶段四（监控与调优）依赖阶段二、三完成（有数据才能监控调优）
- 阶段五（文档同步）为收尾，依赖前四阶段全部完成

## 风险提示

| 风险项 | 等级 | 阶段 | 缓解措施 |
|--------|------|------|---------|
| JNI 崩溃（SIGABRT） | 高 | 阶段一/二 | 降级机制 + 崩溃监控 + 自动回退 OkHttp |
| ProGuard 规则缺失 | 高 | 阶段一/二 | 完整 keep 规则 + release 包真机测试 |
| 循环依赖（SO 下载） | 中 | 阶段二 | CronetLoader.kt 的 SO 下载保留 HttpURLConnection |
| APK 体积增加 | 低 | 阶段一 | 项目采用动态下载 SO 方案，APK 零增量（SO 运行时下载到 externalCache） |
| 电池消耗（QUIC 保活） | 低 | 阶段四 | 配置 idle timeout + 监控 |
