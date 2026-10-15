package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B15 批死码清理（被活等价实现取代 ⇒ 删除）：`AiImageProviderManageActivity.showActions` 是生图模型
 * 项菜单的**旧实现**，已被**已接线**的 `providerActions`（`providerActions = ::providerActions`，
 * 由 `AppManagementScaffold` 消费）整体取代且零调用。
 *
 * 断言缝说明：旧实现与宿主 UI 均需 Compose 宿主（不可纯 JVM 行为化）⇒ 只能以源码探针守护
 * 「旧实现不回潮 + 活单源仍在」（已按 G-42 exception 登记 `empty_test_allowlist.json` 含理由）。
 */
class AiImageProviderDeadActionsRetiredTest {

    @Test
    fun deadDuplicateMenuBuilderStaysDeleted() {
        val src = code()
        assertFalse("旧菜单实现 showActions 不得回潮", src.contains("fun showActions(provider"))
    }

    @Test
    fun liveSingleSourceMenuBuilderRemainsWired() {
        val src = code()
        assertTrue("活单源 providerActions 须存在", src.contains("fun providerActions(provider"))
        assertTrue("且须仍被宿主接线", src.contains("providerActions = ::providerActions"))
    }

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/config/AiImageProviderManageActivity.kt"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
    }
}
