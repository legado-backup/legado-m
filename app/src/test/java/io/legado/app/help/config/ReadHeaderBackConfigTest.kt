package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.2 页眉返回按钮 · 配置链不变量（源码文本断言）。
 *
 * 为什么用源码断言：`ReadBookConfig` 是触碰 `appCtx`/prefs 的 `object`，JVM 内不可实例化；
 * 而本条的**真实风险**恰恰是「字段加了但某条链路没透传」（本项目已多次实证的沉默杀手：
 * `Config` 字段 + 代理读写 + `toMap`（样式包/备份）+ share→export 拷贝 四处缺一即「保存/导出即丢」）。
 */
class ReadHeaderBackConfigTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    private fun readBookConfig() = read("src/main/java/io/legado/app/help/config/ReadBookConfig.kt")

    @Test
    fun fieldDefaultsToFalse() {
        val t = readBookConfig()
        assertTrue(
            "默认必须关（否则老用户阅读页凭空多一个按钮）",
            t.contains("var showHeaderBackButton: Boolean = false")
        )
    }

    @Test
    fun allFourConfigLinksAreWired() {
        val t = readBookConfig()
        assertTrue("① Config 字段缺失", t.contains("var showHeaderBackButton: Boolean = false,"))
        assertTrue("② 对象代理读缺失", t.contains("get() = config.showHeaderBackButton"))
        assertTrue("② 对象代理写缺失", t.contains("config.showHeaderBackButton = value"))
        assertTrue("③ toMap（样式包/备份导出）缺失", t.contains("\"showHeaderBackButton\" to showHeaderBackButton"))
        assertTrue(
            "④ share→export 拷贝缺失（共用布局导出会丢该设置）",
            t.contains("exportConfig.showHeaderBackButton = shareConfig.showHeaderBackButton")
        )
    }

    @Test
    fun tipConfigProxyIsWired() {
        val t = read("src/main/java/io/legado/app/help/config/ReadTipConfig.kt")
        assertTrue("ReadTipConfig 代理读缺失", t.contains("get() = ReadBookConfig.config.showHeaderBackButton"))
        assertTrue("ReadTipConfig 代理写缺失", t.contains("ReadBookConfig.config.showHeaderBackButton = value"))
    }
}