package io.legado.app.utils

import java.nio.charset.Charset
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * REQ-09 / AD-14：字符集探测 GB 系 → GB18030 降级 单测。
 *
 * 背景：`EncodingDetect.getEncode` 原实现为 `match?.name ?: "UTF-8"` —— 探测命中 GBK/GB2312
 * 时直接用 GBK 解码，GB18030 的 4 字节扩展字符会被解成乱码/替换字符。GB18030 是 GBK、GB2312
 * 的**真超集**，故命中 GB 系时升到 GB18030 是严格不劣化。
 *
 * 覆盖分层：
 * - `resolveEncode` 纯逻辑（全分支，确定性）：抽取出来是为免依赖 `CharsetDetector` 对样本的
 *   统计探测结果（ICU 文档明言短文本探测不可靠），使断言可复现。
 * - `getEncode` 端到端仅断言「返回的是 JVM 可解析的字符集名」，验证真实探测链路不抛异常。
 */
class EncodingDetectGb18030Test {

    private fun gbk(text: String): ByteArray = text.toByteArray(Charset.forName("GBK"))
    private fun gb18030(text: String): ByteArray = text.toByteArray(Charset.forName("GB18030"))

    @Test
    fun resolveEncode_gbkDetected_upgradesToGb18030() {
        val bytes = gbk("中文测试内容")
        assertEquals("GB18030", EncodingDetect.resolveEncode("GBK", bytes))
        assertEquals("GB18030", EncodingDetect.resolveEncode("GB2312", bytes))
        assertEquals("GB18030", EncodingDetect.resolveEncode("gbk", bytes))
    }

    @Test
    fun resolveEncode_gb18030ExtensionCharsRoundTrip() {
        // U+3400（㐀）位于 GB18030 四字节区，GBK 无法表示 ⇒ 只有升到 GB18030 才能无损还原
        val text = "㐀龘中文测试"
        val bytes = gb18030(text)
        val encode = EncodingDetect.resolveEncode("GBK", bytes)
        assertEquals("GB18030", encode)
        assertEquals("GB18030 解码须无损还原含扩展字符的原文", text, String(bytes, Charset.forName(encode)))
    }

    @Test
    fun resolveEncode_nonGbDetected_isUnchanged() {
        assertEquals("UTF-8", EncodingDetect.resolveEncode("UTF-8", "中文".toByteArray(Charsets.UTF_8)))
        assertEquals(
            "ISO-8859-1",
            EncodingDetect.resolveEncode("ISO-8859-1", byteArrayOf(1, 2, 3))
        )
    }

    @Test
    fun resolveEncode_nullDetected_fallsBackToUtf8() {
        assertEquals("UTF-8", EncodingDetect.resolveEncode(null, byteArrayOf(1, 2, 3)))
    }

    @Test
    fun resolveEncode_gbDetectedButBytesNotGb_fallsBackToUtf8() {
        // 0xFF 在 GB18030 中为非法字节 ⇒ 解码出现替换字符 ⇒ 判定字节流并非 GB 系，回落 UTF-8
        assertEquals("UTF-8", EncodingDetect.resolveEncode("GBK", byteArrayOf(0xFF.toByte())))
    }

    @Test
    fun resolveEncode_emptyBytes_gbDetected_fallsBackToUtf8() {
        assertEquals("UTF-8", EncodingDetect.resolveEncode("GBK", ByteArray(0)))
    }

    @Test
    fun getEncode_endToEndReturnsSupportedCharset() {
        // 真实探测链路（CharsetDetector）须返回 JVM 可解析的字符集名，且不抛异常
        val encode = EncodingDetect.getEncode("hello 中文内容".toByteArray(Charsets.UTF_8))
        assertTrue("getEncode 返回的字符集名须受 JVM 支持: $encode", Charset.isSupported(encode))
    }
}