package io.legado.app.ui.main.ai.compose

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B24：`AiChatScreen.AiFallbackAvatar` 被取代分支退役守护。
 *
 * 证据：同文件 `Avatar` 族有 27 处活引用（活的头像组件族存在）⇒ 零调用的
 * `AiFallbackAvatar`（含 `@Composable` 注解）属冗余回退变体（被取代），退役。
 */
class AiFallbackAvatarRetiredTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `被取代的回退头像分支已退役且活头像族仍在`() {
        val src = code("src/main/java/io/legado/app/ui/main/ai/compose/AiChatScreen.kt")
        assertEquals("被取代的回退头像应退役", false, src.contains("fun AiFallbackAvatar("))
        assertEquals("活头像组件族仍须存在", true, src.contains("Avatar"))
    }
}
