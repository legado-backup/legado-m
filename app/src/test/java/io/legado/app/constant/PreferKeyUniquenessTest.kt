package io.legado.app.constant

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 配置键唯一性不变量测试。
 *
 * 为什么值得测：`PreferKey` 里所有键最终落到同一个 SharedPreferences 文件，
 * **两个不同常量若取同一字符串值**（复制粘贴/改名遗漏）会互相覆盖 —— 表现为
 * 「改 A 设置却影响 B」的静默串扰，且编译期无任何提示。此处把该不变量固化为断言。
 *
 * 本次连带覆盖：B1·R5 新增 `pageTurnAnimSpeed` 键的登记（键名与注释齐备）。
 */
class PreferKeyUniquenessTest {

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/constant/PreferKey.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun allPrefKeysHaveUniqueStringValues() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toList()
        assertTrue("应解析出足量配置键（当前 ${pairs.size}）", pairs.size > 300)

        val byValue = pairs.groupBy({ it.second }, { it.first })
        val dup = byValue.filter { it.value.size > 1 }
        assertTrue(
            "存在取同一字符串值的配置键（会造成设置串扰）：" +
                dup.entries.joinToString("; ") { "${it.key} <- ${it.value}" },
            dup.isEmpty()
        )
    }

    @Test
    fun r5PageTurnAnimSpeedKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("pageTurnAnimSpeed", pairs["pageTurnAnimSpeed"])
    }

    /** B3 新增键登记（R16 书架未读强调）。未登记即编译不过，此处固化**取值**防改名漏改。 */
    @Test
    fun b3BookshelfUnreadEmphasisKeyRegistered() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        assertEquals("bookshelfUnreadEmphasis", pairs["bookshelfUnreadEmphasis"])
    }

    /**
     * 主题失守修复配套（2026-09-24）：两个「首装标志」**必须分开**。
     *
     * 事故背景：`theme_first_install_done` 的语义是「本机为全新安装」（迁移后长期为 true），
     * 却被当成「已完成首装」用 ⇒ 每次启动重复套用外观套件、把用户主题还原。
     * 若两者将来被合并/取同值，该缺陷会立刻复发 ⇒ 此处固化「键名与取值都不同」。
     */
    @Test
    fun appearanceKitAutoApplyFlag_isDistinctFromThemeFirstInstallDone() {
        val pairs = Regex("const val (\\w+)\\s*=\\s*\"([^\"]*)\"")
            .findAll(source())
            .map { it.groupValues[1] to it.groupValues[2] }
            .toMap()
        val autoApply = pairs["appearanceKitAutoApplyDone"]
        val firstInstall = pairs["themeFirstInstallDone"]
        assertEquals("appearanceKitAutoApplyDone", autoApply)
        assertEquals("theme_first_install_done", firstInstall)
        assertTrue(
            "两个首装标志语义不同，取值不得相同（否则重复套用缺陷复发）",
            autoApply != firstInstall
        )
    }
}