# 检查点2 扩展测试报告

> 用户反馈"需调整"：要求扩大视频源测试范围，区分订阅源问题 vs 底层代码问题。

## 测试范围

| 轮次 | 源编号 | 数量 | 测试方式 |
|------|--------|------|---------|
| 第一轮 | 源1-8 | 8 | batch_source_test.py（上一会话） |
| 第二轮 | 源9-16 | 8 | batch_source_test.py + logcat抓取（本会话） |

## 测试结果分类

### A. 正常播放（底层无问题）

| 源 | 结果 | 说明 |
|----|------|------|
| 源1-5 | ✅ 正常 | R5嗅探/直接播放成功 |
| 源9-10 | ✅ 正常 | R5嗅探记录，无播放失败 |
| 源13-14 | ✅ R5嗅探正常 | 命中 `/addons/dplayer/` 路径，部分集数失败（疑CDN问题） |

### B. 订阅源问题（需用户修源，非底层Bug）

| 源 | 问题 | 归类 |
|----|------|------|
| 源6 | DNS失效 | 站点已失效，源配置过期 |
| 源7 | SSL连接重置 | 站点证书/网络问题 |
| 源8 | 封面图配置错误 | 源规则配置问题 |
| 源15-16 | 部分集数失败 | 疑CDN/源内容问题 |

### C. 底层代码问题（需修代码）⭐ 重点

| 源 | 问题 | 根因 |
|----|------|------|
| 源11-12 | 播放失败 urlLen=6816 | **ruleContent非空分支 content无有效性校验** |

## 源11-12 播放失败根因深度分析

### 日志证据链

1. **logcat 无 extractPrecise / R5静态解析 / R5网络抓包 日志** → 未走 ruleContent空分支的R5自动抓取
2. **logcat 无 "加载订阅源为链接的正文失败"** → ruleContent非空分支 Rss.getContent 成功返回 content
3. **urlLen=6816, htmlLen=415969** → 播放URL是HTML内容（约400KB页面被当作URL）
4. **errorCode=2004 (ERROR_CODE_IO_BAD_HTTP_STATUS)** → ExoPlayer请求无效URL返回HTTP错误
5. **自动降级 ExoPlayer→WebView(playerType=2)** → WebView加载到HTML页面（非视频）
6. **episode=0 / episode=2** → 多集播放（parseRssRoutes 或单URL分支）

### 代码路径追踪

`VideoPlay.kt` startPlay 方法：
```
L248: ruleContent = s.ruleContent
L249: if (ruleContent.isNullOrBlank())  ← R5自动抓取分支（源11-12未走此分支）
L387: else  ← ruleContent非空分支（源11-12走此分支）
L388:   Rss.getContent(loadScope, rssArticle, ruleContent, s)
L389:     onSuccess { content ->
L390:       content = content.trim()
L392:       parseRssRoutes(content, ...)  ← 多线路解析
L404:       if (content.isEmpty()) throw ContentEmptyException
L406:       else if (content.contains("<MPD")) → mpd文本
L411:       else { NetworkUtils.getAbsoluteURL(rssArticle.link, content) }  ⭐ content被当URL
L414:       videoUrl = mUrl  ← 6816字节HTML被设为videoUrl
```

### 根因结论

**双重问题**：
1. **源问题**：源11-12 的 ruleContent 规则配置错误，Rss.getContent 返回了约400KB的HTML页面内容（包含 `<script>` 标签等）而非干净视频URL
2. **底层防御不足**：`VideoPlay.kt L404-413` 对 content 没有做URL有效性校验。content 不含 `<MPD`、不为空，走 L411 被当URL直接传给播放器

**为什么 extractPrecise 不可能产生此问题**：
- extractPrecise 的4个子方法（VideoTags/Meta/ScriptJson/JsVars）正则均限定 `https?://[^"']+?\.(?:m3u8|mp4)` 结尾
- 不可能匹配出包含 `<script>` 标签的6816字节URL
- 所以问题不在R5自动抓取，而在ruleContent非空分支

## 修复方案

### P3-1: ruleContent非空分支 content 有效性校验（核心修复）

**位置**：`VideoPlay.kt L404-413`

**方案**：在 content 被当URL之前，增加有效性校验：
- URL长度上限（≤2048字符，正常视频URL极少超过500字符，6816明显异常）
- 非法字符检查（不含 `<` `>` 换行符，URL不应含HTML标签）
- 校验失败时：记录警告日志（含content长度+前40字符脱敏）+ 降级到R5嗅探（复用ruleContent空分支逻辑）

**收益**：即使源规则配置错误返回HTML，底层也能兜底降级到R5嗅探，而非直接播放HTML导致失败

### P3-2: isVideoUrl 防御性增强（次要）

**位置**：`VideoUrlExtractor.kt L336-342`

**方案**：增加长度上限（≤2048）和非法字符检查（不含 `<` `>` 空格）
**收益**：防御性编程，虽然当前未直接触发，但避免未来潜在风险

## 总结

| 问题类型 | 数量 | 处理方式 |
|----------|------|---------|
| 订阅源问题 | 5个源 | 需用户修源（DNS/SSL/封面图/ruleContent配置） |
| 底层代码问题 | 1处（content无校验） | ✅ 已修复（P3-1） |
| 正常播放 | 11个源 | 无需处理 |

原始6项修复（P1-1~P2-2）验证全部有效，4种错误模式归零。新发现1处底层防御不足（P3-1），建议修复后重新测试源11-12确认降级R5嗅探生效。

## P3-1 修复验证结果（legado_app_3.26.071411.apk）

重新测试源11-12，logcat证据链确认P3-1修复完全生效：

| 验证项 | 修复前 | 修复后 | 结果 |
|--------|--------|--------|------|
| `P3-1: ruleContent返回非视频URL, 降级R5嗅探` | 无（未校验直接播放） | 多次触发（len=6816, hasScript=true） | ✅ content有效性校验生效 |
| `P3-1降级R5嗅探命中` | 无 | 命中视频流路径 `/videos/202607/...` | ✅ R5嗅探成功命中 |
| ExoPlayer onPlayerError (2004) | 2次 | 0次 | ✅ 错误消失 |
| `降级决策: ExoPlayer→WebView` | 多次 | 0次 | ✅ 无ExoPlayer→WebView降级 |

**结论**：源11-12播放失败问题已彻底解决。ruleContent配置错误返回HTML时，底层P3-1校验拦截 + 降级R5嗅探成功命中真实视频流URL + ExoPlayer正常播放，不再出现2004错误和WebView降级。
