package io.legado.app.help.video

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 切集加载反馈闭环（episode-switch-loading-and-legacy-inline C1/C2）。
 *
 * 契约：发起切集 ⇒ 立即置 true；setUp 下发（采集/嗅探空窗结束）⇒ 置 false；
 * 失败与页面停止由观察者兜底收起。本测试锁定三处必达点，防止后续改动漏掉收起点
 * 导致遮罩永久残留（spec Drawbacks 明确列出的风险）。
 */
class SwitchLoadingFeedbackContractTest {

    @Test
    fun pipelineClearsLoadingOnBothChains() {
        val pipeline = SourceFileProbe.sourceText("help/video/VideoPlaybackPipeline.kt")
        // 书源 setUpAndPlay + 订阅源 playEpisode 各一次收起
        assertEquals(
            2,
            Regex("postEvent\\(EventBus\\.VIDEO_SWITCH_LOADING, false\\)")
                .findAll(pipeline).count()
        )
        assertTrue(pipeline.contains("postEvent(EventBus.VIDEO_SUB_TITLE"))
    }

    @Test
    fun switchEntryPointsRaiseLoading() {
        val videoPlay = SourceFileProbe.sourceText("model/VideoPlay.kt")
        // 书源章节入口 + 订阅源集入口各一次置 true
        assertEquals(
            2,
            Regex("postEvent\\(EventBus\\.VIDEO_SWITCH_LOADING, true\\)")
                .findAll(videoPlay).count()
        )
        assertTrue(videoPlay.contains("private fun startPlayBookChapter"))
        assertTrue(videoPlay.contains("fun playRssEpisode"))
    }

    @Test
    fun activityHidesOnErrorAndStop() {
        val activity = SourceFileProbe.sourceText("ui/video/VideoPlayerActivity.kt")
        assertTrue(activity.contains("observeEvent<Boolean>(EventBus.VIDEO_SWITCH_LOADING)"))
        // 错误观察者收起 + onStop 收起（两处兜底）
        assertEquals(
            2,
            Regex("binding\\.switchLoading\\.gone\\(\\)").findAll(activity).count()
        )
    }
}
