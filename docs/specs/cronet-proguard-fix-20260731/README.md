# Cronet ProGuard 规则修复（2026-07-31）

> 状态：🔄 设计中
> 创建时间：2026-07-31 07:41:45
> 作者：AI Agent

## 功能概述

修复 release 包打开视频订阅源时 SIGABRT 崩溃问题。根因是 R8 混淆移除了 `org.chromium.net.Cronet` 入口类，导致 libcronet.so 在 JNI_OnLoad 阶段 `FindClass` 返回 null，`GetStaticMethodID(null, ...)` 触发 native abort。

同时修复由此引发的"整体嗅探能力减弱"问题：Cronet 崩溃后 CronetInterceptor 降级到 OkHttp，OkHttp 的 Conscrypt TLS 指纹被 CDN 检测拒绝，导致视频嗅探 Range 请求被 CDN 返回 403/连接重置，嗅探失败率大幅上升。

## 核心能力

1. **崩溃修复**：补全 ProGuard 规则，保留 libcronet.so 通过 JNI 反射调用的所有 Java 类，确保 release 包 Cronet native 引擎正常初始化
2. **嗅探恢复**：Cronet 正常工作后，CronetInterceptor 使用 BoringSSL TLS 栈（与 Chrome 一致），CDN 不再拒绝嗅探请求
3. **回归防护**：在 package-naming.md 中强化 ProGuard 规则验证清单，防止后续 R8 升级再次移除关键类

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（Technical Approach/ADR/Data Flow/File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式） |

## 根因铁证

```
Abort message: 'JNI DETECTED ERROR IN APPLICATION: java_class == null
    in call to GetStaticMethodID
    from java.lang.String java.lang.Runtime.nativeLoad(java.lang.String, java.lang.ClassLoader, java.lang.Class)'

#06 pc 000000000045f118  /data/data/io.legado.miss.app.release/app_cronet/arm64-v8a/libcronet.150.0.7871.128.so
```

崩溃日志路径：`docs/issues/user/temp/20260731/001/extracted/logcat.txt`（9 次崩溃，全部同模式，时间 07:23:24 ~ 07:24:48）

## 影响范围

| 受影响项 | 说明 |
|---------|------|
| release 包 | 直接崩溃（SIGABRT），无法使用 |
| 测试包/共存包 | 不受影响（minifyEnabled=false，R8 不启用） |
| 视频订阅源 | 打开即崩溃（触发 cronetEngine lazy 初始化） |
| 视频嗅探 | Cronet 崩溃后降级 OkHttp，TLS 指纹被 CDN 拒绝 |
