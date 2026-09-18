package io.legado.app.help.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 更新通道收敛 + 代理加速 + 版本比较单测（app-update-github-channel）。
 *
 * 覆盖不依赖 Android context 的纯函数：versionName 数值化、资产 versionCode 解析、
 * 代理模板改写与主机名提取、内置模板常量。
 * （`isNewerThanCurrent` 依赖 AppConst.appInfo，属真机 L2 验证范围）
 */
class AppUpdateChannelTest {

    // === versionName 数值化（AD-03）===

    @Test
    fun `versionName数值化 定宽时间段保证数值序等于时间序`() {
        val early = AppUpdate.versionValueOf("3.26.091720")
        val late = AppUpdate.versionValueOf("3.26.100815")
        assertTrue("跨月递增", late > early)
        // 同月内递增
        assertTrue(AppUpdate.versionValueOf("3.26.091721") > early)
    }

    @Test
    fun `versionName数值化 忽略尾部字母后缀`() {
        // 测试包版本名带 c 后缀，数值化后应与不带后缀完全一致
        assertEquals(
            AppUpdate.versionValueOf("3.26.091817"),
            AppUpdate.versionValueOf("3.26.091817c")
        )
    }

    @Test
    fun `versionName数值化 8位旧命名先对齐为6位`() {
        assertEquals(
            AppUpdate.versionValueOf("3.24.010108"),
            AppUpdate.versionValueOf("3.24.01010820")
        )
    }

    @Test
    fun `versionName数值化 格式不符返回0`() {
        assertEquals(0L, AppUpdate.versionValueOf(""))
        assertEquals(0L, AppUpdate.versionValueOf("abc"))
        assertEquals(0L, AppUpdate.versionValueOf("3.26"))
        assertEquals(0L, AppUpdate.versionValueOf("v3.26.091720"))
    }

    // === 资产 versionCode 解析（AD-03）===

    @Test
    fun `资产名带versionCode时正确解析`() {
        assertEquals(
            10539L,
            AppReleaseInfo.parseVersionCode("legado_app_3.26.081303_10539.apk")
        )
    }

    @Test
    fun `本项目资产名不含versionCode时返回0`() {
        // 实测发布资产命名（gh api 确认）：legado_miss_app_3.26.091720.apk
        assertEquals(0L, AppReleaseInfo.parseVersionCode("legado_miss_app_3.26.091720.apk"))
        assertEquals(0L, AppReleaseInfo.parseVersionCode("legado_miss_app_debug_3.26.091720.apk"))
        assertEquals(0L, AppReleaseInfo.parseVersionCode("legado_legacy_app_3.26.091720.apk"))
    }

    @Test
    fun `资产名解析不崩溃`() {
        assertEquals(0L, AppReleaseInfo.parseVersionCode(""))
        assertEquals(0L, AppReleaseInfo.parseVersionCode("abc.apk"))
    }

    // === 代理模板改写（AD-02 / §5.1）===

    @Test
    fun `占位符写法替换原始地址`() {
        assertEquals(
            "https://gh-proxy.com/https://api.github.com/x",
            AppUpdateConfig.applyTemplate(
                "https://gh-proxy.com/\${url}",
                "https://api.github.com/x"
            )
        )
        assertEquals(
            "https://p.example/https://api.github.com/x",
            AppUpdateConfig.applyTemplate(
                "https://p.example/{url}",
                "https://api.github.com/x"
            )
        )
    }

    @Test
    fun `无占位符时按前缀拼接且处理尾部斜杠`() {
        assertEquals(
            "https://p.example/https://api.github.com/x",
            AppUpdateConfig.applyTemplate("https://p.example/", "https://api.github.com/x")
        )
        assertEquals(
            "https://p.example/https://api.github.com/x",
            AppUpdateConfig.applyTemplate("https://p.example", "https://api.github.com/x")
        )
    }

    @Test
    fun `代理主机名提取用于摘要展示`() {
        assertEquals(
            "gh-proxy.com",
            AppUpdateConfig.proxyLabel("https://gh-proxy.com/\${url}")
        )
        assertEquals(
            "cors.isteed.cc",
            AppUpdateConfig.proxyLabel("https://cors.isteed.cc/github.com")
        )
        // 无 scheme 时原样返回，不抛异常
        assertEquals("p.example", AppUpdateConfig.proxyLabel("p.example/\${url}"))
    }

    // === 内置模板常量（design §8 实测定稿）===

    @Test
    fun `内置模板为实测选定的3个且均带占位符`() {
        val templates = AppUpdateConfig.DEFAULT_GITHUB_PROXY_TEMPLATES
        assertEquals(3, templates.size)
        assertEquals("https://gh-proxy.com/\${url}", templates[0])
        assertEquals("https://tvv.tw/\${url}", templates[1])
        assertEquals("https://cors.isteed.cc/\${url}", templates[2])
        assertTrue(templates.all { it.contains("\${url}") })
    }
}