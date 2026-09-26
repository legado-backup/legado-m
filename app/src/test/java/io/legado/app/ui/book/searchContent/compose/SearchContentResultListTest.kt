package io.legado.app.ui.book.searchContent.compose

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：`item_search_list` 退役（全文搜索结果列表 View → Compose）。
 *
 * 换装前：`SearchContentActivity` 的 `FastScrollRecyclerView(UpLinearLayoutManager + VerticalDivider)`
 * + `SearchContentAdapter`，条目 inflate `item_search_list.xml`（单 `TextView`，文本为 `Spanned`）。
 * 换装后：Compose `LazyColumn`（`SearchContentResultList`，行内 `AndroidView{TextView}` 承载同一 `Spanned`）
 * + `ComposeLazyListFastScroller`（保留快速滚动行为）。
 */
class SearchContentResultListTest {

    private fun layout(name: String): File = File(SourceFileProbe.layoutDir(), name)

    private fun mainJava(rel: String): File =
        File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel")

    private fun listSource(): String =
        SourceFileProbe.sourceText("ui/book/searchContent/compose/SearchContentResultList.kt")

    /**
     * 宿主源码的**代码面**（去块注释 + 行注释）。
     *
     * 为什么不用 `SourceFileProbe.sourceText`：它只剥「以 `//` 或 `*` 开头」的行，
     * **单行 KDoc（以 `/` 加两个星号起头的单行注释）与行首非 `*` 的块注释不被剥除** ⇒ 注释里的历史类名
     * 会造成假阳性（本项目已多次踩坑，见 `交接文档-20260925.md` §8）。此处补一层块注释剔除，
     * 保证「不得残留」类断言只反映真实代码。
     */
    private fun hostSource(): String {
        val raw = SourceFileProbe.rawText("ui/book/searchContent/SearchContentActivity.kt")
        return raw.replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
            .lines()
            .filterNot { it.trimStart().startsWith("//") }
            .joinToString("\n")
    }

    @Test
    fun deadArtifactsAreGone() {
        assertFalse("死布局应已退役：item_search_list.xml", layout("item_search_list.xml").isFile)
        assertFalse(
            "死 Adapter 应已退役：SearchContentAdapter.kt",
            mainJava("ui/book/searchContent/SearchContentAdapter.kt").isFile
        )
    }

    @Test
    fun hostNoLongerHasViewList() {
        val host = hostSource()
        assertFalse(host.contains("FastScrollRecyclerView"))
        assertFalse(host.contains("UpLinearLayoutManager"))
        assertFalse(host.contains("VerticalDivider"))
        assertFalse(host.contains("SearchContentAdapter"))
        assertTrue("宿主须改挂 Compose 列表单源", host.contains("SearchContentResultList("))
        assertTrue(
            "滚动行为等价须保留快速滚动件",
            host.contains("ComposeLazyListFastScroller(")
        )
        assertTrue("结果集须以 state 驱动重组", host.contains("resultItems ="))
    }

    @Test
    fun hostColorHexIsLazyInitialized() {
        // 真机 L2 实证（2026-09-26）：属性初始化器在 `attachBaseContext` 之前执行，
        // 构造期访问主题资源 ⇒ `Unable to instantiate activity`（Activity 无法实例化）
        val host = hostSource()
        assertTrue(
            "取色十六进制串必须 by lazy（构造期访问主题资源会崩）",
            host.contains("private val textColorHex by lazy") &&
                host.contains("private val accentColorHex by lazy")
        )
    }

    @Test
    fun listPreservesSpannedRenderingAndDivider() {
        val src = listSource()
        // 富文本逐 span 等价：行内仍走 getHtmlCompat 产出的 Spanned（不重写 HTML 解析）
        assertTrue(src.contains("item.getHtmlCompat(textColorHex, accentColorHex)"))
        assertTrue("当前阅读章加粗口径须保留", src.contains("tv.paint.isFakeBoldText ="))
        // 分割线取色与 DividerItemDecoration 同源（运行时解析主题 listDivider）
        assertTrue(src.contains("android.R.attr.listDivider"))
        // 点击仅在 query 非空时回调（原 registerListener 口径）
        assertTrue(src.contains("clickable(enabled = item.query.isNotBlank())"))
    }
}