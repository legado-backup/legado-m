package io.legado.app.base

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `composeShell` 消费页的**单源装配不变量**（CA′ 1.2 收口，JVM 可跑）。
 *
 * 判据（tasks §1.2 验证标准）：「3 页 B→A 归一后**断言不再出现 `composeShell` 之外的手写
 * ComposeView 装配**」——即凡经 `composeShell(this)` 建壳的页面，挂载 Compose 内容**只能**走
 * `View.attachComposeContent` 单源，禁止再手写
 * `ComposeView(…).apply { setViewCompositionStrategy(…); setContent { … } }`。
 *
 * 反模式根源：历史每页复制三行样板，策略（`DisposeOnViewTreeLifecycleDestroyed`）与
 * `layoutParams` 分散在 N 处 ⇒ 单源变更必漏（本次即归一 3 页）。
 */
class ComposeShellSingleSourceTest {

    private fun mainJavaRoot(): File = SourceFileProbe.mainJavaRoot()

    /** 剥掉行注释与 KDoc 星号行（单源口径，见 [SourceFileProbe.stripComments]）。 */
    private fun stripped(f: File): String = SourceFileProbe.stripComments(f.readText())

    private fun consumers(): List<File> =
        mainJavaRoot().walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .filter { stripped(it).contains("composeShell(this)") }
            .toList()

    /**
     * **例外汇总（显式登记，非放宽判据）**：允许「在 View 内核内部原位承载 Compose 段落」的页面。
     *
     * 登记理由（`ui/replace/edit/ReplaceEditActivity.kt`，CE 5.2 第 7 页）：该页字段区是 **View 内核**
     * （`NoChildScrollNestedScrollView` 对 `requestChildFocus` 有特化，是键盘/焦点联动的既有口径，
     * 不得换成 Compose 滚动）；而 F64 高级组头与 F69 样本区两个 Compose 段落**语义上夹在字段之间**
     * （位置即渐进披露的分组归属），既不能上移也不能下移 ⇒ 原地 `ComposeView` 是唯一 interop 通道。
     *
     * 登记绑定条件（缺一即应删掉本条例外）：
     *  ①页面主骨架仍必须走 `attachComposeContent`（同类的单源断言）；
     *  ②`ComposeView` 构造点必须收敛到**单一工厂** `composeSlot()`，由
     *    `ReplaceEditShellMigrationTest.composeViewOnlyInSanctionedSlotFactory` 二次锁定；
     *  ③`setContent` 合成策略与旧 XML 口径一致（不自行 `setViewCompositionStrategy`）。
     */
    private val interleavedSlotExceptions = setOf(
        "io/legado/app/ui/replace/edit/ReplaceEditActivity.kt",
    )

    private fun rel(f: File): String =
        f.relativeTo(mainJavaRoot()).path.replace('\\', '/')

    @Test
    fun consumersExist() {
        val n = consumers().size
        assertTrue("composeShell 消费页数量异常（$n）——扫描根或匹配口径可能失效", n >= 25)
    }

    @Test
    fun noConsumerHandWritesComposeView() {
        val bad = consumers().filter { f ->
            val s = stripped(f)
            s.contains("ComposeView(") || s.contains("ViewCompositionStrategy")
        }.filterNot { rel(it) in interleavedSlotExceptions }
            .map { rel(it) }
        assertEquals(
            "以下 composeShell 消费页仍在手写 ComposeView 装配（应统一走 attachComposeContent 单源）：$bad",
            emptyList<String>(),
            bad
        )
    }

    /** 例外汇总不得变成「无人复核的白名单」：条目必须真实存在且确有 `ComposeView(`（否则应删除）。 */
    @Test
    fun registeredExceptionsAreStillReal() {
        interleavedSlotExceptions.forEach { rel ->
            val f = File(mainJavaRoot(), rel)
            assertTrue("例外汇总登记了不存在的页面：$rel", f.isFile)
            assertTrue("$rel 已不再手写 ComposeView ⇒ 应删除该例外登记", stripped(f).contains("ComposeView("))
            assertTrue("$rel 例外不允许绕过主骨架单源", stripped(f).contains("attachComposeContent {"))
        }
    }

    @Test
    fun normalizedThreePagesUseSingleSource() {
        val root = mainJavaRoot()
        listOf(
            "io/legado/app/ui/config/AiImageProviderEditActivity.kt",
            "io/legado/app/ui/main/ai/AiImageGalleryActivity.kt",
            "io/legado/app/ui/rss/search/RssArticleInfoActivity.kt",
        ).forEach { rel ->
            val f = File(root, rel)
            assertTrue("缺少 CA′ 1.2 归一目标页：$rel", f.isFile)
            assertTrue("$rel 必须走 attachComposeContent 单源", stripped(f).contains("attachComposeContent {"))
        }
    }
}