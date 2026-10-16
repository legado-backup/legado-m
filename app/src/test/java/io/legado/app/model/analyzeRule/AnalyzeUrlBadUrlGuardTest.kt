package io.legado.app.model.analyzeRule

import io.legado.app.testkit.SourceFileProbe
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-104：规则产物 URL 为空 / 格式非法时的**业务异常化**护栏。
 *
 * 缺陷（设备巡检 200 样本 #126 实测）：空 host 的规则 URL 会让 OkHttp 抛裸
 * `IllegalArgumentException: Invalid URL host: ""`；该类型非 `NoStackTraceException`
 * ⇒ `QualityReportApplier.failureKindOf` 归因落到「网络（网站失效）」，真因却是**规则缺失**
 * ⇒ 用户与质检都误判为「源站坏了」。
 *
 * 交付：`AnalyzeUrl.executeStrRequest` 入口前置判定（`isBlankOrBadHttpUrl`）并抛业务异常
 * ⇒ 归因回到「规则/维度」侧，调试面亦可读到可读 message。
 */
class AnalyzeUrlBadUrlGuardTest {

    @Test
    fun `空地址与非法http地址判为可疑`() {
        assertTrue("null", isBlankOrBadHttpUrl(null))
        assertTrue("空串", isBlankOrBadHttpUrl(""))
        assertTrue("纯空白", isBlankOrBadHttpUrl("   "))
        assertTrue("无主机 http://", isBlankOrBadHttpUrl("http://"))
        assertTrue("无主机带端口 http://:8080", isBlankOrBadHttpUrl("http://:8080"))
        // 诊断取证：OkHttp 会把 `https:///a` **归一化**为 `https://a/`（host=a）⇒ 属可发起的请求，不判可疑
        assertEquals("https://a/", "https:///a".toHttpUrlOrNull().toString())
    }

    @Test
    fun `合法http地址判为可用`() {
        assertFalse(isBlankOrBadHttpUrl("https://example.com/search?q=1"))
        assertFalse(isBlankOrBadHttpUrl("http://example.com"))
        assertFalse("大写 scheme 同样合法", isBlankOrBadHttpUrl("HTTP://example.com/a"))
    }

    @Test
    fun `非http scheme不参与判定避免误伤`() {
        assertFalse("本地文件", isBlankOrBadHttpUrl("file:///sdcard/book.txt"))
        assertFalse("data 协议", isBlankOrBadHttpUrl("data:text/plain;base64,QQ=="))
    }

    @Test
    fun `请求入口必须前置调用该判据`() {
        val src = SourceFileProbe.sourceText("model/analyzeRule/AnalyzeUrl.kt")
        assertTrue(
            "executeStrRequest 入口须前置判定（否则裸 IAE 归因误判回潮）",
            src.contains("if (isBlankOrBadHttpUrl(urlNoQuery))")
        )
        assertEquals("判据须抛业务异常而非裸 IAE", true, src.contains("throw NoStackTraceException("))
    }
}
