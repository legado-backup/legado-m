package io.legado.app.help.storage

import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.joinAll
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R9 备份/恢复跨流程共享锁单测。
 *
 * 覆盖：
 * 1. 并发时临界区串行（备份等待恢复，而非并发清空工作目录）
 * 2. 临界区抛异常后锁被释放（不会永久占用）
 * 3. 锁不可重入 —— 嵌套申请会挂起（用超时断言，防真实死锁把测试挂死）
 */
class BackupRestoreLockTest {

    @Test
    fun withStorageLock_serializesCriticalSections() = runBlocking {
        val order = mutableListOf<String>()
        val first = launch {
            BackupRestoreLock.withStorageLock {
                order.add("a-start")
                delay(100)
                order.add("a-end")
            }
        }
        val second = launch {
            delay(10)
            BackupRestoreLock.withStorageLock {
                order.add("b-start")
                order.add("b-end")
            }
        }
        joinAll(first, second)
        assertEquals(
            listOf("a-start", "a-end", "b-start", "b-end"),
            order
        )
    }

    @Test
    fun withStorageLock_exceptionReleasesLock() = runBlocking {
        runCatching {
            BackupRestoreLock.withStorageLock { error("boom") }
        }
        // 锁已释放：再次申请应在超时内立即获得（不被永久占用）
        var acquired = false
        withTimeout(1_000) {
            BackupRestoreLock.withStorageLock { acquired = true }
        }
        assertTrue("异常后锁未释放", acquired)
    }

    @Test
    fun withStorageLock_isNotReentrant_nestedCallTimesOut() = runBlocking {
        var timedOut = false
        BackupRestoreLock.withStorageLock {
            try {
                withTimeout(150) {
                    // 嵌套申请同一把锁：Mutex 不可重入，此调用应一直挂起
                    BackupRestoreLock.withStorageLock { }
                }
                throw AssertionError("嵌套申请未被阻塞，锁实现可能可重入")
            } catch (_: TimeoutCancellationException) {
                timedOut = true
            }
        }
        assertTrue("嵌套申请未按预期挂起（不可重入约束失效）", timedOut)
    }
}