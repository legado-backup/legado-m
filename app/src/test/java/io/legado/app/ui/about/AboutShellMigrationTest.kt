package io.legado.app.ui.about

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：关于页（`activity_about`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML = `LinearLayout { ll_about(2 个 TextView) ; fl_fragment }`，顶栏由 `installGlassTopBar` 在
 * **`binding.root` 首插 ComposeView**（XML 里 `MainTopBarView` 节点早已移除，只留注释）。
 * 换装后 `attachComposeContent` 会 `removeAllViews()` ⇒ **顶栏必须搬进页内 Composition**（顶栏包 §4.1），
 * 否则顶栏会被清掉。
 *
 * 本测试锁死五类事实：
 *  ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *  ②XML 已退役（`activity_about.xml` 不存在）
 *  ③顶栏已搬入页内（`GlassTopAppBar` + `TopBarActionRow`；**不得再调 `installGlassTopBar`**）
 *  ④Fragment 容器由组合托管（显式 `R.id.fl_fragment` + `post{}` 延迟提交；id 已迁 `values/ids.xml`）
 *  ⑤宿主逻辑与观感口径未变（accent 上色 / 两个一级动作 / 高度语义保持 `fillMaxHeight` 而非 `weight`）
 */
class AboutShellMigrationTest {

    private val page = "ui/about/AboutActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置合成策略", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityAboutBinding"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_about.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_about.xml").exists()
        )
    }

    @Test
    fun topBarIsRenderedInPage() {
        val s = src()
        assertFalse(
            "不得再用 installGlassTopBar（它与 attachComposeContent 的 removeAllViews 互斥）",
            s.contains("installGlassTopBar")
        )
        assertTrue("顶栏必须在页内直接渲染", s.contains("GlassTopAppBar("))
        assertTrue("两个一级动作必须走 TopBarActionRow", s.contains("TopBarActionRow("))
        // 动作逐项保留（评分 + 分享，均 alwaysShow）
        assertTrue("评分入口必须保留", s.contains("iconRes = R.drawable.ic_star_border"))
        assertTrue("分享入口必须保留", s.contains("iconRes = R.drawable.ic_share"))
        assertTrue("两个动作必须保持顶栏一级图标语义", s.contains("alwaysShow = true"))
        assertTrue("返回必须仍走 finish()", s.contains("onNavClick = { finish() }"))
    }

    @Test
    fun fragmentContainerIsHostedByComposition() {
        val s = src()
        assertTrue("Fragment 容器必须是 Activity 字段（by lazy）", s.contains("private val flFragment: FrameLayout by lazy"))
        assertTrue("容器必须显式赋 id（事务按 id 定位）", s.contains("id = R.id.fl_fragment"))
        assertTrue("事务必须延到容器上树后提交", s.contains("flFragment.post {"))
        assertTrue("容器必须以 AndroidView 原样托管", s.contains("factory = { flFragment }"))
        assertFalse("不得再引用已退役布局里的绑定节点", s.contains("binding.flFragment"))
        // id 必须已迁入 values/ids.xml（否则 R.id.fl_fragment 随 XML 退役消失）
        val ids = SourceFileProbe.sourceTextByPath("src/main/res/values/ids.xml")
        assertTrue("fl_fragment 必须登记到 values/ids.xml", ids.contains("<item name=\"fl_fragment\" type=\"id\" />"))
    }

    @Test
    fun hostLogicAndVisualParityPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun applySummaryAccent(",
            "ForegroundColorSpan(accentColor)",
            "aboutFragment = AboutFragment()",
            "private val tvAppSummary: TextView by lazy",
            "private val aboutHeader: LinearLayout by lazy",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 观感：字号/粗体/居中/内外边距逐项复刻
        assertTrue("应用名必须保持 20sp", s.contains("textSize = 20f"))
        assertTrue("应用名必须保持粗体", s.contains("Typeface.DEFAULT_BOLD"))
        assertTrue("应用名必须居中", s.contains("gravity = Gravity.CENTER_HORIZONTAL"))
        assertTrue("原 padding=10dp 必须复刻", s.contains("setPadding(10.dpToPx()"))
        assertTrue("原 margin=6dp 必须复刻", s.contains(".padding(6.dp)"))
        // 高度语义：原 fl_fragment 是 match_parent ⇒ 必须保持 fillMaxHeight，不得改 weight（那是用户可见变更）
        assertTrue("Fragment 容器高度必须保持原 match_parent 语义", s.contains(".fillMaxHeight()"))
        assertFalse("不得擅自改成 weight（属用户可见变更，须另行走 updateLog）", s.contains("Modifier.weight("))
    }
}