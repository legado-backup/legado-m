package io.legado.app.ui.book.source.debug

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 调试页「一键跑全链」（A-4）与「试播地址提取」（A-5）单元测试（design AD-02 / tasks 3.9 / 3.10）。
 *
 * 断言要点：
 * 1. 全链键一律**从最上游起点**开始（URL ⇒ 详情链；关键字 ⇒ 搜索链），一次点完即串跑全链；
 * 2. 试播地址只从「正文响应」事件里取，取不到则返回 `null`（不显示可点无效的入口）；
 * 3. 地址尾部标点被清理（避免把句号/括号带进播放器）。
 */
class DebugChainAndTryPlayTest {

    // ============ A-4 全链键 ============

    @Test
    fun fullChainKey_searchTarget_usesKeywordAsSearchChain() {
        assertEquals(
            "搜索目标的全链键即关键字（Debug 会依次进入 搜索→详情→目录→正文）",
            "总裁",
            fullChainKey(BookDebugTarget.SEARCH, "总裁"),
        )
    }

    @Test
    fun fullChainKey_urlTargets_startFromInfoChain() {
        val url = "https://site-a.example/detail?series_id=1"
        listOf(BookDebugTarget.INFO, BookDebugTarget.TOC, BookDebugTarget.CONTENT).forEach { target ->
            assertEquals(
                "$target 的全链键应回到最上游（详情链起点），否则只跑该段",
                url,
                fullChainKey(target, url),
            )
        }
    }

    @Test
    fun fullChainKey_stripsMagicPrefixes() {
        val url = "https://site-a.example/player/1"
        assertEquals("应剥掉 -- 前缀，否则会被当成正文短链只跑一段",
            url, fullChainKey(BookDebugTarget.CONTENT, "--$url"))
        assertEquals("应剥掉 ++ 前缀",
            url, fullChainKey(BookDebugTarget.TOC, "++$url"))
        assertEquals("发现目标应保留 :: 形态（Debug 按该形态分发发现链）",
            "发现::$url", fullChainKey(BookDebugTarget.EXPLORE, "$url"))
    }

    // ============ A-5 试播地址提取 ============

    @Test
    fun extractTryPlayUrl_picksUrlFromContentResponse() {
        val entries = listOf(
            10 to "搜索响应 https://site-a.example/list",
            40 to "https://site-a.example/player/1",
        )
        assertEquals(
            "应取正文响应里的地址（而非搜索响应）",
            "https://site-a.example/player/1",
            extractTryPlayUrl(entries),
        )
    }

    @Test
    fun extractTryPlayUrl_prefersLastContentResponse() {
        val entries = listOf(
            40 to "https://site-a.example/player/1",
            40 to "https://site-a.example/player/2",
        )
        assertEquals("应取最后一条正文响应", "https://site-a.example/player/2", extractTryPlayUrl(entries))
    }

    @Test
    fun extractTryPlayUrl_returnsNullWhenAbsent() {
        assertNull("无正文响应时不得给出试播入口", extractTryPlayUrl(emptyList()))
        assertNull("正文响应里无 URL 时返回 null", extractTryPlayUrl(listOf(40 to "取流不可用：越权集")))
        assertNull("只有非正文响应时返回 null", extractTryPlayUrl(listOf(10 to "https://site-a.example/list")))
    }

    @Test
    fun extractTryPlayUrl_trimsTrailingPunctuation() {
        assertEquals(
            "尾部标点应被清理（否则播放器会拿到带标点的坏地址）",
            "https://site-a.example/x.m3u8",
            extractTryPlayUrl(listOf(40 to "地址：https://site-a.example/x.m3u8。")),
        )
    }
}