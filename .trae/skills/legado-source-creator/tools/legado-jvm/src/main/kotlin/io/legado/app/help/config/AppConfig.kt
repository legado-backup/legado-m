package io.legado.app.help.config

// 源码参照: app/src/main/java/io/legado/app/help/config/AppConfig.kt
// 简化说明: AppConfig Stub，isCronet 固定 false，userAgent 固定值 | 已知上限: 无配置持久化 | 升级路径: 从配置文件读取

object AppConfig {
    val isCronet: Boolean = false
    var userAgent: String = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}
