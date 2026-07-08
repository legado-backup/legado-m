package io.legado.app.help.coroutine

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Coroutine 链式协程 CancellationException 守卫单元测试
 *
 * 验证点：协程被取消时，CancellationException 必须被透传，不应触发 error 回调。
 * 对照点：普通异常仍应正常触发 error 回调；正常完成仍应触发 success 回调。
 *
 * 使用 CoroutineStart.LAZY 确保回调注册后再启动协程，规避"协程太快完成回调不执行"问题。
 * 已知上限：使用 Dispatchers.Unconfined 规避 Android Main Dispatcher 依赖 | 升级路径：引入 kotlinx-coroutines-test 用 runTest 替代 runBlocking
 */
class CoroutineTest {

    @Test
    fun cancellation_doesNotTriggerErrorCallback() = runBlocking {
        val scope = CoroutineScope(Dispatchers.Unconfined)
        var errorCalled = false

        val job = Coroutine.async<String>(
            scope = scope,
            context = Dispatchers.Unconfined,
            start = CoroutineStart.LAZY,
            executeContext = Dispatchers.Unconfined
        ) {
            delay(1000L)
            "result"
        }.onError {
            errorCalled = true
        }

        job.start()
        delay(100L)
        job.cancel()
        delay(300L)
        scope.cancel()

        assertFalse("协程取消不应触发 error 回调", errorCalled)
    }

    @Test
    fun normalException_triggersErrorCallback() = runBlocking {
        val scope = CoroutineScope(Dispatchers.Unconfined)
        var errorCalled = false

        val job = Coroutine.async<String>(
            scope = scope,
            context = Dispatchers.Unconfined,
            start = CoroutineStart.LAZY,
            executeContext = Dispatchers.Unconfined
        ) {
            throw RuntimeException("test error")
        }.onError {
            errorCalled = true
        }

        job.start()
        delay(300L)
        scope.cancel()

        assertTrue("普通异常应触发 error 回调", errorCalled)
    }

    @Test
    fun successfulCompletion_triggersSuccessCallback() = runBlocking {
        val scope = CoroutineScope(Dispatchers.Unconfined)
        var successCalled = false

        val job = Coroutine.async<String>(
            scope = scope,
            context = Dispatchers.Unconfined,
            start = CoroutineStart.LAZY,
            executeContext = Dispatchers.Unconfined
        ) {
            "result"
        }.onSuccess {
            successCalled = true
        }

        job.start()
        delay(300L)
        scope.cancel()

        assertTrue("正常完成应触发 success 回调", successCalled)
    }
}
