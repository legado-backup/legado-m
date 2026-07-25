# 包名规范（package-naming）

> 本项目在原版legado-E基础上扩展了包名机制，支持自定义包名实现与原版共存。
> 应用名称：**阅读M**

## 三类包定义

| 包类型 | 基础包名 | 后缀 | 最终包名 | 桌面显示名 | 用途 |
|--------|---------|------|---------|----------|------|
| **测试包** | `io.legado.miss.app` | `.debug` | `io.legado.miss.app.debug` | **阅读M.D** | 开发调试、快速验证（默认） |
| **共存包** | `io.legado.app` | `.debug` | `io.legado.app.debug` | **阅读M·共存** | 与原版legado-E共存 |
| **正式包** | `io.legado.miss.app` | `.release` | `io.legado.miss.app.release` | **阅读M** | 正式发布、生产环境 |

> **显示名规则**：通过 `manifestPlaceholders` 在 `app/build.gradle` 中按构建类型动态设置。共存包传入 `-PcustomAppId` 时自动切换为 `阅读M·共存`。

## 配置差异

| 配置项 | 测试包 | 共存包 | 正式包 |
|--------|--------|--------|--------|
| 桌面显示名 | 阅读M.D | 阅读M·共存 | 阅读M |
| `manifestPlaceholders.app_name` | `@string/app_name` | `@string/app_name` | `@string/app_name`（默认）/ `@string/app_name_a`（releaseA）/ `@string/app_name_s`（releaseS） |
| `minifyEnabled` | `false` | 由构建类型决定 | `true` |
| `shrinkResources` | `false` | 由构建类型决定 | `true` |
| `applicationIdSuffix` | `.debug` | `.debug` | `.release` |
| `versionNameSuffix` | `debug` | `debug` | 无 |
| 构建速度 | 快 | 中 | 慢 |
| APK体积 | 大 | 中 | 小 |

> **app_name 字段说明**：buildTypes 按 `applicationIdSuffix` 选择不同 strings.xml 字段（详见 [build-apk-guide.md](../project-flow/build-apk-guide.md) 第二章"桌面显示名配置"）。`@string/app_name`/`@string/app_name_a`/`@string/app_name_s` 在 4 个 strings.xml 中同步配置（values/values-zh/values-zh-rTW/values-zh-rHK），中文系统下取 values-zh 的值，必须 4 个文件同步修改。

## 日常开发打包策略

> **核心原则：日常开发主要打共存包，收到用户反馈后再打全量包。**

| 场景 | 打包类型 | 命令 | 说明 |
|------|---------|------|------|
| **AI开发完善功能后** | 共存包 | `build-legado.bat debug io.legado.app` | 不影响已安装的原版，快速验证 |
| **日常调试迭代** | 共存包 | `build-legado.bat debug io.legado.app` | 与原版数据共存，无需迁移 |
| **收到用户反馈需发布** | 测试包 + 正式包 | `build-legado.bat` → `build-legado.bat release` | 打全量包交付用户 |
| **紧急修复快速验证** | 测试包 | `build-legado.bat` | 最快速度验证修复效果 |

**为什么日常打共存包？**
- 共存包使用原版包名`io.legado.app`，与原版legado-E共存，不影响日常使用
- AI开发完成后需要真机验证，共存包可以边用原版边测新功能
- 全量包（测试包/正式包）包名为`io.legado.miss.app`，需卸载原版才能安装，只在做用户交付时打

## 真机测试包选择规范（强制）

> **来源**：2026-07-26 用户决策 + [AGENTS.md "🔴🔴 强制规则：真机测试包选择规范"](../../AGENTS.md)
> **强制等级**：🔴🔴（违反=失败）

真机测试时必须按任务类型选择对应的 APK 包，禁止混用。违反将导致测试结果失真或污染正式环境。

### 包选择规则

| 任务类型 | 必须使用的包 | 包名 | 选择理由 |
|---------|------------|------|---------|
| **项目代码优化/开发** | 测试包 | `io.legado.miss.app.debug` | debug 构建保留完整调试信息、未启用 ProGuard 混淆、日志输出完整，便于定位代码变更引入的问题 |
| **书源/订阅源创建优化（Skill 真机测试）** | 内置正式包 | `io.legado.miss.app.release` | release 构建模拟生产环境真实行为（含 ProGuard 混淆+正式签名+Cronet provider 保留验证），确保源在生产环境可用；同时验证 release 包是否因混淆规则缺失导致功能异常 |
| **共存包测试** | 共存包 | `io.legado.app.debug` | 仅在需要与原版 legado 共存场景下使用（如多 AI 并发测试隔离） |

### 禁止行为

- ❌ 代码优化任务用正式包测试（无法定位问题，且正式包签名固定无法频繁替换）
- ❌ Skill 真机测试用测试包测试（无法验证生产环境真实行为，可能漏掉 ProGuard 混淆问题）
- ❌ 在同一模拟器实例上同时操作多个包（会导致 Activity 抢占，测试结果不可靠，铁证：2026-07-25 三包并发抢占模拟器）

### 与"日常开发打包策略"的关系

"日常开发打包策略"章节描述的是**构建阶段**的打包选择（AI 开发完善功能后打共存包快速验证）；
本章节描述的是**真机测试阶段**的包选择强制规范。两者不冲突：
- 日常开发构建：可继续用共存包快速验证（不涉及代码优化的功能验证）
- 真机测试代码优化：必须用测试包（涉及代码变更的回归验证）
- 真机测试 Skill 源：必须用正式包（验证生产环境可用性）

### 包名速查

| 包类型 | 包名 | 应用名 | UID（模拟器） |
|--------|------|--------|-------------|
| 测试包 | `io.legado.miss.app.debug` | 阅读M | u0_a64 |
| 正式包 | `io.legado.miss.app.release` | 阅读M | u0_a65 |
| 共存包 | `io.legado.app.debug` | 阅读M | 与原版共存 |

## 使用方法

| 操作 | 命令 | 最终包名 |
|------|------|---------|
| 构建共存包（日常开发推荐） | `build-legado.bat debug io.legado.app` | `io.legado.app.debug` |
| 构建测试包 | `build-legado.bat` | `io.legado.miss.app.debug` |
| 构建正式包 | `build-legado.bat release` | `io.legado.miss.app.release` |

## 正式包签名流程

> **铁律**：正式签名证书和密码绝不提交 git，已在 `.gitignore` 排除（`*.jks`、`*.keystore`、`local.properties`）。
> **不变签名铁律**：发布后不能更换签名，否则用户无法覆盖升级。证书丢失只能重新生成，但已安装用户无法升级到新签名版本，务必妥善备份证书。

### 1. 生成签名证书（仅首次）

```bash
keytool -genkeypair -v \
  -keystore legado_release.jks \
  -alias legado \
  -keyalg RSA -keysize 2048 \
  -validity 36500 \
  -storepass <你的密码> \
  -keypass <你的密码> \
  -dname "CN=Legado, OU=Dev, O=Miss, L=CN, ST=CN, C=CN"
```

- 有效期 100 年（36500 天）
- RSA 2048 位密钥
- 别名：`legado`
- keystore 文件：`legado_release.jks`（项目根目录，不入 git）

### 2. 配置 local.properties（不入 git）

在项目根目录的 `local.properties` 中添加：

```properties
RELEASE_STORE_FILE=legado_release.jks
RELEASE_STORE_PASSWORD=<你的密码>
RELEASE_KEY_ALIAS=legado
RELEASE_KEY_PASSWORD=<你的密码>
```

> **读取顺序**（见 `app/build.gradle`）：命令行 `-P` 参数 → `gradle.properties` → `local.properties`。`local.properties` 用于本地开发，`gradle.properties` 用于 CI/CD（也不入 git）。

### 3. 构建正式包

```bash
./gradlew assembleAppRelease -x lint
```

构建时 `app/build.gradle` 会自动读取 `local.properties` 中的签名配置，应用到 release 包。`debug` 和 `release` 构建类型共用同一 `signingConfigs.myConfig`，确保三个包签名一致。

### 4. 验证签名

```bash
apksigner verify --print-certs app/build/outputs/apk/app/release/<apk文件名>
```

正式签名应显示：
- `Signer #1 certificate DN: CN=Legado, OU=Dev, O=Miss, L=CN, ST=CN, C=CN`
- 不再显示 `CN=Android Debug`（debug 签名特征）

### 5. 签名一致性原则

| 原则 | 说明 |
|------|------|
| **三包统一签名** | debug/release/coexist 包均使用同一正式签名证书（`build.gradle` 中 debug/release 共用 `myConfig`） |
| **不变签名铁律** | 发布后不能更换签名，否则用户无法覆盖升级 |
| **证书丢失不可恢复** | 证书丢失只能重新生成，但已安装用户无法升级到新签名版本，务必妥善备份证书 |

## APK输出位置

构建成功后APK会自动拷贝到`output/apk/`下对应子目录，文件名通过包名标识区分：

| 包类型 | Gradle输出目录 | 最终拷贝位置 |
|--------|--------------|------------|
| 测试包 | `app/build/outputs/apk/app/debug/` | `output/apk/test/legado_miss_app_<version>.apk` |
| 正式包 | `app/build/outputs/apk/app/release/` | `output/apk/release/legado_miss_app_<version>.apk` |
| 共存包 | `app/build/outputs/apk/app/debug/` | `output/apk/coexist/legado_legacy_app_<version>.apk` |

> **注意**：测试包和共存包在Gradle中都输出到`debug/`目录，后构建的会覆盖先构建的。bat脚本会在构建完成后立即拷贝到`output/apk/{test|coexist|release}/`，通过子目录隔离，不会覆盖。

## APK文件名规则

APK文件名包含包名标识，用于区分不同包类型：

| 包类型 | 文件名格式 | 示例 |
|--------|----------|------|
| 测试包 | `legado_miss_app_<version>.apk` | `legado_miss_app_3.26.071900.apk` |
| 正式包 | `legado_miss_app_<version>.apk` | `legado_miss_app_3.26.071900.apk` |
| 共存包 | `legado_legacy_app_<version>.apk` | `legado_legacy_app_3.26.071900.apk` |

> **注意**：测试包和正式包的APK文件名相同（因为`outputFileName`使用`defaultConfig.versionName`，不含`versionNameSuffix`），但位于不同目录（`output/default/debug/` vs `output/default/release/`），不会互相覆盖。如需在同一目录区分，可将`outputFileName`中的`defaultConfig.versionName`改为`variant.versionName`。

包名标识规则（在`app/build.gradle`中配置）：
- `io.legado.miss.app` → `miss`
- `io.legado.app` → `legacy`
- 其他自定义包名 → 取最后一段（如`com.my.legado` → `legado`）

## 与原版差异

- **原版legado-E**：单一固定包名`io.legado.app`，不支持共存
- **本项目（阅读M）**：基础包名`io.legado.miss.app`，支持`-PcustomAppId`参数实现自定义包名；共存包使用原版包名`io.legado.app`，可与原版共存

## 注意事项

- **包名变更后无法覆盖安装**：从`io.legado.app`改为`io.legado.miss.app`后，新包无法覆盖旧包安装（包名不同=不同应用），需先卸载旧包
- **namespace不变**：Kotlin源码包路径仍是`io.legado.app`，只有applicationId变了，不影响源码
- **Firebase需重新配置**：新包名需在Firebase Console中重新注册，或移除google-services插件
