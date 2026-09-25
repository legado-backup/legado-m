package io.legado.app.ui.font

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 首项（2026-09-26）：`item_font` → `FontAdapter` 列表迁移**收尾**契约测试。
 *
 * 事实链（实测）：`FontSelectDialog` 早已由 `ComposeDialogFragment + AppDialogFrame + LazyColumn +
 * FontItemRow` 承载字体列表（迁移说明见其 KDoc），而 View 侧 `FontAdapter`（`RecyclerAdapter<FileDoc,
 * ItemFontBinding>`）**已无任何实例化点** ⇒ `FontAdapter.kt` 与 `item_font.xml` 双双成为**残留死件**。
 *
 * 本项收尾 = ①把 `FontAdapter.CallBack.onFontSelect` 的单一实现降级为 `FontSelectDialog` 的页内私有函数
 * ②删除 `FontAdapter.kt` 与 `item_font.xml` ③同步机检计数（`CfItemHostCoverageTest` 35 / 25）。
 *
 * 本测试锁死四件事，防「死件回流」与「列表实现回退」：
 *   ①两个死件不得复活；②弹框不得再引用 View 侧适配器；③Compose 列表实现（LazyColumn + FontItemRow）仍在；
 *   ④`onFontSelect` 必须是页内私有（不得重新变成对外 override 的接口实现）。
 */
class FontSelectComposeOnlyTest {

    private val dialogRel = "ui/font/FontSelectDialog.kt"
    private val root: File = SourceFileProbe.mainJavaRoot()

    @Test
    fun deadAdapterAndItemLayoutAreGone() {
        assertFalse(
            "FontAdapter.kt 已无实例化点，应保持删除状态（死件不得回流）",
            File(root, "io/legado/app/ui/font/FontAdapter.kt").isFile
        )
        val itemFont = SourceFileProbe.layoutDir().resolve("item_font.xml")
        assertFalse("item_font.xml 已随本项退役，应保持删除状态", itemFont.isFile)
    }

    @Test
    fun dialogNoLongerReferencesViewAdapter() {
        // ⚠️ 必须用 `sourceText`（剥注释）：KDoc 里为记录迁移历史会提到 `FontAdapter.CallBack`，
        // 若用 rawText 会把「历史说明」误判为「仍在引用」（本项目已多次实证此类假阳性）。
        val code = SourceFileProbe.sourceText(dialogRel)
        assertFalse("弹框代码不得再引用 FontAdapter", code.contains("FontAdapter"))
        assertFalse("弹框代码不得再实现其 CallBack 接口", code.contains("FontAdapter.CallBack"))
        assertFalse(
            "onFontSelect 不得再是对外 override（已降级为页内私有函数）",
            code.contains("override fun onFontSelect(")
        )
        assertTrue("onFontSelect 必须为页内私有函数", code.contains("private fun onFontSelect(docItem: FileDoc)"))
        assertTrue(
            "迁移历史必须留注释（后者易误以为从未有过 View 适配器）",
            SourceFileProbe.rawText(dialogRel).contains("FontAdapter.CallBack.onFontSelect")
        )
    }

    @Test
    fun composeListImplementationStillInPlace() {
        val code = SourceFileProbe.sourceText(dialogRel)
        assertTrue("字体列表必须仍由 LazyColumn 承载", code.contains("LazyColumn("))
        assertTrue("字体行必须仍有 Compose 实现", code.contains("FontItemRow("))
        assertTrue(
            "字体自身渲染预览（Typeface 构造）语义不得丢",
            code.contains("Typeface.createFromFile") || code.contains("Typeface.Builder")
        )
    }

    @Test
    fun hostCallbackContractKept() {
        // 弹框自身的 CallBack（父级实现，回传选中字体）必须保留 —— 它才是对外的契约
        val code = SourceFileProbe.sourceText(dialogRel)
        assertTrue("弹框自身 CallBack 接口必须保留", code.contains("interface CallBack {"))
        assertTrue("选中回传必须保留", code.contains("fun selectFont(path: String)"))
        assertTrue("当前字体路径读取必须保留", code.contains("val curFontPath: String"))
    }
}