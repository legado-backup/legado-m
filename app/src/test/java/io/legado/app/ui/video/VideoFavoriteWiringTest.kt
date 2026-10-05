package io.legado.app.ui.video

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-live-favorite-fix AD-02/AD-03：收藏入口三处调用点的**接线不变量**。
 *
 * 锁定的四条易失守约定（本次缺陷的成因正是它们各自为政）：
 * ① 可见性判定必须**三处同源**（Activity 顶栏 / Fragment 悬浮 / Activity 传统布局）⇒ 全部走 `canFavoriteCurrent()`；
 * ② 收藏按钮状态必须**首次进入即刷新**（此前只在收藏增删改后刷新 ⇒ 顶栏进入恒不显示），切文章/切线路后也要刷新；
 * ③ 收藏动作必须是「有则编辑 / 记录转收藏 / 当前构造入库」三段式，且**不得静默**（失败须 toast）；
 * ④ 新增文案须双 strings（values + values-zh）齐备。
 */
class VideoFavoriteWiringTest {

    private fun res(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val activity by lazy { res("src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt") }
    private val fragment by lazy { res("src/main/java/io/legado/app/ui/video/VideoFragment.kt") }
    private val viewModel by lazy { res("src/main/java/io/legado/app/ui/video/VideoPlayerViewModel.kt") }
    private val stringsEn by lazy { res("src/main/res/values/strings.xml") }
    private val stringsZh by lazy { res("src/main/res/values-zh/strings.xml") }

    @Test
    fun visibilityIsSingleSourcedAcrossThreeCallSites() {
        assertTrue(
            "顶栏可见性须走单源判定",
            activity.contains("starVisible = VideoPlay.canFavoriteCurrent()")
        )
        assertTrue(
            "悬浮星标可见性须走同一判定",
            fragment.contains("if (VideoPlay.canFavoriteCurrent())")
        )
        assertTrue(
            "传统布局图标同步须被接线（此前从未调用）",
            Regex("""upLegacyStarState\(\)""").findAll(activity).count() >= 2
        )
        // 旧口径必须消失（否则又会漂移）
        assertEquals(
            false,
            fragment.contains("val showStar = VideoPlay.book == null && !VideoPlay.singleUrl")
        )
        assertEquals(
            false,
            activity.contains("starVisible = VideoPlay.rssStar != null || VideoPlay.rssRecord != null")
        )
    }

    @Test
    fun starStateRefreshedOnEntryAndOnArticleSwitch() {
        // 调用点：① LiveData 观察者 ② initSource 成功块（首次进入）③ UP_VIDEO_INFO（切文章/线路/集）
        val calls = Regex("""upStarMenu\(\)""").findAll(activity).count()
        assertTrue("upStarMenu 应有定义 + ≥3 处调用，实际=$calls", calls >= 4)
        val infoAt = activity.indexOf("observeEvent<ArrayList<Int>>(EventBus.UP_VIDEO_INFO)")
        assertTrue(
            "切文章/切线路后须刷新收藏状态",
            activity.indexOf("upStarMenu()", infoAt) > infoAt
        )
    }

    @Test
    fun addFavoriteIsThreeStageAndNeverSilent() {
        assertTrue("③ 当前条目直接构造", viewModel.contains("VideoPlay.buildCurrentStar()"))
        assertTrue("② 记录转收藏保留", viewModel.contains("VideoPlay.rssRecord?.toStar()"))
        assertTrue("失败须给出提示（不静默）", viewModel.contains("R.string.video_favorite_no_context"))
        assertEquals(
            "旧的「静默空转」写法须消失",
            false,
            viewModel.contains("VideoPlay.rssStar ?: VideoPlay.rssRecord?.toStar()?.let {")
        )
    }

    @Test
    fun toastTextRegisteredInBothStringFiles() {
        assertTrue(stringsEn.contains("name=\"video_favorite_no_context\""))
        assertTrue(stringsZh.contains("name=\"video_favorite_no_context\""))
    }
}