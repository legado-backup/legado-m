# Spec: 依赖升级性能优化 + minSdk 迁移

## Intent

Legado 项目当前使用 74+ 依赖项，部分依赖版本已有新版本发布，其中一些新版本包含**显著性能改进**。同时，AndroidX 生态自 2025 年底起统一将 minSdk 提升至 23，导致 minSdk=21 的项目无法升级。本 spec 旨在：
1. 将 minSdk 从 21 提升至 23，解锁 AndroidX 升级路径
2. 识别升级后能带来显著性能提升的依赖，评估安全性
3. 制定分优先级的升级方案，确保升级后功能不受影响

## Scope

### 在范围内

| 类别 | 说明 |
|------|------|
| minSdk 21→23 迁移 | 提升 minSdk 并清理兼容代码 |
| 可安全升级的依赖 | 升级风险低、性能增益明确的依赖 |
| 需适配升级的依赖 | 升级有中等风险但性能增益大，需要代码适配 |
| WebView 性能优化 | 代码层修复（setLayerType + hardwareAccelerated，非依赖版本问题） |
| 已锁定依赖的确认 | 重新确认锁定原因是否仍然成立 |

### 不在范围内

| 类别 | 说明 |
|------|------|
| 依赖替换（如 Glide → Coil） | 不涉及框架替换，仅升级现有依赖版本 |
| 新增依赖 | 不引入项目当前未使用的依赖 |
| 构建工具链变更 | AGP/Kotlin/KSP 升级属于独立任务（当前 2.3.10/8.13.2 已是最新） |
| JVM 仿真器依赖同步 | 仿真器依赖版本独立锁定，不纳入本次升级 |
| webkit 1.14→1.16 升级 | webkit 1.16.0 要求 minSdk≥24，超出本次 minSdk=23 的范围 |
| shouldInterceptRequest 缓存 | 风险较高（过滤绕过、缓存一致性、线程阻塞），降为 P2 延后 |
| Room 2.8.x 升级 | 2.7.2 不存在，2.8.4 有 KMP 架构变更风险，需单独评估 |

## Approach

### Selected Approach：minSdk 迁移 + 分层分优先级渐进升级

**核心思路**：先将 minSdk 提升至 23 解锁 AndroidX 升级路径，然后按「性能增益 × 升级安全性」矩阵分三层推进，每层升级后验证编译和功能。

**执行顺序**：
1. **Phase 0**: minSdk 21→23（前置条件）
2. **Phase 1**: P0 层升级（低风险高收益，含 lifecycle 2.11 + core 1.19）
3. **Phase 2**: WebView 性能修复（代码层）
4. **Phase 3**: P1 层升级（需适配）
5. **Phase 4**: 验证 + 文档同步

**选择理由**：
1. minSdk→23 是 AndroidX 1.12+/1.9+ 的硬性前置条件，必须先行
2. 渐进升级避免"大爆炸"式变更导致的不可控回归
3. 分层明确优先级，最大化性能收益/风险比
4. 每层独立验证，失败可快速回滚

### Alternatives Considered

| 替代方案 | 否决理由 |
|----------|----------|
| 全量一次性升级所有可升级依赖 | 风险不可控：一个依赖出问题会阻塞所有其他依赖的验证；难以定位回归源头 |
| 保持 minSdk=21，仅升级不受限的依赖 | 放弃 lifecycle 2.11/activity 1.13/core 1.19/material 1.14/media3 1.10 等重要升级，性能收益大幅缩水 |
| minSdk→24（而非 23） | 进一步减少用户覆盖；webkit 是唯一需要 minSdk=24 的依赖，且项目仅 1 个文件使用其 API，不值得 |
| 只升级安全补丁不升级性能版本 | 违反用户"带来巨大性能提升"的核心需求 |
| 依赖替换（如 Coil 替换 Glide） | Glide 5.0.5 已是最新主版本，自定义 ModelLoader/Transformation 迁移成本极高，替换收益不确定 |
| Room 升级到 2.8.4 | 2.8.x 有 KMP 架构变更和 minSdk=23 要求，需额外适配验证，收益不明确 |

### Drawbacks

| 缺点 | 接受理由 |
|------|----------|
| minSdk→23 影响 <1% 的 API 21-22 用户 | 这些设备多为 2014-2015 年发布，AndroidX 生态已不再支持 |
| webkit 1.16.0 无法升级（需 minSdk=24） | 项目仅 WebSettingsExtensions.kt 使用 webkit API，性能增益有限，可后续单独评估 |
| commons-text 确认硬锁定（desugaring 不覆盖 Arrays.setAll） | 已通过深度验证确认，即使 minSdk=23 也无法升级（Arrays.setAll 需 API 24+） |
| core-ktx 1.19.0 变空壳 | 扩展函数已移入 core 主模块，保留 core-ktx 依赖声明保证兼容性，无需代码修改 |
| OkHttp 升级可能影响 ObsoleteUrlFactory | 已识别为 P1 级别，需专门运行时验证 |
| gsyVideoPlayer 与 media3 1.10.x 兼容性 | 需运行时验证视频播放功能 |
| shouldInterceptRequest 缓存延后 | 风险过高（过滤绕过、缓存一致性），当前 WebView 性能提升主要靠 setLayerType |

### Prior Art

- OkHttp 5.x 迁移：多个 Android 开源项目已完成，无重大兼容性问题报告
- Coroutines 1.10→1.11：JetBrains 官方稳定发布，Channel 性能优化已合入主分支
- AndroidX minSdk→23：自 2025 年底起成为 AndroidX 生态统一标准
- Lifecycle 2.9→2.11：AndroidX 官方稳定发布，2.11.0 已走完完整 alpha→beta→rc→stable 流程
- Core 1.17→1.19：AndroidX 官方稳定发布，1.19.0 已走完完整 alpha→stable 流程

## Requirements

### 功能需求

| ID | 需求 | 优先级 |
|----|------|--------|
| R1 | 将 minSdk 从 21 提升至 23 | P0 |
| R2 | 清理 API 21-22 兼容代码（含遗漏项：WebViewPool/BottomWebViewDialog/SystemUtils） | P0 |
| R3 | 识别所有可安全升级的依赖项并量化性能增益 | P0 |
| R4 | 执行 P0 层升级（7 个依赖）并验证编译通过 | P0 |
| R5 | 执行 WebView 性能修复（setLayerType + hardwareAccelerated） | P0 |
| R6 | 执行 P1 层升级（OkHttp）并验证功能正确性 | P1 |
| R7 | 更新 libs.versions.toml 中的版本号和注释 | P0 |
| R8 | commons-text 确认硬锁定（Arrays.setAll 需 API 24+，desugaring 不覆盖） | 已确认 |

### 非功能需求

| ID | 需求 |
|----|------|
| NFR1 | 每个依赖升级后 APK 必须编译通过 |
| NFR2 | 不触碰已锁定的 5 项依赖（jsoup/rhino/hutool/commons-text/protobuf） |
| NFR3 | 升级后不降低任何现有功能的可用性 |
| NFR4 | 升级方案必须可回滚（通过 git revert） |
| NFR5 | desugar 依赖保留（API 23 仍需 desugaring 支持 Java 8 API） |

## Scenarios

### 场景 1：minSdk 迁移成功

1. 修改 build.gradle 中 minSdk 为 23
2. 清理 8 处 API 21-22 兼容代码（含遗漏项）
3. 编译通过
4. 核心功能验证

### 场景 2：P0 层升级成功

1. 修改 libs.versions.toml 中 7 个 P0 依赖版本号
2. 执行 `gradlew assembleAppDebug` 编译通过
3. 安装 APK，验证核心功能（书架、搜索、阅读、书源管理、音频播放）
4. 合并变更

### 场景 3：P1 层升级需运行时验证

1. 修改 OkHttp 版本号
2. 编译通过
3. 运行 ObsoleteUrlFactory.main() 冒烟测试
4. 验证 Cronet 集成和 HTTP 请求
5. 如果运行时失败：回退 OkHttp 到 5.3.2

### 场景 4：某依赖升级后功能回归

1. 编译通过但运行时发现功能异常
2. 回滚该依赖到原版本
3. 记录回滚原因，标记为 P2 观望
4. 继续其他依赖的升级

### 场景 5：gsyVideoPlayer 与 media3 1.10.x 不兼容

1. 升级 media3 后编译通过
2. 运行视频播放功能测试
3. 如果 gsyVideoPlayer-exo2 崩溃或异常：评估 gsyVideoPlayer 是否有适配新版本
4. 无适配版本则回退 media3 或锁定 gsyVideoPlayer 的 media3 传递依赖
