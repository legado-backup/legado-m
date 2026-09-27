package io.legado.app.ui.main

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 用户裁决（2026-09-27）：**删除底栏悬浮搜索按钮**。
 *
 * 该按钮牵涉 6 处（布局 / MainActivity 玻璃与约束 / 配置链 / 设置开关 / 双 strings / 备份忽略键），
 * 任一处漏删都会留下**悬空引用**（编译期可见）或**静默残链**（编译期不可见，如旧备份写回已删键）。
 * 本测试把「已删干净」固化为回归不变量。
 *
 * 搜索可达性同时被锁定：底栏按钮删除后，「书架 / 我的」两模式的搜索入口只剩顶栏，
 * 故 `defaultTopBarShowSearch` 默认值必须为 **true**，否则用户无从搜索。
 */
class BottomBarSearchRemovalTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val layout by lazy { read("src/main/res/layout/activity_main.xml") }
    private val mainActivity by lazy {
        read("src/main/java/io/legado/app/ui/main/MainActivity.kt")
    }
    private val preferKey by lazy { read("src/main/java/io/legado/app/constant/PreferKey.kt") }
    private val appConfig by lazy { read("src/main/java/io/legado/app/help/config/AppConfig.kt") }
    private val topBarView by lazy {
        read("src/main/java/io/legado/app/ui/widget/MainTopBarView.kt")
    }
    private val backupConfig by lazy { read("src/main/java/io/legado/app/help/storage/BackupConfig.kt") }
    private val otherConfig by lazy {
        read("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt")
    }

    @Test
    fun layoutNoLongerDeclaresBottomSearchButton() {
        listOf(
            "search_button_container",
            "search_button_glass_view",
            "search_button_shell_overlay",
            "@+id/search_button\"",
            "@+id/search_button_icon"
        ).forEach { id ->
            assertFalse("布局仍残留底栏搜索按钮节点：$id", layout.contains(id))
        }
        // 约束不得再指向已删节点
        assertFalse("布局约束仍指向已删的 search_button_container", layout.contains("@id/search_button_container"))
        // 侧边导航的搜索按钮属**保留项**（不在本次删除范围）
        assertTrue("侧边导航搜索按钮须保留", layout.contains("@+id/side_search_button"))
    }

    @Test
    fun mainActivityStillOwnsNoBottomSearchButtonBinding() {
        listOf(
            "searchButtonContainer", "searchButtonGlassView", "searchButtonShellOverlay",
            "searchButtonIcon", "isFloatingSearchHidden"
        ).forEach { symbol ->
            assertFalse("MainActivity 仍引用已删符号：$symbol", mainActivity.contains(symbol))
        }
        assertTrue("侧边导航搜索行点击须保留", mainActivity.contains("sideSearchButton.setOnClickListener"))
    }

    @Test
    fun configChainIsFullyRemoved() {
        assertFalse("PreferKey 仍声明已删键", preferKey.contains("const val floatingBottomBarHideSearch"))
        assertFalse("AppConfig 仍暴露已删属性", appConfig.contains("var floatingBottomBarHideSearch"))
        assertFalse(
            "设置页仍残留该开关（断言声明而非词面：注释里会提到它为何被删）",
            otherConfig.contains("key = PreferKey.floatingBottomBarHideSearch")
        )
    }

    @Test
    fun oldBackupPreferenceMustBeIgnoredOnRestore() {
        assertTrue(
            "旧备份中的已删键必须纳入 ignorePrefKeys（防写回）",
            backupConfig.contains("\"floatingBottomBarHideSearch\"")
        )
    }

    @Test
    fun topBarSearchIsTheRemainingEntryAndDefaultsToVisible() {
        // 「书架 / 我的」的顶栏搜索可见性由顶栏包配置决定（补偿联动已删）
        assertTrue(
            "顶栏搜索可见性须读顶栏包配置",
            topBarView.contains("searchButton.isVisible = config.showSearchInDefaultStyle")
        )
        assertTrue(
            "defaultTopBarShowSearch 默认值须为 true（底栏入口删除后的可达性底线）",
            appConfig.contains("getPrefBoolean(PreferKey.defaultTopBarShowSearch, true)")
        )
    }
}