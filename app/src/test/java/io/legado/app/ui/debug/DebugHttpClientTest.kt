package io.legado.app.ui.debug

import org.junit.Assert.assertSame
import org.junit.Test

/**
 * 调试屏共用客户端行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 断言"同一性"：反复取用必须是**同一个实例**（连同其连接池/线程池）。若有人把它改回
 * `get() = OkHttpClient.Builder().build()`（即每次调用新建），本用例即失败 —— 那正是本次
 * 修复要防的回退（每次进入调试屏新建线程池 + 连接池且旧的不回收）。
 */
class DebugHttpClientTest {

    @Test
    fun repeatedAccess_returnsSameClientInstance() {
        assertSame(debugHttpClient, debugHttpClient)
    }

    @Test
    fun repeatedAccess_returnsSameConnectionPoolAndDispatcher() {
        assertSame(debugHttpClient.connectionPool, debugHttpClient.connectionPool)
        assertSame(debugHttpClient.dispatcher, debugHttpClient.dispatcher)
    }
}
