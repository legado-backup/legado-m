package io.legado.app.help.storage

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * core-flow-test-coverage tasks 10.1 / design.md §十 #16 —— 【BUG-3】数据丢失回归守护。
 *
 * 辞晨以 `fbc0492` 修复的「`Backup.clearCache` 与进行中备份竞争 ⇒ ZIP 静默丢文件」缺陷，
 * 我方**同存**：[Backup.kt:736] `fun clearCache()` **不持锁**清空 `backupPath`/`zipFilePath`，
 * 却在 [App.kt:201] 启动期被调用；而备份主流程 `backupLocked`([:375]) 持 `withStorageLock`
 * 在同一目录写入 ⇒ 二者竞争即丢文件。
 * [BackupRestoreLock] KDoc 亦明定铁律：「所有『清空 / 写入 backupPath』的入口必须经 withStorageLock」。
 *
 * 【AD-02 例外（如实标注）】`Backup.backupPath`/`zipFilePath` 依赖 `appCtx`（Android），
 * 纯 JVM 无法构造并发场景 ⇒ 以**源码文本探针**守护；
 * `clearCache_acquiresStorageLock...` 在修复前为**红**，修复后转绿。
 */
class BackupClearCacheLockTest {

    private val source = SourceFileProbe.sourceText("help/storage/Backup.kt")

    /** `clearCache` 是文件末个函数 ⇒ 取其后的剩余文本即为函数体。 */
    private fun clearCacheBody(): String = source.substringAfter("fun clearCache()")

    @Test
    fun clearCache_acquiresStorageLock_soItCannotRaceOngoingBackup() {
        assertTrue(
            "clearCache() 必须经 withStorageLock 与备份/恢复互斥（否则与进行中备份竞争丢文件）",
            clearCacheBody().contains("withStorageLock")
        )
    }

    @Test
    fun clearCache_isSuspendOrNonBlockingOnMainThread() {
        // 与备份互斥需 suspend（Mutex 不可在非挂起上下文锁定）
        assertTrue(
            "clearCache() 应为 suspend（Mutex 锁需要挂起上下文）",
            source.contains("suspend fun clearCache()")
        )
    }
}
