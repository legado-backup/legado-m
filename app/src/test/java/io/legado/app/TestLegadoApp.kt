package io.legado.app

import android.app.Application
import splitties.init.injectAsAppCtx

/**
 * 测试专用 Application（**仅存在于 `src/test`**）：在任何测试触达 `AppConfig` 之前完成 `appCtx` 注入。
 *
 * 由 `app/src/test/resources/robolectric.properties` 的 `application=io.legado.app.TestLegadoApp`
 * 对**所有 Robolectric 测试**全局生效（测试类仍可用 `@Config(application = ...)` 单独覆盖）。
 *
 * 为什么不继承生产 `App`：`App` 是 **final class**（Kotlin 默认 final），且其 `onCreate` 会拉
 * 生产侧初始化（DB 等）——Robolectric 下并不需要，反而增加不确定性 ⇒ 这里只继承 [Application]
 * 并**只**做 `appCtx` 注入这一件事。
 *
 * 为什么需要它（NEW-14）：全套件跑在同一 JVM，`AppConfig.<clinit>` 直接读 `appCtx`。
 * 生产 `App` 的注入由 **App Startup** 提供，而 Robolectric 下 App Startup 不运行
 * （实测报错原文：`App Startup didn't run … call injectAsAppCtx() in the app's Application subclass`）
 * ⇒ 一旦某测试在注入前触达 `AppConfig`，JVM 就缓存失败并把后续所有触达变成
 * `NoClassDefFoundError`（不可逆），表现为「新增一个测试类就让上百个无关用例变红」。
 * 本类把注入前移到 **Application 创建时机**（早于任何测试类），因此与执行顺序无关。
 */
class TestLegadoApp : Application() {

    override fun onCreate() {
        injectAsAppCtx()
        super.onCreate()
    }
}
