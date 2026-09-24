package io.legado.app.ui.rss.source.edit

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 6 页（`activity_rss_source_edit`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（LinearLayout 竖向）+ 5 个节点」：
 *   `compose_top_bar`（已 Compose）/ 两个 `HorizontalScrollView`（4 个 `ThemeCheckBox`；
 *   类型/版面/并发参数行）/ `tab_layout`（36dp）/ `recycler_view`（EditEntity 双列网格）。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，其中**四个 View 内核**
 * （多选框行 / 参数行 / TabLayout / RecyclerView）一律以 `AndroidView` **原样托管**。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再手写 ComposeView / viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_rss_source_edit.xml` 不存在）
 *   ③四个 View 内核仍**以 AndroidView 原样托管**（程序化等价物，不是换成「看起来差不多」的 Compose 组件）
 *   ④**CB-1 ⑤ Insets 监听链路仍在**（锚点由 XML 的 recyclerView 改为合成壳 root，逻辑与 padding 落点等价）
 *   ⑤宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑥编辑态装配不变量（4 个 Tab / 双列网格 + spanSizeLookup / 类型切换联动 adapter）
 *   ⑦`ThemeCheckBox` 程序化构造依赖的构造签名（由 ThemeCheckBoxProgrammaticCtorTest 另一侧锁死）
 */
class RssSourceEditShellMigrationTest {

    private val page = "ui/rss/source/edit/RssSourceEditActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityRssSourceEditBinding"))
        assertFalse("顶栏不得再经 ComposeView.setContent", s.contains("composeTopBar.setContent"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_rss_source_edit.xml")
        assertFalse("activity_rss_source_edit.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue(
            "四个 View 内核必须经 AndroidView 托管",
            s.contains("AndroidView(") && s.contains("factory = { checkRowView }") &&
                s.contains("factory = { paramRowView }") && s.contains("factory = { tabLayoutView }") &&
                s.contains("factory = { recyclerView }")
        )
        assertTrue(
            "多选框行/参数行必须程序化重建为 HorizontalScrollView + LinearLayout（原几何：8dp 内边距 + 垂直居中）",
            s.contains("HorizontalScrollView(this)") && s.contains("LinearLayout(this)") &&
                s.contains("setPadding(8.dpToPx(), 0, 8.dpToPx(), 0)") && s.contains("Gravity.CENTER_VERTICAL")
        )
        assertTrue(
            "TabLayout 必须程序化重建（36dp 高 + elevation 3dp，底/指示器色由 initView 覆写）",
            s.contains("TabLayout(this)") && s.contains(".height(36.dp)") &&
                s.contains("elevation = 3.dpToPx().toFloat()")
        )
        assertTrue(
            "RecyclerView 必须程序化重建且保持 clipToPadding=false（原 XML 明文）",
            s.contains("RecyclerView(this)") && s.contains("clipToPadding = false")
        )
        assertTrue(
            "多选框必须是 ThemeCheckBox（accent tint 语义不丢）",
            s.contains("ThemeCheckBox(this)")
        )
        assertTrue(
            "下拉框必须保持 XML 的视图主题（`android:theme=\"@style/Spinner\"`）",
            s.contains("AppCompatSpinner(ContextThemeWrapper(this, R.style.Spinner))")
        )
        assertTrue(
            "解析并发输入框必须保持 60dp/数字键盘/最长 2 位（原 XML 逐项）",
            s.contains("InputType.TYPE_CLASS_NUMBER") && s.contains("InputFilter.LengthFilter(2)")
        )
    }

    @Test
    fun insetsAnchorChainPreserved() {
        val s = src()
        // CB-1 ⑤：原位 insets 监听链路不得因换装消失（锚点改 root，逻辑与落点等价）
        assertTrue("insets 监听必须仍在", s.contains("setOnApplyWindowInsetsListenerCompat"))
        assertTrue("insets 锚点须为合成壳 root（组合内 AndroidView 不保证收到派发）", s.contains("binding.root.setOnApplyWindowInsetsListenerCompat"))
        assertTrue(
            "RecyclerView 底部内边距的既有口径必须保留（无 IME 时补导航栏高）",
            s.contains("recyclerView.bottomPadding = if (imeHeight == 0) navigationBarHeight else 0")
        )
        assertTrue("软键盘工具条的初始内边距必须仍随 IME 高度更新", s.contains("softKeyboardTool.initialPadding = imeHeight"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun createCheckRow(",
            "private fun createParamRow(",
            "private fun label(",
            "private fun checkBox(",
            "private fun spinner(",
            "private fun createParseConcurrencyEdit(",
            "private fun createTabLayout(",
            "private fun createRecyclerView(",
            "private fun initView(",
            "private fun setEditEntities(",
            "private fun locateField(",
            "private fun clearFieldErrors(",
            "private fun onFullEditClicked(",
            "private fun buildMenuActions(",
            "override fun finish(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun behaviorInvariantsKept() {
        val s = src()
        // 4 个 Tab（基本/起始/列表/WEB_VIEW）逐项不得少
        assertTrue("Tab「源基本」必须保留", s.contains("R.string.source_tab_base"))
        assertTrue("Tab「源起始」必须保留", s.contains("R.string.source_tab_start"))
        assertTrue("Tab「列表规则」必须保留", s.contains("R.string.source_tab_list"))
        assertTrue("Tab「WEB_VIEW」必须保留", s.contains("\"WEB_VIEW\""))
        // 双列网格 + spanSizeLookup（checkBox 占 1 span，其余整行 2 span）
        assertTrue("必须仍为双列网格", s.contains("GridLayoutManager(this, 2)"))
        assertTrue("spanSizeLookup 口径必须保留", s.contains("EditEntity.ViewType.checkBox -> 1"))
        // 主题色消费（Tab 底/指示器）
        assertTrue("Tab 指示器色必须仍取 accentColor", s.contains("tabLayoutView.setSelectedTabIndicatorColor(accentColor)"))
        // 类型切换联动 adapter
        assertTrue("源类型切换必须仍刷新 adapter", s.contains("adapter.currentSourceType = position"))
        // 字段读写链路（保存与回填）
        assertTrue("保存必须仍读 4 个多选框", s.contains("source.enabled = cbIsEnable.isChecked"))
        assertTrue("保存必须仍读解析并发", s.contains("source.parseConcurrency = editParseConcurrency.text.toString()"))
        assertTrue("回填必须仍写解析并发", s.contains("editParseConcurrency.setText("))
    }
}