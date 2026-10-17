package io.legado.app.help.config

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 首屏加载模板**库/选择语义纯内核**单测（reader-theme-family 3.12 配对）。
 *
 * 只测纯内核（`selectLoadingTemplate` / `saveLoadingTemplate` / `deleteLoadingTemplate` /
 * `applyLoadingTemplateId` / `upsertLoadingTemplate` / `newLoadingTemplateId`）——
 * Context 侧只是"读偏好 → 调内核 → 写偏好"的薄壳，**内核正确即语义正确**。
 *
 * 关注点（都是"用户点了没反应/点了却出错"的高发面）：
 * ①选择键为空/失效 ⇒ **回落默认**（不白屏）；②内置**不可删**、不可被导入载荷冒充；
 * ③上限（条数 32 / 体积 48KB）**有中文失败原因**；④编辑不存在的模板 ⇒ 失败而非静默新增；
 * ⑤覆盖不挪位、新增追加尾部（列表顺序是用户可感知的）。
 */
class EpubLoadingTemplateManagerTest {

    private fun legalJson(name: String = "自制套"): String = JSONObject().apply {
        put("type", EpubLoadingTemplate.DOC_TYPE)
        put("version", EpubLoadingTemplate.DOC_VERSION)
        put("name", name)
        put("description", "")
        put("scene", Scene.ORBIT.key)
        put("eyebrow", "")
        put("caption", "")
        put("titleFont", "serif")
        put("titleSize", 28.0)
        put("artScale", 1.0)
        listOf("day", "night").forEach { which ->
            put(which, JSONObject().apply {
                listOf("background", "horizon", "ink", "muted", "accent", "glow")
                    .forEach { put(it, "#223344") }
            })
        }
    }.toString()

    @Test
    fun `选择键为空或失效时回落默认套`() {
        val library = emptyList<EpubLoadingTemplate>()
        assertEquals("空键 ⇒ 默认", EpubLoadingTemplate.DEFAULT, selectLoadingTemplate(library, ""))
        assertEquals("null ⇒ 默认", EpubLoadingTemplate.DEFAULT, selectLoadingTemplate(library, null))
        assertEquals("未知名 ⇒ 默认", EpubLoadingTemplate.DEFAULT, selectLoadingTemplate(library, "local.gone"))
    }

    @Test
    fun `选择键命中内置或自定义时分别返回对应套`() {
        val builtIn = EpubLoadingTemplate.BUILT_IN[2]
        assertEquals(builtIn, selectLoadingTemplate(emptyList(), builtIn.id))

        val custom = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "one")
        assertEquals(custom, selectLoadingTemplate(listOf(custom), custom.id))
    }

    @Test
    fun `新增保存分配 local 前缀 id 并追加到库尾`() {
        val first = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "a")
        val result = saveLoadingTemplate(listOf(first), legalJson(), null, EpubLoadingTemplate.LOCAL_PREFIX + "new")
        val (library, template) = result.getOrThrow()
        assertEquals("库长度 +1", 2, library.size)
        assertEquals("新增排在尾部", template, library.last())
        assertTrue("新 id 必须是 local 前缀（防冒充内置）", template.id.startsWith(EpubLoadingTemplate.LOCAL_PREFIX))
        assertFalse("新模板不得被判为内置", template.builtIn)
    }

    @Test
    fun `编辑已有项覆盖且不挪位不增条数`() {
        val a = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "a")
        val b = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "b")
        val result = saveLoadingTemplate(listOf(a, b), legalJson(name = "改名后"), a.id, "ignored")
        val (library, template) = result.getOrThrow()
        assertEquals("条数不变", 2, library.size)
        assertEquals("位置不变（仍在首位）", a.id, library.first().id)
        assertEquals("内容已更新", "改名后", template.name)
        assertEquals("改名后", library.first().name)
    }

    @Test
    fun `编辑不存在的模板必须失败而非静默新增`() {
        val result = saveLoadingTemplate(
            emptyList(), legalJson(), EpubLoadingTemplate.LOCAL_PREFIX + "ghost", "x"
        )
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message.orEmpty().contains("不在自定义库中"))
    }

    @Test
    fun `自定义条数上限为 32`() {
        val full = (1..EpubLoadingTemplateManager.MAX_TEMPLATES)
            .map { customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "t$it") }
        val result = saveLoadingTemplate(full, legalJson(), null, EpubLoadingTemplate.LOCAL_PREFIX + "more")
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message.orEmpty().contains("最多保存"))
    }

    @Test
    fun `导入体积上限为 48KB 且先于解析生效`() {
        val padded = legalJson() + " ".repeat(EpubLoadingTemplateManager.MAX_IMPORT_BYTES)
        val result = saveLoadingTemplate(emptyList(), padded, null, EpubLoadingTemplate.LOCAL_PREFIX + "big")
        assertTrue(result.isFailure)
        assertTrue(
            "应报体积过大（而不是解析错误）：${result.exceptionOrNull()?.message}",
            result.exceptionOrNull()?.message.orEmpty().contains("模板文件过大")
        )
    }

    @Test
    fun `删除：内置不可删 不存在报错 存在则移除`() {
        val builtInId = EpubLoadingTemplate.BUILT_IN[0].id
        assertTrue("内置不可删", deleteLoadingTemplate(emptyList(), builtInId).isFailure)
        val custom = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "x")
        assertTrue("不在库中应报错", deleteLoadingTemplate(listOf(custom), EpubLoadingTemplate.LOCAL_PREFIX + "y").isFailure)
        val remaining = deleteLoadingTemplate(listOf(custom), custom.id).getOrThrow()
        assertTrue("删除后库为空", remaining.isEmpty())
    }

    @Test
    fun `应用：id 必须存在`() {
        val custom = customTemplate(EpubLoadingTemplate.LOCAL_PREFIX + "applied")
        val known = EpubLoadingTemplate.BUILT_IN + custom
        assertTrue("内置可应用", applyLoadingTemplateId(known, EpubLoadingTemplate.BUILT_IN[1].id).isSuccess)
        assertTrue("自定义可应用", applyLoadingTemplateId(known, custom.id).isSuccess)
        assertTrue("不存在必须失败", applyLoadingTemplateId(known, EpubLoadingTemplate.LOCAL_PREFIX + "no").isFailure)
    }

    @Test
    fun `新 id 唯一且前缀固定`() {
        val id1 = newLoadingTemplateId()
        val id2 = newLoadingTemplateId()
        assertTrue(id1.startsWith(EpubLoadingTemplate.LOCAL_PREFIX))
        assertTrue("两次生成不得相同", id1 != id2)
    }

    private fun customTemplate(id: String): EpubLoadingTemplate =
        EpubLoadingTemplate(
            id = id, name = "自制", description = "", scene = Scene.BLOOM,
            eyebrow = "", caption = "", titleFont = "serif", titleSize = 28f, artScale = 1f,
            day = EpubLoadingTemplate.BUILT_IN[0].day, night = EpubLoadingTemplate.BUILT_IN[0].night
        )
}
