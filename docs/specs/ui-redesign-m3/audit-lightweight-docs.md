# 轻量设计文档（L-*.md）质量审计报告

> 审计时间：2026-08-13
> 审计目录：`docs/specs/ui-redesign-m3/pages/light/`
> 审计对象：43 份轻量文档（任务描述称 44 份，实际目录内共 43 份，无缺失文件）
> 对照基线：`pages/_light-template.md`（轻量模板）、`pages/_template.md`（完整 v2 模板）、`pages-inventory.md`（功能点登记）
> 审计方式：逐份 Read 全部文档 + Grep 核查 task 占位符，对照 pages-inventory 功能点逐页比对

## 判定标准（满足任一即列待补齐）

1. **页面身份 task 号为占位符 `12.xx` / `tasks.md 12.xx`**（非精确 task 号，最关键指导性缺陷）
2. 差异点表缺失"功能点对照 pages-inventory"明确清单
3. 三态/组件选型/差异点为空洞占位（"不适用"/"—"泛滥到无法指导开发）
4. 缺失布局结构说明（可引用族文档但需明确；无法从继承声明判断布局）
5. 变更记录缺失

---

## 一、低质/待补齐文档清单（16 份）

> 共性缺陷：**页面身份「对应 task」仍为模板占位符 `tasks.md 12.xx`，且大部分「变更记录」第 7 节同样残留 `task 12.xx`**，未替换为精确 task 号。判定标准第 1 条（最关键缺陷）命中。其余结构（继承声明/差异点功能点对照/组件选型/三态/i18n/验收标准）均完整，无标准 2/3/4/5 缺陷。

| # | 文件名 | 具体缺陷 | 补齐要点 |
|---|--------|---------|---------|
| 1 | `L-B14-explore-show.md` | 页面身份 `tasks.md 12.xx` 占位符 | 填入精确 task 号（现 12.16 族内预审任务） |
| 2 | `L-B15-storage-manage.md` | 页面身份 `tasks.md 12.xx` 占位符 | 填入精确 task 号 |
| 3 | `L-B16-txt-toc-rule.md` | 页面身份 `tasks.md 12.xx` 占位符 | 填入精确 task 号 |
| 4 | `L-C3-booksource-debug.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `关联 task 12.xx` | 填入精确 task 号（C3 在 pages-inventory 无独立条目，需确认归属） |
| 5 | `L-C4-replace-rule.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 6 | `L-C5-highlight-rule.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 7 | `L-C6-dict-rule.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 8 | `L-C9-file-manage.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 9 | `L-C10-download-manage.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 10 | `L-C11-url-record.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 11 | `L-C12-recycle-bin.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 12 | `L-C13-source-login.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 13 | `L-C15-image-gallery.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 14 | `L-C16-auto-task.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 15 | `L-C17-welcome.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |
| 16 | `L-C20-about-record.md` | 页面身份 `tasks.md 12.xx` + 变更记录 `task 12.xx` | 填入精确 task 号 |

> 说明：以上 16 份仅命中**判定标准 1（task 占位符）**，功能内容本身完整、可指导开发；但 task 号为指引性信息，占位符未替换会使后续 AI 无法定位对应实施/验证任务，属最关键的指导性缺陷，故列为待补齐。

---

## 二、质量合格文档清单（27 份）

> 结构完整：页面身份含精确 task 号 / 继承声明明确 / 差异点表含功能点对照 pages-inventory 清单 / 组件选型引用 §3.4 / 三态齐全且"不适用"均属页型合理（Preference 页、全屏播放页等） / i18n 与无障碍 / 验收标准 / 变更记录。逐份核实无占位符、无空洞占位。

**含精确 task 号（9 份）**：
- `L-A5-base-bookshelf.md`（task 12.16j）
- `L-B2-toc.md`（task 12.16p）
- `L-B3-bookmark.md`（task 12.16p）
- `L-B4-highlight.md`（task 12.16p）
- `L-B11-search.md`（task 12.16p）
- `L-C19-debug-tools.md`（task 12.16k）
- `L-D2-rss-source-edit.md`（task 12.16n）
- `L-D5-rss-search.md`（task 12.16p）
- `L-E2-theme-config.md`（task 12.16p）

**task 标注为「待接线」但功能完整（6 份）**：
> 页面身份明确标注 `task 待接线`（诚实声明当前无精确接线任务），非占位符；其余结构完整。属次要观察项（见结论）。
- `L-B7-bookinfo-edit.md`（L-B5 亦标注「待接线」但含 `12.16p 族内` 精确引用，归入本组）
- `L-B8-bookshelf-manage.md`
- `L-B9-import-book.md`
- `L-B10-cache.md`
- `L-B12-manga.md`
- `L-B13-audio.md`
- `L-B5-all-bookmark.md`

**仅有 pages-inventory 引用、无 task 号（11 份）**：
> 页面身份仅列 `pages-inventory Dx/Ex（优先级）`，未标注 task 号，但非占位符；内容完整。属次要观察项（见结论）。
- `L-D3-rss-source-debug.md`
- `L-D4-rss-articles.md`
- `L-D6-read-rss.md`
- `L-D7-rss-favorites.md`
- `L-D8-rule-sub.md`
- `L-D9-video-player.md`
- `L-E1-backup-config.md`
- `L-E3-cover-config.md`
- `L-E4-other-config.md`
- `L-E5-precise-manage.md`
- `L-E6-welcome-config.md`

---

## 三、结论摘要

- **待补齐总数：16 份**（均因 task 号占位符 `12.xx` 未替换，判定标准 1 命中）
- **质量合格：27 份**
- **审计对象差异**：任务描述称 44 份，实际目录内共 **43 份**，逐份核验无缺失、无任务清单外的多余文件，应为描述笔误。
- **次要观察项（非占位符、不影响功能指导）**：
  1. 6 份文档（L-B7/B8/B9/B10/B12/B13）页面身份标 `task 待接线` —— 诚实声明，但若要达到模板"精确 task 号"标准，需在 tasks.md 落实对应接线任务后回填。
  2. 11 份文档（D3/D4/D6/D7/D8/D9 与 E1/E3/E4/E5/E6）仅有 pages-inventory 引用、无 task 号 —— 同上，属可回填项，非硬缺陷。
  - 建议：待补齐 16 份的 task 号回填可一并参考上述两类，统一在 tasks.md 落号。
- **审计方法**：全部 43 份已用 Read 逐份通读，task 占位符经 Grep 双源核验（16 处命中），无臆测项。
