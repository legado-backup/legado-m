# JS 模式参考手册 — 子文档索引

> 源文件：`js-patterns.md` → 拆分为 11 个子文档
> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

---

## ⚠️ 创建新子文档前必须检查

1. **内容归属**：新内容是否属于已有子文档的范畴？优先追加到现有子文档，而非新建
2. **交叉引用**：新内容是否与其他子文档有重叠？如有，在两处都添加指向链接
3. **索引同步**：新建子文档后，必须在本文件中添加索引条目，否则无法被检索
4. **命名规范**：文件名使用小写kebab-case，必须能从文件名推断内容主题

---

## 子文档索引

### method-frequency.md

- **描述**：java.xxx 方法调用频率 TOP15 排行表，展示最常用的 Java 桥接方法及其调用次数
- ✅ 包含：md5Encode / getString / put / ajax / get / log / timeFormat / getElements / lang / aesBase64DecodeToString / base64DecodeToByteArray / md5Encode16 / security / setContent / t2s
- ❌ 不包含：方法的具体用法示例（→ [url-js-patterns.md](url-js-patterns.md) 搜索URL中的方法用法 / [rule-js-patterns.md](rule-js-patterns.md) 规则中的方法用法 / [crypto-patterns.md](crypto-patterns.md) 加密方法用法 / [fix-learned.md](fix-learned.md) 实战中的高级方法用法）
- **触发关键词**：java方法、调用频率、TOP15、md5Encode、getString、java.put、java.ajax、java.get、方法排行
- **自进化写入规则**：当发现新的高频 java.xxx 方法（调用次数 > 200）时，追加到 TOP15 表格并调整排名；当现有方法调用次数有显著变化时更新数据

### result-patterns.md

- **描述**：result 变量的10种使用模式 + 6种控制流模式 + 6种变量赋值模式，涵盖 JS 规则中最基础的数据操作范式
- ✅ 包含：result.match / result.replace / result.split / result=赋值 / if-else / JSON.stringify/parse / for/while/try-catch / url/list/src/html/body/doc 变量
- ❌ 不包含：result 在具体规则字段中的应用（→ [rule-js-patterns.md](rule-js-patterns.md)）/ result 跨字段传递的完整示例（→ [url-js-patterns.md](url-js-patterns.md) loginUrl 中 cookie 检查）
- **触发关键词**：result变量、match、replace、split、控制流、if-else、for循环、while、try-catch、变量赋值、url构造、list构造
- **自进化写入规则**：当发现新的 result.xxx 高频模式（次数 > 100）时追加到表格；当发现新的控制流或赋值范式时补充

### url-js-patterns.md

- **描述**：searchUrl / exploreUrl / loginUrl 三个 URL 字段的 JS 模式，共 5,019 个示例的 9 种核心模式
- ✅ 包含：API签名构造 / 动态URL / POST请求 / 分类列表生成 / 带缓存分类 / 日期动态生成 / 简单登录 / 浏览器登录 / Cookie检查
- ❌ 不包含：加密签名的完整流程（→ [crypto-patterns.md](crypto-patterns.md)）/ 登录后的设备注册（→ [fix-learned.md](fix-learned.md)）/ 搜索结果解析（→ [rule-js-patterns.md](rule-js-patterns.md)）
- **触发关键词**：searchUrl、exploreUrl、loginUrl、搜索URL、发现分类、登录、API签名、POST请求、动态URL、分类列表、Cookie检查、浏览器登录
- **自进化写入规则**：当发现新的 URL 字段 JS 模式（出现 > 50 次）时追加新小节；当现有模式有变体时补充到对应小节

### rule-js-patterns.md

- **描述**：ruleContent / ruleToc / ruleBookInfo 三个规则字段的 JS 模式，共 13,514 个示例的 11 种核心模式
- ✅ 包含：API响应解析 / 加密内容解密 / 多页正文拼接 / WebView获取 / hex解码 / API目录解析 / 繁简转换 / 分页目录 / Base64编码传递 / JSONPath条件判断 / 多字段组合
- ❌ 不包含：AES解密详细参数（→ [crypto-patterns.md](crypto-patterns.md)）/ HLS视频播放器（→ [hls-player.md](hls-player.md)）/ 大神源完整链路（→ [master-analysis.md](master-analysis.md)）
- **触发关键词**：ruleContent、ruleToc、ruleBookInfo、正文解析、目录解析、书籍详情、API响应、加密解密、多页拼接、WebView、hex解码、繁简转换、分页目录、Base64传递
- **自进化写入规则**：当发现新的规则字段 JS 模式（出现 > 30 次）时追加新小节；当正文/目录/详情解析有新范式时补充

### crypto-patterns.md

- **描述**：加密/签名模式汇总，453 个示例中的 3 种核心加密方式（AES解密 / MD5签名 / X-Gorgon签名）
- ✅ 包含：AES/CBC/PKCS5Padding 解密 / MD5签名 / X-Gorgon签名（抖音/番茄系）/ **Mirages主题图片AES解密（WordPress+Mirages主题，含loadBannerDirect提取+data-xkrkllgl属性+OkHttp获取byte[]+createSymmetricCrypto解密）**
- ❌ 不包含：AES+GZIP组合解密（→ [fix-learned.md](fix-learned.md)）/ HmacMD5/HmacSHA256 签名流程（→ [fix-learned.md](fix-learned.md)）/ DES加密（→ [fix-learned.md](fix-learned.md)）/ 凯撒密码（→ [fix-learned.md](fix-learned.md)）/ JavaImporter调用加密库（→ [fix-learned.md](fix-learned.md)）
- **触发关键词**：加密、签名、AES、MD5、X-Gorgon、createSymmetricCrypto、decryptBase64ToString、md5Encode、抖音签名、番茄签名
- **自进化写入规则**：当发现新的加密/签名模式（出现 > 20 次）时追加新小节；当现有加密方式有新参数组合时补充示例

### master-analysis.md

- **描述**：大神源完整链路分析（起点/淘小说）+ 订阅源JS技巧（微博/视频），展示复杂源的全链路设计思路
- ✅ 包含：起点优+源6阶段链路 / 淘小说优++源4技巧 / 微博博主4技巧 / 18AV视频源4技巧
- ❌ 不包含：具体加密实现（→ [crypto-patterns.md](crypto-patterns.md)）/ 视频播放器HTML模板（→ [hls-player.md](hls-player.md)）/ 实战修复经验（→ [fix-learned.md](fix-learned.md)）
- **触发关键词**：大神源、完整链路、起点、淘小说、订阅源、微博、视频源、复杂度评分、全链路分析
- **自进化写入规则**：当分析新的复杂源（复杂度 > 500 分）时追加新小节；当现有源有新技巧发现时补充到对应条目

### common-traps.md

- **描述**：7 个最常见的 JS 陷阱，写书源规则时必须避开的坑
- ✅ 包含：Rhino ES5限制 / result必须返回 / @js: vs <js> / put/get进程缓存 / webView异步 / POST必须method / 正则双转义
- ❌ 不包含：具体修复方法（→ [fix-learned.md](fix-learned.md)）/ @tag过时语法替换（→ [fix-learned.md](fix-learned.md)）
- **触发关键词**：陷阱、坑、ES5、Rhino限制、let/const、箭头函数、模板字符串、result返回、@js vs <js>、进程缓存、webView异步、正则转义
- **自进化写入规则**：当发现新的常见陷阱（影响 > 10 个源）时追加条目；当现有陷阱有新变体时补充说明

### hls-player.md

- **描述**：自定义 HLS 视频播放器完整模板，含标题显示、视频地址复制、倍速播放、跳进跳退等交互功能
- ✅ 包含：DPlayer+m3u8提取 / hls.js HTML模板 / type=0 WebView渲染 / 标题/地址/复制/倍速/跳进/全屏设计
- ❌ 不包含：通用 ruleContent 解析模式（→ [rule-js-patterns.md](rule-js-patterns.md)）/ 其他视频源技巧（→ [master-analysis.md](master-analysis.md) 18AV源）
- **触发关键词**：HLS、m3u8、视频播放器、DPlayer、hls.js、WebView渲染、type=0、视频源、自定义播放器
- **自进化写入规则**：当发现新的视频播放器模板（如 DASH/MPD）时追加新小节；当 hls.js 版本升级影响模板时更新 CDN 链接和 API

### auto-video-player.md

- **描述**：V1 自动抓取视频播放器模板参考文档，四种方法自动提取视频URL并播放
- ✅ 包含：DOM提取 / 正则提取 / JS变量提取 / XHR/Fetch拦截提取 / 模板变量说明 / config配置项 / m3u8/mp4分流 / 分页加载 / Legado JSBridge
- ❌ 不包含：手动提取视频URL（→ [hls-player.md](hls-player.md)）/ 注入式优化（→ [inject-video-player.md](inject-video-player.md)）/ 通用 ruleContent 解析模式（→ [rule-js-patterns.md](rule-js-patterns.md)）
- **触发关键词**：自动抓取、V1、视频提取、DOM提取、正则提取、JS变量提取、XHR拦截、auto-video-player、自动视频播放器
- **自进化写入规则**：当发现新的视频URL提取方法时追加到四种方法中；当模板变量或config配置项变更时同步更新

### inject-video-player.md

- **描述**：V3 注入式视频播放器优化脚本参考文档，劫持已有播放器实例，优化缓冲+去广告
- ✅ 包含：6种播放器检测+原生兜底 / destroy+recreate缓冲优化 / 事件拦截广告拦截 / 净化模式 / 卡顿检测+自动降级 / XHR/Fetch拦截 / 全局控制栏+进度条
- ❌ 不包含：自建播放器模板（→ [hls-player.md](hls-player.md) / [auto-video-player.md](auto-video-player.md)）/ 通用 ruleContent 解析模式（→ [rule-js-patterns.md](rule-js-patterns.md)）
- **触发关键词**：注入脚本、V3、播放器劫持、缓冲优化、去广告、destroy+recreate、事件拦截、webJs注入、inject-video-player
- **自进化写入规则**：当发现新的播放器框架需要支持时追加到 PLAYER_DEFS；当广告拦截机制有新变体时补充到对应小节

### fix-learned.md

- **描述**：实战修复中学到的 15+ 高级 JS 技巧，涵盖 API签名全流程、组合解密、Cloudflare绕过、代码复用、Java类调用等深度经验
- ✅ 包含：HmacMD5/HmacSHA256签名 / 参数排序+MD5 / 凯撒密码 / AES+GZIP组合 / Cloudflare绕过 / 设备注册 / JSON相对路径 / eval代码复用 / JavaImporter加密库 / payAction借阅 / getLoginInfoMap / try-catch版本回退 / Jsoup.parse / 两步异步搜索 / @tag过时替换
- ❌ 不包含：基础加密模式（→ [crypto-patterns.md](crypto-patterns.md)）/ 基础规则模式（→ [rule-js-patterns.md](rule-js-patterns.md)）/ 常见陷阱（→ [common-traps.md](common-traps.md)）
- **触发关键词**：实战修复、HmacMD5、HmacSHA256、凯撒密码、GZIP解密、Cloudflare绕过、设备注册、eval复用、JavaImporter、payAction、getLoginInfoMap、版本回退、Jsoup.parse、异步搜索、@tag过时
- **自进化写入规则**：当修复新源时发现未记录的 JS 技巧，立即追加新小节；当现有技巧有新变体或改进方案时补充到对应条目
