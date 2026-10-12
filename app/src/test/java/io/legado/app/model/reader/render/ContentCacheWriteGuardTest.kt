package io.legado.app.model.reader.render

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

/**
 * 内容缓存写入稳定性边界单测（epub-md-rich-rendering 补充任务 S12 配对；AD-28⑥ / NFR-07①）。
 *
 * 覆盖「磁盘满：禁写并提示」的三段语义：
 * ① 写前空间判据（**未知容量不得阻断**、低于阈值禁写、payload 计入估算）；
 * ② 写失败分类（磁盘满/无权限 ⇒ `CacheWriteFailed`；其它**不误报**）；
 * ③ 用户提示去重（窗口内只提示一次，超窗可再提示）。
 */
class ContentCacheWriteGuardTest {

    @Test
    fun `写前空间判据——未知容量不阻断而低容量禁写`() {
        assertTrue("usableSpace 取不到（0）⇒ 视为未知，不得阻断缓存", ContentCacheWriteGuard.hasRoomForCache(0L, 1_000L))
        assertTrue("负值同属未知", ContentCacheWriteGuard.hasRoomForCache(-1L, 1_000L))
        assertFalse("仅剩 1 字节 ⇒ 禁写", ContentCacheWriteGuard.hasRoomForCache(1L, 1_000L))
        assertFalse(
            "恰好等于安全余量 ⇒ 禁写（判据为严格大于）",
            ContentCacheWriteGuard.hasRoomForCache(ContentCacheWriteGuard.MIN_FREE_BYTES, 0L)
        )
        assertTrue(
            "多 1 字节即可写",
            ContentCacheWriteGuard.hasRoomForCache(ContentCacheWriteGuard.MIN_FREE_BYTES + 1, 0L)
        )
    }

    @Test
    fun `写前空间判据——按上界把正文长度计入占用`() {
        // 100 字符 ⇒ 上界 300 字节：余量恰为 MIN 时禁写，多 1 字节才放行
        assertFalse(
            "余量被正文占用吃满 ⇒ 禁写",
            ContentCacheWriteGuard.hasRoomForCache(ContentCacheWriteGuard.MIN_FREE_BYTES + 300, 100L)
        )
        assertTrue(
            "余量仍高于阈值 ⇒ 放行",
            ContentCacheWriteGuard.hasRoomForCache(ContentCacheWriteGuard.MIN_FREE_BYTES + 301, 100L)
        )
        assertFalse("乱序负数长度按 0 处理（不放大占用）也应只看余量", ContentCacheWriteGuard.hasRoomForCache(1L, -5L))
    }

    @Test
    fun `写失败分类——磁盘满与拒绝写被识别为 CacheWriteFailed`() {
        listOf(
            "ENOSPC (No space left on device)",
            "write failed: ENOSPC",
            "Disk full",
            "Quota exceeded",
            "open failed: EACCES (Permission denied)",
            "Read-only file system"
        ).forEach { message ->
            val error = ContentCacheWriteGuard.classifyWriteFailure(IOException(message))
            assertTrue("『$message』应被识别为缓存写失败", error is ReaderError.CacheWriteFailed)
        }
    }

    @Test
    fun `写失败分类——其它异常不得误报`() {
        assertNull("空异常不得报", ContentCacheWriteGuard.classifyWriteFailure(null))
        assertNull("无文案不得报（不可靠识别则不误报）", ContentCacheWriteGuard.classifyWriteFailure(IOException()))
        assertNull("普通网络/IO 异常不得报", ContentCacheWriteGuard.classifyWriteFailure(IOException("Connection reset by peer")))
        assertNull("NPE 不得报", ContentCacheWriteGuard.classifyWriteFailure(NullPointerException("boom")))
    }

    @Test
    fun `写失败分类——消息携带原文便于诊断`() {
        val error = ContentCacheWriteGuard.classifyWriteFailure(IOException("ENOSPC (No space left on device)"))
        assertEquals(
            "必须把原始 errno 文案带进异常消息（真机定位靠它）",
            true,
            error?.message?.contains("No space left on device")
        )
    }

    @Test
    fun `用户提示去重——窗口内一次、超窗再提示`() {
        val t0 = 1_000L
        assertTrue("从未提示过 ⇒ 首次必提示", ContentCacheWriteGuard.shouldNotify(0L, t0))
        assertFalse("窗口内不得重复提示", ContentCacheWriteGuard.shouldNotify(t0, t0 + ContentCacheWriteGuard.NOTIFY_DEDUPE_MS - 1))
        assertTrue("达到窗口即可再提示", ContentCacheWriteGuard.shouldNotify(t0, t0 + ContentCacheWriteGuard.NOTIFY_DEDUPE_MS))
    }
}