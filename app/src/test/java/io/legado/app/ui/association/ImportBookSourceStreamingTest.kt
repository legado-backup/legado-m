package io.legado.app.ui.association

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源导入的**流式化接线**不变量（REQ-05 / AD-13）。
 *
 * 三处入口（文本 / uri 本地流 / 网络流）原各自一次性 `GSON.fromJsonArray<BookSource>`，
 * 换装后必须**三处全部**改走 `BookSourceIncrementalParser`；漏改任一处即回到「整表入内存」，
 * 且编译期完全无感（函数仍存在、签名不变）。
 */
class ImportBookSourceStreamingTest {

    private val viewModel by lazy {
        listOf(
            File("src/main/java/io/legado/app/ui/association/ImportBookSourceViewModel.kt"),
            File("../app/src/main/java/io/legado/app/ui/association/ImportBookSourceViewModel.kt"),
            File("app/src/main/java/io/legado/app/ui/association/ImportBookSourceViewModel.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun noOneShotBookSourceArrayParsingRemains() {
        assertFalse(
            "仍存在一次性整表反序列化（应为增量解析）",
            viewModel.contains("GSON.fromJsonArray<BookSource>(")
        )
    }

    @Test
    fun allThreeEntriesUseIncrementalParser() {
        val usages = Regex("BookSourceIncrementalParser").findAll(viewModel).count()
        assertTrue("三处入口均须走增量解析（实得 $usages 处，期望 ≥ 3）", usages >= 3)
        assertTrue(
            "文本分支须流式解析",
            viewModel.contains("parseBookSourcesIncrementalInto(mText.byteInputStream(), allSources)")
        )
        assertTrue(
            "uri/本地流分支须流式解析",
            viewModel.contains("parseBookSourcesIncrementalInto(inputS, allSources)")
        )
        assertTrue(
            "网络流分支须流式解析（返回 List 供并发聚合）",
            viewModel.contains("parseBookSourcesIncrementalInto(stream, list)")
        )
    }

    @Test
    fun networkBranchKeepsEmptyListErrorSemantics() {
        // 原实现：网络分支空表也抛「不是书源」（与文本/uri 分支的空表静默不同）
        assertTrue(
            "网络分支空表须保持原「不是书源」语义",
            viewModel.contains("""if (count == 0) throw NoStackTraceException("不是书源")""")
        )
    }
}