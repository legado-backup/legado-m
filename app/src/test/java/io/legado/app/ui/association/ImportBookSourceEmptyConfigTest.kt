package io.legado.app.ui.association

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.1（J10 硬阻断口径）：导入链路的接线不变量
 *
 * 判定单源在 `help/source`，本测试只管「剔除点 + 回执 + 文案三处都真的接上了」。
 */
class ImportBookSourceEmptyConfigTest {

    private val viewModelCode =
        SourceFileProbe.sourceText("ui/association/ImportBookSourceViewModel.kt")
    private val dialogCode =
        SourceFileProbe.sourceText("ui/association/ImportBookSourceDialog.kt")

    @Test
    fun emptySourcesAreRemovedAtTheSingleChokePoint() {
        assertTrue(
            "必须在 allSources 定型的收口点（comparisonSource）就地剔除",
            viewModelCode.contains("val keptSources = allSources.filterNot { it.isEmptyConfiguration() }")
        )
        assertTrue(
            "剔除后必须真正回写 allSources（列表/校验/导入三链共用一个数组）",
            viewModelCode.contains("allSources.addAll(keptSources)")
        )
        assertTrue(
            "剔除数量必须回执给 UI",
            viewModelCode.contains("emptyConfigCount.postValue(ignoredCount)")
        )
    }

    @Test
    fun dialogShowsIgnoredReceipt() {
        assertTrue(
            "弹框必须观测回执",
            dialogCode.contains("viewModel.emptyConfigCount.observe(viewLifecycleOwner)")
        )
        assertTrue(
            "标题必须追加回执文案（否则用户以为源少了）",
            dialogCode.contains("R.string.import_empty_source_ignored")
        )
    }

    @Test
    fun stringResourceExistsInDefaultValues() {
        assertTrue(
            "默认资源必须存在（中文文案在 values-zh，由本地化流程维护）",
            SourceFileProbe.resValuesRawText("strings.xml")
                .contains("name=\"import_empty_source_ignored\"")
        )
    }
}