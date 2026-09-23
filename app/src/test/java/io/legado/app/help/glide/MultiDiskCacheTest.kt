package io.legado.app.help.glide

import com.bumptech.glide.load.Key
import com.bumptech.glide.load.engine.cache.DiskCache
import com.bumptech.glide.signature.ObjectKey
import java.io.File
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R19「封面双区磁盘缓存」单测。
 *
 * 验收口径（tasks §4.3）：**清缓存（清临时区）后封面仍在**；非封面图清理不影响封面；
 * 以及封面路由判据本身可用（不依赖 Glide 内部实现，用 ObjectKey 的真实 toString 校验）。
 */
class MultiDiskCacheTest {

    private class FakeDiskCache : DiskCache {
        val stored = LinkedHashMap<Key, File>()
        var clearCount = 0
            private set

        override fun get(key: Key): File? = stored[key]

        override fun put(key: Key, writer: DiskCache.Writer) {
            stored[key] = File("fake-${stored.size}")
        }

        override fun delete(key: Key) {
            stored.remove(key)
        }

        override fun clear() {
            stored.clear()
            clearCount++
        }
    }

    private class FakeKey(private val id: String) : Key {
        override fun updateDiskCacheKey(messageDigest: MessageDigest) {
            messageDigest.update(id.toByteArray(Charsets.UTF_8))
        }

        override fun equals(other: Any?): Boolean = other is FakeKey && other.id == id

        override fun hashCode(): Int = id.hashCode()

        override fun toString(): String = id
    }

    private val coverKey = FakeKey("DataCacheKey{sourceKey=x, signature=ObjectKey{object=${CoverDiskCacheMarker.MARKER}}}")
    private val commonKey = FakeKey("DataCacheKey{sourceKey=y, signature=ObjectKey{object=legado:other}}")
    private val writer = DiskCache.Writer { true }

    private fun newPair(): Pair<MultiDiskCache, Pair<FakeDiskCache, FakeDiskCache>> {
        val cover = FakeDiskCache()
        val common = FakeDiskCache()
        return MultiDiskCache(cover, common) to (cover to common)
    }

    /** 路由：封面键落封面区，其余键落临时区。 */
    @Test
    fun routing_splitsCoverAndCommonKeys() {
        val (cache, zones) = newPair()
        val (cover, common) = zones
        cache.put(coverKey, writer)
        cache.put(commonKey, writer)
        assertEquals("封面键必须落封面区", 1, cover.stored.size)
        assertEquals("普通键必须落临时区", 1, common.stored.size)
        assertEquals(coverKey, cover.stored.keys.first())
        assertEquals(commonKey, common.stored.keys.first())
        assertTrue(cache.isCoverKey(coverKey))
        assertFalse(cache.isCoverKey(commonKey))
    }

    /** get/delete 必须与 put 同区（否则「写进封面区、删在临时区」会泄漏）。 */
    @Test
    fun getAndDelete_followSameZoneAsPut() {
        val (cache, zones) = newPair()
        val (cover, common) = zones
        cache.put(coverKey, writer)
        cache.put(commonKey, writer)
        assertTrue(cache.get(coverKey) != null)
        assertNull("临时区查封面键必须为空（防跨区误命中）", common.get(coverKey))
        cache.delete(coverKey)
        assertNull(cache.get(coverKey))
        assertEquals("删封面键不得动临时区", 1, common.stored.size)
    }

    /** R19 核心验收语义：**清缓存只清临时区**，封面持久区保留（断网仍可显示封面）。 */
    @Test
    fun clear_onlyClearsCommonZone_coverSurvives() {
        val (cache, zones) = newPair()
        val (cover, common) = zones
        cache.put(coverKey, writer)
        cache.put(commonKey, writer)
        cache.clear()
        assertEquals("临时区必须被清", 0, common.stored.size)
        assertEquals(1, common.clearCount)
        assertEquals("封面持久区不得被清", 1, cover.stored.size)
        assertEquals(0, cover.clearCount)
        assertTrue("清缓存后封面仍可命中", cache.get(coverKey) != null)
    }

    @Test
    fun clearAll_clearsBothZones() {
        val (cache, zones) = newPair()
        val (cover, common) = zones
        cache.put(coverKey, writer)
        cache.put(commonKey, writer)
        cache.clearAll()
        assertEquals(0, common.stored.size)
        assertEquals(0, cover.stored.size)
    }

    /**
     * 判据可用性（不依赖 Glide 内部实现）：真实 `ObjectKey(MARKER).toString()` 必须含标记串。
     *
     * 背景：Glide 未暴露「取请求签名」的 API，故路由靠键字符串包含标记；
     * 若 `ObjectKey` 的 toString 口径变化（升级 Glide），本断言会先失败并提醒。
     */
    @Test
    fun markerIsVisibleInRealObjectKeyToString() {
        val rendered = ObjectKey(CoverDiskCacheMarker.MARKER).toString()
        assertTrue("真实签名对象必须暴露标记串：$rendered", rendered.contains(CoverDiskCacheMarker.MARKER))
        assertFalse(CoverDiskCacheMarker.isCover(null))
        assertFalse(CoverDiskCacheMarker.isCover(FakeKey("no-marker-here")))
    }
}