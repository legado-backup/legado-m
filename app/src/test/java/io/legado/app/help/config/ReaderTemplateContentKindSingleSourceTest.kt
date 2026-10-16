package io.legado.app.help.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-91：模板内容形态单一判据的**UI 门面**接线（`ReaderTemplateManager.isTextLikeContent`）。
 *
 * 门面只做转发，判据单源在 `ReaderTemplateAvailabilityPolicy`（纯策略）—— 与 `ReaderTemplateManager`
 * 自身 KDoc 的约定一致：「业务判据全部留在 `model...template` 的纯策略里，避免同一规则出现两份」。
 */
class ReaderTemplateContentKindSingleSourceTest {

    private val src = SourceFileProbe.sourceText("help/config/ReaderTemplateManager.kt")

    @Test
    fun `manager facade delegates to the pure policy`() {
        assertEquals(
            "门面必须定义 isTextLikeContent",
            1,
            Regex("""fun isTextLikeContent\(""").findAll(src).count()
        )
        assertEquals(
            "门面必须转发到策略单源（不得自行内联内容形态判据）",
            1,
            Regex("""ReaderTemplateAvailabilityPolicy\.isTextLikeContent\(""").findAll(src).count()
        )
        assertEquals(
            "门面不得再内联 isEpub/isAudio 形态判据",
            0,
            Regex("""book\.isEpub \|\| book\.isAudio""").findAll(src).count()
        )
    }
}
