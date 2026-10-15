package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-42 试点批：`ThemeManageActivity` 宿主主题作用域上提守护。
 *
 * 缺陷背景：原 `attachComposeContent` 内**仅用 `LegadoTheme` 裹顶栏**（`GlassTopAppBar`），
 * 内容区（`ThemePackageManageScreen`）落在作用域外 ⇒ 主题包/夜间/自定义主题色下回落 M3 默认色板与字号。
 * 本批把 `LegadoTheme` 上提为内容根；并顺带删除此前受该宿主阻挡的零调用助手 `toThemeManageColorOrNull`。
 */
class ThemeManageHostThemeScopeTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `宿主主题作用域已上提且零调用助手已退役`() {
        val src = code("src/main/java/io/legado/app/ui/config/ThemeManageActivity.kt")
        // 精确形态：LegadoTheme 直接包裹内容 Column（证明「上提为内容根」而非仅裹顶栏）
        assertEquals("LegadoTheme 须直接包裹内容 Column", true,
            src.contains("LegadoTheme {\n                Column(modifier = Modifier.fillMaxSize()) {"))
        assertEquals("受阻挡的零调用助手已退役", false, src.contains("toThemeManageColorOrNull"))
        assertEquals("内容屏仍在（未误删）", true, src.contains("ThemePackageManageScreen("))
    }
}
