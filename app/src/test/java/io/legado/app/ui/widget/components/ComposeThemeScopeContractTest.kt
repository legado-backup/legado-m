package io.legado.app.ui.widget.components

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 弹层/对话框取色单源源契约（fix-compose-theme-scope-and-cache-icon tasks 2B / 4.1，AD-06）。
 *
 * 守护：弹层族文字/图标/分隔线取色必须走 `AppDialogStyle` 直色（或弹层内容色），
 * **禁止** `MaterialTheme.colorScheme.onSurface(Variant)` 等 M3 派生色 ——
 * 其真值取决于宿主是否提供主题作用域（2026-10-08 报障根因之一）。
 *
 * 刻意**不纳入**跨场景复用组件（`SettingsSearchBar` / `MetricGrid` / `SettingsToggleRow` /
 * `GroupHeader` / `RowIcon` / `TagChip`）：它们在普通页面与弹层内共用，替换会造成「弹层外变黑」，
 * 其存量收敛登记为后续批次（spec E9）。
 */
class ComposeThemeScopeContractTest {

    private val dialogFamily = listOf(
        "io/legado/app/ui/widget/components/AppMenuSheet.kt",
        "io/legado/app/ui/widget/components/AppModalBottomSheet.kt",
        "io/legado/app/ui/widget/components/ColorPickerSheet.kt",
        "io/legado/app/ui/widget/components/HighlightStyleSheet.kt",
        "io/legado/app/ui/widget/components/ConfirmDialog.kt",
        "io/legado/app/ui/widget/components/AppTextDialog.kt",
        "io/legado/app/ui/widget/components/AppEditDialog.kt",
        "io/legado/app/ui/widget/components/AppConfirmDialog.kt",
        "io/legado/app/ui/widget/components/SingleChoiceDialog.kt"
    )

    @Test
    fun dialogFamily_hasNoM3DerivedSurfaceOrTextColor() {
        dialogFamily.forEach { ComposeThemeScopeAssert.assertNoM3DerivedTextColor(it) }
    }
}