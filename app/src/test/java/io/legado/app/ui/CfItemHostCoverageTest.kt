package io.legado.app.ui

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 批次**范围闭合**的机检不变量（tasks §6.1 验证标准：「38 个 `item_*` 全覆盖映射」+「distinct 宿主列表」）。
 *
 * 为什么必须机检：CF 的硬禁忌是「**不得单独删除 item XML**」（Adapter 仍 inflate ⇒ 必崩），
 * 因此「哪个 item 归哪个宿主列表」必须**可核**，否则退役时机无从判断。同时它兜住两类真实风险：
 *   ①**孤儿 item**（无任何宿主 ⇒ 其实是死件，应走死件清理而非 CF）
 *   ②**映射漂移**（Adapter 改名/迁移后清单失实 ⇒ 按错误清单删 XML 即崩溃）
 *
 * 口径（实测，2026-09-24）：
 *   · 命中通道 = ①`R.layout.<item>` ②`<ItemCamel>Binding`（ViewBinding 生成类）——两者任一即算「在用」；
 *   · 扫描面 = main 源集 java 根下的全部 kt/java（**不含测试**：测试不应成为 item 存活理由）；
 *   · 「宿主」= 命中文件本身（Adapter / 直接 inflate 的 Activity/Fragment / 复用 item 的组件）。
 *
 * 依据：`docs/specs/compose-advance-continuation/tasks.md` §6.1 / `CF-宿主列表清单.md`。
 */
class CfItemHostCoverageTest {

    private fun layoutDir(): File = SourceFileProbe.layoutDir()

    private fun itemLayouts(): List<String> =
        layoutDir().listFiles()
            ?.filter { it.isFile && it.extension == "xml" && it.nameWithoutExtension.startsWith("item_") }
            ?.map { it.nameWithoutExtension }
            ?.sorted()
            ?: emptyList()

    /**
     * 只保留「可能引用 item 布局」的源文件，压小扫描面。
     * ⚠️ 必须同时保留两类：①字面 `R.layout.item_…` ②ViewBinding 生成类 `Item…Binding`
     * —— 只看字面量会**漏掉全部 Binding-only 宿主**（实测：初版即因此把候选集压到 <20 而假失败）。
     */
    private fun candidateSources(): List<Pair<String, String>> {
        val itemRef = Regex("R\\.layout\\.item_")
        val bindingRef = Regex("(?<![A-Za-z0-9_])Item[A-Za-z0-9]*Binding")
        return SourceFileProbe.mainJavaRoot().walkTopDown()
            .filter { it.isFile && (it.extension == "kt" || it.extension == "java") }
            .map { it.relativeTo(SourceFileProbe.mainJavaRoot()).path to it.readText() }
            .filter { itemRef.containsMatchIn(it.second) || bindingRef.containsMatchIn(it.second) }
            .toList()
    }

    /** `item_rss_article_1` → `ItemRssArticle1Binding`。 */
    private fun bindingName(item: String): String =
        item.split("_").filter { it.isNotEmpty() }
            .joinToString("") { it.replaceFirstChar { c -> c.uppercaseChar() } } + "Binding"

    private fun hostsOf(item: String, sources: List<Pair<String, String>>): List<String> {
        val direct = Regex("R\\.layout\\.${Regex.escape(item)}(?![A-Za-z0-9_])")
        val binding = Regex("(?<![A-Za-z0-9_])${Regex.escape(bindingName(item))}(?![A-Za-z0-9_])")
        return sources.filter { direct.containsMatchIn(it.second) || binding.containsMatchIn(it.second) }
            .map { it.first }
    }

    @Test
    fun everyItemLayoutHasAtLeastOneHost() {
        val sources = candidateSources()
        assertTrue("候选源文件异常（${sources.size}）—— 扫描根或过滤口径可能失效", sources.size >= 20)
        val items = itemLayouts()
        assertEquals("在用 item 布局数应为 36（38 − CA′ 已删 2 真死件）", 36, items.size)
        val orphans = items.filter { hostsOf(it, sources).isEmpty() }
        assertTrue(
            "以下 item 布局**无任何宿主**（属真死件，应走死件清理而非 CF）：$orphans",
            orphans.isEmpty()
        )
    }

    @Test
    fun deadItemsAreGone() {
        val items = itemLayouts().toSet()
        // CA′ 1.0 已删的两件真死件（三通道零引用）；断言它们不再存在，防「回退」或误生成
        listOf("item_cache_chapter", "item_cover").forEach { dead ->
            assertTrue("$dead 应已在 CA′ 1.0 删除（零引用真死件）", dead !in items)
        }
    }

    @Test
    fun adapterHostCountMatchesInventory() {
        val sources = candidateSources()
        val adapters = itemLayouts()
            .flatMap { hostsOf(it, sources) }
            .filter { it.contains("Adapter") }
            .toSet()
        assertEquals(
            "Adapter 宿主数应与 `CF-宿主列表清单.md` 登记的实测值一致（映射漂移即 FAIL）",
            26, adapters.size
        )
    }

    @Test
    fun lowRiskComposeListsExist() {
        // tasks §6.1：优先已有 Compose 实现的 4 个低风险列表（清单中列为 CF 首推）
        val root = SourceFileProbe.mainJavaRoot()
        listOf(
            "io/legado/app/ui/main/bookshelf/compose/BookshelfComposeList.kt",
            "io/legado/app/ui/main/bookshelf/compose/BookshelfComposeItems.kt",
            "io/legado/app/ui/main/explore/ExploreModernListScreen.kt",
            "io/legado/app/ui/main/explore/DiscoverySuiteHomeScreen.kt",
            "io/legado/app/ui/main/my/MySettingsScreen.kt",
            "io/legado/app/ui/main/ai/AiImageGalleryScreen.kt",
        ).forEach { rel ->
            assertTrue("低风险 Compose 列表实现缺失：$rel", File(root, rel).isFile)
        }
    }
}