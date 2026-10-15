package io.legado.app

import androidx.test.core.app.ApplicationProvider
import io.legado.app.help.config.AppConfig
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import splitties.init.appCtx

/**
 * 套件级 **bootstrap**：在任何其他测试类之前把 `appCtx`（进而 `AppConfig.<clinit>`）准备就绪。
 *
 * ## 为什么必须有这个类（NEW-14 实测）
 *
 * 本仓测试跑在**同一个 JVM** 里，而 `AppConfig` 是 `object`（`<clinit>` 直接读 `appCtx`）。
 * 只要**任一**测试类在 `appCtx` 尚未注入时碰到 `AppConfig`，JVM 就会缓存这次失败
 * （`ExceptionInInitializerError` ⇒ 之后所有访问变 `NoClassDefFoundError: Could not
 * initialize class io.legado.app.help.config.AppConfig`）—— 且这个"毒"**不可逆**。
 * 铁证（2026-10-15，本轮 HL-3 批次）：新增测试类改变了类扫描顺序，
 * `BookshelfSnapshotStoreTest`（13 例）与 `BadgeViewThemeModeTest`（2 例）**全红**，
 * 而两者**单独跑全绿**（`--tests` 隔离运行实测）⇒ 纯粹是"谁先碰到 AppConfig"的顺序依赖。
 *
 * ## 为什么类名以 `Aaa` 开头
 *
 * Gradle 按测试类目录扫描顺序执行（近似按包/类名排序）。本类以 `Aaa` 开头 ⇒ 尽量排在全套件最前，
 * **主动触达**一次 `AppConfig` 以便注入没到位时立刻失败（真正的注入由 `TestLegadoApp` 在
 * Application 创建时机完成，与顺序无关；本类只是"早响"的哨兵）。
 *
 * ⚠️ 本类**故意不写** `@Config(application = Application::class)`：需要 Robolectric 装载
 * `TestLegadoApp`（见 `src/test/resources/robolectric.properties`）——它在 `onCreate` 里完成
 * `appCtx` 注入；换成裸 `Application` 则注入不发生，本 bootstrap 就失去意义。
 */
@RunWith(RobolectricTestRunner::class)
class AaaAppCtxBootstrapTest {

    @Test
    fun appCtxIsInitializedBeforeAnyOtherTest() {
        assertNotNull(
            "套件必需：appCtx 必须由真实 Application 初始化（否则 AppConfig 会被永久毒化）",
            appCtx
        )
        // 触达 AppConfig 会触发其 <clinit>：注入没到位就在这里**响**（而不是静默毒化后续 500+ 个类）
        val first = AppConfig.isEInkMode
        val second = AppConfig.isEInkMode
        assertTrue("AppConfig 静态初始化必须成功，且读值必须稳定", first == second)
        assertNotNull(
            "appCtx 必须可用于取 Application（Robolectric 已装载真实 Application）",
            ApplicationProvider.getApplicationContext<android.content.Context>()
        )
    }
}
