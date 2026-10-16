package io.legado.app.ui.book.changesource

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 换源弹窗「View 时代主题助手」**整族退役**守护（迁移残留死件）。
 *
 * 缺陷背景：`ChangeSourceDialogTheme.kt`（`forceOpaque` / `changeSourceSurfaceColor` /
 * `changeSourceMutedColor` / `changeSourceDialogBackground` 4 个 `internal` 成员）全仓零消费者 ——
 * 其唯一消费方是 **View 时代**的换源弹窗；而本仓 `ChangeBookSourceDialog` / `ChangeChapterSourceDialog`
 * 已迁移为 **Compose**（`ComposeDialogFragment` + `AppDialogFrame` + `AppDialogStyle`）
 * ⇒ 该文件属**迁移残留**（被 Compose 取色体系取代），已整文件退役。
 *
 * 本类守护：①退役文件与符号不得回流；②两弹窗确实已迁 Compose 并消费 `AppDialogStyle`（活替代存在）。
 */
class ChangeSourceDialogThemeTest {

    private val main = "src/main/java/io/legado/app/ui/book/changesource/"

    private fun dirText(): String {
        val dir = listOf(File(main), File("../app/$main"), File("app/$main"))
            .first { it.isDirectory }
        return dir.listFiles { f -> f.extension == "kt" }!!.sortedBy { it.name }
            .joinToString("\n") { it.readText().replace("\r\n", "\n") }
    }

    @Test
    fun `View 时代主题助手已整族退役`() {
        val all = dirText()
        assertEquals(
            "退役文件不得回流",
            false,
            all.contains("fun Context.changeSourceDialogBackground(")
        )
        listOf("changeSourceMutedColor", "changeSourceSurfaceColor").forEach { name ->
            assertEquals("退役符号 $name 不得回流", false, all.contains("fun Context.$name("))
        }
    }

    @Test
    fun `换源弹窗已迁 Compose 并消费 AppDialogStyle`() {
        val all = dirText()
        assertEquals("两弹窗须为 ComposeDialogFragment（活替代存在）", true, all.contains("ComposeDialogFragment"))
        assertEquals("须消费 Compose 取色体系 AppDialogStyle", true, all.contains("AppDialogStyle"))
    }
}
