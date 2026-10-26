package io.legado.app

import io.legado.app.service.McpDebugService

/**
 * App 启动钩子 —— **debug 变体实现**（web-mcp-productization 二期 · tasks 5.1）。
 *
 * 机制同 `DebugToolProvider`（决策 #24）：**按变体拆 sourceSet** —— 本文件在 `src/debug/`，
 * `src/release/` 有同名空实现，`src/main` **不放**该符号 ⇒ 每个变体恰好拿到一份，
 * 不会触发 `Redeclaration`（Android sourceSet 覆盖对**类**无效的已知陷阱）。
 *
 * 用途：App 启动时自动拉起 MCP 内腿服务（8765），开发者 AI 经 `adb reverse` 即可直连，
 * 无需手工 `am startservice`。
 */
object DebugAppHook {

    /** App `onCreate` 时调用（幂等）。 */
    fun onAppCreate() {
        McpDebugService.start()
    }

    /**
     * App 内「一键初始化」入口用：启动内腿并回报**当前**是否已就绪（幂等）。
     *
     * 注意：首次 `start()` 是异步的（服务 `onCreate` 把 server 启动投递到 IO 线程），
     * 因此这里可能仍返回 `false` —— 调用方应稍后再查 [isLegRunning] 刷新界面。
     */
    fun startLeg(): Boolean {
        McpDebugService.start()
        return McpDebugService.isRun
    }

    /** 内腿是否已就绪（同进程快速判定；跨进程/时序不准时用 [probeLeg] 实测校正）。 */
    fun isLegRunning(): Boolean = McpDebugService.isRun

    /**
     * **实测**内腿是否在监听回环端口（真机实测：同进程静态标记在部分时序下读到 `false`，
     * 而端口实际已在监听 ⇒ 界面状态以本函数为准，避免"服务已起却显示正在启动"）。
     *
     * 只能在工作线程调用（会做一次本机 TCP 连接）。
     */
    fun probeLeg(timeoutMs: Int = 200): Boolean = try {
        java.net.Socket().use { socket ->
            socket.connect(java.net.InetSocketAddress(McpDebugService.LOOPBACK_HOST, McpDebugService.PORT), timeoutMs)
            true
        }
    } catch (e: Throwable) {
        false
    }

    /** 内腿监听地址（供界面展示连接方式；不含凭据）。 */
    fun legAddress(): String = McpDebugService.listenAddress
}