# spec.md — 视频播放问题修复第1轮

## Intent（意图）

解决用户安装最新版客户端后，订阅源视频播放出现"网页 video 标签可播放但内置播放器不可播放"的回归问题，同时修复日志深度分析发现的其他 4 类问题，提升视频播放稳定性和用户体验。

## Scope（范围）

### In Scope（纳入范围）

#### P0: ExoPlayer HLS 播放失败降级机制

- **问题**: ExoPlayer 对 HLS TS 分片的 H264 SPS NAL unit 解析过严（`ParsableNalUnitBitArray.assertValidOffset` 抛出 `IllegalStateException`），导致错误码 2000 (ERROR_CODE_IO_UNSPECIFIED)，07-12 日志中出现 265 次播放失败
- **根因**: ExoPlayer 的 `TsExtractor` 严格校验 H264 SPS 数据格式，而 WebView 的 Chromium 媒体引擎 + HLS.js 更宽容
- **修复**:
  - S0-1: ExoPlayer 失败后，**自动用 skill V2 hls-video-player.html 模板**包装视频 URL，WebView 加载播放（手动降级按钮触发）
  - S0-2: 设置中添加"播放器类型"选项（自动/内置/WebView），选 WebView 时直接用 V2 模板播放
  - S0-3: Exo2MediaPlayer.onPlayerError 补充 ERROR_CODE_IO_UNSPECIFIED (2000) 的友好提示

#### P1-1: 加密解密失败容错

- **问题**: JS 脚本执行时 `IllegalBlockSizeException: DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH`（AES/DES 解密数据长度不是块整数倍）
- **修复**: 增强错误提示（告知用户哪个源解密失败）+ 容错处理（解密失败时不崩溃）

#### P1-2: ClassCastException 类型容错

- **问题**: `java.lang.String cannot be cast to java.util.List`，rss 获取内容时类型转换失败
- **修复**: 增加类型容错处理（String→List 安全转换）

#### P2-1: 网络连接问题优化

- **问题**: Connection reset / SocketTimeoutException / ConnectException（部分域名 DNS 解析失败）
- **修复**: 增强网络重试机制（对 Connection reset 自动重试）

#### P2-2: 源格式问题容错

- **问题**: "链接参数 JSON 格式不规范，请改为规范格式"
- **修复**: 增强 JSON 格式容错（对不规范的链接参数提供降级处理）

### Out of Scope（排除范围）

- **自定义 TsExtractor**: 不修改 ExoPlayer 的 TS 解析逻辑（工作量太大，且 ExoPlayer 不提供"宽容模式"选项）
- **自动降级到 WebView**: 不实现 ExoPlayer 失败后自动切换 WebView（实现复杂，需管理两个播放器生命周期，留待后续优化）
- **源质量问题修复**: 不修复源本身的 JS 脚本/格式问题（App 层面只做容错）
- **书源视频播放**: 仅修复订阅源（RssSource）视频播放，不涉及书源（BookSource）

## Approach（方案）

### 核心方案: P0 ExoPlayer 失败降级（使用 skill V2 模板）

采用 **手动降级（V2 模板）+ 配置选项** 组合方案：

1. **手动降级（S0-1）**: ExoPlayer 播放失败时，错误提示中添加"使用 WebView 播放"按钮，用户点击后**使用 skill 中的 V2 hls-video-player.html 模板**包装视频 URL，WebView 加载播放
2. **配置选项（S0-2）**: 设置中添加"播放器类型"选项（自动/内置/WebView），选 WebView 时直接用 V2 模板播放
3. **友好提示（S0-3）**: 补充 ERROR_CODE_IO_UNSPECIFIED (2000) 的友好提示

### 为什么使用 skill V2 模板而非简单 video 标签

| 对比项 | 简单 video 标签 | skill V2 模板（774行） |
|--------|---------------|----------------------|
| HLS.js 核心 | ❌ 无 | ✅ v1.4.12 稳定版 |
| 进度条系统 | ❌ 无 | ✅ 播放进度+缓冲进度双显示 |
| 快进快退 | ❌ 无 | ✅ 6按钮（±30s/1m/3m） |
| 倍速播放 | ❌ 无 | ✅ 1x/3x/5x/10x/15x |
| 全屏控制 | ❌ 无 | ✅ requestFullscreen + 状态监听 |
| 横竖屏反转 | ❌ 无 | ✅ 90°/180°/270° 旋转 |
| 上下集切换 | ❌ 无 | ✅ 多视频地址支持 |
| 错误自动重试 | ❌ 无 | ✅ NETWORK_ERROR → startLoad / MEDIA_ERROR → recoverMediaError |
| 响应式设计 | ❌ 无 | ✅ @media 768px 断点 |

### 为什么选 V2 而非 V1/V3

| 版本 | 适用场景 | 是否适合降级 |
|------|---------|------------|
| V1 自动抓取 | 从 HTML 提取视频 URL | ❌ 降级场景已有视频 URL，不需要提取 |
| **V2 手动输入** | 已知视频 URL，直接加载 | ✅ **降级场景已有视频 URL，最适合** |
| V3 注入式 | 劫持已有播放器实例 | ❌ ExoPlayer 失败后没有已有播放器可劫持 |

### 内容规则（ruleContent）填写方式

**核心原则：用户不需要修改 ruleContent**

| 播放器类型 | ruleContent 填写方式 | App 处理逻辑 |
|-----------|---------------------|-------------|
| type=2（内置播放器） | 返回视频 URL | ExoPlayer 直接播放 |
| type=0（WebView 模式） | 返回 HTML 页面 | WebView 渲染 HTML |
| **降级模式（新增）** | **仍返回视频 URL（type=2）** | **App 自动用 V2 模板包装视频 URL，WebView 加载** |

**降级流程**：
1. 用户 ruleContent 仍返回视频 URL（type=2，无需修改）
2. ExoPlayer 尝试播放失败（错误码 2000）
3. 用户点击"使用 WebView 播放"
4. App 读取 V2 模板，替换 `{{result}}` 为视频 URL，`{{videoTitle}}` 为标题
5. WebView 加载替换后的 HTML，Chromium + HLS.js 播放

### Alternatives Considered（备选方案）

#### 方案A: 自动降级（ExoPlayer 失败后自动切换 WebView）

- **优点**: 用户体验最好，无需干预
- **缺点**: 实现复杂，需管理 ExoPlayer 和 WebView 两个播放器的生命周期；自动切换可能导致用户困惑
- **不采用原因**: 实现复杂度高，先用手动降级快速解决问题，后续可考虑

#### 方案B: 修复 ExoPlayer TS 解析（自定义 TsExtractor）

- **优点**: 从根本解决问题
- **缺点**: ExoPlayer 的 TsExtractor 不提供"宽容模式"选项；需要自定义 Extractor 并 fork ExoPlayer，工作量大
- **不采用原因**: 工作量太大，且 ExoPlayer 不支持配置宽容模式

#### 方案C: 仅使用 WebView 播放（放弃 ExoPlayer）

- **优点**: 兼容性最好
- **缺点**: 丢失 ExoPlayer 的优势（原生缓存/硬件解码/调试信息）；用户体验降级
- **不采用原因**: 因噎废食，ExoPlayer 对大多数源仍是最优选择

### Drawbacks（ drawbacks）

1. **手动降级需用户干预**: 用户需要点击"使用 WebView 播放"按钮，不够智能
2. **WebView 模式需要网络加载 HLS.js**: 首次加载需要从 CDN 下载 hls.js（约 200KB），后续有缓存
3. **配置选项可能被忽略**: 用户可能不知道有"播放器类型"配置选项
4. **P1/P2 修复为容错而非根治**: 加密解密失败/类型转换异常的根因在源本身，App 层面只能容错

## Requirements（需求）

### R1: ExoPlayer 失败降级机制（使用 skill V2 模板）

- **R1.1**: ExoPlayer 播放失败时，错误提示对话框中显示"使用 WebView 播放"按钮
- **R1.2**: 用户点击"使用 WebView 播放"后，使用 skill V2 hls-video-player.html 模板包装视频 URL，WebView 加载播放
- **R1.3**: WebView 播放模式下显示"切换回内置播放器"按钮
- **R1.4**: WebView 播放模式复用 V2 模板的完整功能（进度条/倍速/全屏/横竖屏/上下集/错误重试）
- **R1.5**: WebView 播放模式正确处理 Referer/Header（通过 HLS.js xhrSetup 注入）

### R2: 播放器类型配置

- **R2.1**: 设置中添加"播放器类型"选项（自动/内置播放器/WebView）
- **R2.2**: "自动"模式默认使用内置播放器，失败后提示降级
- **R2.3**: "内置播放器"模式始终使用 ExoPlayer
- **R2.4**: "WebView"模式始终使用 V2 模板播放

### R3: 错误处理优化

- **R3.1**: Exo2MediaPlayer.onPlayerError 补充 ERROR_CODE_IO_UNSPECIFIED (2000) 的友好提示
- **R3.2**: 加密解密失败时显示源名称，便于用户定位问题源
- **R3.3**: ClassCastException 时进行类型容错（String→List 安全转换）
- **R3.4**: 网络连接问题（Connection reset）自动重试

### R4: 源格式容错

- **R4.1**: 链接参数 JSON 格式不规范时提供降级处理（尝试解析非标准 JSON）

## Scenarios（场景）

### 场景1: ExoPlayer 播放失败后手动降级（使用 V2 模板）

```
前置: 用户打开订阅源视频，使用内置播放器（type=2，ruleContent 返回视频 URL）
1. ExoPlayer 尝试播放 m3u8
2. H264 SPS 解析失败，错误码 2000
3. 显示错误提示对话框："播放失败 - 视频格式不兼容，可尝试使用 WebView 播放"
4. 对话框显示"使用 WebView 播放"按钮
5. 用户点击按钮
6. App 读取 V2 模板，替换 {{result}} 为视频 URL，{{videoTitle}} 为标题
7. WebView 加载替换后的 HTML
8. Chromium + HLS.js 播放视频，显示进度条/倍速/全屏等控件
```

### 场景2: 用户预先选择 WebView 播放器

```
前置: 用户已知某订阅源内置播放器不兼容
1. 用户进入设置 → 视频播放设置
2. 将"播放器类型"改为"WebView"
3. 返回订阅源，打开视频
4. App 直接用 V2 模板包装视频 URL，WebView 加载播放
5. 无需等待 ExoPlayer 失败
```

### 场景3: 加密解密失败容错

```
前置: 订阅源的 JS 脚本解密逻辑有问题
1. 用户加载订阅源内容
2. JS 脚本执行解密时抛出 IllegalBlockSizeException
3. App 显示错误提示："订阅源 XXX 解密失败，请联系源作者修复"
4. App 不崩溃，用户可继续使用其他源
```

### 场景4: ClassCastException 类型容错

```
前置: 订阅源的 ruleContent 返回 String 但代码期望 List
1. 用户加载订阅源内容
2. 类型转换时检测到 String，不抛出 ClassCastException
3. 自动将 String 包装为单元素 List
4. 内容正常显示
```
