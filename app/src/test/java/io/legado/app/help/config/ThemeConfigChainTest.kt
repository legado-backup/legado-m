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

    /**
     * W7 8.2 / REQ-30：文章级离线预取属性须落在 `AppConfig` 且**默认关闭**（不改变既有行为）。
     */
    @Test
    fun imageArticlePrefetchDefaultsOff() {
        assertTrue(
            "AppConfig 须暴露 `imageArticlePrefetch` 且默认 false",
            appConfig.contains("getPrefBoolean(PreferKey.imageArticlePrefetch, false)")
        )
    }

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
    fun bottomWallpaperPackageHelpersStayForPendingWiring() {
        // B30 **更正**（2026-10-16）：这两个 helper 一度被按「被取代」判死（我已提交退役），复核证明**误判** ——
        // 关键证据：`addOrUpdate`(:302) 只调 `normalizeConfig`(:1272)（纯字段归一、**不复制壁纸进包**）；
        // 全文件唯一调「复制进包」的 `normalizeWallpaperPath`(:1298) 的活路径是 `copyEntryForMode`(:325)。
        // ⇒ UI 现行＝**绝对路径引用**模式（裁剪产物不随包），helper＝**壁纸随包（相对名）**模式 ⇒ **存储模式不同、无活替代者**
        // ⇒ 按「无活替代 ⇒ 保留」处置，**禁止当死码删**（B24 教训）。本用例为该结论的**永久防回退**断言。
        assertTrue(
            "壁纸随包模式的保存入口须保留（未接线，无活替代者）",
            navIconConfig.contains("fun saveBottomWallpaperToPackage(")
        )
        assertTrue(
            "壁纸随包模式的清理入口须保留（未接线，无活替代者）",
            navIconConfig.contains("fun clearBottomWallpaper(entry: Entry): Entry")
        )
        assertTrue(
            "跨日夜模式复制路径须仍在（唯一调用 normalizeWallpaperPath 的活路径）",
            navIconConfig.contains("normalizeWallpaperPath(source.wallpaperPath, dir)")
        )
    }
}