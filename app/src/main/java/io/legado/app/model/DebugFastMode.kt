package io.legado.app.model

/**
 * 调试快速模式策略（纯函数 + 会话门控单点）。
 *
 * 背景（2026-10-27 用户反馈）：调试时并发解析会让日志顺序交错、同一列表项信息重复；
 * 目标是在**调试会话内**收敛为「并发 1 + 只取首页 + 只取首条」，生产行为保持不变。
 *
 * 门控由 [Debug.isDebugSessionFor] 提供（`debugRunning + debugSource`）：
 * 调试结束/取消后立即失效，不会影响随后的试播或正常阅读。
 */
object DebugFastMode {

    /** 当前源是否处于进行中的调试会话。 */
    fun enabled(sourceUrl: String?): Boolean = Debug.isDebugSessionFor(sourceUrl)

    /** 解析并发：调试时固定 1，否则沿用调用方配置。 */
    fun parseConcurrency(configured: Int, fast: Boolean): Int = if (fast) 1 else configured

    /** 条目上限：调试时只取首条（0 条仍为 0），否则不限。 */
    fun itemLimit(count: Int, fast: Boolean): Int = if (fast) minOf(1, count) else count

    /** 是否允许分页：调试时禁用（只解析首页）。 */
    fun paginationEnabled(fast: Boolean): Boolean = !fast

    /** 调试开始时打一条说明，避免用户误判「源只有 1 条」。 */
    fun logFastMode(sourceUrl: String?) {
        if (enabled(sourceUrl)) {
            Debug.log(sourceUrl, "◇调试快速模式：解析并发=1，仅首页/首条（生产行为不变）")
        }
    }
}
