# java.xxx 方法调用频率 TOP15

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

## 调用频率排行

| 排名 | 方法 | 调用次数 | 用途 | 详细文档 |
|------|------|----------|------|---------|
| 1 | `java.md5Encode` | 5,586 | MD5哈希，API签名 | [crypto-encoding.md](../js-extensions/crypto-encoding.md) |
| 2 | `java.getString` | 3,656 | JSONPath取值，解析API响应 | [rule-parsing.md](../js-extensions/rule-parsing.md) |
| 3 | `java.put` | 3,610 | 缓存键值对，跨阶段传变量 | [global-objects.md](../js-extensions/global-objects.md) |
| 4 | `java.ajax` | 2,783 | HTTP请求，获取额外数据 | [network.md](../js-extensions/network.md) |
| 5 | `java.get` | 2,328 | 从缓存取值 | [global-objects.md](../js-extensions/global-objects.md) |
| 6 | `java.log` | 1,618 | 调试输出 | [utils.md](../js-extensions/utils.md) |
| 7 | `java.timeFormat` | 1,206 | 时间格式化 | [utils.md](../js-extensions/utils.md) |
| 8 | `java.getElements` | 794 | CSS选择器获取元素列表 | [rule-parsing.md](../js-extensions/rule-parsing.md) |
| 9 | `java.lang` | 481 | 多语言支持 | [ui-interaction.md](../js-extensions/ui-interaction.md) |
| 10 | `java.aesBase64DecodeToString` | 442 | AES解密(Base64编码) | [crypto-encoding.md](../js-extensions/crypto-encoding.md) |
| 11 | `java.base64DecodeToByteArray` | 380 | Base64解码为字节数组 | [crypto-encoding.md](../js-extensions/crypto-encoding.md) |
| 12 | `java.md5Encode16` | 373 | MD5哈希(16位) | [crypto-encoding.md](../js-extensions/crypto-encoding.md) |
| 13 | `java.security` | 292 | 安全相关操作 | [crypto-encoding.md](../js-extensions/crypto-encoding.md) |
| 14 | `java.setContent` | 268 | 设置正文内容 | [rule-parsing.md](../js-extensions/rule-parsing.md) |
| 15 | `java.t2s` | 257 | 繁体转简体 | [utils.md](../js-extensions/utils.md) |

## 高频方法使用示例

### 1. java.md5Encode — API 签名（最常见场景）

```javascript
// 典型用法：为 API 请求生成签名
var ts = new Date().getTime();
var sign = java.md5Encode(ts + "salt" + key);
var url = "https://api.example.com/list?ts=" + ts + "&sign=" + sign;
java.ajax(url);
```

### 2. java.getString — JSONPath 取值

```javascript
// 从 API 响应中提取字段
var json = java.ajax(apiUrl);
var title = java.getString(json, "$.data.title");
var list = java.getString(json, "$.data.list[*].name");
```

### 3. java.put + java.get — 跨阶段变量传递

```javascript
// searchUrl 中获取 token
var token = result.match(/token=(\w+)/)[1];
java.put("auth_token", token);

// ruleContent 中使用 token
var token = java.get("auth_token");
java.ajax(baseUrl + "?token=" + token);
```

### 4. java.ajax — 多步请求

```javascript
// 第一步：获取加密密钥
var keyPage = java.ajax("https://example.com/api/key");
var key = keyPage.match(/key='([^']+)'/)[1];

// 第二步：用密钥请求内容
var content = java.ajax("https://example.com/api/content?key=" + key);
```

> **注意**：`java.ajax()` 在 JVM 仿真器中不自动携带 Cookie/Header，依赖 Cookie 的请求可信度为"低"。详见 [ajax-diff-analysis.md](../../tools/ajax-diff-analysis.md)。

## 频率洞察

- **MD5 签名占第一**：说明 API 签名验证是书源最常见需求
- **put/get 占第3/5**：跨阶段变量传递是核心模式
- **ajax 占第4**：多步请求是常见模式，但也带来 Cookie/Header 差异问题
- **加密相关占 3/15**：AES/MD5/Base64 合计占比约 30%，加密是 Legado 书源的重要能力
