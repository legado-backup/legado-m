package io.legado.app.model

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅源巡检**配置面**接线不变量（源码文本断言；测试缝不可行为化 ⇒ 见 `empty_test_allowlist.json` 的 exception 登记）。
 *
 * 为什么只能结构断言：`CheckRssSource` 的配置读写在对象初始化时即访问 `CacheManager`（依赖 `appCtx`），
 * 纯 JVM 触发它有污染整个测试 JVM 的风险（NEW-14 同族）⇒ 不能从单测直接读该对象；本文件守护其**形态契约**，
 * 行为侧由 `RssCheckFailureUnificationTest` 的纯函数（分组名/维度态）覆盖。
 */
class RssCheckConfigWiringTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun dedupDefaultsToOnSoDuplicateMarkerCanActuallyLand() {
        // NEW-28：去重标注（NEW-27 的「重复源」标记）此前因整条巡检链路无入口而从未生效；
        // 接线时默认值必须是 true，否则「标记重复源」这条订阅源侧独有收益仍然是空的。
        val src = code("src/main/java/io/legado/app/model/CheckRssSource.kt")
        val dedupLine = src.lines().first { it.contains("var enableDedup") }
        assertTrue(
            "去重默认须为开启（否则去重标记永不产生）：$dedupLine",
            dedupLine.contains("?: true")
        )
        assertFalse("不得残留「默认关闭」的旧注释", src.contains("// 去重设置（默认关闭）"))
    }

    @Test
    fun deadKeywordFieldIsRemoved() {
        // `CheckRssSource.keyword` 全仓零读取（服务侧搜索关键词是硬编码）⇒ 死字段，已删。
        val src = code("src/main/java/io/legado/app/model/CheckRssSource.kt")
        assertFalse("死字段 keyword 不得回潮", src.contains("var keyword"))
    }

    @Test
    fun serviceChannelStillExposesStartStopResume() {
        // UI 接线依赖的三条服务通道须保持（start 传选中源 id 列表、stop/resume 供通知动作）
        val src = code("src/main/java/io/legado/app/model/CheckRssSource.kt")
        assertTrue("须有 start 通道", src.contains("fun start(context: Context, sources: List<RssSource>)"))
        assertTrue("须写入选中 id 列表", src.contains("\"checkRssSourceSelectedIds\""))
        assertTrue("须有 stop 通道", src.contains("fun stop(context: Context)"))
        assertTrue("须有 resume 通道", src.contains("fun resume(context: Context)"))
    }
}
