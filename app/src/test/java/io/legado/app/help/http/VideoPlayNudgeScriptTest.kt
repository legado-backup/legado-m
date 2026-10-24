package io.legado.app.help.http

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 播放页「自动播放轻推」脚本不变量（2026-10-24 真机实证补丁）。
 *
 * 真机故障：采集站播放页必须先点播放才发 m3u8 请求；后台嗅探无手势 ⇒ 160 次嗅探 0 命中，
 * 播放与缓存同时失败。轻推脚本负责在播放器区域内触发一次播放。
 *
 * 本测试锁定三条不可失守的约定：
 * 1. 必须静音 + playsinline（后台 WebView 无手势依赖，非静音会被拦截）；
 * 2. 必须调用 video.play()（只 click 不 play 在部分播放器上无效）；
 * 3. 点击必须**限流**（≤3 次）且限定在含 video 的播放器区域内（防误触广告）。
 */
class VideoPlayNudgeScriptTest {

    private val js: String = VideoSniffPolicy.PLAY_NUDGE_JS

    @Test
    fun mutesAndPlaysInlineForBackgroundWebView() {
        assertEquals("必须静音后播放", true, js.contains("v.muted=true"))
        assertEquals("必须设置 playsinline", true, js.contains("playsinline"))
    }

    @Test
    fun callsPlayOnVideoElements() {
        assertEquals("必须调用 video.play()", true, js.contains("v.play()"))
    }

    @Test
    fun clickCountIsBoundedAndScopedToPlayerArea() {
        assertTrue("点击次数须限流 ≤3（防广告连环弹）", js.contains("n<3"))
        assertEquals("点击须限定在含 video 的播放器区域", true, js.contains("querySelector('video')"))
    }

    @Test
    fun scriptReportsDiagnosticsForTroubleshooting() {
        // 真机排障需要知道「页面有没有 video 元素 / play() 是否执行 / 点了几个」，
        // 否则只能看到 0 命中却无法区分根因
        assertEquals("必须返回诊断摘要", true, js.contains("return JSON.stringify(out)"))
        assertEquals("必须统计 video 元素数量", true, js.contains("out.v=vs.length"))
        assertEquals("必须统计点击次数", true, js.contains("out.c=n"))
    }

    /**
     * 命中可交付口径（2026-10-24 真机铁证）。
     *
     * 现场：缓存逐集时嗅探会话在第 5ms 就被「命中」并 destroy，命中 URL == 播放页 URL，
     * 于是上层判 null ⇒ 每集必失败。等于会话目标页的命中必须**只入缓冲、不交付、不销毁会话**，
     * 否则 nudge 与 `window.__videoUrls__` 读取都没机会执行。
     */
    @Test
    fun samePageRequestIsNotDeliverable() {
        val page = "https://example.com/play/abc.html"
        assertEquals("命中 URL 与会话目标页相同时不可交付", false, VideoSniffPolicy.isDeliverableHit(page, page))
        assertEquals(
            "真实媒体直链（不同 URL）可交付",
            true,
            VideoSniffPolicy.isDeliverableHit("https://cdn.example.com/x/index.m3u8", page)
        )
    }

    @Test
    fun tsSegmentsAreNotDeliverable() {
        val page = "https://example.com/play/abc.html"
        assertEquals(
            "HLS 分片必须只入缓冲（ExoPlayer 需 m3u8 主索引）",
            false,
            VideoSniffPolicy.isDeliverableHit("https://cdn.example.com/x/seg001.ts?t=1", page)
        )
        assertEquals(
            "无会话页时仍按分片规则排除",
            false,
            VideoSniffPolicy.isDeliverableHit("https://cdn.example.com/x/SEG002.TS", null)
        )
    }

    /**
     * 候选形态分类（诊断口径，2026-10-24 真机排障所需）。
     *
     * 需要区分「播放器走 MSE ⇒ 流地址只在分片请求里」与「直链 URL 形态不匹配源正则」，
     * 否则只能看到 0 命中却无法定位根因。
     */
    @Test
    fun candidateShapeClassifiesMseAndHttpUrls() {
        val urls = listOf(
            "https://cdn.example.com/x/index.m3u8",
            "__MSE__:blob:https://example.com/1a2b",
            "__MSE_MIME__:application/vnd.apple.mpegurl",
            "blob:https://example.com/3c4d"
        )
        val shape = VideoSniffPolicy.classifyCandidates(urls) { it.endsWith(".m3u8") }
        assertEquals("总数", 4, shape.total)
        assertEquals("http 直链数", 1, shape.http)
        assertEquals("MSE/blob 数", 2, shape.blobOrMse)
        assertEquals("MIME 标记数", 1, shape.mime)
        assertEquals("匹配数", 1, shape.matched)
    }

    @Test
    fun candidateShapeFlagsUnmatchedHttpUrls() {
        // 直链 URL 存在但形态不匹配源正则：分类必须能暴露这一根因
        val shape = VideoSniffPolicy.classifyCandidates(listOf("https://cdn.example.com/stream?id=9")) { false }
        assertEquals(0, shape.blobOrMse)
        assertEquals(1, shape.http)
        assertEquals(0, shape.matched)
    }
}
