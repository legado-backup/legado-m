# 打包流程规整

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> ⚠️ **历史 spec 文档提示（2026-07-21 更新）**：本 spec 文档创建时项目包名为 `io.legado.missapp`（无点），后续已重命名为 `io.legado.miss.app`（有点）。本文档中所有 `io.legado.missapp` 均为历史值，**实际打包请以 [build-apk-guide.md](../../project-flow/build-apk-guide.md) 为准**（包名 `io.legado.miss.app`、任务名 `assembleAppDebug`/`assembleAppRelease`、签名用 local.properties 方式）。

> 统一 Legado 项目的包名规范与打包流程，提供面向 AI 执行的标准化操作指南，解决当前脚本与构建配置不一致的问题。

## 背景与问题

### 当前状态
- **打包脚本**：`build-legado.bat` 默认包名 `io.legado.missapp`
- **构建配置**：`build.gradle` 默认包名已修改为 `io.legado.missapp`（与脚本一致）
- **包名后缀**：release 构建 `.release`，debug 构建 `.debug`
- **自定义支持**：通过 `-PcustomAppId` 参数支持自定义包名

### 核心问题
1. ~~**脚本与配置不一致**~~：✅ 已解决（默认包名已统一为 `io.legado.missapp`）
2. **缺少包名分类规范**：测试包/共存包/正式包无明确命名规则
3. **文档缺少 AI 执行规范**：现有文档（693行）面向人类，缺少面向 AI 的结构化执行流程
4. **脚本功能分散**：签名配置、包名管理、输出路径等分散在多处

## 核心能力

### 1. 统一包名规范（三级分类）

| 分类 | 包名格式 | 用途 | 示例 |
|------|---------|------|------|
| **测试包** | `io.legado.missapp.debug` | 开发调试、功能验证（默认） | `io.legado.missapp.debug` |
| **共存包** | 用户自定义 | 与原版共存、私有化部署 | `com.mycompany.legado.debug` |
| **正式包** | `io.legado.missapp.release` | 生产环境、分发发布 | `io.legado.missapp.release` |

> **设计说明**：基础包名统一为 `io.legado.missapp`（与原版 `io.legado.app` 区分），通过 buildTypes 后缀区分 debug/release，不使用 productFlavors 简化构建流程。

### 2. AI 可执行打包流程

提供结构化的执行步骤，包含：
- **前置检查**：环境验证（JDK/SDK/签名配置）
- **包名选择**：根据任务类型自动选择包名
- **构建执行**：标准化命令与参数
- **结果验证**：APK 校验、包名确认、签名验证
- **异常处理**：常见错误与解决方案

### 3. 脚本规整与增强

- **统一默认包名**：脚本与 build.gradle 保持一致（`io.legado.app`）
- **包名分类支持**：新增 `--test` / `--coexist` 参数快捷指定
- **输出路径规范化**：统一输出到 `output/apk/{buildType}/` 目录
- **构建产物命名**：`legado-{buildType}-{versionCode}-{timestamp}.apk`

### 4. 文档体系完善

- **AI 执行手册**：结构化步骤、决策树、异常处理
- **人类操作指南**：保留现有文档，补充包名规范章节
- **配置速查表**：包名映射、参数对照、常见场景

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格：包名规范设计、AI 执行流程设计、脚本改造方案 |
| [design.md](./design.md) | 技术设计：包名生成逻辑、脚本改造细节、文档结构调整 |
| [tasks.md](./tasks.md) | 任务清单：脚本改造、文档规整、测试验证、交付物 |

## 价值与收益

### 对 AI Agent
- **执行确定性**：标准化流程减少决策分支，提高执行成功率
- **错误可恢复**：异常处理流程完整，失败后有明确恢复路径
- **知识可复用**：结构化文档易于加载到记忆系统

### 对开发者
- **包名清晰**：三级分类避免混淆，用途一目了然
- **操作简化**：新增快捷参数，减少手动输入
- **可追溯性**：构建产物命名规范，便于版本管理

### 对项目
- **配置一致**：脚本与构建配置统一，减少踩坑
- **文档清晰**：AI + 人类双轨文档，覆盖不同场景
- **可维护性**：规范化流程降低维护成本

## 状态

🔄 设计中

## 相关文档

- 现有打包指南：[docs/project-flow/build-apk-guide.md](../../project-flow/build-apk-guide.md)
- 构建配置：[app/build.gradle](../../../app/build.gradle)
- 打包脚本：[build-legado.bat](../../../build-legado.bat)