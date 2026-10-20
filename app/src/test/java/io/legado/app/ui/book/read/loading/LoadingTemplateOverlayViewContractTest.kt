package io.legado.app.ui.book.read.loading

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「文本面首屏加载模板覆盖层」契约单测（reader-theme-family 3.13 配对，2026-10-20）。
 *
 * 背景（用户诉求）：「首屏加载模板」此前**只有 EPUB 首屏**能看到；要求它像主题模式一样适配
 * **所有阅读格式**（在线/离线文本小说 + EPUB）。真机取证（`loading overlay mode=` 正式自证串）：
 * 在线/离线文本书 **0 条样本**（epub 路径根本不注入）⇒ 文本面无任何覆盖层。
 *
 * 本契约锁死四件事（均可在文本层机检，无需设备；行为侧由真机自证串覆盖）：
 *  ①布局中覆盖层存在、id 正确、**位于 `text_rich_read_view` 之后**（保证叠在文本面之上）；
 *  ②覆盖层**不吃手势**（不设 clickable/focusable），且默认 `gone`；
 *  ③**绘制失败即透明**：`onDraw` 只有一次绘制调用（`overlay.draw`），无任何其他 canvas 绘制
 *    ⇒ `draw` 返回 false 时本层什么都不画（"最弱也不比改造前差"，与 EPUB 侧同一不变量）；
 *  ④Activity 接线：`syncTextLoadingOverlay` 在 `upContent` 与 `contentLoadFinish` **各至少调用一次**。
 *
 * ⚠️【局限】`ReadBookActivity.upContent` / `LoadingTemplateOverlayView.onDraw` 是 Android 实例方法，
 * 依赖 Activity/View 宿主，纯 JVM 无法调用（与本仓既有 `OtherConfigLoadingTemplateEntryTest` 同族局限）
 * ⇒ 这里用源码文本探针锁结构事实；**真机行为**由 `logLoadingOverlayMode` 的正式自证串覆盖。
 */
class LoadingTemplateOverlayViewContractTest {

    private val layout = SourceFileProbe.layoutDir().resolve("activity_book_read.xml").readText()
    private val overlayView = SourceFileProbe.sourceText("ui/book/read/loading/LoadingTemplateOverlayView.kt")
    private val activity = SourceFileProbe.sourceText("ui/book/read/ReadBookActivity.kt")

    private val overlayId = "@+id/loading_template_overlay"
    private val textRichId = "@+id/text_rich_read_view"

    /** 提取布局里承载该 id 的整个元素块（自 `<...LoadingTemplateOverlayView` 到其 `/>`）。 */
    private fun overlayElementBlock(): String {
        val match = Regex(
            "<io\\.legado\\.app\\.ui\\.book\\.read\\.loading\\.LoadingTemplateOverlayView[\\s\\S]*?/>"
        ).find(layout)
        return match?.value ?: throw AssertionError("布局中未找到 LoadingTemplateOverlayView 元素（含 id $overlayId）")
    }

    /** 提取一个方法体（自 `signature` 后到下一个 4 空格缩进的 `}`）。 */
    private fun bodyOf(source: String, signature: String): String {
        val start = source.indexOf(signature)
        if (start < 0) throw AssertionError("未找到方法签名：$signature")
        val bodyStart = source.indexOf('{', start)
        val end = source.indexOf("\n    }", bodyStart)
        if (end < 0) throw AssertionError("未找到方法体结束：$signature")
        return source.substring(bodyStart, end)
    }

    @Test
    fun `布局覆盖层须存在且层叠在文本面之上`() {
        val block = overlayElementBlock()
        assertTrue("元素须带 id=$overlayId", block.contains("android:id=\"$overlayId\""))
        val textRichIndex = layout.indexOf(textRichId)
        val overlayIndex = layout.indexOf(overlayId)
        assertTrue("text_rich_read_view 须在布局中", textRichIndex >= 0)
        assertTrue("覆盖层须在布局中", overlayIndex >= 0)
        // 后出现的子视图绘制在上层 ⇒ 覆盖层必须排在文本面之后，否则模板会被文本页盖住（等于没生效）
        assertTrue("覆盖层必须位于 text_rich_read_view 之后（否则被文本面遮盖）", overlayIndex > textRichIndex)
    }

    @Test
    fun `覆盖层默认隐藏且不吃手势`() {
        val block = overlayElementBlock()
        assertTrue("默认须 gone（未加载时不得占屏）", block.contains("android:visibility=\"gone\""))
        assertFalse("不得设 clickable（会吃掉翻页手势）", block.contains("clickable"))
        assertFalse("不得设 focusable（会抢焦点）", block.contains("focusable"))
    }

    @Test
    fun `绘制失败即透明 全类不得有任何其他 canvas 绘制`() {
        val onDraw = bodyOf(overlayView, "override fun onDraw(canvas: Canvas)")
        // 行为事实①：本层唯一绘制入口是 overlay.draw（返回 false ⇒ 它自身没画 ⇒ 本层没画别的东西 ⇒ 透明）
        assertEquals(
            "onDraw 只能有一次绘制调用（overlay.draw）",
            1,
            Regex("overlay\\.draw\\(canvas,").findAll(onDraw).count()
        )
        assertEquals(
            "onDraw 不得出现第二次绘制调用（任何 draw(）",
            1,
            Regex("draw\\(").findAll(onDraw).count()
        )
        // 行为事实②：显式分支 —— draw 返回 false 时直接返回（不补画底色/文字）
        assertTrue(
            "须有显式回落分支 if (!drewTemplate) return",
            Regex("if \\(!drewTemplate\\) return").containsMatchIn(onDraw)
        )
        // 行为事实③：全类都不得有 canvas 绘制（否则"返回 false 即透明"不成立）
        assertEquals("全类不得出现 canvas.draw 调用", 0, Regex("canvas\\.draw").findAll(overlayView).count())
    }

    @Test
    fun `Activity 须在内容更新与加载完成两处各同步一次文本面首屏`() {
        assertTrue(
            "须定义同步点 syncTextLoadingOverlay",
            Regex("private fun syncTextLoadingOverlay\\(\\)").containsMatchIn(activity)
        )
        val upContentRegion = activity.substring(
            activity.indexOf("override fun upContent("),
            activity.indexOf("override suspend fun upContentAwait(")
        )
        assertTrue(
            "upContent 进入时须同步文本面首屏（切章时 curTextChapter 置 null 后正是此回调）",
            upContentRegion.contains("syncTextLoadingOverlay()")
        )
        val finishStart = activity.indexOf("override fun contentLoadFinish() {")
        val finishEnd = activity.indexOf("private fun consumeOpenReadAloudPanelIntent", finishStart)
        val finishRegion = activity.substring(finishStart, finishEnd)
        assertTrue(
            "contentLoadFinish 须同步（保证内容就绪即隐藏）",
            finishRegion.contains("syncTextLoadingOverlay()")
        )
    }

    @Test
    fun `图片书排除与保留的同步点须各有一处结构保证`() {
        // 3.13 收口（2026-10-20）：
        // ①`ReadBook.upData(book)` 必经 `callBack.upMenuView()`，`upMenuView` 里的同步点保留 ——
        //   它的职责是"内容就绪即收尾隐藏"（**不再**是开轮依据：切章/翻页不得再弹首屏模板，
        //   见下一个用例的第三轮裁定）。
        val menuStart = activity.indexOf("override fun upMenuView() {")
        val menuEnd = activity.indexOf("override fun loadChapterList", menuStart)
        assertTrue("upMenuView 覆写须存在", menuStart >= 0 && menuEnd > menuStart)
        assertTrue(
            "upMenuView 须保留同步点（用于就绪收尾）",
            activity.substring(menuStart, menuEnd).contains("syncTextLoadingOverlay()")
        )
        // ②图片书/漫画的内容不进 `curTextChapter`（走 `ReadManga`）⇒ 若纳入"文本面"判定，
        //   `curTextChapter == null` 恒真 ⇒ 覆盖层常驻不消失（真实回归风险）⇒ 必须显式排除 `isImage`。
        val sync = bodyOf(activity, "private fun syncTextLoadingOverlay()")
        assertTrue("文本面判定须排除图片书/漫画（!it.isImage）", sync.contains("!it.isImage"))
        assertTrue("文本面判定须排除 EPUB（!it.isEpub）", sync.contains("!it.isEpub"))
    }

    @Test
    fun `首屏模板须只在进入阅读页展示一次且不闪一下`() {
        // 需求沿革（两轮用户口径都要满足）：
        //  · 第二轮（2026-10-20）：「只有第一次才有，并且时间太短了，退出阅读再进就没有了」
        //    ⇒ 根因：`ReadBook` 是常驻单例 ⇒「退出再进」时 `curTextChapter` 已就绪，而旧判据是
        //    "`curTextChapter == null` 才显示" ⇒ 该场景永不显示；内容一到就 `hide()` ⇒ 只闪一下。
        //  · 第三轮（2026-10-20）：「只有打开一本书看书的时候，第一次才展示，为什么现在翻页到这个内置主题
        //    一个轮次后再次出现？」⇒ 上一版按 `ReadBook.durChapterIndex` 变化开轮 ⇒ **翻页/切章重复弹**。
        // 故本轮收窄为「**每个"进入阅读页"只展示一次**」：
        //  ① 显示判据不得再用"无内容页"；
        //  ② 开轮判据须是"本轮是否已展示过"，且**不得**再依赖章节序号；
        //  ③ 轮次须在**两个入口点**武装：`onPostCreate`（首次进入）/ `onNewIntent`（`singleTask` 复用实例再进）；
        //  ④ 最短展示时长常量 + 延迟收尾的轮次戳守卫。
        val sync = bodyOf(activity, "private fun syncTextLoadingOverlay()")
        assertTrue(
            "开轮判据须是「本轮是否已展示过」",
            sync.contains("if (!textLoadingRoundOpened)")
        )
        assertFalse(
            "不得再按章节序号开轮（翻页/切章重复弹的根因）",
            sync.contains("ReadBook.durChapterIndex")
        )
        assertTrue("开轮时须真的 show()（注入模板 + 文案）", sync.contains(".show("))
        assertFalse(
            "显示判据不得再用 `curTextChapter == null`（那是「退出再进看不到」的根因）",
            sync.contains("curTextChapter == null")
        )
        assertTrue("须使用最短展示时长常量", sync.contains("TEXT_LOADING_MIN_MS"))
        assertTrue("延迟收尾须带轮次戳守卫（防新轮被旧定时器收掉）", sync.contains("textLoadingRoundAt == stamp"))
        assertTrue(
            "最短展示时长须为常量定义（900ms）",
            Regex("private const val TEXT_LOADING_MIN_MS = 900L").containsMatchIn(activity)
        )
        assertTrue(
            "须定义轮次武装点 private fun armTextLoadingRound()",
            Regex("private fun armTextLoadingRound\\(\\)").containsMatchIn(activity)
        )
        assertTrue(
            "首次进入（onPostCreate）须武装轮次",
            bodyOf(activity, "override fun onPostCreate(savedInstanceState: Bundle?)")
                .contains("armTextLoadingRound()")
        )
        assertTrue(
            "singleTask 复用实例再进（onNewIntent）须武装轮次",
            bodyOf(activity, "override fun onNewIntent(intent: Intent)")
                .contains("armTextLoadingRound()")
        )
    }
}
