package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 外观/布局配置链的**一致性不变量**（2026-09-27 底栏搜索按钮删除 + 顶栏搜索可达性兜底）。
 *
 * 覆盖两条易失守的约定：
 * 1. 已删配置键 `floatingBottomBarHideSearch` 及派生字段 `hideSearchInFloatingStyle`
 *    在多份配置模型（AppConfig / MainLayoutPresetConfig / NavigationBarIconConfig /
 *    AppearanceKitManager）中**不得残留**（残留即悬空配置，编译期不可见）；
 * 2. `defaultTopBarShowSearch` 默认值必须为 **true**：底栏入口删除后顶栏是「书架 / 我的」
 *    的唯一搜索入口，默认 false 会让用户无从搜索。
 */
class ThemeConfigChainTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val appConfig by lazy { read("src/main/java/io/legado/app/help/config/AppConfig.kt") }
    private val presetConfig by lazy {
        read("src/main/java/io/legado/app/help/config/MainLayoutPresetConfig.kt")
    }
    private val navIconConfig by lazy {
        read("src/main/java/io/legado/app/help/config/NavigationBarIconConfig.kt")
    }
    private val kitManager by lazy {
        read("src/main/java/io/legado/app/help/config/AppearanceKitManager.kt")
    }
    private val topBarConfig by lazy { read("src/main/java/io/legado/app/help/config/TopBarConfig.kt") }

    @Test
    fun removedSearchToggleLeavesNoDanglingConfig() {
        assertFalse("AppConfig 仍暴露已删属性", appConfig.contains("var floatingBottomBarHideSearch"))
        assertFalse(
            "MainLayoutPresetConfig 仍声明已删函数",
            presetConfig.contains("fun floatingBottomBarHideSearch()")
        )
        assertFalse(
            "底栏包配置模型仍保留 hideSearchInFloatingStyle 派生字段",
            navIconConfig.contains("hideSearchInFloatingStyle")
        )
        assertFalse(
            "外观套件绑定模型仍保留已删字段",
            kitManager.contains("var floatingBottomBarHideSearch")
        )
    }

    @Test
    fun removedBuiltinKitIsRemappedNotDangling() {
        // 套件本体已移除，但常量与旧 id 重映射必须保留（否则旧 pref 指向不存在的套件）
        assertTrue(
            "旧套件 id 必须重映射到 KIT_FLOATING",
            kitManager.contains("if (it == KIT_FLOATING_NO_SEARCH) KIT_FLOATING else it")
        )
    }

    @Test
    fun topBarSearchDefaultsToVisible() {
        assertTrue(
            "AppConfig.defaultTopBarShowSearch 默认须为 true",
            appConfig.contains("getPrefBoolean(PreferKey.defaultTopBarShowSearch, true)")
        )
        assertTrue(
            "MainLayoutPresetConfig 默认须为 true",
            presetConfig.contains("getPrefBoolean(PreferKey.defaultTopBarShowSearch, true)")
        )
        assertTrue(
            "TopBarConfig 字段默认值须为 true",
            topBarConfig.contains("var showSearchInDefaultStyle: Boolean = true")
        )
    }

    @Test
    fun rssAutoVideoSwitchDefaultsToEnabled() {
        // REQ-12：默认开启（用户装上即可受益）；键名由设计固定
        assertTrue(
            "AppConfig.rssAutoVideoToPlayer 须存在且默认 true",
            appConfig.contains("getPrefBoolean(PreferKey.rssAutoVideoToPlayer, true)")
        )
    }

    @Test
    fun bottomBarSignatureNoLongerDependsOnRemovedKey() {
        assertFalse(
            "底栏签名不得再拼入已删键（否则签名恒不变导致刷新失效）",
            navIconConfig.contains("MainLayoutPresetConfig.floatingBottomBarHideSearch()")
        )
    }

    @Test
    fun sniffRaceSwitchDefaultsToEnabled() {
        // W2 / REQ-14：嗅探赛马化默认开启；关闭即为零回归回滚点（回落原串行链）
        assertTrue(
            "AppConfig.sniffRaceEnabled 须存在且默认 true",
            appConfig.contains("getPrefBoolean(PreferKey.sniffRaceEnabled, true)")
        )
        assertTrue(
            "setter 须落同一键（防读写分叉）",
            appConfig.contains("putPrefBoolean(PreferKey.sniffRaceEnabled, value)")
        )
    }
}