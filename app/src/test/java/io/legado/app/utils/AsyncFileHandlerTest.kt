package io.legado.app.utils

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.util.logging.Level
import java.util.logging.LogRecord
import java.util.logging.SimpleFormatter

/**
 * core-flow-test-coverage 批次 6（PERF-1）—— 日志文件写盘行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 背景：`AsyncFileHandler.publish` 把落盘任务提交到执行器。本次改动把它从**业务队列**
 *（`globalExecutor`）迁到**日志队列**（`logExecutor`）—— 用例只断言**外部可观察行为**：
 * ①正常记录最终**真的写进文件**；②`null` 记录不写任何内容也不抛（`isLoggable(null)` 为 false）。
 */
class AsyncFileHandlerTest {

    private fun pollUpTo(timeoutMs: Long, cond: () -> Boolean): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            if (cond()) return true
            Thread.sleep(50)
        }
        return cond()
    }

    @Test
    fun publish_writesRecordToFile() {
        val dir = Files.createTempDirectory("async-file-handler").toFile()
        val handler = AsyncFileHandler(dir.path + "/log-%g.txt")
        handler.formatter = SimpleFormatter()
        try {
            handler.publish(LogRecord(Level.INFO, MARKER))
            val hit = pollUpTo(5000) { anyNonEmptyFile(dir) }
            assertTrue("日志记录应被异步写入磁盘文件", hit)
        } finally {
            runCatching { handler.close() }
            dir.deleteRecursively()
        }
    }

    @Test
    fun publish_nullRecord_writesNothing() {
        val dir = Files.createTempDirectory("async-file-handler-null").toFile()
        val handler = AsyncFileHandler(dir.path + "/log-%g.txt")
        try {
            handler.publish(null)
            Thread.sleep(300)   // 给异步路径留出（不应发生的）写入时间
            assertFalse("null 记录不应写入任何内容", anyNonEmptyFile(dir))
        } finally {
            runCatching { handler.close() }
            dir.deleteRecursively()
        }
    }

    /** 目录内是否存在**非空**文件（`FileHandler` 构造期会建空文件，故以长度判定） */
    private fun anyNonEmptyFile(dir: java.io.File): Boolean =
        dir.listFiles()?.any { it.isFile && it.length() > 0 } == true

    private companion object {
        const val MARKER = "async-file-handler-marker"
    }
}
