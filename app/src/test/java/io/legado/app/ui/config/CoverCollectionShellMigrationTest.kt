package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：封面图集管理页（`activity_cover_collection_manage`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML = `LinearLayout { MainTopBarView@title_bar ; RecyclerView@recycler_view ; TextView@btn_add }`，
 * 顶栏由 `installGlassTopBar(binding, …)` 在 **`binding.root` 首插 ComposeView** 提供 ⇒ 与换装后的
 * `attachComposeContent` 的 `removeAllViews()` **互斥** ⇒ 顶栏必须**搬进页内 Composition**（顶栏包 §4.1）。
 *
 * **顺带修真实缺陷（已入 updateLog）**：`btn_add`（「创建图集」）经真机 dump 实测为
 * `clickable="false"` 的**可见重复按钮**（页面内已有真实入口），且原手拼 ComposeView 以
 * `match_parent` 高度挂在根 LinearLayout 尾部 ⇒ 内容区被挤占 96px。换装后内容区改 `weight(1f)`，
 * 该残留死节点随壳退役。
 *
 * 本测试锁死六类事实：单源装配 / XML 退役 / 顶栏页内渲染 / 条件动作保留 / 死按钮已清除 / 宿主逻辑未变。
 */
class CoverCollectionShellMigrationTest {

    private val page = "ui/config/CoverCollectionManageActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityCoverCollectionManageBinding"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_cover_collection_manage.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_cover_collection_manage.xml").exists()
        )
    }

    @Test
    fun topBarIsRenderedInPage() {
        val s = src()
        assertFalse(
            "不得再用 installGlassTopBar（它与 attachComposeContent 的 removeAllViews 互斥）",
            s.contains("installGlassTopBar")
        )
        assertFalse("原 initTopBar() 必须被合并掉", s.contains("private fun initTopBar("))
        assertTrue("顶栏必须在页内直接渲染", s.contains("GlassTopAppBar("))
        assertTrue("动作行必须走 TopBarActionRow", s.contains("TopBarActionRow("))
        assertTrue("条件云容器动作必须保留（iconRes + alwaysShow）", s.contains("iconRes = R.drawable.ic_outline_cloud_24"))
        assertTrue("云容器动作必须保持顶栏一级图标语义", s.contains("alwaysShow = true"))
        assertTrue("返回必须仍走 finish()", s.contains("onNavClick = { finish() }"))
    }

    @Test
    fun deadDuplicateButtonIsGone() {
        val s = src()
        assertFalse("不得再引用已退役的 btn_add 节点", s.contains("binding.btnAdd"))
        assertFalse("不得再引用已退役的 titleBar/recyclerView 节点", s.contains("binding.titleBar") || s.contains("binding.recyclerView"))
        assertFalse("不得再出现「摘节点 + 手拼」的旧装配", s.contains("container.removeView(") || s.contains("container.addView("))
        // 内容区改由 weight(1f) 承载（原 match_parent 手拼 ComposeView 会挤占内容区）
        assertTrue("内容区必须以 weight(1f) 承载", s.contains(".weight(1f)"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun onResume(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun initComposeContent(",
            "private fun updateContainerMenu(",
            "private fun showContainerSelector(",
            "private fun loadCollections(",
            "private fun showAddActions(",
            "private fun showCreateDialog(",
            "private fun showRenameDialog(",
            "private fun importZip(",
            "private fun openDetail(",
            "private fun exportCollection(",
            "private fun coverActions(",
            "private val importZip =",
            "private val exportZip =",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 屏幕参数逐项保留
        listOf(
            "isNight = isNightState.value",
            "entries = entriesState.value",
            "onItemClick = ::openDetail",
            "itemActions = ::coverActions",
            "onAddClick = ::showAddActions",
        ).forEach { marker ->
            assertTrue("屏幕接线不得缺失：`$marker`", s.contains(marker))
        }
    }
}