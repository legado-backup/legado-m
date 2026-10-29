package io.legado.app.help.player

/**
 * R13：听书定时「最后 30 秒音量渐弱」的纯计算部分。
 *
 * 抽成纯函数以便单测锁定契约（服务侧只负责按 [STEP_MS] 节拍取值并写入 `exoPlayer.volume`）：
 * - 定时递减到 `timeMinute == 1` 时开始渐弱，再经 30 秒降到 0，正好与 `timeMinute == 0` 的停止点对齐；
 * - 任何暂停/取消定时/停止/切集都会立即取消并恢复 `volume = 1f`（见 AudioPlayService）。
 */
object AudioTimerFade {

    /** 渐弱总时长：最后 30 秒 */
    const val DURATION_MS = 30_000L

    /** 音量下发节拍（200ms 一次，足够平滑且不至于过度占用主线程） */
    const val STEP_MS = 200L

    /**
     * 渐弱音量曲线：线性下降，起点 1.0、终点 0.0；越界按端点钳制（防止恢复瞬间跳变）。
     *
     * @param elapsedMs 已渐弱的毫秒数（负数按 0 处理）
     */
    fun volumeAt(elapsedMs: Long): Float {
        if (elapsedMs <= 0L) return 1f
        if (elapsedMs >= DURATION_MS) return 0f
        return 1f - elapsedMs.toFloat() / DURATION_MS.toFloat()
    }
}
