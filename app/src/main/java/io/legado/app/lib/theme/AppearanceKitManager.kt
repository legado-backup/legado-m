package io.legado.app.lib.theme

import io.legado.app.constant.AppLog
import io.legado.app.constant.EventBus
import io.legado.app.utils.postEvent
import java.util.concurrent.ConcurrentHashMap

/**
 * 主题外观套件管理器
 *
 * 任务：THEME-B-06（P2，用户价值 3.8）
 * 基于 Archive fork 仓库 AppearanceKit 套件架构（905 行）裁剪实现
 *
 * 核心能力：
 * - 跨组件主题套件注册与绑定
 * - 主题变更统一通知
 * - 套件状态查询
 *
 * 简化说明：本项目已有 ThemeConfig + EventBus 主题系统，本套件作为统一外观入口
 * 已知上限：未实现 Archive 的完整 905 行能力（如动态套件切换、跨进程同步）
 * 升级路径：后续可扩展套件元数据、动态切换、跨进程同步等高级能力
 */
object AppearanceKitManager {

    /** 套件注册表（套件名 -> 套件句柄） */
    private val kitRegistry = ConcurrentHashMap<String, AppearanceKit>()

    /** 套件变更监听器列表 */
    private val changeListeners = mutableListOf<AppearanceKitChangeListener>()

    /**
     * 注册主题外观套件
     *
     * @param kit 套件实例
     * @return true 表示注册成功，false 表示已存在同名套件
     */
    @Synchronized
    fun registerKit(kit: AppearanceKit): Boolean {
        val name = kit.kitName
        if (kitRegistry.containsKey(name)) {
            AppLog.put("AppearanceKitManager: kit already registered, name=$name")
            return false
        }
        kitRegistry[name] = kit
        AppLog.put("AppearanceKitManager: kit registered, name=$name")
        notifyChange(name, ChangeType.REGISTERED)
        return true
    }

    /**
     * 注销主题外观套件
     *
     * @param kitName 套件名称
     * @return true 表示注销成功
     */
    @Synchronized
    fun unregisterKit(kitName: String): Boolean {
        val removed = kitRegistry.remove(kitName)
        if (removed != null) {
            AppLog.put("AppearanceKitManager: kit unregistered, name=$kitName")
            notifyChange(kitName, ChangeType.UNREGISTERED)
            return true
        }
        return false
    }

    /**
     * 获取套件
     *
     * @param kitName 套件名称
     * @return 套件实例，不存在返回 null
     */
    fun getKit(kitName: String): AppearanceKit? {
        return kitRegistry[kitName]
    }

    /**
     * 获取所有已注册套件名称
     */
    fun getRegisteredKits(): Set<String> {
        return kitRegistry.keys.toSet()
    }

    /**
     * 应用所有套件配置（主题变更时调用）
     */
    @Synchronized
    fun applyAllKits() {
        kitRegistry.values.forEach { kit ->
            try {
                kit.onApplyAppearance()
            } catch (e: Throwable) {
                AppLog.put("AppearanceKitManager: applyAllKits failed, kit=${kit.kitName}", e)
            }
        }
        // 通过 EventBus 通知主题变更（与现有 ThemeConfig 体系一致，复用 UP_CONFIG 事件）
        postEvent(EventBus.UP_CONFIG, System.currentTimeMillis())
    }

    /**
     * 应用单个套件配置
     *
     * @param kitName 套件名称
     * @return true 表示应用成功
     */
    fun applyKit(kitName: String): Boolean {
        val kit = kitRegistry[kitName] ?: return false
        return try {
            kit.onApplyAppearance()
            notifyChange(kitName, ChangeType.APPLIED)
            true
        } catch (e: Throwable) {
            AppLog.put("AppearanceKitManager: applyKit failed, kit=$kitName", e)
            false
        }
    }

    /**
     * 添加套件变更监听器
     */
    @Synchronized
    fun addChangeListener(listener: AppearanceKitChangeListener) {
        if (!changeListeners.contains(listener)) {
            changeListeners.add(listener)
        }
    }

    /**
     * 移除套件变更监听器
     */
    @Synchronized
    fun removeChangeListener(listener: AppearanceKitChangeListener) {
        changeListeners.remove(listener)
    }

    @Synchronized
    private fun notifyChange(kitName: String, changeType: ChangeType) {
        changeListeners.forEach { listener ->
            try {
                listener.onKitChanged(kitName, changeType)
            } catch (e: Throwable) {
                AppLog.put("AppearanceKitManager: notifyChange failed, listener=$listener", e)
            }
        }
    }

    /** 套件变更类型 */
    enum class ChangeType {
        REGISTERED,
        UNREGISTERED,
        APPLIED
    }

    /** 套件变更监听器接口 */
    fun interface AppearanceKitChangeListener {
        fun onKitChanged(kitName: String, changeType: ChangeType)
    }
}
