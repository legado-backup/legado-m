# F-P0-1 调试工具集 测试用例（第二波扩展）

> 6 大调试工具深度测试 + 入口迁移验证（实测修正：真实路径为"我的→其它设置→（滚动）→调试工具"，updateLog.md 的"设置→其他设置"描述不准确）

## 功能概述

在"我的→其它设置→调试工具"入口添加 6 个开发调试工具，支持复制结果，便于书源开发调试。

> 入口迁移实测确认（2026/07/08）：
> - updateLog.md 说迁移到"设置→其他设置→调试工具"
> - 实测真实路径：**我的 → 其它设置（preference 条目）→ 滚动 4 次 → 调试工具**
> - "其它设置"是"我的"页面中段可点击 preference 条目，点击进入 ConfigActivity（OtherConfigFragment）
> - "调试工具"preference（key=debug_tools）在页面底部，需滚动 4 次可见
> - 点击后跳转 DebugToolsActivity，含编码转换/curl/正则/时间戳等工具

**入口**：MainActivity → 我的 → 其它设置 → 调试工具（preference key=debug_tools）
**实现文件**：DebugToolsActivity.kt + CurlTestScreen.kt / HttpTestScreen.kt / PingTestScreen.kt / RegexTestScreen.kt / TimestampTestScreen.kt / EncodingTestScreen.kt

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug

---

## TC-F-P0-1-15：调试工具入口迁移验证（Level 3，正常用例）

**关联源码**：DebugToolsActivity.kt
**关联 Activity**：DebugToolsActivity

**前置资源**：
[共享] App 已安装并可正常启动

**测试步骤**：
1. 启动 App，进入主界面
2. 点击 我的
3. 点击 其它设置
4. 滚动 down
5. 滚动 down
6. 滚动 down
7. 滚动 down
8. 点击 调试工具

**预期结果**：
- ✅ 调试工具入口在"设置→其他设置"下可见
- ✅ 点击后进入调试工具列表（DebugToolsActivity）
- ✅ 6 个工具（编码转换/HTTP请求/curl/ping/正则/时间戳）均可点击

## TC-F-P0-1-16：编码转换 - 多种编码循环切换（Level 3，正常用例）

**关联源码**：EncodingTestScreen.kt, DebugToolsActivity.kt
**关联 Activity**：DebugToolsActivity

**前置资源**：
[共享] App 已安装

**测试步骤**：
1. 点击 我的
2. 点击 其它设置
3. 滚动 down
4. 滚动 down
5. 滚动 down
6. 滚动 down
7. 点击 调试工具
8. 点击 编码转换
9. 输入 "测试文本123"
10. 点击 Base64
11. 点击 转换
12. 点击 URL
13. 点击 转换
14. 点击 Unicode
15. 点击 转换

**预期结果**：
- ✅ Base64 编码结果正确（5q2k5rWL6K+VMTIz）
- ✅ URL 编码结果正确（%E6%B5%8B%E8%AF%95%E6%96%87%E6%9C%AC1%32%33）
- ✅ Unicode 编码结果正确
- ✅ 切换过程不崩溃，结果实时更新

## TC-F-P0-1-17：HTTP 请求 - POST 方法带请求体（Level 3，正常用例）

**关联源码**：HttpTestScreen.kt, DebugToolsActivity.kt
**关联 Activity**：DebugToolsActivity

**前置资源**：
[共享] App 已安装，网络可用

**测试步骤**：
1. 进入"调试工具→HTTP 请求"
2. URL 输入 `https://httpbin.org/post`
3. 方法选择 POST
4. 请求体输入 `{"key":"value"}`
5. 点击"发送"
6. 查看响应

**预期结果**：
- ✅ HTTP 状态码 200
- ✅ 响应体包含 echo 的请求数据
- ✅ 支持复制响应
- ✅ 不崩溃

## TC-F-P0-1-18：curl 命令 - 复杂参数与重定向跟随（Level 3，正常用例）

**关联源码**：CurlTestScreen.kt, DebugToolsActivity.kt
**关联 Activity**：DebugToolsActivity

**前置资源**：
[共享] App 已安装，网络可用

**测试步骤**：
1. 进入"调试工具→curl 命令"
2. 输入 `curl -L -X GET https://httpbin.org/redirect-to?url=https://httpbin.org/get`
3. 点击"执行"
4. 查看输出

**预期结果**：
- ✅ 正确执行 curl 命令（-L 跟随重定向）
- ✅ 显示最终响应内容
- ✅ 支持复制结果
- ✅ 不崩溃

## TC-F-P0-1-19：时间戳 - 负数与极大值边界（Level 3，边界用例）

**关联源码**：TimestampTestScreen.kt, DebugToolsActivity.kt
**关联 Activity**：DebugToolsActivity

**前置资源**：
[共享] App 已安装

**测试步骤**：
1. 进入"调试工具→时间戳转换"
2. 输入 `-1`，点击"转换"
3. 清空，输入 `9999999999999`（极大值），点击"转换"
4. 清空，输入 `abc`（非数字），点击"转换"

**预期结果**：
- ✅ -1 显示合理日期（不崩溃，如 1970-01-01 之前或错误提示）
- ✅ 极大值不导致溢出崩溃，显示合理结果或提示
- ✅ 非数字输入提示"请输入有效数字"
- ✅ 全程不崩溃
