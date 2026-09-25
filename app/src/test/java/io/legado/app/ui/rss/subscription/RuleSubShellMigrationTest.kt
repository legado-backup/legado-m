package io.legado.app.ui.rss.subscription

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b 首个页面（`activity_rule_sub`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页 XML 早已是无语义死壳——宿主 `initComposeContent()` 在运行时把 `recycler_view` /
 * `tv_empty_msg` 从父容器移除，再**手拼一个 ComposeView** 插回原索引位。CE-b 把这条「运行时装配」
 * 收敛到 `composeShell` + `attachComposeContent` 单源承载，页面 XML 随之退役（死资源清理）。
 *
 * 本测试锁死五类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再手写 ComposeView / ViewCompositionStrategy
 *     / 运行时从父容器摘节点**
 *   ②XML 已退役（`activity_rule_sub.xml` 不存在）
 *   ③`AppManagementScaffold` 仍**页内直接渲染**（本页历史上不经 `installGlassTopBar`，如实锁定）
 *   ④`AppManagementScaffold` 的关键语义参数与空态双分支**逐项保留**
 *   ⑤宿主业务逻辑**未消失**（逐项断言方法名）
 */
class RuleSubShellMigrationTest {

    private val page = "ui/rss/subscription/RuleSubActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("禁止运行时从父容器摘节点（原死壳装配手法）", s.contains("indexOfChild(") || s.contains("removeView("))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityRuleSubBinding"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_rule_sub.xml")
        assertFalse("activity_rule_sub.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun scaffoldRendersInPageNotViaAnchorInstaller() {
        val s = src()
        assertTrue("顶栏必须由页内 AppManagementScaffold 直接渲染", s.contains("AppManagementScaffold("))
        // 本页历史上从不经 installGlassTopBar（无 title_bar 锚点）⇒ 如实锁定该事实，防未来被误改
        assertFalse("本页不应引入 installGlassTopBar（无顶栏锚点）", s.contains("installGlassTopBar("))
    }

    @Test
    fun scaffoldSemanticsPreserved() {
        val s = src()
        listOf(
            "title = getString(R.string.rule_subscription)",
            "selectedCount = 0",
            "totalCount = filteredItems.size",
            "searchQuery = searchQueryState.value",
            "searchHint = getString(R.string.search)",
            "onSearchChange = { searchQueryState.value = it }",
            "iconRes = R.drawable.ic_add",
            "onBack = { finish() }",
        ).forEach { marker ->
            assertTrue("换装不得改动壳语义参数：缺少 `$marker`", s.contains(marker))
        }
        // 空态双分支：无搜索词用页面空态文案，有搜索词用「无结果」文案（原逐字语义）
        assertTrue("空态必须保留无搜索词分支", s.contains("getString(R.string.rule_sub_empty_msg)"))
        assertTrue("空态必须保留搜索无结果分支", s.contains("getString(R.string.search_result)"))
        // 拖拽仅在非搜索态可用（原逐字语义）
        assertTrue("拖拽开关口径必须保留", s.contains("dragEnabled = searchQueryState.value.isBlank()"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun initComposeContent(",
            "private fun initData(",
            "private fun filterRuleSubs(",
            "private fun addSubscription(",
            "private fun openSubscription(",
            "private fun editSubscription(",
            "override fun saveRuleSub(",
            "private fun ruleSubMenuActions(",
            "private fun delSubscription(",
            "private fun moveSubscription(",
            "private fun moveSubscriptionBy(",
            "private fun persistSubscriptionOrder(",
            "private fun updateSourceSub(",
            "private fun sameRuleSubContent(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        assertTrue("列表去重/重排仍走共享单源 replaceByIndex", s.contains("replaceByIndex("))
    }
}