package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Test
import java.net.URI

/**
 * AD-01 域名探测端口（2026-10-18）
 *
 * 旧实现 `url.port.takeIf { it > 0 } ?: 80` 对 **https 源**（`URI` 默认端口为 -1）也去连 **80**
 * ⇒ HTTPS 站常只开 443 ⇒ Socket 快探必然失败（真机 8282 域失败中约 68% 属此类误判）。
 * 现按 scheme 取端口：显式端口优先，否则 https→443 / http→80。
 */
class SourceQualityCheckerPortTest {

    @Test
    fun `https默认端口取443`() {
        assertEquals(443, SourceQualityChecker.resolveDomainPort(URI("https://example.com/path")))
    }

    @Test
    fun `http默认端口取80`() {
        assertEquals(80, SourceQualityChecker.resolveDomainPort(URI("http://example.com/")))
    }

    @Test
    fun `显式端口优先保留`() {
        assertEquals(8443, SourceQualityChecker.resolveDomainPort(URI("https://example.com:8443/x")))
        assertEquals(8080, SourceQualityChecker.resolveDomainPort(URI("http://example.com:8080/x")))
    }

    @Test
    fun `带#片段时端口仍正确`() {
        // 调用侧会先 substringBefore('#')，此处直接验证带片段 URI 的解析仍按 scheme 取端口
        assertEquals(443, SourceQualityChecker.resolveDomainPort(URI("https://example.com/#anchor")))
    }
}
