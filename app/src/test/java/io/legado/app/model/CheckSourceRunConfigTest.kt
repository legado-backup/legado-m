package io.legado.app.model

import io.legado.app.help.IntentData
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「内置批量巡检」运行期配置的**行为**单测（`CheckSourceRunConfig.resolve` 为纯函数，可 JVM 直测）。
 *
 * 护栏目标：程序化启动（REST `/startCheckSource`）能选择**下游维度档位**与**单源超时**，且
 * **缺省一律沿用 [CheckSource] 持久化现值**（行为零变化）；显式布尔优先于档位；非法档位必须显式失败
 * 而不是被静默忽略（否则调用方以为已生效、实际仍跑全量）。
 */
class CheckSourceRunConfigTest {

    @Test
    fun `全缺省即空配置_完全沿用单例现值`() {
        val cfg = CheckSourceRunConfig.resolve(null, null, null, null, null)
        assertTrue("全 null ⇒ 空配置（行为零变化）", cfg.isEmpty)
        assertNull(cfg.timeoutMs)
        assertNull(cfg.checkInfo)
        assertNull(cfg.checkCategory)
        assertNull(cfg.checkContent)
    }

    @Test
    fun `L3档开启下游三维`() {
        val cfg = CheckSourceRunConfig.resolve("L3", null, null, null, null)
        assertEquals(true, cfg.checkInfo)
        assertEquals(true, cfg.checkCategory)
        assertEquals(true, cfg.checkContent)
        assertFalse("有覆盖项即非空配置", cfg.isEmpty)
    }

    @Test
    fun `L2档只开详情`() {
        val cfg = CheckSourceRunConfig.resolve("L2", null, null, null, null)
        assertEquals(true, cfg.checkInfo)
        assertEquals(false, cfg.checkCategory)
        assertEquals(false, cfg.checkContent)
    }

    @Test
    fun `L1档关闭全部下游维度`() {
        val cfg = CheckSourceRunConfig.resolve("L1", null, null, null, null)
        assertEquals(false, cfg.checkInfo)
        assertEquals(false, cfg.checkCategory)
        assertEquals(false, cfg.checkContent)
    }

    @Test
    fun `档位大小写不敏感且首尾空白被裁剪`() {
        val cfg = CheckSourceRunConfig.resolve(" l3 ", null, null, null, null)
        assertEquals(true, cfg.checkInfo)
        assertEquals(true, cfg.checkCategory)
        assertEquals(true, cfg.checkContent)
    }

    @Test
    fun `显式布尔优先于档位`() {
        // depth=L3 本应三维全开，显式 checkContent=false 必须覆盖之，其余仍取档位值
        val cfg = CheckSourceRunConfig.resolve("L3", null, null, null, false)
        assertEquals(true, cfg.checkInfo)
        assertEquals(true, cfg.checkCategory)
        assertEquals(false, cfg.checkContent)
    }

    @Test
    fun `未给档位时显式布尔独立生效`() {
        val cfg = CheckSourceRunConfig.resolve(null, null, true, false, null)
        assertEquals(true, cfg.checkInfo)
        assertEquals(false, cfg.checkCategory)
        assertNull("未指定项须保持 null（沿用现值）", cfg.checkContent)
    }

    @Test
    fun `非法档位须显式失败而非静默忽略`() {
        val ex = assertThrows(IllegalArgumentException::class.java) {
            CheckSourceRunConfig.resolve("L9", null, null, null, null)
        }
        assertTrue("错误文案须含合法取值", ex.message!!.contains("L1"))
    }

    @Test
    fun `超时只接受正数`() {
        assertEquals(12_000L, CheckSourceRunConfig.resolve(null, 12_000L, null, null, null).timeoutMs)
        assertNull("<=0 视为未指定", CheckSourceRunConfig.resolve(null, 0L, null, null, null).timeoutMs)
        assertNull("负数视为未指定", CheckSourceRunConfig.resolve(null, -1L, null, null, null).timeoutMs)
    }

    @Test
    fun `运行期配置经IntentData一次性下发并读取`() {
        // 复刻 CheckSource.start → CheckSourceService.onStartCommand 的下发/消费契约
        IntentData.put(CheckSourceRunConfig.INTENT_KEY, CheckSourceRunConfig(checkInfo = true))
        val got = IntentData.get<CheckSourceRunConfig>(CheckSourceRunConfig.INTENT_KEY)
        assertNotNull("下发后须可读取", got)
        assertEquals(true, got!!.checkInfo)
        assertNull("IntentData.get 须移除键（一次性，防上次配置被误消费）",
            IntentData.get<CheckSourceRunConfig>(CheckSourceRunConfig.INTENT_KEY))
    }
}
