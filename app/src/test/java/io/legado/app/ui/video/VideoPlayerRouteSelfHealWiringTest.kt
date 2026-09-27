package io.legado.app.ui.video

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-13：**首线路失败自动换线**（用户可见）接线不变量。
 *
 * 落点说明：线路上下文（多线路列表 + 播放器实例 + 线路选择器 UI）**只存在于 Activity**，
 * 因此换线动作必须落在 `VideoPlayerActivity` 的统一错误观察点；裁决本身收敛在
 * `PlaybackErrorPolicy.decideRouteSelfHeal`（纯函数，另见其单测）。
 *
 * 三条易失守约定：① 观察点必须先尝试自愈、成功则不弹错误框；② 换线入口必须与线路选择器
 * **同一入口**（避免两条分叉）；③ 文案必须双 strings 齐备且含线路名占位符。
 */
class VideoPlayerRouteSelfHealWiringTest {

    private fun res(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val activity by lazy { res("src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt") }
    private val stringsEn by lazy { res("src/main/res/values/strings.xml") }
    private val stringsZh by lazy { res("src/main/res/values-zh/strings.xml") }

    @Test
    fun errorObserverTriesSelfHealBeforeShowingDialog() {
        val observerAt = activity.indexOf("observeEvent<String>(EventBus.VIDEO_PLAY_ERROR)")
        assertTrue("未找到统一错误观察点", observerAt > 0)
        val healAt = activity.indexOf("if (tryAutoSwitchRouteOnError(it)) return@observeEvent", observerAt)
        val dialogAt = activity.indexOf("showVideoPlayErrorDialog(it)", observerAt)
        assertTrue("观察点须先尝试换线自愈", healAt > observerAt)
        assertTrue("换线自愈须在错误对话框之前（成功则不弹框）", healAt < dialogAt)
    }

    @Test
    fun decisionIsDelegatedToPurePolicyFunction() {
        assertTrue(
            "裁决须复用 PlaybackErrorPolicy.decideRouteSelfHeal（纯函数，单测锁定）",
            activity.contains("PlaybackErrorPolicy.decideRouteSelfHeal(")
        )
        assertTrue("不允许换线时须放弃并回错误提示", activity.contains("if (!decision.allowed) {"))
    }

    @Test
    fun switchUsesSameEntrancesAsRouteSelector() {
        assertTrue("新模式换线入口须与线路选择器一致", activity.contains("VideoPlay.switchToRoute(to, playerView)"))
        assertTrue("旧模式换线入口须与线路选择器一致", activity.contains("VideoPlay.switchRssRoute(to)"))
        assertTrue("切线路后须播放该线路首集", activity.contains("VideoPlay.playRssEpisode(playerView, episode)"))
        assertTrue("切线路须刷新线路/集数列表 UI", activity.contains("upRssRoutesView()"))
    }

    @Test
    fun toastTextIsRegisteredInBothStringFiles() {
        assertTrue(stringsEn.contains("name=\"video_route_self_heal_toast\""))
        assertTrue(stringsZh.contains("name=\"video_route_self_heal_toast\""))
        assertTrue("英文文案须含线路名占位符", stringsEn.contains("switched to line: %1\$s"))
        assertTrue("中文文案须含线路名占位符", stringsZh.contains("已自动切换到线路：%1\$s"))
        assertTrue(
            "换线成功后须给用户可见回执（线路名）",
            activity.contains("getString(R.string.video_route_self_heal_toast, routes[to].name)")
        )
    }

    @Test
    fun selfHealEmitsDiagnosableLogs() {
        assertEquals(true, activity.contains("VideoRouteSelfHeal: 换线"))
        assertEquals(true, activity.contains("VideoRouteSelfHeal: 跳过换线"))
    }
}