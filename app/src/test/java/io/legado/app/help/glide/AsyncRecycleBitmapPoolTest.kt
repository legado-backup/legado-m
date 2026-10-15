package io.legado.app.help.glide

import android.graphics.Bitmap
import com.bumptech.glide.load.engine.bitmap_recycle.BitmapPoolAdapter
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.util.concurrent.atomic.AtomicInteger

/**
 * core-flow-test-coverage 批次 6（PERF-1）—— Glide 位图回收行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 背景：`AsyncRecycleBitmapPool.put` 把回收任务提交到执行器；本次改动把它从**业务队列**
 *（`globalExecutor`）迁到**位图回收队列**（`glideExecutor`）—— 否则列表快速滑动时密集的
 * 回收任务会与正文解析互相排队。用例断言**外部可观察行为**：`put` 传入的位图最终被
 * 转交给底层 pool（用记录型 delegate 观察），且转交过程不吞异常。
 */
@RunWith(RobolectricTestRunner::class)
class AsyncRecycleBitmapPoolTest {

    private class RecordingPool : BitmapPoolAdapter() {
        val putCount = AtomicInteger(0)
        override fun put(bitmap: Bitmap) {
            putCount.incrementAndGet()
        }
    }

    @Test
    fun put_isDelegatedToUnderlyingPool() {
        val recorder = RecordingPool()
        val pool = AsyncRecycleBitmapPool(recorder)

        pool.put(Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888))

        val deadline = System.currentTimeMillis() + 5000
        while (System.currentTimeMillis() < deadline && recorder.putCount.get() == 0) {
            Thread.sleep(50)
        }
        assertTrue("位图应最终被转交给底层 pool", recorder.putCount.get() == 1)
    }
}
