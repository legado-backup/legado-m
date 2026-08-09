package io.legado.app.ui.book.cache

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File

class CacheStorageStatsTest {

    private lateinit var tempDir: File

    @Before
    fun setUp() {
        tempDir = File(System.getProperty("java.io.tmpdir"), "legado_cache_stats_test_${System.nanoTime()}")
        tempDir.mkdirs()
    }

    @After
    fun tearDown() {
        tempDir.deleteRecursively()
    }

    @Test
    fun directorySize_returnsZero_forMissing() {
        assertEquals(0L, directorySize(File(tempDir, "not_exist")))
    }

    @Test
    fun directorySize_sumsRecursively() {
        val sub = File(tempDir, "sub")
        sub.mkdirs()
        val a = File(tempDir, "a.bin")
        val b = File(sub, "b.bin")
        a.writeBytes(ByteArray(100))
        b.writeBytes(ByteArray(150))
        assertEquals(250L, directorySize(tempDir))
    }

    @Test
    fun directorySize_returnsFileLength_forSingleFile() {
        val f = File(tempDir, "single.bin")
        f.writeBytes(ByteArray(77))
        assertEquals(77L, directorySize(f))
    }

    @Test
    fun directorySize_emptyDir_returnsZero() {
        val empty = File(tempDir, "empty")
        empty.mkdirs()
        assertEquals(0L, directorySize(empty))
    }

    @Test
    fun formatBytes_units() {
        assertEquals("512 B", formatBytes(512))
        assertEquals("1.5 KB", formatBytes(1536))
        assertEquals("2.00 MB", formatBytes(2 * 1024 * 1024))
        assertEquals("1.00 GB", formatBytes(1024L * 1024 * 1024))
    }

    @Test
    fun formatBytes_zero() {
        assertEquals("0 B", formatBytes(0))
    }
}
