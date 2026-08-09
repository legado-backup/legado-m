package io.legado.app.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * DownloadState 内存单例纯 JVM 单测（precise-manage）
 *
 * 已知上限：cancelDownload/queryAllTaskStatus 依赖系统 DownloadManager
 * （splitties `downloadManager`），纯 JVM 无法获取，留待真机（tasks 5.7 真机项）。
 * 此处的 addTask/updateTask/removeTask/clear 为纯内存 StateFlow 操作，可安全单测。
 */
class DownloadStateTest {

    @Test
    fun addTask_createsWaitingTask() {
        DownloadState.clear()
        DownloadState.addTask(1L, "https://example.com/book.zip", "book.zip", 1000L)

        val task = DownloadState.tasks.value[1L]
        assertEquals("https://example.com/book.zip", task?.url)
        assertEquals("book.zip", task?.fileName)
        assertEquals(DownloadStatus.WAITING, task?.status)
        assertEquals(0, task?.progress)
    }

    @Test
    fun updateTask_recordsDownloadedBytes() {
        DownloadState.clear()
        DownloadState.addTask(2L, "https://example.com/a.txt", "a.txt", 1000L)

        DownloadState.updateTask(2L, progress = 50, totalSize = 100, downloadedSize = 50)
        val task = DownloadState.tasks.value[2L]
        assertEquals(50, task?.progress)
        assertEquals(100, task?.totalSize)
        assertEquals(50, task?.downloadedSize)
    }

    @Test
    fun updateTask_unknownId_ignored() {
        DownloadState.clear()
        DownloadState.updateTask(999L, progress = 10)
        assertTrue(DownloadState.tasks.value.isEmpty())
    }

    @Test
    fun updateTask_statusUpdateKeepsFields() {
        DownloadState.clear()
        DownloadState.addTask(3L, "https://example.com/c.bin", "c.bin", 1000L)
        DownloadState.updateTask(3L, status = DownloadStatus.RUNNING)
        val task = DownloadState.tasks.value[3L]
        assertEquals(DownloadStatus.RUNNING, task?.status)
        assertEquals("c.bin", task?.fileName)
    }

    @Test
    fun removeTask_removesFromFlow() {
        DownloadState.clear()
        DownloadState.addTask(4L, "https://example.com/d.apk", "d.apk", 1000L)
        DownloadState.removeTask(4L)
        assertTrue(DownloadState.tasks.value.isEmpty())
    }

    @Test
    fun clear_emptiesFlow() {
        DownloadState.clear()
        DownloadState.addTask(5L, "https://example.com/e", "e", 1000L)
        DownloadState.addTask(6L, "https://example.com/f", "f", 2000L)
        assertEquals(2, DownloadState.tasks.value.size)
        DownloadState.clear()
        assertTrue(DownloadState.tasks.value.isEmpty())
    }
}