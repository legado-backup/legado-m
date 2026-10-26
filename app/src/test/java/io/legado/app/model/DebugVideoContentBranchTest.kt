package io.legado.app.model

import io.legado.app.constant.BookSourceType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 视频类源 content 调试结论 单元测试（design AD-02 / tasks 3.2 / spec Requirement A-2）。
 *
 * 断言要点：三种结论（成功地址 / 额度外或取流不可用 / 交内置浏览器）各有**明确期望输出**，
 * 且非视频源行为不变（不引入新判定）。
 */
class DebugVideoContentBranchTest {

    private val video = BookSourceType.video

    @Test
    fun playUrl_isReportedAsSuccess() {
        val c = DebugVideoConclusion.of(video, "https://site-a.example/player/1", browserMode = false)
        assertEquals("返回可播放地址应判 PLAY_URL", DebugVideoConclusion.Outcome.PLAY_URL, c.outcome)
        assertTrue("结论文案应提示可与真机试播对照", c.message.contains("取流成功"))
    }

    @Test
    fun lockedEpisode_emptyContent_isReportedAsUnavailable() {
        val c = DebugVideoConclusion.of(video, "", browserMode = false)
        assertEquals("未返回地址应判 UNAVAILABLE", DebugVideoConclusion.Outcome.UNAVAILABLE, c.outcome)
        assertTrue("应给出可读原因（额度/页面环境）", c.message.contains("取流不可用"))
        assertTrue("应提示可切换内置浏览器再试", c.message.contains("内置浏览器"))
    }

    @Test
    fun browserMode_isReportedAsBrowserOnly() {
        val c = DebugVideoConclusion.of(video, "", browserMode = true)
        assertEquals("浏览器模式下空返回应判 BROWSER_ONLY", DebugVideoConclusion.Outcome.BROWSER_ONLY, c.outcome)
        assertTrue("应说明取流由网页播放器完成", c.message.contains("内置浏览器"))
    }

    @Test
    fun browserMode_stillPreferRealUrlWhenPresent() {
        val c = DebugVideoConclusion.of(video, "https://site-a.example/x.m3u8", browserMode = true)
        assertEquals(
            "有真实地址时优先报取流成功（不被浏览器模式掩盖）",
            DebugVideoConclusion.Outcome.PLAY_URL,
            c.outcome,
        )
    }

    @Test
    fun nonVideoSource_behaviorUnchanged() {
        val ok = DebugVideoConclusion.of(BookSourceType.default, "正文内容", browserMode = false)
        assertEquals("非视频源有内容即成功", DebugVideoConclusion.Outcome.PLAY_URL, ok.outcome)

        val empty = DebugVideoConclusion.of(BookSourceType.default, "  ", browserMode = true)
        assertEquals("非视频源空内容即不可用（不受 browserMode 影响）",
            DebugVideoConclusion.Outcome.UNAVAILABLE, empty.outcome)
    }

    // ============ 正文为空的成因区分（真机 2026-10-26：浏览器模式空正文被误报为规则失败） ============

    @Test
    fun playModeOf_readsFromVariableString() {
        assertEquals("从 k=v; 串取 playmode", "browser",
            DebugVideoConclusion.playModeOf("playmode=browser;diag=1"))
        assertEquals("兼容 & 分隔", "browser", DebugVideoConclusion.playModeOf("diag=1&playmode=browser"))
        assertEquals("键序无关", "browser", DebugVideoConclusion.playModeOf("Playmode=x\nplaymode=browser"))
        assertEquals("缺失 ⇒ 空串", "", DebugVideoConclusion.playModeOf("diag=1"))
        assertEquals("null 安全", "", DebugVideoConclusion.playModeOf(null))
    }

    @Test
    fun emptyContentHint_browserModeSaysExpected() {
        val hint = DebugVideoConclusion.emptyContentHint(video, "playmode=browser")
        assertTrue("浏览器模式下必须说明空正文属预期（不得让用户以为是规则坏了）", hint.contains("属预期"))
        assertTrue("必须说明播放已交由浏览器页", hint.contains("浏览器页"))
    }

    @Test
    fun emptyContentHint_sniffModeSaysNoAddressWithActions() {
        val hint = DebugVideoConclusion.emptyContentHint(video, "playmode=")
        assertTrue("非浏览器模式应说明未取到地址", hint.contains("未提取到可播放地址"))
        assertTrue("应给出可操作下一步（登录 / 切浏览器模式）",
            hint.contains("登录") && hint.contains("内置浏览器播放"))
    }

    @Test
    fun emptyContentHint_nonVideoIsEmpty() {
        assertEquals("非视频源不追加视频专属提示（避免污染普通正文结论）", "",
            DebugVideoConclusion.emptyContentHint(BookSourceType.default, "playmode=browser"))
    }
}