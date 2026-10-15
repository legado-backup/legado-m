package io.legado.app.model.analyzeRule

import io.legado.app.constant.AppPattern
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * B15 批死码清理（被活等价实现取代 ⇒ 删除）：`AnalyzeUrl.extractHostFromUrl`（取 host，功能由
 * `AppPattern.domainRegex` 的活消费点承担）与 `AnalyzeUrl.saveCookie`（cookie 落盘已由 `HttpHelper`
 * 的 cookieJar 承担）双双**零调用**（新审计器命中）。
 *
 * 本类①**行为锁定 host 抽取的单源正则**（删除后不得改变取 host 口径）；②锁住两个死帮助函数不回潮。
 */
class AnalyzeUrlDeadHelpersRetiredTest {

    @Test
    fun hostPatternSingleSourceKeepsWorking() {
        assertEquals("example.com", AppPattern.domainRegex.find("https://example.com/a")?.groupValues?.getOrNull(1))
        assertEquals("host.cn", AppPattern.domainRegex.find("http://host.cn")?.groupValues?.getOrNull(1))
        assertEquals(null, AppPattern.domainRegex.find("not-a-url")?.groupValues?.getOrNull(1))
    }

    @Test
    fun deadHelpersDoNotComeBack() {
        val src = code()
        assertFalse("死帮助函数 extractHostFromUrl 不得回潮", src.contains("fun extractHostFromUrl("))
        assertFalse("死帮助函数 saveCookie 不得回潮（cookieJar 已承担落盘）", src.contains("fun saveCookie("))
    }

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
    }
}
