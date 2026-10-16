package io.legado.app.model

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-81 接线契约 —— 划线**落库后**必须触发 Obsidian 自动导出。
 *
 * 存在理由：`ThoughtObsidianExporter.exportBookAsync` 是「新增划线时自动导出」的唯一入口，
 * 且它内部自判 `AppConfig.obsidianAutoExport` 开关。若这条调用点缺失，用户的开关就形同虚设
 * （编译期完全无感，只有真机划一条线再去看 vault 才能发现）⇒ 按「数量 + 位置」钉在源码层。
 *
 * 位置口径：必须挂在 `bookHighlightDao.insert` 的 **`onSuccess`** 成功分支之后 —— 落库是异步的，
 * 若在 UI 调用点直接触发会与 `insert` 竞态，导致最新一条划线漏进导出文件（导出器按书读全量划线）。
 */
class ReadBookObsidianExportWiringTest {

    private val source = SourceFileProbe.sourceText("model/ReadBook.kt")

    @Test
    fun `新增划线路径必须恰有一处触发自动导出`() {
        assertEquals(
            "新增划线路径必须恰有一个自动导出触发点（缺失 ⇒ 自动导出开关失效；多余 ⇒ 重复写盘）",
            1,
            Regex("""ThoughtObsidianExporter\.exportBookAsync\(""").findAll(source).count()
        )
        assertTrue(
            "必须导入导出器单源",
            source.contains("import io.legado.app.ui.book.thought.ThoughtObsidianExporter")
        )
    }

    @Test
    fun `触发点必须位于划线的落库成功分支`() {
        assertTrue(
            "自动导出必须挂在 `bookHighlightDao.insert(highlight)` 的 onSuccess 之后（避免与异步落库竞态）",
            Regex(
                """bookHighlightDao\.insert\(highlight\)[\s\S]{0,400}?onSuccess\s*\{[\s\S]{0,400}?exportBookAsync"""
            ).containsMatchIn(source)
        )
    }
}
