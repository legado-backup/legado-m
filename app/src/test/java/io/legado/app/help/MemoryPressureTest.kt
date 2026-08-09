package io.legado.app.help

import android.content.ComponentCallbacks2
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class MemoryPressureTest {

    private var fakeNow = 1_000_000L

    @Before
    fun setUp() {
        MemoryPressure.availableMemoryProvider = { 4L * 1024 * 1024 }
        MemoryPressure.currentTimeProvider = { fakeNow }
        MemoryPressure.resetForTest()
    }

    @After
    fun tearDown() {
        MemoryPressure.availableMemoryProvider = null
        MemoryPressure.currentTimeProvider = null
        MemoryPressure.resetForTest()
    }

    @Test
    fun shouldTrimNow_lowAvailable_isTrue() {
        assertTrue(MemoryPressure.shouldTrimNow())
    }

    @Test
    fun shouldTrimNow_highAvailable_isFalse() {
        MemoryPressure.availableMemoryProvider = { 512L * 1024 * 1024 }
        assertFalse(MemoryPressure.shouldTrimNow())
    }

    @Test
    fun trimLevel_lowMemory_isCritical() {
        MemoryPressure.availableMemoryProvider = { 4L * 1024 * 1024 }
        assertEquals(
            ComponentCallbacks2.TRIM_MEMORY_RUNNING_CRITICAL,
            MemoryPressure.trimLevelForCurrentState()
        )
    }

    @Test
    fun throttleTrim_executes_whenNeeded() {
        var executed = 0
        MemoryPressure.throttleTrim { executed++ }
        assertEquals(1, executed)
    }

    @Test
    fun throttleTrim_skips_withinInterval() {
        var executed = 0
        MemoryPressure.throttleTrim { executed++ }
        MemoryPressure.throttleTrim { executed++ }
        assertEquals(1, executed)
    }

    @Test
    fun throttleTrim_executes_afterInterval() {
        var executed = 0
        MemoryPressure.throttleTrim { executed++ }
        fakeNow = 1_002_000L
        MemoryPressure.throttleTrim { executed++ }
        assertEquals(2, executed)
    }

    @Test
    fun throttleTrim_skips_whenMemoryAvailable() {
        MemoryPressure.availableMemoryProvider = { 512L * 1024 * 1024 }
        var executed = 0
        MemoryPressure.throttleTrim { executed++ }
        assertEquals(0, executed)
    }
}
