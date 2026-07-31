# Rhino 兼容性速查表

> Legado 使用 Rhino 1.8.1 作为规则 JS 引擎（非 V8/Node.js）。本表汇总 ES5 支持语法、ES6+ 不支持语法、替代写法与类型转换陷阱，创建/优化书源时务必对照。
>
> 相关文档：
> - 陷阱详解见 `../troubleshooting/rhino-js-traps.md`
> - JS 执行环境差异见 `./js-env-diff.md`
> - 加密相关陷阱见 `../troubleshooting/crypto-traps.md`

---

## 1. ES5 支持的语法清单

> Rhino 1.8.1 + `Context.VERSION_ES6` 配置下，以下 ES5 及更早语法可正常使用。

| 类别 | 支持语法 | 示例 |
|------|---------|------|
| 变量声明 | `var` | `var x = 1;` |
| 函数声明 | `function` | `function foo(a) { return a; }` |
| 函数表达式 | `var f = function() {}` | `var fn = function(x) { return x * 2; };` |
| 正则字面量 | `/pattern/flags`（ES3 基本特性） | `/(\d+)\.(\d+)/.exec("1.2")` |
| 基本运算 | 算术/比较/逻辑/位运算 | `a + b`, `a === b`, `a && b`, `a \| b` |
| `for` 循环 | 经典 `for` | `for (var i = 0; i < n; i++) { ... }` |
| `while` 循环 | `while` / `do...while` | `while (i < n) { i++; }` |
| `if-else` | 条件分支 | `if (a > 0) { ... } else { ... }` |
| `switch` | 多分支 | `switch (x) { case 1: ...; break; }` |
| `try-catch` | 异常捕获（单 catch 子句） | `try { ... } catch (e) { ... }` |
| `Math` 对象 | `Math.floor/round/max/min/...` | `Math.floor(a / b)` |
| `JSON` 对象 | `JSON.parse` / `JSON.stringify` | `JSON.parse(java.ajax(url))` |
| `String` 方法 | `indexOf/slice/substring/replace/split/charAt` | `s.indexOf("x") > -1` |
| `Array` 方法 | `push/pop/shift/unshift/slice/concat/join/sort` | `arr.push(item)` |
| `Object` 方法 | `keys/values`（ES5+） | `Object.keys(obj)` |
| `Date` 对象 | `new Date()` / `getTime()` | `new Date().getTime()` |
| `parseInt/parseFloat` | 全局转换函数 | `parseInt("12", 10)` |
| `typeof / instanceof` | 类型判断 | `typeof x === "string"` |

**注意**：Rhino 的 `try-catch` 仅支持单个 catch 参数，不支持 ES2019 的 `catch {}` 省略参数语法（需写 `catch (e)`）。

---

## 2. ES6+ 不支持的语法清单

> 以下语法在 Rhino 1.8.1 中**不可用**或行为不可靠，创建书源时禁止使用。

| 语法 | ES 版本 | Rhino 1.8.1 表现 | 说明 |
|------|---------|------------------|------|
| `let` | ES6 | ❌ 不可靠 | 部分场景报错或作用域异常，统一用 `var` |
| `const` | ES6 | ❌ 不可靠 | 同上 |
| 箭头函数 `=>` | ES6 | ❌ SyntaxError | 用 `function() {}` |
| 模板字符串 `` `...${var}` `` | ES6 | ❌ SyntaxError | 用字符串拼接 `+` |
| `padStart` / `padEnd` | ES2017 | ❌ TypeError | 手动补零 |
| `String.includes` | ES6 | ❌ TypeError | 用 `indexOf > -1` |
| `String.startsWith` | ES6 | ❌ TypeError | 用 `indexOf === 0` |
| `String.endsWith` | ES6 | ❌ TypeError | 用 `indexOf(suffix, str.length - suffix.length) > -1` |
| `Array.includes` | ES7 | ❌ TypeError | 用 `indexOf > -1` |
| `Promise` | ES6 | ❌ 不可用 | 用同步调用（Rhino 无事件循环） |
| `async / await` | ES2017 | ❌ 不可用 | 用同步调用 |
| 解构赋值 | ES6 | ❌ SyntaxError | 逐个赋值 |
| 扩展运算符 `...` | ES6 | ❌ SyntaxError | 用 `concat()` 或循环 |
| `for...of` | ES6 | ❌ 不可靠 | 用经典 `for` 循环 |
| `for...in` | ES5 | ⚠️ 可用但语义为遍历键名 | 遍历数组用经典 `for` 更安全 |
| `Map` / `Set` | ES6 | ❌ 不可用 | 用普通 Object / Array 替代 |
| `Symbol` | ES6 | ❌ 不可用 | 无替代方案 |
| 默认参数 `function(a=1)` | ES6 | ❌ 不可靠 | 用 `a = a \|\| 1` |
| 命名捕获组 `(?<name>)` | ES2018 | ❌ SyntaxError | 用普通捕获组 `(...)` |
| 后行断言 `(?<=...)` | ES2018 | ❌ SyntaxError | 改用正向逻辑 |
| Unicode 属性 `\p{...}` + `/u` | ES2018 | ❌ 无效标志 | 用字符类替代 |

---

## 3. 替代写法对照表

| ES6+ 写法 | Rhino 兼容替代写法 |
|-----------|-------------------|
| `arr.includes(x)` | `arr.indexOf(x) > -1` |
| `str.includes(sub)` | `str.indexOf(sub) > -1` |
| `str.startsWith(prefix)` | `str.indexOf(prefix) === 0` |
| `str.endsWith(suffix)` | `str.indexOf(suffix, str.length - suffix.length) > -1` |
| `str.padStart(2, '0')` | `if (mm < 10) mm = '0' + mm;` |
| `` `Hello ${name}` `` | `'Hello ' + name` |
| `(x) => x + 1` | `function(x) { return x + 1; }` |
| `let x = 1` | `var x = 1` |
| `const y = 2` | `var y = 2` |
| `for (var item of arr)` | `for (var i = 0; i < arr.length; i++) { var item = arr[i]; }` |
| `var {a, b} = obj` | `var a = obj.a; var b = obj.b;` |
| `var [a, b] = arr` | `var a = arr[0]; var b = arr[1];` |
| `[...arr1, ...arr2]` | `arr1.concat(arr2)` |
| `fn(...args)` | `fn.apply(null, args)` |
| `Array.from(arrLike)` | `var arr = []; for (var i = 0; i < arrLike.length; i++) arr.push(arrLike[i]);` |
| `new Map()` | `var map = {}; map[key] = value;` |
| `new Set()` | `var set = {}; set[key] = true;` |
| `Object.values(obj)` | `var v = []; for (var k in obj) v.push(obj[k]);` |
| `Object.entries(obj)` | `var e = []; for (var k in obj) e.push([k, obj[k]]);` |

---

## 4. 类型转换陷阱

> ⚠️ 这是 Rhino 环境最隐蔽的一类陷阱：Java 对象与 JS 原生对象交互时类型不匹配，导致 `.length`、`===`、数组方法等行为异常。

### 4.1 `java.ajax()` 返回值是 Java 字符串

```javascript
// ❌ 错误：ajax 返回 java.lang.String，不是 JS 原生 string
var html = java.ajax(url);
if (html.length > 100) { ... }   // html.length 是方法引用，不是数字！
if (html.charAt(0) === '<') { ... } // html.charAt(0) 返回 Java char，=== '<' 失败！

// ✅ 正确：用 String() 显式转换为 JS 原生字符串
var html = String(java.ajax(url));
if (html.length > 100) { ... }    // 现在是数字
if (html.charAt(0) === '<') { ... } // 现在是 JS 字符串比较
```

**铁律**：凡是从 `java.ajax()`、`java.connect()`、`java.get/post()` 等返回的字符串，第一步必须 `String(...)` 转换。

### 4.2 `.length` 属性陷阱

| 调用方式 | 返回值 | 说明 |
|----------|--------|------|
| `java.ajax(url).length` | Java 方法引用（非数字） | 不能直接用于比较/运算 |
| `String(java.ajax(url)).length` | 数字 | 正确用法 |
| `javaString.length()` | 数字（Java 方法调用） | Java 风格调用，可用但不推荐 |

**示例**：
```javascript
var raw = java.ajax(url);
if (raw.length > 0) { ... }      // ❌ 永远为真（方法引用是 truthy）
var js = String(raw);
if (js.length > 0) { ... }       // ✅ 正确判断
```

### 4.3 `.charAt(i)` 与 `===` 比较陷阱

```javascript
var raw = java.ajax(url);
// ❌ raw.charAt(0) 返回 Java char 对象，与 JS 字符串 '<' 严格相等比较失败
if (raw.charAt(0) === '<') { ... }

var js = String(raw);
// ✅ 转换后 charAt 返回 JS 字符串，=== 比较正常
if (js.charAt(0) === '<') { ... }
```

### 4.4 NativeArray 实现 Java List

`NativeArray`（Rhino 的 JS 数组实现）同时实现了 `java.util.List`，但**部分 JS 数组方法不可用或行为异常**：

| 操作 | 是否可用 | 说明 |
|------|---------|------|
| `arr[i]` 索引访问 | ✅ | 正常 |
| `arr.length` | ✅ | 返回数字 |
| `arr.push()` / `pop()` | ✅ | 正常 |
| `arr.slice()` / `concat()` | ✅ | 正常 |
| `arr.indexOf()` | ✅ | 正常 |
| `arr.forEach()` | ⚠️ 部分场景 | 优先用经典 `for` 循环 |
| `arr.map()` / `filter()` | ⚠️ 部分场景 | 优先用经典 `for` 循环 |
| 作为 `java.util.List` 传给 Java 方法 | ✅ | 可被 Java 端识别 |

**建议**：在规则 JS 中处理数组，优先使用经典 `for` 循环，避免依赖高阶数组方法。

### 4.5 NativeObject 属性访问

`NativeObject`（Rhino 的 JS 对象实现）属性访问方式：

```javascript
var obj = { a: 1, b: "2" };

// ✅ 点号访问（推荐）
var x = obj.a;

// ✅ 方括号访问（动态键名时使用）
var key = "a";
var y = obj[key];

// ⚠️ 遍历键名用 for...in（注意 hasOwnProperty 检查）
for (var k in obj) {
    if (obj.hasOwnProperty(k)) {
        // 处理 obj[k]
    }
}
```

### 4.6 数字与字符串隐式转换

```javascript
var n = java.ajax(url);  // 返回 Java String
var num = n * 1;         // ✅ 隐式转换为 JS number（但 NaN 风险）
var num2 = parseInt(n, 10); // ✅ 更安全的转换
```

---

## 5. Rhino 版本说明

### 5.1 版本锁定

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Rhino 版本 | **1.8.1** | 锁定，不可升级 |
| Context 版本 | `Context.VERSION_ES6` | 部分启用 ES6，但不完整 |
| 锁定原因 | API 24 以下缺少 `Arrays.setAll` | 升级到 1.8.2+ 需要 API 24+ |
| minSdk | 23（项目当前） | 低于 24，故无法升级 Rhino |

### 5.2 升级阻塞铁证

- **新版本依赖**：Rhino 1.8.2+ 内部使用 `java.util.Arrays.setAll`
- **API 限制**：`Arrays.setAll` 需要 Android API 24+（Android 7.0）
- **项目 minSdk**：23（Android 6.0）
- **结论**：在提升 minSdk 至 24 之前，**禁止升级 Rhino**

### 5.3 测试注意事项

> ⚠️ **禁止用 Node.js 测试 JS 后直接用于 Legado！** 必须在 Rhino 1.8.1 环境中验证。

- Node.js 使用 V8 引擎，支持完整 ES2015+
- Chrome WebView 使用 V8 引擎，支持完整 ES2015+
- Legado 规则 JS 使用 Rhino 1.8.1，仅支持部分 ES5/ES6

**正则表达式测试**：详见 `../troubleshooting/rhino-js-traps.md` §3.2，特别是命名捕获组、后行断言、Unicode 属性等 ES2018+ 特性在 Rhino 1.8.1 中会报 SyntaxError。

### 5.4 相关依赖锁定

| 依赖 | 版本 | 锁定原因 |
|------|------|---------|
| jsoup | 1.16.2 | 破坏性变更 jsoup#2017，不可升级 |
| hutool | 5.8.22 | 书源加解密依赖，不可升级 |
| Rhino | 1.8.1 | API 24 限制，不可升级 |
