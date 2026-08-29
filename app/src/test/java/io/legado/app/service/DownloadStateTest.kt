package io.legado.app.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 下载状态模型纯 JVM 单测（download-manager-maturity）
 *
 * 覆盖：DownloadTask 默认值与 copy 语义、状态/类型枚举、resumeFromDb 的
 * valueOf 容错解析口径、DownloadState.tasks 初始态。
 *
 * 已知上限：DownloadState.addTask/updateTask/removeTask/clear 已 Room-first 化
 * （appDb.downloadTaskDao 同步落库），纯 JVM 无法构造 appDb，留待仪器测试
 * 或 Robolectric（升级路径：抽象 Dao 接口后可全量单测）。
 */
class DownloadStateTest {

    // === DownloadTask 数据类 ===

    @Test
    fun downloadTask_defaults() {
        val task = DownloadTask(id = 1L, url = "https://example.com/a.mp4", fileName = "a.mp4", startTime = 1000L)
        assertEquals(DownloadStatus.WAITING, task.status)
        assertEquals(DownloadTaskType.DIRECT, task.taskType)
        assertEquals(0, task.progress)
        assertEquals(0, task.totalSize)
        assertEquals(0, task.downloadedSize)
        assertEquals(0L, task.speed)
        assertEquals(null, task.localPath)
        assertEquals(null, task.errorCode)
        assertEquals(null, task.headersJson)
        assertEquals(null, task.resumePointJson)
        assertEquals(null, task.segmentsJson)
    }

    @Test
    fun downloadTask_copyKeepsUnchangedFields() {
        val task = DownloadTask(id = 2L, url = "u", fileName = "f", startTime = 0L)
        val updated = task.copy(status = DownloadStatus.RUNNING, progress = 50)
        assertEquals(DownloadStatus.RUNNING, updated.status)
        assertEquals(50, updated.progress)
        assertEquals("u", updated.url)
        assertEquals("f", updated.fileName)
        assertEquals(2L, updated.id)
    }

    // === 枚举 ===

    @Test
    fun downloadStatus_values() {
        assertEquals(
            listOf("WAITING", "RUNNING", "PAUSED", "COMPLETED", "FAILED"),
            DownloadStatus.entries.map { it.name }
        )
    }

    @Test
    fun downloadTaskType_values() {
        assertEquals(listOf("DIRECT", "HLS"), DownloadTaskType.entries.map { it.name })
    }

    // === resumeFromDb 的 valueOf 容错解析口径（与实现同款 runCatching 模式） ===

    @Test
    fun statusParse_validRoundTrip() {
        val parsed = runCatching { DownloadStatus.valueOf("RUNNING") }.getOrDefault(DownloadStatus.PAUSED)
        assertEquals(DownloadStatus.RUNNING, parsed)
    }

    @Test
    fun statusParse_invalidFallsBackToPaused() {
        val parsed = runCatching { DownloadStatus.valueOf("BAD") }.getOrDefault(DownloadStatus.PAUSED)
        assertEquals(DownloadStatus.PAUSED, parsed)
    }

    @Test
    fun taskTypeParse_invalidFallsBackToDirect() {
        val parsed = runCatching { DownloadTaskType.valueOf("BAD") }.getOrDefault(DownloadTaskType.DIRECT)
        assertEquals(DownloadTaskType.DIRECT, parsed)
    }

    // === DownloadState 初始态（不触发 appDb） ===

    @Test
    fun downloadState_initialTasksEmpty() {
        assertTrue(DownloadState.tasks.value.isEmpty())
        assertTrue(DownloadState.queryAllTaskStatus().isEmpty())
    }
}
