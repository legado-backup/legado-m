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

    private val js: String = BackstageWebView.playNudgeScript()

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
}
