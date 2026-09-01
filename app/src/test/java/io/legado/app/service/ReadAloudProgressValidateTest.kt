package io.legado.app.service

import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.Assert.fail

/**
 * C1 朗读原语化：ReadAloudProgress init 边界校验（分册 §8.1 ReadAloudProgressValidateTest）。
 * 其余分册用例（ShouldFollowAloudAdvance/Generation/EMA/预测）依赖 Android 运行时
 * （ReadBook/LiveBus/TextChapter），归 L2 真机验证（l2_verify_aloud_primitives.py 待补）。
 */
class ReadAloudProgressValidateTest {

    @Test
    fun paragraph_valid_construction() {
        val p = ReadAloudProgress(0, 0, 1, ReadAloudProgress.Kind.PARAGRAPH)
        assertTrue(p.position == 0 && p.total == 1)
    }

    @Test
    fun paragraph_outOfRange_throws() {
        try {
            ReadAloudProgress(0, 5, 5, ReadAloudProgress.Kind.PARAGRAPH)
            fail("position == total must throw for PARAGRAPH")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message.orEmpty().contains("paragraph position"))
        }
    }

    @Test
    fun paragraph_negativeIndex_throws() {
        try {
            ReadAloudProgress(-1, 0, 1, ReadAloudProgress.Kind.PARAGRAPH)
            fail("negative chapterIndex must throw")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message.orEmpty().contains("chapterIndex"))
        }
    }

    @Test
    fun time_allowsEqualTotal() {
        val p = ReadAloudProgress(3, 100, 100, ReadAloudProgress.Kind.TIME)
        assertTrue(p.position == p.total)
    }

    @Test
    fun time_outOfRange_throws() {
        try {
            ReadAloudProgress(0, 101, 100, ReadAloudProgress.Kind.TIME)
            fail("position > total must throw for TIME")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message.orEmpty().contains("time position"))
        }
    }

    @Test
    fun zeroTotal_throws() {
        try {
            ReadAloudProgress(0, 0, 0, ReadAloudProgress.Kind.PARAGRAPH)
            fail("total == 0 must throw")
        } catch (expected: IllegalArgumentException) {
            assertTrue(expected.message.orEmpty().contains("total"))
        }
    }
}
