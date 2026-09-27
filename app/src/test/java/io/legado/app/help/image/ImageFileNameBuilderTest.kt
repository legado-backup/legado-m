package io.legado.app.help.image

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.5 / REQ-24：图片保存文件名规范化的**纯逻辑**用例。
 *
 * 关键不变量（对应验收判据「语义可辨 / 无非法字符 / 无重名覆盖」）：
 * - 语义：来源 + 文章 + 序号 + 时间戳都在名里；
 * - 非法字符与空白必须被清除（SAF/Windows 禁用集）；
 * - **同名去重**：候选名已存在时追加 `_n`，否则同名会走 `createFileIfNotExist` 静默覆盖。
 */
class ImageFileNameBuilderTest {

    private val ctx = ImageNameContext(
        sourceName = "我的订阅",
        articleTitle = "第 3 话/更新",
        index = 7,
    )

    @Test
    fun buildKeepsSemanticPartsAndLegalCharsOnly() {
        val name = ImageFileNameBuilder.build(ctx, "https://example.test/a/b.png", at = 0L)
        assertTrue("须含来源名", name.contains("我的订阅"))
        assertTrue("须含文章标题（非法字符已替换）", name.contains("第3话_更新"))
        assertTrue("须含序号", name.contains("p007"))
        assertTrue("须保留真实扩展名", name.endsWith(".png"))
        assertTrue("不得残留非法字符", listOf('/', '\\', ':', '*', '?', '"', '<', '>', '|').none { it in name })
        assertTrue("不得含空白字符", !name.any { it.isWhitespace() })
    }

    @Test
    fun differentUrlsProduceDifferentNamesAndSameInputIsStable() {
        val a1 = ImageFileNameBuilder.build(ctx, "https://example.test/1.jpg", at = 1_700_000_000_000L)
        val a2 = ImageFileNameBuilder.build(ctx, "https://example.test/1.jpg", at = 1_700_000_000_000L)
        val b = ImageFileNameBuilder.build(ctx, "https://example.test/2.jpg", at = 1_700_000_000_000L)
        assertEquals("同输入须稳定（可复现）", a1, a2)
        assertNotEquals("不同图片不得同名（URL 摘要参与命名）", a1, b)
    }

    @Test
    fun blankContextFallsBackInsteadOfEmptyBase() {
        val name = ImageFileNameBuilder.build(ImageNameContext(), "https://example.test/x", at = 0L)
        assertTrue("无上下文须回落通用名而非空串", name.startsWith("image_"))
    }

    @Test
    fun extensionComesFromUrlAndFallsBackToJpg() {
        assertEquals("png", ImageFileNameBuilder.extensionOf("https://a.test/x.PNG"))
        assertEquals("webp", ImageFileNameBuilder.extensionOf("https://a.test/x.webp?size=2"))
        assertEquals("jpg", ImageFileNameBuilder.extensionOf("https://a.test/noext"))
        assertEquals("jpg", ImageFileNameBuilder.extensionOf("https://a.test/x.unknown"))
    }

    @Test
    fun uniqueInAppendsSuffixUntilFree() {
        val existing = setOf("a_p001_x.jpg", "a_p001_x_1.jpg")
        assertEquals("a_p001_x_2.jpg", ImageFileNameBuilder.uniqueIn("a_p001_x.jpg", existing))
        assertEquals("free.jpg", ImageFileNameBuilder.uniqueIn("free.jpg", existing))
    }

    @Test
    fun sanitizeHandlesNullAndIllegalOnlyInput() {
        assertEquals("", ImageFileNameBuilder.sanitize(null))
        assertEquals("", ImageFileNameBuilder.sanitize("   "))
        assertEquals("", ImageFileNameBuilder.sanitize("..."))
        assertEquals("a_b", ImageFileNameBuilder.sanitize(" a\\b "))
    }
}