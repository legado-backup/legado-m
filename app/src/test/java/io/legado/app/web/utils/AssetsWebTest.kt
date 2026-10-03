package io.legado.app.web.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * AssetsWeb 单测（一期 · 3.4 MIME 扩展 / 3.5 路径安全）。
 *
 * 只测两个**纯函数**（`mimeOf` / `isSafePath`）—— `AssetsWeb` 实例化依赖 `appCtx.assets`
 * （非纯 JVM 可构造），故把判定逻辑收进 companion 以便直接验证（同 `TokenManager.TokenStore` 接缝思路）。
 */
class AssetsWebTest {

    // ------------------------------------------------------------ 3.4 MIME

    @Test
    fun mimeOf_newExtensions_areMapped() {
        val expected = mapOf(
            "/vue/assets/a.png" to "image/png",
            "/vue/assets/a.svg" to "image/svg+xml",
            "/vue/assets/a.woff" to "font/woff",
            "/vue/assets/a.woff2" to "font/woff2",
            "/vue/assets/a.ttf" to "font/ttf",
            "/vue/assets/a.json" to "application/json",
            "/vue/assets/a.map" to "application/json",
        )
        expected.forEach { (path, mime) ->
            assertEquals("$path 的 MIME 不符", mime, AssetsWeb.mimeOf(path))
        }
    }

    @Test
    fun mimeOf_jpg_usesStandardValue_imageJpeg() {
        // 行为变更登记：原 image/jpg（非标准）⇒ 改为标准值 image/jpeg（design §1.4.2 / REQ-1-304）
        assertEquals("image/jpeg", AssetsWeb.mimeOf("/vue/assets/a.jpg"))
        assertEquals("image/jpeg", AssetsWeb.mimeOf("/vue/assets/a.jpeg"))
    }

    @Test
    fun mimeOf_legacyExtensions_unchanged() {
        assertEquals("text/html", AssetsWeb.mimeOf("/vue/index.html"))
        assertEquals("text/html", AssetsWeb.mimeOf("/vue/index.htm"))
        assertEquals("text/javascript", AssetsWeb.mimeOf("/vue/assets/a.js"))
        assertEquals("text/css", AssetsWeb.mimeOf("/vue/assets/a.css"))
        assertEquals("image/x-icon", AssetsWeb.mimeOf("/favicon.ico"))
    }

    @Test
    fun mimeOf_isCaseInsensitive() {
        assertEquals("image/png", AssetsWeb.mimeOf("/vue/assets/A.PNG"))
        assertEquals("image/jpeg", AssetsWeb.mimeOf("/vue/assets/A.JPG"))
    }

    @Test
    fun mimeOf_unknownOrMissingExtension_fallsBackToHtml_withoutCrash() {
        assertEquals("text/html", AssetsWeb.mimeOf("/vue/assets/a.xyz"))
        // 原实现 lastIndexOf(".") == -1 时 substring(-1) 会抛异常；此处必须回落而非崩
        assertEquals("text/html", AssetsWeb.mimeOf("/vue/assets/noext"))
        assertEquals("text/html", AssetsWeb.mimeOf("/"))
    }

    // ------------------------------------------------------------ 3.5 路径安全

    @Test
    fun isSafePath_acceptsNormalAssetPaths() {
        listOf("/", "/index.html", "/vue/index.html", "/vue/assets/a-b_c.png").forEach {
            assertTrue("$it 应判定为安全", AssetsWeb.isSafePath(it))
        }
    }

    @Test
    fun isSafePath_rejectsTraversalNulAndRelative() {
        listOf(
            "/../legado.db",
            "/vue/../../etc/passwd",
            "/a/../b",
            "/a\u0000b",
            "vue/index.html", // 非 / 开头
            "",
        ).forEach {
            assertFalse("${it.replace('\u0000', '?')} 必须被拒绝", AssetsWeb.isSafePath(it))
        }
    }
}
