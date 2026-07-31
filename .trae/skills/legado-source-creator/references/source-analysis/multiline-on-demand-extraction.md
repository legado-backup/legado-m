# 多线路多集按需采集架构

> **背景**：Legado 阅读M v3.26.072420+ 新增 `ruleRoutes` 和 `ruleEpisodes` 两个字段，用于 RSS 视频源（type=2）的多线路多集按需采集。
> **核心原则**：分离线路采集和集数采集，用户切换线路/集数时才采集视频地址（按需采集），替代 ruleContent JS 全量采集模式。

## 字段说明

| 字段 | 作用 | 支持规则 | 适用场景 |
|------|------|---------|---------|
| `ruleRoutes` | 从详情页采集线路列表（线路名） | CSS/JSONPath/XPath/JS | type=2 视频源，有多线路切换需求 |
| `ruleEpisodes` | 从详情页采集集数列表（集数标题+播放页URL） | CSS/JSONPath/XPath/JS | type=2 视频源，支持 `{routeIndex}`/`{routeIndex+1}` 占位符 |

## MacCMS HTML 模板标准写法（CSS 选择器）

MacCMS HTML 模板站点通常用 `.module-player-list` 结构组织线路和集数：

```json
{
  "ruleRoutes": ".module-player-list .module-player-tab-name@text",
  "ruleEpisodes": ".module-player-list .module-player-list-content:eq({routeIndex}) a@text&&href"
}
```

**说明**：
- `ruleRoutes`：用 CSS 选择器采集所有线路名（`.module-player-tab-name` 的文本）
- `ruleEpisodes`：用 `{routeIndex}` 占位符匹配当前线路索引，采集集数标题（`@text`）和播放页 URL（`href`）

## MacCMS JSON API 模板标准写法（vod_play_from / vod_play_url）

MacCMS JSON API 站点通常返回 `vod_play_from` 和 `vod_play_url` 字段：

```json
{
  "ruleRoutes": "@js:<JSON.parse(result).vod_play_from.split('$$$').map(function(name, i){return name||'线路'+(i+1)}).join('\\n')",
  "ruleEpisodes": "@js:var d=JSON.parse(result).vod_play_url.split('$$$')[{routeIndex}];d.split('#').map(function(item){var p=item.split('$');return p[0]+'$'+p[1]}).join('\\n')"
}
```

**vod_play_from 结构**：`线路1$$$线路2$$$线路3`（用 `$$$` 分隔线路）
**vod_play_url 结构**：`第1集$url1#第2集$url2$$$第1集$url1#第2集$url2`（用 `$$$` 分隔线路，`#` 分隔集数，`$` 分隔标题和URL）

**JS 规则解析**：
- `ruleRoutes` JS：解析 `vod_play_from`，用 `$$$` 分割得到线路名数组，空名用"线路N"替代
- `ruleEpisodes` JS：用 `{routeIndex}` 占位符选择当前线路的集数段，用 `#` 分割得到集数数组，每集用 `$` 分割标题和URL

## 占位符说明

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{routeIndex}` | 当前线路索引（0-based） | 用户选择"线路1"时，routeIndex=0 |
| `{routeIndex+1}` | 当前线路索引（1-based） | 用户选择"线路1"时，routeIndex+1=1 |

## 使用规范

1. **仅 type=2 视频源使用**：`ruleRoutes`/`ruleEpisodes` 仅对 type=2（视频源）生效，其他类型源忽略
2. **ruleContent 回归单集视频 URL**：使用新字段后，`ruleContent` 不再支持返回多线路多集嵌套 JSON，仅支持单集视频 URL
3. **按需采集**：用户切换线路时，App 调用 `Rss.getEpisodesAwait(rssArticle, ruleEpisodes, routeIndex, source)` 重新采集新线路集数
4. **视频地址由统一入口采集**：`VideoUrlExtractor.extractVideoUrlForEpisode` 按 MacCMS 播放页解析 → DOM 解析 → WebView 抓包三层降级采集视频流地址
5. **老源兼容**：未配置 `ruleRoutes`/`ruleEpisodes` 的源仍使用 `ruleContent` JS 模式（兼容老版本）

## 反模式（禁止）

- ❌ 在 `ruleContent` JS 中一次性采集所有线路所有集的播放页 URL
- ❌ 在 `ruleContent` JS 中逐集请求播放页 HTML 提取 m3u8
- ❌ 在 `ruleEpisodes` 中直接采集视频流地址（m3u8/mp4），应只采集播放页 URL
- ❌ 硬编码镜像站 URL 列表（应由 `ruleRoutes` 动态采集）

## 经验来源

`[经验来源:多线路多集按需采集范式]`
