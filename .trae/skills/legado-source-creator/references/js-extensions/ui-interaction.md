# JS 扩展函数参考 — UI 交互

> 拆分自 js-extensions.md §八。Legado 书源 JS 环境中可调用的 UI 交互扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.toast(msg)`。

---

## 八、UI 交互

### openVideoPlayer(url, title) / openVideoPlayer(url, title, isFloat) — 打开视频播放器

```javascript
java.openVideoPlayer("https://example.com/video.mp4", "视频标题");
java.openVideoPlayer("https://example.com/video.mp4", "视频标题", true); // 悬浮窗播放
```

**使用频率**：低

---

### openUrl(url) / openUrl(url, mimeType) — 打开链接或应用跳转

```javascript
java.openUrl("https://example.com");
java.openUrl("legado://import?src=xxx");
java.openUrl("https://example.com", "text/html");
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | String | 是 | 链接地址（支持 legado:// / yuedu:// 协议） |
| mimeType | String | 否 | 指定应用类型 |

**使用频率**：低

---

### toast(msg) / longToast(msg) — 弹窗提示

```javascript
java.toast("操作成功");      // 短时间提示
java.longToast("详细提示信息"); // 长时间提示
```

**使用频率**：低（主要用于调试）

---

### searchBook(key) / searchBook(key, searchScope) — 跳转搜索界面

> 仅在 RssJsExtensions 环境中可用。

```javascript
java.searchBook("斗破苍穹");
java.searchBook("斗破苍穹", "sourceUrl1");
```

**使用频率**：低

---

### addBook(bookUrl) — 添加书籍到书架

> 仅在 RssJsExtensions 环境中可用。

```javascript
java.addBook("https://example.com/book/123");
```

**使用频率**：低

---

### showPhoto(src) — 显示图片

> 仅在 RssJsExtensions 环境中可用。

```javascript
java.showPhoto("https://example.com/image.jpg");
```

**使用频率**：低

---

### open(name, url, title, origin) — 多功能跳转

> 仅在 RssJsExtensions 环境中可用。

```javascript
java.open("login");                          // 打开登录界面
java.open("sort", null, "分类名", "sourceUrl"); // 打开 RSS 分类
java.open("rss", "articleUrl", "标题");       // 打开 RSS 文章
java.open("search", null, "搜索关键词");      // 跳转搜索
java.open("explore", "exploreUrl", "发现名", "sourceUrl"); // 打开发现
```

| name 值 | 说明 |
|---------|------|
| login | 打开登录界面 |
| sort | 打开 RSS 分类 |
| rss | 打开 RSS 文章阅读 |
| search | 跳转搜索 |
| explore | 打开发现 |

**使用频率**：低
