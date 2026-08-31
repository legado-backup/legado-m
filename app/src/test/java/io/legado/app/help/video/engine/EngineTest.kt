package io.legado.app.help.video.engine

import io.legado.app.help.video.SniffCandidate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Phase 3 引擎 JVM 单元测试（任务 4.9）
 *
 * 覆盖点：
 * - M3u8Parser.parseSegments：分片列表 + EXTINF 总时长（毫秒）；空文本
 * - M3u8Parser.pickBestVariant：多码率选最高 BANDWIDTH（含 AVERAGE-BANDWIDTH 干扰剥离 B10）；单一 variant
 * - M3u8Parser.resolveRelative：绝对 URL / 相对路径 / 带 query / URI 解析失败退化
 * - M3u8Parser.parseKeyInfo：METHOD+URI+IV 十六进制解析（含带引号 METHOD）；无 KEY 行
 * - M3u8Parser.parseMediaSequence：#EXT-X-MEDIA-SEQUENCE 提取；缺失→0
 * - HeaderResolver.toJsonHeaders/fromJsonHeaders：往返一致；空 map/空串/null/非法 JSON/JSON null
 *   （失败路径 AppLog.put 在 JVM 安全：LogUtils 用 java.util.logging + gradle returnDefaultValues 兜底 android.util.Log）
 * - SniffResult.url 便捷取值：selected 命中 / null
 *
 * 未覆盖（JVM 不可测）：HeaderResolver.merge 依赖 android.webkit.CookieManager，留 L2 真机/Robolectric。
 */
class EngineTest {

    // ==================== M3u8Parser.parseSegments ====================

    @Test
    fun parseSegments_standardPlaylist() {
        val playlist = """
            #EXTM3U
            #EXT-X-VERSION:3
            #EXT-X-TARGETDURATION:10
            #EXTINF:10.5,
            seg1.ts
            #EXTINF:9.5,
            seg2.ts
            #EXT-X-ENDLIST
        """.trimIndent()
        val (segments, totalMs) = M3u8Parser.parseSegments(playlist)
        assertEquals("分片数=2", 2, segments.size)
        assertEquals("分片顺序保持", listOf("seg1.ts", "seg2.ts"), segments)
        assertEquals("总时长 = (10.5+9.5)*1000 ms", 20000L, totalMs)
    }

    @Test
    fun parseSegments_emptyText() {
        val (segments, totalMs) = M3u8Parser.parseSegments("")
        assertTrue("空文本→空列表", segments.isEmpty())
        assertEquals("空文本→总时长 0", 0L, totalMs)
    }

    @Test
    fun parseSegments_commentBetweenExtinfAndUri() {
        val playlist = """
            #EXTM3U
            #EXTINF:10,
            # some comment line
            seg3.ts
        """.trimIndent()
        val (segments, totalMs) = M3u8Parser.parseSegments(playlist)
        assertEquals("EXTINF 与 URI 间夹注释行仍取到 URI", listOf("seg3.ts"), segments)
        assertEquals("总时长 10000ms", 10000L, totalMs)
    }

    // ==================== M3u8Parser.pickBestVariant ====================

    @Test
    fun pickBestVariant_multiRate_picksHighestBandwidth() {
        val master = """
            #EXTM3U
            #EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
            low.m3u8
            #EXT-X-STREAM-INF:AVERAGE-BANDWIDTH=99999999,BANDWIDTH=2000000,RESOLUTION=1920x1080
            high.m3u8
            #EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720
            mid.m3u8
        """.trimIndent()
        assertEquals(
            "选 BANDWIDTH 最高者（AVERAGE-BANDWIDTH 干扰被剥离，B10）",
            "high.m3u8",
            M3u8Parser.pickBestVariant(master)
        )
    }

    @Test
    fun pickBestVariant_singleVariant() {
        val master = """
            #EXTM3U
            #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=1280x720
            only.m3u8
        """.trimIndent()
        assertEquals("单一 variant 返回该地址", "only.m3u8", M3u8Parser.pickBestVariant(master))
    }

    @Test
    fun pickBestVariant_noStreamInf_returnsNull() {
        val media = """
            #EXTM3U
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        assertNull("纯媒体清单无 STREAM-INF → null", M3u8Parser.pickBestVariant(media))
    }

    // ==================== M3u8Parser.resolveRelative ====================

    @Test
    fun resolveRelative_absoluteUrlReturnedAsIs() {
        assertEquals(
            "绝对 URL 原样返回",
            "https://b.example/x/abs.ts",
            M3u8Parser.resolveRelative("https://a.example/v/index.m3u8", "https://b.example/x/abs.ts")
        )
    }

    @Test
    fun resolveRelative_relativePath() {
        assertEquals(
            "相对路径按 base 目录解析",
            "https://a.example/v/seg0.ts",
            M3u8Parser.resolveRelative("https://a.example/v/index.m3u8", "seg0.ts")
        )
    }

    @Test
    fun resolveRelative_pathWithQuery() {
        assertEquals(
            "带 query 的相对路径",
            "https://a.example/v/seg.ts?token=abc",
            M3u8Parser.resolveRelative("https://a.example/v/index.m3u8", "seg.ts?token=abc")
        )
    }

    @Test
    fun resolveRelative_uriParseFailureFallsBackToTrim() {
        assertEquals(
            "URI 解析失败（含空格）退化为 base 截断拼接",
            "https://a.example/v/a b.ts",
            M3u8Parser.resolveRelative("https://a.example/v/", "a b.ts")
        )
    }

    // ==================== M3u8Parser.parseKeyInfo ====================

    @Test
    fun parseKeyInfo_aes128WithUriAndIv() {
        val playlist = """
            #EXTM3U
            #EXT-X-KEY:METHOD=AES-128,URI="https://a.example/hls/key.key",IV=0x000102030405060708090a0b0c0d0e0f
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        val key = M3u8Parser.parseKeyInfo(playlist)
        assertTrue("命中 KEY 行", key != null)
        key!!
        assertEquals("METHOD=AES-128", "AES-128", key.method)
        assertEquals("URI 属性提取", "https://a.example/hls/key.key", key.uri)
        val expectedIv = ByteArray(16) { it.toByte() }
        assertTrue("IV 十六进制→16 字节（0x00..0x0f）", key.iv != null && key.iv.contentEquals(expectedIv))
    }

    @Test
    fun parseKeyInfo_quotedMethod() {
        val playlist = """#EXT-X-KEY:METHOD="AES-128",URI="k.key""""
        val key = M3u8Parser.parseKeyInfo(playlist)
        assertTrue(key != null)
        key!!
        assertEquals("带引号 METHOD 兼容", "AES-128", key.method)
        assertEquals("URI 属性提取", "k.key", key.uri)
        assertNull("未声明 IV → null", key.iv)
    }

    @Test
    fun parseKeyInfo_noKeyLine_returnsNull() {
        val playlist = """
            #EXTM3U
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        assertNull("无 KEY 行 → null", M3u8Parser.parseKeyInfo(playlist))
    }

    // ==================== M3u8Parser.parseMediaSequence ====================

    @Test
    fun parseMediaSequence_extracted() {
        val playlist = """
            #EXTM3U
            #EXT-X-MEDIA-SEQUENCE:2680
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        assertEquals("提取媒体序号起点", 2680L, M3u8Parser.parseMediaSequence(playlist))
    }

    @Test
    fun parseMediaSequence_missingDefaultsToZero() {
        assertEquals(
            "缺失 #EXT-X-MEDIA-SEQUENCE → 0",
            0L,
            M3u8Parser.parseMediaSequence("#EXTM3U\n#EXTINF:10,\nseg1.ts")
        )
    }

    // ==================== HeaderResolver headersJson 协议 ====================
    // merge/buildHeaders 依赖 android.webkit.CookieManager，JVM 不可测（留 L2/Robolectric）

    @Test
    fun headersJson_roundTrip() {
        val headers = mapOf(
            "User-Agent" to "UA-Test/1.0",
            "Referer" to "https://r.example/page",
            "Cookie" to "k1=v1; k2=v2"
        )
        val json = HeaderResolver.toJsonHeaders(headers)
        assertTrue("非空 map 序列化为非空 JSON", json.isNotBlank())
        assertEquals("往返一致", headers, HeaderResolver.fromJsonHeaders(json))
    }

    @Test
    fun toJsonHeaders_emptyMapReturnsEmptyString() {
        assertEquals("空 map → 空串", "", HeaderResolver.toJsonHeaders(emptyMap()))
    }

    @Test
    fun fromJsonHeaders_nullOrBlankReturnsEmptyMap() {
        assertEquals("null → 空 map", emptyMap<String, String>(), HeaderResolver.fromJsonHeaders(null))
        assertEquals("空串 → 空 map", emptyMap<String, String>(), HeaderResolver.fromJsonHeaders(""))
        assertEquals("空白串 → 空 map", emptyMap<String, String>(), HeaderResolver.fromJsonHeaders("  "))
    }

    @Test
    fun fromJsonHeaders_invalidJsonReturnsEmptyMap() {
        assertEquals(
            "非法 JSON → 空 map（失败路径走 AppLog.put，JVM 安全）",
            emptyMap<String, String>(),
            HeaderResolver.fromJsonHeaders("{not-a-json")
        )
    }

    @Test
    fun fromJsonHeaders_jsonNullReturnsEmptyMap() {
        assertEquals(
            "JSON null（gson 返回 null，orEmpty 兜底）→ 空 map",
            emptyMap<String, String>(),
            HeaderResolver.fromJsonHeaders("null")
        )
    }

    // ==================== SniffModels ====================

    @Test
    fun sniffResult_urlDelegatesToSelected() {
        val candidate = SniffCandidate(url = "https://x.example/v/index.m3u8")
        val result = SniffResult(candidates = listOf(candidate), selected = candidate)
        assertEquals("url = selected?.url", "https://x.example/v/index.m3u8", result.url)
    }

    @Test
    fun sniffResult_noSelection_urlNull() {
        assertNull("selected=null → url=null", SniffResult().url)
    }

    // ==================== M3u8Parser variant 感知（video-sniff-403-and-rss-classic-fix Phase 4 / 5.4）====================

    @Test
    fun isMasterPlaylist_streamInfTrueMediaFalse() {
        val master = """
            #EXTM3U
            #EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1920x1080
            high.m3u8
        """.trimIndent()
        assertTrue("含 #EXT-X-STREAM-INF → master 清单", M3u8Parser.isMasterPlaylist(master))
        val media = """
            #EXTM3U
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        assertTrue("纯媒体清单非 master", !M3u8Parser.isMasterPlaylist(media))
        assertTrue("空文本非 master", !M3u8Parser.isMasterPlaylist(""))
    }

    @Test
    fun pickVariantFromText_masterPicksHighestAndResolvesRelative() {
        val master = """
            #EXTM3U
            #EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
            low/index.m3u8
            #EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1920x1080
            high/index.m3u8
        """.trimIndent()
        assertEquals(
            "master 选 BANDWIDTH 最高者并 resolve 为绝对地址",
            "https://a.example/v/high/index.m3u8",
            M3u8Parser.pickVariantFromText(master, "https://a.example/v/master.m3u8")
        )
    }

    @Test
    fun pickVariantFromText_nonMasterReturnsNull() {
        val media = """
            #EXTM3U
            #EXTINF:10,
            seg1.ts
        """.trimIndent()
        assertNull(
            "媒体清单返回 null（调用方按原地址当媒体清单处理）",
            M3u8Parser.pickVariantFromText(media, "https://a.example/v/media.m3u8")
        )
    }

    // ==================== SniffEngine.score（Phase 4 / 5.3，纯 JVM 可测：不触 CookieManager/网络）====================

    @Test
    fun score_typeWeight_manifestBeatsNewerSegment() {
        val segment = SniffCandidate(
            url = "https://x.example/v/seg-0.ts",
            source = SniffCandidate.SOURCE_WEBVIEW_INTERCEPT,
            timestamp = 2000L  // 分片命中更晚（广告分片先命中场景的镜像）
        )
        val manifest = SniffCandidate(
            url = "https://x.example/v/index.m3u8",
            source = SniffCandidate.SOURCE_WEBVIEW_INTERCEPT,
            timestamp = 1000L
        )
        val best = SniffEngine.score(listOf(segment, manifest))
        assertEquals(
            "类型权重优先：清单胜过更新的分片（时序加成上限低于类型分档差）",
            "https://x.example/v/index.m3u8",
            best?.url
        )
    }

    @Test
    fun score_recency_prefersNewerAmongSameType() {
        val older = SniffCandidate(url = "https://x.example/a/old.mp4", timestamp = 1000L)
        val newer = SniffCandidate(url = "https://x.example/b/new.mp4", timestamp = 9000L)
        val best = SniffEngine.score(listOf(older, newer))
        assertEquals(
            "同类型时新者优先（规避广告先命中）",
            "https://x.example/b/new.mp4",
            best?.url
        )
    }
}
