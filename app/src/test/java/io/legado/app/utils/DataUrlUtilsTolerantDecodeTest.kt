package io.legado.app.utils

import android.app.Application
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * R 批 §3.3.3：Base64 宽容解码单源（[decodeTolerantBase64]）
 *
 * 必须跑 Robolectric：本项目 `unitTests.returnDefaultValues = true`，纯 JVM 下
 * `android.util.Base64` 是返回 null 的桩，测不出真实宽容行为（本轮实测踩过）。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class DataUrlUtilsTolerantDecodeTest {

    private val hi = "hi".toByteArray(Charsets.UTF_8)

    @Test
    fun decodesStandardPayload() {
        assertArrayEquals(hi, decodeTolerantBase64("aGk="))
    }

    @Test
    fun decodesPayloadWithoutPadding() {
        assertArrayEquals(hi, decodeTolerantBase64("aGk"))
    }

    @Test
    fun decodesUrlSafeVariant() {
        // 0xFF 的标准 base64 为 "/w=="，URL-safe 变体用 '_' 代替 '/'
        assertArrayEquals(byteArrayOf(-1), decodeTolerantBase64("_w"))
    }

    @Test
    fun stripsWhitespaceAndLineBreaks() {
        assertArrayEquals(hi, decodeTolerantBase64("aG\n\tk=  "))
    }

    @Test
    fun decodesPercentEscapedPayload() {
        assertArrayEquals(byteArrayOf(-1), decodeTolerantBase64("%2Fw%3D%3D"))
    }

    @Test
    fun cleansMalformedCharactersBeforeRetry() {
        assertArrayEquals(hi, decodeTolerantBase64("aG!k="))
    }

    @Test
    fun returnsNullForUnusablePayload() {
        assertNull(decodeTolerantBase64("   "))
        assertNull(decodeTolerantBase64("!!!"))
    }

    @Test
    fun respectsMaxBytesCap() {
        assertNull("估算超过上限必须拒绝", decodeTolerantBase64("aGk=", maxBytes = 1))
    }

    @Test
    fun dataUrlPathKeepsWorkingAfterRefactor() {
        assertArrayEquals(hi, "data:image/png;base64,aGk=".decodeBase64DataUrlBytes())
        assertNull(
            "非 base64 的 data URI 不属于本解码器职责",
            "data:image/svg+xml;utf8,<svg/>".decodeBase64DataUrlBytes()
        )
    }
}