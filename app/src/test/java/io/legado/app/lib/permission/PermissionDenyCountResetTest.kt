package io.legado.app.lib.permission

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-83：`权限拒绝计数` 缺少重置通道的修复守护。
 *
 * 缺陷（用户可感）：`showSettingDialog` 里 `getDenyCount(it) > 5` 会**直接静音**本次申请并跳系统设置页，
 * 而计数只在用户点「取消」时累加、**此前没有任何重置点** ⇒ 用户多次取消后再想授权也看不到系统弹窗，
 * 且计数永久残留（除清数据）。修复＝授权成功时清零对应权限的计数（[resetDenyCountsIfGranted]）。
 *
 * 为什么能 JVM 断言：把判据抽成了**纯函数**（入参 = 授权结果数组 + 权限名数组 + 回调），
 * 不依赖 Activity / SharedPreferences / Robolectric。
 */
class PermissionDenyCountResetTest {

    // 用字面量避免测试期依赖 android.jar 的 stub（PackageManager.PERMISSION_GRANTED == 0 / DENIED == -1）
    private val granted = 0
    private val denied = -1

    @Test
    fun `授权成功的权限被清零且返回个数正确`() {
        val cleared = mutableListOf<String>()
        val n = resetDenyCountsIfGranted(
            intArrayOf(granted),
            arrayOf("android.permission.CAMERA")
        ) { cleared += it }
        assertEquals("授权成功应清零 1 个权限", 1, n)
        assertEquals("应清零且仅清零被授权的那个权限", listOf("android.permission.CAMERA"), cleared)
    }

    @Test
    fun `混合结果时只清零被授权的权限_拒绝的保留计数`() {
        val cleared = mutableListOf<String>()
        val n = resetDenyCountsIfGranted(
            intArrayOf(denied, granted, denied),
            arrayOf("A", "B", "C")
        ) { cleared += it }
        assertEquals("只有 1 个权限被授权", 1, n)
        assertEquals("拒绝的权限不得清零（否则「多次拒绝后跳设置页」语义被破坏）", listOf("B"), cleared)
    }

    @Test
    fun `全部拒绝时不清零`() {
        val cleared = mutableListOf<String>()
        val n = resetDenyCountsIfGranted(intArrayOf(denied, denied), arrayOf("A", "B")) { cleared += it }
        assertEquals("全部拒绝应返回 0", 0, n)
        assertEquals("全部拒绝时不得触碰任何计数", emptyList<String>(), cleared)
    }

    @Test
    fun `用户取消_空结果数组时安全不抛异常也不清零`() {
        val cleared = mutableListOf<String>()
        val n = resetDenyCountsIfGranted(IntArray(0), arrayOf("A", "B")) { cleared += it }
        assertEquals("空结果应返回 0", 0, n)
        assertEquals("空结果不得清零", emptyList<String>(), cleared)
    }

    @Test
    fun `结果数组比权限数组短时按安全下标取值`() {
        val cleared = mutableListOf<String>()
        val n = resetDenyCountsIfGranted(intArrayOf(granted), arrayOf("A", "B", "C")) { cleared += it }
        assertEquals("只处理有结果的位", 1, n)
        assertEquals("长度不齐时不得越界", listOf("A"), cleared)
    }

    private fun activitySource(): String =
        listOf(
            File("src/main/java/io/legado/app/lib/permission/PermissionActivity.kt"),
            File("../app/src/main/java/io/legado/app/lib/permission/PermissionActivity.kt"),
            File("app/src/main/java/io/legado/app/lib/permission/PermissionActivity.kt")
        ).firstOrNull { it.isFile }?.readText()?.replace("\r\n", "\n") ?: error("未找到 PermissionActivity.kt")

    @Test
    fun `活动内已接线_授权回调确实调用清零`() {
        // 形态探针（带期望值）：防后续重构把调用点删掉——纯函数正确但没人调等于没修
        val hook = activitySource().substringAfter("override fun onRequestPermissionsResult(")
        assertEquals(
            "onRequestPermissionsResult 必须调用 resetDenyCountsIfGranted（NEW-83 接线点）",
            true,
            hook.contains("resetDenyCountsIfGranted(grantResults, permissions, ::resetDenyCount)")
        )
    }

    @Test
    fun `连续拒绝超阈值时跳系统设置而非静默结束`() {
        // NEW-84：阈值闸旧行为＝`finish()`（用户既看不到弹窗、也无任何去处）⇒ 改为送系统设置页
        val src = activitySource()
        val at = src.indexOf("getDenyCount(it) > 5)")
        assertEquals("阈值闸代码位应存在（判据锚点失效需同步更新本测试）", true, at >= 0)
        // 取阈值闸之后的有界窗口（与仓内「400 字符契约」同口径，防越界读到别处）
        val window = src.substring(at, kotlin.math.min(src.length, at + 200))
        assertEquals("阈值闸必须把用户送到系统设置页", true, window.contains("openSettingsActivity()"))
        assertEquals("阈值闸不得再静默 finish（旧行为＝无弹窗也无入口）", false, window.contains("finish()"))
    }
}
