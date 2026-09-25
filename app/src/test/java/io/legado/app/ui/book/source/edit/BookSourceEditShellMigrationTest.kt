package io.legado.app.ui.book.source.edit

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #12（2026-09-26）：`activity_book_source_edit.xml` 退役（顶栏锚点页）契约测试。
 *
 * 换装口径（与同类页 `RssSourceEditActivity` 逐项同构）：
 *  · 宿主 `BookSourceEditActivity` 走 `composeShell(this)` + `attachComposeContent` 单源；
 *  · 原 XML 六段结构（引导条槽 / 多选框行 / 参数行「书源类型标签 + Spinner + 3 个勾选」/
 *    事件与自定义按键行 / `TabLayout` 36dp + 3dp 阴影 / `RecyclerView`）由
 *    [BookSourceEditShellViews] **单源装配**，各段以 `AndroidView` 原样托管；
 *  · 顶栏由 `installGlassTopBar` 运行时注入改为**页内直接渲染**（标题/返回/三组动作逐项不变）；
 *  · `RecyclerView` 的 `0dp` 高度语义由 Compose `weight(1f)` 表达；`TabLayout` 自身保持 36dp。
 *
 * 本测试锁死五件事：
 *   ①宿主不得回退 ViewBinding inflate / 旧顶栏注入；②ComposeView 构造点收敛到装配单源；
 *   ③六段结构齐备且**易丢语义逐项复刻**（Spinner theme+entries / 勾选默认值 / review 隐藏 /
 *     36dp+3dp / clipToPadding）；④insets 锚点仍在 RecyclerView 上（与迁移前同锚点）；
 *   ⑤三组菜单与 6 个 Tab 的分类文案未丢。
 */
class BookSourceEditShellMigrationTest {

    private val host = "ui/book/source/edit/BookSourceEditActivity.kt"
    private val shell = "ui/book/source/edit/BookSourceEditShellViews.kt"

    private fun hostCode(): String = SourceFileProbe.sourceText(host)
    private fun shellCode(): String = SourceFileProbe.sourceText(shell)

    @Test
    fun hostUsesComposeShellSingleSource() {
        val s = hostCode()
        assertTrue("必须走 composeShell 合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源", s.contains("attachComposeContent {"))
        assertFalse("不得残留 ViewBinding inflate", s.contains("by viewBinding("))
        assertFalse("不得残留旧布局绑定", s.contains("ActivityBookSourceEditBinding"))
        assertFalse("不得残留旧顶栏注入", s.contains("installGlassTopBar("))
        assertTrue("顶栏必须页内渲染", s.contains("GlassTopAppBar("))
        assertTrue("顶栏动作必须走 TopBarActionRow", s.contains("TopBarActionRow(topBarActions())"))
    }

    @Test
    fun composeViewConstructionIsSingleSourced() {
        assertFalse("宿主不得自行创建 ComposeView", hostCode().contains("ComposeView("))
        assertFalse("宿主不得自行设置合成策略", hostCode().contains("ViewCompositionStrategy"))
        val single = shellCode()
        assertEquals(
            "装配单源内 ComposeView 构造点必须唯一（引导条槽）",
            1,
            Regex("ComposeView\\(").findAll(single).count()
        )
        assertTrue("引导条槽必须设合成策略（与迁移前 XML 口径一致）", single.contains("setViewCompositionStrategy("))
    }

    @Test
    fun sixSectionsRebuiltWithXmlSemantics() {
        val s = shellCode()
        // ① 引导条槽
        assertTrue("必须有规则帮助引导条槽", s.contains("val cvRuleHelpGuide"))
        // ② Spinner：theme + entries 口径
        assertTrue("Spinner 必须走 ContextThemeWrapper(R.style.Spinner)", s.contains("ContextThemeWrapper(context, R.style.Spinner)"))
        assertTrue("Spinner 必须用 book_type 数组", s.contains("R.array.book_type"))
        // ③ 勾选默认值（XML 逐项复刻）
        assertTrue("is_enable 默认勾选", s.contains("checkBox(R.string.is_enable, checked = true)"))
        assertTrue("discovery 默认勾选", s.contains("checkBox(R.string.discovery, checked = true)"))
        assertTrue("auto_save_cookie 默认勾选", s.contains("checkBox(R.string.auto_save_cookie, checked = true)"))
        assertTrue("review 默认不勾", s.contains("checkBox(R.string.review, checked = false)"))
        assertTrue("review 必须保持 gone（逐字保留 XML 语义）", s.contains("visibility = android.view.View.GONE"))
        assertTrue("is_event_listener 默认不勾", s.contains("checkBox(R.string.is_event_listener, checked = false)"))
        assertTrue("custom_button 默认不勾", s.contains("checkBox(R.string.custom_button, checked = false)"))
        // ④ 两行容器：scrollbars=none + 8dp 内边距 + 垂直居中
        assertTrue("行容器必须关闭横向滚动条", s.contains("isHorizontalScrollBarEnabled = false"))
        assertTrue("行容器必须保留 8dp 内边距", s.contains("setPadding(8.dpToPx(), 0, 8.dpToPx(), 0)"))
        assertTrue("行容器必须垂直居中", s.contains("gravity = Gravity.CENTER_VERTICAL"))
        // ⑤ TabLayout：36dp + 3dp 阴影
        assertTrue("TabLayout 必须 36dp 高", s.contains("36.dpToPx()"))
        assertTrue("TabLayout 必须 3dp 阴影", s.contains("elevation = 3.dpToPx().toFloat()"))
        // ⑥ RecyclerView：clipToPadding=false
        assertTrue("RecyclerView 必须 clipToPadding=false", s.contains("clipToPadding = false"))
    }

    @Test
    fun insetsAnchorUnchanged() {
        val s = hostCode()
        assertTrue(
            "insets 锚点必须仍在 RecyclerView 上（与迁移前同锚点 ⇒ 零语义变化）",
            s.contains("shell.recyclerView.setOnApplyWindowInsetsListenerCompat")
        )
        assertTrue("键盘工具 initialPadding 报送不得丢", s.contains("softKeyboardTool.initialPadding = imeHeight"))
        assertTrue(
            "RecyclerView 的 `0dp` 高度语义必须由 Compose weight 表达",
            s.contains("Modifier.fillMaxWidth().weight(1f)")
        )
    }

    @Test
    fun menuGroupsAndTabsIntact() {
        val s = hostCode()
        listOf(
            "book_source_menu_group_ops",
            "book_source_menu_group_share",
            "book_source_menu_group_diag",
        ).forEach { group ->
            assertTrue("顶栏溢出菜单必须保留分组 $group", s.contains(group))
        }
        listOf(
            "source_tab_base", "source_tab_search", "source_tab_find",
            "source_tab_info", "source_tab_toc", "source_tab_content",
        ).forEach { tab ->
            assertTrue("6 个 Tab 文案不得丢：$tab", s.contains(tab))
        }
        assertTrue("Tab 选中回调必须保留", s.contains("setEditEntities(tab?.position)"))
    }
}