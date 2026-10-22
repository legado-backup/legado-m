package io.legado.app.model.jsSource

import io.legado.app.data.entities.BookSource

/**
 * 单文件 JavaScript 书源与声明式 JSON 书源共用 [BookSource] 实体。
 * 这里使用扩展函数，避免给 Rhino 可达的宿主对象新增公开实例方法。
 */
fun BookSource.isJsSource(): Boolean = !mainJs.isNullOrBlank()

/**
 * 书源是否具备搜索能力：声明式 `searchUrl` 或单文件 JS 的 `search` 函数。
 *
 * 调用点必须用本判据而非 `searchUrl.isNullOrBlank()` —— 否则 JS 源会被误判为
 * 「无搜索」：换源候选、跨源搜书、质检评分模板、发现页搜索入口都会漏掉它们。
 */
fun BookSource.hasSearchCapability(): Boolean =
    !searchUrl.isNullOrBlank() || isJsSource()

/**
 * 图片 click 脚本的延迟哨兵：声明式 click 脚本作用域看不到 `mainJs`，
 * 返回该值表示「交给单文件脚本顶层 `onImageClick` 处理」（与 NG 协议一致）。
 */
const val MAIN_JS_IMAGE_CLICK_DEFERRED = "__legado_main_js_image_click_deferred__"

/** 该 click 结果是否应转交 `onImageClick`（仅 JS 源生效，老源恒 false）。 */
fun BookSource.shouldDeferImageClick(result: Any?): Boolean =
    result?.toString() == MAIN_JS_IMAGE_CLICK_DEFERRED && isJsSource()
