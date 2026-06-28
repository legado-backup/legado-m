# 网站特征→规则类型映射表

> 基于 2026-06-20 修复后测试脚本（DebugResult）对 20 个真实源的端到端测试结果 + 源 JSON 分析提取。

## 映射表

| 网站特征 | 推荐规则类型 | 典型源示例 | 成功率 | 注意事项 |
|---------|-------------|-----------|--------|---------|
| 静态 HTML 列表页 | CSS 选择器 | txtzw.net (爱去小说), qishuta.org (奇书塔) | 0%* | 注意相对 URL 拼接 baseUrl |
| JSON API 响应 | JSONPath ($.field) | uaa.com (UAA-视频) | 0%* | 注意分页参数和嵌套层级 |
| JS 动态渲染 | 需 WebView | 18AV-new, 秀人集v20 | N/A | 标记 needsWebView，用 Selenium 渲染 |
| 套娃源（legado://import） | 无法测试 | 订阅v0暗香迷蝶 | 0% | sourceUrl 非 http URL，跳过测试 |
| 元数据格式源 | 需转换为标准格式 | usable-sources-list.json | 0% | 非 Legado 标准源 JSON，需提取 source 字段 |

> *0% 通过率是因为网站已失效或网络不通，非规则类型问题。规则类型本身的正确性需要网站可访问时才能验证。

## 规则类型识别特征

### 1. CSS 选择器（最稳定）

**识别特征**：
- ruleSearch/ruleExplore 中使用 `class.xxx@text`、`#id@html`、`tag.a@href` 格式
- 典型格式：`#booktext@html`、`.sone`、`class.am-g-collapse.-1@class.am-u-md-6`

**适用场景**：
- 静态 HTML 网站
- 传统小说网站（如笔趣阁、奇书塔）
- 列表页结构固定的网站

**示例**（爱去小说 txtzw.net）：
```json
"ruleContent": {"content": "#booktext@html"},
"ruleSearch": {"bookList": ".listtbs", "bookUrl": ".s2@a.0@href"}
```

### 2. JSONPath（最高效）

**识别特征**：
- ruleSearch/ruleExplore 中使用 `$.field`、`$.model.data` 格式
- 典型格式：`$.title`、`$.model.url`、`$.coverUrl`

**适用场景**：
- REST API 网站
- 现代视频/图片网站（如 UAA-视频）
- 返回 JSON 响应的网站

**示例**（UAA-视频 uaa.com）：
```json
"ruleArticles": "$.model.data",
"ruleTitle": "$.title",
"ruleImage": "$.coverUrl"
```

### 3. JS 规则 + WebView（需渲染）

**识别特征**：
- ruleContent 中包含 `<js>` 标签且调用 `webViewGetSource`/`webView`
- URL 配置中 `webView:true`
- shouldOverrideUrlLoading 字段非空

**适用场景**：
- JS 动态渲染网站
- 视频嗅探网站（如 18AV-new）
- 需要 JS 执行才能获取内容的网站

**示例**（18AV-new）：
```json
"ruleContent": "<js>let videoUrl = java.webViewGetSource(null, baseUrl, null, \".*\\.m3u8.*\");</js>"
```

### 4. 套娃源（无法测试）

**识别特征**：
- sourceUrl 以 `legado://` 开头
- sourceUrl 格式为 `legado://import/rsssource?src=...`

**处理方式**：
- 无法直接测试，需要先解析指向的真实 URL
- 建议用户直接导入真实 URL 的源

## 创建新书源的决策流程

```
1. 访问目标网站 → 查看页面源码
   ├── 静态 HTML → 使用 CSS 选择器（优先）
   ├── JSON API → 使用 JSONPath（高效）
   └── JS 动态渲染 → 配置 WebView（必须）
2. 检查是否需要登录
   ├── 是 → 设置 loginUrl + loginUi + enabledCookieJar
   └── 否 → 继续
3. 编写规则 → 用 JVM 仿真端测试
   ├── success=true → 规则正确
   ├── needsWebView=true → 配置 WebView，用 Selenium 测试
   ├── needsUserIntervention=true → 需要用户手动登录
   └── success=false → 检查 errorStage 和 errorMessage
```
