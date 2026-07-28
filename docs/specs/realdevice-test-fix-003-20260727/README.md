# realdevice-test-fix-003-20260727

> 基于 003 日志深度分析（78700 行/17.5 小时/6 次 FATAL EXCEPTION）+ 002 图片 UX 要求的增量修复 spec。

## 日志深度分析结论

| 指标 | 数值 |
|------|------|
| 嗅探成功/失败 | 47/22（成功率 68.1%） |
| 播放成功/失败 | 37/22（成功率 62.7%） |
| 3003 错误 | 9 次（HLS→Progressive 降级必然失败） |
| FATAL EXCEPTION | 6 次（5 TrackSelector + 1 Glide） |
| 图片 200/403/404 | 1519/40/33 |
| Cronet 降级/恢复 | 21/20 次 |
| DoH 全失败 | 40 次 |

## 问题清单（8 个新发现）

### P0 致命崩溃
| 编号 | 问题 | 根因 | 状态 |
|------|------|------|------|
| V-003-P0-1 | TrackSelector.init 崩溃×5 | 共享 TrackSelector 重复 init | V-P0-1 已修复，需打包验证 |
| V-003-P0-2 | prepareAsyncInternal 重入 | R5 回调 9~16ms 内重入 | **待修复** |
| I-003-P0-1 | Glide destroyed activity 崩溃 | onScrollStateChanged 缺 isDestroyed 守卫 | **待修复** |

### P1 功能缺陷
| 编号 | 问题 | 根因 | 状态 |
|------|------|------|------|
| V-003-P1-1 | BUFFERING 降级必然 3003 | HLS→Progressive，21 Extractor 全失败 | **待修复** |
| I-003-P1-2 | URL 拼接 %0A Bug | parseImageUrls newline split 未 trim | **待修复** |
| V-003-P1-3 | videoFallbackWebview 未触发 | 072709 不含 V-P1-2 末端兜底 | V-P1-2 已修复，需打包验证 |
| I-003-P1-3 | 图片 UX 未落实 | 002 要求工具栏/占位/进度 | **待实施** |

### P2 体验优化
| 编号 | 问题 | 状态 |
|------|------|------|
| V-003-P2-1 | LoadControl 重复创建 | **待修复** |
| T-003-P2-1 | ai_test 分析脚本 | **待实施** |

## Phase 计划

- **Phase A**：P0 崩溃修复（V-003-P0-2 重入保护 + I-003-P0-1 Glide 守卫）+ 编译验证
- **Phase B**：P1 功能缺陷（V-003-P1-1 降级链 + I-003-P1-2 URL %0A + I-003-P1-3 图片 UX）+ 编译验证
- **Phase C**：P2 优化（LoadControl 缓存 + ai_test 脚本）
- **Phase D**：交付（updateLog + 打包 + 真机验证）

## 关联文档

- 深度分析报告：`docs/temp-analysis/log-analysis-003-deep-20260727.md`（599 行）
- 前序 spec：`docs/specs/realdevice-test-fix-20260727/`（Phase A/B 修复）
- 用户反馈：`issues/user/temp/20260727/003/bug.md` + `issues/user/temp/20260727/002/bug.md`
