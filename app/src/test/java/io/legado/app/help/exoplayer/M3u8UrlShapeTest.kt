package io.legado.app.help.exoplayer

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * video-legacy-parity-hls AD-03：m3u8 URL 形态判定（纯函数）。
 *
 * 正例覆盖「路径后缀 / 显式 format·type / 代理端点路径段 / query 相对路径值」四类；
 * 负例覆盖历史 3002 误判场景与过宽匹配风险。
 */
class M3u8UrlShapeTest {

    @Test
    fun matches_pathSuffix() {
        assertEquals(true, M3u8UrlShape.matches("https://a.example/v/index.m3u8"))
        assertEquals(true, M3u8UrlShape.matches("https://a.example/v/index.m3u8?token=1"))
        assertEquals(true, M3u8UrlShape.matches("https://a.example/v/INDEX.M3U8"))
    }

    @Test
    fun matches_explicitQueryFlag() {
        assertEquals(true, M3u8UrlShape.matches("https://a.example/play?format=m3u8"))
        assertEquals(true, M3u8UrlShape.matches("https://a.example/play?type=m3u8"))
    }

    @Test
    fun matches_proxyEndpointPathSegment() {
        assertEquals(true, M3u8UrlShape.matches("https://a.example/api/v1/m3u8/proxy"))
        assertEquals(true, M3u8UrlShape.matches("https://a.example/api/v1/m3u8/proxy?path=abc"))
    }

    @Test
    fun matches_queryRelativeM3u8Value() {
        assertEquals(
            true,
            M3u8UrlShape.matches("https://a.example/api/v1/m3u8/x?path=jpd%2F2026%2Fk%2Fv.m3u8")
        )
        assertEquals(
            true,
            M3u8UrlShape.matches("https://a.example/api/v1/x?path=jpd/2026/k/v.m3u8")
        )
    }

    @Test
    fun rejects_absoluteUrlInsideQuery() {
        // 历史铁证：Play.php?uu=<绝对 URL 含 index.m3u8> 曾被过宽匹配误判 ⇒ HLS 解析非清单内容抛 3002
        assertEquals(
            false,
            M3u8UrlShape.matches(
                "https://a.example/Player/Play.php?uu=https%3A%2F%2Fp.example%2Findex.m3u8"
            )
        )
    }

    @Test
    fun rejects_looseMatches() {
        assertEquals(false, M3u8UrlShape.matches("https://a.example/search?q=m3u8"))
        assertEquals(false, M3u8UrlShape.matches("https://a.example/m3u8x/a"))
        assertEquals(false, M3u8UrlShape.matches("https://a.example/a.m3u8.bak"))
        assertEquals(false, M3u8UrlShape.matches("https://a.example/m3u8"))
        assertEquals(false, M3u8UrlShape.matches("https://a.example/v.mp4"))
        assertEquals(false, M3u8UrlShape.matches(""))
    }

    @Test
    fun rejects_otherContainers() {
        assertEquals(false, M3u8UrlShape.matches("https://a.example/v/index.mpd"))
        assertEquals(false, M3u8UrlShape.matches("https://a.example/v/seg.ts"))
    }

    @Test
    fun hlsRefererInjectedWhenMissing() {
        val hls = "https://a.example/api/v1/m3u8/proxy?path=x.m3u8"
        assertEquals(
            hls,
            M3u8UrlShape.headersWithHlsReferer(emptyMap(), hls)["Referer"]
        )
        assertEquals(1, M3u8UrlShape.headersWithHlsReferer(emptyMap(), hls).size)
    }

    @Test
    fun hlsRefererKeepsExplicitValue() {
        // 大小写不敏感；书源显式 Referer 绝不被覆盖
        val hls = "https://a.example/api/v1/m3u8/proxy"
        val merged = M3u8UrlShape.headersWithHlsReferer(mapOf("referer" to "https://keep"), hls)
        assertEquals("https://keep", merged["referer"])
        assertEquals(1, merged.size)
    }

    @Test
    fun hlsRefererNotInjectedForNonHls() {
        assertEquals(0, M3u8UrlShape.headersWithHlsReferer(emptyMap(), "https://a.example/v.mp4").size)
        assertEquals(0, M3u8UrlShape.headersWithHlsReferer(emptyMap(), "https://a.example/play?q=1").size)
    }
}
