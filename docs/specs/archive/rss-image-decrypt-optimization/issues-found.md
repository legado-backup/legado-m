# 问题清单: 订阅源图片解密优化
> **Spec ID**: rss-image-decrypt-optimization
> **创建日期**: 2026-08-02
> **状态**: 真机问题记录（欢乐谷视频订阅源开发中发现的引擎层问题）

---

## Issue-1: ImageUtils 块对齐校验拦截 base64 文本封面，图片永不显示

### 问题现象
- 欢乐谷视频订阅源（.dat 封面 = base64 编码的 WebP 文本）真机测试：图片始终显示「加载中」占位
- Logcat 大量 `Failed to create image decoder with message 'unimplemented'`（线程 glide-legado-im/glide-disk-cach）
- Glide 磁盘缓存（image_manager_disk_cache）里存的是 base64 文本（head `UklGR...`）而非 WebP 的 RIFF 头
- 无「图片解密错误」AppLog（decode 未执行而非执行失败）

### 根因分析
- `ImageUtils.decode(src, bytes, ...)` 中块对齐校验：
  ```kotlin
  if (bytes.size % 8 != 0 && bytes.size % 16 != 0) {
      return bytes  // 跳过解密！
  }
  ```
- 该校验本意是避免未加密图片（非块对齐）被 AES 强制解密抛 IllegalBlockSizeException
- **误伤场景**：base64 编码的封面文本长度任意（如 95884 % 8 = 4、% 16 = 12），非块对齐 → coverDecodeJs 根本不执行 → base64 文本原样返回给 Glide → skia 解码失败
- 块对齐的 base64（如 30040 % 8 = 0）可正常走 evalJS → 同一批图片只有部分可解密，表现出"部分图片显示部分不显示"
- 未加密图片保护本由 `isKnownImageFormat` 文件头检测（PNG 89/JPG FF D8 FF/GIF 47 49 46 38/WebP 52 49 46 46）独立覆盖，块校验是冗余拦截

### 修复方案（已完成）
`app/src/main/java/io/legado/app/utils/ImageUtils.kt`：
1. 移除块校验块 `if (bytes.size % 8 != 0 && bytes.size % 16 != 0) return bytes`
2. evalJS 失败兜底 `.getOrNull()?.also{ decodeCache.put(src, it) } ?: bytes`（原返回 null → onStreamReady(null) → failUrl 永久短路不再重试；改为返回原始 bytes 允许重试）

### 验证结果（真机通过）
- 清缓存后：cover1-4 std 2-4.5（纯色占位）→ 47-79（真实图片彩色像素）
- skia unimplemented：94 条 → 0 条
- 播放/搜索/分类回归全部通过

### 经验教训
- 块对齐校验不能用于 base64 编码封面的场景（base64 文本长度任意），应依赖文件头检测区分加密与否
- 判图是否显示不能看 ImageView content-desc（静态 XML `@string/loading` 始终显示「加载中…」），须用截图+PIL 像素分析
- release 包 R8 proguard 移除 Log v/i/w/d/e，logcat 无法观察，须用 AppLog.put/putDebug（recordLog=true）

### 自进化沉淀
- 已沉淀至 `.trae/skills/legado-source-creator/references/special-scenarios/encrypted-images.md`（§4.1 陷阱块）
- 已登记 `.trae/skills/legado-source-creator/references/_INDEX.md` 自进化指引
