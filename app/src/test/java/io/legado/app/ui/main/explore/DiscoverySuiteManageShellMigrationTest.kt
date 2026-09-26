package io.legado.app.ui.main.explore

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #8（2026-09-26）：发现套件管理页（`activity_theme_manage` 共用布局的 14 个宿主之一）换装不变量。
 *
 * 本页内容区**整体迁入 Compose**（`DiscoverySuiteManageMode` 状态机驱动三个 Screen）⇒ 只做两件事：
 *   ①`composeShell(this)` + `attachComposeContent` 单源（不得回退 inflate / 手拼 ComposeView）；
 *   ②顶栏由 `installGlassTopBar` 运行时注入改为**页内直接渲染**（标题/动作仍由
 *     `topBarTitleState` / `topBarActionsState` 状态驱动，口径不变）。
 */
class DiscoverySuiteManageShellMigrationTest {

    private val rel = "ui/main/explore/DiscoverySuiteManageActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(rel)

    @Test
    fun hostUsesSingleSourceShell() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("by viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityThemeManageBinding"))
        assertFalse("不得残留旧顶栏运行时注入", s.contains("installGlassTopBar("))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
    }

    @Test
    fun topBarRenderedInPageCompositionAndStaysStateDriven() {
        val s = src()
        assertTrue("顶栏必须页内渲染（GlassTopAppBar）", s.contains("GlassTopAppBar("))
        assertTrue("顶栏标题必须仍由状态驱动", s.contains("title = topBarTitleState"))
        assertTrue("顶栏动作必须仍由状态驱动", s.contains("TopBarActionRow(topBarActionsState)"))
        assertTrue("返回必须走页面自身的返回导航（含未保存拦截）", s.contains("onNavClick = { handleBackNavigation() }"))
        assertTrue(
            "原共用布局的 `recycler_view` 位必须由 Compose 权重表达",
            s.contains("Modifier.fillMaxWidth().weight(1f)")
        )
    }

    @Test
    fun screenModeStateMachinePreserved() {
        val s = src()
        listOf(
            "DiscoverySuiteManageMode.WidgetEditor",
            "DiscoverySuiteManageMode.Detail",
            "DiscoverySuiteWidgetEditorScreen(",
            "DiscoverySuiteDetailScreen(",
            "private fun handleBackNavigation()",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主状态机：缺少 `$marker`", s.contains(marker))
        }
    }
}
