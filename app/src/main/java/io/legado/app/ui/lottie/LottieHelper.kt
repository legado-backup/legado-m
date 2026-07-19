package io.legado.app.ui.lottie

import android.view.View
import com.airbnb.lottie.LottieAnimationView
import io.legado.app.constant.AppLog

/**
 * lottie 动画工具类（DEPS-B-08，P2，用户价值 3.5）。
 *
 * 任务来源：docs/specs/forks-archive-borrow-implementation/design.md L916
 *
 * 核心能力：
 * - 提供 lottie 加载动画的统一应用入口
 * - 支持任意 View 树中查找 LottieAnimationView 并播放/停止
 * - 包装常见异常避免崩溃
 *
 * 简化说明：仅提供基础播放/停止 API，未实现动画缓存与复用
 * 已知上限：未实现动画复用池，每次播放都从 raw 资源加载
 * 升级路径：可扩展动画缓存、自定义动画路径、性能监控
 */
object LottieHelper {

    /** 默认加载动画资源名（res/raw/lottie_loading.json） */
    private const val DEFAULT_LOADING_ANIMATION = "lottie_loading.json"

    /**
     * 在指定 LottieAnimationView 上播放加载动画。
     *
     * @param lottieView LottieAnimationView 实例
     * @param animationName 动画资源名（位于 res/raw/ 下，不含扩展名），null 使用默认加载动画
     * @return true 表示播放成功
     */
    fun playLoading(
        lottieView: LottieAnimationView,
        animationName: String? = null
    ): Boolean {
        return try {
            val name = animationName ?: DEFAULT_LOADING_ANIMATION
            lottieView.setAnimation(name)
            lottieView.repeatCount = -1 // 无限循环
            lottieView.visibility = View.VISIBLE
            lottieView.playAnimation()
            AppLog.putDebug("LottieHelper: playLoading animation=$name")
            true
        } catch (e: Throwable) {
            AppLog.put("LottieHelper: playLoading failed", e)
            false
        }
    }

    /**
     * 停止指定 LottieAnimationView 上的动画并隐藏。
     *
     * @param lottieView LottieAnimationView 实例
     */
    fun stopLoading(lottieView: LottieAnimationView) {
        try {
            if (lottieView.isAnimating) {
                lottieView.cancelAnimation()
            }
            lottieView.visibility = View.GONE
            AppLog.putDebug("LottieHelper: stopLoading")
        } catch (e: Throwable) {
            AppLog.put("LottieHelper: stopLoading failed", e)
        }
    }

    /**
     * 检查 Lottie 动画是否正在播放。
     */
    fun isPlaying(lottieView: LottieAnimationView): Boolean {
        return try {
            lottieView.isAnimating
        } catch (e: Throwable) {
            false
        }
    }
}
