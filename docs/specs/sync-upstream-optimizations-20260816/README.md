# sync-upstream-optimizations-20260816 · 上游同步优化批次（2026-08-16）

> OpenSpec 功能概述。状态：✅ 设计完成（待实施，阶段0门禁=等 Compose 化提交固化）。
> 创建时间：2026-08-16 19:37（08-16 20:15 补充阅读T/MD3/Archive/Jingshiro 调研；08-16 20:4x 自审补强定稿）｜ 类型：上游同步 / 优化批次 ｜ 数据窗口：开源阅读生态近一个月（2026-07-16 ~ 2026-08-16）

## 1. 任务背景

对「阅读·全版本集散地」（momoa.cc.cd/下载/xz，已修正 forks-reference.md 中过期的 momo-b5a.pages.dev 地址）收录的 10 个重点 legado 系仓库逐一拉取近一个月（2026-07-16 ~ 2026-08-16）更新记录（release + 提交级），并与本项目现状做逐项差异核实（25 项候选逐一验证文件级证据），筛选出可落地的同步优化项。

### 1.1 上游活跃度矩阵

| 仓库 | 版本 | 近一个月动态 |
|------|------|------|
| [gedoor/legado](https://github.com/gedoor/legado) | 原版 | ❌ 零提交（最后推送 2026-05-27，未归档但已停更） |
| [LegadoTeam/legado](https://github.com/LegadoTeam/legado) | 喵公子 | ✅ **更新主力**：14 个 release（3.26071315 → beta 3.26081617，7/13~8/16） |
| [Luoyacheng/legado-E](https://github.com/Luoyacheng/legado-E) | Sigma（本项目 fork 源） | ⚠️ 3 提交，含 **EPUB 删除 Ruby 标签修复 PR#451**（964d49e，7/24） |
| [skybbk1001/legadoT](https://github.com/skybbk1001/legadoT) | 阅读T | ✅ 30 提交（图片内联样式、HttpTTS 字段、TextDialog 文档内搜索、移除 hutool 原生加密、角色化朗读等） |
| [HapeLee/legado-with-MD3](https://github.com/HapeLee/legado-with-MD3) | MD3阅读 | ✅ ~27 提交（朗读媒体控制+读完本章、漫画 Compose 迁移、AI 增量分组、TXT 分割字数） |
| [Rimchars/legado](https://github.com/Rimchars/legado) | 阅读Archive | ✅ 46 提交（集中在 relay 隧道/段评 web、高级扉页子系统、内存工作集限制、主题跟随修复） |
| [joestar817/legado_NG](https://github.com/joestar817/legado_NG) | 阅读NG | ✅ 大规模 Compose 迁移（阅读页/订阅模块/划线书签抽屉/阅读浮窗预设/听书胶囊） |
| [Jingshiro/legado](https://github.com/Jingshiro/legado) | Jingshiro | ⚠️ 2 提交，含**阅读记录页 OOM 崩溃 + 详细记录重复膨胀修复**（8/7） |
| [DandanLLab/Legado_Max](https://github.com/DandanLLab/Legado_Max) | 蛋蛋Max | ❌ 零提交 |
| refgd/legado（阅读R）、GEd520/legados（辞晨） | — | ❌ 均零提交 |

> 结论：原版已停更，**喵公子为事实上的活跃上游**；阅读T/MD3 为活跃二级上游，各有独有增量；Sigma 的 EPUB 修复对本项目是确定性 bug 修复；NG/MD3 的 Compose 工作与本项目 `ui-redesign-m3` 同赛道，仅作模式参考。

### 1.2 同步决策总览（25 项候选核实结果）

**A 类：本项目确认缺失、上游已实现 → 本批实施（16 项）**

| # | 同步项 | 上游来源 | 本项目证据（缺失锚点） | 优先级 |
|---|--------|----------|------------------------|--------|
| 1 | EPUB delTag 位运算 bug 修复 + ruby TextNode 合并 | legado-E PR#451（964d49e） | **`Book.kt:345` 存在完全相同的 `and` bug**；`EpubFile.kt:176-181` 仅 `rp,rt` 删除无合并 | P0 |
| 2 | 章节缓存覆盖写入保护 | 喵公子 beta 3.26081617「修复章节缓存覆盖」 | `BookHelp.kt:178-190` saveText 无写入锁（图片下载有 Mutex，文本章节没有） | P0 |
| 3 | 更新弹窗显示包大小/日期 | 喵公子 3.26081008 | `AppUpdate.kt:16-20` UpdateInfo 无 size/date；`UpdateDialog.kt:22-28` 不展示 | P0 |
| 4 | 应用日志导出+分享 | 喵公子 3.26080421 | `AboutActivity.kt:111-170` 已有导出 zip，无分享 intent | P0 |
| 5 | 阅读页下拉书签 | 喵公子 3.26080800 | `PageDelegate.kt:62,66` fling 仅翻页，无下拉书签手势 | P1 |
| 6 | 目录分卷折叠 + 搜索匹配数量 | 喵公子 3.26071522 | `ChapterListAdapter.kt:129,138-147` 仅卷名高亮，无折叠 | P1 |
| 7 | TTS 段落间隔静音 + 听书定时增强（按剩余章节停止 / **读完本章**） | 喵公子 3.26071723 + MD3 PR#2024（8/12 读完本章） | `BaseReadAloudService.kt:157,402-420` 仅按分钟定时；无段落停顿；「读完本章/剩余N章」均无 | P1 |
| 8 | 书源 JS 并发工具（singleFlight/lock/tick） | 喵公子 3.26071723 | `JsExtensions.kt`（1199 行）0 匹配；仅 Kotlin 侧 ConcurrentRateLimiter | P2 |
| 9 | 漫画长按保存图片 | 喵公子 3.26080421 | 文本页已有（`ReadBookActivity.kt:2094`）；`ReadMangaActivity` 0 匹配 | P2 |
| 10 | 删除本地书联动删 WebDAV 文件 | 喵公子 3.26080800 | `BookInfoViewModel.kt:483-495` 删书流程与 AppWebDav 无关联 | P2 |
| 11 | Android 预测返回动画 | 喵公子 3.26080821 | manifest 无 `enableOnBackInvokedCallback`；targetSdk 36 已满足前提 | P2 |
| 12 | 书源级 URL 读取超时/重定向开关 | 喵公子 3.26071522 + 3.26080517 | `AnalyzeUrl.kt:873` 已有 dnsIp（含 resolveIp 别名）；无 readTimeout/redirect | P2 |
| 13 | TextDialog 帮助文档内搜索（全文高亮、上下跳转） | 阅读T（8/14） | `ui/widget/dialog/TextDialog.kt` 全文 0 处 search/highlight | P2 |
| 14 | TXT 无规则匹配时章节分割字数可设置 | MD3（todoXu，8/10） | `TextFile.kt:394` `analyze()` 用硬编码 `maxLengthWithNoToc`，不可配置 | P2 |
| 15 | 阅读记录页 OOM 核查加固 | Jingshiro（8/7：OOM 崩溃+详细记录重复膨胀） | 本项目 ReadRecordActivity 刚 Compose 化（`:88` allTime / `search` 全量明细加载面），需对照核查同类风险 | P2 |
| 16 | HttpTTS 补「启用CookieJar」字段 | 阅读T（8/14） | `HttpTTS.kt:27,73` 已有 jsLib；cookieJar/enableCookieJar 0 匹配 | P2 |

**B 类：大特性/独立子系统，本批不做 → 后续独立立项（6 项）**：段评系统（喵公子分页/SVG/章评 + Archive relay 段评 web，本项目仅 `ReviewRule.kt` 数据结构）、书架批量保存网络封面并恢复书源封面（喵公子 3.26081201）、批量缓存换源正文/批量单章换源（3.26080916）、直链导出口令分享（3.26071621）、朗读 MediaSession 媒体控制通知（MD3 8/11-14）、AI 自动书架分组（MD3 增量模式）。

**C 类：已有等价实现 / 不适用，记录结论不实施（6 项）**：
- Brotli 压缩（喵公子 3.26071323）→ 已有自实现 `DecompressInterceptor.kt:12,40`
- Cronet 150.0.7871.114 升级 → 本项目已是 150.0.7871.128（更新）
- 书架阅读进度显示（3.26071723）→ 已有（commit 3fcfa3ea8）
- WebView UA 统一（3.26071423）→ 已有全局 UA 体系（`AppConfig.kt:914-920`）
- **图片 URL 内联 style 选项（阅读T 8/15：单图 TEXT/FULL/SINGLE/DEFAULT + width/height）→ 已实现**：`TextChapterLayout.kt:675-700` 已解析 `style/width(%与px)/click` URL 选项
- ARM 小体积 APK → 已用 abiFilters 双架构单包方案；HttpTTS jsLib 字段（阅读T）→ 已有（`HttpTTS.kt:27`）
- 页眉页脚模板化/填充式电量图标 → 已有固定槽位+描边电量；阅读页独立配色为用户既有决策，缓
- 滚动阅读丢行位置修复（3.26080517）→ 实现不同构（无 ScrollBehaviorManager），留观测项
- 备份/WebDAV 恢复系列修复 → 本项目 WebDAV 刚独立增强（975992f53），以回归验证代替同步

**D 类：模式参考，不抄代码**：
- 阅读NG Compose 迁移 + **MD3 漫画阅读器 Compose 迁移（Nav3 导航/UDF 状态对齐，8/10）** → 给 `ui-redesign-m3`：① 目录/划线/书签侧滑抽屉分层；② 阅读浮窗预设组；③ 漫画阅读器 Compose 化的状态管理范式（MD3 的 UDF 状态机可直接借鉴）；④ NG 证明阅读内核可与 Compose 外壳共存
- **阅读T 移除 hutool → 原生加密实现（8/13，8/15 修兼容性回归）** → 本项目 hutool 5.8.22 为版本锁定地雷（书源加解密依赖），T 已趟完迁移+回归修复路径，是未来解锁该地雷的成熟参考（本批不动）
- Archive「限制阅读器与缓存工作集」内存优化（7/17）→ 本项目已有内存压力管理，方法可参考

## 2. 核心能力

- **数据正确性**（P0）：EPUB「删除 Ruby/H 标签」开关真正生效；章节缓存并发写入不撕裂不互相覆盖
- **信息透明**（P0）：更新弹窗展示包大小与发布日期；应用日志一键分享（协助远程排障）
- **阅读/听书体验**（P1）：滚动模式下拉快速加书签；目录按卷折叠与搜索计数；TTS 段落停顿 + 定时朗读三模式（按分钟/读完本章/剩余 N 章）
- **能力增强**（P2）：书源 JS 并发原语（去重/互斥/延时）；漫画长按保存；删书联动 WebDAV；预测返回动画；URL 级读取超时与重定向控制；帮助文档内搜索；TXT 分割字数可配；阅读记录页 OOM 加固；HttpTTS CookieJar 字段

## 3. 验收标准（真机验证点）

1. EPUB 书籍开/关「删除 Ruby 标签」「删除 H 标签」立即生效，注音文本无多余空格（对照修复前：开关完全无效）
2. 同一本书批量缓存 + 同时阅读 + 换源并发操作后，章节缓存文件完整可读，无半写/空文件
3. 更新弹窗显示包大小（如 `12.3 MB`）与发布日期；无数据字段时布局正常
4. 关于页「分享日志」拉起系统分享面板，接收方拿到 logs.zip
5. 滚动阅读模式顶部下拉出现书签提示并成功添加；页模式翻页手势无回归
6. 目录点击卷名折叠/展开该卷；搜索显示匹配数量
7. 朗读设置段落间隔生效（Http TTS 与系统 TTS）；定时朗读三种模式（分钟/读完本章/剩余 N 章）到点停止并通知
8. 含 `singleFlight/lock/tick` 的调试 JS 在书源调试页运行通过
9. 漫画页长按当前图保存成功（Android 10+ 适配）
10. 开启联动开关后删书同时删除 WebDAV 对应文件；WebDAV 不可达时删书不被阻塞
11. API 34+ 真机手势返回出现预测动画；阅读页/视频播放/WebView 页返回行为无回归
12. 书源 URL 选项 `{readTimeout: 5000, redirect: false}` 生效（超时中断 / 不自动跟随重定向）
13. 帮助文档（如书源帮助）打开后可全文搜索、高亮、上下跳转
14. TXT 导入无匹配目录规则时，按设置的字数分割成章
15. 阅读记录页在超长阅读明细数据下无 OOM、无重复膨胀（核查结论记录进 issues-found）
16. HttpTTS 导入源含 `enableCookieJar` 字段可正常解析并在编辑页可改
17. 覆盖安装升级后既有阅读配置（含 delTag 位标志）语义不变
- 回归项：换源/缓存/搜索/WebDAV 备份恢复主链路不回归
- 全部验证使用**测试包 `io.legado.miss.app.debug`**（项目代码优化类任务）

## 4. 风险清单与对策（2026-08-16 自审补强）

| 风险 | 等级 | 对策（已写入 design/tasks） |
|------|------|------------------------------|
| 项8 Rhino `Context` 线程绑定 vs singleFlight 跨协程共享 | 🔴 高 | 任务 3.1.0 硬门禁：先浅克隆喵公子/阅读T 对比真实实现，禁止闭门实现；JS 回调限定发起线程 Context 内求值 |
| 项11 `onBackPressed` 覆写残留 × 预测返回开启 = API34+ 返回键失效 | 🔴 高 | 任务 3.4.1 升级硬门禁：grep 清零前禁止开 manifest 开关（Compose 化中途 View 残留页面必须先迁移） |
| 项12 readTimeout/redirect 选项不传导 Cronet 引擎 | 🟡 中 | 设计补强：带选项请求强制走 OkHttp 原生栈；帮助文档注明；3.5.2 含 Cronet 全局开启下验证 |
| 项10 WebDAV 书籍文件同名歧义误删 | 🟡 中 | 设计补强：本地记录精确构造文件名，0/≥2 命中跳过并提示（宁漏勿误） |
| 项5 下拉书签无上游实现可参照（自研交互） | 🟡 中 | AD-11：明确自研规格，验收以本项目 S4 场景为准，不逆向猜上游 |
| 全部行号锚点随 Compose 化提交漂移 | 🟡 中 | 任务 0.3 锚点复核门禁（实施第一步） |
| 项2 锁等待语义（后到者等首个下载完成） | 🟢 低 | 有意取舍：正确性优先（S14 场景验收） |
| 16 项批量大、跨 20+ 文件 | 🟢 低 | 项间独立、阶段化、每阶段可独立验收回滚 |

## 5. 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 意图/范围/方案取舍/R1-R17 需求/场景 |
| [design.md](./design.md) | 16 项逐项落地设计 + ADR + 数据流 + 文件变更表 |
| [tasks.md](./tasks.md) | 阶段 0-4 任务清单（P0→P1→P2→收尾） |

## 6. 状态

- [x] 需求分析（上游调研：10 仓库 release + 提交级；25 项差异核实）
- [x] 四文档生成（含 08-16 20:15 阅读T/MD3/Archive/Jingshiro 补充调研并入；20:4x 自审补强 2 硬门禁 + 5 风险对策）
- [x] 🛑 检查点1：用户审查设计 —— ✅ 2026-08-16 通过定稿（等实施）
- [ ] 开发实施（按 tasks.md 阶段 1→3；**前置：等待当前 Compose 化工作提交固化**，用户已决策）
- [ ] 步骤 5.5 AI 自动端到端测试
- [ ] 🛑 检查点2：用户审核
- [ ] INDEX.md 移入已完成 + 文档同步
