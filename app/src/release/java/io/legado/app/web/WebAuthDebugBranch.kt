package io.legado.app.web

import fi.iki.elonen.NanoHTTPD

/**
 * Web 鉴权「调试卷支路」—— **release 变体空实现**（design AD-03 / tasks 2.2）。
 *
 * release 面**不存在**调试支路：`isEnabled()` 恒 `false`，`match(...)` 恒 `null`
 * ⇒ `WebAuth.verify` 只走既有三级令牌校验，行为与改造前**逐字节等价**；
 * 且本文件**不含任何固定凭据常量**（可由门禁 grep 校验）。
 *
 * 与 `src/debug/java/io/legado/app/web/WebAuthDebugBranch.kt` 成对（按变体拆 sourceSet）。
 */
object WebAuthDebugBranch {

    /** release 无调试支路：恒关闭。 */
    fun isEnabled(): Boolean = false

    /** release 面**不具备**调试卷支路能力 ⇒ 设置页不渲染调试通道卡片。 */
    fun isAvailable(): Boolean = false

    /** release 无调试支路：恒不匹配（调用方回落三级令牌校验）。 */
    fun match(session: NanoHTTPD.IHTTPSession, token: String?): TokenManager.Level? = null
}