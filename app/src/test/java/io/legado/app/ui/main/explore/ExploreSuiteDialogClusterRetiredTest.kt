package io.legado.app.ui.main.explore

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B23：`ExploreFragment` 旧「套件/发现弹窗簇」整体退役守护。
 *
 * 缺陷背景：该 Fragment 内长期并存**一整套 in-fragment 套件弹窗 UI**
 * （选择/管理/创建/重命名/别名/新增挂件/挂件类型·来源·标签/删除确认 + 其专属渲染助手），
 * 经 `audit_dead_private_fun.py` 迭代判定为 **`private` 作用域内零调用（不可达）**：
 * 套件功能本体由活屏 `DiscoverySuiteHomeScreen` / `DiscoverySuiteManageActivity` 承接
 * （`DiscoverySuiteStore` 在文件内仍有 16 处活引用）⇒ 旧弹窗簇属「被取代」实现，整体退役。
 *
 * 本类固化退役结果；并守护套件存储/活屏接线不被误删。
 */
class ExploreSuiteDialogClusterRetiredTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `旧套件弹窗簇已整体退役且套件存储仍活`() {
        val src = code("src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt")
        val retired = listOf(
            "showSuiteSelector", "showSuiteManageDialog", "showCreateSuiteDialog", "showRenameSuiteDialog",
            "showSuiteAliasDialog", "showAddSuiteWidgetDialog", "showSuiteWidgetTypeDialog",
            "showSuiteWidgetSourceDialog", "showSuiteWidgetTagDialog", "confirmDeleteSuite",
            "canShowSuiteDialog", "updateSuite", "saveSuiteConfig", "handleDiscoverToggleFromDialog",
            "createDiscoverDialogControl", "createDiscoverDialogText", "createDiscoverDialogSelect",
            "filterDiscoverDialogItems", "discoverDialogLabel", "applyDiscoverDialogFlexStyle"
        )
        assertEquals("旧弹窗簇不应有声明残留", emptyList<String>(),
            retired.filter { src.contains("fun $it(") })
        assertTrue("套件存储仍是活依赖（不得整体清零）", src.contains("DiscoverySuiteStore"))
    }
}
