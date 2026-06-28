# WebSocket 调试：真机通信协议与陷阱

## 端口与路径

Legado 真机 Web 服务两个端口：
- **HTTP 端口（默认 1122）**：源 CRUD、书籍管理、书架操作等 REST API
- **WebSocket 端口（默认 1123 = HTTP+1）**：实时调试、搜索等长连接 API

WebSocket 三个有效路径：
| 路径 | 功能 | 请求格式 |
|------|------|---------|
| `/bookSourceDebug` | 书源调试（搜索→详情→目录→正文） | `{"tag": "源URL", "key": "搜索关键字"}` |
| `/rssSourceDebug` | RSS源调试（文章列表） | `{"tag": "源URL", "key": "首页"}` |
| `/searchBook` | 全源搜索（搜所有书源） | `{"key": "搜索关键字"}` |

## 关键陷阱

### 陷阱1: WebSocket 端口不响应 HTTP 请求
WebSocketServer 基于 NanoWSD（NanoHTTPD 的 WebSocket 扩展），只在收到合法 WebSocket 升级握手时响应。
- ❌ `curl http://127.0.0.1:1123/` → 连接断开或无响应
- ✅ `wscat -c ws://127.0.0.1:1123/bookSourceDebug`

### 陷阱2: searchBook 会搜索全部书源
`/searchBook` 端点会对真机上**所有**书源发起搜索，2.4万源耗时极长（分钟级）。
- 建议：仅用于少量源的场景，或先筛选源再搜索
- 替代方案：用 `/bookSourceDebug` 对单个源做定向调试

### 陷阱3: 真机调试日志是纯文本格式
与 JAR 仿真器的 JSON 格式不同，真机 WebSocket 调试返回纯文本日志：
- 格式：`[MM:SS.mmm] 日志消息`
- 没有 `type`/`state` 字段
- 需要通过关键词匹配判定阶段：
  - `"列表大小"` → 搜索成功
  - `"获取书名"` / `"书名"` → 详情成功
  - `"目录总数"` → 目录成功
  - `"获取正文"` + `"成功"` → 正文成功
  - `"调试结束"` → 调试流程结束
  - `"UnknownHostException"` → DNS 解析失败

### 陷阱4: Android 模拟器 DNS 可能不可用
Android 模拟器的 DNS 配置可能与宿主机不同：
- PC 能解析的域名，模拟器可能无法解析
- 解决：在模拟器设置中配置 DNS（如 8.8.8.8 / 114.114.114.114）
- 或使用 adb 命令：`adb shell setprop net.dns1 8.8.8.8`

### 陷阱5: getBookSources 返回数据量大
HTTP `GET /getBookSources` 返回全部书源 JSON（2.4万+），数据量约 50-100MB：
- 请求可能超时（需要 120s+ timeout）
- 建议使用 `GET /getBookSource?url=xxx` 获取单个源

## 正确的 WebSocket 连接方式

### Python (websockets 库)
```python
import asyncio, json, websockets

async def debug_book_source(host, port, tag, key):
    async with websockets.connect(f'ws://{host}:{port}/bookSourceDebug', open_timeout=5) as ws:
        await ws.send(json.dumps({"tag": tag, "key": key}))
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=60)
            if "调试结束" in msg:
                break
            print(msg)
```

### JavaScript (浏览器)
```javascript
const ws = new WebSocket('ws://127.0.0.1:1123/bookSourceDebug');
ws.onopen = () => ws.send(JSON.stringify({tag: '源URL', key: '斗破苍穹'}));
ws.onmessage = (e) => console.log(e.data);
```

## 真机 vs JAR 结果差异

| 维度 | 真机 | JAR 仿真器 |
|------|------|-----------|
| 日志格式 | 纯文本 `[MM:SS.mmm] msg` | JSON `{"type":"log","state":11,"msg":"..."}` |
| 网络环境 | Android DNS/网络栈 | PC JVM 网络栈 |
| User-Agent | Android WebView UA | PC JVM UA（已伪装为移动 Chrome） |
| SSL | Android 系统信任链 | JVM 信任链（已信任所有证书） |
| Cookie | Android CookieManager | 内存 CookieStoreStub |
| JS 引擎 | Rhino on Android | Rhino on JVM |
| 搜索全源 | 真机全源搜索（慢） | 不支持全源搜索 |
