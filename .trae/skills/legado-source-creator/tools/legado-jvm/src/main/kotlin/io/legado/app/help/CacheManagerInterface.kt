package io.legado.app.help

import io.legado.app.model.analyzeRule.QueryTTF

// 源码参照: app/src/main/java/io/legado/app/help/CacheManager.kt#L52-L154
// 简化说明: 从 CacheManager object 抽取接口，移除 @Keep/@JvmOverloads 注解 | 已知上限: 无 | 升级路径: 无

/**
 * 缓存管理接口
 * 对应源码 CacheManager object 的所有 public 方法签名
 */
interface CacheManagerInterface {

    /**
     * saveTime 单位为秒
     */
    fun put(key: String, value: Any, saveTime: Int = 0)

    fun putMemory(key: String, value: Any)

    //从内存中获取数据
    fun getFromMemory(key: String): Any?

    fun deleteMemory(key: String)

    fun get(key: String): String?

    fun get(key: String, onlyDisk: Boolean): String?

    fun getInt(key: String): Int?

    fun getLong(key: String): Long?

    fun getDouble(key: String): Double?

    fun getFloat(key: String): Float?

    fun getByteArray(key: String): ByteArray?

    fun putFile(key: String, value: String, saveTime: Int = 0)

    fun getFile(key: String): String?

    fun delete(key: String)

    fun put(key: String, queryTTF: QueryTTF)

    fun getQueryTTF(key: String): QueryTTF?
}
