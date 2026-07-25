# 大神源完整链路分析 + 订阅源JS技巧

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

---

## 十二、大神源完整链路分析

### 起点（优+）— 复杂度2713分

**链路**：搜索→发现→详情→目录→正文

| 阶段 | 关键JS | 技巧 |
|------|--------|------|
| searchUrl | @js:动态构造搜索URL | API签名+POST |
| exploreUrl | @js:生成分类列表 | 缓存+动态分类 |
| ruleSearch | @js:解析搜索结果 | JSONPath+字段映射 |
| ruleBookInfo | @js:解析详情 | hex解码+变量缓存 |
| ruleToc | @js:获取目录 | 分页+VIP标记 |
| ruleContent | @js:获取正文 | API请求+解密 |

**核心技巧**：
1. `java.put()`/`java.get()` 跨阶段传递bookId等变量
2. `java.hexDecodeToString()` 解码hex编码的API响应
3. `java.aesBase64DecodeToString()` 解密AES加密的正文
4. `enabledCookieJar:true` 保持登录状态
5. exploreUrl用JS动态生成分类，支持男女频切换

### 淘小说（优++）— 复杂度1276分

**核心技巧**：
1. searchUrl中构造POST请求体
2. header中设置自定义请求头
3. ruleSearch.kind用JS解析分类标签
4. ruleToc.chapterUrl用JS修正URL格式

---

## 十三、订阅源JS技巧

### 微博博主（复杂度283分）

**核心技巧**：
1. sourceUrl中使用`#`锚点区分不同功能
2. ruleArticles用JS解析微博API
3. ruleContent用JS拼接完整内容
4. sortUrl用JS动态生成博主列表

### 18AV视频源（复杂度260分）

**核心技巧**：
1. loginUrl处理年龄确认页
2. ruleContent用webView获取m3u8地址
3. sortUrl动态生成分类
4. enabledCookieJar保持Cookie
