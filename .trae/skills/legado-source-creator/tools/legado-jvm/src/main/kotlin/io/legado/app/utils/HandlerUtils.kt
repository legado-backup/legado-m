package io.legado.app.utils

// 源码参照: app/src/main/java/io/legado/app/utils/HandlerUtils.kt#L17
// 简化说明: JVM 环境无主线程概念，固定返回 false | 已知上限: 无法检测主线程 | 升级路径: 无

val isMainThread: Boolean get() = false
