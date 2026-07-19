package io.legado.app.lib.theme

import android.view.View
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import io.legado.app.constant.AppLog

/**
 * 跨组件主题套件绑定机制（THEME-B-08 + THEME-E-03，P2，用户价值 3.5）。
 *
 * 任务来源：
 * - docs/specs/forks-archive-borrow-implementation/design.md L882（KitBinding.kt）
 * - analysis-task-priority.md §6 合并组 4（THEME-B-08 + THEME-E-03 合并实施）
 *
 * 核心能力：
 * - 将 AppearanceKit 绑定到 View / LifecycleOwner，实现自动应用与解绑
 * - 监听 AppearanceKitManager 变更，主题变更时自动重新应用
 * - 与 LifecycleOwner 生命周期联动，避免内存泄漏
 *
 * 与 AppearanceKitManager 的关系：
 * - AppearanceKitManager（THEME-B-06）：套件注册中心，负责注册/注销/通知
 * - KitBinding（THEME-B-08 + THEME-E-03）：将套件绑定到具体 View/Activity/Fragment，
 *   主题变更时自动触发 kit.onApplyAppearance()
 *
 * 简化说明：仅实现 View + LifecycleOwner 两种绑定方式，未实现 Fragment 单独绑定
 * 已知上限：未实现绑定池复用，每个绑定创建独立监听器
 * 升级路径：可扩展绑定池、自定义应用时机、绑定优先级
 */
object KitBinding {

    /**
     * 将套件绑定到 View（无生命周期，需手动 unbind）。
     *
     * @param kit 外观套件
     * @param view 目标 View
     * @return 绑定句柄，用于解绑
     */
    fun bind(kit: AppearanceKit, view: View): KitBindingHandle {
        val listener = AppearanceKitManager.AppearanceKitChangeListener { kitName, changeType ->
            if (kitName == kit.kitName && changeType == AppearanceKitManager.ChangeType.APPLIED) {
                applyKitSafely(kit)
            }
        }
        AppearanceKitManager.addChangeListener(listener)

        // 首次绑定立即应用
        applyKitSafely(kit)

        AppLog.putDebug("KitBinding: bind kit=${kit.kitName} to view=${view.javaClass.simpleName}")
        return KitBindingHandle(kit, listener)
    }

    /**
     * 将套件绑定到 LifecycleOwner（生命周期销毁时自动解绑）。
     *
     * @param kit 外观套件
     * @param owner LifecycleOwner（Activity/Fragment）
     * @return 绑定句柄（生命周期销毁时自动失效，也可手动 unbind 提前解绑）
     */
    fun bind(kit: AppearanceKit, owner: LifecycleOwner): KitBindingHandle {
        val listener = AppearanceKitManager.AppearanceKitChangeListener { kitName, changeType ->
            if (kitName == kit.kitName && changeType == AppearanceKitManager.ChangeType.APPLIED) {
                if (owner.lifecycle.currentState.isAtLeast(Lifecycle.State.CREATED)) {
                    applyKitSafely(kit)
                }
            }
        }
        AppearanceKitManager.addChangeListener(listener)

        // 监听生命周期销毁事件自动解绑
        owner.lifecycle.addObserver(object : androidx.lifecycle.LifecycleEventObserver {
            override fun onStateChanged(
                source: androidx.lifecycle.LifecycleOwner,
                event: Lifecycle.Event
            ) {
                if (event == Lifecycle.Event.ON_DESTROY) {
                    AppearanceKitManager.removeChangeListener(listener)
                    source.lifecycle.removeObserver(this)
                    AppLog.putDebug("KitBinding: auto unbind kit=${kit.kitName} on onDestroy")
                }
            }
        })

        // 首次绑定立即应用
        applyKitSafely(kit)

        AppLog.putDebug("KitBinding: bind kit=${kit.kitName} to owner=${owner.javaClass.simpleName}")
        return KitBindingHandle(kit, listener)
    }

    /**
     * 安全应用套件（捕获异常避免崩溃）。
     */
    private fun applyKitSafely(kit: AppearanceKit) {
        try {
            kit.onApplyAppearance()
        } catch (e: Throwable) {
            AppLog.put("KitBinding: applyKitSafely failed kit=${kit.kitName}", e)
        }
    }

    /**
     * 绑定句柄，用于手动解绑。
     */
    class KitBindingHandle(
        private val kit: AppearanceKit,
        private val listener: AppearanceKitManager.AppearanceKitChangeListener
    ) {
        /**
         * 手动解绑（移除监听器）。
         */
        fun unbind() {
            AppearanceKitManager.removeChangeListener(listener)
            AppLog.putDebug("KitBinding: unbind kit=${kit.kitName}")
        }
    }
}
