# 网站分析流程最佳实践

> 分析网站结构和编写规则的最佳实践流程。

## 5.1 推荐分析顺序

```
1. curl 获取首页 HTML → 确认网站类型和基本结构
2. curl/Playwright 获取搜索结果页 HTML → 提取列表 CSS 选择器
   ⚠️ 必须对比搜索结果页与列表页的HTML结构差异！
   ⚠️ 必须验证搜索是否需要登录！
3. curl 获取详情页 HTML → 提取详情字段选择器
4. 分析搜索 URL 模式 → 确定是否需要加密/签名
   ⚠️ 必须分析实际搜索表单的参数名，不能按论坛类型臆测！
5. 如需加密 → 获取页面 JS 源码，分析加密函数
6. 编写 searchUrl 的 JS 规则 → 用已知明文-密文对验证
7. 编写所有 CSS 选择器 → 基于真实 HTML，禁止推测
   ⚠️ 搜索和列表页结构不同时，用 || 操作符兼容
8. 组装完整 JSON → 输出并标注可能需要调整的地方
   ⚠️ searchUrl 的 POST body 中必须包含 page={{page}} 参数
```

## 5.1b 订阅源字段完善清单（实战经验）

> ⚠️ 这些是资深书源作者的经验总结，直接决定订阅源的实用性和可维护性。

### sourceIcon — 图标

```bash
# 从首页 HTML 提取 favicon 或 logo
curl -s -L "URL/" | grep -oE '(href="[^"]*\.(ico|png|svg)[^"]*"[^>]*rel[^>]*icon|src="[^"]*(?:logo|icon)[^"]*")'
```

| 来源 | 选择器 | 示例 |
|------|--------|------|
| `<link rel="icon">` | `link[rel=icon]@href` | `/favicon.ico` |
| 网站 logo `<img>` | `.logo img@src` | `/static/logo.svg` |
| 无图标时 | 留空或用通用视频图标 | — |

### sourceComment — 注释（⚠️ 防丢失关键）

必须包含的信息：
```
网站名(别名) — 网站简介。发布页：https://example.com/ | 特殊处理说明
```

示例：
```
集芳阁(机房哥) — 免费福利视频云搜平台，海量国产资源/JAV等，永久免费。
发布页：https://xn--25b-j8f8g-com-9x6wp54c.www-jfgsou-com.com/
搜索关键词AES-128-CBC+ZeroPadding加密(Key=2d4ebb7cb767dab1 IV=7563ca4af41bd0fb)
正文提取m3u8播放地址(Video.js播放器)
```

**为什么重要**：网站域名经常变更，没有发布页 URL 就找不到新地址。

### ruleNextPage — 分页规则

```bash
# 查找分页结构
curl -s -L "URL/list.html" | grep -Ei "(stui-page|pagination|page.*href|p=\d|下一页)"
```

常见分页模式：

| 模式 | 选择器 | 示例 |
|------|--------|------|
| 标准分页 ul | `ul.stui-page > li > a[href*="p="]@href` | `toplist.php?p=2` |
| 下一页按钮 | `a:contains(下一页)@href` | 需 JS 支持 |
| 数字链接 | `.pagination a.next@href` | `/page/2` |

> **不配 ruleNextPage 的后果**：列表只加载第一页数据。

### rulePubDate / ruleDescription — 信息最大化

使用 `##` 组合符合并多个字段：

```json
{
  "rulePubDate": "span.vodtime@text##⏰时长",
  "ruleDescription": "input.h_d_key@value##🆔ID##span.cate@text##分类"
}
```

| 可用信息 | 常见位置 | 建议放入 |
|----------|----------|----------|
| 视频时长 | `span.vodtime` / `span.duration` | rulePubDate |
| 发布日期 | `div.time` / `span.date` | rulePubDate（用 ## 拼接） |
| 视频分类 | `span.tag` / `span.cate` | ruleDescription |
| 视频 ID | `input.h_d_key` / `data-id` | ruleDescription |
| 点赞/播放数 | `span.likes` / `span.views` | ruleDescription |
| 评分 | `span.score` / `span.rating` | ruleDescription |

> **原则**：除了标题和封面外，网站上所有能抓到的有用信息都应该放进某个字段里。

## 5.2 curl 提取特定 HTML 片段

```bash
# 提取列表区域
curl -s -L "URL" | sed -n '/<ul class="list">/,/<\/ul>/p'

# 提取特定标签
curl -s -L "URL" | grep -E "(class=\"item\"|<article|<h[1-6])" | head -30

# 提取 JS 中的加密函数
curl -s -L "URL" | grep -E "(encrypt|CryptoJS|AES|DES|MD5)" | head -20
```

## 5.2b curl 实战指令速查（两个网站对比）

> 基于两个实战网站（机房哥 jfg / 18AV mjv006）总结的 curl 分析工作流。

### 第一步：探测网站基本信息

```bash
# 获取 HTTP 状态码和页面大小（判断是否被拦截/跳转）
curl -s -L --max-time 15 -o /dev/null -w "HTTP:%{http_code} SIZE:%{size_download}" "https://example.com/"

# 获取完整首页 HTML（查看是否有年龄确认/Cloudflare 拦截）
curl -s -L --max-time 15 "https://example.com/" | head -100
```

**常见情况判断**：

| 现象 | HTTP码 | 页面大小 | 说明 | 解决方案 |
|------|--------|----------|------|----------|
| 正常首页 | 200 | >10KB | 直接可用 | 继续分析 |
| 年龄确认页 | 200 | <2KB | 需点击同意 | 见 §5.2c |
| Cloudflare 拦截 | 403/503 | — | JS 挑战 | 用 Playwright |
| 空白页 | 200 | 0 | DNS/网络问题 | 检查域名 |

### 第二步：提取分类/导航链接

```bash
# 提取所有链接（找分类 URL 模式）
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/" | grep -oE "href=\"[^\"]*\"" | sort -u | head -40

# 提取导航/分类区域
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/" | grep -E "(nav|menu|cate|sort|分类|频道)" | head -30
```

### 第三步：提取列表项 HTML 结构

```bash
# 查找列表容器和条目
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/list.html" | grep -E "(<a |<img |title=|href=.*content)" | head -30

# 提取特定区域（如 <ul class="list">）
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/list.html" | sed -n '/<ul class="list">/,/<\/ul>/p' | head -50
```

### 第四步：提取分页结构

```bash
# 查找分页区域
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/list.html" | grep -E "(page|next|下一页|pagination)" | head -10
```

### 第五步：提取详情页视频播放地址

```bash
# 查找视频播放器/iframe/m3u8
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/detail.html" | grep -E "(video|source|iframe|m3u8|mp4|player|playdata)" | head -20

# 查找加密函数（搜索关键词）
curl -s -L --max-time 15 -b /tmp/cookie "https://example.com/" | grep -E "(encrypt|CryptoJS|AES|DES|MD5)" | head -20
```

### 第六步：提取网站图标和描述

```bash
# favicon / logo
curl -s -L --max-time 15 "https://example.com/" | grep -oE '(href="[^"]*\.(ico|png|svg)[^"]*"[^>]*rel[^>]*icon|src="[^"]*(?:logo|icon)[^"]*")'

# meta description
curl -s -L --max-time 15 "https://example.com/" | grep -E "meta.*description" | head -3
```

## 5.2c 年龄确认页处理

> 实战案例：mjv006.com 首页是年龄确认页，点击"同意"后才进入主站。

### 识别年龄确认页

特征：页面很小（<2KB），包含"同意"/"I agree"/"18+"按钮，点击后跳转。

```bash
# 确认是年龄确认页
curl -s -L --max-time 15 "https://mjv006.com/" | grep -i "agree\|同意\|18\|eighteen"
```

### 处理方式

**方式1：Cookie 预访问（推荐）**

在 Legado 中设置 `loginUrl` 为年龄确认页的"同意"跳转 URL：

```json
{
  "enabledCookieJar": true,
  "loginUrl": "https://mjv006.com/zh/chinese_IamOverEighteenYearsOld/19/index.html"
}
```

Legado 会自动访问该 URL 并保存 Cookie，后续请求自动带上。

**方式2：curl 带 Cookie 调试**

```bash
# 第一步：访问确认页，保存 Cookie
curl -s -L --max-time 15 -c /tmp/cookie "https://mjv006.com/zh/chinese_IamOverEighteenYearsOld/19/index.html" > /dev/null

# 第二步：带 Cookie 访问列表页
curl -s -L --max-time 15 -b /tmp/cookie "https://mjv006.com/zh/chinese_list/all/1.html" | head -100
```

> **注意**：如果不带 Cookie 直接访问列表页，可能返回空内容或被重定向到确认页。

## 5.3 验证加密逻辑

1. 从网页 JS 中找到加密函数和已知输出
2. 在 Legado 的书源调试中测试 JS 规则
3. 对比加密结果是否一致
4. 不一致时检查：Key/IV 是否正确、Padding 方式、编码方式

## 5.4 完整分类结构分析（⚠️ 实战教训）

**我的错误**：只分析了首页的分类链接，遗漏了：
- Film 区域的分类（推荐、专题、女优、无码、中字、动漫等）
- 搜索关键词可以作为分类（如 `/search?wd=大神`）

**正确做法**：
1. 分析网站的所有导航区域（首页、Film、搜索）
2. 发现搜索 URL 可以作为分类入口（搜索关键词分类）
3. 检查是否有隐藏的分类区域（如 `/film/home_list/xxx`）

**搜索关键词分类示例**：
```
大神::/search?wd=大神
学生::/search?wd=学生
91::/search?wd=91
```

**好处**：
- 用户可以直接进入感兴趣的内容分类
- 不需要手动搜索
- 分类数量可以很丰富（20+）

## 5.5 视频订阅源用户体验设计（⚠️ 核心价值）

**我的错误**：只提取了 m3u8 URL，以为 Legado 内置播放器足够。

**用户期望**：
- 视频进度条、缓冲进度显示
- 快进/快退按钮（30s/1m/3m）
- 倍速播放选择（1x/3x/5x/10x/15x）
- 全屏按钮、上一集/下一集切换
- 视频源选择下拉框

**解决方案**：
- 使用 `type: 0`（网页模式）
- ruleContent 返回完整的 HLS.js 播放器 HTML
- 参考 `js-patterns/hls-player.md` 的完整模板

**教训**：视频订阅源的核心价值是**用户体验**，不能只做数据提取。

## 5.6 预加载和缓存优化

**推荐配置**：
```json
{
  "preload": true,
  "cacheFirst": true
}
```

**作用**：
- `preload: true` — 预加载视频，减少等待时间
- `cacheFirst: true` — 缓存优先，重复访问更快

**适用场景**：视频/音频订阅源，提升用户体验。
