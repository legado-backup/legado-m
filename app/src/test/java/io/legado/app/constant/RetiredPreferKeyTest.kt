package io.legado.app.constant

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 已删配置键的**退役不变量**（2026-09-27 用户裁决：删除底栏悬浮搜索按钮）。
 *
 * 删除一个 pref 键涉及三处，漏任一处都会留下隐患：
 * ① `PreferKey` 声明（漏删 ⇒ 死键）
 * ② `BackupConfig.ignorePrefKeys`（漏删 ⇒ **旧备份把已删键写回**）
 * ③ 消费点（漏删 ⇒ 编译期报错，属可见错误）
 */
class RetiredPreferKeyTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val preferKey by lazy { read("src/main/java/io/legado/app/constant/PreferKey.kt") }
    private val backupConfig by lazy {
        read("src/main/java/io/legado/app/help/storage/BackupConfig.kt")
    }

    @Test
    fun removedKeyIsNoLongerDeclared() {
        assertFalse(
            "已删键仍声明在 PreferKey（成为死键）",
            preferKey.contains("const val floatingBottomBarHideSearch")
        )
    }

    @Test
    fun removedKeyIsIgnoredOnRestore() {
        assertTrue(
            "旧备份中的已删键必须纳入 ignorePrefKeys（防写回）",
            backupConfig.contains("\"floatingBottomBarHideSearch\"")
        )
    }

    @Test
    fun ignorePrefKeysIsAStringArrayOnKeyIsNotIgnorePath() {
        // 结构不变量：忽略清单必须是 keyIsNotIgnore 的首条判定（顺序对才生效）
        val body = backupConfig.substringAfter("fun keyIsNotIgnore")
        assertTrue(
            "ignorePrefKeys 必须是 keyIsNotIgnore 的首条判定",
            body.indexOf("ignorePrefKeys.contains(key)") in 1..200
        )
        assertTrue("忽略清单须为字符串数组", backupConfig.contains("private val ignorePrefKeys = arrayOf("))
    }
}