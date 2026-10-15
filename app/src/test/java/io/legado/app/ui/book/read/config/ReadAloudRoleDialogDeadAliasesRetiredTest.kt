package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B15 批死码清理（被活等价实现取代 ⇒ 删除）：`ReadAloudConfigDialog` 的
 * `showAiRoleModelDialog`（模型选择旧实现 ⇒ 活单源 `showAiModelPicker`，被 `showAiReadAloudModelRoutingDialog` 四处调用）
 * 与 `showAiRolePromptDialog`（仅转发 `showMultiRolePromptDialog`，后者本身已被 `onClick = ::showMultiRolePromptDialog` 接线）
 * 双双零调用。
 *
 * 断言缝说明：均为 Compose 弹窗内部实现，纯 JVM 不可行为化 ⇒ 源码探针守护（已按 G-42 exception 登记含理由）。
 */
class ReadAloudRoleDialogDeadAliasesRetiredTest {

    @Test
    fun deadAliasesStayDeleted() {
        val src = code()
        assertFalse("旧模型选择实现 showAiRoleModelDialog 不得回潮", src.contains("fun showAiRoleModelDialog("))
        assertFalse("转发别名 showAiRolePromptDialog 不得回潮", src.contains("fun showAiRolePromptDialog("))
    }

    @Test
    fun liveSingleSourcesRemain() {
        val src = code()
        assertTrue("活模型选择单源 showAiModelPicker 须存在", src.contains("fun showAiModelPicker("))
        assertTrue("活提示词单源 showMultiRolePromptDialog 须存在", src.contains("fun showMultiRolePromptDialog("))
        assertTrue(
            "提示词入口须仍接线到活单源",
            src.contains("onClick = ::showMultiRolePromptDialog")
        )
    }

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/config/ReadAloudConfigDialog.kt"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")
    }
}
