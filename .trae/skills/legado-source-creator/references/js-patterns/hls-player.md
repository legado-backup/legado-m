# 自定义 HLS 视频播放器模式

> 当视频源使用 DPlayer + m3u8 格式时，Legado 内置播放器无法直接播放，需要拼装自定义 HTML 播放器。

### 核心思路

1. 从详情页 HTML 中提取 `data-config='...'` 中的视频 URL
2. 拼装包含 hls.js 的 HTML 页面
3. **type 必须为 0**（WebView 渲染），不能用 type=2（内置播放器）

### 完整模板（含标题+视频地址展示）

```javascript
@js:var doc=org.jsoup.Jsoup.parse(result);
var titleEl=doc.select('h1.post-title');
var title=titleEl&&titleEl.size()>0?titleEl.first().text():'';
var m=result.match(/data-config='([^']+)'/);
if(m){
  var c;
  try{c=JSON.parse(m[1]);}
  catch(e){c=JSON.parse(m[1].replace(/&quot;/g,'"').replace(/&amp;/g,'&'));}
  var u=c.video.url;
  var h='<!DOCTYPE html><html><head><meta charset="UTF-8">';
  h+='<meta name="viewport" content="width=device-width,initial-scale=1">';
  h+='<script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.12"><\/script>';
  h+='<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#111;color:#fff;font-family:sans-serif}';
  h+='.info{padding:8px 12px;background:#1a1a1a}.info h2{font-size:15px;margin:0 0 6px 0;line-height:1.4}';
  h+='.url-box{display:flex;align-items:center;gap:6px}';
  h+='.url-box input{flex:1;padding:6px 8px;background:#222;color:#0f0;border:1px solid #444;border-radius:4px;font-size:12px;font-family:monospace}';
  h+='.url-box button{padding:6px 12px;background:#2563eb;color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;white-space:nowrap}';
  h+='video{width:100%;max-height:45vh;background:#000}';
  h+='.bar{padding:8px;background:#1a1a1a;display:flex;flex-wrap:wrap;gap:4px}';
  h+='.bar button,.bar select{padding:4px 8px;background:#333;color:#fff;border:1px solid #555;border-radius:4px;font-size:12px;cursor:pointer}</style>';
  h+='</head><body>';
  h+='<div class="info">';
  if(title){h+='<h2>'+title+'</h2>';}
  h+='<div class="url-box"><input id="vu" value="'+u+'" readonly onclick="this.select()"><button onclick="cp()">复制</button></div>';
  h+='</div>';
  h+='<video id="v" controls autoplay muted playsinline></video>';
  h+='<div class="bar">';
  h+='<button onclick="sk(-180)">←3m</button>';
  h+='<button onclick="sk(-60)">←1m</button>';
  h+='<button onclick="sk(-30)">←30s</button>';
  h+='<button onclick="sk(30)">30s→</button>';
  h+='<button onclick="sk(60)">1m→</button>';
  h+='<button onclick="sk(180)">3m→</button>';
  h+='<select onchange="v.playbackRate=parseFloat(this.value)">';
  h+='<option value="1">1x</option><option value="2">2x</option><option value="3">3x</option>';
  h+='<option value="5">5x</option><option value="10">10x</option>';
  h+='</select>';
  h+='<button onclick="v.requestFullscreen&&v.requestFullscreen()">全屏</button>';
  h+='</div>';
  h+='<script>var v=document.getElementById("v"),url="'+u+'";';
  h+='function init(s){';
  h+='if(Hls.isSupported()){var h=new Hls();h.loadSource(s);h.attachMedia(v);';
  h+='h.on(Hls.Events.MANIFEST_PARSED,function(){v.play()})}';
  h+='else if(v.canPlayType("application/vnd.apple.mpegurl")){v.src=s;v.play()}';
  h+='}if(url&&url.indexOf("m3u8")>-1)init(url);';
  h+='function sk(s){v.currentTime+=s}';
  h+='function cp(){var i=document.getElementById("vu");i.select();document.execCommand("copy")}';
  h+='<\/script></body></html>';h;
}else{var b=doc.select('[itemprop=articleBody]');b&&b.size()>0?b.first().html():result;}
```

### 关键设计要点

| 要素 | 设计 | 原因 |
|------|------|------|
| 标题显示 | `h1.post-title` 提取，显示在播放器上方 | 知道当前视频是什么内容 |
| 视频地址 | 绿色等宽字体 input，点击全选 | 一键复制真实 m3u8 地址，方便用其他工具下载 |
| 复制按钮 | `document.execCommand("copy")` | Android WebView 兼容的复制方式 |
| 倍速播放 | select 下拉 1x~10x | 快速浏览长视频 |
| 跳进跳退 | 6 个按钮覆盖 ±30s/1m/3m | 精确定位 |
| autoplay + muted | 自动播放但静音 | 浏览器策略要求静音才能自动播放 |

### 完整版播放器模板（实战案例：91短视频）

> 用户优化版本包含约 20000 字符的完整 HLS.js 播放器，以下是关键功能设计。

**完整版功能清单**：

| 功能 | 实现 | 用户价值 |
|------|------|----------|
| 视频进度条 | CSS + JS 实时更新 | 可视化播放进度和缓冲状态 |
| 快进/快退 | 6 个按钮（±30s/1m/3m）| 精确定位关键片段 |
| 倍速播放 | 1x/3x/5x/10x/15x | 快速浏览长视频 |
| 全屏按钮 | `requestFullscreen()` | 更好的观看体验 |
| 上一集/下一集 | 视频源数组 + 索引切换 | 多集视频无缝切换 |
| 视频源选择 | select 下拉框 | 多视频源时自由选择 |
| 显/隐信息 | toggle 按钮 | 隐藏标题等信息，专注视频 |
| 错误重试 | HLS.js Events.ERROR 处理 | 自动恢复播放 |

**ruleContent 提取逻辑**：
```javascript
class.player-wrapper@all
<js>
var reg = /[?&]url=([^"&\s]+)/i;
var match = result.match(reg);
result = match ? match[1] : '';
</js>
<!DOCTYPE html>
<!-- V2.20260606.1 -->
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="dns-prefetch" href="//cdn.jsdelivr.net">
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.12"></script>
<!-- 完整 CSS 样式 -->
<style>
/* 视频进度条样式 */
.video-progress-bar { position: relative; height: 4px; background: #333; }
.video-buffer-progress { height: 100%; background: #666; width: 0%; }
.video-progress { height: 100%; background: #ff4444; width: 0%; }
/* 其他样式... */
</style>
</head>
<body>
<div id="container">
  <h3 id="title">视频播放</h3>
  <div id="video-wrapper">
    <div class="video-progress-bar">
      <div class="video-buffer-progress" id="video-buffer-progress"></div>
      <div class="video-progress" id="video-progress"></div>
    </div>
    <video id="video-element" controls preload="auto" autoplay muted>
      <source id="video-source" src="" type="">
    </video>
  </div>
  <div id="video-url"></div>
  <div id="video-controls-bar">
    <button id="skip-3m">←3m</button>
    <button id="skip-1m">←1m</button>
    <button id="skip-30s">←30s</button>
    <button id="skip-plus30s">30s→</button>
    <button id="skip-plus1m">1m→</button>
    <button id="skip-plus3m">3m→</button>
    <select id="playback-rate-select">
      <option value="1.0">1x</option>
      <option value="3.0">3x</option>
      <option value="5.0">5x</option>
      <option value="10.0">10x</option>
      <option value="15.0">15x</option>
    </select>
    <button id="fullscreen-btn">全屏</button>
  </div>
  <div id="video-source-container" style="display: none;">
    <button id="prev-video-btn">上一集</button>
    <select id="video-source-select"></select>
    <button id="next-video-btn">下一集</button>
  </div>
  <div id="toggle-buttons">
    <button id="toggle-messages-btn">显/隐信息</button>
  </div>
</div>
<script>
// HLS.js 初始化逻辑
var video = document.getElementById('video-element');
var hls = new Hls();
hls.loadSource('提取的m3u8_URL');
hls.attachMedia(video);
hls.on(Hls.Events.MANIFEST_PARSED, function() { video.play(); });
// 错误重试
hls.on(Hls.Events.ERROR, function(event, data) {
  if (data.fatal) { hls.startLoad(); }
});
// 进度条更新
video.addEventListener('timeupdate', function() {
  var progress = (video.currentTime / video.duration) * 100;
  document.getElementById('video-progress').style.width = progress + '%';
});
video.addEventListener('progress', function() {
  var buffered = (video.buffered.end(0) / video.duration) * 100;
  document.getElementById('video-buffer-progress').style.width = buffered + '%';
});
// 其他控制逻辑...
</script>
</body>
</html>
```

**关键经验**：
- 视频订阅源的核心价值是**用户体验**，不能只提取 URL
- 完整播放器模板约 20000 字符，但用户价值巨大
- type 必须为 0，让 WebView 渲染 HTML 播放器

### 🔴 完整播放器模板文件（推荐直接复用）

> **已保存为独立模板文件，后续开发视频播放器时直接复用！**

**模板位置**：[templates/hls-video-player.html](../../templates/hls-video-player.html)

**模板功能清单**（774行，21070字符）：

| 功能模块 | 实现细节 | 用户价值 |
|----------|----------|----------|
| **视频标题** | `{{videoTitle}}` 模板变量 + 自动显示 | 知道当前播放的是什么内容 |
| HLS.js 核心 | v1.4.12 稳定版 + 完整缓冲配置 | 流畅播放 m3u8 流 |
| 进度条系统 | 播放进度 + 缓冲进度双显示 | 可视化播放状态 |
| 快进快退 | 6 按钮（±30s/1m/3m）+ 消息提示 | 精确定位片段 |
| 倍速播放 | 1x/3x/5x/10x/15x 五档 | 快速浏览长视频 |
| 全屏控制 | requestFullscreen + 状态监听 | 沉浸式观看 |
| **横竖屏反转** | 90°/180°/270° 旋转 + 自适应宽高 | 横屏观看竖屏视频 |
| 上下集切换 | 视频源数组 + 上一集/下一集按钮 | 多集无缝切换 |
| 视频源选择 | select 下拉框 + 动态填充 | 多源自由选择 |
| 错误自动重试 | NETWORK_ERROR → startLoad / MEDIA_ERROR → recoverMediaError | 自动恢复播放 |
| 响应式设计 | @media 768px 断点 + 字体/按钮自适应 | 手机端友好 |
| 显/隐信息 | toggle 按钮 + messages/debug 控制 | 专注视频内容 |
| 版权信息 | 与显/隐按钮同行居右 + 字体小一号 | 标注作者版本 |

**使用方法**：

1. **在 ruleContent 中引用模板**：
   ```javascript
   // 第一步：提取视频标题（可选）
   class.title-area@text  // 或其他选择器提取标题
   <js>
   var videoTitle = result;  // 保存标题
   java.put('videoTitle', videoTitle);  // 缓存标题
   result;  // 继续传递
   </js>

   // 第二步：提取视频地址
   class.player-wrapper@all  // 提取包含视频地址的元素
   <js>
   var videoTitle = java.get('videoTitle') || '';  // 获取缓存的标题
   var reg = /[?&]url=([^"&\s]+)/i;  // 正则提取视频 URL
   var match = result.match(reg);
   var videoUrl = match ? match[1] : '';

   // 第三步：拼装 HTML（读取模板文件内容）
   var html = '粘贴 templates/hls-video-player.html 的完整内容';
   html = html.replace('{{videoTitle}}', videoTitle);
   html = html.replace('{{result}}', videoUrl);
   result = html;
   </js>
   ```

2. **模板变量说明**：
   | 变量 | 用途 | 提取方式 |
   |------|------|----------|
   | `{{videoTitle}}` | 视频标题，显示在播放器顶部 | CSS 选择器提取 `h1@text` / `.title@text` 等 |
   | `{{result}}` | 视频地址（m3u8/mp4） | 正则提取 / CSS 选择器 / JS 解析 |

3. **type 必须设置为 0**：
   ```json
   {
     "sourceType": 0,  // 网页模式，WebView 渲染 HTML 播放器
     "ruleContent": {
       "content": "@js:...完整模板HTML..."
     }
   }
   ```
   ⚠️ **禁止使用 type=2**：type=2 会尝试用内置播放器直接播放 ruleContent 返回的字符串（当作视频 URL），导致播放失败

3. **支持多视频地址**：
   - 模板自动解析逗号/换行分隔的多个地址
   - 自动显示"上一集/下一集"按钮
   - 自动填充视频源选择下拉框

4. **自定义配置**（可选）：
   ```javascript
   var config = {
       skipIntroSeconds: 0,    // 跳过片头秒数
       showDescription: false, // 是否显示描述
       hlsJsConfig: {          // HLS.js 缓冲配置
           maxBufferLength: 180,
           maxBufferSize: 200 * 1024 * 1024,
           // ...完整配置见模板
       }
   };
   ```

**模板优势**：

| 对比项 | 简单版（只提取 URL） | 完整版模板 |
|--------|---------------------|------------|
| 视频标题 | ❌ 无 | ✅ 从网页提取并显示 |
| 用户体验 | ❌ 需手动复制 URL 到播放器 | ✅ 直接在 App 内播放 |
| 进度控制 | ❌ 无 | ✅ 进度条 + 快进快退 |
| 倍速播放 | ❌ 无 | ✅ 1x~15x 五档 |
| 多集切换 | ❌ 无 | ✅ 上一集/下一集 |
| 错误恢复 | ❌ 无 | ✅ 自动重试 |
| 手机适配 | ❌ 无 | ✅ 响应式设计 |

**后续开发规范**：

> ⚠️ **强制要求**：后续开发视频订阅源时，**必须优先使用此完整模板**，不得简化为只提取 URL 的版本。用户观看体验是视频源的核心价值。

- 新建视频源时，直接复制模板文件内容
- 根据目标网站调整视频 URL 提取逻辑（正则/CSS/JS）
- 保持所有公共功能（进度条、倍速、全屏、上下集）不变
- 仅在必要时调整 config 配置（如跳过片头）

### 🔴 三版本视频播放器体系

> 视频播放器模板现已形成完整的三版本体系，根据不同场景选择对应版本。

| 版本 | 模板文件 | 适用场景 | type |
|------|----------|----------|------|
| V1 | [auto-video-player.html](../../templates/auto-video-player.html) | 自动抓取：从网页 HTML 提取视频 URL 并播放 | 0 |
| V2 | [hls-video-player.html](../../templates/hls-video-player.html) | 手动输入：已知视频 URL，直接加载播放 | 0 |
| V3 | [inject-video-player.js](../../templates/inject-video-player.js) | 注入优化：劫持已有播放器实例，优化缓冲+去广告 | 0（webJs注入） |

**选择指南**：
- 视频URL可从HTML直接提取 → V1
- 视频URL已知 → V2
- 视频URL需JS运行时生成/带加密参数 → V3
- 前两种方式都抓不到 → V3

详细文档：
- V1: [auto-video-player.md](./auto-video-player.md)
- V3: [inject-video-player.md](./inject-video-player.md)
