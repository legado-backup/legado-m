package io.legado.app.ui.book.read.page.provider

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B18：`ZhLayout` 标点压缩旧助手退役守护。
 *
 * 缺陷背景：`getPostPancOffset`/`getPrePancOffset`（按标点生长方向做字距微调）经
 * `audit_dead_private_fun.py` 判定 `private` 作用域内零调用（不可达）；其唯一消费者消失，
 * 仅被二者使用的 `gap` 常量随之成为孤儿 ⇒ 一并退役。活实现 `getDesiredWidth` 保留。
 */
class ZhLayoutRetiredKernHelperTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `标点压缩旧助手与孤立 gap 已退役且活实现仍在`() {
        val src = code("src/main/java/io/legado/app/ui/book/read/page/provider/ZhLayout.kt")
        assertEquals("旧标点偏移助手应退役", emptyList<String>(),
            listOf("getPostPancOffset", "getPrePancOffset").filter { src.contains("fun $it(") })
        assertEquals("仅被上述助手使用的 gap 常量应一并退役", false, src.contains("private val gap ="))
        assertEquals("活实现 getDesiredWidth 必须保留", true, src.contains("fun getDesiredWidth("))
    }
}
