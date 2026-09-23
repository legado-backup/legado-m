package io.legado.app.utils

import java.io.ByteArrayInputStream
import java.io.InputStream
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R20「UTF-8 SHA-256 收敛」单测。
 *
 * 验收口径（tasks §4.4）：**新旧摘要逐位一致**、兆级输入不物化整段、
 * 且不无谓替换小载荷（仅两处登记点改调）。
 */
class Utf8Sha256Test {

    /** 旧实现（改造前口径），用于逐位对照。 */
    private fun legacyHex(text: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(text.toByteArray())
            .joinToString("") { "%02x".format(it) }

    @Test
    fun hex_matchesLegacyImplementation() {
        listOf(
            "",
            "a",
            "回归样本正文",
            "\uD83D\uDE00 emoji + 混合 ASCII",
            "line1\nline2\r\nline3",
            "x".repeat(4096)
        ).forEach { input ->
            assertEquals(
                "摘要必须与旧实现逐位一致：len=${input.length}",
                legacyHex(input),
                Utf8Sha256.hex(input)
            )
        }
    }

    /** 独立锚点：SHA-256("") 是公开已知常量（避免「新旧实现都错」的自证陷阱）。 */
    @Test
    fun emptyInput_matchesKnownDigest() {
        assertEquals(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            Utf8Sha256.hex("")
        )
        assertEquals(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            Utf8Sha256.hex(ByteArray(0))
        )
    }

    /** 十六进制口径：小写、定长 64。 */
    @Test
    fun hex_isLowercaseAnd64Chars() {
        val value = Utf8Sha256.hex("回归样本")
        assertEquals(64, value.length)
        assertTrue("必须为小写十六进制", value.all { it in '0'..'9' || it in 'a'..'f' })
    }

    /** 兆级输入：字符串/字节两条通道结果一致（证明字节通道与文本通道同口径）。 */
    @Test
    fun megaByteInput_stringAndByteChannelsAgree() {
        val mega = buildString {
            while (length < 1_000_000) append("回归样本正文0123456789\n")
        }
        assertEquals(
            Utf8Sha256.hex(mega),
            Utf8Sha256.hex(mega.toByteArray(Charsets.UTF_8))
        )
    }

    /** 流式通道：必须**分块**消费（而非一次读完），且摘要与整体一致。 */
    @Test
    fun streamChannel_readsInChunks_andMatchesWholeDigest() {
        val payload = ByteArray(100_000) { (it % 251).toByte() }
        val counter = ChunkCountingStream(ByteArrayInputStream(payload))
        val streamed = Utf8Sha256.hex(counter, bufferSize = 4096)
        assertEquals(
            "流式摘要必须与整体摘要一致",
            Utf8Sha256.hex(payload),
            streamed
        )
        assertTrue(
            "必须多次分块读取（实得 ${counter.readCalls} 次），否则等于一次性物化",
            counter.readCalls >= 25
        )
        assertTrue(
            "单次读取不得超过给定缓冲（实得最大 ${counter.maxRequested}）",
            counter.maxRequested <= 4096
        )
    }

    @Test
    fun streamChannel_emptyInput() {
        assertEquals(
            Utf8Sha256.hex(""),
            Utf8Sha256.hex(ByteArrayInputStream(ByteArray(0)))
        )
    }

    /** 非法缓冲参数必须 fail-fast（防 0 长度缓冲导致死循环/空读）。 */
    @Test(expected = IllegalArgumentException::class)
    fun streamChannel_rejectsNonPositiveBuffer() {
        Utf8Sha256.hex(ByteArrayInputStream(ByteArray(4)), bufferSize = 0)
    }

    private class ChunkCountingStream(private val delegate: InputStream) : InputStream() {
        var readCalls = 0
            private set
        var maxRequested = 0
            private set

        override fun read(): Int = delegate.read()

        override fun read(b: ByteArray, off: Int, len: Int): Int {
            readCalls++
            maxRequested = maxOf(maxRequested, len)
            return delegate.read(b, off, len)
        }
    }
}