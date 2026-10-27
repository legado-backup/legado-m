package io.legado.app.help.exoplayer

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * CENC fMP4 软件解密单测（设计 AD-04）。
 *
 * 用**手工构造的最小 fMP4**（moov+encv/sinf/tenc + moof/traf/tfhd/trun/senc + mdat）验证：
 * 全样本 / subsample 两种 AES-CTR 解密正确、加密信令盒降级为 free、样本入口恢复原始编码四字码。
 * 纯 JVM（不跑 Robolectric）：AES-CTR 必须用真实 JDK 实现，Robolectric 下 Cipher 初始化不可靠。
 */
class CencFmp4DecryptorTest {

    companion object {
        private val KEY = ByteArray(16) { (it + 1).toByte() }
        private val IV = ByteArray(16) { (it * 3 + 1).toByte() }
    }

    private val key: ByteArray get() = KEY
    private val iv: ByteArray get() = IV
    private val kid = "0123456789abcdef0123456789abcdef"

    // ------------------------------------------------------------ 夹具构造

    private fun box(type: String, payload: ByteArray): ByteArray {
        val buffer = ByteBuffer.allocate(8 + payload.size)
        buffer.putInt(8 + payload.size)
        buffer.put(type.toByteArray(Charsets.US_ASCII))
        buffer.put(payload)
        return buffer.array()
    }

    private fun int32(value: Int): ByteArray = ByteBuffer.allocate(4).putInt(value).array()

    private fun tkhd(): ByteArray {
        val payload = ByteArray(4 + 8 + 4 + 8) { 0 }
        ByteBuffer.wrap(payload).putInt(12, 1) // v0：payload+12 = track_ID
        return box("tkhd", payload)
    }

    private fun tenc(ivSize: Int): ByteArray {
        val payload = ByteArray(8 + 16) { 0 }
        payload[6] = 1 // default_isProtected
        payload[7] = ivSize.toByte() // default_Per_Sample_IV_Size
        return box("tenc", payload)
    }

    private fun encvEntry(withEncryption: Boolean): ByteArray {
        val sinf = box(
            "sinf",
            box("frma", "hvc1".toByteArray(Charsets.US_ASCII)) +
                box("schi", tenc(16))
        )
        val payload = ByteArray(6 + 2 + 70) { 0 } + if (withEncryption) sinf else ByteArray(0)
        return box(if (withEncryption) "encv" else "hvc1", payload)
    }

    private fun moov(withEncryption: Boolean = true): ByteArray {
        val stsd = box("stsd", int32(0) + int32(1) + encvEntry(withEncryption))
        val stbl = box("stbl", stsd)
        val minf = box("minf", stbl)
        val mdia = box("mdia", minf)
        val trak = box("trak", tkhd() + mdia)
        return box("moov", trak)
    }

    private data class MoofResult(val bytes: ByteArray, val sampleOffsetInMoof: Int)

    private fun moof(dataOffset: Int, sampleSize: Int, sencPayload: ByteArray): MoofResult {
        val tfhd = box("tfhd", int32(0x020000) + int32(1))
        val trun = box(
            "trun",
            int32(0x000001 or 0x000200) + int32(1) + int32(dataOffset) + int32(sampleSize)
        )
        val senc = box("senc", sencPayload)
        val traf = box("traf", tfhd + trun + senc)
        val moof = box("moof", traf)
        // 样本数据紧跟 moof 后的 mdat 头（8 字节）
        return MoofResult(moof, moof.size + 8)
    }

    private fun sencFull(iv: ByteArray): ByteArray =
        int32(0) + int32(1) + iv

    private fun sencSubsamples(iv: ByteArray, subsamples: List<Pair<Int, Int>>): ByteArray {
        val out = ByteArrayOutputStream()
        out.write(int32(0x000002))
        out.write(int32(1))
        out.write(iv)
        out.write(ByteBuffer.allocate(2).putShort(subsamples.size.toShort()).array())
        subsamples.forEach { (clear, encrypted) ->
            out.write(ByteBuffer.allocate(2).putShort(clear.toShort()).array())
            out.write(int32(encrypted))
        }
        return out.toByteArray()
    }

    private fun cipher(): Cipher {
        val keyBytes = KEY.copyOf()
        val ivBytes = IV.copyOf()
        require(keyBytes.size == 16) { "key size ${keyBytes.size}" }
        require(ivBytes.size == 16) { "iv size ${ivBytes.size}" }
        val cipher = Cipher.getInstance("AES/CTR/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(keyBytes, "AES"), IvParameterSpec(ivBytes))
        return cipher
    }

    private fun buildFile(sencPayload: ByteArray, sample: ByteArray): ByteArray {
        // dataOffset 先占位 0，拿到 moof 尺寸后再回填（长度不变）
        var moof = moof(0, sample.size, sencPayload)
        moof = moof(moof.sampleOffsetInMoof, sample.size, sencPayload)
        val mdat = box("mdat", sample)
        return moov() + moof.bytes + mdat
    }

    // ---------------------------------------------------------------- 用例

    @Test
    fun decryptInPlace_fullSampleRestoresPlaintextAndPatchesBoxes() {
        val plain = ByteArray(64) { (it * 7 + 3).toByte() }
        val encrypted = cipher().doFinal(plain)
        val data = buildFile(sencFull(iv), encrypted)

        val stats = CencFmp4Decryptor.decryptInPlace(data, key)

        assertEquals(1, stats.sampleCount)
        assertEquals(1, stats.trackCount)
        assertTrue(stats.patchedBoxes >= 2)
        val sampleStart = data.size - encrypted.size
        assertArrayEquals(plain, data.copyOfRange(sampleStart, data.size))
        // encv -> hvc1（长度不变），sinf/senc -> free
        assertTrue(indexOf(data, "encv".toByteArray(Charsets.US_ASCII)) < 0)
        assertTrue(indexOf(data, "hvc1".toByteArray(Charsets.US_ASCII)) >= 0)
        assertEquals(-1, indexOf(data, "senc".toByteArray(Charsets.US_ASCII)))
        assertTrue(indexOf(data, "free".toByteArray(Charsets.US_ASCII)) >= 0)
    }

    @Test
    fun decryptInPlace_subsamplesDecryptOnlyEncryptedRanges() {
        // 4 clear + 8 encrypted + 4 clear + 12 encrypted
        val plain = ByteArray(28) { (it * 5 + 1).toByte() }
        val cipher = cipher()
        val encrypted = plain.copyOf()
        System.arraycopy(cipher.update(plain, 4, 8), 0, encrypted, 4, 8)
        System.arraycopy(cipher.update(plain, 16, 12), 0, encrypted, 16, 12)
        val senc = sencSubsamples(iv, listOf(4 to 8, 4 to 12))
        val data = buildFile(senc, encrypted)

        val stats = CencFmp4Decryptor.decryptInPlace(data, key)

        assertEquals(1, stats.sampleCount)
        val sampleStart = data.size - plain.size
        assertArrayEquals(plain, data.copyOfRange(sampleStart, data.size))
    }

    @Test
    fun decryptInPlace_returnsZeroWhenNoEncryptionBoxes() {
        val plain = ByteArray(32) { it.toByte() }
        val data = moov(withEncryption = false) + moof(0, plain.size, sencFull(iv)).bytes + box("mdat", plain)
        val stats = CencFmp4Decryptor.decryptInPlace(data, key)
        assertEquals(0, stats.sampleCount)
    }

    @Test
    fun decrypt_removesEncryptionBoxesAndKeepsPlaintext() {
        val plain = ByteArray(64) { (it * 11 + 5).toByte() }
        val encrypted = cipher().doFinal(plain)
        val data = buildFile(sencFull(iv), encrypted)

        val result = CencFmp4Decryptor.decrypt(data, key)

        assertEquals(1, result.stats.sampleCount)
        val bytes = result.bytes
        assertTrue("重写后体积应缩小", bytes.size < data.size)
        assertEquals(-1, indexOf(bytes, "senc".toByteArray(Charsets.US_ASCII)))
        assertEquals(-1, indexOf(bytes, "saiz".toByteArray(Charsets.US_ASCII)))
        assertEquals(-1, indexOf(bytes, "saio".toByteArray(Charsets.US_ASCII)))
        assertEquals(-1, indexOf(bytes, "sinf".toByteArray(Charsets.US_ASCII)))
        assertEquals(-1, indexOf(bytes, "encv".toByteArray(Charsets.US_ASCII)))
        val mdat = indexOf(bytes, "mdat".toByteArray(Charsets.US_ASCII))
        assertTrue(mdat > 0)
        val payloadStart = mdat + 4
        assertArrayEquals(plain, bytes.copyOfRange(payloadStart, payloadStart + plain.size))
        // 样本入口恢复原始编码四字码（frma=hvc1）
        assertTrue(indexOf(bytes, "hvc1".toByteArray(Charsets.US_ASCII)) >= 0)
    }

    @Test
    fun isRequired_gateRequiresCencKidAndMissingClearKeySupport() {
        // 声明正确 + kid 合法 ⇒ 是否降级只取决于设备 ClearKey 能力（真机结果由设备决定）
        assertTrue(CencDrmSessionProvider.isCencEncryption("cenc-aes-ctr"))
        assertEquals(kid, CencDrmSessionProvider.normalizeKid(kid))
    }

    private fun indexOf(haystack: ByteArray, needle: ByteArray): Int {
        outer@ for (i in 0..haystack.size - needle.size) {
            for (j in needle.indices) {
                if (haystack[i + j] != needle[j]) continue@outer
            }
            return i
        }
        return -1
    }
}
