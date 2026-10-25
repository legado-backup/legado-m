package io.legado.app.ui.video

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 传统布局内嵌选集面板接线（episode-switch-loading-and-legacy-inline C3）。
 *
 * 断言三件事：
 * 1. 书源/订阅源两条链都把分组面板绑定到 `chapters_container`（不再只靠弹框入口）；
 * 2. 内嵌面板与弹框共用同一个 binder 与同一个点击入口（防止双实现漂移）；
 * 3. 单集/无集时面板隐藏（不出现空占位）。
 */
class VideoLegacyInlinePanelWiringTest {

    private val src: String by lazy {
        SourceFileProbe.sourceText("ui/video/VideoPlayerActivity.kt")
    }

    @Test
    fun bookAndRssChainsBothBindInlinePanel() {
        // 定义 1 处 + 调用 3 处（书源 showToc / 订阅源 showRssEpisodes / 切卷重绑）
        assertEquals(3, Regex("bindInlineEpisodePanel\\(").findAll(src).count() - 1)
        assertTrue(src.contains("titles = toc.map { it.title }"))
        assertTrue(src.contains("titles = episodes.map { it.title }"))
    }

    @Test
    fun inlinePanelSharesSingleBinderAndSelectionEntry() {
        // 弹框与内嵌共用同一 binder 类型
        assertTrue(src.contains("EpisodePanelBinder("))
        // 两个入口（内嵌面板回调 + 弹框回调）都收敛到同一选集方法
        assertEquals(1, Regex("private fun selectEpisodeAt\\(").findAll(src).count())
        assertEquals(2, Regex("selectEpisodeAt\\(position\\)").findAll(src).count())
    }

    @Test
    fun panelHiddenWhenNoEpisodes() {
        // 无集/单集隐藏：bindInline 早退 + 书源无集 + 订阅源无集 + 单URL 直连，共 4 处
        assertEquals(4, Regex("binding\\.episodePanel\\.root\\.gone\\(\\)").findAll(src).count())
        assertTrue(src.contains("if (titles.size <= 1)"))
    }
}
