package io.legado.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 隔离沙箱进程判定（ng-js-source-port / quickjs-sandbox）。
 *
 * 回归背景（2026-10-22 真机）：`quickjs_sandbox` 隔离进程同样实例化 [App]，
 * 原实现无条件执行语言包装与宿主初始化 ⇒ ContextImpl 无 UserManager，
 * `getSharedPreferences` 抛 NPE，进程启动即 FATAL，宿主侧绑定 5s 超时（BIND_TIMEOUT）。
 * 判定必须对「主进程」返回 false（否则会跳过全部初始化，App 直接不可用）。
 */
class IsolatedSandboxProcessTest {

    @Test
    fun sandboxProcessIsDetected() {
        assertTrue(isIsolatedSandboxProcess("io.legado.miss.app.debug:quickjs_sandbox"))
        assertTrue("带子后缀同样属于沙箱进程", isIsolatedSandboxProcess("io.legado:quickjs_sandbox:worker"))
    }

    @Test
    fun mainProcessIsNotSandbox() {
        assertFalse(isIsolatedSandboxProcess("io.legado.miss.app.debug"))
        assertFalse(isIsolatedSandboxProcess("io.legado.miss.app.debug:web"))
        assertFalse(isIsolatedSandboxProcess(null))
    }
}
