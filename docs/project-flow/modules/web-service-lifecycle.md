# Web 服务 — 服务生命周期与系统能力

> 由 [modules/web-service.md](web-service.md) 拆分（2026-08-30）。本文件为 Web 服务**运行层**唯一权威源：WebService 前台服务生命周期、WebTileService 快捷磁贴、ReaderProvider ContentProvider 通道、ShortCuts 动态快捷方式、WiFi 传书、帮助系统、Web 导航首页、配置参考、安全模型、性能分析、故障排查。
> REST API/路由/WebSocket/Vue3 前端对照见 [web-service-api.md](web-service-api.md)；Python 重构参考见 [../python-ref/web-service.md](../python-ref/web-service.md)。

---

---

---

## 1. WebService Android 服务生命周期

> 源码：[WebService.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/service/WebService.kt)

### 1.1 服务架构

```
┌─────────────────────────────────────────────────────┐
│                   WebService                        │
│              (BaseService / 前台 Service)            │
├─────────────────────────────────────────────────────┤
│  companion object:                                  │
│    isRun: Boolean        ← 全局运行状态标志          │
│    hostAddress: String   ← 当前服务地址（通知用）    │
│    start(context)        ← 普通启动                 │
│    startForeground(context) ← 前台服务启动           │
│    stop(context)         ← 停止服务                 │
│    serve()               ← 保活心跳（重启服务）      │
├─────────────────────────────────────────────────────┤
│  内部组件:                                          │
│    httpServer: HttpServer?        ← NanoHTTPD 实例  │
│    webSocketServer: WebSocketServer? ← NanoWSD 实例 │
│    wakeLock: PowerManager.WakeLock  ← CPU 唤醒锁    │
│    wifiLock: WifiManager.WifiLock  ← WiFi 高性能锁  │
│    networkChangedListener           ← 网络变化监听   │
│    notificationList                 ← 通知内容列表   │
└─────────────────────────────────────────────────────┘
```

### 1.2 启动流程

```
用户操作 / WebTileService / 代码调用
       │
       ▼
WebService.start(context)  或  startForeground(context)
       │
       ▼
onCreate()
  ├─ 读取 WakeLock 偏好 (PreferKey.webServiceWakeLock, 默认 false)
  ├─ 若启用 WakeLock → acquire() wakeLock + wifiLock
  ├─ isRun = true
  ├─ upTile(true) → 通知 WebTileService 更新磁贴状态
  ├─ networkChangedListener.register()
  └─ 设置 onNetworkChanged 回调
       │
       ▼
onStartCommand(intent)
  ├─ action == "stop" → stopSelf()
  ├─ action == "copyHostAddress" → sendToClip(hostAddress)
  ├─ action == "serve" → 保活心跳（重新 acquire WakeLock）
  └─ else → upWebServer()
       │
       ▼
upWebServer()
  ├─ 停止旧 httpServer / webSocketServer（若存活）
  ├─ 获取本机 IP 地址列表 (NetworkUtils.getLocalIPAddress())
  ├─ 若无 IP → toast "web service cant start" → stopSelf()
  ├─ 创建 HttpServer(port) + WebSocketServer(port+1)
  ├─ httpServer.start()
  ├─ webSocketServer.start(30_000)  ← 30s 通信超时
  ├─ 更新 notificationList（每个 IP 一行 "http://{ip}:{port}"）
  ├─ hostAddress = notificationList.first()
  ├─ isRun = true
  ├─ postEvent(EventBus.WEB_SERVICE, hostAddress)
  └─ startForegroundNotification()
       │
       ▼
startForegroundNotification()
  ├─ NotificationCompat.Builder(channelIdWeb)
  ├─ VISIBILITY_PUBLIC
  ├─ setOngoing(true)  ← 不可滑动清除
  ├─ ContentTitle: "Web服务"
  ├─ ContentText: IP地址列表（换行分隔）
  ├─ ContentIntent → 点击复制 hostAddress 到剪贴板
  └─ Action: "停止" → IntentAction.stop → stopSelf()
```

### 1.3 停止流程

```
用户点击通知"停止" / WebTileService / 代码调用
       │
       ▼
onDestroy()
  ├─ 若启用 WakeLock → release() wakeLock + wifiLock
  ├─ networkChangedListener.unRegister()
  ├─ isRun = false
  ├─ httpServer?.stop()（若存活）
  ├─ webSocketServer?.stop()（若存活）
  ├─ postEvent(EventBus.WEB_SERVICE, "")
  └─ upTile(false) → 通知 WebTileService 更新磁贴状态
```

### 1.4 网络变化监听

[WebService.kt#L93-L111](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/service/WebService.kt#L93-L111)

```
NetworkChangedListener.onNetworkChanged 回调:
  ├─ 重新获取本机 IP 地址列表
  ├─ 更新 notificationList（每个 IP 一行）
  ├─ 更新 hostAddress
  ├─ startForegroundNotification() → 刷新前台通知
  └─ postEvent(EventBus.WEB_SERVICE, hostAddress) → 通知 UI 层
```

- **场景**：WiFi 切换、移动网络切换、飞行模式切换时自动刷新通知中的 IP 地址
- **注意**：网络变化时仅更新通知和 `hostAddress`，不重启 HttpServer/WebSocketServer

### 1.5 保活机制（serve）

[HttpServer.kt#L26](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/web/HttpServer.kt#L26)

```kotlin
override fun serve(session: IHTTPSession): Response {
    WebService.serve()  // 每个请求都触发 serve()
    ...
}
```

- `WebService.serve()` 发送 `action="serve"` 的 Intent 启动 WebService
- 作用：若 Android 系统杀死了 WebService 进程，下一个 HTTP 请求会自动重启服务
- 副作用：每次请求都会重新 acquire WakeLock（若启用），确保服务不被休眠

### 1.6 端口配置

[WebService.kt#L185-L191](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/service/WebService.kt#L185-L191)

| 配置项 | 偏好键 | 默认值 | 范围 | 说明 |
|--------|--------|--------|------|------|
| HTTP 端口 | `PreferKey.webPort` | 1122 | 1024-65530 | 超出范围回退到 1122 |
| WebSocket 端口 | 自动计算 | 1123 | HTTP端口+1 | 不可独立配置 |
| WakeLock | `PreferKey.webServiceWakeLock` | false | - | 启用后保持 CPU/WiFi 唤醒 |

---

## 2. WebTileService 快捷磁贴

> 源码：[WebTileService.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/service/WebTileService.kt)

### 2.1 功能说明

Android 7.0+ 快捷设置磁贴，可在下拉通知栏一键开关 Web 服务。

### 2.2 状态同步

| 事件 | 行为 |
|------|------|
| `onStartListening()` | 根据 `WebService.isRun` 设置磁贴状态（ACTIVE/INACTIVE） |
| `IntentAction.start` | 磁贴设为 `STATE_ACTIVE` |
| `IntentAction.stop` | 磁贴设为 `STATE_INACTIVE` |

### 2.3 点击行为

```
onClick()
  ├─ WebService.isRun == true → WebService.stop(this)
  └─ WebService.isRun == false
       ├─ Android 14+ (UPSIDE_DOWN_CAKE)
       │    ├─ 创建透明 Dialog
       │    ├─ Dialog.onShow → WebService.startForeground(this)
       │    │   └─ 捕获 ForegroundServiceStartNotAllowedException
       │    └─ showDialog(dialog)
       │        └─ 捕获 BadTokenException
       └─ Android < 14
            └─ WebService.start(this)
```

- **Android 14+ 限制**：后台启动前台服务需通过 `showDialog()` 获取临时窗口焦点，才能调用 `startForeground()`
- **异常处理**：`ForegroundServiceStartNotAllowedException` 和 `BadTokenException` 均静默捕获（仅 printStackTrace）

---

## 3. ReaderProvider（ContentProvider 通道）

> 源码：[ReaderProvider.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/api/ReaderProvider.kt)
> AndroidManifest 注册：`android:name=".api.ReaderProvider"`, `android:authorities="${applicationId}.readerProvider"`

### 3.1 功能概述

ReaderProvider 是 Android ContentProvider，将 Web API 的核心功能通过 ContentProvider 机制暴露给第三方应用，无需 HTTP 连接即可操作阅读数据。

### 3.2 双通道架构

```
┌─────────────────────────────────────────────────────────┐
│                  Controller 层                          │
│  BookController / BookSourceController / RssSourceController │
├──────────────────────┬──────────────────────────────────┤
│   HTTP 通道          │   ContentProvider 通道            │
│   NanoHTTPD          │   ReaderProvider                  │
│   端口 1122          │   authority: {pkg}.readerProvider │
│   浏览器/前端调用     │   第三方 App 调用                 │
│   ReturnData JSON    │   SimpleCursor (JSON in Cursor)  │
│   runBlocking        │   runBlocking                    │
└──────────────────────┴──────────────────────────────────┘
```

### 3.3 URI 路由表

| RequestCode | URI 路径 | HTTP 对应 | CRUD 方法 |
|-------------|---------|----------|----------|
| SaveBookSource | `bookSource/insert` | POST /saveBookSource | insert |
| SaveBookSources | `bookSources/insert` | POST /saveBookSources | insert |
| DeleteBookSources | `bookSources/delete` | POST /deleteBookSources | delete |
| GetBookSource | `bookSource/query` | GET /getBookSource | query |
| GetBookSources | `bookSources/query` | GET /getBookSources | query |
| SaveRssSource | `rssSource/insert` | POST /saveRssSource | insert |
| SaveRssSources | `rssSources/insert` | POST /saveRssSources | insert |
| DeleteRssSources | `rssSources/delete` | POST /deleteRssSources | delete |
| GetRssSource | `rssSource/query` | GET /getRssSource | query |
| GetRssSources | `rssSources/query` | GET /getRssSources | query |
| SaveBook | `book/insert` | POST /saveBook | insert |
| GetBookshelf | `books/query` | GET /getBookshelf | query |
| RefreshToc | `book/refreshToc/query` | GET /refreshToc | query |
| GetChapterList | `book/chapter/query` | GET /getChapterList | query |
| GetBookContent | `book/content/query` | GET /getBookContent | query |
| GetBookCover | `book/cover/query` | GET /cover | query |
| SaveBookProgress | — | POST /saveBookProgress | insert |

> **注意**：RSS 源的 delete 路由（`rssSources/delete`）实际调用了 `BookSourceController.deleteSources()` 而非 `RssSourceController.deleteSources()`，这是一个 bug。

### 3.4 调用方式

#### 查询操作（query）

```kotlin
// 获取书架
val uri = Uri.parse("content://${packageName}.readerProvider/books/query")
val cursor = contentResolver.query(uri, null, null, null, null)
cursor?.let {
    it.moveToFirst()
    val json = it.getString(0)  // ReturnData JSON 字符串
}

// 获取章节列表
val uri = Uri.parse("content://${packageName}.readerProvider/book/chapter/query?url={encodedUrl}")
val cursor = contentResolver.query(uri, null, null, null, null)
```

#### 插入操作（insert）

```kotlin
val uri = Uri.parse("content://${packageName}.readerProvider/bookSource/insert")
val values = ContentValues().apply {
    put("json", sourceJsonString)  // key 固定为 "json"
}
contentResolver.insert(uri, values)
```

#### 删除操作（delete）

```kotlin
val uri = Uri.parse("content://${packageName}.readerProvider/bookSources/delete")
contentResolver.delete(uri, sourceJsonString, null)  // selection 直接传 JSON
```

### 3.5 SimpleCursor 响应格式

```kotlin
private class SimpleCursor(data: ReturnData?) : MatrixCursor(arrayOf("result"), 1) {
    private val mData: String = Gson().toJson(data)
    init { addRow(arrayOf(mData)) }
}
```

- Cursor 列名固定为 `"result"`
- 值为 `ReturnData` 的 JSON 序列化字符串
- 调用方需 `cursor.getString(0)` 获取 JSON 后反序列化

### 3.6 与 HTTP 通道的差异

| 维度 | HTTP 通道 | ContentProvider 通道 |
|------|----------|---------------------|
| 通信方式 | HTTP 请求 | Android IPC |
| 适用场景 | 浏览器/远程客户端 | 同设备第三方 App |
| 认证 | 无 | Android 沙箱权限 |
| 响应格式 | HTTP Response (JSON) | Cursor (JSON in column) |
| 文件上传 | 支持（addLocalBook） | 不支持 |
| 替换规则 | 支持 | 不支持 |
| WebSocket | 支持 | 不支持 |
| RSS 删除 | 正确路由 | **bug：路由到 BookSourceController** |

---

## 4. ShortCuts（动态快捷方式）

> 源码：[ShortCuts.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/api/ShortCuts.kt)

### 4.1 功能概述

在 Android 启动器长按 App 图标时显示的 3 个动态快捷方式，由 `ReaderProvider.onCreate()` 初始化。

### 4.2 快捷方式列表

| ID | 标签 | Intent | 说明 |
|----|------|--------|------|
| `bookshelf` | 书架 | `MainActivity` | 直接进入书架 |
| `lastRead` | 最近阅读 | `MainActivity` → `ReadBookActivity` | 打开上次阅读的书籍 |
| `readAloud` | 朗读 | `SharedReceiverActivity` (action=readAloud) | 开始朗读 |

---

## 5. WiFi 传书功能

> 源码：[uploadBook/index.html](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/assets/web/uploadBook/index.html)

### 5.1 功能概述

通过浏览器向 Android 设备传输电子书文件的 Web 页面，无需数据线，同一局域网内即可传书。

### 5.2 技术实现

| 维度 | 实现 |
|------|------|
| 前端框架 | 原生 HTML5 + jQuery 1.4.2 |
| 文件上传 | HTML5 `<input type="file" multiple>` + FormData |
| 拖拽上传 | 支持（drag & drop） |
| 后端端点 | `POST /addLocalBook` |
| 响应处理 | `BookController.addLocalBook(session.parameters, files)` |

### 5.3 支持的文件格式

```
TXT、EPUB、UMD、PDF、MOBI、AZW3、AZW
```

### 5.4 页面布局

- **PC 端**：表格布局（文件名 / 大小 / 操作），支持拖拽区域
- **移动端**：响应式布局，简化操作界面
- **状态提示**：上传进度、成功/失败反馈

### 5.5 上传流程

```
选择文件 / 拖拽文件
       │
       ▼
FormData 构造（fileName + fileData）
       │
       ▼
POST /addLocalBook  (multipart/form-data)
       │
       ▼
BookController.addLocalBook()
  ├─ 解析 fileName 和 fileData
  ├─ 保存到本地存储
  └─ 返回 ReturnData(isSuccess=true/false)
```

---

## 6. 帮助系统

> 源码目录：`app/src/main/assets/web/help/`

### 6.1 功能概述

Web 端帮助文档系统，使用 Markdown 渲染，供用户查阅使用说明。

### 6.2 技术实现

| 维度 | 实现 |
|------|------|
| 模块加载 | RequireJS (AMD) |
| Markdown 渲染 | Marked.js |
| 样式 | GitHub Flavored Markdown 风格 |
| 内容来源 | APK assets 中的 Markdown 文件 |

---

## 7. Web 导航首页

> 源码：[index.html](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/assets/web/index.html)

### 7.1 功能概述

Web 服务根路径 `/` 的导航首页，提供四个功能入口。

### 7.2 页面结构

```
Legado Web 导航
├─ 标题: "昨日邻家乞新火，晓窗分与读书灯"
├─ [书架]  → vue/index.html
├─ [书源]  → vue/index.html#/bookSource
├─ [传书]  → uploadBook/index.html
└─ [订阅源] → vue/index.html#/rssSource
```

### 7.3 技术实现

| 维度 | 实现 |
|------|------|
| 模板 | Forty by HTML5 UP |
| 响应式 | viewport meta + CSS 媒体查询 |
| 导航菜单 | GitHub 链接、作者链接 |
| 菜单 | 汉堡菜单（移动端） |

---

## 8. 配置完整参考

### 8.1 偏好键

| 偏好键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `PreferKey.webPort` | Int | 1122 | HTTP 服务端口（范围 1024-65530） |
| `PreferKey.webServiceWakeLock` | Boolean | false | 是否保持 CPU/WiFi 唤醒 |

### 8.2 通知渠道

| 渠道 ID | 用途 | 重要性 |
|---------|------|--------|
| `AppConst.channelIdWeb` | Web 服务前台通知 | DEFAULT |

### 8.3 通知 ID

| ID | 用途 |
|----|------|
| `NotificationId.WebService` | Web 服务前台通知 |

### 8.4 EventBus 事件

| 事件 | 数据类型 | 触发时机 |
|------|---------|---------|
| `EventBus.WEB_SERVICE` | String | 服务启动/停止/网络变化时发送 hostAddress 或空字符串 |

### 8.5 Intent Action

| Action | 目标 | 说明 |
|--------|------|------|
| `IntentAction.stop` | WebService | 停止服务 |
| `IntentAction.start` | WebTileService | 磁贴激活 |
| `"serve"` | WebService | 保活心跳 |
| `"copyHostAddress"` | WebService | 复制 IP 到剪贴板 |

---

## 9. 安全模型分析

### 9.1 当前安全状态

| 维度 | 状态 | 风险等级 | 说明 |
|------|------|---------|------|
| 认证 | **无** | 🔴 高 | 任何局域网设备均可访问所有 API |
| 授权 | **无** | 🔴 高 | 无角色/权限区分，所有操作完全开放 |
| CORS | 动态 Origin 回显 | 🟡 中 | `Access-Control-Allow-Origin` 回显请求 Origin，允许任意跨域 |
| 传输加密 | **无** | 🟡 中 | 纯 HTTP，无 HTTPS/TLS |
| 输入校验 | 部分 | 🟡 中 | Controller 层有基本校验，路由层无 |
| CSRF | **无** | 🟡 中 | 无 CSRF Token 机制 |
| 速率限制 | **无** | 🟡 中 | 无请求频率限制 |

### 9.2 CORS 动态 Origin 机制

[HttpServer.kt#L43](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/web/HttpServer.kt#L43)

```kotlin
response.addHeader("Access-Control-Allow-Origin", session.headers["origin"])
```

- **设计意图**：允许任意前端页面跨域访问 API（方便第三方工具集成）
- **安全影响**：任何网站都可以向 Legado Web API 发起跨域请求
- **缓解因素**：服务仅监听局域网，不暴露公网

### 9.3 安全边界

```
┌──────────────────────────────────────┐
│          局域网 (LAN)                │
│  ┌────────┐    ┌──────────────────┐  │
│  │ 浏览器  │───▶│ Legado Web API   │  │
│  │ (任意)  │    │ (无认证)         │  │
│  └────────┘    └──────────────────┘  │
│                                      │
│  风险：同网段任何设备可完全控制阅读App │
└──────────────────────────────────────┘
         ✕ 不暴露公网
```

### 9.4 已知风险场景

| 场景 | 影响 | 缓解 |
|------|------|------|
| 公共 WiFi | 同网段用户可删除书籍/书源 | 不在公共 WiFi 开启 Web 服务 |
| 恶意网页 | 跨域请求删除书籍 | 服务仅监听局域网 |
| 中间人攻击 | HTTP 明文传输 | 局域网内风险较低 |

---

## 10. 性能与并发分析

### 10.1 单线程模型

| 组件 | 线程模型 | 影响 |
|------|---------|------|
| NanoHTTPD | 单线程（默认） | 请求串行处理 |
| `runBlocking` | 阻塞调用线程 | POST 请求期间阻塞 NanoHTTPD 工作线程 |
| WebSocket | NanoWSD 独立线程 | 与 HTTP 互不阻塞 |

### 10.2 性能瓶颈

[HttpServer.kt#L53](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/web/HttpServer.kt#L53)

```kotlin
returnData = runBlocking {  // 阻塞 NanoHTTPD 工作线程
    when (uri) { ... }
}
```

| 瓶颈 | 原因 | 影响 |
|------|------|------|
| POST 请求阻塞 | `runBlocking` 占用工作线程 | 并发 POST 请求排队 |
| 大数据序列化 | GSON.toJson 全量序列化 | >3000 条时内存压力 |
| Bitmap 压缩 | PNG 压缩在请求线程 | 封面/图片请求慢 |
| 无连接池 | 每次请求独立处理 | 无 Keep-Alive 复用 |

### 10.3 流式响应优化

[HttpServer.kt#L117-L131](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/web/HttpServer.kt#L117-L131)

```kotlin
if (data is List<*> && data.size > 3000) {
    val pipe = Pipe(16 * 1024)  // 16KB 缓冲区
    Coroutine.async {
        pipe.sink.buffer().outputStream().bufferedWriter(Charsets.UTF_8).use {
            GSON.toJson(returnData, it)  // 异步流式写入
        }
    }
    newChunkedResponse(Response.Status.OK, "application/json", pipe.source.buffer().inputStream())
}
```

- **触发条件**：返回数据为 List 且 size > 3000
- **机制**：okio Pipe（16KB 缓冲区）+ Coroutine.async 异步序列化
- **优势**：避免一次性将大量 JSON 加载到内存
- **传输方式**：HTTP Chunked Transfer Encoding

### 10.4 并发能力评估

| 场景 | 预期表现 |
|------|---------|
| 单用户浏览书架 | 流畅 |
| 单用户搜索+调试 | 流畅（WebSocket 独立线程） |
| 多用户同时操作 | POST 请求串行，GET 较快 |
| 大量书源导出（>3000） | 流式响应，内存可控 |

---

## 11. 故障排查指南

### 11.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 无法访问 Web 服务 | 服务未启动 | 检查 `WebService.isRun`，从设置中启动 |
| IP 地址显示不可用 | 无网络连接 | 连接 WiFi 或移动网络 |
| 端口冲突 | 端口被占用 | 修改 `PreferKey.webPort`（默认 1122） |
| 请求超时 | `runBlocking` 阻塞 | 等待当前请求完成 |
| WebSocket 断开 | 30s 通信超时 | 检查网络稳定性 |
| 封面/图片加载失败 | 书源规则问题 | 检查 coverUrl/imageUrl 是否有效 |
| 传书失败 | 文件格式不支持 | 确认格式为 TXT/EPUB/UMD/PDF/MOBI/AZW3/AZW |
| CORS 错误 | 浏览器安全策略 | 确保从导航首页进入，非直接 IP 访问 |
| 服务自动停止 | Android 后台限制 | 启用 WakeLock 或关闭电池优化 |

### 11.2 调试方法

| 方法 | 说明 |
|------|------|
| 通知点击 | 点击前台通知复制 hostAddress 到剪贴板 |
| LogUtils | HttpServer 每个请求记录 START/END 时间戳 |
| adb logcat | 过滤 `HttpServer` TAG 查看请求日志 |
| EventBus | 监听 `EventBus.WEB_SERVICE` 获取服务状态变化 |

### 11.3 错误响应格式

```
正常响应: ReturnData { isSuccess=true, errorMsg="", data=... }
错误响应: ReturnData { isSuccess=false, errorMsg="错误信息", data=null }
异常响应: 纯文本 e.message（非 JSON 格式）
```

> **注意**：异常时 `HttpServer` 返回纯文本 `e.message`，不是 `ReturnData` JSON 格式。前端需兼容两种响应格式。
