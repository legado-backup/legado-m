# 多模块架构

> Gradle 多模块结构：1 个 Android 主模块 + 2 个 Gradle 库模块 + 1 个 Vue3 前端子项目。
> 模块清单以 `settings.gradle` 为准（勿凭记忆新增）。

## 概述

项目采用"主模块集中、底层库下沉"的多模块划分：业务代码全部在 `:app`，与宿主强相关的第三方库经重打包后拆为独立 Gradle 模块（JS 沙箱、本地书解析），Web 管理端为独立 npm 子项目，构建产物由脚本同步进 `app` assets。

## 模块清单（settings.gradle 实际声明）

| 模块 | 路径 | 类型 | 职责 |
|------|------|------|------|
| `:app` | `app/` | Android 应用模块 | 全部业务：UI、规则引擎、数据层、服务、Web 服务 |
| `:modules:rhino` | `modules/rhino/` | Java/Kotlin 库 | Rhino JS 沙箱引擎（`com.script.rhino` 重打包） |
| `:modules:book` | `modules/book/` | Java 库 | EPUB（epublib）与 UMD（umdlib）解析（`me.ag2s` 重打包） |
| Web 前端 | `modules/web/` | Vue3 + Vite npm 子项目 | 远程书架/书源管理 Web 端（非 Gradle 模块） |

`settings.gradle` 末尾声明：`include ':app'`、`include ':modules:book'`、`include ':modules:rhino'`，`rootProject.name = 'legado'`。

## 核心类清单（modules/rhino，包 com.script.rhino）

| 类名 | 路径 | 职责 |
|------|------|------|
| RhinoScriptEngine | modules/rhino/src/main/java/com/script/rhino/RhinoScriptEngine.kt | JS 引擎实现（javax.script 接口） |
| RhinoClassShutter | modules/rhino/src/main/java/com/script/rhino/RhinoClassShutter.kt | 类访问白名单（沙箱核心） |
| RhinoWrapFactory | modules/rhino/src/main/java/com/script/rhino/RhinoWrapFactory.kt | Java 对象包装策略 |
| RhinoContextFactory | modules/rhino/src/main/java/com/script/RhinoContextFactory.kt | Context 工厂（超时/指令数限制入口） |

## 核心类清单（modules/book，包 me.ag2s）

| 类名 | 路径 | 职责 |
|------|------|------|
| EpubBook | modules/book/src/main/java/me/ag2s/epublib/domain/EpubBook.java | EPUB 书籍模型 |
| EpubReader | modules/book/src/main/java/me/ag2s/epublib/epub/EpubReader.java | EPUB 解析入口 |
| UmdBook | modules/book/src/main/java/me/ag2s/umdlib/domain/UmdBook.java | UMD 书籍模型 |
| UmdReader | modules/book/src/main/java/me/ag2s/umdlib/umd/UmdReader.java | UMD 解析入口 |

## 关键机制

- **依赖方向**：仅 `:app` 依赖 `:modules:rhino` / `:modules:book`，两个库模块不反向依赖 app。
- **沙箱下沉原因**：Rhino 1.8.1 锁版（新版 VarHandle.compareAndExchange 不被 desugaring 覆盖），独立模块便于锁定与替换，详见根 `gradle/libs.versions.toml` 注释。
- **Web 前端产物同步**：`modules/web/` 执行 `npm run build` 后由 `scripts/sync.js` 将产物复制进 `app` assets，App 内由 NanoHTTPD 对外服务。
- **深入阅读**：JS 沙箱细节见 [rhino-module.md](../modules/rhino-module.md)；EPUB/UMD 解析见 [local-book.md](../modules/local-book.md)；Gradle 配置见 [build-configuration.md](./build-configuration.md)；前端架构见 [frontend.md](./frontend.md)。
