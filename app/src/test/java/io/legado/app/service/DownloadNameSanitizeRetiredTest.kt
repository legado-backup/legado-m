package io.legado.app.service

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * B15 批死码清理（被活等价实现取代 ⇒ 删除）：`DownloadService.sanitizeFileName` 只是
 * `sanitizeDownloadName` 的转发壳（`= sanitizeDownloadName(name)`）且**零调用**（新审计器命中）。
 *
 * 本类①**行为锁定保留下来的单源清洗语义**（删除后不得悄悄改变下载文件名口径）；②锁住旧壳不回潮。
 */
class DownloadNameSanitizeRetiredTest {

    @Test
    fun liveSanitizerKeepsItsContract() {
        assertEquals("a_b_c", sanitizeDownloadName("a/b:c"))
        assertEquals("x", sanitizeDownloadName("  x  "))
        assertEquals("a_b", sanitizeDownloadName("a\nb"))
        assertEquals("a_b", sanitizeDownloadName("a\\b"))
    }

    @Test
    fun deadForwarderDoesNotComeBack() {
        assertFalse("旧转发壳 sanitizeFileName 不得回潮", code().contains("fun sanitizeFileName("))
    }

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/service/DownloadService.kt"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
    }
}
