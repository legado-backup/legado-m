package io.legado.app.ui.book.read.page

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.2 页眉返回按钮 · 命中与语义（源码文本断言）。
 *
 * 本条的两个真实风险点：①**命中必须早于既有九宫格**（否则与 `tlRect` 冲突、按钮点不到，
 * 交接文档已实测该坑）②**返回语义必须复用系统返回键链路**，不能直 `finish()`（本仓返回键有
 * 6 级拦截：收面板/退搜索/恢复进度/停自动翻页/尊重 `disableReturnKey`）。
 */
class PageViewHeaderBackWiringTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    private fun pageView() = read("src/main/java/io/legado/app/ui/book/read/page/PageView.kt")

    private fun readView() = read("src/main/java/io/legado/app/ui/book/read/page/ReadView.kt")

    @Test
    fun pageViewRendersAndTintsBackIconFromTipColor() {
        val t = pageView()
        assertTrue(
            "显隐必须由开关驱动",
            t.contains("ivHeaderBack.isGone = !ReadTipConfig.showHeaderBackButton")
        )
        assertTrue(
            "取色必须走 tipColor（禁硬编码）",
            t.contains("ivHeaderBack.imageTintList = ColorStateList.valueOf(tipColor)")
        )
    }

    @Test
    fun hiddenButtonKeepsHeaderRowHeight() {
        val t = pageView()
        assertTrue(
            "开关开启时左槽须保留行高（对齐上游口径）",
            t.contains("tvHeaderLeft.isGone = tipHeaderLeft == none && !ReadTipConfig.showHeaderBackButton")
        )
    }

    @Test
    fun hitRectIsNullWhenNotTappable() {
        val t = pageView()
        assertTrue("必须提供命中矩形", t.contains("fun headerBackHitRect(): Rect?"))
        val guard = "if (!isMainView || iv.isGone || binding.llHeader.isGone) return null"
        assertTrue("命中矩形须在「非主视图/图标隐藏/页眉隐藏」时返回 null", t.contains(guard))
        assertTrue("未布局时不得命中", t.contains("if (iv.width <= 0 || iv.height <= 0) return null"))
    }

    @Test
    fun readViewChecksHeaderBackBeforeNineGrid() {
        val t = readView()
        val hit = t.indexOf("val headerBackRect = curPage.headerBackHitRect()")
        val grid = t.indexOf("isTextSelected -> Unit")
        assertTrue("必须命中页眉返回矩形", hit > 0)
        assertTrue("九宫格分支必须存在（回归护栏）", grid > 0)
        assertTrue("命中判定必须早于九宫格分发", hit < grid)
    }

    @Test
    fun backRoutesThroughSystemBackChainNotDirectFinish() {
        val t = readView()
        assertTrue(
            "必须复用系统返回键链路",
            t.contains("(activity as? ComponentActivity)?.onBackPressedDispatcher?.onBackPressed()")
        )
        assertFalse("不得直 finish（会跳过 6 级拦截：丢进度/绕过用户设置）", t.contains("activity?.finish()"))
    }
}