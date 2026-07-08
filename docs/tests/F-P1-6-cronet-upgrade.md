# F-P1-6 Cronet 网络引擎升级 测试用例

> Task 26.5 / F-P1-6：Cronet 从 128.0.6613.40 升级到 149.0.7827.201

## 功能概述

| 子功能 | 说明 |
|--------|------|
| 版本升级 | `gradle.properties` CronetVersion 128.0.6613.40 → 149.0.7827.201 |
| jar 更新 | `app/cronetlib/` 下 5 个 jar 全部替换为 149 版本 |
| so 更新 | 4 架构 so（arm64-v8a/armeabi-v7a/x86/x86_64）全部替换为 149 版本 |
| cronet.json 重新生成 | 各架构 so 的 MD5 重新计算 |
| API 兼容性修复 | `ThreadUtils.setThreadAssertsDisabledForTesting` → `hasSubtleSideEffectsSetThreadAssertsDisabledForTesting` |

**升级动机**：同步最新 Chrome TLS 指纹，改善部分站点旧版本指纹拦截导致的 403 报错；优化弱网/高延迟场景 QUIC 性能与 HTTP/3 兼容性。

**实现文件**：
- `gradle.properties`（版本号修改）
- `app/src/main/assets/cronet.json`（由 downloadCronet 自动重新生成）
- `app/cronetlib/*.jar`（由 downloadCronet 自动替换）
- `app/src/main/java/io/legado/app/App.kt`（L76 API 废弃修复）
- `app/src/main/assets/updateLog.md`（cronet 版本号行同步）

**升级基础设施**：
- `app/download.gradle`：Gradle 任务 `downloadCronet`，自动下载 jar + so + 生成 cronet.json
- `.github/scripts/cronet.sh`：GitHub Actions 自动化升级脚本

## 测试环境

- 设备：JVM 编译验证（Level 2）+ Android 6.0+ 真机（Level 3）
- 构建版本：appDebug
- 测试框架：编译验证 + 真机操作

---

## 一、编译与 API 兼容性（Level 2 已通过）

### TC-F-P1-6-01：gradle.properties 版本号修改正确 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 读取 `gradle.properties` L44-45
2. 确认 CronetVersion=149.0.7827.201 + CronetMainVersion=149.0.0.0

**预期结果**：
- ✅ CronetVersion=149.0.7827.201
- ✅ CronetMainVersion=149.0.0.0

**实际结果**：通过

### TC-F-P1-6-02：downloadCronet 下载完整 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 执行 `gradlew app:downloadCronet`
2. 检查 `app/cronetlib/` 下 5 个 jar 文件
3. 检查 `app/src/main/assets/cronet.json` 内容

**预期结果**：
- ✅ 5 个 jar 全部下载：cronet_api/cronet_impl_common_java/cronet_impl_native_java/cronet_impl_platform_java/cronet_shared_java
- ✅ cronet.json 包含 4 架构 MD5 + version=149.0.7827.201
- ✅ arm64-v8a: 1bb19e53b3534b2884ffaff3f6267804
- ✅ armeabi-v7a: 905e8fb3f090dd33f5f9d2c635ff3750
- ✅ x86: 8c7a1804136f90ff221f2bebf5ee1d30
- ✅ x86_64: 05f8556ad90f65edc0ecb31586ee2600

**实际结果**：通过（16s）

### TC-F-P1-6-03：API 兼容性检查 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 反编译新 `cronet_impl_native_java.jar` 中的 `org.chromium.base.ThreadUtils`
2. 检查 `setThreadAssertsDisabledForTesting` 方法是否存在
3. 查找替代方法

**预期结果**：
- ✅ 旧方法 `setThreadAssertsDisabledForTesting(boolean)` 已移除
- ✅ 新方法 `hasSubtleSideEffectsSetThreadAssertsDisabledForTesting(boolean)` 存在（签名相同）
- ✅ 其余 API（ExperimentalCronetEngine/UrlRequest/UploadDataProvider/X509Util）均兼容

**实际结果**：通过（反编译验证）

### TC-F-P1-6-04：App.kt API 废弃修复 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 读取 `App.kt` L75-79
2. 确认使用新方法名

**预期结果**：
- ✅ `ThreadUtils.hasSubtleSideEffectsSetThreadAssertsDisabledForTesting(true)`
- ✅ 添加注释说明 Cronet 149 API 变更

**实际结果**：通过

### TC-F-P1-6-05：编译验证 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 执行 `gradlew app:assembleAppDebug`

**预期结果**：
- ✅ BUILD SUCCESSFUL
- ✅ 无 Cronet 相关编译错误
- ✅ 警告均为预先存在（bundleOf/systemUiVisibility deprecated）

**实际结果**：通过（3m 20s）

### TC-F-P1-6-06：updateLog.md cronet 版本号同步 ✅ Level 2 已通过

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 读取 `updateLog.md` L5

**预期结果**：
- ✅ `## cronet版本: 149.0.7827.201`

**实际结果**：通过

---

## 二、真机回归测试（Level 3 待验证）

### TC-F-P1-6-07：Cronet so 下载与加载 ⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 首次启动（无缓存 so）

**测试步骤**：
1. 启动应用
2. 观察 `DebugLog` 输出 CronetLoader 加载日志
3. 检查 so 下载是否成功

**预期结果**：
- ✅ 从 `storage.googleapis.com` 下载 `libcronet.149.0.7827.201.so`
- ✅ MD5 校验通过
- ✅ CronetEngine 初始化成功
- ✅ `DebugLog.d("Cronet Version:", "149.0.7827.201")` 输出

### TC-F-P1-6-08：书源搜索功能 ⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- Cronet 已启用
- 导入 3+ 个书源

**测试步骤**：
1. 进入书源列表
2. 选择书源，执行搜索
3. 检查搜索结果是否正常

**预期结果**：
- ✅ 搜索请求正常发起（Cronet 引擎）
- ✅ 搜索结果正确返回
- ✅ 无 403 报错（除非站点本身限制）
- ✅ 无 ERR_CERT_/ERR_SSL_ 错误

### TC-F-P1-6-09：章节抓取功能 ⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 已添加一本书籍

**测试步骤**：
1. 进入书籍详情
2. 点击"获取目录"
3. 选择一章阅读

**预期结果**：
- ✅ 目录获取正常
- ✅ 章节内容加载正常
- ✅ 无网络错误

### TC-F-P1-6-10：图片加载功能 ⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 书源配置了封面图片

**测试步骤**：
1. 进入书架
2. 检查书籍封面是否加载

**预期结果**：
- ✅ 封面图片正常加载
- ✅ 无图片加载失败

### TC-F-P1-6-11：订阅源更新功能 ⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 导入订阅源

**测试步骤**：
1. 进入订阅源列表
2. 刷新订阅源

**预期结果**：
- ✅ 订阅源内容正常刷新
- ✅ 无网络错误

### TC-F-P1-6-12：TLS 指纹改善验证（核心价值）⏳ 待验证

**关联源码**：Cronet.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 准备一个原 128 版本会被 403 拦截的书源（如有）

**测试步骤**：
1. 使用原 128 版本访问该书源，记录 403 报错
2. 升级到 149 版本后访问同一书源
3. 对比访问结果

**预期结果**：
- ✅ 原 128 版本被 403 拦截的书源，149 版本可正常访问（TLS 指纹同步最新 Chrome）
- ✅ 或两者都被拦截（站点限制非指纹原因）

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 2（编译验证） | 6 | 6 ✅ | 0 |
| Level 3（真机验证） | 6 | 0 | 6 ⏳ |
| **合计** | **12** | **6** | **6** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 真机验证未执行 | Level 3 用例待用户在真机上验证 | 见第 27 章节集成验证 |
| TLS 指纹改善需对比验证 | 需准备原 128 版本被拦截的书源对比 | 用户实际使用中观察 403 报错减少情况 |
| so 运行时下载需网络 | 首次启动需访问 storage.googleapis.com | 用户需确保网络可访问 Google Storage |
