package io.legado.app.web

import io.legado.app.web.TokenManager.Level

/**
 * 调试支路的**纯判定**（design AD-03 / tasks 2.1；无 Android 依赖，便于 JVM 单测）。
 *
 * 三条件**全部满足**才授予 `MANAGE`，任一不满足一律返回 `null`（调用方回落既有三级令牌校验）：
 *  1. 支路开关开启（可关闭，见 `PreferKey.webAuthDebugBranch`）；
 *  2. 携带的凭据等于**该变体期望的固定值**（release 变体不提供期望值 ⇒ 恒 `null`）；
 *  3. **连接层来源为回环**（`IHTTPSession.remoteIpAddress`，**非请求头** ⇒ 不可伪造）。
 *
 * 为什么不看请求头：`X-Forwarded-For` / `Host` 等均可被同机进程伪造，
 * 只有连接层来源 + 服务端绑定回环才是不可伪造的约束（AD-03 第 2 条）。
 *
 * 独立成纯函数的意义：本类是「授予最高权限」的分支，必须能被逐条断言覆盖
 * （三条件各自的否定分支 + 全满足分支），不能只靠集成测试。
 */
internal fun decideDebugBranchLevel(
    enabled: Boolean,
    suppliedToken: String?,
    clientIp: String?,
    expectedToken: String,
): Level? {
    if (!enabled) return null
    if (expectedToken.isEmpty()) return null
    val supplied = suppliedToken?.trim().orEmpty()
    if (supplied.isEmpty() || supplied != expectedToken) return null
    if (!isLoopbackAddress(clientIp)) return null
    return Level.MANAGE
}

/** 连接层来源是否回环（IPv4 / IPv6 环回与 localhost）。 */
internal fun isLoopbackAddress(ip: String?): Boolean {
    val v = ip?.trim().orEmpty()
    if (v.isEmpty()) return false
    return v == "127.0.0.1" ||
        v == "::1" ||
        v == "0:0:0:0:0:0:0:1" ||
        v == "localhost" ||
        v.startsWith("127.")
}