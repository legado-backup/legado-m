package io.legado.app.ui

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 批次**范围闭合**的机检不变量（tasks §5.1 验证标准：「45 个页名 → 六个桶，集合校验，缺一即 FAIL」）。
 *
 * 为什么必须机检：CE-a/CE-b 的页名清单是从「实测 XML 行数 + 复杂度 + 例外汇总」推导出来的，
 * **人工核对必然漂移**（本轮已实证蓝图数字多次失实：string 544→实测 40、可清壳 57→实测 0）。
 * 故把「45 = CE-a 18 + CE-b 17 + 技术硬例外保留 4 + 主 Tab 3 + `activity_main` 1 + 专向 spec 2」
 * 固化为集合断言：任一新页加入/遗漏、任一桶被挪动，本测试即失败。
 *
 * 依据：`docs/specs/compose-advance-continuation/tasks.md` §5.1 / `XML优化方案.md` §4.3-§4.5。
 */
class CeScopePartitionTest {

    private fun layoutDir(): File = SourceFileProbe.layoutDir()

    /** 实测口径：`activity_*` + `fragment_*` 布局（`layout-land` 变体不计）。 */
    private fun actualPages(): Set<String> =
        layoutDir().listFiles()
            ?.filter { it.isFile && it.extension == "xml" }
            ?.map { it.nameWithoutExtension }
            ?.filter { it.startsWith("activity_") || it.startsWith("fragment_") }
            ?.toSet()
            ?: emptySet()

    /** CE-a 18：真实 View 主体（E 类 23 − 转 CG 保留 2 − 专向 spec 2 − `activity_main` 1）。 */
    private val ceA = setOf(
        "activity_book_read", "activity_manga", "activity_video_player", "fragment_video",
        "activity_image_crop", "activity_image_gallery", "activity_image_detail",
        "activity_theme_manage", "activity_code_edit", "activity_replace_edit",
        "activity_rss_source_edit", "activity_book_source_edit", "activity_paragraph_rule_edit",
        "activity_audio_play", "activity_book_search", "activity_search_content",
        "activity_rss_search", "activity_web_view",
    )

    /** CE-b 17：C 有效面 7 + D 10（实测全非纯容器 ⇒ 主体级改造）。 */
    private val ceB = setOf(
        // C 有效面 7
        "activity_about", "activity_explore_show", "activity_import_book",
        "activity_qrcode_capture", "activity_rss_read", "activity_translucence",
        "fragment_web_view_login",
        // D 10
        "activity_arrange_book", "activity_book_source", "activity_cover_collection_manage",
        "activity_replace_rule", "activity_rss_artivles", "activity_rss_favorites",
        "activity_rss_source", "activity_rule_sub", "activity_s3_container_manage",
        "fragment_rss_articles",
    )

    /** 技术硬例外保留 4（真不做，附理由见 component-registry §5.2）。 */
    private val reserved = setOf(
        "fragment_rss", "fragment_explore", "activity_read_record_stats", "activity_source_login",
    )

    /** 主 Tab 3（层 1 顶栏，DoD 例外③）。 */
    private val mainTabs = setOf("fragment_bookshelf1", "fragment_bookshelf2", "fragment_my_config")

    /** 主壳容器 1（随 CG 批次）。 */
    private val mainShell = setOf("activity_main")

    /** 专向 spec 2（`read-record-header-unify` / `book-info-modern-compose`）。 */
    private val dedicatedSpecs = setOf("activity_read_record", "activity_book_info")

    private fun buckets() = listOf(
        "CE-a" to ceA, "CE-b" to ceB, "技术硬例外保留" to reserved,
        "主 Tab" to mainTabs, "主壳" to mainShell, "专向 spec" to dedicatedSpecs,
    )

    @Test
    fun bucketSizesAreLocked() {
        assertEquals("CE-a 必须为 18 页", 18, ceA.size)
        assertEquals("CE-b 必须为 17 页", 17, ceB.size)
        assertEquals("技术硬例外保留必须为 4 页", 4, reserved.size)
        assertEquals("主 Tab 必须为 3 页", 3, mainTabs.size)
        assertEquals("主壳必须为 1 页", 1, mainShell.size)
        assertEquals("专向 spec 必须为 2 页", 2, dedicatedSpecs.size)
    }

    @Test
    fun bucketsAreMutuallyExclusive() {
        val all = buckets().flatMap { it.second }
        assertEquals("六个桶之间不得重复：${all.size} vs ${all.toSet().size}", all.size, all.toSet().size)
    }

    @Test
    fun partitionCoversAllActualPages() {
        val actual = actualPages()
        val mapped = buckets().flatMap { it.second }.toSet()
        assertEquals("实测页面数应为 45（activity_* 37 + fragment_* 8）", 45, actual.size)
        val missing = actual - mapped
        val extra = mapped - actual
        assertTrue("以下实测布局未落入任何桶：$missing", missing.isEmpty())
        assertTrue("以下桶内页名在实测布局中不存在（蓝图失实）：$extra", extra.isEmpty())
    }
}