# Legado（开源阅读）APK 打包指南

> 从零开始，在 Windows 11 上构建 Legado APK 的完整指南，包含环境搭建、签名配置、打包命令、包名修改等。

---

## 一、环境准备

### 1.1 必需软件

| 软件 | 版本要求 | 下载地址 | 说明 |
|------|---------|---------|------|
| **JDK** | 17（必须） | https://adoptium.net/temurin/releases/?version=17 | 项目 `build.gradle` 指定 `JavaLanguageVersion.of(17)` |
| **Android SDK** | compileSdk 36 | 通过 Android Studio 或 cmdline-tools 安装 | 需安装 Android 15 (API 36) 平台 |
| **Git** | 任意 | https://git-scm.com/ | 版本号计算依赖 `git rev-list` |

### 1.2 安装 Android SDK（两种方式任选）

#### 方式 A：安装 Android Studio（推荐，改源码必选）

> **如果需要修改 Kotlin 源码，必须选此方式！** Android Studio 提供 Kotlin 智能提示、代码跳转、重构、调试等能力，cmdline-tools 无法替代。

1. 下载 Android Studio：https://developer.android.com/studio
2. 安装时勾选 Android SDK、Android Virtual Device
3. 安装完成后，打开 SDK Manager → SDK Platforms 标签，勾选 **Android 15.0 (API 36)**
4. 切换到 SDK Tools 标签，勾选安装：
   - Android SDK Build-Tools（最新版）
   - Android SDK Command-line Tools
   - Android SDK Platform-Tools
5. 打开项目：File → Open → 选择 Legado 项目根目录
6. 等待 Gradle Sync 完成（首次需下载依赖，可能数分钟）
7. Sync 完成后即可编辑代码 + 一键运行

> Android Studio 会自动创建 `local.properties` 并配置 SDK 路径，无需手动操作。

#### 方式 B：仅安装 cmdline-tools（仅适合打包，不适合改代码）

> 仅适合「不改代码只打包」的场景。如果要修改 Kotlin 源码，此方式无法提供代码补全、语法检查、跳转定义等开发能力，效率极低。

**两种方式核心能力对比：**

| 能力 | cmdline-tools | Android Studio |
|------|--------------|----------------|
| 编译打包 APK | 可以 | 可以 |
| 修改 Kotlin 代码 | 能改（记事本级别） | **能改（智能提示+跳转+重构）** |
| 代码补全/自动导入 | 无 | 有 |
| 跳转到定义/查找引用 | 无 | 有 |
| 语法错误实时提示 | 无 | 有 |
| 代码重构（重命名等） | 无 | 有 |
| 调试断点 | 无 | 有 |
| Layout XML 预览 | 无 | 有 |
| 下载大小 | ~150MB | ~1GB+ |
| 磁盘总占用 | ~300MB | ~3GB+ |
| 适合场景 | 纯打包、CI/CD、服务器 | **改源码、日常开发、调试** |

**第 1 步：下载**

访问官方页面：https://developer.android.com/studio#command-line-tools-only

滚动到底部 **"Command line tools only"** 区域，下载 **Windows** 版 ZIP（约 150MB）。

**第 2 步：解压到正确目录结构**

> 此步最容易踩坑——目录结构必须是三级嵌套，否则 sdkmanager 会报错。

```
C:\Android\Sdk\
  └── cmdline-tools\
       └── latest\
            ├── bin\
            │    ├── sdkmanager.bat
            │    └── avdmanager.bat
            ├── lib\
            └── ...
```

```powershell
# 创建 SDK 根目录
mkdir C:\Android\Sdk

# 创建三级嵌套目录
mkdir C:\Android\Sdk\cmdline-tools\latest

# 解压下载的 ZIP 后，把解压出 cmdline-tools 文件夹里的所有内容
# （bin、lib 等子目录）复制到 C:\Android\Sdk\cmdline-tools\latest\ 中
#
# ❌ 错误：内容放在 cmdline-tools\ 而不是 cmdline-tools\latest\
# ✅ 正确：内容放在 cmdline-tools\latest\
#
# 可以用 PowerShell 自动完成：
# Expand-Archive -Path "$env:USERPROFILE\Downloads\commandlinetools-win-*.zip" -DestinationPath C:\Android\Sdk\cmdline-tools\latest -Force
```

**第 3 步：设置环境变量**

```powershell
# 在 PowerShell 中执行（需要重启终端后生效）

# 设置 ANDROID_HOME
[System.Environment]::SetEnvironmentVariable("ANDROID_HOME", "C:\Android\Sdk", "User")

# 设置 ANDROID_SDK_ROOT
[System.Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", "C:\Android\Sdk", "User")

# 追加 PATH（不覆盖已有 PATH）
$oldPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
$newPath = "$oldPath;C:\Android\Sdk\cmdline-tools\latest\bin;C:\Android\Sdk\platform-tools"
[System.Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
```

> **重要**：设置完成后必须关闭当前终端，重新打开才能生效。

**第 4 步：接受许可证 + 安装构建所需组件**

```powershell
# 接受所有许可证（一路 y 下去）
sdkmanager --licenses

# 安装 Legado 构建所需的三个核心组件
sdkmanager "platforms;android-36" "build-tools;36.0.0" "platform-tools"
```

三个组件的作用与大小：

| 组件 | 大小 | 作用 |
|------|------|------|
| `platforms;android-36` | ~70MB | Android 15 API 框架，compileSdk 36 必需 |
| `build-tools;36.0.0` | ~60MB | APK 打包工具（aapt2、d8、apksigner 等） |
| `platform-tools` | ~40MB | adb 等设备通信工具 |

**常用 sdkmanager 命令速查：**

```powershell
# 查看已安装组件
sdkmanager --list_installed

# 查看所有可用组件
sdkmanager --list

# 安装额外组件（按需）
sdkmanager "ndk;27.0.12077973"     # 如需 NDK
sdkmanager "cmake;3.22.1"          # 如需 CMake

# 更新所有已安装组件
sdkmanager --update

# 卸载组件
sdkmanager --uninstall "build-tools;35.0.0"
```

**国内镜像加速（可选）：**

如果直连 Google 下载慢，可以配置国内镜像。编辑 `C:\Android\Sdk\cmdline-tools\latest\bin\sdkmanager.bat` 同目录或通过代理设置：

```powershell
# 方式 1：使用 HTTP 代理
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
sdkmanager "platforms;android-36" "build-tools;36.0.0" "platform-tools"

# 方式 2：使用腾讯镜像（无需代理）
sdkmanager --no_https --proxy=http --proxy_host=mirrors.cloud.tencent.com --proxy_port=80 "platforms;android-36"
```

> Gradle 构建时的依赖下载也可以配置镜像，见 `settings.gradle` 中已注释的镜像仓库行。

### 1.3 配置项目 SDK 路径

在项目根目录创建 `local.properties`（此文件已在 `.gitignore` 中，不会被提交）：

```properties
sdk.dir=C:\\Android\\Sdk
# 或 Android Studio 默认路径：
# sdk.dir=C:\\Users\\<你的用户名>\\AppData\\Local\\Android\\Sdk
```

### 1.4 验证环境

```powershell
java -version          # 应显示 openjdk version "17" 或 17.x.x
gradlew --version     # 应显示 Gradle 8.x
```

---

## 二、项目构建配置概览

| 配置项 | 值 | 来源文件 |
|--------|-----|---------|
| compileSdk | 36 | `build.gradle` (root) |
| minSdk | 21 | `app/build.gradle` |
| targetSdk | 36 | `app/build.gradle` |
| applicationId | `io.legado.app` | `app/build.gradle` |
| namespace | `io.legado.app` | `app/build.gradle` |
| JDK | 17 | `app/build.gradle` (jvmToolchain) |
| Kotlin | 2.3.10 | `gradle/libs.versions.toml` |
| AGP | 8.13.2 | `gradle/libs.versions.toml` |
| OkHttp | 5.3.2 | `gradle/libs.versions.toml` |
| 版本名格式 | `3.yy.MMddHH` | `app/build.gradle` (releaseTime) |
| 版本号 | `10000 + gitCommitCount` | `app/build.gradle` |

### 构建变体说明

| 变体 | applicationId | 后缀 | 用途 |
|------|--------------|------|------|
| **appDebug** | `io.legado.app.debug` | `.debug` | 开发调试，不混淆 |
| **appRelease** | `io.legado.app.release` | `.release` | 正式发布，混淆+收缩 |
| **googleRelease** | `io.legado.play` | — | Google Play 发布 |

> **注意**：debug 和 release 的 applicationId 不同（后缀不同），可以在同一设备上同时安装。

---

## 三、签名配置（Release 构建）

### 3.1 生成签名密钥

```powershell
keytool -genkey -v -keystore legado.jks -keyalg RSA -keysize 2048 -validity 10000 -alias legado
```

按提示输入密码、姓名、组织等信息。生成的 `legado.jks` 文件请妥善保管。

### 3.2 配置签名信息

在 `gradle.properties` 文件末尾追加（此文件含敏感信息，确保不提交到公开仓库）：

```properties
RELEASE_STORE_FILE=./legado.jks
RELEASE_STORE_PASSWORD=你的密钥库密码
RELEASE_KEY_ALIAS=legado
RELEASE_KEY_PASSWORD=你的密钥密码
```

将 `legado.jks` 文件复制到 `app/` 目录下。

> **项目内置签名文件**：`.github/workflows/legado.jks` 是 CI/CD 使用的签名文件（base64 编码在 GitHub Secrets 中），本地构建需自行生成。

### 3.3 签名配置原理

`app/build.gradle` 中的签名逻辑：

```groovy
signingConfigs {
    if (project.hasProperty("RELEASE_STORE_FILE")) {
        myConfig {
            storeFile file(RELEASE_STORE_FILE)
            storePassword RELEASE_STORE_PASSWORD
            keyAlias RELEASE_KEY_ALIAS
            keyPassword RELEASE_KEY_PASSWORD
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
            enableV4Signing = true
        }
    }
}
```

如果 `gradle.properties` 中没有 `RELEASE_STORE_FILE` 属性，Release 构建将不签名（生成未签名 APK）。

---

## 四、构建 APK

### 4.1 Debug 构建（最简单）

```powershell
# 进入项目根目录
cd f:\myself\github\WeAgentChat\temp\legado

# 构建 Debug APK
.\gradlew assembleAppDebug

# 输出位置
# app\build\outputs\apk\app\debug\legado_app_3.版本号debug.apk
```

Debug 构建无需签名配置，使用默认 debug 签名。

### 4.2 Release 构建（正式发布）

```powershell
# 前提：已完成签名配置（第三章）
.\gradlew assembleAppRelease

# 输出位置
# app\build\outputs\apk\app\release\legado_app_3.版本号.apk
```

### 4.3 构建所有变体

```powershell
.\gradlew assembleDebug assembleRelease
```

### 4.4 输出 APK 命名规则

APK 文件名格式：`legado_app_<flavor>_<version>.apk`

- flavor = `app`（目前仅此一个 product flavor）
- version = `3.yy.MMddHH`（如 `3.26.062819`）

### 4.5 常见构建问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `SDK location not found` | 缺少 `local.properties` | 创建文件并设置 `sdk.dir` |
| `Could not resolve io.legado.app:book` | 子模块未同步 | 先执行 `.\gradlew clean` |
| Cronet 下载失败 | 网络问题 | 配置代理或手动下载 Cronet JAR |
| `Execution failed for ':app:kspDebugKotlin'` | Room schema 冲突 | `.\gradlew clean` 后重新构建 |
| 编译 OOM | JVM 内存不足 | 在 `gradle.properties` 中调大 `-Xmx` |

---

## 五、Cronet 网络库

Legado 使用 Chromium Cronet 作为网络加速库。Cronet 相关文件位于 `app/cronetlib/`。

### 5.1 已有文件

- `app/cronetlib/cronet_api.jar`
- `app/cronetlib/cronet_shared_java.jar`
- `app/src/main/assets/cronet.json`（SO 文件 MD5 映射）

### 5.2 更新 Cronet 版本

```powershell
# 1. 修改 gradle.properties 中的 CronetVersion
# CronetVersion=128.0.6613.40

# 2. 执行下载任务
.\gradlew app:downloadCronet
```

此任务会下载对应版本的 JAR 和各架构 SO 文件，并更新 `cronet.json`。

---

## 六、Vue3 Web 模块构建（可选）

Legado 内嵌 Vue3 前端（`modules/web/`），用于 Web 书源编辑功能。

```powershell
# 进入 web 模块目录
cd modules\web

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建（含类型检查 + 同步到 assets）
npm run build
```

> **注意**：`npm run build` 会执行 `sync.js`，该脚本仅在 GitHub Actions 中自动执行。本地构建需手动确认 `dist/` 内容已复制到 `app/src/main/assets/web/`。

---

## 七、修改包名（applicationId）

### 7.1 什么是包名？

包名（applicationId）是 Android 系统中唯一标识应用的字符串，决定了应用在设备上的身份。修改包名后，新包名和原包名被视为两个不同的应用，可以同时安装。

### 7.2 当前包名结构

| 构建类型 | applicationId | 说明 |
|---------|--------------|------|
| Debug | `io.legado.app.debug` | 默认 debug 后缀 |
| Release | `io.legado.app.release` | 默认 release 后缀 |
| Google Play | `io.legado.play` | 特殊 product flavor |

### 7.3 修改方法

#### 方法一：修改 applicationId（最简单，推荐）

只需修改 `app/build.gradle` 中的 `applicationId`：

```groovy
// app/build.gradle 第 50 行
defaultConfig {
    applicationId "com.yourname.legado"  // 改为你的包名
    // ...
}
```

同时修改 release 的 `applicationIdSuffix`，确保不同构建类型包名不同：

```groovy
buildTypes {
    release {
        applicationIdSuffix '.release'  // 最终包名: com.yourname.legado.release
    }
    debug {
        applicationIdSuffix '.debug'    // 最终包名: com.yourname.legado.debug
    }
}
```

> **注意**：此方法只改 applicationId，不改 Kotlin 源码包结构（namespace）。applicationId 和 namespace 是独立的——applicationId 决定应用在设备上的标识，namespace 决定 R 类和 BuildConfig 的包路径。两者可以不同。

#### 方法二：彻底改包名（包含源码包路径）

如果要完全改变应用身份（包括源码包路径），需要更多修改：

**步骤 1：修改 namespace**

```groovy
// app/build.gradle 第 28 行
android {
    namespace = 'com.yourname.legado'  // 改为你的包名
}
```

**步骤 2：移动源码目录**

```powershell
# 将 Java/Kotlin 源码从 io/legado/app 移到 新包路径
# app/src/main/java/io/legado/app/ → app/src/main/java/com/yourname/legado/
# app/src/debug/java/io/legado/app/ → app/src/debug/java/com/yourname/legado/
```

**步骤 3：批量替换包名引用**

在所有 `.kt` 文件中：
- `package io.legado.app` → `package com.yourname.legado`
- `import io.legado.app` → `import com.yourname.legado`

在 `AndroidManifest.xml` 中：
- `android:name=".App"` 中的相对引用无需修改（相对路径自动跟随 namespace）
- 绝对引用如 `io.legado.app.xxx` 需手动替换

**步骤 4：更新 Firebase 配置**

修改 `app/google-services.json`，将所有 `package_name` 改为新包名：

```json
{
  "client_info": {
    "android_client_info": {
      "package_name": "com.yourname.legado.debug"
    }
  }
}
```

> 如果不需要 Firebase（崩溃统计、性能统计），可以移除 `google-services.json` 和 `app/build.gradle` 中的 `alias libs.plugins.google.services` 插件。

**步骤 5：更新 ProGuard 规则**

检查 `app/proguard-rules.pro` 中是否有硬编码的 `io.legado.app` 包名引用（如 `-keep class io.legado.app.**`），需要同步修改。

**步骤 6：同步修改子模块**

子模块 `modules/book/` 和 `modules/rhino/` 也有自己的 `build.gradle`，如果 `namespace` 引用了 `io.legado`，需同步修改。

### 7.4 修改包名后的注意事项

| 注意事项 | 说明 |
|---------|------|
| **数据迁移** | 包名变更后，新应用无法读取旧应用的数据，需手动备份恢复 |
| **WebDAV 同步** | Legado 支持 WebDAV 备份恢复，可用于数据迁移 |
| **书源兼容** | 书源 JSON 不依赖包名，可直接导入 |
| **签名一致性** | 使用同一签名密钥可实现覆盖安装（如果只改 applicationIdSuffix） |
| **Firebase** | 新包名需在 Firebase Console 中重新注册应用 |
| **已有用户** | 如果是公开发布，新包名无法覆盖旧包名的已安装应用 |

---

## 八、GitHub Actions 自动构建

项目已配置 CI/CD（`.github/workflows/release.yml`），支持自动构建和发布。

### 8.1 触发方式

手动触发（workflow_dispatch）：在 GitHub 仓库 Actions 页面点击 "Run workflow"。

### 8.2 前置配置

需在仓库 Settings → Secrets 中设置：

| Secret | 说明 |
|--------|------|
| `RELEASE_KEY_STORE` | JKS 签名文件的 base64 编码：`base64 -i legado.jks` |
| `RELEASE_KEY_ALIAS` | 密钥别名 |
| `RELEASE_KEY_PASSWORD` | 密钥密码 |
| `RELEASE_STORE_PASSWORD` | 密钥库密码 |
| `ACTIONS_TOKEN` | 用于推送 APK 到 release 分支的 GitHub Token |

### 8.3 产出物

- `legado_app_<version>.apk`：标准 Release 版
- `legado_google_<version>.apk`：Google Play 版（如配置了 SERVICE_ACCOUNT_JSON）

---

## 九、快速开始（5 分钟上手）

```powershell
# 1. 确认 JDK 17
java -version

# 2. 设置 SDK 路径
echo "sdk.dir=C:\\Users\\<你>\\AppData\\Local\\Android\\Sdk" > local.properties

# 3. 构建 Debug APK（无需签名配置）
.\gradlew assembleAppDebug

# 4. 找到 APK
ls app\build\outputs\apk\app\debug\*.apk

# 5. 安装到设备
adb install app\build\outputs\apk\app\debug\legado_app_app_*.apk
```

---

## 十、参考链接

| 资源 | 地址 |
|------|------|
| Legado 源码 | https://github.com/gedoor/legado |
| Android Studio | https://developer.android.com/studio |
| JDK 17 (Adoptium) | https://adoptium.net/temurin/releases/?version=17 |
| Android SDK cmdline-tools | https://developer.android.com/studio#command-line-tools-only |
| keytool 文档 | https://docs.oracle.com/en/java/javase/17/docs/specs/man/keytool.html |
| Gradle Wrapper | 项目内置 `gradlew` / `gradlew.bat`，无需单独安装 |
