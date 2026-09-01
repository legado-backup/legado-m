# 视频订阅源专项陷阱

> 视频源（type=2）特有的陷阱，含URL转换/嗅探/播放页链路/导入验证/MacCMS解析等。

## 陷阱40: `##` 字符串替换操作符（URL转换利器）

Legado 规则引擎支持 `##` 操作符对提取的字符串进行替换，语法 `规则##旧字符串##新字符串`。

**适用场景**：
1. 列表链接是详情页，需要转换为播放页URL模式
2. URL 路径段替换（如 `/detail/` → `/play/`）
3. 去掉 URL 后缀（如 `##.html##` 去掉 .html）

**示例**：`ruleLink = "a@href##info##play"` 将 `/info/` 替换为 `/play/`

**优势**：比 JS 方案更稳定（不依赖 Rhino 引擎），更简单（无需正则匹配），更正确（直接字符串替换）

## 陷阱41: 嗅探模式（ruleContent 为空触发内置播放器嗅探）

视频订阅源中 `ruleContent` 设为空字符串 `""` 时，Legado 内置播放器会自动嗅探播放页的视频地址（m3u8/mp4）。

**适用场景**：
1. 播放页是标准 HTML 含 `<video>` 或 m3u8 流
2. 视频地址通过 JS 动态加载

**不适用**：
1. 视频地址需要复杂 JS 解密
2. 播放页需要登录或 cookie

**⚠️ 优先级澄清（修正 2026-08-02）**：嗅探（ruleContent=""）是**兜底方案（P4）而非首选**。视频地址提取严格遵循 SKILL.md 偏好优先级：**P1 CMS API（ac=detail&ids）→ P2 播放页内联 JS 正则提取（见陷阱41b）→ P3 XPath/CSS 选择器 → P4 嗅探兜底**。不要因为"ruleContent 留空最简单"就直接选嗅探——嗅探慢、耗电、依赖网络抓包且可能误抓广告流；能正则提取到内联 `var url="..."` 就优先用规则提取。

## 陷阱41b: 播放页内联 JS 变量正则提取（P2 首选方案）

当播放页 HTML 中直接内联视频地址变量（如 xgplayer/自有播放器常写 `var url = "https://.../index.m3u8?sign=..."`），用正则直接提取，**优于**嗅探。

**提取模板**：
```json
{
  "ruleContent": "@js:(function(){var m=result.match(/var url = \"([^\"]+)\"/);return m?m[1]:'';})()"
}
```

**要点**：
1. 变量名/引号以真实页面为准，先 Playwright 在播放页查 `var url =` / `var playUrl =` / `domainPlay` 等特征
2. 若 `ruleContent` 规则里 JS 拿到的 `result` 是解码后的播放页 HTML（见 document.write 编码陷阱），先解码再 match
3. 提取的 m3u8 常带动态 sign 参数（每次刷新页面变化），**无需固定**——每次播放都重新请求播放页提取即可
4. 验证：`java.ajax` / curl 带 Referer 抓 m3u8 URL 返回 `#EXTM3U` 即有效
5. 若 m3u8 流是 AES-128 加密（`#EXT-X-KEY METHOD=AES-128`），Legado ExoPlayer 会自动处理 key URI，规则无需干预

**经验来源**：`[经验来源:播放页内联变量正则提取范式]`

## 陷阱42: 播放页链路验证（列表链接≠播放页）

视频网站常见三层结构"列表页→详情页→播放页"，列表链接往往指向详情页（无视频），需要点击触发才到播放页。

**Phase 1 必经验证**：
1. 用 Playwright 点击列表项，落地页是否直接含 `<video>` 或 m3u8 流
2. 若落地页是详情页，分析"详情页→播放页"跳转规律（URL模式差异/按钮选择器/href 属性）
3. 优先用 `##` 操作符转换 URL（如 `/info/` → `/play/`），次选 JS 提取播放页 URL

**禁止**：假设列表链接直接是播放页，必须验证

## 陷阱43: 导入源后必须验证写入（DELETE+INSERT 不可靠）

`import_rss_source.py` 用 DELETE + INSERT 方式更新源，但 WAL 模式下可能被旧 WAL 覆盖导致更新失败。

**强制验证流程**：
1. 导入后用 `SELECT ruleLink, ruleContent FROM rssSources WHERE sourceUrl = ?` 确认字段值是最新版
2. 若仍是旧版，直接用 Python sqlite3 操作：DELETE + INSERT OR REPLACE + COMMIT + PRAGMA wal_checkpoint(TRUNCATE)
3. push 回设备前必须 force-stop App + 删除设备端 WAL/SHM
4. push 后必须 `chown <uid>:<uid>` + `chmod 660`（uid 从 `adb shell dumpsys package <pkg> | grep userId=` 获取）

**反模式**：信任脚本返回的"导入成功"而不验证实际字段值

## 陷阱49: 视频播放URL转换完整链路（`##` 操作符）

视频网站列表链接常指向详情页（含视频信息但无视频流），需要转换为播放页URL。

**方案**：ruleLink 用 `a@href##info##play`（Legado字符串替换操作符 `##`），将列表链接 `/info/{id}.html` 替换为 `/play/{id}.html`。

**ruleContent 留空**：让内置播放器嗅探播放页的 m3u8 请求（见陷阱41嗅探模式）

**完整链路**：列表页 → ruleLink 转换URL → 播放页 → ruleContent="" 嗅探 → m3u8 播放

**经验来源**：`[经验来源:URL转换范式]`

## 陷阱60: MacCMS 多线路多集免 JS 标准写法（routes 规范化 + 列表范式）

MacCMS 采集站多线路多集是扁平编码字符串（`$$$` 分线路、`#` 分集、`$` 分名址），**解析层自动规范化**——源规则零 JS：

```json
{
  "type": 2,
  "ruleArticles": "$.list[*]",
  "ruleTitle": "$.vod_name##\\.mp4$",
  "ruleImage": "$.vod_pic",
  "ruleLink": "https://{API域名}/api.php/provide/vod?ac=detail&ids={{$.vod_id}}",
  "ruleRoutes": "$.routes[*].name",
  "ruleEpisodes": "$.routes[{routeIndex}].episodes",
  "ruleContent": ""
}
```

**要点**：
1. `{{$.vod_id}}` 大括号模板拼详情**绝对 URL**（相对路径会被 isUrl 拼接出错误地址）
2. `{routeIndex}` 占位符（0-based）切线路时注入，对五种解析模式透明
3. ruleContent 留空走多线路模式（集数地址由 ruleEpisodes 直出）
4. 兜底旧写法仍可用：`$.list[0].vod_play_url`（隐式 `$$$` 分组）或 `##\$\$\$##\n` replaceRegex 转行

**经验来源**：`[经验来源:rss-cms-multiroute-nojs 2026-09-01]`

## 陷阱61: 采集站 UA 限流——列表只剩 1 条数据 ⚠️ 高频

**现象**：列表只有 1 条、分页消失；logcat `bodyLen=2226`（正常应几十~几百 KB）；本机/模拟器 curl 同 URL 却正常（305KB）。
**根因**：采集站 CDN/WAF 按客户端指纹（应用默认 UA）返回受限响应。
**修复**：源 `header` 配浏览器 UA：
```json
"header": "{\"User-Agent\": \"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36\"}"
```
**验证**：logcat `RSS自定义规则解析完成 文章数=20`（≥10 正常；=1 即命中）。

**经验来源**：`[经验来源:rss-cms-multiroute-nojs 2026-09-01]`

## 陷阱62: MacCMS 父分类（type_pid=0）无数据

sortUrl 枚举一级分类（电影/连续剧等 type_pid=0）时，列表响应仅 81 字节（`list:[]`）——实际内容在**子分类**。生成 sortUrl 前先 `GET /api.php/provide/vod` 看 class 数组的 type_pid，只枚举子分类；同时按内容政策过滤不合适分类。

**经验来源**：`[经验来源:rss-cms-multiroute-nojs 2026-09-01]`

## 陷阱63: sortUrl 页码占位符必须 `{{page}}` 双括号

单括号 `{page}` 不被 AnalyzeUrl 替换，原样发出导致站点 System Error（HTML 响应，列表空）。分类分隔符用 `&&&`（解析已修复 `&&` 优先级残留 `&` 问题），名址用 `::`。

**经验来源**：`[经验来源:rss-cms-multiroute-nojs 2026-09-01]`

## 陷阱64: ruleLink 详情链接必须用 `ids=` 参数

`?ac=detail&ids={vod_id}` 才是单条详情；直接用列表页 URL 当详情会因 normalize 只取 list[0] 而**张冠李戴**（点 A 影片出 B 影片）。同时列表页响应与详情响应字段有差异（列表项可能缺 vod_content 等），详情数据以 ids 响应为准。

**经验来源**：`[经验来源:rss-cms-multiroute-nojs 2026-09-01]`
