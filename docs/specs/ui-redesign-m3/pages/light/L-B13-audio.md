# L-B13 音频播放（AudioPlayActivity）· 轻量设计文档

> **适用**：B13 音频播放为枝叶页，继承族文档 `pages/P2-reader.md`（S5 全屏沉浸范式）。

## 0. 页面身份
- **页面名 / 文件锚点**：`ui/book/audio/AudioPlayActivity.kt`（416 行）
- **所属族文档**：`pages/P2-reader.md`（继承 S5 全屏沉浸范式）
- **骨架归类**：S5 全屏沉浸页（+LyricViewX 第三方歌词）
- **对应 task**：tasks.md `12.44`；pages-inventory B13（task 待接线）

## 1. 继承声明
- 复用骨架：S5 全屏沉浸（内容层 + 控件层 + 菜单浮出）
- 复用组件（§3.4）：`AppDropdownMenu`（音频菜单）、`SliderRow`（倍速/定时 SliderPopup）、`AppModalBottomSheet`
- 复用状态范式：沉浸式 + 事件驱动（EventBus）

## 2. 差异点（与族文档唯一不同处）
| 维度 | 族文档 | 本页差异 | 说明 |
|------|--------|---------|------|
| 内容层 | ReadView 排版 | 封面 + 模糊背景 + 歌词 LyricViewX（章节变量 lyric/durLyric，点击跳转） | 差异核心 |
| 控制 | — | 播放/暂停 FAB（长按停止）；上一章/下一章；播放模式循环；进度条+缓冲+时间；倍速 SliderPopup；定时停止 SliderPopup | |
| 导航 | — | 章节→TocActivity | |
| 菜单 | — | 自定义按钮/换源/登录/保持唤醒/复制音频URL/编辑源/跳过片头片尾/日志 | |
| 事件 | — | AUDIO_STATE/SUB_TITLE/SIZE/PROGRESS/BUFFER/SPEED/DS/MEDIA_BUTTON；退出未入书架询问 | |

## 3. 组件选型（仅列差异组件）
| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SliderRow`（新） | 滑块拖动菜单 | 倍速/定时 SliderPopup |
| `AppDropdownMenu` | M3 DropdownMenu | 音频菜单 |
| `AppModalBottomSheet` | L1 浮层面板 | 章节/换源 |

## 4. 三态
| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `AppVideoView` | 缓冲态（ExoPlayer BUFFERING） |
| 空态 | — | 不适用 |
| 错误 | — | 播放失败提示 + 重试 |

## 5. i18n 与无障碍
- 新文案 strings.xml 双语；播放/停止/倍速等控件无硬编码中文

## 6. 验收标准（轻量）
- [ ] 播放/暂停 FAB（长按停止）+ 上一章/下一章 + 播放模式循环 + 进度条/缓冲/时间
- [ ] 倍速 SliderPopup / 定时停止 SliderPopup / 歌词 LyricViewX / 封面模糊背景
- [ ] 章节→TocActivity；菜单（自定义按钮/换源/登录/保持唤醒/复制音频URL/编辑源/跳过片头片尾/日志）
- [ ] 事件（AUDIO_STATE/SUB_TITLE/SIZE/PROGRESS/BUFFER/SPEED/DS/MEDIA_BUTTON）；三态/i18n 补齐；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立，task 12.44
