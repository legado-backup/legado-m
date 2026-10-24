package io.legado.app.help.exoplayer

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-14（AD-05）：`sniffVideoType` **赛马化接线**不变量。
 *
 * 三条易失守的约定：
 * 1. 开关 / 冷却期必须回落**原串行链**（零回归回滚点），且串行链内部逐行等价改造前；
 * 2. 四段确定性短路（本地文件 / 非法 scheme / HTML 接口 / `.m3u8` 后缀）必须**留在赛马之前**；
 * 3. 策略集与预置决策一致：并发上限 2、后缀兜底不抢占、m3u8 预检仅在后缀不可判定时加入。
 */
class ExoPlayerHelperSniffRaceWiringTest {

    private val helper by lazy {
        listOf(
            File("src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt"),
            File("../app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt"),
            File("app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun raceIsGatedBySwitchAndCooldownWithSerialFallback() {
        assertTrue(
            "须以「开关关闭 或 冷却期」回落串行链",
            helper.contains("if (!AppConfig.sniffRaceEnabled || !sniffRaceLimiter.canRace())")
        )
        assertTrue("串行链须独立成函数（回滚点）", helper.contains("private suspend fun sniffVideoTypeSerial("))
        assertTrue(
            "串行链须保留改造前的超时日志与后缀兜底",
            helper.contains("sniffVideoType: timeout (") && helper.contains("sniffByExtensionFallback(url, \"timeout ")
        )
    }

    @Test
    fun manifestDetectorIsAvailableForPlaybackFallbackOrdering() {
        // 2026-10-24：播放侧降级链排序需要「内容是否 m3u8」的确定结论（否则注定失败的 HLS
        // 解析会让 GSY 释放播放器 ⇒ 黑屏）
        assertEquals("必须提供内容预检入口", true, helper.contains("suspend fun detectM3u8Manifest("))
        assertEquals(
            "预检明确失败须能区分返回 false",
            true,
            helper.contains("is M3u8PreCheckDataSource.PreCheckResult.Fail ->")
        )
        assertEquals("预检超时预算须 ≥3s（弱网/CDN 冷启动）", true, helper.contains("timeoutMs: Long = 6000L"))
    }

    @Test
    fun deterministicShortCircuitsStayBeforeRace() {
        val raceAt = helper.indexOf("SniffRace.race(")
        assertTrue("未找到赛马调用", raceAt > 0)
        assertTrue("file:// 短路须在赛马前", helper.indexOf("if (url.startsWith(\"file://\"))") < raceAt)
        assertTrue("非法 scheme 短路须在赛马前", helper.indexOf("if (!url.startsWith(\"http://\")") < raceAt)
        assertTrue("HTML 接口短路须在赛马前", helper.indexOf("if (isHtmlInterfaceUrl(url))") < raceAt)
        val m3u8ShortCircuit = "url.lowercase().substringBefore(\"?\").substringBefore(\"#\").endsWith(\".m3u8\")"
        val m3u8At = helper.indexOf(m3u8ShortCircuit)
        assertTrue("m3u8 后缀短路须存在", m3u8At > 0)
        assertTrue("m3u8 后缀短路须在赛马前", m3u8At < raceAt)
    }

    @Test
    fun raceUsesPresetConcurrencyAndTotalTimeout() {
        assertTrue("并发上限须取 SniffRace 预置值（2）", helper.contains("maxConcurrent = SniffRace.DEFAULT_MAX_CONCURRENT"))
        assertTrue("总超时不得放宽（沿用既有 5s）", helper.contains("totalTimeoutMs = SNIFF_TIMEOUT_MS"))
        assertEquals(true, helper.contains("private const val SNIFF_TIMEOUT_MS = 5000L"))
    }

    @Test
    fun strategySetMatchesDesignDecisions() {
        // 后缀兜底：零请求 + 不抢占
        assertTrue(helper.contains("name = \"Extension\""))
        assertTrue(helper.contains("canWin = false"))
        assertTrue(helper.contains("networkBound = false"))
        // 权威 Range：既有实现零改动，UNKNOWN 不参与抢占
        assertTrue(helper.contains("sniffWithRangeRequestR4(u, h).takeIf { it.contentType != SniffResult.TYPE_UNKNOWN }"))
        // m3u8 预检：仅在后缀不可判定时加入（控请求面）
        val gateAt = helper.indexOf("if (guessTypeByUrl(url) == null)")
        val preCheckAt = helper.indexOf("name = \"M3u8PreCheck\"")
        assertTrue("m3u8 预检策略须带「后缀不可判定」门禁", gateAt > 0 && preCheckAt > gateAt)
    }

    @Test
    fun limiterFeedsFailureSuccessSignals() {
        assertTrue("全灭须记一次失败（触发冷却）", helper.contains("sniffRaceLimiter.noteFailure()"))
        assertTrue("有权威结果须记成功（打断连续失败）", helper.contains("sniffRaceLimiter.noteSuccess()"))
    }
}