package io.legado.app.constant

// 简化说明：移除 @IntDef（androidx.annotation.IntDef）Android 依赖 | 已知上限：失去编译期类型检查 | 升级路径：无
@Suppress("ConstPropertyName")
object BookSourceType {

    const val default = 0           // 0 文本
    const val audio = 1             // 1 音频
    const val image = 2            // 2 图片
    const val file = 3               // 3 只提供下载服务的网站
    const val video = 4             //4 视频

    @Target(AnnotationTarget.VALUE_PARAMETER)
    @Retention(AnnotationRetention.SOURCE)
    annotation class Type

}
