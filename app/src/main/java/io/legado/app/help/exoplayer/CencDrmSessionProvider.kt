package io.legado.app.help.exoplayer

import android.util.Base64
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.drm.DefaultDrmSessionManager
import androidx.media3.exoplayer.drm.DrmSessionManager
import androidx.media3.exoplayer.drm.DrmSessionManagerProvider
import androidx.media3.exoplayer.drm.ExoMediaDrm
import androidx.media3.exoplayer.drm.FrameworkMediaDrm
import androidx.media3.exoplayer.drm.LocalMediaDrmCallback
import io.legado.app.constant.AppLog

/**
 * CENC Clear-Key 会话提供者（设计 AD-01/AD-02）。
 *
 * 条件分支语义：**只有** MediaItem 显式声明 CLEARKEY DrmConfiguration 时才返回 ClearKey 会话，
 * 其余一律返回 [DrmSessionManager.DRM_UNSUPPORTED]（与 Media3 默认 provider 行为一致）⇒ 存量明文播放零回归。
 *
 * key 来源经 [CencKeyProvider] 抽象；未命中时同样返回 DRM_UNSUPPORTED 并留可读日志（不泄露 key）。
 */
@OptIn(UnstableApi::class)
class CencDrmSessionProvider(
    private val keyProvider: CencKeyProvider,
    private val sessionManagerFactory: (String, ByteArray) -> DrmSessionManager? =
        ::createClearKeySessionManager
) : DrmSessionManagerProvider {

    companion object {
        /** 书源契约里的加密标识（CENC AES-CTR） */
        const val ENCRYPTION_CENC_AES_CTR = "cenc-aes-ctr"

        /** 缓存上限：MediaDrm 属稀缺系统资源，只保留最近播放过的少量 kid */
        private const val MAX_CACHED_SESSIONS = 4

        fun isCencEncryption(encryption: String?): Boolean =
            encryption?.trim()?.equals(ENCRYPTION_CENC_AES_CTR, ignoreCase = true) == true

        /** kid 归一化：只接受 32 位 hex（容忍 `0x` 前缀与 `-` 分隔），其余视为非法 */
        fun normalizeKid(raw: String?): String? {
            val text = raw?.trim()
                ?.removePrefix("0x")?.removePrefix("0X")
                ?.replace("-", "")
                ?.lowercase()
                ?: return null
            if (text.length != 32) return null
            return text.takeIf { candidate -> candidate.all { it in '0'..'9' || it in 'a'..'f' } }
        }

        /**
         * 仅当「声明 CENC + kid 合法」时给 MediaItem 挂 DrmConfiguration。
         *
         * kid 通过 mediaId 传给 [CencDrmSessionProvider]（MediaItem.DrmConfiguration 无 kid 字段）。
         * 不设置 keySetId —— 那是离线 license 标识，语义不同。
         */
        fun attachCencIfNeeded(
            builder: MediaItem.Builder,
            kid: String?,
            encryption: String?
        ): MediaItem.Builder {
            if (!isCencEncryption(encryption)) return builder
            val normalizedKid = normalizeKid(kid) ?: return builder
            return builder
                .setMediaId(normalizedKid)
                .setDrmConfiguration(
                    MediaItem.DrmConfiguration.Builder(C.CLEARKEY_UUID)
                        .setMultiSession(true)
                        .build()
                )
        }
    }

    private val lock = Any()

    /** kid -> 已建会话（LRU：跨集切换复用，避免每集新建 MediaDrm） */
    private val cache = object : LinkedHashMap<String, DrmSessionManager>(4, 0.75f, true) {
        override fun removeEldestEntry(
            eldest: MutableMap.MutableEntry<String, DrmSessionManager>
        ): Boolean = size > MAX_CACHED_SESSIONS
    }

    override fun get(mediaItem: MediaItem): DrmSessionManager {
        val drmConfiguration = mediaItem.localConfiguration?.drmConfiguration
            ?: return DrmSessionManager.DRM_UNSUPPORTED
        if (drmConfiguration.scheme != C.CLEARKEY_UUID) {
            return DrmSessionManager.DRM_UNSUPPORTED
        }
        val kid = normalizeKid(mediaItem.mediaId)
        if (kid == null) {
            AppLog.putWarn("CencDrm: mediaId 不是合法 kid，CENC 回退为不支持")
            return DrmSessionManager.DRM_UNSUPPORTED
        }
        val key = keyProvider.key(kid)
        if (key == null || key.size != 16) {
            // 只输出 kid 长度与是否命中，绝不输出 key/kid 内容
            AppLog.put("CencDrm: 缺少解密密钥，无法播放 CENC 流, kidLen=${kid.length}")
            return DrmSessionManager.DRM_UNSUPPORTED
        }
        synchronized(lock) {
            cache[kid]?.let { return it }
            if (cache.size >= MAX_CACHED_SESSIONS) {
                val iterator = cache.entries.iterator()
                while (iterator.hasNext()) {
                    val entry = iterator.next()
                    iterator.remove()
                    kotlin.runCatching { entry.value.release() }
                }
            }
            val manager = sessionManagerFactory(kid, key)
            if (manager == null) {
                // 设备不支持 ClearKey（如部分模拟器缺 clearkey 插件）：不缓存、不崩溃，交回普通路径
                return DrmSessionManager.DRM_UNSUPPORTED
            }
            cache[kid] = manager
            AppLog.putDebug("CencDrm: 创建 ClearKey 会话, kidLen=${kid.length}")
            return manager
        }
    }
}

/**
 * ClearKey 会话构建：MediaDrm(CLEARKEY) + 固定授权响应（按 kid 缓存 ⇒ 响应与 kid 一一对应）。
 *
 * W3C ClearKey 授权响应格式：{"keys":[{"kty":"oct","k":<base64url key>,"kid":<base64url kid>}],"type":"temporary"}
 */
@OptIn(UnstableApi::class)
private fun createClearKeySessionManager(kid: String, key: ByteArray): DrmSessionManager? {
    // 先探测设备 ClearKey 能力：部分模拟器/机型无 clearkey 插件，
    // FrameworkMediaDrm.newInstance 会抛 UnsupportedDrmException，绝不能让它冒泡到播放线程（曾 FATAL）
    if (!android.media.MediaDrm.isCryptoSchemeSupported(C.CLEARKEY_UUID)) {
        AppLog.put("CencDrm: 设备不支持 ClearKey MediaDrm，跳过 CENC 播放")
        return null
    }
    val licenseResponse = buildClearKeyLicense(kid, key).toByteArray(Charsets.UTF_8)
    return DefaultDrmSessionManager.Builder()
        .setUuidAndExoMediaDrmProvider(
            C.CLEARKEY_UUID,
            ExoMediaDrm.Provider { uuid -> FrameworkMediaDrm.newInstance(uuid) }
        )
        .setMultiSession(true)
        .build(LocalMediaDrmCallback(licenseResponse))
}

/** 生成 ClearKey 授权响应（base64url 无填充，符合 EME ClearKey 规范） */
@OptIn(UnstableApi::class)
internal fun buildClearKeyLicense(kid: String, key: ByteArray): String {
    val kidBytes = hexToBytesOrNull(kid) ?: ByteArray(16)
    fun encode(bytes: ByteArray): String =
        Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
    return """{"keys":[{"kty":"oct","k":"${encode(key)}","kid":"${encode(kidBytes)}"}],"type":"temporary"}"""
}
