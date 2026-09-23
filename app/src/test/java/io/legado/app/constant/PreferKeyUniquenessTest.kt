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
}