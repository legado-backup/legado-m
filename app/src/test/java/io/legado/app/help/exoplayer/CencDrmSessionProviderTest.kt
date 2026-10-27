package io.legado.app.help.exoplayer

import android.app.Application
import androidx.media3.common.C
import androidx.media3.common.DrmInitData
import androidx.media3.common.Format
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.drm.DrmSessionManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.nio.ByteBuffer

/**
 * CENC Clear-Key 管线单测（video-cenc-clearkey-playback AD-01/AD-02/AD-05）。
 *
 * 覆盖：kid 归一化、CENC 标识判定、MediaItem 条件式 DRM 挂载、key 命中/未命中分支、
 * ClearKey 授权响应格式、合成 pssh 结构、Format 注入与幂等。
 * 不触真实 MediaDrm（Robolectric 无 ClearKey 插件）——会话构建用工厂注入替身。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class CencDrmSessionProviderTest {

    private val kid = "0123456789abcdef0123456789abcdef"
    private val key = ByteArray(16) { it.toByte() }

    private fun mediaItem(kidValue: String?, encryptionScheme: Boolean = true): MediaItem {
        // 注意：Media3 的 LocalConfiguration 仅在 uri 非空时创建，测试必须给一个 URI
        var builder = MediaItem.Builder().setUri("https://example.com/v/1.mp4")
        if (encryptionScheme) {
            builder = CencDrmSessionProvider.attachCencIfNeeded(builder, kidValue, "cenc-aes-ctr")
        } else if (kidValue != null) {
            builder = builder.setMediaId(kidValue)
        }
        return builder.build()
    }

    @Test
    fun normalizeKid_acceptsHexVariants() {
        assertEquals(kid, CencDrmSessionProvider.normalizeKid("0123456789ABCDEF0123456789ABCDEF"))
        assertEquals(kid, CencDrmSessionProvider.normalizeKid("0x0123456789abcdef0123456789abcdef"))
        assertEquals(
            kid,
            CencDrmSessionProvider.normalizeKid("0123-4567-89ab-cdef-0123-4567-89ab-cdef")
        )
    }

    @Test
    fun normalizeKid_rejectsIllegal() {
        assertNull(CencDrmSessionProvider.normalizeKid(null))
        assertNull(CencDrmSessionProvider.normalizeKid(""))
        assertNull(CencDrmSessionProvider.normalizeKid("0123"))
        assertNull(CencDrmSessionProvider.normalizeKid("zzzz456789abcdef0123456789abcdef"))
    }

    @Test
    fun isCencEncryption_matchesOnlyCencCtr() {
        assertTrue(CencDrmSessionProvider.isCencEncryption("cenc-aes-ctr"))
        assertTrue(CencDrmSessionProvider.isCencEncryption(" CENC-AES-CTR "))
        assertFalse(CencDrmSessionProvider.isCencEncryption(null))
        assertFalse(CencDrmSessionProvider.isCencEncryption("aes-128"))
    }

    @Test
    fun attachCenc_setsClearKeyDrmAndNormalizedMediaId() {
        val item = mediaItem(kid.uppercase())
        val drm = item.localConfiguration?.drmConfiguration
        assertNotNull(drm)
        assertEquals(C.CLEARKEY_UUID, drm!!.scheme)
        assertEquals(kid, item.mediaId)
    }

    @Test
    fun attachCenc_skipsWhenNoDeclarationOrIllegalKid() {
        assertNull(mediaItem(kid, encryptionScheme = false).localConfiguration?.drmConfiguration)
        assertNull(mediaItem("bad-kid", encryptionScheme = true).localConfiguration?.drmConfiguration)
        assertNull(mediaItem(null, encryptionScheme = true).localConfiguration?.drmConfiguration)
    }

    @Test
    fun provider_returnsUnsupportedForNonDrmMedia() {
        val provider = CencDrmSessionProvider(MemoryKeyProvider(mapOf(kid to key)))
        assertSame(
            DrmSessionManager.DRM_UNSUPPORTED,
            provider.get(mediaItem(kid, encryptionScheme = false))
        )
    }

    @Test
    fun provider_returnsUnsupportedWhenKeyMissing() {
        val provider = CencDrmSessionProvider(MemoryKeyProvider(emptyMap()))
        assertSame(DrmSessionManager.DRM_UNSUPPORTED, provider.get(mediaItem(kid)))
    }

    @Test
    fun provider_buildsSessionOnceAndCachesPerKid() {
        var factoryCalls = 0
        val provider = CencDrmSessionProvider(
            MemoryKeyProvider(mapOf(kid to key)),
            sessionManagerFactory = { factoryKid, _ ->
                factoryCalls++
                assertEquals(kid, factoryKid)
                DrmSessionManager.DRM_UNSUPPORTED
            }
        )
        val first = provider.get(mediaItem(kid))
        val second = provider.get(mediaItem(kid))
        assertEquals(1, factoryCalls)
        assertSame(first, second)
    }

    @Test
    fun provider_returnsUnsupportedWhenDeviceLacksClearKey() {
        // 设备不支持 ClearKey 时工厂返回 null ⇒ 不崩溃、回落普通路径（曾经 UnsupportedDrmException FATAL）
        val provider = CencDrmSessionProvider(
            MemoryKeyProvider(mapOf(kid to key)),
            sessionManagerFactory = { _, _ -> null }
        )
        assertSame(DrmSessionManager.DRM_UNSUPPORTED, provider.get(mediaItem(kid)))
    }

    @Test
    fun buildClearKeyLicense_containsKidAndKeyBase64() {
        val license = buildClearKeyLicense(kid, key)
        assertTrue(license.startsWith("{\"keys\":[{\"kty\":\"oct\",\"k\":\""))
        assertTrue(license.endsWith("\"}],\"type\":\"temporary\"}"))
        // kid 16 字节 -> base64url 无填充 22 字符（只校验结构，不校验 key 内容）
        val kidB64 = license.substringAfter("\"kid\":\"").substringBefore("\"")
        assertEquals(22, kidB64.length)
        assertFalse(kidB64.contains("="))
    }

    @Test
    fun buildClearKeyPssh_hasValidBoxStructure() {
        val pssh = buildClearKeyPssh(kid)
        assertEquals(48, pssh.size)
        assertEquals("pssh", String(pssh, 4, 4, Charsets.US_ASCII))
        assertEquals(1, pssh[8].toInt())
        val buffer = ByteBuffer.wrap(pssh)
        buffer.position(12)
        assertEquals(C.CLEARKEY_UUID.mostSignificantBits, buffer.long)
        assertEquals(C.CLEARKEY_UUID.leastSignificantBits, buffer.long)
        assertEquals(1, buffer.int)
        val kidBytes = ByteArray(16)
        buffer.get(kidBytes)
        assertEquals(kid, kidBytes.joinToString("") { "%02x".format(it) })
    }

    @Test
    fun withClearKeyDrmInitData_injectsAndIsIdempotent() {
        val pssh = buildClearKeyPssh(kid)
        val plain = Format.Builder().setSampleMimeType("video/avc").build()
        val injected = plain.withClearKeyDrmInitData(pssh)
        val drmInitData = injected.drmInitData
        assertNotNull(drmInitData)
        assertEquals(1, drmInitData!!.schemeDataCount)
        assertTrue(drmInitData.get(0).matches(C.CLEARKEY_UUID))
        assertTrue(drmInitData.get(0).data!!.contentEquals(pssh))
        // 已含 ClearKey schemeData ⇒ 原样返回，不重复注入
        assertSame(injected, injected.withClearKeyDrmInitData(pssh))
    }

    @Test
    fun withClearKeyDrmInitData_keepsExistingSchemeData() {
        val other = DrmInitData.SchemeData(C.WIDEVINE_UUID, "video/mp4", byteArrayOf(1, 2, 3))
        val existing = Format.Builder()
            .setSampleMimeType("video/avc")
            .setDrmInitData(DrmInitData(other))
            .build()
        val injected = existing.withClearKeyDrmInitData(buildClearKeyPssh(kid))
        val injectedDrm = injected.drmInitData!!
        assertEquals(2, injectedDrm.schemeDataCount)
        assertTrue(injectedDrm.get(0).matches(C.CLEARKEY_UUID))
        assertTrue(injectedDrm.get(1).matches(C.WIDEVINE_UUID))
    }

    @Test
    fun offlineMappingProvider_parsesValidEntriesOnly() {
        val file = java.io.File.createTempFile("cenc_keys", ".json")
        try {
            file.writeText(
                """{"$kid":"00112233445566778899aabbccddeeff","bad-kid":"00112233445566778899aabbccddeeff","0123456789abcdef0123456789abcdee":"xyz"}"""
            )
            val provider = OfflineMappingKeyProvider(file)
            val loaded = provider.key(kid.uppercase())
            assertNotNull(loaded)
            assertEquals(16, loaded!!.size)
            assertNull(provider.key("bad-kid"))
            assertNull(provider.key("ffffffffffffffffffffffffffffffff"))
        } finally {
            file.delete()
        }
    }
}
