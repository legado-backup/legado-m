package io.legado.app.help.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * unify-changelog-and-release：`UpdateLogDigest` 纯函数单测。
 *
 * 覆盖：版本名→日期解析 / 区间截取 / 去日期 / 分节合并顺序 / 跨版（跳版）覆盖 /
 * 起点不可解析兜底（最新一天）/ 空数据返回 null / 标题行。
 */
class UpdateLogDigestTest {

    private val sample = """
        # 更新日志

        ## cronet版本: 153.0.8010.27

        **2026/10/09（优化）**
        ### 优化
        - 甲优化
        ### 修复
        - 甲修复

        **2026/10/08（问题修复）**
        ### 修复
        - 乙修复

        **2026/10/07（优化与修复）**
        ### 优化
        - 丙优化
        ### 修复
        - 乙修复
    """.trimIndent()

    @Test
    fun parseVersionDate_validAndInvalid() {
        assertEquals("2026/10/09", UpdateLogDigest.parseVersionDate("3.26.100911"))
        assertEquals("2026/10/03", UpdateLogDigest.parseVersionDate("3.26.100321"))
        assertEquals("2026/09/28", UpdateLogDigest.parseVersionDate("3.26.092809"))
        assertEquals("2026/10/09", UpdateLogDigest.parseVersionDate(" 3.26.100911debug "))
        assertNull(UpdateLogDigest.parseVersionDate(null))
        assertNull(UpdateLogDigest.parseVersionDate(""))
        assertNull(UpdateLogDigest.parseVersionDate("1.2.3"))
    }

    @Test
    fun digest_rangeOnly_noDates_sectionOrder() {
        val text = UpdateLogDigest.digest(sample, "3.26.100321", "3.26.100911")!!
        // 标题行写出版本区间
        assertTrue(text.startsWith("3.26.100321 → 3.26.100911"))
        // 去日期：不得残留任何 YYYY/MM/DD
        assertTrue("不得残留日期标题", !text.contains("2026/10/"))
        // 分节顺序：优化 在 修复 之前
        assertTrue(text.indexOf("### 优化") < text.indexOf("### 修复"))
        // 三天条目全在
        listOf("甲优化", "甲修复", "乙修复", "丙优化").forEach {
            assertTrue("缺条目: $it", text.contains("- $it"))
        }
    }

    @Test
    fun digest_jumpVersion_coversWholeRange() {
        // 起点更早（09/28）⇒ 覆盖 10/07~10/09 全区间
        val text = UpdateLogDigest.digest(sample, "3.26.092809", "3.26.100911")!!
        assertTrue(text.contains("- 丙优化"))   // 10/07
        assertTrue(text.contains("- 乙修复"))   // 10/08
        assertTrue(text.contains("- 甲优化"))   // 10/09
    }

    @Test
    fun digest_fromUnparseable_fallsBackToNewestDay() {
        val text = UpdateLogDigest.digest(sample, "", "3.26.100911")!!
        assertTrue("兜底应只含最新一天（10/09）", text.contains("- 甲优化"))
        assertTrue("兜底不应含更早的 10/07 条目", !text.contains("- 丙优化"))
        // 起点缺失时不写区间标题
        assertTrue(!text.contains("→"))
    }

    @Test
    fun digest_emptyRange_returnsNull() {
        // 起点晚于所有条目 ⇒ 区间为空
        assertNull(UpdateLogDigest.digest(sample, "3.26.101020", "3.26.101021"))
    }

    @Test
    fun digest_noBlocks_returnsNull() {
        assertNull(UpdateLogDigest.digest("# 更新日志\n\n无任何日期块\n", "3.26.100321", "3.26.100911"))
        assertNull(UpdateLogDigest.digest("", "3.26.100321", "3.26.100911"))
    }
}