package io.legado.app.help.gsyVideo

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-86 续：视频播放器静音开关必须**单源**。
 *
 * 缺陷背景（此前未发现）：`VideoPlayer.toggleMute()` 零调用，而 `initView` 中 `ivMute` 的点击回调
 * **逐字复制**了它的实现（`isMuted = !isMuted` + `setNeedMute` + `updateMuteIcon`）
 * ⇒ 同一判据两份实现（改一处忘另一处，日后极易漂移）。本批已单源化：回调改为调用 `toggleMute()`。
 *
 * 锁定两件事：
 * ① 点击回调必须走单源函数（而非内联复制）；
 * ② 状态翻转语句在文件内只允许出现一次（出现 2 次即视为重复实现回流）。
 */
class VideoPlayerMuteSingleSourceTest {

    private val src by lazy { SourceFileProbe.sourceText("help/gsyVideo/VideoPlayer.kt") }

    @Test
    fun `静音点击回调必须调用单源 toggleMute`() {
        assertEquals("回调须单源调用", true, src.contains("setOnClickListener { toggleMute() }"))
        assertEquals("单源实现须存在", true, src.contains("fun toggleMute()"))
    }

    @Test
    fun `静音状态翻转语句不得内联复制`() {
        val flips = Regex("isMuted\\s*=\\s*!isMuted").findAll(src).count()
        assertEquals("静音翻转语句必须只有一处（单源），禁止内联复制回流", 1, flips)
    }
}
