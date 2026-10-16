package io.legado.app.model.localBook.epubcore.direct

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * NEW-86 回归：`EpubDirectDocumentBuilder` 的页排方向判定必须**单源**。
 *
 * 缺陷背景（此前未发现）：`resolvePageLayoutDirection` 此前**零调用**，而 `buildChapter` 内联
 * 复制了一份语义完全相同的 `when`（竖排 → rtl/ltr；否则根 `dir` → 出版方
 * `page-progression-direction`）⇒ 同一判据两份实现，后续极易漂移（改一处忘另一处）。
 *
 * 本用例双重锁定：
 * ① 行为 —— rtl/ltr 判定表的优先级（竖排 > 根 dir > 出版方方向）与归一化；
 * ② 单源 —— 「竖排 → rtl」判定分支全仓只允许出现一次，防止重复实现回流。
 */
class EpubLayoutDirectionResolutionTest {

    @Test
    fun verticalWritingModesDecideDirection() {
        // 竖排书写模式是最高优先级判据：rl → rtl，lr → ltr
        assertEquals(
            "rtl",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection("vertical-rl", null, null)
        )
        assertEquals(
            "rtl",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection("sideways-rl", null, null)
        )
        assertEquals(
            "ltr",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection("vertical-lr", null, null)
        )
        assertEquals(
            "ltr",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection("sideways-lr", null, null)
        )
    }

    @Test
    fun horizontalWritingFallsBackToRootThenPackage() {
        // 非竖排分支：根 dir 优先于出版方 spine 方向
        assertEquals(
            "rtl",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, "rtl", "ltr")
        )
        assertEquals(
            "ltr",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, "LTR", null)
        )
        // 无根 dir 时才回落到 page-progression-direction，且必须归一化（大小写/空白无关）
        assertEquals(
            "rtl",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection("horizontal-tb", null, "RTL")
        )
        assertEquals(
            "ltr",
            EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, null, " ltr ")
        )
    }

    @Test
    fun unknownInputsYieldNull() {
        assertNull(EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, null, null))
        assertNull(EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, null, "sideways"))
        assertNull(EpubDirectDocumentBuilder.resolvePageLayoutDirection(null, "auto", "auto"))
    }

    @Test
    fun directionJudgeStaysSingleSource() {
        // 单源守护：`when` 判定分支只允许出现在所抽函数内，禁止在 buildChapter 再复制一份
        val code = SourceFileProbe.sourceText(
            "model/localBook/epubcore/direct/EpubDirectDocumentBuilder.kt"
        )
        val branch = Regex("\"vertical-rl\",\\s*\"sideways-rl\"\\s*->\\s*\"rtl\"")
        assertEquals(
            "「竖排→rtl」判定分支必须只有一处（单源），禁止再内联复制",
            1,
            branch.findAll(code).count()
        )
    }
}
