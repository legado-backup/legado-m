# spec.md — 视频下载与下载管理整合

## Intent

让「下载管理」从当前"只有页面、无内容入口、仅系统下载"的死角，变成用户在视频播放器中即可触发的完整下载能力：

- 新增播放器下载按钮，下载当前播放视频，默认以视频标题命名。
- 用自研多线程分片引擎（IDM 式）替代系统 DownloadManager 实现快速下载。
- m3u8 流下载完成后转 mp4 并清理分片。
- 下载任务继续在现有下载管理页中管理（正在/完成等分类）。

## Scope

### In Scope
- 视频播放器右侧操作栏新增「下载」按钮。
- 自研直链多线程分片下载引擎（Range 并发 Part 下载 + 合并）。
- m3u8 分片下载 → ts 合并 → mp4 重封装 → 清理中间文件。
- DownloadService / DownloadState 改造：由系统 DownloadManager 切换到自研引擎，保持状态视图兼容。
- 下载管理页（DownloadManageActivity/Screen）任务操作（暂停/重试/删除/打开/清理）适配新引擎。

### Out of Scope
- 不打包 ffmpeg（原生库体积与授权成本，改用平台 API，见 AD-02）。
- 不引入 media3 下载模块（无法导出明文 mp4，HLS→mp4 不支持，见 Alternatives）。
- 不处理 DRM（Widevine 等）加密流；AES-128 加密分片下载暂不支持（见 Drawbacks）。
- 不改写下载管理页 Compose UI 框架，仅换数据源。
- 不新增「视频下载」独立于下载管理的第二个入口体系。

## Approach

### Selected Approach

**自研下载引擎 + 平台媒体 API，两段式下载（直链 / m3u8）。**

1. **入口**：`VideoFragment` 的 `right_buttons` 容器中，在 `btnFullscreen/btnStar/btnSettings` 附近新增 `btnDownload`。点击时读取 `VideoPlay.videoUrl`（已解析的当前播放地址）、防盗链 headers、`VideoPlay.videoTitle`（默认文件名）发起下载，并跳转/提示进入下载管理页。
2. **直链多线程分片**：新建自研分片下载核心，复用现有 OkHttp/Cronet 网络栈：
   - HEAD/GET 探测 `Accept-Ranges` / 206 支持。支持 → 按配置并发数（默认 3）切分 `Range: bytes=start-end` 多片并行下载到 `.partN` 临时文件；全部成功按序合并成目标文件并删除 Part。不支持 → 降级单线程整段下载。
   - 支持暂停（记录已下载偏移可分片续传）/ 取消（清理 Part）。
3. **m3u8 转 mp4**：解析 m3u8 master/playlist → 选择主码流 / 当前分辨率 → 并发下载 ts 分片（复用防盗链头）→ 顺序拼接为单个 `.ts` → 用 Android 平台 `MediaExtractor` 解封装 + `MediaMuxer` 重封装为 `.mp4`（PTS 连续性按分片累积偏移矫正）→ 删除 `.ts` 及 ts 分片、清单临时文件。
4. **状态解耦**：`DownloadService`/`DownloadState` 从系统 `DownloadManager` 解耦到自研引擎，`DownloadState` 维持任务状态源，`DownloadManageActivity` 轮询/过滤逻辑基本保留。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 打包 ffmpeg 做 m3u8→mp4 | 直接、转换质量高、支持任意封装 | APK 体积 +30~80MB（各 ABI 原生库），授权需按 LGPL 拆分，对一个阅读器应用过重；不采纳 |
| 引入 media3 `exoplayer-downloader` | 官方 HLS 下载器 | 输出为 ExoPlayer 私有缓存格式，不能得到可拷贝的明文 mp4；HLS→mp4 不提供；不采纳 |
| 只合并 ts 不改封装（改名 .mp4） | 实现最简单 | 容器仍是 MPEG-TS，非用户要求的真实 mp4，部分播放器/编辑场景兼容差；不采纳 |
| 继续用系统 DownloadManager | 零开发量 | 单一系统级队列，不能并发分片、不能 m3u8 转 mp4、进度类型受限；已证明无法满足需求；不采纳 |

### Drawbacks

| 已知缺点 | 接受理由 |
|---------|---------|
| 自研引擎需处理边界场景（非 Range 服务器、断点续传、网络抖动） | 项目已有 OkHttp/Cronet 重试与降级经验（ExoPlayerHelper）；收益远大于风险 |
| `MediaExtractor`/`MediaMuxer` 对部分非常规 HLS（如 PTS 不连续、非标准编码、无音频轨）存在抛异常/时间轴跳变风险 | 常规 VOD m3u8（H.264+AAC）均能正确处理；异常时回退为保留合并后的 `.ts` 并提示，保证"下载成功不丢数据" |
| AES-128 加密分片、DRM 流需额外解密链路，本期不支持 | 绝大多数公开 HLS 为明文；加密流提示"暂不支持加密流下载"，播放不受影响 |
| 直链分片下载在极少数仅支持顺序请求的服务器上会退化为单线程，速度不及多片 | 这是协议层面限制而非实现缺陷；已正确降级 |

### Prior Art
- ExoPlayerHelper 已有 HLS sniff（`C.TYPE_HLS`）、AES-128 密钥注入、指数退避重试，为本 m3u8 下载提供路径识别与重试参考。
- `HttpReadAloudService` 已用 `CacheDataSource` + `InputStreamDataSource` 做 HTTP 流写入缓存，作为文件写入参考。

## Requirements

### R1 播放器下载入口
- R1.1 视频播放器右栏（right_buttons）新增「下载」按钮。
- R1.2 按钮可用前提：当前有大 0 的已解析 `VideoPlay.videoUrl`。
- R1.3 点击后发起下载，默认文件名 = `VideoPlay.videoTitle`（非空时），URL 空时 Toast 提示不可下载。
- R1.4 下载发起成功后提示并可跳转下载管理页。

### R2 直链多线程分片下载
- R2.1 支持 mp4/mkv/flv/webm 等渐进式 HTTP 直链。
- R2.2 支持 Range(206) → 并发分片下载（默认并发 3，可配置）；完成后顺序合并。
- R2.3 不支持 Range → 自动降级单线程整段下载。
- R2.4 支持暂停（可续传）/ 取消（清理 Part）/ 失败重试。
- R2.5 下载进度、字节数、速度写入 DownloadState 供管理页展示。

### R3 m3u8 分片下载并转 mp4
- R3.1 识别 m3u8（含 Header/URL 后缀/嗅探）进入 HLS 下载分支。
- R3.2 解析 master 清单选主码流；解析 playlists/segments 得到分片列表。
- R3.3 并发下载 ts 分片（复用防盗链头）至临时目录。
- R3.4 按顺序合并分片为单个 `.ts`。
- R3.5 用 MediaExtractor+MediaMuxer 重封装 `.ts`→`.mp4`（PTS 偏移矫正）。
- R3.6 转换失败时回退保留 `.ts` 并提示；转换成功则清理全部分片与 `.ts`。
- R3.7 AES-128 加密 / DRM 流提示不支持，不进入下载。

### R4 下载管理整合
- R4.1 下载任务纳入现有 DownloadManageActivity 展示（全部/正在/暂停/完成/失败）。
- R4.2 暂停/重试/删除/打开/清理等操作适配自研引擎。
- R4.3 完成的任务默认保存目录：`Download/`（直链 mp4）与 `Download/m3u8/`（转换产物），文件名重复自动加序号。

### R5 健壮性
- R5.1 下载中取消/应用退出清理临时 Part 与转换中间文件。
- R5.2 存储不足、无网络、超时、并发上限均有处理与提示，不崩溃。
- R5.3 统一日志走 `AppLog.put()`，禁止残留调试 Log。

## Scenarios

### 场景 1：直接视频一键下载（Happy Path）
用户在播放器观看竖屏直链视频 → 点击右栏「下载」按钮 → Toast「已加入下载」→ 触发分片下载 → 下载管理页「正在下载」出现该任务 → 完成后在「已完成」分类，可打开播放本地文件。

### 场景 2：m3u8 转 mp4（Happy Path）
用户播放 m3u8 资源 → 点击「下载」→ 进入 HLS 分支 → 并发下载分片 → 合并 ts → 重封装 mp4 → 清理分片 → 管理页显示「已完成」，本地为 `.mp4`。

### 场景 3：服务器不支持 Range（降级）
直链服务器对 Range 返回 200 而非 206 → 引擎检测到后降级单线程 → 仍完整下载成功。

### 场景 4：加密流不支持（异常路径）
m3u8 含 AES-128 加密标志 → 点击下载 → Toast「暂不支持加密流下载」，不产生半成品文件。

### 场景 5：重复文件名（边界）
已存在同名文件 → 自动命名为 `标题(1).mp4`，避免覆盖已有下载。