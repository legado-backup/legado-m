package io.legado.app.ui.book.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读页模板路由契约（epub-md-rich-rendering 阶段 4.14 配对）。
 *
 * 存在理由：路由改动落在 5000+ 行的 `ReadBookActivity` 里，而**默认关闭**（4.9）意味着
 * 回归测试跑不到这条路径 ⇒ 一旦漏接（比如忘了在 `keyPage` 里加分支、或忘了在 `onDestroy` 释放），
 * 症状只有"开了模板的用户"能遇到：翻页没反应 / WebView 泄漏 / 主题切换不生效。
 * 故把这几处接线钉在源码层。
 */
class ReadBookTemplateRoutingTest {

    private val activity = "ui/book/read/ReadBookActivity.kt"

    private fun text(): String = SourceFileProbe.sourceText(activity)

    @Test
    fun `开关关闭时不得进入模板面`() {
        val s = text()
        assertTrue("必须有整体开关判据", s.contains("ReaderTemplateManager.templatesEnabled()"))
        assertTrue("解析入口必须存在", s.contains("private suspend fun ensureTemplateAwait()"))
        assertTrue(
            "无生效模板必须回落既有面（否则开关形同虚设）",
            s.contains("loadTextRichContentAwait(relativePosition, resetPageOffset, success)")
        )
    }

    @Test
    fun `两处内容分派都接了模板面`() {
        val s = text()
        // 1 处声明 + 2 处调用点（upContent / upContentAwait）⇒ 命名出现次数至少 3
        assertTrue(
            "upContent/upContentAwait 两处分派都要接（当前命名出现 ${Regex("loadTemplateContentAwait").findAll(s).count()} 次）",
            Regex("loadTemplateContentAwait").findAll(s).count() >= 3
        )
        assertTrue("模板面必须有独立载入函数", s.contains("private suspend fun loadTemplateContentAwait("))
    }

    @Test
    fun `翻页主题切换与进度都覆盖模板面`() {
        val s = text()
        assertTrue("keyPage 必须有模板分支", s.contains("if (templateActive) {") && s.contains("backend.pageNext()"))
        assertTrue("主题/字号变更必须重载模板面", s.contains("private fun reloadTemplateCurrent()"))
        assertTrue("进度条必须覆盖模板面", s.contains("if (textRichActive || templateActive) {"))
    }

    @Test
    fun `位置保存恢复与资源释放齐备`() {
        val s = text()
        assertTrue("onPause 必须保存模板位置", s.contains("saveTemplatePosition()"))
        assertTrue("首帧后必须恢复位置", s.contains("private fun onTemplateRendered("))
        assertTrue("onDestroy 必须释放", s.contains("switchTemplate(false)"))
        assertTrue("两面共用承载位 ⇒ 必须互斥", s.contains("if (templateActive) switchTemplate(false)"))
    }

    @Test
    fun `模板面与文本富渲染面共用同一承载位`() {
        val s = text()
        assertTrue(
            "可见性判据必须同源（否则两个 WebView 同时可见）",
            s.contains("textRichReadView.isVisible = textRichActive || templateActive")
        )
        assertFalse("不得为模板新增独立承载位节点（避免布局漂移）", s.contains("templateReadView"))
    }

    @Test
    fun `装饰档位与动效随真值下发且支持系统减少动效`() {
        // 4.8d：装饰是用户级设置，必须在**每次渲染时**从偏好单源重算（否则改档位后不生效）
        val s = text()
        assertTrue("档位必须来自管理门面（单源）", s.contains("ReaderTemplateManager.decorationCssValue(reduceMotion)"))
        assertTrue("动效必须来自管理门面（单源）", s.contains("ReaderTemplateManager.decorationMotionEnabled(reduceMotion)"))
        assertTrue("必须探测系统减少动效", s.contains("private fun isSystemReduceMotion()"))
        assertTrue(
            "减少动效必须用系统动画缩放判据（与 CSS prefers-reduced-motion 同源）",
            s.contains("Settings.Global.ANIMATOR_DURATION_SCALE")
        )
        assertTrue(
            "解析日志必须带装饰档位（真机 L2 的宿主侧证据；缺了只能靠猜沙箱有没有收到）",
            s.contains("decor=\${ReaderTemplateManager.decorationCssValue(isSystemReduceMotion())}")
        )
    }

    @Test
    fun `动效生命周期与稳定随机已接线`() {
        // 4.15 C6：沙箱看不到宿主手势/生命周期 ⇒ 必须由宿主在 DOWN/UP 与 onPause/onResume 下令
        val s = text()
        assertTrue("必须有触摸期停动效入口", s.contains("override fun dispatchTouchEvent(ev: MotionEvent)"))
        assertTrue("按下即停（拖动跟手）", s.contains("MotionEvent.ACTION_DOWN -> templateBackend?.setMotionPaused(true)"))
        assertTrue(
            "抬手/取消即恢复",
            s.contains("MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL ->") &&
                s.contains("templateBackend?.setMotionPaused(false)")
        )
        assertTrue(
            "离页必须停（onPause 处下发）",
            Regex("setMotionPaused\\(true\\)").findAll(s).count() >= 2
        )
        assertTrue(
            "回前台必须恢复（onResume 处下发）",
            Regex("setMotionPaused\\(false\\)").findAll(s).count() >= 2
        )
        // 4.15 C4：稳定随机种子随真值下发（同章同值）
        assertTrue("种子必须由书名+章节稳定推导", s.contains("ReaderTemplateSeed.of(bookName, chapterTitle)"))
        assertTrue("种子必须进 ReaderValues", s.contains("seed = ReaderTemplateSeed.of("))
    }

    @Test
    fun `文本类内容按模板总开关放开且 md 与 EPUB 口径不变`() {
        // 用户反馈「开启模板后看不到任何变化」的机制性根因：
        // ① 总闸原先要求 isMarkdown ⇒ 在线正文/txt 永不进模板面；
        // ② 内容探测原先只认 <usehtml>（md 独有）⇒ 即便进面也拿不到正文。
        val s = text()
        assertTrue("md 仍走 mdRichRender 开关", s.contains("AppConfig.mdRichRender"))
        assertTrue(
            "非 md 文本类内容随模板总开关放开（默认关 ⇒ 零回归）",
            s.contains("ReaderTemplateManager.templatesEnabled()")
        )
        assertTrue(
            "文本类格式闸门须排除 EPUB 与音视频/图片/PDF（对齐 archive isOrdinaryText）",
            s.contains("if (book.isEpub || book.isAudio || book.isVideo || book.isImage || book.isPdf) return false")
        )
        assertTrue(
            "在线正文须先读内容缓存、未缓存时**按需下载**（archive 同口径；只读缓存会让冷启在线书回落 canvas）",
            s.contains("BookHelp.getContent(book, chapter)?.let { return it }") &&
                s.contains("CacheBook.getOrCreate(source, book).downloadAwait(chapter)")
        )
        assertTrue(
            "非 md 内容必须允许非 <usehtml> 归一化（否则归一化前就会回落 canvas）",
            s.contains("richTextAllowsPlainText()") &&
                s.contains("allowPlainText = richTextAllowsPlainText()")
        )
    }

    @Test
    fun `模板失败按书级原子降级且熔断防反复（S11）`() {
        // AD-28② 的模板侧落地：模板失败原本只 `switchTemplate(false)` 一次，**无书级状态** ⇒
        // 下一章 `upContent` 又会重进模板面（逐章闪回 = "降级反复"），且没有同章熔断。
        val s = text()
        assertTrue("必须有书级模板闸门", s.contains("private fun templateAllowedForCurrentBook()"))
        assertTrue(
            "闸门必须复用书级降级判据（与 EPUB core 同一治理层）",
            s.contains("isBookRenderDegradedToCanvas(ReadBook.book?.bookUrl)")
        )
        assertTrue(
            "降级后本章必须改走文本富渲染面（不再尝试模板）",
            s.contains("if (!templateAllowedForCurrentBook()) {") &&
                s.contains("loadTextRichContentAwait(relativePosition, resetPageOffset, success)")
        )
        assertTrue(
            "模板面开局必须向治理层登记书级后端",
            s.contains("renderGovernor.startBook(book.bookUrl, BackendSelectionPolicy.Backend.DIRECT_WEB)")
        )
        assertTrue(
            "失败必须上报治理层（书级降级 + 同章 15s 熔断）",
            s.contains("renderGovernor.onChapterFailure(") &&
                s.contains("textRichPreparedIndex.coerceAtLeast(0)")
        )
        assertTrue(
            "契约变更必须清降级状态（换模板/切日夜后能按新契约重试）",
            Regex("renderGovernor\\.dispose\\(\\)").findAll(s).count() >= 3
        )
    }

    @Test
    fun `产品指标在真实站点计数且同书去重（S4）`() {
        // S4 / SP-09：指标若漏接线就是**恒 0 的死统计**（页面照常工作、无人察觉）⇒ 源码层钉住三个站点。
        val s = text()
        assertTrue(
            "内容首次加载必须记一次『打开』（md 使用率分母/分子）",
            s.contains("reportBookOpenedOnce()") && s.contains("private fun reportBookOpenedOnce()")
        )
        assertTrue(
            "打开计数必须同书去重（否则重载/换面会重复计数）",
            s.contains("if (metricsBookKey == book.bookUrl) return")
        )
        assertTrue(
            "⚠️ 不得把打开计数挂在 onResume 的契约键函数上（首帧 ReadBook.book 未就绪 ⇒ 恒漏计）",
            !s.contains("首次进入阅读页 ⇒ 记一次")
        )
        assertTrue(
            "模板面真正用上时必须计数（模板启用率分子）",
            s.contains("ReaderMetrics.app.templateSurfaceUsed()")
        )
        assertTrue("同书必须去重（否则重载会重复计数）", s.contains("metricsTemplateBookKey"))
        assertTrue(
            "只在真的发生降级时计数（被熔断拒绝的不重复计 ⇒ 与『降级不反复』同口径）",
            s.contains("if (outcome?.degraded == true) ReaderMetrics.app.templateDegraded()")
        )
    }

    @Test
    fun `改完设置返回阅读页立即重载当前章`() {
        // 「设置后立马可以看到书籍变化」：管理页/主题设置是另一页面 ⇒ 必须按契约键比对后重载
        val s = text()
        assertTrue("必须有契约键重载入口", s.contains("private fun refreshReadSurfaceIfContractChanged()"))
        assertTrue("onResume 必须调用它", s.contains("refreshReadSurfaceIfContractChanged()"))
        assertTrue(
            "契约键必须含选中模板（否则换模板时键不变 ⇒ 复用旧解析结果 ⇒ 看起来没生效）",
            s.contains("ReaderTemplateManager.effectiveId(night)")
        )
        assertTrue("必须含日夜（日夜切换会换模板）", s.contains("|\$night|"))
        assertTrue("必须含总开关", s.contains("ReaderTemplateManager.templatesEnabled()}|"))
        assertTrue("必须清面状态（否则被'同章且后端在场即跳过'的防重入闸住）", s.contains("textRichPreparedIndex = -1"))
        assertTrue("必须清模板解析缓存", s.contains("templateResolvedKey = null"))
    }
}