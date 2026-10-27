package io.legado.app.help.exoplayer

import com.google.gson.reflect.TypeToken
import io.legado.app.constant.AppLog
import io.legado.app.utils.GSON
import splitties.init.appCtx
import java.io.File

/**
 * CENC 解密密钥来源抽象（设计 AD-03）。
 *
 * 播放层只认「kid(32 位 hex) -> 16 字节 key」，不关心 key 从何而来：
 * 生产默认实现为空/离线映射（未命中返回 null ⇒ 能力存在但不自动生效），
 * 研究轨可用 [MemoryKeyProvider] 或替换 [CencKeyStore.provider] 注入。
 *
 * 安全边界（AD-06）：key 禁止进入书源、日志、交付产物；日志只记录 kid 长度与命中与否。
 */
interface CencKeyProvider {

    /** @param kid 32 位 hex（大小写不敏感）；命中返回 16 字节 key，未命中返回 null */
    fun key(kid: String): ByteArray?
}

/**
 * 内存映射实现：研究轨/单测手工注入 key，进程退出即失效（不落盘、不进仓库）。
 */
class MemoryKeyProvider(keys: Map<String, ByteArray>) : CencKeyProvider {

    private val map: Map<String, ByteArray> = keys.mapKeys { it.key.trim().lowercase() }

    override fun key(kid: String): ByteArray? = map[kid.trim().lowercase()]
}

/**
 * 离线映射实现：[file] 为 JSON `{"<32位hex kid>":"<32位hex key>"}`。
 *
 * - 文件缺失/损坏/键值非法 ⇒ 视为无 key（不抛异常、绝不影响存量明文播放）
 * - 仅在文件 mtime 变化时重载，便于测试期热改映射
 * - 日志只输出条目数，不输出 kid/key 内容
 */
class OfflineMappingKeyProvider(
    private val file: File = File(appCtx.filesDir, FILE_NAME)
) : CencKeyProvider {

    companion object {
        const val FILE_NAME = "cenc_keys.json"
    }

    @Volatile
    private var loadedMtime: Long = Long.MIN_VALUE

    @Volatile
    private var mapping: Map<String, ByteArray> = emptyMap()

    override fun key(kid: String): ByteArray? {
        ensureLoaded()
        return mapping[kid.trim().lowercase()]
    }

    private fun ensureLoaded() {
        val mtime = file.lastModified()
        if (mtime == loadedMtime) return
        synchronized(this) {
            if (mtime == loadedMtime) return
            mapping = if (file.isFile) {
                kotlin.runCatching { parse(file.readText()) }
                    .onFailure {
                        // 只暴露异常类型，不打印文件内容（可能含 key）
                        AppLog.putWarn("CencKey: 离线映射解析失败 ${it.javaClass.simpleName}")
                    }
                    .getOrDefault(emptyMap())
            } else {
                emptyMap()
            }
            loadedMtime = mtime
            AppLog.putDebug("CencKey: 离线映射加载 count=${mapping.size}")
        }
    }

    private fun parse(text: String): Map<String, ByteArray> {
        if (text.isBlank()) return emptyMap()
        val type = object : TypeToken<Map<String, String>>() {}.type
        val raw: Map<String, String> = GSON.fromJson(text, type) ?: return emptyMap()
        val result = HashMap<String, ByteArray>(raw.size)
        raw.forEach { (kid, keyHex) ->
            val kidBytes = hexToBytesOrNull(kid)
            val keyBytes = hexToBytesOrNull(keyHex)
            // 非法键值直接跳过：宁可无 key，也不能把脏数据带进 MediaDrm
            if (kidBytes != null && kidBytes.size == 16 && keyBytes != null && keyBytes.size == 16) {
                result[kid.trim().lowercase()] = keyBytes
            }
        }
        return result
    }
}

/**
 * 全局密钥入口：默认离线映射；研究轨/测试可在启动早期替换为其它实现。
 */
object CencKeyStore {

    @Volatile
    var provider: CencKeyProvider = OfflineMappingKeyProvider()
}

/** 32 位 hex -> 16 字节；非法返回 null（不去猜、不补齐） */
internal fun hexToBytesOrNull(hex: String?): ByteArray? {
    val text = hex?.trim()?.removePrefix("0x")?.removePrefix("0X") ?: return null
    if (text.length % 2 != 0 || text.isEmpty()) return null
    return kotlin.runCatching {
        ByteArray(text.length / 2) { index ->
            text.substring(index * 2, index * 2 + 2).toInt(16).toByte()
        }
    }.getOrNull()
}
