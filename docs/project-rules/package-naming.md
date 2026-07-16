# 包名规范（package-naming）

> 本项目在原版legado-E基础上扩展了包名机制,支持自定义包名实现与原版共存。

## 三类包定义

| 包类型 | 基础包名 | 后缀 | 最终包名 | 用途 |
|--------|---------|------|---------|------|
| **测试包** | `io.legado.app` | `.debug` | `io.legado.app.debug` | 开发调试、快速验证(默认) |
| **共存包** | 用户自定义 | `.debug`或无 | 如`com.my.legado.debug` | 与原版共存、私有化部署 |
| **正式包** | `io.legado.app` | `.release` | `io.legado.app.release` | 正式发布、生产环境 |

## 配置差异

| 配置项 | 测试包 | 共存包 | 正式包 |
|--------|--------|--------|--------|
| `minifyEnabled` | `false` | 由构建类型决定 | `true` |
| `shrinkResources` | `false` | 由构建类型决定 | `true` |
| `applicationIdSuffix` | `.debug` | `.debug`或无 | `.release` |
| 构建速度 | 快 | 中 | 慢 |
| APK体积 | 大 | 中 | 小 |

## 使用方法

| 操作 | 命令 | 最终包名 |
|------|------|---------|
| 构建测试包(默认) | `build-legado.bat` | `io.legado.app.debug` |
| 构建正式包 | `build-legado.bat release` | `io.legado.app.release` |
| 构建共存包 | `build-legado.bat debug com.my.legado` | `com.my.legado.debug` |

## 与原版差异

- **原版legado-E**: 单一固定包名`io.legado.app`,不支持共存
- **本项目**: 支持`-PcustomAppId`参数实现自定义包名,可与原版共存
