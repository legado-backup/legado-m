package io.legado.app.data.dao

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源 DAO 的 JS 源查询 API（ng-js-source-port）。
 *
 * 两个查询是「不整行加载就能判定/取脚本」的最小面：
 * 签名一变，MCP/巡检/脚本编辑都会编译失败，故用反射锁住存在性与返回类型。
 */
class BookSourceDaoJsQueryTest {

    @Test
    fun getMainJs_existsAndReturnsString() {
        val method = BookSourceDao::class.java.methods.firstOrNull { it.name == "getMainJs" }
        requireNotNull(method) { "缺少 getMainJs（脚本读取唯一入口）" }
        assertEquals(String::class.java, method.returnType)
        assertEquals(1, method.parameterCount)
    }

    @Test
    fun hasJsSource_existsAndReturnsBoolean() {
        val method = BookSourceDao::class.java.methods.firstOrNull { it.name == "hasJsSource" }
        requireNotNull(method) { "缺少 hasJsSource（巡检/统计判定入口）" }
        assertTrue(
            method.returnType == Boolean::class.java || method.returnType == java.lang.Boolean::class.java
        )
    }
}
