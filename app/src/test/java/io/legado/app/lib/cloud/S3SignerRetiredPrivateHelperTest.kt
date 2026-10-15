package io.legado.app.lib.cloud

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31 续批：`S3Signer` 零调用私有件退役守护（G-44 覆盖盲区修复后新命中）。
 *
 * 退役项：`private fun String.encodeAwsPath()` —— 与被保留的 `encodeAwsQuery()` **函数体逐字相同**
 * （URLEncoder + `+`→`%20` + `%7E`→`~`），且签名路径把 URI 取为 `url.encodedPath`（**已编码**）
 * ⇒ 无任何活消费点（零调用 + 同语义活替代 ⇒ A 档）。
 */
class S3SignerRetiredPrivateHelperTest {

    @Test
    fun `零调用路径编码助手已退役且查询编码者仍在`() {
        val src = SourceFileProbe.sourceText("lib/cloud/S3Signer.kt")
        assertEquals("退役项不得回潮", false, src.contains("encodeAwsPath"))
        assertEquals("活替代者 encodeAwsQuery 必须保留", true, src.contains("encodeAwsQuery"))
        assertEquals("签名 URI 必须继续取已编码路径", true, src.contains("url.encodedPath"))
        assertEquals("签名查询必须继续走编码器", true, src.contains("encodeAwsQuery()"))
    }
}
