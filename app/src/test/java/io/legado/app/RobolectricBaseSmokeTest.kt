package io.legado.app

import android.app.Application
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * B5 · R23 测试底座**实证**测试（不是装饰性冒烟：本项目历史上多次栽在「声明了但从未生效」）。
 *
 * 证明三件事同时成立：
 *  1. `org.robolectric:robolectric` 依赖可用且能在 JVM 侧起 Android 运行时；
 *  2. `testOptions.unitTests.includeAndroidResources = true` 生效 —— 能读到**真实**资源
 *     （不是 `returnDefaultValues` 的 null/0 桩）；
 *  3. `androidx.test:core` 的 `ApplicationProvider` 可用。
 *
 * `@Config(application = Application::class)` 是刻意的：默认会实例化清单里的
 * `io.legado.app.App`（重初始化：配置/数据库/网络栈），既慢又与单测无关；
 * 底座实证只关心「Android 运行时 + 资源」两项能力。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class RobolectricBaseSmokeTest {

    @Test
    fun appContextIsAvailable() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        assertNotNull("Robolectric 必须提供 Context", context)
        assertTrue("包名不得为空", context.packageName.isNotBlank())
    }

    /** 读真实资源：`returnDefaultValues` 的桩会给 0/null，只有 includeAndroidResources 才能拿到真实串。 */
    @Test
    fun realStringResourceIsReadable() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertTrue("必须读到真实 app_name 资源（证明 includeAndroidResources 生效）", appName.isNotBlank())
    }

    /** 读真实字符串数组：覆盖 res/values/arrays.xml 类资源，进一步排除「只对单串生效」的偶合。 */
    @Test
    fun realStringArrayResourceIsReadable() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val types = context.resources.getStringArray(R.array.book_type)
        assertTrue("必须读到非空字符串数组资源", types.isNotEmpty())
    }
}
