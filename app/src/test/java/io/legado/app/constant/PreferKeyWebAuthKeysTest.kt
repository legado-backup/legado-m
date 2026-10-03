package io.legado.app.constant

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.lang.reflect.Modifier

/**
 * Web 鉴权 6 键单测（一期 · 0.4 / design §1.2.1）。
 *
 * 守两条不变量：
 * 1. 6 个键**存在且取值唯一**（键值重复会让两处配置互相覆盖）；
 * 2. 新键的取值**不与既有任何键冲突**（历史铁证：键值撞车导致配置漂移）。
 */
class PreferKeyWebAuthKeysTest {

    /** 反射取出本 object 全部 `const val ... : String` 的 (字段名, 取值)。 */
    private fun allStringKeys(): List<Pair<String, String>> =
        PreferKey::class.java.declaredFields
            .filter {
                it.type == String::class.java && Modifier.isStatic(it.modifiers)
            }
            .map {
                it.isAccessible = true
                it.name to (it.get(null) as String)
            }

    private val webAuthFieldNames = listOf(
        "webTokenReadonly",
        "webTokenManage",
        "webTokenAdmin",
        "webTokenGeneratedAt",
        "webAuthStrict",
        "webServiceFirstLaunchDone"
    )

    @Test
    fun sixWebAuthKeys_exist() {
        val names = allStringKeys().map { it.first }
        webAuthFieldNames.forEach { field ->
            assertTrue("缺少键字段：$field", names.contains(field))
        }
    }

    @Test
    fun sixWebAuthKeyValues_areDistinct() {
        val values = allStringKeys()
            .filter { webAuthFieldNames.contains(it.first) }
            .map { it.second }
        assertEquals("6 个新键须全部取到", 6, values.size)
        assertEquals("6 个新键取值不得重复", values.size, values.distinct().size)
    }

    @Test
    fun webAuthKeyValues_doNotCollideWithOtherKeys() {
        val all = allStringKeys()
        val newValues = all.filter { webAuthFieldNames.contains(it.first) }.map { it.second }
        val others = all.filterNot { webAuthFieldNames.contains(it.first) }
        newValues.forEach { value ->
            val collided = others.filter { it.second == value }
            assertTrue(
                "新键取值 \u0022$value\u0022 与既有键冲突：${collided.map { it.first }}",
                collided.isEmpty()
            )
        }
    }

    @Test
    fun webAuthKeyValues_followCamelCaseNaming() {
        allStringKeys()
            .filter { webAuthFieldNames.contains(it.first) }
            .forEach { (field, value) ->
                assertEquals("键值约定=字段名同名 camelCase：$field", field, value)
            }
    }
}
