package io.legado.app.ui.widget

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 主界面顶栏的**搜索可达性**不变量（2026-09-27 底栏悬浮搜索按钮删除）。
 *
 * 底栏按钮删除后，「书架 / 我的」两模式的搜索入口只剩顶栏 ⇒
 * ① 原「底栏隐藏搜索时自动顶上来」的补偿联动必须移除（它依赖已删键）；
 * ② 顶栏搜索可见性改由顶栏包配置决定，且该配置默认值必须为 true（否则用户无从搜索）。
 */
class MainTopBarViewSearchTest {

    private val topBarView by lazy {
        listOf(
            File("src/main/java/io/legado/app/ui/widget/MainTopBarView.kt"),
            File("../app/src/main/java/io/legado/app/ui/widget/MainTopBarView.kt"),
            File("app/src/main/java/io/legado/app/ui/widget/MainTopBarView.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun compensationLinkageIsRemoved() {
        assertFalse(
            "顶栏仍依赖已删键做补偿联动",
            topBarView.contains("floatingBottomBarHideSearch")
        )
        assertFalse(
            "补偿联动函数应已移除",
            topBarView.contains("isFloatingSearchHidden")
        )
    }

    @Test
    fun searchVisibilityIsDrivenByTopBarPackageConfig() {
        assertTrue(
            "「书架 / 我的」的搜索可见性须读顶栏包配置",
            topBarView.contains("searchButton.isVisible = config.showSearchInDefaultStyle")
        )
    }

    @Test
    fun sideNavigationSearchRowIsKept() {
        assertTrue(
            "侧边导航的搜索行属保留项",
            topBarView.contains("sideSearchButton") || topBarView.contains("searchEntry")
        )
    }
}