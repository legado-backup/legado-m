package io.legado.app.model.jsSource

import io.legado.app.data.entities.BookSource

/**
 * 单文件 JavaScript 书源与声明式 JSON 书源共用 [BookSource] 实体。
 * 这里使用扩展函数，避免给 Rhino 可达的宿主对象新增公开实例方法。
 */
fun BookSource.isJsSource(): Boolean = !mainJs.isNullOrBlank()

/**
 * 图片 click 脚本的延迟哨兵：声明式 click 脚本作用域看不到 `mainJs`，
 * 返回该值表示「交给单文件脚本顶层 `onImageClick` 处理」（与 NG 协议一致）。
 */
const val MAIN_JS_IMAGE_CLICK_DEFERRED = "__legado_main_js_image_click_deferred__"

/** 该 click 结果是否应转交 `onImageClick`（仅 JS 源生效，老源恒 false）。 */
fun BookSource.shouldDeferImageClick(result: Any?): Boolean =
    result?.toString() == MAIN_JS_IMAGE_CLICK_DEFERRED && isJsSource()
