package io.legado.app.ui.replace

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：替换规则管理页（`activity_replace_rule`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML = `LinearLayout`（`TitleBar@title_bar` 带 `contentLayout=view_search` + `FrameLayout` 内
 * `FastScrollRecyclerView` + `SelectActionBar@select_action_bar`）。实测宿主 `initComposeContent()` 早已把三者
 * **全部作废**（titleBar/selectActionBar 置 GONE、recyclerView 摘出后原位插入手拼 `ComposeView`）⇒ XML 是
 * **死壳**，换装只需把「运行时装配」收敛为合成壳单源，并顺手清掉随之失效的死代码。
 *
 * 本测试锁死五类事实：
 *  ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *  ②XML 已退役（`activity_replace_rule.xml` 不存在）
 *  ③旧 View `SelectActionBar` 链路清零（`SelectActionBar.CallBack` / `initSelectActionView` / `setCallBack`）
 *  ④批量动作回调**必须保留**（`selectAll` / `revertSelection` / `onClickSelectBarMainAction` 仍被 Scaffold 调用）
 *  ⑤宿主业务逻辑未因换装消失
 */
class ReplaceRuleShellMigrationTest {

    private val page = "ui/replace/ReplaceRuleActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityReplaceRuleBinding"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_replace_rule.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_replace_rule.xml").exists()
        )
    }

    @Test
    fun legacySelectActionBarChainIsCleared() {
        val s = src()
        assertFalse("旧 View SelectActionBar 接口不应再实现", s.contains("SelectActionBar.CallBack"))
        assertFalse("旧 SelectActionBar 的装配方法应随壳退役", s.contains("private fun initSelectActionView("))
        assertFalse("不得再操作已退役的 selectActionBar", s.contains("binding.selectActionBar"))
        assertFalse("不得再引用旧 titleBar 节点", s.contains("binding.titleBar"))
    }

    @Test
    fun scaffoldBatchCallbacksArePreserved() {
        val s = src()
        // 这三个函数原为 SelectActionBar.CallBack 的实现；壳退役后仍被 AppManagementScaffold 消费 ⇒ 必须保留
        assertTrue("批量全选回调必须保留", s.contains("private fun selectAll(selectAll: Boolean)"))
        assertTrue("批量反选回调必须保留", s.contains("private fun revertSelection()"))
        assertTrue("批量删除回调必须保留", s.contains("private fun onClickSelectBarMainAction()"))
        assertTrue("Scaffold 必须接线全选/反选/删除", s.contains("onSelectAll = { selectAll(true) }"))
        assertTrue("Scaffold 必须接线反选", s.contains("onInvertSelection = { revertSelection() }"))
        assertTrue("Scaffold 必须接线批量删除", s.contains("onClick = ::onClickSelectBarMainAction"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun observeReplaceRuleData(",
            "private fun observeGroupData(",
            "private fun pageMenuActions(",
            "private fun showFilterMenu(",
            "private fun exportSelected(",
            "private fun showImportDialog(",
            "private fun ruleMenuActions(",
            "private fun getSelectedRules(",
            "private fun updateSearchQuery(",
            "private fun sameReplaceRuleContent(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }
}