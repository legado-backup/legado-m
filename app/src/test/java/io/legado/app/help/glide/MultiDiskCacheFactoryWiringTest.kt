package io.legado.app.help.glide

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R19 接线不变量。
 *
 * 守的是**分区落点**与**请求侧标记**——两者缺一，"双区"就退化成单区：
 * - 封面区必须在 `filesDir`（清缓存清的是 `cacheDir`）⇒ 否则「清缓存后断网无封面」；
 * - 普通区必须在 `cacheDir`（随清缓存释放）⇒ 否则临时图会把持久区撑满；
 * - 封面请求必须带签名 ⇒ 否则所有图都落临时区；
 * - 磁盘缓存必须挂上双区工厂（且不再残留单区工厂）；
 * - 总量口径不缩水（改造前单区 1000MB ⇒ 双区合计仍 1000MB）。
 */
class MultiDiskCacheFactoryWiringTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun zonesArePlacedOnPersistentAndTemporaryDirs() {
        val factory = code("help/glide/MultiDiskCacheFactory.kt")
        assertTrue(
            "封面区必须落 filesDir（清缓存不影响）",
            factory.contains("File(context.filesDir, COVER_DIR_NAME)")
        )
        assertTrue(
            "普通区必须落 cacheDir（随清缓存释放）",
            factory.contains("InternalCacheDiskCacheFactory(context, COMMON_DIR_NAME, COMMON_MAX_BYTES)")
        )
        assertEquals("cover_disk_cache", MultiDiskCacheFactory.COVER_DIR_NAME)
        assertEquals("common_disk_cache", MultiDiskCacheFactory.COMMON_DIR_NAME)
    }

    /** 总量口径：改造前单区 1000MB ⇒ 双区合计不得缩水（也不得暗中翻倍）。 */
    @Test
    fun totalBudget_matchesLegacySingleZone() {
        assertEquals(1024L * 1024 * 1024, MultiDiskCacheFactory.COVER_MAX_BYTES + MultiDiskCacheFactory.COMMON_MAX_BYTES)
    }

    @Test
    fun glideModuleUsesMultiZoneFactory() {
        val module = code("help/glide/LegadoGlideModule.kt")
        assertTrue("必须挂双区工厂", module.contains("builder.setDiskCache(MultiDiskCacheFactory(context))"))
        assertTrue(
            "不得残留单区工厂（否则双区形同虚设）",
            !module.contains("setDiskCache(InternalCacheDiskCacheFactory(")
        )
    }

    @Test
    fun coverRequestCarriesMarkerSignature() {
        val cover = code("model/BookCover.kt")
        assertTrue(
            "封面请求必须带标记签名（否则落进临时区，清缓存即丢）",
            cover.contains(".signature(CoverDiskCacheMarker.SIGNATURE)")
        )
    }

    /** 清缓存语义：`clear()` 只清临时区（封面持久区的唯一保全点）。 */
    @Test
    fun clearSemantics_onlyClearsCommonZone() {
        val factory = code("help/glide/MultiDiskCacheFactory.kt")
        assertTrue("clear() 必须只清临时区", factory.contains("commonCache.clear()"))
        assertTrue("全清必须另设显式入口", factory.contains("fun clearAll()"))
        assertTrue(
            "clearAll 必须两个区都清",
            factory.contains("coverCache.clear()")
        )
    }

    /**
     * 双区落点必须有**正式诊断日志**（真机排查「封面重下」时的唯一可观测证据）。
     *
     * 口径：`AppLog.putDebugWithTag` + 专用 tag（属正式诊断日志，禁止当临时日志清理）。
     */
    @Test
    fun zoneBuildIsDiagnosable() {
        val factory = code("help/glide/MultiDiskCacheFactory.kt")
        assertTrue("必须用统一日志通道", factory.contains("AppLog.putDebugWithTag("))
        assertTrue("tag 必须是专用常量", factory.contains("const val TAG = \"CoverDiskCache\""))
        assertTrue("日志必须同时报出两个区的落点", factory.contains("双区磁盘缓存就绪"))
    }
}