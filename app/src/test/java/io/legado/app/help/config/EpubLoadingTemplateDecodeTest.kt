package io.legado.app.help.config

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 首屏加载模板**契约与纯函数**单测（reader-theme-family 3.12 配对）。
 *
 * 覆盖两件事：
 * ①**编解码契约**（`decodeLoadingPayload` / `encodeLoadingPayload` / `parseLoadingLibrary`）——
 *    类型/版本/白名单/区间/色值/文案长度逐项**边界值**断言；往返（encode→decode）全字段等值；
 *    `parseLoadingLibrary` 对"冒充内置 id"的条目必须丢弃（否则用户可绕开"内置不可删"）。
 * ②**模型纯函数**（`parseHexColor` / `luminance` / `argbToHex` / `Palette.tokens` / 昼夜取套）——
 *    这些是明暗判定与 SVG 参数化的底座，错一位就会出现"夜间首屏刺眼"这类难以归因的观感问题。
 */
class EpubLoadingTemplateDecodeTest {

    private fun payload(
        type: String = EpubLoadingTemplate.DOC_TYPE,
        version: Int = EpubLoadingTemplate.DOC_VERSION,
        name: String = "测试套",
        description: String = "说明",
        scene: String = "ink",
        eyebrow: String = "题记",
        caption: String = "副文案",
        titleFont: String = "serif",
        titleSize: Double = 28.0,
        artScale: Double = 1.0,
        includeDay: Boolean = true,
        dayColor: String = "#F6F1E6"
    ): String = JSONObject().apply {
        put("type", type)
        put("version", version)
        put("name", name)
        put("description", description)
        put("scene", scene)
        put("eyebrow", eyebrow)
        put("caption", caption)
        put("titleFont", titleFont)
        put("titleSize", titleSize)
        put("artScale", artScale)
        if (includeDay) {
            put("day", JSONObject().apply {
                listOf("background", "horizon", "ink", "muted", "accent", "glow").forEach { put(it, dayColor) }
            })
        }
        put("night", JSONObject().apply {
            listOf("background", "horizon", "ink", "muted", "accent", "glow").forEach { put(it, "#101216") }
        })
    }.toString()

    private fun expectFail(json: String, keyword: String) {
        val result = decodeLoadingPayload(json)
        assertTrue("应判失败：$keyword", result.isFailure)
        val message = result.exceptionOrNull()?.message.orEmpty()
        assertTrue("失败原因应含『$keyword』，实际=$message", message.contains(keyword))
    }

    @Test
    fun `合法载荷可解码且字段逐一就位`() {
        val result = decodeLoadingPayload(payload(scene = "bloom", titleFont = "sans-serif", titleSize = 24.0, artScale = 0.9))
        val decoded = result.getOrNull()
        assertNotNull("合法载荷必须可解码：${result.exceptionOrNull()?.message}", decoded)
        assertEquals("测试套", decoded!!.name)
        assertEquals("说明", decoded.description)
        assertEquals(Scene.BLOOM, decoded.scene)
        assertEquals("sans-serif", decoded.titleFont)
        assertEquals(24.0f, decoded.titleSize, 0.001f)
        assertEquals(0.9f, decoded.artScale, 0.001f)
        assertEquals(6, decoded.day.tokens().size)
    }

    @Test
    fun `类型与版本必须严格等值`() {
        expectFail(payload(type = "legado.epub.reader"), "不是首屏加载模板")
        expectFail(payload(version = 2), "模板版本不支持")
    }

    @Test
    fun `场景与字体走白名单`() {
        expectFail(payload(scene = "aurora"), "不支持的场景")
        expectFail(payload(titleFont = "weird-font"), "不支持的标题字体")
        // 白名单内每一项都应通过（防止白名单与模型脱节）
        EpubLoadingTemplate.TITLE_FONTS.forEach { font ->
            assertTrue("白名单字体应可用：$font", decodeLoadingPayload(payload(titleFont = font)).isSuccess)
        }
        Scene.KEYS.forEach { key ->
            assertTrue("白名单场景应可用：$key", decodeLoadingPayload(payload(scene = key)).isSuccess)
        }
    }

    @Test
    fun `字号与插画缩放走闭区间边界`() {
        assertTrue("下限 18 应通过", decodeLoadingPayload(payload(titleSize = 18.0)).isSuccess)
        assertTrue("上限 36 应通过", decodeLoadingPayload(payload(titleSize = 36.0)).isSuccess)
        expectFail(payload(titleSize = 17.9), "标题字号越界")
        expectFail(payload(titleSize = 36.1), "标题字号越界")

        assertTrue("缩放下限 0.7 应通过", decodeLoadingPayload(payload(artScale = 0.7)).isSuccess)
        assertTrue("缩放上限 1.2 应通过", decodeLoadingPayload(payload(artScale = 1.2)).isSuccess)
        expectFail(payload(artScale = 0.69), "插画缩放越界")
        expectFail(payload(artScale = 1.21), "插画缩放越界")
    }

    @Test
    fun `色值必须是合法六位十六进制`() {
        expectFail(payload(dayColor = "#FFF"), "day.background")
        expectFail(payload(dayColor = "#GG0000"), "day.background")
        expectFail(payload(includeDay = false), "缺少 day 配色")
    }

    @Test
    fun `文案字段长度上限`() {
        expectFail(payload(name = ""), "模板名不得为空")
        expectFail(payload(name = "x".repeat(EpubLoadingTemplate.MAX_NAME_LENGTH + 1)), "模板名过长")
        expectFail(payload(description = "x".repeat(EpubLoadingTemplate.MAX_DESCRIPTION_LENGTH + 1)), "说明 过长")
        expectFail(payload(eyebrow = "x".repeat(EpubLoadingTemplate.MAX_EYEBROW_LENGTH + 1)), "题记 过长")
        expectFail(payload(caption = "x".repeat(EpubLoadingTemplate.MAX_CAPTION_LENGTH + 1)), "副文案 过长")
    }

    @Test
    fun `编码解码往返全字段等值`() {
        val original = EpubLoadingTemplate.BUILT_IN[1]
        val json = encodeLoadingPayload(original, includeId = false)
        assertTrue("载荷里不得带 id（防冒充内置）", !json.contains("\"id\""))
        val decoded = decodeLoadingPayload(json).getOrNull()
        assertNotNull(decoded)
        assertEquals(original.name, decoded!!.name)
        assertEquals(original.description, decoded.description)
        assertEquals(original.scene, decoded.scene)
        assertEquals(original.eyebrow, decoded.eyebrow)
        assertEquals(original.caption, decoded.caption)
        assertEquals(original.titleFont, decoded.titleFont)
        assertEquals(original.titleSize, decoded.titleSize, 0.001f)
        assertEquals(original.artScale, decoded.artScale, 0.001f)
        assertEquals(original.day, decoded.day)
        assertEquals(original.night, decoded.night)
    }

    @Test
    fun `库存解析丢弃坏数据与冒充内置的条目`() {
        assertTrue("空文本 ⇒ 空库", parseLoadingLibrary(null).isEmpty())
        assertTrue("坏 JSON ⇒ 空库（不抛，管理页必须能打开）", parseLoadingLibrary("{oops").isEmpty())

        val good = EpubLoadingTemplate.LOCAL_PREFIX + "abc"
        val item = JSONObject(encodeLoadingPayload(EpubLoadingTemplate.BUILT_IN[0], includeId = true))
            .put("id", good)
        val faked = JSONObject(encodeLoadingPayload(EpubLoadingTemplate.BUILT_IN[0], includeId = true))
            .put("id", EpubLoadingTemplate.BUILT_IN_PREFIX + "ink")
        val library = parseLoadingLibrary("[$item,$faked]")
        assertEquals("只应保留合法的自定义条目", 1, library.size)
        assertEquals(good, library[0].id)

        val roundTrip = parseLoadingLibrary(encodeLoadingLibrary(library))
        assertEquals("库存往返不丢字段", library, roundTrip)
    }

    @Test
    fun `内置集契约与默认套`() {
        assertEquals("内置套数须与场景数一致（防死场景）", Scene.entries.size, EpubLoadingTemplate.BUILT_IN.size)
        assertEquals("默认套 = 第一套", EpubLoadingTemplate.BUILT_IN.first(), EpubLoadingTemplate.DEFAULT)
        EpubLoadingTemplate.BUILT_IN.forEach { template ->
            assertTrue("内置套 id 前缀", template.builtIn)
            assertEquals("内置套 id 须与 scene 对应", EpubLoadingTemplate.BUILT_IN_PREFIX + template.scene.key, template.id)
            assertTrue("内置套名不得为空", template.name.isNotBlank())
            assertEquals(
                "内置套须在模型白名单内（否则导入导出往返会失败）",
                true, decodeLoadingPayload(encodeLoadingPayload(template, includeId = false)).isSuccess
            )
        }
    }

    @Test
    fun `纯函数 luminance 与色值解析`() {
        assertTrue("白色亮度 > 0.5（系统栏取深色图标）", luminance(0xFFFFFFFF.toInt()) > Palette.LUMINANCE_THRESHOLD)
        assertTrue("黑色亮度 < 0.5", luminance(0xFF000000.toInt()) < Palette.LUMINANCE_THRESHOLD)
        assertEquals("黑白端点亮度", 1f, luminance(0xFFFFFFFF.toInt()), 0.01f)
        assertEquals(0f, luminance(0xFF000000.toInt()), 0.01f)

        assertEquals("解析应带不透明 α", 0xFFF6F1E6.toInt(), parseHexColor("#F6F1E6"))
        assertEquals("大小写等价", parseHexColor("#f6f1e6"), parseHexColor("#F6F1E6"))
        assertEquals("无 # 也接受", parseHexColor("F6F1E6"), parseHexColor("#F6F1E6"))
        assertNull("三位缩写非法", parseHexColor("#FFF"))
        assertNull("非十六进制非法", parseHexColor("#GG0000"))
        assertNull("空值非法", parseHexColor(null))

        assertEquals("#F6F1E6", argbToHex(0xFFF6F1E6.toInt()))
        assertEquals("#101216", argbToHex(0xFF101216.toInt()))
    }

    @Test
    fun `昼夜取套与明暗图标判定`() {
        val template = EpubLoadingTemplate.BUILT_IN[0]
        assertEquals("night=true 取夜套", template.night, template.palette(true))
        assertEquals("night=false 取日套", template.day, template.palette(false))

        val light = Palette(0xFFFFFFFF.toInt(), 0xFFFFFFFF.toInt(), 0, 0, 0, 0)
        val dark = Palette(0xFF000000.toInt(), 0xFF000000.toInt(), 0, 0, 0, 0)
        assertTrue("亮底 ⇒ 系统栏取深色图标", light.darkStatusIcons && light.darkNavigationIcons)
        assertTrue("暗底 ⇒ 系统栏取浅色图标", !dark.darkStatusIcons && !dark.darkNavigationIcons)
    }
}
