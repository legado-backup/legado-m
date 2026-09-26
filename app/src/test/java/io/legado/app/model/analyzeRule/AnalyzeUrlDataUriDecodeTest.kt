package io.legado.app.model.analyzeRule

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.3：`AnalyzeUrl` 的 data URI 解码统一到宽容解码单源
 *
 * 原实现 `Base64.decode(groupValues[1], DEFAULT)` 严格解码 ⇒ 畸形 data URI 直接抛异常打断整条链路。
 */
class AnalyzeUrlDataUriDecodeTest {

    private val code = SourceFileProbe.sourceText("model/analyzeRule/AnalyzeUrl.kt")

    @Test
    fun dataUriGoesThroughSharedTolerantDecoder() {
        assertTrue(
            "data URI 必须走单源宽容解码",
            code.contains("return urlNoQuery.decodeBase64DataUrlBytes()")
        )
        assertFalse(
            "不得残留严格解码调用",
            code.contains("Base64.decode(dataUriBase64, Base64.DEFAULT)")
        )
    }

    @Test
    fun failureStillFallsBackToNetwork() {
        assertTrue(
            "解码失败（返回 null）必须回落网络请求，不得中断 getByteArrayAwait",
            code.contains("getByteArrayIfDataUri()?.let {")
        )
    }
}