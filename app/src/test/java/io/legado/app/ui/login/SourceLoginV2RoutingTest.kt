package io.legado.app.ui.login

import io.legado.app.data.entities.BookSource
import io.legado.app.model.login.isLoginUiV2
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 登录弹窗分流（ng-js-source-port）。
 *
 * `loginUi` 为 `{"version":2}` 标记时走动态表单（按钮驱动），其余（`@js:` / `<js>` / 静态 JSON）
 * 必须继续走老表单，保证历史书源登录零回归。
 */
class SourceLoginV2RoutingTest {

    @Test
    fun version2Marker_routesToDynamicForm() {
        assertTrue(BookSource(loginUi = """{"version":2}""").isLoginUiV2())
    }

    @Test
    fun legacyLoginUi_keepsOldForm() {
        assertFalse(BookSource(loginUi = """[{"name":"账号","type":"text"}]""").isLoginUiV2())
        assertFalse(BookSource(loginUi = "@js:function loginUi(){}").isLoginUiV2())
        assertFalse(BookSource(loginUi = null).isLoginUiV2())
    }
}
