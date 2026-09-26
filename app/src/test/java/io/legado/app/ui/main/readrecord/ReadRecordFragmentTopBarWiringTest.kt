package io.legado.app.ui.main.readrecord

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §5.3「残留节点清理」配对测试（记录页主 Tab 宿主）。
 *
 * 背景：`activity_read_record.xml` 与 `ReadRecordActivity` **共用**，其中的
 * `MainTopBarView@id/top_bar`（`visibility=gone`）是历史残留空壳；`ReadRecordFragment`
 * 原先在 `installComposeTopBar()` 里按「先摘旧顶栏节点、再于索引 0 插入 Compose 顶栏」处理它。
 * 本次将残留节点与两处引用一并清理（插入索引本就 `coerceAtMost(childCount)`，与旧节点无关）。
 */
class ReadRecordFragmentTopBarWiringTest {

    @Test
    fun fragmentNoLongerRemovesResidualTopBarNode() {
        val src = SourceFileProbe.sourceText("ui/main/readrecord/ReadRecordFragment.kt")
        assertFalse(
            "ReadRecordFragment 不得再引用 binding.topBar（残留节点已退役）",
            src.contains("binding.topBar")
        )
    }

    @Test
    fun fragmentStillInstallsComposeTopBarAtHead() {
        val src = SourceFileProbe.sourceText("ui/main/readrecord/ReadRecordFragment.kt")
        assertTrue("仍须摘除布局内的真实 title_bar 节点", src.contains("removeView(binding.titleBar)"))
        assertTrue(
            "Compose 顶栏仍须插入到容器头部（索引 0，带 childCount 兜底）",
            src.contains("container.addView(topBarView, 0.coerceAtMost(container.childCount))")
        )
        assertTrue("仍须渲染 Compose 顶栏单源 GlassTopAppBar", src.contains("GlassTopAppBar("))
    }
}