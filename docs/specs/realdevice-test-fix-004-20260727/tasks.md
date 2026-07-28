# tasks.md - 004 真机测试问题任务清单

> **任务状态**：[ ] 未开始 / [~] 进行中 / [x] 已完成 / [!] 阻塞

## Phase A: P0 修复（首帧延迟 + AppLog 保障）

### A-1: DoH 冷启动优化（V-004-P0-1）
- [ ] A-1.1: DohDns.kt 新增 `isColdStart` 标志位 + `COLD_START_DISABLE_MS = 30_000L` 常量
- [ ] A-1.2: DohDns.kt lookup 方法修改：冷启动场景首次失败立即熔断 30s（非 5min）
- [ ] A-1.3: DohDns.kt 新增 `asyncPreheatDoh()` 方法：30s 后异步预热 DoH
- [ ] A-1.4: DohDns.kt 成功路径添加 `isColdStart = false` 重置
- [ ] A-1.5: 编译验证

### A-2: 嗅探前 DNS 预解析（V-004-P0-1）
- [ ] A-2.1: ExoPlayerHelper.kt 新增 `preResolveDns(url: String)` 方法
- [ ] A-2.2: Exo2MediaPlayer.kt prepareAsyncInternal 中 sniffVideoType 前调用 `preResolveDns`
- [ ] A-2.3: 编译验证

### A-3: AppLog 初始化保障（V-004-P0-2）
- [ ] A-3.1: AppLog.kt put 方法增加防御性初始化检查（`ensureInitialized()`）
- [ ] A-3.2: AppLog.kt 新增 `ensureInitialized()` 方法（重新初始化日志缓冲区）
- [ ] A-3.3: AppLog.kt put 方法增加 catch 兜底（AppLog 失败不影响业务）
- [ ] A-3.4: 编译验证

### A-4: VideoPlay.initSource 失败日志（V-004-P0-2）
- [ ] A-4.1: VideoPlayerActivity.kt onActivityCreated 中 initSource 失败记录详细日志
- [ ] A-4.2: VideoPlayerActivity.kt onActivityCreated 中 initSource 成功记录耗时日志
- [ ] A-4.3: 编译验证

### A-5: Phase A 编译验证
- [ ] A-5.1: `./gradlew assembleDebug` 编译通过
- [ ] A-5.2: 无新增编译错误

## Phase B: P1 修复（DoH 熔断 + Cronet 日志）

### B-1: DoH 熔断阈值优化（V-004-P1-1）
- [ ] B-1.1: 验证 A-1 的冷启动熔断逻辑覆盖 P1-1 场景（冷启动首次失败即熔断）
- [ ] B-1.2: 热启动场景保持 3 次熔断 5min 逻辑不变

### B-2: Cronet Request Canceled 日志降级（V-004-P1-2）
- [ ] B-2.1: CronetInterceptor.kt catch 块识别 "Canceled" 关键词
- [ ] B-2.2: Canceled 异常跳过 `printOnDebug()` 和协议错误计数
- [ ] B-2.3: Canceled 异常输出 DEBUG 级别日志
- [ ] B-2.4: 编译验证

### B-3: Phase B 编译验证
- [ ] B-3.1: `./gradlew assembleDebug` 编译通过
- [ ] B-3.2: 无新增编译错误

## Phase C: P2 优化（延后）

### C-1: 子 m3u8 预取（V-004-P2-1，延后）
- [ ] C-1.1: 调研 media3 1.10.1 HlsMediaSource 自定义子 m3u8 加载器可行性
- [ ] C-1.2: 或升级 media3 版本支持子 m3u8 预取
- [ ] C-1.3: 实施（延后至下个迭代）

**说明**：子 m3u8 预取涉及 HlsMediaSource 内部逻辑，当前 media3 1.10.1 不支持自定义，需升级或自定义 DataSource.Factory 拦截，风险较高，延后至 P2。

## Phase D: 验证 + 打包

### D-1: updateLog 更新
- [ ] D-1.1: 基于 git diff 分析真实代码变更
- [ ] D-1.2: 更新 `app/src/main/assets/updateLog.md`

### D-2: 编译打包
- [ ] D-2.1: `./gradlew assembleDebug` 编译测试包
- [ ] D-2.2: 验证 APK 生成成功

### D-3: 真机验证（用户测试）
- [ ] D-3.1: 安装测试包到真机
- [ ] D-3.2: 冷启动场景进入视频播放器，首帧渲染时间 ≤ 2s
- [ ] D-3.3: 快速切换 9 个视频，AppLog 持续输出
- [ ] D-3.4: 日志中无 `W System.err: Cronet Request Canceled` 噪音
- [ ] D-3.5: DoH 冷启动首次失败后 30s 熔断，异步预热成功后恢复

## 实施顺序

```
Phase A (P0)
  ├─ A-1: DoH 冷启动优化
  ├─ A-2: 嗅探前 DNS 预解析
  ├─ A-3: AppLog 初始化保障
  ├─ A-4: initSource 失败日志
  └─ A-5: 编译验证

Phase B (P1)
  ├─ B-1: DoH 熔断阈值（验证 A-1 覆盖）
  ├─ B-2: Cronet 日志降级
  └─ B-3: 编译验证

Phase C (P2，延后)
  └─ C-1: 子 m3u8 预取

Phase D (验证 + 打包)
  ├─ D-1: updateLog 更新
  ├─ D-2: 编译打包
  └─ D-3: 真机验证
```

## 关键约束

1. **同一文件 Edit 串行执行**：DohDns.kt/ExoPlayerHelper.kt/Exo2MediaPlayer.kt/AppLog.kt/VideoPlayerActivity.kt/CronetInterceptor.kt 各文件的多个 Edit 必须串行
2. **临时日志统一 tag**：使用 `AppLog.TAG_VIDEO_INIT` 等统一 tag（如需新增）
3. **编译前更新 updateLog**：Phase D-1 在 D-2 编译前完成
4. **真机测试用测试包**：`io.legado.miss.app.debug`（debug 构建，含调试日志）
