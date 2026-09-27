package io.legado.app.ui.about

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §5.3「残留节点清理」配对测试。
 *
 * 背景：`activity_read_record.xml` 历史上留了一个 `MainTopBarView@id/top_bar`（`visibility=gone`）
 * 的**残留节点** —— 它既不是 `installGlassTopBar` 的锚点（该函数按 `R.id.title_bar` 定位），也不参与渲染，
 * 仅让「10 个 `MainTopBarView` 声明里 5 个是空壳」的认知更混乱（design AD-TB-05 / tasks §5.3）。
 * 本测试锁住「已清理」：布局不得再出现该节点，页面不得再引用 `topBar` 视图。
 */
class ReadRecordTopBarNodeRetiredTest {

    private fun layoutRaw(name: String): String =
        File(SourceFileProbe.layoutDir(), name).readText()

    @Test
    fun layoutNoLongerDeclaresResidualTopBarNode() {
        val xml = layoutRaw("activity_read_record.xml")
        assertFalse(
            "activity_read_record.xml 不得再声明残留节点 MainTopBarView",
            xml.contains("MainTopBarView")
        )
        assertFalse(
            "activity_read_record.xml 不得再声明 id/top_bar",
            xml.contains("@+id/top_bar")
        )
        // 顶栏包 §5.2（2026-09-27）：真实节点 `TitleBar@id/title_bar` 亦整批退役 ——
        // 两个宿主（ReadRecordActivity / ReadRecordFragment）都已改用 Compose 顶栏，
        // 该节点在两条渲染路径上均不参与显示（原为「置 GONE / 运行时摘除」的历史占位）。
        assertFalse(
            "activity_read_record.xml 不得再声明遗留 View 顶栏 TitleBar",
            xml.contains("io.legado.app.ui.widget.TitleBar")
        )
        assertFalse(
            "activity_read_record.xml 不得再声明 id/title_bar",
            xml.contains("@+id/title_bar")
        )
    }

    @Test
    fun activityNoLongerReferencesTopBarView() {
        val src = SourceFileProbe.sourceText("ui/about/ReadRecordActivity.kt")
        assertFalse(
            "ReadRecordActivity 不得再引用 binding.topBar（残留节点已退役）",
            src.contains("binding.topBar")
        )
        assertFalse(
            "ReadRecordActivity 不得再引用已退役的 binding.titleBar",
            src.contains("binding.titleBar")
        )
        // 既有 Compose 换装语义不变：legacy 列表视图照旧隐藏、Compose 宿主显式可见
        assertTrue(src.contains("binding.scrollView.visibility"))
        assertTrue(src.contains("binding.composeHost.visibility"))
    }
}