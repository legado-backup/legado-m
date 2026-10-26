package io.legado.app.model

import io.legado.app.constant.BookSourceType

/**
 * 视频类书源「正文/取流」调试结论的可读化（design AD-02 · A-2 / spec Requirement A-2 / A-5）。
 *
 * 背景：`Debug.startDebug` 原按 **key 形态**分发，不区分源类型 ⇒ 视频源调 content 时，
 * 「成功返回播放页地址」「判定为额度外（越权集）」「取流不可用」三种结果在日志里长得一样
 * （都只是「正文页解析完成」或一句异常），用户无法据此判断到底卡在哪一步。
 *
 * 本对象把「取流返回文本」映射成**三态可读结论**，纯函数、无 Android 依赖，便于单测锁定：
 *  - [Outcome.PLAY_URL]：拿到了可播放地址（或视频源约定的播放页地址）；
 *  - [Outcome.BROWSER_ONLY]：未返回地址且源选择了「内置浏览器播放」⇒ 由页面自身取流；
 *  - [Outcome.UNAVAILABLE]：未拿到地址且非浏览器模式 ⇒ 取流不可用（需给出可读原因）。
 */
object DebugVideoConclusion {

    /** 三种结论。 */
    enum class Outcome { PLAY_URL, BROWSER_ONLY, UNAVAILABLE }

    /** 结论 + 面向用户的说明（日志/调试页直接展示）。 */
    data class Conclusion(val outcome: Outcome, val message: String)

    /**
     * 判定取流结论。
     *
     * @param sourceType 书源类型（仅 [BookSourceType.video] 走视频语义）
     * @param contentText 正文/取流链路返回的文本
     * @param browserMode 源是否处于「内置浏览器播放」模式（每集由网页播放器自行取流）
     */
    fun of(sourceType: Int, contentText: String?, browserMode: Boolean): Conclusion {
        val text = contentText.orEmpty().trim()
        val hasUrl = text.startsWith("http://") || text.startsWith("https://")
        if (sourceType != BookSourceType.video) {
            // 非视频源保持原语义：只要有内容即视为解析成功（不引入新判定）
            return if (text.isNotEmpty()) {
                Conclusion(Outcome.PLAY_URL, "解析完成")
            } else {
                Conclusion(Outcome.UNAVAILABLE, "解析结果为空")
            }
        }
        return when {
            hasUrl -> Conclusion(
                Outcome.PLAY_URL,
                "取流成功：已取得可播放地址（调试结论可与真机试播对照，见「在播放器中试播」）"
            )

            browserMode -> Conclusion(
                Outcome.BROWSER_ONLY,
                "交内置浏览器播放：本链路不返回地址（取流由网页播放器完成），请在内置浏览器中观看"
            )

            else -> Conclusion(
                Outcome.UNAVAILABLE,
                "取流不可用：未返回可播放地址。常见原因：本集超出免费额度（站点要求登录/改用 App）、" +
                    "站点取流需页面环境（可切换到「内置浏览器播放」再试）"
            )
        }
    }

    /** 仅判定结果（供单测/日志分类使用）。 */
    fun outcomeOf(sourceType: Int, contentText: String?, browserMode: Boolean): Outcome =
        of(sourceType, contentText, browserMode).outcome

    /**
     * 从源变量串取 `playmode` 的值（缺失 ⇒ 空串）。纯函数，供内核与调试页共用同一解析口径。
     *
     * 源变量形态为 `k=v;k2=v2`（也兼容 `&` 与换行分隔）。
     */
    fun playModeOf(variable: String?): String =
        variable.orEmpty()
            .split(';', '&', '\n')
            .asSequence()
            .map { it.trim() }
            .firstOrNull { it.startsWith("playmode=") }
            ?.substringAfter('=')
            ?.trim()
            .orEmpty()

    /**
     * 视频源**正文为空**时的追加提示（空串 ⇒ 非视频源，调用方不追加）。
     *
     * 为什么需要（2026-10-26 真机实测）：浏览器播放模式下 `getContent` **按设计返回空串**
     * （取流交给网页播放器），但 MCP `source_content_test` 只报「内容为空 ⇒ 正文规则解析失败」
     * ⇒ 用户/AI 会把"预期内的空正文"误读成规则错误。此处把两种成因分开说清。
     */
    fun emptyContentHint(sourceType: Int, variable: String?): String {
        if (sourceType != BookSourceType.video) return ""
        return if (playModeOf(variable) == "browser") {
            "内置浏览器播放模式下正文为空属预期：播放已交由浏览器页完成（若要嗅探取流请切回播放器模式）"
        } else {
            "未提取到可播放地址：本集可能超出免费额度（需网页登录）或站点要求页面环境（可切「内置浏览器播放」再试）"
        }
    }
}
