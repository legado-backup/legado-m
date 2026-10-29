// 来源：LegadoS（github.com/Sun-QAQ/legado，GPL-3.0 同源 fork）眼动翻页实现。
// 移植：仅调整包路径与 M 侧接线（ReadBookActivity / 阅读菜单 / 配置），判定逻辑逐字保留。
// 详见 docs/specs/batch-20261029-reader-core/design.md §1.1。

package io.legado.app.ui.book.read.eye

/** Worker-only inference pacing. Periodic probes allow tracking to resume automatically. */
internal class GazeProcessingCadence {
    var intervalMs = 100L
        private set
    private var lastFrame: Long? = null
    private var missingSince: Long? = null

    fun shouldProcess(now: Long): Boolean {
        if (lastFrame?.let { now - it < intervalMs } == true) return false
        lastFrame = now
        return true
    }

    fun onObservation(hasGaze: Boolean, now: Long) {
        if (hasGaze) {
            missingSince = null
            intervalMs = 100L
        } else {
            val since = missingSince ?: now.also { missingSince = it }
            // A normal blink or brief tracking failure must not slow down gestures.
            intervalMs = if (now - since >= 3000L) 500L else 100L
        }
    }
}
