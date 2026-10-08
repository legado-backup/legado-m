package io.legado.app.ui.video

import io.legado.app.testutil.ComposeThemeScopeAssert
import org.junit.Test

/**
 * 视频详情弹层取色单源源契约（fix-compose-theme-scope-and-cache-icon tasks 2B / 4.1，AD-06）。
 *
 * 原实现 `val palette = MaterialTheme.colorScheme`（onSurface/onSurfaceVariant/primary/
 * surfaceVariant/onPrimary）⇒ 已收敛为 `AppUiTokens.dialogStyle()` 直色。
 */
class ComposeThemeScopeContractTest {

    @Test
    fun videoBookDetailSheet_hasNoM3DerivedSurfaceOrTextColor() {
        ComposeThemeScopeAssert.assertNoM3DerivedTextColor(
            "io/legado/app/ui/video/VideoBookDetailSheet.kt"
        )
    }
}