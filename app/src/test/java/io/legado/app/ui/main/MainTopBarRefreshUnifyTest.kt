package io.legado.app.ui.main

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §2.1：宿主侧**去掉按类型分叉**的刷新入口（JVM 可跑，2026-09-25）。
 *
 * 原实现：`if (view is MainTopBarView) view.refreshStyle() else if (view is TitleBar) view.refreshTopBarAppearance()`
 * ⇒ 不同类型顶栏刷新结果不一致（09-08 用户报障）。归一后只按 [TopBarRefreshable] 接口调用。
 */
class MainTopBarRefreshUnifyTest {

    private val rel = "ui/main/MainActivity.kt"

    @Test
    fun hostUsesInterfaceOnly() {
        val code = SourceFileProbe.sourceText(rel)
        assertTrue(
            "宿主必须只按接口调用（统一入口）",
            code.contains("(view as? TopBarRefreshable)?.refreshTopBarStyle()")
        )
        assertFalse(
            "不得残留类型分叉：view is MainTopBarView",
            code.contains("view is MainTopBarView")
        )
        assertFalse(
            "不得残留类型分叉：view is TitleBar",
            code.contains("view is TitleBar")
        )
        assertFalse(
            "不得残留旧专有刷新调用（refreshStyle / refreshTopBarAppearance）",
            code.contains("view.refreshStyle()") || code.contains("view.refreshTopBarAppearance()")
        )
    }

    @Test
    fun interfaceIsImported() {
        assertTrue(
            "TopBarRefreshable 必须显式 import（否则 KDOC 链接与类型解析失效）",
            SourceFileProbe.rawText(rel).contains("import io.legado.app.ui.widget.TopBarRefreshable")
        )
    }

    @Test
    fun walkStillCoversViewTree() {
        val code = SourceFileProbe.sourceText(rel)
        assertTrue(
            "递归遍历 View 树的行为不得丢失（五主 Tab 顶栏都靠它刷新）",
            code.contains("refreshMainTopBars(view.getChildAt(index))")
        )
    }
}