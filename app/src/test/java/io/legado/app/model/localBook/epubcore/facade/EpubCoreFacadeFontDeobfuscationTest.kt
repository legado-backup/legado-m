package io.legado.app.model.localBook.epubcore.facade

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 内嵌字体去混淆的**接线契约**（epub-md-rich-rendering 阶段 1.3 配对）。
 *
 * 为什么单列接线测试（而非只测算法）：去混淆器本身正确、但**没被装上**时，症状与"完全没实现"
 * 一模一样（字体仍乱码/回退），而两者修复成本天差地别 ⇒ 必须把"装上了、且装的是同一实例"钉死。
 *
 * 三条不变量：
 * ①**唯一装配点**：`EpubCoreFacade.open` 传给门面的 archive 必须是 `wrap(...)` 的产物
 *   （否则去混淆器成为无消费者的死代码）；
 * ②**顺序**：`wrap` 必须在 `EpubPackageParser().parse(...)` **之后**——密钥由全书标识派生，
 *   提前包装拿不到 `identifier` ⇒ 一律降级为"不包装"（静默失效）；
 * ③**标识来源**：必须是 `pkg.metadata.identifier`（出版物唯一标识），不得改用书名等无关字段。
 */
class EpubCoreFacadeFontDeobfuscationTest {

    private val facade = "model/localBook/epubcore/facade/EpubCoreFacade.kt"

    private fun text(): String = SourceFileProbe.sourceText(facade)

    @Test
    fun `门面装配的 archive 必须是去混淆器的产物`() {
        val s = text()
        assertTrue(
            "EpubCoreFacade 必须把 wrap(...) 的产物装配进门面（否则去混淆器是无消费者死代码）",
            s.contains("archive = EpubFontDeobfuscatingArchive.wrap(archive, pkg.metadata.identifier)")
        )
        assertFalse(
            "不得在门面构造点直通未包装的 archive（等价于把去混淆结果丢弃）",
            // ⚠️ 不能粗匹配 "archive = archive,"：`EpubTypefaceResolver(context=…, archive=archive, …)`
            // 是**消费者读取已包装字段**的正常写法，粗匹配会把它误判成违规。
            Regex("EpubCoreFacade\\(\\s*archive = archive,").containsMatchIn(s)
        )
    }

    @Test
    fun `包装必须晚于包解析（密钥依赖全书标识）`() {
        val s = text()
        val parse = s.indexOf("EpubPackageParser().parse(archive)")
        val wrap = s.indexOf("EpubFontDeobfuscatingArchive.wrap(")
        assertTrue("包解析调用必须仍在（wrap 依赖其产物）", parse > 0)
        assertTrue("wrap 调用必须存在", wrap > 0)
        assertTrue(
            "wrap 必须晚于包解析：密钥 = f(identifier)，提前包装取不到标识会静默退化为不包装",
            wrap > parse
        )
    }

    @Test
    fun `密钥标识必须取出版物唯一标识`() {
        val s = text()
        assertTrue(
            "必须传 pkg.metadata.identifier（不得用 title 等无关字段冒充标识）",
            s.contains("pkg.metadata.identifier")
        )
        assertTrue(
            "必须导入去混淆器（同包全限定写法不存在 ⇒ 该 import 是装配在位的必要条件）",
            s.contains("import io.legado.app.model.localBook.epubcore.font.EpubFontDeobfuscatingArchive")
        )
    }

    @Test
    fun `装配点唯一（避免出现绕过去混淆的第二条打开路径）`() {
        val s = text()
        val wraps = Regex("EpubFontDeobfuscatingArchive\\.wrap\\(").findAll(s).count()
        assertEquals("去混淆装配应只有一个入口（多点装配必有遗漏）", 1, wraps)
        val opens = Regex("fun open\\(").findAll(s).count()
        assertEquals("门面打开入口应唯一（多入口会绕过装配）", 1, opens)
    }
}