package io.legado.app.help

import io.legado.app.model.analyzeRule.QueryTTF
import java.lang.ref.SoftReference
import java.util.Collections
import java.util.LinkedHashMap
import java.util.concurrent.ConcurrentHashMap

// 源码参照: app/src/main/java/io/legado/app/help/CacheManager.kt#L52-L154
// 简化说明: 使用 ConcurrentHashMap+SoftReference 替代 LruCache+Room+ACache，无持久化 | 已知上限: 重启后缓存丢失，SoftReference 在内存不足时被 GC 回收 | 升级路径: 接入 SQLite 或文件系统

/**
 * 缓存管理 Stub 实现
 * 使用内存 Map+SoftReference 替代 Room 数据库和 ACache 文件缓存
 * SoftReference 防止 OOM，queryTTFMap 对齐真机 LruCache 上限4
 */
object CacheManagerStub : CacheManagerInterface {

    private data class PersistentEntry(val value: String, val deadline: Long)

    // 内存缓存（对应源码 memoryLruCache），SoftReference 防止 OOM
    private val memoryCache = ConcurrentHashMap<String, SoftReference<Any>>()

    // 持久缓存（对应源码 appDb.cacheDao）
    private val diskCache = ConcurrentHashMap<String, SoftReference<PersistentEntry>>()

    // 字节数组缓存（对应源码 ACache.getAsBinary）
    private val byteArrayCache = ConcurrentHashMap<String, SoftReference<ByteArray>>()

    // 文件缓存（对应源码 ACache.getAsString）
    private val fileCache = ConcurrentHashMap<String, SoftReference<String>>()

    // QueryTTF 缓存（对应源码 queryTTFMap，LruCache 上限4）
    private val queryTTFMap = Collections.synchronizedMap(
        object : LinkedHashMap<String, QueryTTF>(8, 0.75f, true) {
            override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, QueryTTF>?): Boolean {
                return size > 4
            }
        }
    )

    override fun put(key: String, value: Any, saveTime: Int) {
        val deadline = if (saveTime == 0) 0L else System.currentTimeMillis() + saveTime * 1000
        when (value) {
            is ByteArray -> byteArrayCache[key] = SoftReference(value)
            else -> {
                val valueStr = value.toString()
                putMemory(key, valueStr)
                diskCache[key] = SoftReference(PersistentEntry(valueStr, deadline))
            }
        }
    }

    override fun putMemory(key: String, value: Any) {
        memoryCache[key] = SoftReference(value)
    }

    override fun getFromMemory(key: String): Any? {
        val ref = memoryCache[key] ?: return null
        val value = ref.get()
        if (value == null) {
            memoryCache.remove(key)
        }
        return value
    }

    override fun deleteMemory(key: String) {
        memoryCache.remove(key)
    }

    override fun get(key: String): String? {
        getFromMemory(key)?.let {
            if (it is String) return it
        }
        val ref = diskCache[key] ?: return null
        val entry = ref.get()
        if (entry == null) {
            diskCache.remove(key)
            return null
        }
        if (entry.deadline == 0L || entry.deadline > System.currentTimeMillis()) {
            return entry.value.also {
                putMemory(key, it)
            }
        }
        diskCache.remove(key)
        return null
    }

    override fun get(key: String, onlyDisk: Boolean): String? {
        if (!onlyDisk) {
            return get(key)
        }
        val ref = diskCache[key] ?: return null
        val entry = ref.get()
        if (entry == null) {
            diskCache.remove(key)
            return null
        }
        if (entry.deadline == 0L || entry.deadline > System.currentTimeMillis()) {
            return entry.value
        }
        diskCache.remove(key)
        return null
    }

    override fun getInt(key: String): Int? {
        getFromMemory(key)?.let {
            if (it is Int) return it
        }
        return get(key, true)?.toIntOrNull()
    }

    override fun getLong(key: String): Long? {
        getFromMemory(key)?.let {
            if (it is Long) return it
        }
        return get(key, true)?.toLongOrNull()
    }

    override fun getDouble(key: String): Double? {
        getFromMemory(key)?.let {
            if (it is Double) return it
        }
        return get(key, true)?.toDoubleOrNull()
    }

    override fun getFloat(key: String): Float? {
        getFromMemory(key)?.let {
            if (it is Float) return it
        }
        return get(key, true)?.toFloatOrNull()
    }

    override fun getByteArray(key: String): ByteArray? {
        val ref = byteArrayCache[key] ?: return null
        val value = ref.get()
        if (value == null) {
            byteArrayCache.remove(key)
        }
        return value
    }

    override fun putFile(key: String, value: String, saveTime: Int) {
        fileCache[key] = SoftReference(value)
    }

    override fun getFile(key: String): String? {
        val ref = fileCache[key] ?: return null
        val value = ref.get()
        if (value == null) {
            fileCache.remove(key)
        }
        return value
    }

    override fun delete(key: String) {
        diskCache.remove(key)
        deleteMemory(key)
        byteArrayCache.remove(key)
        fileCache.remove(key)
    }

    override fun put(key: String, queryTTF: QueryTTF) {
        synchronized(queryTTFMap) {
            queryTTFMap[key] = queryTTF
        }
    }

    override fun getQueryTTF(key: String): QueryTTF? {
        synchronized(queryTTFMap) {
            return queryTTFMap[key]
        }
    }
}
