# spec：本地打包提速（local-build-speedup）

## Intent

将日常本地打包（debug 测试包）耗时从 7m33s 压缩至 ≤4 分钟，clean 全量从 10m39s 压缩至 ≤7 分钟；打包过程系统内存峰值从 93.5% 降至 ≤91%；打完包空闲 10 分钟后 daemon 自动退出、内存回落。零业务代码侵入，不改变 APK 产物行为。

## Scope

**In（本期）**
- `build-legado.bat`：移除打包前 Kotlin daemon 缓存删除与 `gradlew --stop`；移除构建命令 `--no-daemon`；debug/release 分场景堆参数注入；新增内存观测输出；新增 `daemon-stop` 参数保留手动清场入口；失败分支保留 STOP_DAEMON
- `gradle.properties`：开启 `org.gradle.configuration-cache=true`、`org.gradle.parallel=true`（`caching` 保持 false，P3 二期）
- `app/build.gradle`：`releaseTime()` 与 `gitCommits` 改用 Gradle ValueSource（配置期求值 → 执行期求值），保证 CC 下版本号正确
- `ai_tests/scripts/quick_build_install.py`：编译后立即清 daemon 的行为改为「仅在编译失败或显式参数时清场」，与 bat 行为对齐
- 内存观测：bat 打包前后各输出一行系统内存/ java 进程 RSS 摘要

**Out（明确排除）**
- P3 build cache（`org.gradle.caching=true`）：三包切换场景收益，留待二期实测评估
- kapt→KSP Glide 迁移（Glide 5 KSP Windows 跨盘 bug 待复验，独立任务）
- 模拟器/IDE 内存占用优化（非 java 22GB 大头，不属构建链路）
- release 正式包构建链路改动（R8 OOM 敏感，保持 4g 现状）
- `stop-daemons.bat`、文档中的构建规范更新随收尾同步

## Approach（精简）

1. **daemon 复用**：构建产物与 Kotlin 增量快照依赖 daemon 存活。现有内存保险已具备：`org.gradle.jvmargs=-Xmx4g`、`kotlin.daemon.jvmargs=-Xmx4g`、`org.gradle.daemon.idletimeout=600000`（10min 自退）。实测空闲 daemon RSS ~1.2~1.4GB/个，驻留代价可控
2. **debug 降堆**：命令行 `-Dorg.gradle.jvmargs="-Xmx3g ..."` 与 `-Dkotlin.daemon.jvmargs="-Xmx3g ..."` 注入（命令行优先级高于 gradle.properties）；release 分支不注入，沿用 properties 4g
3. **版本号 ValueSource**：`releaseTime()`、`gitCommits` 包装为 `Provider<String/Int>`，CC 缓存键含 ValueSource 输入，时间变化触发重配置，解决"版本号不更新"历史问题
4. **内存观测**：PowerShell 采样 `Win32_OperatingSystem` 可用内存 + java 进程 WorkingSet 求和，bat 内联一行命令，不建独立脚本文件
5. **与 AGENTS.md 规则 6 的衔接（红队 H1）**：规则 6 原语义"构建后必须清场防内存堆积"，P1 后改写为"daemon 复用 + `idletimeout=600000` 空闲 10min 自退（连带回收 Kotlin daemon）+ `daemon-stop` 手动清场入口"——防堆积目标不变，手段从强制清场改为自动回收；收尾阶段同步改写 AGENTS.md 规则 6 与 build-apk-guide.md §4.10

## Requirements

- **R1 提速**：日常增量打包（少量源码改动）耗时 ≤ 4 分钟；clean 全量 ≤ 7 分钟
- **R2 版本号正确性**：
  - R2.1 连续两次打包，`versionName` 时间戳单调递增（CC 开启下）
  - R2.2 `-PappVersion=3.26.082918` 显式覆盖生效
  - R2.3 `-PcustomAppId=io.legado.app` 共存包构建正常
  - R2.4 `versionCode = 10000 + gitCommits` 数值与 git 提交数一致
- **R3 内存**：打包过程系统内存峰值 ≤ 91%；daemon 复用后空闲驻留 java RSS ≤ 4GB（双 daemon 合计）
- **R4 release 不回归**：release 分支构建参数不含降堆注入（走 properties 4g）；本期不要求跑完整 release 打包，仅验证配置分支正确
- **R5 门禁不回归**：libcronet.so 打包校验门禁仍强制执行且通过
- **R6 自动回收**：打包完成后空闲 10 分钟，Gradle/Kotlin daemon 自动退出（`idletimeout=600000` 生效）
- **R7 清场入口**：`build-legado.bat daemon-stop` 可手动清场；构建失败分支自动清场保留；`clean` 参数行为不变
- **R8 测试链路对齐**：`quick_build_install.py` 默认不再每次清 daemon，编译失败或 `--stop-daemon` 参数时清场

## Scenarios

#### Scenario: 日常增量打包提速
- **WHEN** 上次构建产物存在，仅改动少量源码文件后执行 `build-legado.bat`
- **THEN** 复用存活 daemon 与 Kotlin 增量快照，耗时 ≤ 4 分钟，产物 APK 正确

#### Scenario: CC 开启下版本号更新
- **WHEN** configuration cache 命中（无配置变更），间隔 ≥1 分钟连续两次打包
- **THEN** 两次 APK 的 `versionName` 时间戳不同且后者更新；`-PappVersion` 覆盖时使用显式值

#### Scenario: 内存安全
- **WHEN** debug 打包执行中与打包完成后
- **THEN** 过程峰值 ≤ 91%；打完包 bat 不杀 daemon；空闲 10 分钟 daemon 自退、内存回落；`daemon-stop` 可随时强制清场

#### Scenario: 失败自动清场
- **WHEN** 构建失败（exit code ≠ 0）
- **THEN** 自动执行 STOP_DAEMON 清场（保留现有行为），提示可用 `clean`

#### Scenario: 共存包与发布链路
- **WHEN** `build-legado.bat release` 或 `build-legado.bat debug io.legado.app`
- **THEN** 构建参数与现状一致（release 不降堆），libcronet.so 校验通过，产物落对应 dist 子目录
