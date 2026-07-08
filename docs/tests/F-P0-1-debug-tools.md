# F-P0-1 调试工具集 测试用例

> 6 大调试工具：编码转换 / HTTP 请求 / curl 命令 / ping / 正则测试 / 时间戳转换

## 功能概述

在"我的→其它设置→调试工具"入口添加 6 个开发调试工具，支持复制结果，便于书源开发调试。

> 入口迁移说明（updateLog.md 2026/07/08 + 实测修正 + D1 click 滚动查找）：
> 原入口"我的→调试工具"已迁移。updateLog.md 描述为"设置→其他设置→调试工具"，
> 但实测真实路径为 **我的 → 其它设置（preference 条目）→ 滚动到底部 → 调试工具**。
> "其它设置"是"我的"页面中段的可点击 preference 条目（非分类标题"设置"），
> 点击后进入 ConfigActivity（OtherConfigFragment），页面内"调试工具"在底部需滚动 4 次可见。
> **D1 优化（OpenSpec e2e-ui-executor-hardening）**：click 滚动查找已实现，用例无需显式 scroll 步骤，
> click 找不到元素时自动向下滚动 N 次查找（config.SCROLL_SEARCH_MAX=5）。

**入口**：MyActivity → 其它设置 → 调试工具（preference key=debug_tools）
**实现文件**：CurlTestScreen.kt / HttpTestScreen.kt / PingTestScreen.kt / RegexTestScreen.kt / TimestampTestScreen.kt / EncodingTestScreen.kt + DebugToolsActivity.kt

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug

---

## TC-F-P0-1-01：编码转换工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 点击 我的
2. 点击 其它设置
3. 点击 调试工具
4. 点击 编码转换
5. 输入 "你好世界"
6. 点击 转换
7. 点击 复制

> 步骤说明（2026/07/08 修正）：EncodeToolsScreen 使用 Jetpack Compose `ExposedDropdownMenuBox` 选择编码类型，"Base64 编码"（encodeTypes[0]）为默认选中（currentType=0），无需显式点击选择，故原"点击 Base64"步骤已删除。

**预期结果**：
- ✅ 转换过程不崩溃，无异常
- ✅ 编码结果正常显示

## TC-F-P0-1-02：编码转换 - 空输入（边界用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入编码转换工具
2. 不输入任何内容
3. 点击"转换"

**预期结果**：
- ✅ 提示"请输入内容"
- ✅ 不崩溃

## TC-F-P0-1-03：HTTP 请求工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入"HTTP 请求"工具
2. URL 输入 `https://httpbin.org/get`
3. 方法选择 GET
4. 点击"发送"
5. 查看响应

**预期结果**：
- ✅ 正确显示 HTTP 状态码 200
- ✅ 正确显示响应头和响应体
- ✅ 支持复制响应

## TC-F-P0-1-04：HTTP 请求 - 无效 URL（异常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入 HTTP 请求工具
2. URL 输入 `invalid-url`
3. 点击"发送"

**预期结果**：
- ✅ 显示错误提示"URL 格式错误"或类似信息
- ✅ 不崩溃

## TC-F-P0-1-05：curl 命令工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入"curl 命令"工具
2. 输入 `curl https://httpbin.org/get`
3. 点击"执行"
4. 查看输出

**预期结果**：
- ✅ 正确执行 curl 命令
- ✅ 显示响应内容
- ✅ 支持复制结果

## TC-F-P0-1-06：curl 命令 - 语法错误（异常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入 curl 工具
2. 输入 `curl`（无 URL）
3. 点击"执行"

**预期结果**：
- ✅ 显示 curl 错误信息
- ✅ 不崩溃

## TC-F-P0-1-07：ping 工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入"ping"工具
2. 输入 `www.baidu.com`
3. 点击"开始"
4. 查看结果

**预期结果**：
- ✅ 显示 ping 延迟结果
- ✅ 支持停止 ping
- ✅ 支持复制结果

## TC-F-P0-1-08：ping - 不可达主机（异常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入 ping 工具
2. 输入 `nonexistent.host.invalid`
3. 点击"开始"

**预期结果**：
- ✅ 显示"无法解析主机"或超时信息
- ✅ 不崩溃

## TC-F-P0-1-09：正则测试工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入"正则测试"工具
2. 正则输入 `第[一二三四五六七八九十百千0-9]+章`
3. 测试文本输入 `第一章 雨夜来客\n第二章 暗流涌动`
4. 点击"测试"

**预期结果**：
- ✅ 高亮显示匹配结果
- ✅ 显示匹配数量
- ✅ 支持复制匹配结果

## TC-F-P0-1-10：正则测试 - 无效正则（异常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入正则测试工具
2. 正则输入 `[invalid`
3. 点击"测试"

**预期结果**：
- ✅ 显示"正则表达式格式错误"
- ✅ 不崩溃

## TC-F-P0-1-11：时间戳转换工具（正常用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入"时间戳转换"工具
2. 输入当前时间戳（秒级）
3. 点击"转换"

**预期结果**：
- ✅ 正确转换为日期时间格式
- ✅ 支持反向转换（日期→时间戳）
- ✅ 支持复制结果

## TC-F-P0-1-12：时间戳 - 边界值（边界用例）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 进入时间戳工具
2. 输入 `0`
3. 点击"转换"

**预期结果**：
- ✅ 显示 1970-01-01 00:00:00
- ✅ 不崩溃

---

## 集成验证

### TC-F-P0-1-13：调试工具入口可达性（Level 3）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
1. 安装 APK
2. 点击 我的
3. 点击 其它设置
4. 滚动 down
5. 滚动 down
6. 滚动 down
7. 滚动 down
8. 点击 调试工具

**预期结果**：
- ✅ 调试工具入口可见
- ✅ 点击后进入调试工具列表
- ✅ 6 个工具均可点击进入

### TC-F-P0-1-14：调试工具编译验证（Level 2）

**关联源码**：DebugToolsActivity.kt, CurlTestScreen.kt, HttpTestScreen.kt, PingTestScreen.kt, RegexTestScreen.kt, TimestampTestScreen.kt, EncodingTestScreen.kt
**关联 Activity**：DebugToolsActivity

**测试步骤**：
```bash
./gradlew.bat :app:assembleAppDebug
```

**预期结果**：
- ✅ BUILD SUCCESSFUL
