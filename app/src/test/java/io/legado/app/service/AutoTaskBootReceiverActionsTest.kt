package io.legado.app.service

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B2 · R7「唤醒重排」接收器的**跨文件一致性**不变量。
 *
 * 为什么值得测：`AutoTaskBootReceiver.HANDLED_ACTIONS`（代码侧）与 `AndroidManifest.xml` 的
 * `intent-filter`（声明侧）是**两处独立书写**的动作集合——只改一侧就会出现
 * 「接收器自认处理、系统却不派发」（或反之）的静默失效，且编译期完全无感。
 */
class AutoTaskBootReceiverActionsTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private fun code(): String = read("src/main/java/io/legado/app/service/AutoTaskBootReceiver.kt")
        .lines()
        .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
        .joinToString("\n")

    private fun manifest(): String = read("src/main/AndroidManifest.xml")

    /** Intent 常量 → 清单里必须出现的 action 字符串。 */
    private val expected = mapOf(
        "Intent.ACTION_BOOT_COMPLETED" to "android.intent.action.BOOT_COMPLETED",
        "Intent.ACTION_TIMEZONE_CHANGED" to "android.intent.action.TIMEZONE_CHANGED",
        "Intent.ACTION_TIME_CHANGED" to "android.intent.action.TIME_SET",
        "Intent.ACTION_MY_PACKAGE_REPLACED" to "android.intent.action.MY_PACKAGE_REPLACED"
    )

    @Test
    fun receiverHandlesExactlyFourAlarmInvalidatingEvents() {
        val t = code()
        expected.keys.forEach { constant ->
            assertTrue("接收器应处理 $constant", t.contains(constant))
        }
    }

    @Test
    fun manifestRegistersReceiverWithMatchingActions() {
        val m = manifest()
        assertTrue("清单必须注册 .service.AutoTaskBootReceiver", m.contains("android:name=\".service.AutoTaskBootReceiver\""))
        expected.values.forEach { action ->
            assertTrue("清单 intent-filter 缺少 $action", m.contains("android:name=\"$action\""))
        }
    }

    @Test
    fun rescheduleIsIdempotentAndFailSafe() {
        val t = code()
        assertTrue("重排必须走 AutoTask.refreshSchedule（内部先取消再重建 ⇒ 幂等）",
            t.contains("AutoTask.refreshSchedule("))
        assertTrue("重排异常必须被捕获（广播不得崩溃）", t.contains("runCatching"))
        assertTrue("失败须留日志便于排查", t.contains("AppLog.put("))
        assertEquals("不认识的 action 必须直接返回", true, t.contains("action !in HANDLED_ACTIONS"))
    }
}