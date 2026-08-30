# 真机测试问题修复 - 项目导航

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **创建时间**：2026-07-27 10:00
> **来源**：用户真机测试（APK legado_miss_app_3.26.072709.apk）问题清单 `issues/user/temp/20260727/` + 新日志 `temp/logs/Downloadslogs(3).(1)..zip` 深度分析（`temp/logs/review2_report.md`）+ 主代理源码交叉验证
> **状态**：设计阶段，待用户审查
> **优先级**：P0（含 100% 可复现崩溃 + 核心功能回归）

---

## §1 项目简介

### 1.1 背景

用户用 07-27 最新包真机测试，反馈三类问题：
1. **视频**：基本可用，但 2 次半框崩溃退出播放器 + 2 次嗅探播放弹框报错 + 其他
2. **图片**：**所有详情图片全部无法查看**（V4 改造严重回归）+ UX 诉求（工具栏对齐视频播放器：收藏/三点菜单[刷新、配置、浏览器打开、日志]；占位底图+加载状态可见性）
3. **阅读高亮**：双引号独立字体后其他高亮无法覆盖；高亮预设规则不生效且无初始化常用规则

日志深度分析确认：**5 次 FATAL 崩溃（100% 可复现的设计缺陷）+ 图片 403×86 次且降级链断裂 + 4 项机制性问题**。

### 1.2 核心目标

| 指标 | 当前值 | 目标值 | 修复来源 |
|------|--------|--------|---------|
| 播放器并发崩溃 | 5 次 FATAL/100% 可复现 | 0 | V-P0-1：TrackSelector 每实例独立 |
| 图片详情加载 | 全挂（403×86） | 成功率≥95% | I-P0-1：防盗链头链路修复 |
| 图片降级链 | 86 张仅 1 张触发且被吞 | 每图独立降级+主线程回调 | I-P0-2 |
| 播放首帧 READY 率 | 46%（26/56） | ≥80% | 网络模块修复带动 |
| 直链降级链起步错误 + 3003 弹框 | 3003×9（2 会话）+ MANIFEST_MALFORMED 无谓试错 | 0 | V-P1-1：直链后缀识别+启发式降级链 / V-P1-2：3003 白名单+末端兜底 |
| Cronet 乒乓抖动 | 2 分钟 6 轮 | 每会话≤1 次降级 | N-P1-1：恢复迟滞 |
| DohDns 成功率 | 0/249，avg 244s 串行 | IDN 场景 <500ms | N-P1-2 |
| 高亮预设规则 | 不生效+无初始化 | 开箱即用+生效 | R-P1（已拆出至独立 spec `highlight-rule-fix-20260727`） |

### 1.3 问题清单总览

| 模块 | 编号 | 问题 | 优先级 | 证据 |
|------|------|------|--------|------|
| 视频 | V-P0-1 | PlayerInstancePool.sharedTrackSelector 共享单例 → 并发 prepare 二次 init → ISE 崩溃 ×5 | P0 | PlayerInstancePool.kt:54/:104 + 5×FATAL 调用栈 |
| 视频 | V-P1-1 | 直链后缀未识别（inferContentTypeByExtension 只认清单后缀）+ UNKNOWN 降级链固定 HLS 优先起步 → .mp4 直链两次必然试错 | P1 | ExoPlayerHelper.kt:430-438 + Exo2MediaPlayer.kt:193 + 09-30 会话日志 |
| 视频 | V-P1-2 | 3003 逃逸 isUnrecoverableError 白名单 → isParsingError 死代码 → 降级末端失败不触发 WEBVIEW 兜底（双触发路径全死） | P1 | Exo2MediaPlayer.kt:709-740 + 3003 弹框×9 |
| 图片 | I-P0-1 | 详情图全挂：403×86（防盗链拒绝，数据层 12/12 成功非空） | P0 | 日志 09:41:01-09:41:10 |
| 图片 | I-P0-2 | 降级链断裂：fallback-3 在 Glide 工作线程调 WebView 方法被吞；86 张仅 1 张触发降级 | P0 | 日志 + ImageGalleryActivity.kt:182-205 |
| 图片 | I-P1-1 | UX 对齐视频播放器：收藏 + 三点菜单（刷新/配置/浏览器打开/日志） | P1 | 用户诉求 |
| 图片 | I-P1-2 | 占位底图 + 加载状态可见（总张数/已加载指示） | P1 | 用户诉求 |
| 网络 | N-P1-1 | Cronet 乒乓抖动：2 分钟 6 轮降级↔恢复（最快 0.018s 切回） | P1 | CronetInterceptor.kt:107-111 |
| 网络 | N-P1-2 | DohDns 0/249 成功率（punycode IDN 公共 DoH 不收录）+ 串行最坏 9s×N | P1 | 日志统计 + DohDns.kt |
| 网络 | N-P2-1 | 日志脱敏缺口 2 处：AnalyzeUrl 完整 URL 明文 + VideoSubTitle 事件源标题明文（198 行） | P2 | 日志实锤 |
| 网络 | N-P2-2 | RedirectCache 命中不更新 Referer + LRU sortedBy 弱一致 | P2 | RedirectCacheInterceptor.kt:54/:95 |
| 图片 | I-P2-1 | 渐进式加载未实现（无 thumbnail()） | P2 | 全项目零调用 |
| 阅读 | R-P1-1 | 双引号独立字体后其他高亮无法覆盖（Span/绘制层级冲突） | P1 | HighlightDraw.kt/ContentTextView.kt |
| 阅读 | R-P1-2 | 高亮预设规则不生效 + 无初始化常用规则 | P1 | HighlightRuleStore.kt/HighlightPresetRuleDialog.kt |

---

## §2 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 功能规格：问题清单详述+验收标准 |
| [design.md](./design.md) | 技术设计：每个问题的根因+修复方案+成熟方案参考 |
| [tasks.md](./tasks.md) | 任务清单：按 Phase 组织+验收勾选 |

## §3 实施策略

- **Phase A（P0 止血）**：V-P0-1 + I-P0-1 + I-P0-2 → 编译验证
- **Phase B（P1 机制）**：V-P1-1 + V-P1-2 + N-P1-1 + N-P1-2 → 编译验证
- **Phase C（P1 体验）**：I-P1-1 + I-P1-2 + R-P1-1 + R-P1-2 → 编译验证
- **Phase D（P2 收尾）**：N-P2-1 + N-P2-2 + I-P2-1 + ai_test 验证脚本
- **Phase E**：updateLog + 编译 + 打包 → 用户真机复测
