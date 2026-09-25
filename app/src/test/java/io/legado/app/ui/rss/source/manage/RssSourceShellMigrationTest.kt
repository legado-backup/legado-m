package io.legado.app.ui.rss.source.manage

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：订阅源管理页（`activity_rss_source`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景与书源管理页**同构**：原 XML = `LinearLayout`（`TitleBar@title_bar` 带 `contentLayout=view_search` +
 * `FrameLayout` 内 `FastScrollRecyclerView`），宿主 `initComposeContent()` 早已把两者作废并手拼 `ComposeView`
 * 插回原索引位 ⇒ XML 是**死壳**，换装只做「运行时装配 → 合成壳单源」。
 */
class RssSourceShellMigrationTest {

    private val page = "ui/rss/source/manage/RssSourceActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
        assertFalse("不再需要摘取父容器/占位索引", s.contains("container.addView(cv, index)"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityRssSourceBinding"))
        assertFalse("不得再引用已退役的 titleBar 节点", s.contains("binding.titleBar"))
        assertFalse("不得再引用已退役的 recyclerView 节点", s.contains("binding.recyclerView"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_rss_source.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_rss_source.xml").exists()
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun initGroupFlow(",
            "private fun upSourceFlow(",
            "private fun showFilterMenu(",
            "private fun pageMenuActions(",
            "private fun showImportDialog(",
            "private fun toggleSourceSelection(",
            "private fun sourceMenuActions(",
            "private fun sameRssSourceListContent(",
            "private fun updateSearchQuery(",
            "private fun checkSelectedInterval(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 写回必须走 SnapshotListUpdates（既有实机铁证：直接下标写不落地）
        assertTrue("列表写回必须仍走 replaceAt", s.contains("sourcesState.replaceAt(index, updated)"))
    }
}