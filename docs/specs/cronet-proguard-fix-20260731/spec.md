# Spec: Cronet ProGuard 规则修复

## Intent

修复 release 包打开视频订阅源时 SIGABRT 崩溃（9 次连续崩溃，全部同模式），并恢复由此导致的视频嗅探能力减弱。

**用户原话**：
> "使用最新的包，打开视频订阅源，还是闪退，日志在：docs\issues\user\temp\20260731\001\Downloadslogs(1).(5)..zip 并且现在整体嗅探能力，以及好多地方都闪退！"

## Scope

### 做什么
- 补全 ProGuard 规则，保留 libcronet.so 通过 JNI 反射调用的所有 Java 类
- 验证 release 包 Cronet native 引擎正常初始化（class=CronetUrlRequestContext）
- 验证视频嗅探能力恢复（Cronet DataSource 优先，BoringSSL TLS 栈）
- 强化 package-naming.md 的 ProGuard 规则验证清单

### 不做什么
- 不修改 CronetHelper.kt 的动态下载逻辑（已验证 so 下载成功）
- 不修改 CronetLoader.kt 的 manualLoad 逻辑（已验证 System.load 触发 JNI 正常）
- 不修改 ExoPlayerHelper.kt 的嗅探逻辑（嗅探减弱是 Cronet 降级的连锁反应，非嗅探逻辑本身问题）
- 不回退动态下载方案（APK 体积优化保留）

## Approach

### Selected Approach

**精准补全 ProGuard 规则**：在 `proguard-rules.pro` 中追加保留 `org.chromium.net.*` 核心 API 类的规则。

**理由**：
- 根因明确：R8 移除了 libcronet.so 通过 JNI 反射调用的 Java 类（`org.chromium.net.Cronet` 等）
- 修复精准：只追加缺失的 keep 规则，不影响现有混淆优化
- 风险最低：不改动已验证的动态下载/加载逻辑，只补全混淆规则
- 体积可控：保留的类数量有限，APK 体积增加可忽略

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 保留整个 `org.chromium.**` 包（`-keep class org.chromium.** { *; }`） | 过度保留：会保留大量非 JNI 调用的类，APK 体积增加不可控；不符合精准修复原则 |
| 回退到 jniLibs 打包 so（放弃动态下载） | 治标不治本：so 打包方式与 R8 移除 Java 类是两个独立问题；APK 体积增加 6.37MB；用户已明确要求动态下载方案 |
| 放弃 Cronet，改用 OkHttp + Conscrypt | 不可行：CDN TLS 指纹检测会拒绝 OkHttp 的 Conscrypt TLS 栈，m3u8 视频无法播放（2026-07-30 已验证） |
| 升级 Cronet 版本 | 风险高：版本升级可能引入新依赖和兼容性问题，且当前根因是 ProGuard 规则缺失非 Cronet 本身 bug |

### Drawbacks

1. **APK 体积微增**：保留的 Java 类不会被 R8 混淆/移除，APK 体积可能增加几十 KB（可接受）
2. **依赖人工维护**：若后续 Cronet 版本升级引入新的 JNI 调用类，需手动补充 keep 规则（通过验证清单缓解）
3. **不能 100% 覆盖**：libcronet.so 是闭源二进制，无法穷举所有 JNI 调用的类，只能基于崩溃日志和官方文档补全（通过真机验证缓解）

### Prior Art

- Chromium 官方 ProGuard 规则：`app/cronet-proguard-rules.pro`（已包含部分 keep 规则，但未覆盖 `org.chromium.net.Cronet` 入口类）
- 2026-07-30 修复：已补全 NativeCronetProvider/JavaCronetProvider/HttpEngineNativeProvider/CronetProviderInstaller/NativeCronetEngineBuilderImpl/AndroidProxy/AndroidProxyOptions（但遗漏了 API 入口类）

## Requirements

### R1: 崩溃修复
- release 包打开视频订阅源不再 SIGABRT 崩溃
- libcronet.so JNI_OnLoad 正常完成（FindClass 不返回 null）
- Cronet 引擎初始化成功（class=CronetUrlRequestContext，非 JavaCronetEngine）

### R2: 嗅探恢复
- 视频嗅探 Range 请求使用 Cronet DataSource（BoringSSL TLS 栈）
- CDN 不再因 TLS 指纹检测拒绝嗅探请求
- 嗅探成功率恢复到 2026-07-30 验证水平

### R3: 回归防护
- package-naming.md 新增 ProGuard 规则验证清单
- 验证清单包含：release 包构建后确认 keep 规则生效（mapping.txt 检查关键类未被移除）
- 记忆持久化：将"Cronet API 入口类必须 keep"写入 Hard Constraints

### R4: 不引入新问题
- 测试包/共存包功能不受影响（minifyEnabled=false，R8 不启用）
- 动态下载逻辑不受影响（so 文件下载/加载流程不变）
- APK 体积增加 ≤ 100KB

## Scenarios

### Scenario 1: 用户打开视频订阅源（崩溃场景）
- 前置：release 包已安装，首次打开
- 操作：点击视频订阅源进入
- 预期：不崩溃，正常显示订阅源列表
- 修复前：SIGABRT 崩溃（9 次连续）

### Scenario 2: 用户播放视频（嗅探场景）
- 前置：已进入订阅源视频播放页
- 操作：点击视频播放
- 预期：Cronet DataSource 优先，嗅探成功，ExoPlayer 播放
- 修复前：Cronet 崩溃后降级 OkHttp，TLS 指纹被拒绝，嗅探失败

### Scenario 3: 测试包回归验证
- 前置：测试包构建
- 操作：打开视频订阅源 + 播放视频
- 预期：功能正常（测试包不受 ProGuard 影响）

### Scenario 4: release 包覆盖安装
- 前置：旧版 release 包已安装
- 操作：覆盖安装新版 release 包
- 预期：不崩溃，Cronet 正常初始化
