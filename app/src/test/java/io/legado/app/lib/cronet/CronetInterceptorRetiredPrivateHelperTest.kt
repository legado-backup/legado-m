package io.legado.app.lib.cronet

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31 续批：`CronetInterceptor` 零调用私有件退役守护（G-44 覆盖盲区修复后新命中）。
 *
 * 退役项：`private fun getCookie(url)` —— 自建 `Cookie` 请求头的私有助手（零调用）；活路径是
 * `CookieManager.loadRequest(newReq)`（同职责且更完备：走项目 CookieManager 而非裸 cookieJar）
 * ⇒ A 档（零调用 + 同语义活替代）。
 */
class CronetInterceptorRetiredPrivateHelperTest {

    @Test
    fun `零调用取 Cookie 助手已退役且活路径仍在`() {
        val src = SourceFileProbe.sourceText("lib/cronet/CronetInterceptor.kt")
        assertEquals("退役项不得回潮", false, src.contains("fun getCookie"))
        assertEquals("活路径必须保留（项目 CookieManager 装载）", true, src.contains("CookieManager.loadRequest(newReq)"))
        assertEquals("装载前的头存在性判据必须保留", true, src.contains("header(cookieJarHeader)"))
    }
}
