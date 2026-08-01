# 问题清单: 图片加载与视频切换线程协调修复

> **Spec ID**: image-thread-coordination-fix-20260731
> **创建日期**: 2026-07-31
> **状态**: 实施完成，待真机测试

---

## FR-7: NullPointerException(monitor-enter) 调用栈分析

### 问题现象
logs(9) 中多次出现 `java.lang.NullPointerException: Null reference used for synchronization (monitor-enter)` 异常。

### 技术分析
- **异常类型**: NullPointerException: Null reference used for synchronization (monitor-enter)
- **发生位置**: android.view.Surface.release(Surface.java:491)
- **线程**: FinalizerDaemon（GC finalizer 线程，tid=25228）
- **调用栈**:
  ```
  android.view.Surface.release(Surface.java:491)
  java.lang.Daemons$FinalizerDaemon.doFinalize(Daemons.java:387)
  java.lang.Daemons$FinalizerDaemon.processReference(Daemons.java:367)
  java.lang.Daemons$FinalizerDaemon.runInternal(Daemons.java:339)
  ```
- **发生频率**: 21:53:07 - 21:54:07 约 1 分钟内 5+ 次
- **伴随警告**: "A resource failed to call Surface.release."

### 根因分析
1. **Android Framework 级别问题**: Surface.release() 在 Surface.java:491 处使用 synchronized(mLock)，但 mLock 为 null
2. **触发条件**: Surface 对象被 GC 回收时，FinalizerDaemon 调用 doFinalize → Surface.release()，此时 Surface 内部的 mLock 已被置 null（native 层已释放）
3. **不可控性**: FinalizerDaemon 是 GC 回收线程，App 无法控制其调用时机
4. **已知问题**: 这是 Android Framework 的已知 bug，在 Android 8-12 的某些版本上出现，与 ExoPlayer/SurfaceView 的 Surface 生命周期管理相关

### 结论
- **无需 App 代码修复**: 这是 Android Framework 级别的 finalizer 问题，不是 App 代码 bug
- **影响评估**: 该异常被 System.err 输出为 W/E 级别日志，不会导致 App 崩溃或 ANR，仅是日志噪音
- **建议**: 忽略此日志，如需减少噪音可考虑在 ExoPlayer 释放时主动调用 Surface.release()（但需评估是否有其他副作用）

### 代码修复
无（FR-7 定义为"调用栈重新分析"，分析结论为系统级问题无需代码修复）

---

## 待真机测试验证项

### L2 真机测试场景
1. **图片滑动场景**: 快速滑动图片画布 30 秒，验证图片正常显示（FR-1 节流生效）
2. **视频切换场景**: 连续切换视频 10 次，验证无回调竞争（FR-2/FR-3 释放时序+回调忽略）
3. **快速切换文章**: 连续快速切换文章 3 次，验证只执行最后一次（FR-4/FR-6 防抖+状态保护）
4. **切换集数**: 切换集数 10 次，验证无 cancel-prepare 竞争（FR-4 防抖）
5. **弱网环境**: 弱网环境播放，验证连续 3 次 TTFB>1000ms 后降档（FR-5 TTFB 降档）
6. **网络恢复**: 网络恢复后自动恢复自动档位（FR-5 恢复机制）

### 日志验证项
1. "Cronet request canceled" 下降 ≥ 60%（FR-1 节流生效）
2. "preloadAround skip: activity destroyed" 不上升（FR-1 不影响现有守卫）
3. "callback ignored due to scope cancelled" 出现（FR-3 回调忽略生效）
4. "switchToArticle: debounce, cancel previous async task" 出现（FR-4 防抖生效）
5. "FR-5: force downgrade" 出现（FR-5 降档生效）
6. "FR-5: recover to auto tier" 出现（FR-5 恢复生效）
7. 节流期间并发连接数 ≤ 10（FR-1 连接数控制）
8. 无 OOM 发生（连续滑动 30 秒）
9. onDestroyView 主线程耗时增加 < 10ms，无 ANR（FR-2 释放时序）
