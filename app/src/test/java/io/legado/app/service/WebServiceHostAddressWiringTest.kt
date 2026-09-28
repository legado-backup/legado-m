package io.legado.app.service

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 一期 §6.2「地址活字牌（S1）」接线不变量（**源码文本断言**，与本包既有 Service 测试同口径：
 * Service 类不必在 JVM 中加载，避免 Android 运行时依赖）。
 *
 * 锁住三件事：
 * ① `hostAddress` **唯一写入点** = `setHostAddress`（否则又会出现"静态字段已更新、StateFlow 没更新"
 *   的两条读路径分叉，设置页活字牌会永远停在旧值）；
 * ② 服务内既有的地址刷新点（网络回调 / 起服务）都改走该写入点；
 * ③ 服务销毁必须清空地址（否则页面会显示已失效的地址）。
 */
class WebServiceHostAddressWiringTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/service/WebService.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText().replace("\r\n", "\n")
    }

    @Test
    fun hostAddressIsReadOnlyOutsideAndHasSingleWriter() {
        val t = code()
        assertTrue(
            "hostAddress 必须以 `private set` 暴露（外部只能读，防绕过 Flow 直写）",
            t.contains("var hostAddress = \"\"\n            private set")
        )
        assertTrue(
            "必须提供 StateFlow 供设置页订阅（S1 免轮询）",
            t.contains("val hostAddressFlow: StateFlow<String> = _hostAddressFlow.asStateFlow()")
        )
        // 全文件出现 `hostAddress =` 的位置只允许两处：声明处 + setHostAddress 内赋值
        val rawAssignments = Regex("""(?<!_)(?<!\w)hostAddress\s*=""")
            .findAll(t)
            .map { it.value }
            .count()
        assertEquals(
            "除声明与 setHostAddress 内部外，不得再有 hostAddress 直接赋值（发现 $rawAssignments 处）",
            2,
            rawAssignments
        )
    }

    @Test
    fun allRefreshPointsGoThroughSetter() {
        val t = code()
        assertTrue(
            "必须存在唯一写入点 setHostAddress",
            t.contains("private fun setHostAddress(value: String)")
        )
        // 只统计「以 setHostAddress( 开头的语句行」，避开函数定义行与 Flow 声明行
        val callLines = t.lines().count { it.trim().startsWith("setHostAddress(") }
        assertEquals(
            "写入点调用次数：网络回调有地址 / 网络回调无地址 / 起服务成功 / 销毁清空 = 4（实际 $callLines）",
            4,
            callLines
        )
        assertTrue("起服务成功路径须写入地址", t.contains("setHostAddress(notificationList.first())"))
        assertTrue(
            "服务销毁须清空地址（否则页面显示失效地址）",
            t.contains("setHostAddress(\"\")")
        )
    }

    @Test
    fun portComesFromSingleSourcePolicy() {
        val t = code()
        assertTrue(
            "端口归一须走单源策略，禁止在服务内再写区间字面量",
            t.contains("WebPortPolicy.normalize(getPrefInt(PreferKey.webPort, WebPortPolicy.DEFAULT))")
        )
        assertTrue(
            "服务内不得残留 1024..65530 字面量（区间唯一真源 = WebPortPolicy.RANGE）",
            !t.contains("1024..65530")
        )
    }
}
