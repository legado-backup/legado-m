package io.legado.app.model

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.mozilla.javascript.Context
import org.mozilla.javascript.Scriptable

/**
 * B2 · R11「Rhino 返回值 JSON 兼容化」单测。
 *
 * 用**真实 Rhino 对象**（`org.mozilla.javascript` 在单测类路径可用）验证三件事：
 * ①`NativeArray` 不能再退化成 `{"0":…}`（数组语义必须保留）
 * ②自引用（循环引用）必须断链为 `null` 而不是抛栈溢出/被吞掉
 * ③`null`、普通字符串、嵌套结构往返正常，且 Rhino 内部键（`__proto__`）被剔除
 */
class AutoTaskJsonCompatTest {

    private val gson = Gson()

    private fun <T> withRhino(block: (Context, Scriptable) -> T): T {
        val cx = Context.enter()
        try {
            return block(cx, cx.initStandardObjects())
        } finally {
            Context.exit()
        }
    }

    @Test
    fun nativeArray_keepsArraySemantics() {
        withRhino { cx, scope ->
            val arr = cx.newArray(scope, arrayOf<Any>(1, "two", true))
            val out = toJsonCompatible(arr)
            assertTrue("NativeArray 必须转成 List，实际=${out?.javaClass?.simpleName}", out is List<*>)
            assertEquals(3, (out as List<*>).size)

            val json = gson.toJson(out)
            assertTrue("序列化结果必须是 JSON 数组，实际=$json", json.startsWith("[") && json.endsWith("]"))
            assertFalse("不得退化成对象形式（丢数组语义）：$json", json.contains("\"0\""))
        }
    }

    @Test
    fun nativeObject_becomesStringKeyedMap_withNestedStructures() {
        withRhino { cx, scope ->
            val child = cx.newObject(scope)
            child.put("name", child, "c1")
            val root = cx.newObject(scope)
            root.put("type", root, "refreshToc")
            root.put("child", root, child)
            root.put("list", root, cx.newArray(scope, arrayOf<Any>("x", "y")))

            val out = toJsonCompatible(root) as Map<*, *>
            assertEquals("refreshToc", out["type"])
            assertEquals("c1", (out["child"] as Map<*, *>)["name"])
            assertEquals(2, (out["list"] as List<*>).size)

            val json = gson.toJson(out)
            assertTrue("嵌套结构应可正常序列化，实际=$json", json.contains("\"refreshToc\""))
        }
    }

    @Test
    fun cyclicReference_isCutToNullWithoutCrash() {
        withRhino { cx, scope ->
            val obj = cx.newObject(scope)
            obj.put("type", obj, "notify")
            obj.put("self", obj, obj)

            val out = toJsonCompatible(obj) as Map<*, *>
            assertEquals("notify", out["type"])
            assertNull("自引用必须断链为 null（防栈溢出）", out["self"])

            // 共享（非循环）引用不受影响：同一对象被两处引用时均应正常展开
            val shared = cx.newObject(scope)
            shared.put("v", shared, 1)
            val holder = cx.newObject(scope)
            holder.put("a", holder, shared)
            holder.put("b", holder, shared)
            val holderOut = toJsonCompatible(holder) as Map<*, *>
            assertEquals(1, (holderOut["a"] as Map<*, *>)["v"])
            assertEquals(1, (holderOut["b"] as Map<*, *>)["v"])
        }
    }

    @Test
    fun nullPlainStringAndInternalKeys() {
        assertNull(toJsonCompatible(null))
        assertEquals("hello", toJsonCompatible("hello"))
        assertEquals(42, toJsonCompatible(42))
        assertEquals(true, toJsonCompatible(true))

        withRhino { cx, scope ->
            val obj = cx.newObject(scope)
            obj.put("type", obj, "notify")
            obj.put("__proto__", obj, "should-be-removed")
            val out = toJsonCompatible(obj) as Map<*, *>
            assertFalse("Rhino 内部键必须剔除", out.containsKey("__proto__"))
            assertEquals("notify", out["type"])
        }
    }
}