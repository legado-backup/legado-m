package io.legado.app.web

import fi.iki.elonen.NanoHTTPD
import io.legado.app.constant.PreferKey
import io.legado.app.utils.getPrefBoolean
import splitties.init.appCtx

/**
 * Web 鉴权「调试卷支路」—— **debug 变体实现**（design AD-03 / tasks 2.1~2.5）。
 *
 * 机制同 [io.legado.app.DebugAppHook]（决策 #24）：**按变体拆 sourceSet** ——
 * 本文件在 `src/debug/`，`src/release/` 有同名空实现，`src/main` **不放该符号**
 * ⇒ 每个变体恰好拿到一份，不触发 `Redeclaration`；`src/main` 的 `WebAuth` 可正常引用。
 *
 * 安全边界（三条件，见 [decideDebugBranchLevel]）：
 *  1. **内腿绑定回环**（`McpDebugService` 以 `127.0.0.1` 启动）⇒ 局域网/外网物理不可达；
 *  2. **debug 变体专属**（release 恒 `null`）；
 *  3. **固定值匹配**（仅开发者本机已知；不打印、不入库到版本库）。
 * 任一不满足 ⇒ 完全回落既有三级令牌校验，行为与改造前一致。
 *
 * 残余风险与缓解：debug 包在本机被同机进程读到固定值的风险由「仅回环 + 可关闭开关」缓解
 * （关闭开关后即使三条件满足也回落，见 [isEnabled]）。
 */
object WebAuthDebugBranch {

    /**
     * 开发者本机固定凭据（**仅 debug 变体存在**；release 面无此常量，门禁可 grep 校验）。
     * 与用户主令牌体系（`TokenManager`）无关，避免两套凭据耦合。
     */
    private const val FIXED_TOKEN = "9f2c7a41d8b34e6f90c5a2e7b18d4f63"

    /** 支路开关（`PreferKey.webAuthDebugBranch`，默认开启；关闭后完全回落三级令牌校验）。 */
    fun isEnabled(): Boolean =
        runCatching { appCtx.getPrefBoolean(PreferKey.webAuthDebugBranch, true) }.getOrDefault(true)

    /**
     * 本变体**是否具备**调试卷支路能力（与 [isEnabled] 的「开关开没开」是两件事）。
     *
     * 用途：设置页据此决定是否渲染「调试通道」卡片 —— release 面恒 `false` ⇒ 正式包**看不到**
     * 任何调试入口（新增符号不泄漏到 release，tasks 5.5.2）。
     */
    fun isAvailable(): Boolean = true

    /**
     * 凭据**掩码**（供 App 内「一键初始化」卡片展示，见 spec B-6）。
     *
     * 只暴露前 2 位与长度 ⇒ 用户能确认"用的是哪一份凭据"，同时不把明文留在界面上。
     * release 面无凭据 ⇒ 恒空串。
     */
    fun maskedToken(): String = "${FIXED_TOKEN.take(2)}***<len=${FIXED_TOKEN.length}>"

    /**
     * 三条件判定：满足返回 [TokenManager.Level.MANAGE]，否则 `null`（调用方回落）。
     *
     * 注意：来源判定取 **`session.remoteIpAddress`（连接层）**，**不读任何请求头**。
     */
    fun match(session: NanoHTTPD.IHTTPSession, token: String?): TokenManager.Level? =
        decideDebugBranchLevel(
            enabled = isEnabled(),
            suppliedToken = token,
            clientIp = session.remoteIpAddress,
            expectedToken = FIXED_TOKEN,
        )
}