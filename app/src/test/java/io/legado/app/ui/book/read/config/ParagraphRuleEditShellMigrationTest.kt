package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-a #11（2026-09-26）：`activity_paragraph_rule_edit.xml` 退役（**2 个宿主共用布局**）契约测试。
 *
 * 换装口径：
 *  · 两个宿主（段落规则编辑 / 自定义按键编辑）一律 `composeShell(this)` + `attachComposeContent` 单源；
 *  · 字段区（原 `nested_scroll > ll_content`：5 组 `TextInputLayout` + 1 个勾选 + 4 个 `CodeView`
 *    + 3 个 Compose 槽）整体程序化重建，由 [ParagraphRuleEditShellViews] **单源装配**，
 *    再以 `AndroidView` 原样托管（滚动/焦点语义由 `NoChildScrollNestedScrollView` 承担）；
 *  · 顶栏由 `installGlassTopBar` 运行时注入改为**页内直接渲染**（标题/返回/动作逐项不变）。
 *
 * 本测试锁死六件事（防回归 / 防「静默退化」）：
 *   ①两宿主不得回退到 ViewBinding inflate / 旧顶栏注入；
 *   ②装配单源文件存在且 ComposeView 构造点收敛到唯一工厂（宿主不得自建/自设策略）；
 *   ③6 个 `et_*` 节点必须赋原 `R.id`（`hintFor(view)` 依赖）；
 *   ④勾选/超时/多行等**易丢语义逐项复刻**（singleLine / inputType / maxLines / 默认勾选文案）；
 *   ⑤自定义按键页的**运行时分步重排**语义保留（10 个节点清单不得漂移）；
 *   ⑥`nested_scroll` 的 `weight=1` 语义由宿主 `Modifier.weight(1f)` 表达（不得改成无权重）。
 */
class ParagraphRuleEditShellMigrationTest {

    private val shellRel = "ui/book/read/config/ParagraphRuleEditShellViews.kt"
    private val paragraphRel = "ui/book/read/config/ParagraphRuleEditActivity.kt"
    private val readMenuRel = "ui/book/read/config/ReadMenuCustomButtonEditActivity.kt"

    private fun shell(): String = SourceFileProbe.sourceText(shellRel)

    @Test
    fun bothHostsUseComposeShellSingleSource() {
        listOf(paragraphRel, readMenuRel).forEach { rel ->
            val s = SourceFileProbe.sourceText(rel)
            assertTrue("$rel 必须走 composeShell 合成壳", s.contains("composeShell(this)"))
            assertTrue("$rel 必须走 attachComposeContent 单源", s.contains("attachComposeContent {"))
            assertFalse("$rel 不得残留 ViewBinding inflate", s.contains("by viewBinding("))
            assertFalse("$rel 不得残留旧布局绑定", s.contains("ActivityParagraphRuleEditBinding"))
            assertFalse("$rel 不得残留旧顶栏注入", s.contains("installGlassTopBar("))
        }
    }

    @Test
    fun topBarRenderedInPageComposition() {
        listOf(paragraphRel, readMenuRel).forEach { rel ->
            val s = SourceFileProbe.sourceText(rel)
            assertTrue("$rel 顶栏必须页内渲染（GlassTopAppBar）", s.contains("GlassTopAppBar("))
            assertTrue("$rel 顶栏动作必须走 TopBarActionRow", s.contains("TopBarActionRow(topBarActions())"))
            assertTrue(
                "$rel 原 nested_scroll 的 `0dp + weight=1` 语义必须由 Compose 权重表达",
                s.contains("Modifier.fillMaxWidth().weight(1f)")
            )
            assertTrue(
                "$rel 字段区必须由 AndroidView 原样托管装配单源",
                s.contains("factory = { shell.nestedScroll }")
            )
        }
    }

    @Test
    fun composeViewConstructionIsSingleSourced() {
        // ⚠️ `ComposeShellSingleSourceTest` 以「文件内是否出现 ComposeView( / ViewCompositionStrategy」
        // 判定整文件；宿主一旦自行创建 ComposeView 或自设策略即判违规 ⇒ 必须有此断言兜住。
        listOf(paragraphRel, readMenuRel).forEach { rel ->
            val s = SourceFileProbe.sourceText(rel)
            assertFalse("$rel 不得自行创建 ComposeView（应交由 ParagraphRuleEditShellViews.composeSlot）", s.contains("ComposeView("))
            assertFalse("$rel 不得自行设置合成策略", s.contains("ViewCompositionStrategy"))
        }
        val single = shell()
        assertEquals(
            "装配单源内 ComposeView 构造点必须唯一（唯一工厂 composeSlot）",
            1,
            Regex("ComposeView\\(").findAll(single).count()
        )
        assertTrue("唯一工厂必须设置合成策略（与迁移前 XML 内 ComposeView 口径一致）", single.contains("setViewCompositionStrategy("))
    }

    @Test
    fun editTextIdsKeptForHintLookup() {
        val s = shell()
        listOf("et_name", "et_login_url", "et_login_ui", "et_timeout", "et_script", "et_js_lib").forEach { id ->
            assertTrue("字段节点必须赋 R.id.$id（宿主 hintFor(view) 依赖）", s.contains("id = R.id.$id"))
        }
        // 宿主侧提示映射不得漂移
        assertTrue(SourceFileProbe.sourceText(paragraphRel).contains("R.id.et_script -> getString(R.string.paragraph_rule_script)"))
        assertTrue(SourceFileProbe.sourceText(readMenuRel).contains("R.id.et_script -> getString(R.string.read_menu_button_script)"))
    }

    @Test
    fun fieldSemanticsCopiedFromXml() {
        val s = shell()
        assertTrue("名称字段必须仍 singleLine", s.contains("setSingleLine(true)"))
        assertTrue("超时字段必须仍为数字输入", s.contains("inputType = InputType.TYPE_CLASS_NUMBER"))
        listOf(6, 8, 14, 12).forEach { lines ->
            assertTrue("CodeView 必须复刻 XML 的 maxLines=$lines", s.contains("maxLines = $lines"))
        }
        assertTrue("Cookie 勾选必须保留原文案", s.contains("setText(R.string.auto_save_cookie)"))
        assertTrue("字段容器必须保留 XML 的 10dp 内边距", s.contains("val pad = 10.dpToPx()"))
        assertTrue("字段容器必须仍是竖向 LinearLayout", s.contains("orientation = LinearLayout.VERTICAL"))
    }

    @Test
    fun readMenuRuntimeReorderIntact() {
        val s = SourceFileProbe.sourceText(readMenuRel)
        assertTrue("运行时分步重排必须保留（shell.run 作用域）", s.contains("private fun applyFormOrder() = shell.run {"))
        listOf(
            "tilName", "cvScriptTemplates", "tilScript",
            "cvLoginAdvanced",
            "tilLoginUrl", "tilLoginUi", "cbIsEnableCookie", "tilTimeout", "tilJsLib",
            "cvScriptTest",
        ).forEach { member ->
            assertTrue("重排清单必须仍含 $member", s.contains(member))
        }
        assertTrue("两个 Compose 槽在本页必须置为可见", s.contains("cvLoginAdvanced.visibility = View.VISIBLE"))
        assertTrue("两个 Compose 槽在本页必须置为可见", s.contains("cvScriptTest.visibility = View.VISIBLE"))
        assertTrue("段落规则页的两个槽必须保持 gone（零占位）", shell().contains("visibility = View.GONE"))
    }
}