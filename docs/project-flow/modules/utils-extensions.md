# Legado 工具与扩展

> `app/src/main/java/io/legado/app/utils/` 目录——全局工具类与 Kotlin 扩展函数集合（100+ 文件，含 4 个子包）。

## 概述

utils 层为全项目提供无业务状态的基础能力：扩展函数按宿主类型拆分文件（Context/Fragment/Uri/...），有状态工具用 `object` 单例，与业务解耦，可被任意层引用。

## 核心类清单

| 类名 | 路径（utils/ 下） | 职责 |
|------|------|------|
| CoroutineExtensions | CoroutineExtensions.kt | 协程链式扩展（配合项目自定义 Coroutine 封装） |
| GsonExtensions / JsonExtensions | GsonExtensions.kt / JsonExtensions.kt | JSON 序列化/反序列化扩展 |
| NetworkUtils | NetworkUtils.kt | 网络状态与连通性检测 |
| ChineseUtils | ChineseUtils.kt | 简繁转换 |
| EncodingDetect | EncodingDetect.kt | 文本编码探测（TXT 打开链路依赖） |
| FileUtils / FileExtensions | FileUtils.kt / FileExtensions.kt | 文件读写与路径操作 |
| StringUtils / StringExtensions | StringUtils.kt / StringExtensions.kt | 字符串处理扩展（正则/分段/匹配） |
| UrlUtil / JsURL | UrlUtil.kt / JsURL.kt | URL 解析与相对地址合并 |
| EncoderUtils | EncoderUtils.kt | Base64/Hex 等编码转换 |
| ImageUtils / BitmapUtils | ImageUtils.kt / BitmapUtils.kt | 图片压缩、合成与处理 |
| ACache | ACache.kt | 轻量磁盘+内存缓存 |
| EventBusExtensions | EventBusExtensions.kt | EventBus 注册/postEvent 扩展 |
| Debounce / Throttle | Debounce.kt / Throttle.kt | 防抖与节流 |
| ColorUtils | ColorUtils.kt | 颜色解析与变换 |
| QRCodeUtils | QRCodeUtils.kt | 二维码生成/识别 |
| CronSchedule | CronSchedule.kt | Cron 表达式解析（自动任务调度依赖） |
| CssStyleParser | CssStyleParser.kt | CSS 样式解析（正文净化链路） |
| MD5Utils | MD5Utils.kt | MD5 摘要 |

## 子包清单

| 子包 | 内容 | 职责 |
|------|------|------|
| `canvasrecorder/` | CanvasRecorderFactory、CanvasRecorderImpl、Api23/Api29 实现、`pools/`（CanvasPool/PicturePool/RenderNodePool） | 离屏画布录制与对象池化复用 |
| `compress/` | SafeZipExtractor、ZipUtils、LibArchiveUtils | 压缩包解压（SafeZipExtractor 做路径安全校验） |
| `objectpool/` | ObjectPool、BaseSafeObjectPool、ObjectPoolLocked | 通用对象池 |
| `viewbindingdelegate/` | ActivityViewBindings、FragmentViewBindings、ViewBindingProperty | ViewBinding 委托绑定 |

## 关键机制

- **扩展函数优先**：同类型能力按宿主拆文件（如 `ContextExtensions.kt`、`UriExtensions.kt`、`ViewExtensions.kt`），调用侧以 `import` 按需引入。
- **对象池模式**：canvasrecorder 与 objectpool 均提供 `Locked`/`Safe` 变体，池化复用高频大对象（Canvas/Picture/RenderNode）降低 GC 压力。
- **安全解压**：`SafeZipExtractor` 对 entry 路径做校验，防 Zip Slip；ZIP 相关统一走 `compress/` 子包。
- **深入阅读**：协程封装见根 `AGENTS.md` 代码约束；加密相关工具见 [tools-infrastructure.md](./tools-infrastructure.md)。
