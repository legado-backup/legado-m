package io.legado.app.testkit

import io.legado.app.help.md.MdDocumentBuilder
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 单测夹具约定（epub-md-rich-rendering 补充任务 **S13** 配对）。
 *
 * 为什么需要：此前各用例把 md / 模板 / xhtml 样本**内联成字符串**（`MdDocumentBuilderTest` /
 * `ReaderTemplateImportMapperTest` 等），同一样本在多个用例里被复制并各自漂移；而"把样本挪进
 * `fixtures/`"这类改造**不会让任何用例变红**（漏了也没人发现）⇒ 必须有本用例把
 * 「目录齐备 + **真的被解析器消费**」钉住，否则约定层形同虚设（本项目铁证：只写文档的约束一律失效）。
 */
class FixturesConventionTest {

    /** 夹具一律走**测试类路径**（`app/src/test/resources/`），不用相对工作目录（后者随运行方式变化）。 */
    private fun fixture(path: String): String =
        javaClass.classLoader!!.getResource(path)?.readText()
            ?: throw AssertionError("夹具缺失：$path（应位于 app/src/test/resources/$path）")

    @Test
    fun `三类夹具齐备且非空`() {
        listOf(
            "fixtures/md/basic.md",
            "fixtures/template/minimal.json",
            "fixtures/epub/spine-fragment.xhtml"
        ).forEach { assertTrue("$it 不得为空", fixture(it).isNotBlank()) }
    }

    @Test
    fun `md 夹具可被真实解析器复用而非仅存在`() {
        // 仅断言"文件存在"是空真：必须真的喂给生产解析器并检查结构产物
        val built = MdDocumentBuilder.build(fixture("fixtures/md/basic.md"))
        assertTrue("GFM 表格须渲染为 table", built.html.contains("<table>"))
        assertTrue("删除线须渲染为 del", built.html.contains("<del>"))
        assertTrue("标题须进入纯文本（供朗读/气泡同源）", built.plainText.contains("夹具基准标题"))
    }

    @Test
    fun `模板夹具满足模板契约最小结构`() {
        val json = fixture("fixtures/template/minimal.json")
        listOf("\"schemaVersion\"", "\"type\"", "\"id\"", "\"firstPageHtml\"", "\"otherPageHtml\"")
            .forEach { assertTrue("模板最小结构缺少 $it", json.contains(it)) }
        assertTrue("必须带正文槽契约 data-reader-flow", json.contains("data-reader-flow"))
    }

    @Test
    fun `epub 片段夹具为可解析的 XHTML 骨架`() {
        val xhtml = fixture("fixtures/epub/spine-fragment.xhtml")
        assertTrue("须声明 XHTML 命名空间", xhtml.contains("http://www.w3.org/1999/xhtml"))
        assertTrue("须有 body 开合", xhtml.contains("<body>") && xhtml.contains("</body>"))
        assertTrue("须含可被解析的正文段落", xhtml.contains("<p>"))
    }
}