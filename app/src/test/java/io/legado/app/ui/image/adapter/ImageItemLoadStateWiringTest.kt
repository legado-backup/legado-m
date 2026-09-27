package io.legado.app.ui.image.adapter

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W7 8.3（REQ-29）：画布**逐项**加载态呈现的接线不变量。
 *
 * 为什么值得测（实证根因）：此前加载期间 PhotoView 无内容、item 底色为黑，
 * 用户看到纯黑**无法区分「正在加载」与「已经坏掉」**（静默黑屏）；且降级链耗尽后
 * 只有一条 footer 级提示 + 「切换网页模式」弹窗，**没有逐项原因与原地重试**。
 *
 * 这三件事（占位 / 逐项原因 / 原地重试）**都不会**造成编译失败，只能靠断言锁住；
 * 同时断言「未新增状态机」（tasks §8 8.3 明确约束）。
 */
class ImageItemLoadStateWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val adapter by lazy {
        read("src/main/java/io/legado/app/ui/image/adapter/ImageCanvasAdapter.kt")
    }
    private val layout by lazy { read("src/main/res/layout/item_image_canvas.xml") }

    @Test
    fun layoutProvidesItemScopedLoadingAndErrorViews() {
        assertTrue("逐项占位视图缺失（静默黑屏会复现）", layout.contains("android:id=\"@+id/pb_item_loading\""))
        assertTrue("逐项失败原因视图缺失", layout.contains("android:id=\"@+id/tv_item_error\""))
        assertTrue("逐项重试按钮缺失", layout.contains("android:id=\"@+id/btn_item_retry\""))
        assertTrue("逐项失败容器缺失", layout.contains("android:id=\"@+id/layout_item_error\""))
    }

    @Test
    fun bindResetsItemScopedState() {
        val bindAt = adapter.indexOf("fun bind(item: ImageCanvasItem.ImageItem, position: Int)")
        assertTrue("未找到 bind", bindAt > 0)
        val block = adapter.substring(bindAt, adapter.indexOf("val sourceOrigin = resolveSourceOrigin()", bindAt))
        assertTrue("bind 须隐藏上一轮复用残留的逐项失败层", block.contains("hideItemError()"))
        assertTrue("bind 须显示逐项占位（无静默黑屏）", block.contains("showItemLoading()"))
    }

    @Test
    fun successPathHidesItemPlaceholder() {
        // 统一呈现轨成功后必须收起占位
        val showAt = adapter.indexOf("private fun showSsivImage(")
        val showBlock = adapter.substring(showAt, adapter.indexOf("private fun loadIntoPhotoView(", showAt))
        assertTrue("SSIV 呈现成功后须收起逐项占位", showBlock.contains("hideItemLoading()"))
    }

    @Test
    fun terminalFailureShowsItemErrorAndKeepsRetryReachable() {
        // 降级链的两条 level-4 出口都必须落到「逐项原因 + 原地重试」
        val occurrences = Regex("""hideItemLoading\(\)\s*\n\s*showItemError\(e\)""").findAll(adapter).count()
        assertEquals("降级链两条 level-4 出口都须呈现逐项失败（实得 $occurrences）", 2, occurrences)
        assertTrue(
            "逐项失败文案须复用 footer 同口径分类（不得直接抛 Throwable.message）",
            adapter.contains("val category = classifyError(e ?: Throwable(\"unknown\"))")
        )
        assertTrue(
            "逐项重试按钮须有接线（此前无任何逐项重试入口）",
            adapter.contains("binding.btnItemRetry.setOnClickListener { retryFromScratch() }")
        )
        assertTrue(
            "逐项失败文案色须走语义色单源（禁止页内写死色值）",
            adapter.contains("binding.tvItemError.setTextColor(AppSemanticColors.Danger.toArgb())")
        )
    }

    @Test
    fun itemRetryRestartsFallbackChainAndClearsPreheatMark() {
        val retryAt = adapter.indexOf("private fun retryFromScratch()")
        assertTrue("未找到逐项重试实现", retryAt > 0)
        val block = adapter.substring(retryAt, minOf(adapter.length, retryAt + 1800))
        assertTrue("重试须把降级链计数器归零（否则直接从第 4 级起步）", block.contains("retryCount = 0"))
        assertTrue(
            "重试须清除该 URL 的预热标记，让第 3 级（WebView 预热）重新可用",
            block.contains("preheatedUrlHashes.remove(url.hashCode())")
        )
        assertTrue("重试须重新发起加载", block.contains("loadImage(url, opts, currentPosition)"))
    }

    @Test
    fun noNewStateMachineIntroduced() {
        // tasks §8 8.3 明确「不新增状态机」：5 态 sealed class 保持原样
        assertTrue(
            "LoadState 须仍是 IDLE/LOADING/SUCCESS/ERROR/NO_MORE 五态",
            adapter.contains("object NO_MORE : LoadState()")
        )
        assertEquals(
            "逐项呈现不得引入新的 sealed class 状态机",
            1,
            Regex("""sealed class \w+""").findAll(adapter).count()
        )
        assertTrue(
            "逐项占位视图须初始隐藏（否则会在每项常驻显示）",
            Regex("""pb_item_loading[\s\S]{0,240}?android:visibility="gone"""").containsMatchIn(layout)
        )
    }
}
