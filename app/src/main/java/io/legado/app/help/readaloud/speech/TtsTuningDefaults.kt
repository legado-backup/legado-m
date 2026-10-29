package io.legado.app.help.readaloud.speech

import android.content.Context
import io.legado.app.constant.AppLog
import io.legado.app.constant.IntentAction
import io.legado.app.constant.PreferKey
import io.legado.app.help.config.AppConfig
import io.legado.app.help.readaloud.ReadAloudSpeakerLoudnessManager
import io.legado.app.service.BaseReadAloudService
import io.legado.app.utils.startService

/**
 * R5：朗读「可折腾参数」一键恢复默认（AD-08 白名单语义）。
 *
 * 只重置**数值/策略**项：
 * - 全局语速 `ttsSpeechRate`、跟随系统 `ttsFollowSys`、段间停顿 `ttsParagraphPauseMs`；
 * - 引擎级 `ttsEngineParamsJson`（各引擎 speechRate/pitch/volume）；
 * - 响度均衡三项 + 已学习的响度统计。
 *
 * **永久排除（资产/身份/用户意图）**：`ttsEngine`、HttpTTS 实体（密钥/请求头/音色）、
 * 发言人分组、角色配音路由、`ttsCastingActiveId`、悬浮窗外观、以及
 * `ttsTimer/ttsTimerMode/ttsTimerChapters`（定时关闭属用户意图，重置会误关定时）。
 *
 * 朗读进行中重置：只更新偏好并走既有 `reInitTts` 热重建，不改播放队列与当前句。
 */
object TtsTuningDefaults {

    /** 响度均衡默认值（与 AppConfig 的 getPrefInt 默认值同源，禁止各自写死漂移） */
    const val DEFAULT_TARGET_VOICE_VOLUME = 100
    const val DEFAULT_MAX_SPEAKER_GAIN = 135
    const val DEFAULT_NARRATOR_BASE_GAIN = 110

    /** 重置白名单（数值/策略项）；与 [protectedPreferenceKeys] 必须零交集（单测锁定） */
    val resetPreferenceKeys: Set<String> = setOf(
        PreferKey.ttsSpeechRate,
        PreferKey.ttsFollowSys,
        PreferKey.ttsParagraphPauseMs,
        PreferKey.ttsEngineParamsJson,
        PreferKey.readAloudTargetVoiceVolume,
        PreferKey.readAloudMaxSpeakerGain,
        PreferKey.readAloudNarratorBaseGain,
        PreferKey.readAloudSpeakerLoudnessStats
    )

    /** 永久排除（资产/身份/用户意图），任何情况不得被重置 */
    val protectedPreferenceKeys: Set<String> = setOf(
        PreferKey.ttsEngine,
        PreferKey.ttsCastingActiveId,
        PreferKey.ttsTimer,
        PreferKey.ttsTimerMode,
        PreferKey.ttsTimerChapters
    )

    fun reset(context: Context) {
        kotlin.runCatching {
            AppConfig.ttsSpeechRate = AppConfig.defaultSpeechRate
            AppConfig.ttsFlowSys = true
            AppConfig.ttsParagraphPauseMs = 0
            AppConfig.readAloudTargetVoiceVolume = DEFAULT_TARGET_VOICE_VOLUME
            AppConfig.readAloudMaxSpeakerGain = DEFAULT_MAX_SPEAKER_GAIN
            AppConfig.readAloudNarratorBaseGain = DEFAULT_NARRATOR_BASE_GAIN
            // 引擎级参数：整表清空即回到 speechRate/pitch/volume = 1.0（含内存缓存）
            TtsEngineParamsStore.clearAll()
            // 已学习的响度统计缓存一并清空
            ReadAloudSpeakerLoudnessManager.reset()
            if (BaseReadAloudService.isRun) {
                context.startService<BaseReadAloudService> {
                    action = IntentAction.reInitTts
                }
            }
            AppLog.put("TtsTuningDefaults: 朗读参数已恢复默认")
        }.onFailure {
            AppLog.put("TtsTuningDefaults 重置失败: ${it.localizedMessage}")
        }
    }
}
