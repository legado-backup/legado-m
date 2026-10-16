package io.legado.app.lib.theme

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-86 续批 4：`ThemeUtils` 零引用助手退役守护。
 *
 * `resolveDrawable` 全仓零引用（**无**书源 JS 文档条目 / 无 XML 或反射调用），而同对象
 * `resolveColor` / `resolveFloat` 均活跃 ⇒ 属「未被使用的旧助手」⇒ 已删。
 * 本用例防其回流，并守住活实现不被误删。
 */
class ThemeUtilsRetiredHelperTest {

    private val src by lazy { SourceFileProbe.sourceText("lib/theme/ThemeUtils.kt") }

    @Test
    fun `零引用助手退役且活实现仍在`() {
        assertEquals("resolveDrawable 不得回流", false, src.contains("fun resolveDrawable("))
        assertEquals("活实现 resolveColor 必须保留", true, src.contains("fun resolveColor("))
        assertEquals("活实现 resolveFloat 必须保留", true, src.contains("fun resolveFloat("))
    }
}
