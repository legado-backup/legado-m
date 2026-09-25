package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.4 动作尺寸基准统一（design AD-TB-07）契约测试（JVM 可跑，2026-09-25）。
 *
 * 原状：`TopBarConfig` 自持 `36f / 34f / 8f` 三个私有常量（与 `dimens` 里
 * `top_bar_regular_action_size` / `bookshelf_action_button_size` / `bookshelf_action_button_padding`
 * **重复维护**），而 View 侧 `MainTopBarView` 读的是资源 ⇒ 改一处必漏一处（双源）。
 *
 * 本测试锁死四件事：①常量已删除 ②基准**只**从 `dimens` 取（3 个资源 id 全部命中）
 * ③px↔dp 与 fontScale 相乘顺序保持等价（default 34 / regular 36 / 内边距 8 取值不变）
 * ④与 View 侧同源（同 3 个资源 id）。
 */
class TopBarActionSizeDimensSingleSourceTest {

    private val configRel = "help/config/TopBarConfig.kt"
    private val viewRel = "ui/widget/MainTopBarView.kt"

    private fun bodyOf(code: String, funSignature: String): String {
        val start = code.indexOf(funSignature)
        assertTrue("未定位到 $funSignature", start >= 0)
        val end = code.indexOf("\n    }", start)
        assertTrue("未定位到 $funSignature 的函数体结束", end > start)
        return code.substring(start, end)
    }

    @Test
    fun privateDpConstantsRemoved() {
        val code = SourceFileProbe.sourceText(configRel)
        listOf(
            "ACTION_CONTAINER_REGULAR_DP",
            "ACTION_CONTAINER_DEFAULT_DP",
            "ACTION_ICON_PADDING_DP",
        ).forEach { name ->
            assertFalse("尺寸双源铁律：不得保留私有 dp 常量 $name（基准唯一来源 = dimens）", code.contains(name))
        }
    }

    @Test
    fun baseValuesComeFromDimens() {
        val code = SourceFileProbe.sourceText(configRel)
        listOf(
            "R.dimen.top_bar_regular_action_size",
            "R.dimen.bookshelf_action_button_size",
            "R.dimen.bookshelf_action_button_padding",
        ).forEach { id ->
            assertTrue("基准必须从 $id 取（dimens 单源）", code.contains(id))
        }
        assertTrue(
            "取 px 必须用 getDimension（float，无 getDimensionPixelSize 的取整漂移）",
            code.contains("resources.getDimension(")
        )
        assertFalse(
            "不得回退到取整口径（会让非整数 density 下 34/36dp 出现 ±0.2dp 漂移）",
            code.contains("getDimensionPixelSize(R.dimen.top_bar_regular_action_size")
        )
    }

    @Test
    fun pxToDpAndFontScaleOrderPreserved() {
        val code = SourceFileProbe.sourceText(configRel)
        val container = bodyOf(code, "fun actionContainerSize(")
        assertTrue(
            "容器 = 基准(dp) × fontScale（顺序不得调换）",
            container.contains("actionContainerBaseDp(context) * iconScale(context)")
        )
        val icon = bodyOf(code, "fun actionIconSize(")
        assertTrue(
            "图标 = 容器 − 2×内边距(dp)×fontScale（与 MainTopBarView CENTER_INSIDE 口径一致）",
            icon.contains("actionContainerSize(context) - 2 * actionIconPaddingDp(context) * iconScale(context)")
        )
        val pxToDp = bodyOf(code, "private fun actionContainerBaseDp(")
        assertTrue(
            "px → dp 折回必须除以 density（保持「基准 dp × fontScale」等价）",
            pxToDp.contains("/ context.resources.displayMetrics.density")
        )
    }

    @Test
    fun dimenValuesUnchanged() {
        val dimens = SourceFileProbe.resValuesText("dimens.xml")
        assertTrue(
            "bookshelf_action_button_size 必须仍为 34dp（default 顶栏容器基准）",
            dimens.contains("<dimen name=\"bookshelf_action_button_size\">34dp</dimen>")
        )
        assertTrue(
            "top_bar_regular_action_size 必须仍为 36dp（regular 顶栏包容器基准）",
            dimens.contains("<dimen name=\"top_bar_regular_action_size\">36dp</dimen>")
        )
        assertTrue(
            "bookshelf_action_button_padding 必须仍为 8dp（图标内边距基准）",
            dimens.contains("<dimen name=\"bookshelf_action_button_padding\">8dp</dimen>")
        )
    }

    @Test
    fun sameSourceAsViewSide() {
        val view = SourceFileProbe.sourceText(viewRel)
        listOf(
            "R.dimen.bookshelf_action_button_size",
            "R.dimen.top_bar_regular_action_size",
            "R.dimen.bookshelf_action_button_padding",
        ).forEach { id ->
            assertTrue("View 侧必须仍用同一资源 id $id（双栈同源）", view.contains(id))
        }
    }
}