package io.legado.app.model.localBook.epubcore.template

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 与 archive 的**双向互兼容**契约（2026-10-14，用户目标扩展）：
 * 「我们的主题导出后可以在 archive 导入」—— 导入导出无压力，行为模式尽可能一样。
 *
 * archive 侧权威判据（源码：`temp/forks-comparison/Rimchars_legado/app/src/main/java/io/legado/app/
 * model/localBook/epubcore/template/EpubReaderTemplate.kt`）：
 * - 常量：`SCHEMA_VERSION=1` / `SCROLL_SCHEMA_VERSION=2` / `TYPE_PAGED="paged"` / `TYPE_SCROLL="scroll"`；
 * - 解析（`fromJsonObject`）：`schemaVersion` **必须是 JSON 数字**；其余字段必须是 **JSON 字符串**
 *   （未给出的可选字段回落默认值，但 `id`/`name` **必填**）；解析后立刻 `validate()`，不通过**整包导入失败**；
 * - 校验（`validate`）：version ∈ 1..2；type ∈ {paged,scroll}；scroll ⇒ version ≥ 2；按类型要求对应
 *   HTML 非空；`id`/`name` 非空；
 * - `id` 以 `builtin.` 开头时 archive 侧**自动改存为副本**（`copyReaderTemplate`）⇒ 我方导出内置 id 不会撞库。
 *
 * 本测试把上述规则**逐条落成断言**：任一条漂移（新增字段/改常量/放宽必填/改键名）都会在**提交期**
 * 被拦下，而不是等真机导入到 archive 失败才发现。
 */
class ReaderTemplateArchiveInteropTest {

    /** archive 侧 `EpubReaderTemplate` 的字段全集：键名不得漂移（少键 ⇒ 抛异常；多键 ⇒ 语义不明） */
    private val archiveFields = setOf(
        "schemaVersion", "id", "name", "description",
        "firstPageHtml", "otherPageHtml", "css", "javascript", "type", "scrollHtml"
    )

    private val builtinDir = File("src/main/assets/reader")

    private fun builtinJsonFiles(): List<File> =
        builtinDir.listFiles { f -> f.isDirectory && File(f, "readerTemplate.json").isFile }
            .orEmpty().map { File(it, "readerTemplate.json") }.sortedBy { it.parentFile.name }

    @Test
    fun `内置模板满足 archive 侧解析与校验规则`() {
        val files = builtinJsonFiles()
        assertTrue("未找到内置模板（路径=${builtinDir.absolutePath}）", files.size >= 11)
        files.forEach { file ->
            val json: JsonObject = JsonParser.parseString(file.readText()).asJsonObject
            val where = file.parentFile.name
            assertTrue(
                "$where: 出现 archive 不认识的字段：${json.keySet() - archiveFields}",
                (json.keySet() - archiveFields).isEmpty()
            )
            assertTrue("$where: 缺少必填字段 id/name", json.has("id") && json.has("name"))
            val version = json.get("schemaVersion")
            assertNotNull("$where: 缺少 schemaVersion", version)
            assertTrue(
                "$where: schemaVersion 必须是 JSON 数字（archive 的 readVersion 要求 isNumber）",
                version.isJsonPrimitive && version.asJsonPrimitive.isNumber
            )
            assertTrue("$where: schemaVersion 必须 ∈ 1..2", version.asInt in 1..2)
            archiveFields.filter { it != "schemaVersion" }.forEach { name ->
                val element = json.get(name) ?: return@forEach
                assertTrue("$where: $name 必须是 JSON 字符串", element.isJsonPrimitive && element.asJsonPrimitive.isString)
            }
            val type = json.get("type")?.asString.orEmpty()
            assertTrue("$where: type 必须是 paged/scroll", type == "paged" || type == "scroll")
            if (type == "scroll") {
                assertTrue("$where: 滚动模板需要格式版本 2", version.asInt >= 2)
                assertTrue("$where: 缺 scrollHtml", json.get("scrollHtml")?.asString.orEmpty().isNotBlank())
            } else {
                assertTrue("$where: 缺 firstPageHtml", json.get("firstPageHtml")?.asString.orEmpty().isNotBlank())
                assertTrue("$where: 缺 otherPageHtml", json.get("otherPageHtml")?.asString.orEmpty().isNotBlank())
            }
        }
    }

    @Test
    fun `格式契约常量与版本域和 archive 同源`() {
        assertEquals(1, EpubReaderTemplate.SCHEMA_VERSION)
        assertEquals(2, EpubReaderTemplate.SCROLL_SCHEMA_VERSION)
        assertEquals("paged", EpubReaderTemplate.TYPE_PAGED)
        assertEquals("scroll", EpubReaderTemplate.TYPE_SCROLL)
        // 版本上界与类型域：archive 侧 `schemaVersion !in 1..2` / 非法 type 一律拒绝
        val base = EpubReaderTemplate(
            schemaVersion = 3, id = "user.x", name = "x",
            firstPageHtml = "<div></div>", otherPageHtml = "<div></div>"
        )
        assertTrue("版本 3 必须被拒", base.validate().any { it.contains("不支持的模板版本") })
        val badType = base.copy(schemaVersion = 1, type = "x")
        assertTrue("非法 type 必须被拒", badType.validate().any { it.contains("不支持的模板类型") })
        val scrollV1 = base.copy(schemaVersion = 1, type = EpubReaderTemplate.TYPE_SCROLL, scrollHtml = "<div></div>")
        assertTrue("v1 滚动模板必须被拒（与 archive 同判）", scrollV1.validate().any { it.contains("滚动模板需要格式版本 2") })
    }

    @Test
    fun `archive 形态模板（v1 paged 与 v1 scroll）可被我方导入`() {
        // archive 导出物的真实形态：v1 paged，以及 **v1 + scroll**（archive 内置 `builtin.doraemon_scroll` 即此形态）。
        // 我方导入必须照单全收（v1 → v2 自动升级），否则"archive 主题导入我们"这条腿是断的。
        val paged = """
            {"schemaVersion":1,"type":"paged","id":"builtin.some","name":"示例",
             "description":"","firstPageHtml":"<div data-reader-flow=\"body\"></div>",
             "otherPageHtml":"<div data-reader-flow=\"body\"></div>","css":"body{}","javascript":"","scrollHtml":""}
        """.trimIndent()
        val pagedResult = ReaderTemplateImportMapper.importTemplateJson(paged)
        assertTrue("archive v1 paged 必须可导入：${pagedResult.summary()}", pagedResult.succeeded)
        assertTrue("内置 id 须改名以免与内置冲突", pagedResult.template!!.id.startsWith("user."))
        assertEquals("须升级到当前 schema", EpubReaderTemplate.SCROLL_SCHEMA_VERSION, pagedResult.template!!.schemaVersion)

        val scroll = """
            {"schemaVersion":1,"type":"scroll","id":"builtin.scrollish","name":"示例滚动",
             "description":"","firstPageHtml":"","otherPageHtml":"","css":"body{}","javascript":"",
             "scrollHtml":"<div data-reader-flow=\"body\"></div>"}
        """.trimIndent()
        val scrollResult = ReaderTemplateImportMapper.importTemplateJson(scroll)
        assertTrue("archive v1 滚动模板必须可导入（自动升级）：${scrollResult.summary()}", scrollResult.succeeded)
        assertEquals("scroll", scrollResult.template!!.type)
        assertTrue("升级后必须通过结构校验", scrollResult.template!!.validate().isEmpty())
    }

    @Test
    fun `导出往返保真（id_type_html_css_js_scroll 全字段）`() {
        // 导出 →（按 archive 规则解析 → 再导入我方）的往返：字段一个都不能丢，否则"互导入无压力"是假的。
        val source = EpubReaderTemplate(
            schemaVersion = EpubReaderTemplate.SCROLL_SCHEMA_VERSION,
            id = "user.roundtrip", name = "往返", description = "d",
            firstPageHtml = "<div data-reader-flow=\"body\"></div>",
            otherPageHtml = "<div data-reader-flow=\"body\"></div>",
            css = "body{color:#333}",
            javascript = "readerTemplate.on('beforeLayout',function(){});",
            type = EpubReaderTemplate.TYPE_SCROLL,
            scrollHtml = "<div data-reader-flow=\"body\"></div>"
        )
        val exported = source.toJson()
        // archive 侧会先要求"字段名/类型/常量"全部合规（由本类的第一条测试覆盖），这里验证内容无损：
        val reparsed = ReaderTemplateImportMapper.importTemplateJson(exported, remapBuiltinIds = false)
        assertTrue("导出物必须可被解析：${reparsed.summary()}", reparsed.succeeded)
        val back = reparsed.template!!
        assertEquals("id", source.id, back.id)
        assertEquals("name", source.name, back.name)
        assertEquals("description", source.description, back.description)
        assertEquals("type", source.type, back.type)
        assertEquals("css 必须逐字保留", source.css, back.css)
        assertEquals("javascript 必须逐字保留（主题动效/语义全靠它）", source.javascript, back.javascript)
        assertEquals("scrollHtml 必须逐字保留", source.scrollHtml, back.scrollHtml)
        assertEquals("版本须为当前 schema", EpubReaderTemplate.SCROLL_SCHEMA_VERSION, back.schemaVersion)
    }
}
