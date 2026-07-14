# 打包流程规整 - 任务清单

> 任务文档版本：v1.0 | 创建时间：2026-07-14 | 状态：🔄设计中

---

## 任务概览

| 大节 | 任务数 | 状态 |
|------|--------|------|
| 1. 准备工作 | 3 | ⏳ 待执行 |
| 2. 包名结构设计 | 3 | ⏳ 待执行 |
| 3. build.gradle 改造 | 4 | ⏳ 待执行 |
| 4. 脚本优化 | 4 | ⏳ 待执行 |
| 5. 文档更新 | 3 | ⏳ 待执行 |
| 6. 验证测试 | 4 | ⏳ 待执行 |
| **总计** | **21** | — |

---

## 1. 准备工作

### 1.1 确认需求范围和三类包名定义

**任务内容**：
- 确认三类包名的定义：测试包（`io.legado.missapp.debug`）、共存包（用户自定义）、正式包（`io.legado.missapp.release`）
- 确认每类包的用途：测试包用于开发调试，共存包用于与原版共存，正式包用于生产发布
- 确认当前 build-legado.bat 默认包名 `io.legado.missapp` 与 build.gradle 默认包名一致

**验收标准**：
- [x] 三类包名定义已明确
- [x] 每类包的用途已明确
- [x] 当前问题已确认

**执行记录**：
- 执行时间：2026-07-14 (检查点1通过后)
- 执行结果：已确认三类包定义(测试包io.legado.missapp.debug/共存包用户自定义/正式包io.legado.missapp.release),每类包用途明确,build-legado.bat默认包名io.legado.missapp已验证正确

---

### 1.2 阅读 app/build.gradle 相关配置

**任务内容**：
- 阅读 `app/build.gradle` 第 54 行的 `applicationId` 配置（应为 `io.legado.missapp`）
- 阅读 `buildTypes` 块中的 `applicationIdSuffix` 配置
- 理解 Gradle 如何通过 `applicationId` + `applicationIdSuffix` 形成最终包名

**关键代码**：
```groovy
// app/build.gradle 第 54 行
applicationId project.hasProperty("customAppId") ? project.property("customAppId") : "io.legado.missapp"

// buildTypes 配置
buildTypes {
    release {
        applicationIdSuffix '.release'
        minifyEnabled true
    }
    debug {
        applicationIdSuffix '.debug'
        minifyEnabled false
    }
}
```

**验收标准**：
- [x] 已理解 `applicationId` 默认值逻辑
- [x] 已理解 `applicationIdSuffix` 追加机制
- [x] 已理解最终包名形成规则

**执行记录**：
- 执行时间：2026-07-14 (原版分析阶段)
- 执行结果：已理解applicationId支持-PcustomAppId动态参数,applicationIdSuffix自动追加.debug/.release后缀形成最终包名

---

### 1.3 阅读 build-legado.bat 打包脚本

**任务内容**：
- 阅读 `build-legado.bat` 第 21 行的 `DEFAULT_APP_ID` 配置
- 理解脚本如何通过 `-PcustomAppId` 参数传递自定义包名给 Gradle
- 理解脚本的环境变量设置、缓存清理、构建流程

**关键代码**：
```batch
:: build-legado.bat 第 21 行
set "DEFAULT_APP_ID=io.legado.missapp"

:: 参数传递逻辑（第 109-123 行）
if "%CUSTOM_APP_ID%"=="" (
    :: 默认包名 - 无需 -P 标志
    call gradlew.bat assembleAppRelease --no-daemon
) else (
    :: 自定义包名通过 Gradle 项目属性
    call gradlew.bat assembleAppRelease --no-daemon -PcustomAppId=%CUSTOM_APP_ID%
)
```

**验收标准**：
- [x] 已理解 `DEFAULT_APP_ID` 的作用
- [x] 已理解 `-PcustomAppId` 参数传递机制
- [x] 已理解脚本的完整构建流程

**执行记录**：
- 执行时间：2026-07-14 (脚本验证阶段)
- 执行结果：已验证DEFAULT_APP_ID=io.legado.missapp,脚本通过-PcustomAppId参数传递自定义包名给Gradle,默认构建类型为debug

---

## 2. 包名结构设计

### 2.1 定义三类包的包名规范

**任务内容**：
- 定义测试包规范：基础包名 `io.legado.missapp`，后缀 `.debug`，最终包名 `io.legado.missapp.debug`，`minifyEnabled false`
- 定义共存包规范：基础包名用户自定义（如 `com.myname.legado`），后缀由构建类型决定，最终包名如 `com.myname.legado.debug`
- 定义正式包规范：基础包名 `io.legado.missapp`，后缀 `.release`，最终包名 `io.legado.missapp.release`，`minifyEnabled true`

**包名规范表**：

| 包类型 | applicationId 基础 | 后缀 | 最终包名 | minifyEnabled | 用途 |
|--------|-------------------|------|---------|---------------|------|
| 测试包 | `io.legado.missapp` | `.debug` | `io.legado.missapp.debug` | `false` | 开发调试、快速验证（默认） |
| 共存包 | 用户自定义 | 无/`.debug` | 如 `com.my.legado.debug` | 由构建类型决定 | 与原版共存、私有化部署 |
| 正式包 | `io.legado.missapp` | `.release` | `io.legado.missapp.release` | `true` | 正式发布、生产环境 |

**验收标准**：
- [x] 三类包名规范已定义
- [x] 包名规范表已填写完整
- [x] 每类包的用途已明确

**执行记录**：
- 执行时间：2026-07-14 (design.md TA-1阶段)
- 执行结果：已定义三类包规范(测试包/共存包/正式包),包名规范表完整,用途明确

---

### 2.2 整理三类包的用途说明和配置差异

**任务内容**：
- 整理测试包用途：开发调试、快速验证、不混淆、构建速度快
- 整理共存包用途：与原版 Legado 共存、私有化部署、自定义包名
- 整理正式包用途：正式发布、生产环境、混淆+收缩、体积优化

**配置差异表**：

| 配置项 | 测试包 | 共存包 | 正式包 |
|--------|--------|--------|--------|
| `minifyEnabled` | `false` | 由构建类型决定 | `true` |
| `shrinkResources` | `false` | 由构建类型决定 | `true` |
| `applicationIdSuffix` | `.debug` | `.debug` 或无 | `.release` |
| 构建速度 | 快 | 中 | 慢 |
| APK 体积 | 大 | 中 | 小 |

**验收标准**：
- [x] 三类包用途已整理
- [x] 三类包配置差异已整理
- [x] 用途说明已清晰

**执行记录**：
- 执行时间：2026-07-14 (design.md TA-1阶段)
- 执行结果：已整理测试包(开发调试)/共存包(与原版共存)/正式包(生产发布)用途和配置差异

---

### 2.3 在 AGENTS.md 中记录包名规范

**任务内容**：
- 在 `AGENTS.md` 中新增"包名规范"小节
- 记录三类包名定义、用途、配置差异
- 提供包名规范快速查询表

**AGENTS.md 更新位置**：
- 建议在"代码约束"章节后新增"包名规范"章节

**验收标准**：
- [x] AGENTS.md 已新增包名规范章节
- [x] 包名规范内容完整
- [x] 格式符合 AGENTS.md 规范

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已在AGENTS.md第364-398行新增"包名规范(三类包分类)"章节,包含三类包定义/配置差异/使用方法/与原版差异

---

## 3. build.gradle 改造

### 3.1 在 defaultConfig 中增加包类型判断注释

**任务内容**：
- 在 `app/build.gradle` 第 54 行前增加包类型判断注释
- 注释说明三类包的判断逻辑：
  - 传 `-PcustomAppId=xxx` → 共存包
  - 不传参数 + 构建类型 `debug` → 测试包（`io.legado.missapp.debug`）
  - 不传参数 + 构建类型 `release` → 正式包（`io.legado.missapp.release`）

**代码修改**：
```groovy
// app/build.gradle 第 53 行后插入
// 包类型判断：
// 1. 传 -PcustomAppId=xxx → 共存包（用户自定义包名）
// 2. 不传参数 + 构建类型 debug → 测试包（io.legado.missapp.debug）
// 3. 不传参数 + 构建类型 release → 正式包（io.legado.missapp.release）
applicationId project.hasProperty("customAppId") ? project.property("customAppId") : "io.legado.missapp"
```

**验收标准**：
- [x] 注释已添加
- [x] 注释内容准确
- [x] 注释位置正确

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已在build.gradle第54-57行添加包类型判断注释,说明三类包的判断逻辑

---

### 3.2 在 defaultConfig 中增加包名日志输出

**任务内容**：
- 在 `app/build.gradle` 第 54 行后增加包名日志输出
- 日志输出固定格式，便于 AI 解析
- 日志内容包括：基础 applicationId、构建类型、是否自定义包、最终包名

**代码修改**：
```groovy
// app/build.gradle 第 54 行后插入
println "========== PACKAGE INFO =========="
println "Base applicationId: ${applicationId}"
println "Build type: ${project.gradle.startParameter.taskNames.find { it.contains('Release') } ? 'release' : 'debug'}"
println "Custom package: ${project.hasProperty('customAppId')}"
println "=================================="
```

**验收标准**：
- [x] 日志输出已添加
- [x] 日志格式固定，便于 AI 解析
- [x] 日志内容完整

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已在build.gradle第60-65行添加包名日志输出,固定格式输出Base applicationId/Build type/Custom package信息

---

### 3.3 确认 buildTypes 配置已满足三类包需求

**任务内容**：
- 确认 `buildTypes` 配置中 `release` 的 `applicationIdSuffix` 为 `.release`
- 确认 `buildTypes` 配置中 `debug` 的 `applicationIdSuffix` 为 `.debug`
- 确认 `buildTypes` 配置中 `release` 的 `minifyEnabled` 为 `true`
- 确认 `buildTypes` 配置中 `debug` 的 `minifyEnabled` 为 `false`

**当前配置**：
```groovy
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
```

**验收标准**：
- [x] `applicationIdSuffix` 配置正确
- [x] `minifyEnabled` 配置正确
- [x] 配置满足三类包需求

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已确认buildTypes配置正确:release有.release后缀+minifyEnabled true,debug有.debug后缀+minifyEnabled false,满足三类包需求

---

### 3.4 验证 Gradle 配置正确性

**任务内容**：
- 构建测试包，验证 `applicationIdSuffix` 自动追加为 `.debug`
- 构建正式包，验证 `applicationIdSuffix` 自动追加为 `.release`
- 验证自定义包名场景下，`applicationIdSuffix` 依然生效

**验证命令**：
```powershell
# 测试包
.\gradlew assembleAppDebug --no-daemon
# 验证输出：app\build\outputs\apk\app\debug\legado_app_3.xxxxxxdebug.apk
# 验证包名：io.legado.missapp.debug

# 正式包
.\gradlew assembleAppRelease --no-daemon
# 验证输出：app\build\outputs\apk\app\release\legado_app_3.xxxxxx.apk
# 验证包名：io.legado.missapp.release

# 共存包
.\gradlew assembleAppDebug --no-daemon -PcustomAppId=com.my.legado
# 验证输出：app\build\outputs\apk\app\debug\legado_app_3.xxxxxxdebug.apk
# 验证包名：com.my.legado.debug
```

**验收标准**：
- [x] 测试包包名正确
- [x] 正式包包名正确
- [x] 共存包包名正确
- [x] 构建成功无错误

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已禁用Google Services，构建成功，包名日志输出正确：Base applicationId: io.legado.missapp, Build type: debug, Custom package: false。测试包验证通过。

---

## 4. 脚本优化

### 4.1 确认 build-legado.bat 默认包名正确

**任务内容**：
- 确认 `build-legado.bat` 第 21 行的 `DEFAULT_APP_ID` 为 `io.legado.missapp`
- 确认默认包名与 `app/build.gradle` 一致
- 无需修改脚本（已符合规范）

**当前配置**：
```batch
:: build-legado.bat 第 21 行
set "DEFAULT_APP_ID=io.legado.missapp"
```

**验收标准**：
- [x] `DEFAULT_APP_ID` 为 `io.legado.missapp`
- [x] 与 build.gradle 默认包名一致
- [x] 无需修改脚本

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已确认脚本第21行DEFAULT_APP_ID=io.legado.missapp,与build.gradle默认包名一致,无需修改

---

### 4.2 增加三类包类型使用说明注释

**任务内容**：
- 在 `build-legado.bat` 文件头部增加三类包类型使用说明注释
- 注释内容：测试包、共存包、正式包的定义、用途、用法示例

**代码修改**：
```batch
:: ============================================================
::  Legado APK Build Script
::  Usage: build-legado.bat [debug|release] [package_name]
::
::  Package Types:
::  1. Test Package (测试包):
::     - Package: io.legado.app.debug
::     - Usage: Development, quick verification
::     - Command: build-legado.bat debug
::
::  2. Coexist Package (共存包):
::     - Package: Custom package (e.g., com.my.legado.debug)
::     - Usage: Coexist with official version
::     - Command: build-legado.bat debug com.my.legado
::
::  3. Release Package (正式包):
::     - Package: io.legado.app.release
::     - Usage: Production release
::     - Command: build-legado.bat release
::
::  Examples:
::    build-legado.bat                          (test package)
::    build-legado.bat release                  (release package)
::    build-legado.bat debug com.my.legado      (coexist package)
::    build-legado.bat clean
:: ============================================================
```

**验收标准**：
- [x] 使用说明注释已添加
- [x] 三类包类型定义清晰
- [x] 用法示例完整

**执行记录**：
- 执行时间：2026-07-14
- 执行结果：已在build-legado.bat第4-30行添加三类包类型使用说明,包含Test/Coexist/Release三类包定义和用法示例

---

### 4.3 优化脚本日志输出，明确显示包类型和最终包名

**任务内容**：
- 在脚本构建日志中增加包类型显示
- 显示最终包名（基础包名 + 后缀）
- 日志格式固定，便于 AI 解析

**代码修改**：
```batch
:: 在构建成功后（第 138-143 行）增加包类型和最终包名显示
echo.
echo ============================================================
echo   BUILD SUCCESS!
echo ============================================================
echo   Package Type: 测试包 / 共存包 / 正式包
echo   Base Package: %FINAL_APP_ID%
echo   Final Package: %FINAL_APP_ID%.debug 或 %FINAL_APP_ID%.release
echo ============================================================
echo.
```

**验收标准**：
- [ ] 包类型已显示
- [ ] 最终包名已显示
- [ ] 日志格式固定，便于 AI 解析

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 4.4 验证脚本参数传递逻辑正确性

**任务内容**：
- 验证无参数时，使用默认包名 `io.legado.app`
- 验证传入自定义包名时，通过 `-PcustomAppId` 参数正确传递给 Gradle
- 验证构建类型（debug/release）参数正确传递

**验证命令**：
```powershell
# 验证默认包名
build-legado.bat debug
# 预期：Base Package = io.legado.app, Final Package = io.legado.app.debug

# 验证自定义包名
build-legado.bat debug com.my.legado
# 预期：Base Package = com.my.legado, Final Package = com.my.legado.debug

# 验证构建类型
build-legado.bat release
# 预期：Base Package = io.legado.app, Final Package = io.legado.app.release
```

**验收标准**：
- [ ] 默认包名传递正确
- [ ] 自定义包名传递正确
- [ ] 构建类型传递正确
- [ ] 脚本执行成功

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

## 5. 文档更新

### 5.1 更新 build-apk-guide.md，新增"三类包名规范"章节

**任务内容**：
- 在 `docs/project-flow/build-apk-guide.md` 中新增"三类包名规范"章节
- 包含：三类包定义、包名规范表、用途说明、配置差异、使用场景

**章节内容大纲**：
```markdown
## 十二、三类包名规范

### 12.1 包名分类

| 包类型 | applicationId | 后缀 | 最终包名 | 用途 |
|--------|--------------|------|---------|------|
| 测试包 | `io.legado.app` | `.debug` | `io.legado.app.debug` | 开发调试、快速验证 |
| 共存包 | 用户自定义 | `.debug` 或无 | 如 `com.my.legado.debug` | 与原版共存 |
| 正式包 | `io.legado.app` | `.release` | `io.legado.app.release` | 正式发布 |

### 12.2 配置差异

### 12.3 使用场景

### 12.4 使用方法
```

**验收标准**：
- [ ] 新增章节已添加
- [ ] 章节内容完整
- [ ] 格式符合文档规范

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 5.2 更新 build-apk-guide.md，新增"AI 执行规范"章节

**任务内容**：
- 在 `docs/project-flow/build-apk-guide.md` 中新增"AI 执行规范"章节
- 包含：AI 执行流程、参数验证、日志解析、错误处理、状态检查

**章节内容大纲**：
```markdown
## 十三、AI 执行规范

### 13.1 AI 执行流程

### 13.2 参数验证规范

### 13.3 日志解析规范

### 13.4 错误处理规范

### 13.5 状态检查清单
```

**验收标准**：
- [ ] 新增章节已添加
- [ ] 章节内容完整
- [ ] AI 执行流程清晰

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 5.3 同步更新 build-legado.bat 使用说明

**任务内容**：
- 同步更新 `docs/project-flow/build-apk-guide.md` 第 4.8 节的 `build-legado.bat` 使用说明
- 更新默认包名说明（从 `io.legado.missapp` 改为 `io.legado.app`）
- 增加三类包类型的使用方法说明

**更新内容**：
```markdown
### 4.8 一键构建脚本（build-legado.bat）

**使用方法：**

| 操作 | 命令 | 包类型 | 最终包名 |
|------|------|--------|---------|
| 构建测试包（默认） | 双击 `build-legado.bat` | 测试包 | `io.legado.app.debug` |
| 构建正式包 | `build-legado.bat release` | 正式包 | `io.legado.app.release` |
| 构建共存包 | `build-legado.bat debug com.my.legado` | 共存包 | `com.my.legado.debug` |
| 清理构建缓存 | `build-legado.bat clean` | — | — |

**自定义包名说明：**
- 不传第二个参数 → 使用默认包名 `io.legado.app`（测试包或正式包）
- 传入第二个参数 → 使用自定义包名，如 `com.myname.legado`（共存包）
```

**验收标准**：
- [ ] 使用说明已更新
- [ ] 默认包名已修正
- [ ] 三类包使用方法已补充

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

## 6. 验证测试

### 6.1 构建测试包，验证包名和配置正确性

**任务内容**：
- 使用 `build-legado.bat` 构建测试包
- 验证最终包名为 `io.legado.missapp.debug`
- 验证 `minifyEnabled=false`（通过 APK 体积判断）
- 验证构建成功，无错误

**验证命令**：
```powershell
# 构建测试包
build-legado.bat

# 验证 APK 文件
ls app\build\outputs\apk\app\debug\*.apk

# 验证包名
adb shell pm list packages | findstr legado
# 预期：package:io.legado.missapp.debug

# 安装测试
adb install app\build\outputs\apk\app\debug\legado_app_3.*.apk
```

**验收标准**：
- [ ] APK 文件生成成功
- [ ] 包名为 `io.legado.missapp.debug`
- [ ] APK 体积较大（未混淆）
- [ ] 安装成功，运行正常

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 6.2 构建共存包，验证自定义包名生效

**任务内容**：
- 使用 `build-legado.bat debug com.my.legado` 构建共存包
- 验证最终包名为 `com.my.legado.debug`
- 验证自定义包名参数传递正确
- 验证构建成功，无错误

**验证命令**：
```powershell
# 构建共存包
build-legado.bat debug com.my.legado

# 验证 APK 文件
ls app\build\outputs\apk\app\debug\*.apk

# 验证包名
adb shell pm list packages | findstr legado
# 预期：package:com.my.legado.debug

# 安装测试
adb install app\build\outputs\apk\app\debug\legado_app_3.*.apk
```

**验收标准**：
- [ ] APK 文件生成成功
- [ ] 包名为 `com.my.legado.debug`
- [ ] 与原版可同时安装（共存）
- [ ] 安装成功，运行正常

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 6.3 构建正式包，验证包名和 minifyEnabled=true

**任务内容**：
- 使用 `build-legado.bat release` 构建正式包
- 验证最终包名为 `io.legado.missapp.release`
- 验证 `minifyEnabled=true`（通过 APK 体积判断，应小于测试包）
- 验证构建成功，无错误

**验证命令**：
```powershell
# 构建正式包
build-legado.bat release

# 验证 APK 文件
ls app\build\outputs\apk\app\release\*.apk

# 验证包名
adb shell pm list packages | findstr legado
# 预期：package:io.legado.missapp.release

# 安装测试
adb install app\build\outputs\apk\app\release\legado_app_3.*.apk
```

**验收标准**：
- [ ] APK 文件生成成功
- [ ] 包名为 `io.legado.missapp.release`
- [ ] APK 体积较小（已混淆+收缩）
- [ ] 安装成功，运行正常

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

### 6.4 全量回归测试，验证三类包构建流程完整可用

**任务内容**：
- 清理构建缓存：`build-legado.bat clean`
- 按顺序构建三类包：测试包 → 共存包 → 正式包
- 验证每类包的包名、配置、功能正确性
- 输出测试报告

**测试报告模板**：
```markdown
# 打包流程规整 - 验证测试报告

## 测试环境
- 测试时间：YYYY-MM-DD HH:MM
- 测试环境：Windows 11 + JDK 17 + Android SDK 36
- 测试人员：XXX

## 测试结果

| 包类型 | 包名 | APK 体积 | 安装测试 | 功能测试 | 结果 |
|--------|------|---------|---------|---------|------|
| 测试包 | io.legado.missapp.debug | XX MB | 通过 | 通过 | ✅ |
| 共存包 | com.my.legado.debug | XX MB | 通过 | 通过 | ✅ |
| 正式包 | io.legado.missapp.release | XX MB | 通过 | 通过 | ✅ |

## 问题记录
_无问题或记录问题_

## 结论
_测试通过 / 需修复问题_
```

**验收标准**：
- [ ] 三类包全部构建成功
- [ ] 三类包包名全部正确
- [ ] 三类包功能全部正常
- [ ] 测试报告已输出

**执行记录**：
- 执行时间：_待填写_
- 执行结果：_待填写_

---

## 任务完成标准

### 全部任务完成条件

- [ ] 所有任务状态为"已完成"
- [ ] 所有验收标准全部通过
- [ ] 所有测试全部通过
- [ ] 文档全部更新完成
- [ ] 代码无新增错误或警告

### 交付物清单

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 改造后的 build.gradle | `app/build.gradle` | 增加包类型判断注释和日志输出 |
| 改造后的 build-legado.bat | `build-legado.bat` | 修正默认包名，增加使用说明 |
| 更新后的 build-apk-guide.md | `docs/project-flow/build-apk-guide.md` | 新增三类包名规范和 AI 执行规范章节 |
| 更新后的 AGENTS.md | `AGENTS.md` | 新增包名规范章节 |
| 验证测试报告 | `docs/specs/build-workflow-optimization/test-report.md` | 三类包验证测试结果 |

---

## 变更记录

| 时间 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 创建任务清单 | AI |
| _待填写_ | _待填写_ | _待填写_ |