# 打包流程规整 - 技术设计

## Technical Approach

### TA-0 原版规范分析（legado-E/lyc版本）

#### 原版项目信息

- **项目**: legado-E (阅读Sigma)
- **GitHub**: https://github.com/Luoyacheng/legado-E
- **本地路径**: `temp\forks-comparison\legado-E\`
- **分析时间**: 2026-07-14

#### 原版打包命名规范（legado-E/app/build.gradle）

| 配置项 | 原版值 | 说明 |
|--------|--------|------|
| **applicationId** | `io.legado.app` | **固定值**,无动态参数 |
| **release后缀** | `.release` | 最终包名:`io.legado.app.release` |
| **debug后缀** | `.debug` | 最终包名:`io.legado.app.debug` |
| **productFlavors** | 仅`app`一个 | 用于构建变体,不影响包名 |

#### 原版核心代码

```groovy
// legado-E/app/build.gradle 第 50 行
applicationId "io.legado.app"  // 固定值,无动态参数

// buildTypes 配置
buildTypes {
    release {
        applicationIdSuffix '.release'
        minifyEnabled true
        shrinkResources = true
    }
    debug {
        applicationIdSuffix '.debug'
        minifyEnabled false
    }
}

// productFlavors 配置（仅一个）
productFlavors {
    app {
        dimension "mode"
        manifestPlaceholders.put("APP_CHANNEL_VALUE", "app")
    }
}
```

#### 原版与本项目对比

| 对比项 | 原版legado-E | 本项目 | 差异说明 |
|--------|-------------|----------------|---------|
| **基础包名** | `io.legado.app`(固定) | `io.legado.app`(支持自定义) | 本项目支持`-PcustomAppId`动态参数 |
| **自定义包名** | 不支持 | 支持`project.hasProperty("customAppId")` | 本项目可自定义包名实现共存 |
| **包名灵活性** | 单一包名 | 三类包(测试/共存/正式) | 本项目扩展性更强 |
| **后缀机制** | `.debug`/`.release` | 相同 | 一致 |
| **混淆配置** | debug不混淆/release混淆 | 相同 | 一致 |

#### 关键发现

1. **原版不支持共存包**: 原版使用单一固定包名`io.legado.app`,无法与官方版共存
2. **本项目已扩展**: 本项目已通过`project.hasProperty("customAppId")`实现动态包名,支持自定义包名与原版共存
3. **包名规范一致**: 后缀机制(`.debug`/`.release`)和混淆配置完全一致
4. **命名空间**: 原版`namespace = 'io.legado.app'`,本项目应保持一致(Java/Kotlin包名)

#### 对本项目的影响

本项目需要在原版基础上进行以下改造:

1. **保留后缀机制**: 继续`.debug`/`.release`后缀,与原版保持一致
2. **扩展包名参数**: 通过`-PcustomAppId`实现共存包,原版无此机制
3. **文档说明差异**: 在文档中明确说明本项目与原版的差异点

---

### TA-1 包名结构统一设计

#### 当前问题

| 组件 | 默认包名 | 问题 |
|------|---------|------|
| build-legado.bat | `io.legado.missapp` | 与 build.gradle 不一致 |
| app/build.gradle | `io.legado.app` | 官方包名 |
| 最终 Debug 包名 | `io.legado.app.debug` | 后缀自动追加 |
| 最终 Release 包名 | `io.legado.app.release` | 后缀自动追加 |

**核心问题**：脚本默认包名与 Gradle 默认包名不一致，用户混淆时容易打包出错误的包名。

#### 统一方案：三类包名分类

| 包类型 | applicationId 基础 | 后缀 | 最终包名 | 用途 |
|--------|-------------------|------|---------|------|
| **测试包** | `io.legado.missapp` | `.debug` | `io.legado.missapp.debug` | 开发调试，不混淆，快速验证（默认） |
| **共存包** | 用户自定义（如 `com.my.legado`） | `.debug` 或无 | 如 `com.my.legado.debug` | 与原版共存，私有化部署 |
| **正式包** | `io.legado.missapp` | `.release` | `io.legado.missapp.release` | 正式发布，混淆+收缩 |

#### 规范定义

```yaml
包名规范:
  测试包:
    base: "io.legado.missapp"
    suffix: ".debug"
    final: "io.legado.missapp.debug"
    minifyEnabled: false
    用途: "开发调试、快速验证、不混淆（默认）"
  共存包:
    base: "用户自定义（如 com.myname.legado）"
    suffix: ".debug" 或无（由构建类型决定）
    final: "如 com.myname.legado.debug"
    minifyEnabled: 由构建类型决定
    用途: "与原版共存、私有化部署"
  正式包:
    base: "io.legado.missapp"
    suffix: ".release"
    final: "io.legado.missapp.release"
    minifyEnabled: true
    用途: "正式发布、生产环境"
```

### TA-2 build.gradle 改造方案

#### 改造点 1：统一默认 applicationId

**当前代码**（app/build.gradle 第 54 行）：
```groovy
applicationId project.hasProperty("customAppId") ? project.property("customAppId") : "io.legado.app"
```

**改造后**：
```groovy
applicationId project.hasProperty("customAppId") ? project.property("customAppId") : "io.legado.missapp"
```

**说明**：将默认包名从 `io.legado.app` 改为 `io.legado.missapp`，与项目需求一致。

#### 改造点 2：包类型判断逻辑

在 `defaultConfig` 块中增加包类型判断注释和日志输出（不改变实际行为，仅增加可读性）：

```groovy
defaultConfig {
    // 包类型判断：
    // 1. 传 -PcustomAppId=xxx → 共存包（用户自定义包名）
    // 2. 不传参数 + 构建类型 debug → 测试包（io.legado.missapp.debug）
    // 3. 不传参数 + 构建类型 release → 正式包（io.legado.missapp.release）
    applicationId project.hasProperty("customAppId") ? project.property("customAppId") : "io.legado.missapp"

    // 输出最终包名，方便 AI 解析日志
    println "========== PACKAGE INFO =========="
    println "Base applicationId: ${applicationId}"
    println "Build type: ${project.gradle.startParameter.taskNames.find { it.contains('Release') } ? 'release' : 'debug'}"
    println "Custom package: ${project.hasProperty('customAppId')}"
    println "=================================="
}
```

#### 改造点 3：buildTypes 配置保持不变

当前 `buildTypes` 配置已满足三类包需求：

```groovy
buildTypes {
    release {
        applicationIdSuffix '.release'  // 正式包后缀
        minifyEnabled true
        shrinkResources = true
    }
    debug {
        applicationIdSuffix '.debug'    // 测试包后缀
        minifyEnabled false
    }
}
```

**关键机制**：`applicationIdSuffix` 会自动追加到 `applicationId` 后面，形成最终包名。

### TA-3 打包脚本改造方案

#### 改造目标

1. 保持默认包名为 `io.legado.missapp`（与 build.gradle 一致）
2. 默认构建测试包（debug）
3. 增加 AI 友好的日志输出

#### 改造方案

**方案 A：参数重构（推荐）**

```batch
:: 新增参数解析
:: 用法：build-legado.bat [debug|release] [type] [custom_package]
:: type: test（测试包）| coexist（共存包）| release（正式包）
:: custom_package: 仅 coexist 类型需要，指定自定义包名

:: 参数解析逻辑
set "BUILD_TYPE=debug"
set "PACKAGE_TYPE=test"
set "CUSTOM_APP_ID="

if /i "%~1"=="release" set "BUILD_TYPE=release"
if /i "%~2"=="test" set "PACKAGE_TYPE=test"
if /i "%~2"=="coexist" set "PACKAGE_TYPE=coexist"
if /i "%~2"=="release" set "PACKAGE_TYPE=release"

if "%PACKAGE_TYPE%"=="coexist" (
    if "%~3"=="" (
        echo [ERROR] coexist 类型需要指定自定义包名
        exit /b 1
    )
    set "CUSTOM_APP_ID=%~3"
)
```

**方案 B：保持当前用法，仅修正默认包名**

```batch
:: 仅修改第 21 行
set "DEFAULT_APP_ID=io.legado.missapp"
```

**推荐方案 B**（最小改动，向后兼容）：
- 保持 `DEFAULT_APP_ID` 为 `io.legado.missapp`（与 build.gradle 一致）
- 保持当前用法不变：`build-legado.bat [debug|release] [custom_package]`
- 通过文档说明三类包的使用方式

### TA-4 AI 执行流程设计

#### 流程设计原则

1. **参数化**：所有操作通过参数控制，避免硬编码路径
2. **日志结构化**：关键步骤输出固定格式日志，AI 可解析
3. **状态检查**：每步执行后验证结果，失败立即中止

#### AI 执行流程（伪代码）

```yaml
打包流程:
  输入:
    - build_type: "debug" | "release"
    - package_type: "test" | "coexist" | "release"
    - custom_package: string（仅 coexist 类型）

  步骤:
    1. 参数验证:
       - 检查 build_type 有效性
       - 如果 package_type == "coexist"，检查 custom_package 非空
       - 如果 package_type == "test"，设置 build_type = "debug"
       - 如果 package_type == "release"，设置 build_type = "release"

    2. 环境检查:
       - 检查 JAVA_HOME 存在
       - 检查 ANDROID_HOME 存在
       - 检查 gradlew.bat 存在

    3. 清理缓存（可选）:
       - 删除 %LOCALAPPDATA%\kotlin\daemon
       - 执行 gradlew --stop

    4. 构建 APK:
       - 如果 package_type == "test":
         执行 gradlew assembleAppDebug --no-daemon
       - 如果 package_type == "coexist":
         执行 gradlew assembleApp{build_type} --no-daemon -PcustomAppId={custom_package}
       - 如果 package_type == "release":
         执行 gradlew assembleAppRelease --no-daemon

    5. 验证输出:
       - 检查 APK 文件存在
       - 解析 APK 包名（通过 aapt dump badging）
       - 输出结构化结果

  输出:
    - 状态: "success" | "failed"
    - APK路径: string
    - 最终包名: string
    - 构建时长: number
```

#### 日志格式规范

AI 执行时，每个关键步骤需输出固定格式日志：

```log
[AI_BUILD] STEP_START: {step_name}
[AI_BUILD] STEP_PARAM: {key}={value}
[AI_BUILD] STEP_RESULT: {success|failed}
[AI_BUILD] STEP_OUTPUT: {output_path}
[AI_BUILD] STEP_DURATION: {ms}
[AI_BUILD] PACKAGE_INFO: base={base_package}, suffix={suffix}, final={final_package}
```

### TA-5 文档更新方案

#### 文档重构目标

1. **AI 友好**：结构化步骤、参数化命令、固定格式输出
2. **三类包清晰**：明确区分测试包/共存包/正式包的使用场景
3. **错误处理**：常见问题快速定位表

#### 文档结构设计

```markdown
# 打包流程规范（AI 执行版）

## 快速开始

### 一键命令（推荐 AI 使用）

| 包类型 | 命令 | 最终包名 |
|--------|------|---------|
| 测试包 | `build-legado.bat` | `io.legado.missapp.debug` |
| 正式包 | `build-legado.bat release` | `io.legado.missapp.release` |
| 共存包 | `build-legado.bat debug com.my.legado` | `com.my.legado.debug` |

### AI 执行流程

1. 参数验证
2. 环境检查
3. 执行构建
4. 验证输出
5. 返回结果

## 包名规范

### 三类包分类

（详细说明）

## 常见问题

（快速定位表）
```

## Architecture Decisions

### AD-01: 包名分类策略 - 三类包统一管理

- **Context**: 当前 build-legado.bat 默认包名（`io.legado.missapp`）与项目需求一致，但缺少明确的包名分类规范。测试包、共存包、正式包的使用场景未明确区分。
- **Concern**: 如何在不破坏现有功能的前提下，统一包名规范，让用户和 AI 都能清晰理解三种包类型的差异和使用方式。
- **Decision**: 采用"测试包/共存包/正式包"三类包分类策略，通过构建类型和可选的自定义包名参数组合实现：
  - **测试包**：默认包名 `io.legado.missapp` + `.debug` 后缀，用于开发调试
  - **共存包**：用户自定义包名，用于与原版共存
  - **正式包**：默认包名 `io.legado.missapp` + `.release` 后缀，用于生产发布
- **Goal**: 统一包名规范，减少用户混淆，让 AI 能根据包类型自动选择正确的构建参数。
- **Tradeoff**: 需要更新文档，但保持向后兼容（现有用法仍然有效）。共存包需要用户手动指定包名，增加一步操作，但换来与原版共存的能力。
- **Status**: Proposed

### AD-02: AI 执行流程设计 - 参数化 + 日志结构化

- **Context**: 当前打包文档（build-apk-guide.md）面向人类用户，步骤描述详细但缺乏 AI 执行所需的固定格式日志和参数化命令。AI 执行时需要解析大量文本才能确定执行步骤。
- **Concern**: 如何让 AI 能够可靠地执行打包流程，并在失败时快速定位问题？
- **Decision**: 采用"参数化 + 日志结构化"策略：
  1. **参数化**：所有操作通过参数控制（build_type、package_type、custom_package），避免硬编码路径
  2. **日志结构化**：关键步骤输出固定格式日志（`[AI_BUILD] STEP_START/RESULT/OUTPUT`），AI 可解析
  3. **状态检查**：每步执行后验证结果，失败立即中止并输出错误码
- **Goal**: 让 AI 能根据包类型自动选择正确的构建参数，在失败时快速定位问题，无需人工介入。
- **Tradeoff**: 需要改造打包脚本（增加参数解析和结构化日志），增加实现复杂度。但换来 AI 执行的可靠性和自动化能力。
- **Status**: Proposed

### AD-03: 脚本改造策略 - 最小改动 + 向后兼容

- **Context**: build-legado.bat 已有完整的环境检查、缓存清理、构建逻辑，但默认包名与 build.gradle 不一致。如果重构脚本，可能引入新 bug。
- **Concern**: 如何统一包名，同时保持现有功能稳定？
- **Decision**: 采用"最小改动 + 向后兼容"策略：
  1. **仅修正默认包名**：将 `DEFAULT_APP_ID` 从 `io.legado.missapp` 改为 `io.legado.app`
  2. **保持参数接口不变**：现有用法 `build-legado.bat [debug|release] [custom_package]` 仍然有效
  3. **通过文档说明三类包**：不在脚本中新增参数，通过文档引导用户理解包类型
- **Goal**: 最小改动统一包名，降低引入 bug 的风险，保持现有用户习惯。
- **Tradeoff**: 无法通过脚本参数明确指定包类型（如 `--type test`），需要用户通过文档理解。但换来极低的改造风险和 100% 向后兼容。
- **Status**: Proposed

## Data Flow

### 打包流程数据流（文本描述）

```
┌─────────────────────────────────────────────────────────────┐
│  1. 用户/AI 输入                                             │
│  - build_type: debug | release                              │
│  - custom_package: 可选（共存包需要）                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 参数解析与包类型判定                                       │
│  - 如果 custom_package 为空 → 测试包 or 正式包（默认包名）     │
│  - 如果 custom_package 非空 → 共存包（自定义包名）            │
│  - 根据 build_type 确定最终包名后缀                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 环境检查                                                 │
│  - 检查 JAVA_HOME（JDK 17）                                  │
│  - 检查 ANDROID_HOME（Android SDK）                          │
│  - 检查 gradlew.bat 存在                                     │
│  - 失败 → 输出 [AI_BUILD] ERROR: {缺失项}                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 缓存清理（可选，解决常见构建问题）                         │
│  - 删除 %LOCALAPPDATA%\kotlin\daemon（解决 AccessDenied）    │
│  - 执行 gradlew --stop（停止残留 daemon）                     │
│  - 清理 transforms 缓存（解决跨盘符问题）                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 构建 APK                                                 │
│  - 测试包：gradlew assembleAppDebug --no-daemon              │
│  - 正式包：gradlew assembleAppRelease --no-daemon            │
│  - 共存包：gradlew assembleApp{build_type}                   │
│            --no-daemon -PcustomAppId={custom_package}        │
│  - 输出日志：[AI_BUILD] STEP_START: BUILD                    │
│              [AI_BUILD] PACKAGE_INFO: base=xxx, suffix=xxx   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. 验证输出                                                 │
│  - 检查 APK 文件存在（app/build/outputs/apk/app/{type}/）    │
│  - 通过 aapt dump badging 解析 APK 包名                       │
│  - 输出结构化结果：                                           │
│    [AI_BUILD] STEP_RESULT: success                           │
│    [AI_BUILD] STEP_OUTPUT: {apk_path}                        │
│    [AI_BUILD] PACKAGE_FINAL: {final_package_name}            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  7. 返回结果（供 AI 解析）                                    │
│  {                                                           │
│    "status": "success" | "failed",                           │
│    "apk_path": "app/build/outputs/apk/...",                  │
│    "package_name": "io.legado.app.debug",                    │
│    "build_duration_ms": 123456                               │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### 包名计算规则

```
输入参数：
  build_type = "debug" | "release"
  custom_package = string | null

计算逻辑：
  if custom_package == null:
    base_package = "io.legado.app"
  else:
    base_package = custom_package

  if build_type == "debug":
    suffix = ".debug"
  else if build_type == "release":
    suffix = ".release"

  final_package = base_package + suffix

输出：
  final_package: "io.legado.app.debug" | "io.legado.app.release" | "{custom_package}.debug" | "{custom_package}.release"
```

## File Changes

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `app/build.gradle` | 修改 | 将默认包名从 `io.legado.app` 改为 `io.legado.missapp`（第 54 行），增加包类型判断注释和日志输出 |
| `build-legado.bat` | 保持不变 | 默认包名 `io.legado.missapp` 已与 build.gradle 一致 |
| `docs/project-flow/build-apk-guide.md` | 重构 | 新增"三类包分类"章节，新增"AI 执行流程"章节，优化文档结构 |
| `docs/specs/build-workflow-optimization/README.md` | 新增 | 功能概述、核心能力、文档索引、状态标记 |
| `docs/specs/build-workflow-optimization/spec.md` | 新增 | Intent/Scope/Approach/Requirements/Scenarios |
| `docs/specs/build-workflow-optimization/tasks.md` | 新增 | 任务清单 |
| `docs/INDEX.md` | 更新 | 更新 spec 状态标记 |

## 验证标准

### 功能验证

1. **测试包构建**：执行 `build-legado.bat`，验证最终包名为 `io.legado.missapp.debug`
2. **正式包构建**：执行 `build-legado.bat release`，验证最终包名为 `io.legado.missapp.release`
3. **共存包构建**：执行 `build-legado.bat debug com.test.legado`，验证最终包名为 `com.test.legado.debug`

### 文档验证

1. **三类包清晰**：文档明确区分测试包/共存包/正式包的使用场景和命令
2. **AI 友好**：文档包含结构化步骤、参数化命令、固定格式输出示例
3. **错误处理**：文档包含常见问题快速定位表

### 回归验证

1. **向后兼容**：现有用法仍然有效，不影响已有用户习惯
2. **构建稳定**：脚本改动不引入新 bug，构建流程稳定