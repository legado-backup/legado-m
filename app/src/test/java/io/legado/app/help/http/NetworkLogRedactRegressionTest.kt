package io.legado.app.help.http

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * P0 NetworkLog 脱敏回归守护单测（分册 §9.1 编号 21）
 *
 * 现状守护（NetworkLog 零修改回归）：验证脱敏函数对敏感 header 集合、token query、
 * Bearer/Basic 凭据、JSON/form 凭据的处理行为——出现 [已脱敏] 且原值不出现。
 * formatHeaders(Map)/redactCredentialsForLog/redactUrlForLog 均为纯函数，纯 JVM 可测。
 */
class NetworkLogRedactRegressionTest {

    companion object {
        private const val REDACTED = "[已脱敏]"
    }

    @Test
    fun sensitiveHeadersAndCredentialsRedacted() {
        // ---- 敏感 header 集合：值整体替换为 [已脱敏]，原值不出现；普通 header 保留 ----
        val secretBearer = "Bearer sk-abc123secret"
        val secretCookie = "session=s3cr3tvalue; uid=42"
        val headers = mapOf(
            "Authorization" to secretBearer,
            "Proxy-Authorization" to "Basic cHJveHk6c2VjcmV0",
            "Cookie" to secretCookie,
            "Set-Cookie" to "token=respCookieSecret",
            "x-api-key" to "apiKeySecret123",
            "X-CSRF-Token" to "csrfSecret",
            "Content-Type" to "application/json"
        )
        val formatted = NetworkLog.formatHeaders(headers)
        assertFalse("Bearer 原值不应出现在 header 日志", formatted.contains(secretBearer))
        assertFalse("Cookie 原值不应出现在 header 日志", formatted.contains(secretCookie))
        assertFalse(formatted.contains("cHJveHk6c2VjcmV0"))
        assertFalse(formatted.contains("respCookieSecret"))
        assertFalse(formatted.contains("apiKeySecret123"))
        assertFalse(formatted.contains("csrfSecret"))
        assertEquals("Authorization: $REDACTED", formatted.lineSequence().first { it.startsWith("Authorization:") })
        assertTrue(formatted.contains("Cookie: $REDACTED"))
        assertTrue(formatted.contains("x-api-key: $REDACTED"))
        assertTrue("普通 header 应原样保留", formatted.contains("Content-Type: application/json"))

        // ---- token query：URL 凭据参数脱敏，其余参数与路径保留 ----
        val url = "https://e.example/api/v1/data?x=1&access_token=UrlTokenSecret&y=2"
        val redactedUrl = NetworkLog.redactUrlForLog(url)
        assertFalse("URL 中 token 原值不应出现", redactedUrl.contains("UrlTokenSecret"))
        assertTrue(redactedUrl.contains("&access_token=$REDACTED"))
        assertTrue("非凭据参数应保留", redactedUrl.contains("x=1") && redactedUrl.contains("y=2"))
        assertTrue("路径应保留", redactedUrl.contains("/api/v1/data"))

        // ---- Bearer/Basic 凭据（自由文本） ----
        val bearerText = "Authorization: Bearer abc.def_ghi+junk suffix"
        val redactedBearer = NetworkLog.redactCredentialsForLog(bearerText)
        assertFalse("Bearer 凭据原值不应出现", redactedBearer.contains("abc.def_ghi+junk"))
        assertTrue(redactedBearer.contains("Bearer $REDACTED"))
        assertTrue("前缀外的普通文本应保留", redactedBearer.endsWith(" suffix"))

        val basicText = "Proxy: Basic dXNlcjpwd2Q=="
        val redactedBasic = NetworkLog.redactCredentialsForLog(basicText)
        assertFalse("Basic 凭据原值不应出现", redactedBasic.contains("dXNlcjpwd2Q=="))
        assertTrue(redactedBasic.contains("Basic $REDACTED"))

        // ---- JSON 引号凭据 ----
        val jsonBody = """{"access-token":"jsonSecret1","name":"keep","refresh_token": "jsonSecret2"}"""
        val redactedJson = NetworkLog.redactCredentialsForLog(jsonBody)
        assertFalse("JSON 凭据原值不应出现", redactedJson.contains("jsonSecret1"))
        assertFalse(redactedJson.contains("jsonSecret2"))
        assertTrue(redactedJson.contains("\"access-token\":\"$REDACTED\""))
        assertTrue(redactedJson.contains("\"refresh_token\": \"$REDACTED\""))
        assertTrue("非凭据字段应保留", redactedJson.contains("\"name\":\"keep\""))

        // ---- form 凭据 ----
        val formBody = "username=u&password=formSecret1&sessionid=formSecret2"
        val redactedForm = NetworkLog.redactCredentialsForLog(formBody)
        assertFalse("form 凭据原值不应出现", redactedForm.contains("formSecret1"))
        assertFalse(redactedForm.contains("formSecret2"))
        assertTrue(redactedForm.contains("password=$REDACTED"))
        assertTrue(redactedForm.contains("sessionid=$REDACTED"))
        assertTrue("非凭据字段应保留", redactedForm.contains("username=u"))
    }
}
