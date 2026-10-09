package io.legado.app.ui.main

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * G-37 回归契约：`MainActivity` 的 Compose 宿主入口顶层必须带应用主题作用域。
 *
 * 背景：`liquidGlassSampleBackground` / `bottomNavigationWallpaper` 两处 `setContent`
 * 承载背景层与壁纸层，若宿主顶层缺 `LegadoTheme{}`，其子树 `colorScheme` 会回落
 * M3 默认亮色基线（夜间/自定义主题下「黑字黑图标」）。两处虽不消费色板，
 * 但口径须统一（`theme-consistency-iron-rule` AD-01），且 G-37 以「改动文件」口径校验。
 */
class MainActivityComposeHostScopeTest {

    private fun mainActivity(): String = SourceFileProbe.sourceText("ui/main/MainActivity.kt")

    /** 断言某个调用点前 200 字符内出现了 `LegadoTheme {`（即被顶层包裹） */
    private fun assertWrapped(src: String, callToken: String) {
        val idx = src.indexOf(callToken)
        assertTrue("未找到调用点：$callToken", idx >= 0)
        val window = src.substring((idx - 200).coerceAtLeast(0), idx)
        assertTrue("宿主入口 $callToken 前未出现 LegadoTheme{ 顶层作用域", window.contains("LegadoTheme {"))
    }

    @Test
    fun backgroundHostIsThemeScoped() {
        assertWrapped(mainActivity(), "MainThemeBackgroundLayer(version = mainBackgroundVersion)")
    }

    @Test
    fun wallpaperHostIsThemeScoped() {
        assertWrapped(mainActivity(), "ComposeThemeImageLayer(")
    }
}