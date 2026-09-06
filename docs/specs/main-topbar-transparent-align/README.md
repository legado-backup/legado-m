# main-topbar-transparent-align（主界面四Tab头部透明对齐Archive）

## 状态
**开发中**（2026-09-06 设计审核通过，进入开发）

## 功能概述
主界面四大 Tab（书架/发现/订阅/我的）头部（状态栏+顶栏区域）无法呈现透明沉浸效果，与 Archive 最新版（archive-ref/legado-08172114）视觉不一致。经逐行 diff 定位，真正分叉点为：

1. **P0 主因**：`MaterialValueHelper.kt` 的 `Context.backgroundColor` / `Fragment.backgroundColor` 扩展删除了 Archive 的"配置背景图且非 E-Ink → 返回 TRANSPARENT"透明分支，恒返回 `ThemeStore.backgroundColor`（不透明），透明链路整体失效（该透明分支在本项目已无任何调用方，属"删了没人发现"的静默回归）。
2. **P1 次因**：`BaseActivity` 窗口底色策略分叉——`initTheme` 改为 decorView 常驻 tint（Archive 为清 tint + 实色 fallback）；基类 `upBackgroundImage` 挂图前不清 tint、无图时提前 return 不恢复实色底。
3. **连带修复（红队捕获）**：本项目 `dialogSurfaceBackground`（弹窗底色）消费 `backgroundColor`，透明原语恢复后会连锁导致弹窗整体透明穿帮；Archive 该属性走 `dialog_surface` 独立来源，需一并对齐。
4. **排除项（证据澄清）**：双方 `setBackdropBlur` 均恒传 null（毛玻璃从未激活）、`isOverlayMode`/`applyDefaultStyle`/`applyRegularStyle` 逐行一致，overlay/blur 非根因，本轮不动。

## 核心能力
- 恢复透明原语：配置背景图时 `backgroundColor` 返回透明，头部区域透出背景图（状态栏+顶栏连续沉浸）
- 无背景图/E-Ink 行为不变（实色兜底）
- BaseActivity 窗口底色策略对齐 Archive（保留本项目管理页 tint 钩子）

## 文档索引
| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规范（Intent/Scope/Approach三要素/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（ADR Y-Statement/数据流/文件变更） |
| [tasks.md](./tasks.md) | 任务清单 |

## 变更日志
| 日期 | 变更 |
|------|------|
| 2026-09-06 | 初版设计（探索结论：P0 透明原语 + P1 decorView 着色策略） |
