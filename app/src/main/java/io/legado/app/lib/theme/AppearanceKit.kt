package io.legado.app.lib.theme

/**
 * 主题外观套件接口
 *
 * 任务：THEME-B-06（P2，用户价值 3.8）
 * 跨组件主题套件统一接口，由各组件实现以响应主题变更
 *
 * 简化说明：最小化接口设计，仅定义套件名和应用外观方法
 * 升级路径：后续可扩展套件元数据（版本/作者/描述）、生命周期回调等
 */
interface AppearanceKit {

    /** 套件名称（唯一标识，用于注册与查询） */
    val kitName: String

    /**
     * 应用主题外观
     *
     * 由 AppearanceKitManager 在主题变更时调用，套件实现具体的应用逻辑
     *（如更新背景色、文字颜色、图标 tint 等）
     */
    fun onApplyAppearance()
}
