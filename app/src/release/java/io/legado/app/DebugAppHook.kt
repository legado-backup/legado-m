package io.legado.app

/**
 * App 启动钩子 —— **release 变体空实现**（web-mcp-productization 二期 · tasks 5.1）。
 *
 * release 面没有 MCP 内腿（`McpDebugService` 只在 debug sourceSet 存在）⇒ 此处无操作。
 * 与 `src/debug/java/io/legado/app/DebugAppHook.kt` 成对（按变体拆 sourceSet，见决策 #24）。
 */
object DebugAppHook {

    /** release 无内腿服务：空实现。 */
    fun onAppCreate() {
        // no-op
    }

    /** release 无内腿服务 ⇒ 一键初始化不可用（恒 false）。 */
    fun startLeg(): Boolean = false

    /** release 无内腿服务 ⇒ 永不就绪。 */
    fun isLegRunning(): Boolean = false

    /** release 无内腿服务 ⇒ 不探测（恒 false，且不做任何网络动作）。 */
    fun probeLeg(timeoutMs: Int = 200): Boolean = false

    /** release 无内腿服务 ⇒ 无监听地址。 */
    fun legAddress(): String = ""
}