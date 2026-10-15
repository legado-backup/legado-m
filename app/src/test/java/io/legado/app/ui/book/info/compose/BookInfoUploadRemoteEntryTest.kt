package io.legado.app.ui.book.info.compose

import io.legado.app.ui.book.info.needsUploadConfirm
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B14：沉浸式书籍信息页「上传 WebDav」入口接线不变量。
 *
 * 缺陷背景（本类存在的理由）：`BookInfoComposeActivity.upLoadBook` 实现完整却**全仓零调用点**
 * （`ai_tests/scripts/audit_dead_private_fun.py` 命中），即该页的「上传 WebDav」**从未接线**；
 * 而同一功能的另两种页样式（经典 `BookInfoActivity` / 现代 `BookInfoModernActivity`）都有该菜单项
 * ⇒ 用户切到沉浸式样式后功能凭空消失（可感的功能缺失，属"迁移漏接线"而非死代码）。
 *
 * 判据分两层：①**行为断言** —— 上传前的二次确认口径（有无远端地址）是唯一可 JVM 执行的部分，
 * 以期望值锁定，防止两处页样式各写一份而漂移；②**接线探针** —— 菜单项与回调存在性（Compose 宿主
 * 不可行为化）。
 */
class BookInfoUploadRemoteEntryTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
            .lines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")

    @Test
    fun uploadConfirmDecisionMatchesModernPageContract() {
        // 行为断言（带期望值）：无远端地址（null）⇒ 直接上传；有远端地址 ⇒ 必须先确认（避免覆盖云端备份）
        assertEquals(false, needsUploadConfirm(null))
        assertEquals(true, needsUploadConfirm("remote://host/book"))
        assertEquals(true, needsUploadConfirm("http://host/a.json"))
    }

    @Test
    fun immersiveHostWiresUploadCallbackToImplementation() {
        val activity = code("src/main/java/io/legado/app/ui/book/info/BookInfoComposeActivity.kt")
        assertTrue(
            "沉浸式宿主必须把 onUploadToRemote 接到实现（否则入口点了没反应）",
            activity.contains("onUploadToRemote = ::uploadBookToRemote")
        )
        assertTrue("须有上传实现", activity.contains("private fun uploadBookToRemote()"))
        assertTrue("确认口径须走纯函数单源", activity.contains("needsUploadConfirm("))
        assertTrue("须复用既有 upLoadBook（补齐后不得再是零调用）", activity.contains("upLoadBook(book)"))
    }

    @Test
    fun immersiveMoreMenuExposesTheEntry() {
        val route = code("src/main/java/io/legado/app/ui/book/info/compose/BookInfoComposeRoute.kt")
        assertTrue("更多菜单须含「上传 WebDav」条目", route.contains("R.string.upload_to_remote"))
        assertTrue("菜单条目须触发上传回调", route.contains("actions.onUploadToRemote()"))
        assertTrue(
            "动作契约须暴露上传回调（与经典/现代页同构）",
            route.contains("val onUploadToRemote: () -> Unit")
        )
    }
}
