# 任务清单 — APK 体积审核与精简优化

> 状态：🔄 设计中（v3，基于 debug APK 解压深度分析 + 打包技术手段全量评估）
> 格式：`- [ ] X.Y`（按 OpenSpec 规范）
> 核心约束：**绝对不能影响当前功能**
> v3 变更：补充 APK 内部构成实测 + .so strip 检测 + 打包技术手段评估 + packaging 排除 src/**

## 0. 深度核查（已完成）

- [x] 0.1 material-icons-extended 使用核查（结论：R8已tree-shake，保留不动）
- [x] 0.2 Firebase 移除影响核查（结论：源码零调用，可安全移除）
- [x] 0.3 ProGuard keep + 传递依赖核查（结论：keep主体不可动，toml可清理9个）
- [x] 0.4 资源冗余核查（结论：WebP可省~931KB，其余不可零影响精简）
- [x] 0.5 debug APK 解压深度分析（v3新增：125.7MB内部构成，DEX 108MB/lib 4.6MB/assets 3.3MB/tables 2.95MB）
- [x] 0.6 native .so ELF strip 检测（v3新增：14个.so均已strip，无.debug段，22-28 sections）
- [x] 0.7 打包技术手段全量评估（v3新增：R8/resourceOptimizations/preciseShrinking/nonTransitiveRClass全已启用，无遗漏）
- [x] 0.8 可疑目录定性（v3新增：src/ 40KB JDT源码可排除；google/firebase 随Firebase移除；dtd/tables/tc/org 必需）

## 1. 体积基线建立

- [x] 1.1 记录当前 debug APK 体积（51.07 MB，解压后 125.74 MB，25个DEX）
- [x] 1.2 构建 release APK 记录基线体积（**18.98 MB**，解压后 32.49 MB，3个DEX）
- [x] 1.3 解压 release APK 统计 dex/res/assets/lib 占比
  - DEX: 7.45MB (39.2%) / lib: 4.61MB (24.3%) / resources.arsc: 1.48MB (7.8%)
  - tables+tc: 1.72MB (9.1%) / res: 1.23MB (6.5%) / assets/bg: 0.98MB (5.2%)
  - google+firebase: 120KB (0.6%) / kotlin: 12KB / src: 11KB
- [x] 1.4 release DEX 中 Firebase 残留检测（com/google/firebase 49次 + com/google/android/gms 98次）
- [ ] 1.5 运行 `./gradlew :app:dependencies --configuration appReleaseRuntimeClasspath` 存档（可选）

### release 实测关键发现（v3→v4 修正依据）
- **release 18.98MB 已是合理体积**：DEX 经 R8 优化仅 7.45MB（vs debug 38.1MB，缩小 80.4%）
- **Firebase 移除收益待验证**：proto 文件仅 120KB，但 DEX 残留 Firebase+GMS 类，移除后 R8 可 tree-shake
- **packaging 排除收益修正**：src/ release中仅11KB（非40KB），kotlin/ 仅12KB（非52KB）
- **构建配置修复**：cronet-proguard-rules.pro 补 `-dontwarn android.os.SystemProperties`（Cronet隐藏API引用）

## 2. Batch 1 — Firebase 移除（预估 -1~2MB，零功能影响）

- [ ] 2.1 删 `app/build.gradle` 第14行 `alias libs.plugins.google.services`
- [ ] 2.2 删 `app/build.gradle` 第330-333行 firebase 依赖块
- [ ] 2.3 删 `gradle/libs.versions.toml` 第76行 `firebaseBom`
- [ ] 2.4 删 `gradle/libs.versions.toml` 第110-112行 3 个 firebase 库定义
- [ ] 2.5 删 `gradle/libs.versions.toml` 第239行 `google-services` 插件定义
- [ ] 2.6 删 `app/google-services.json` 文件
- [ ] 2.7 更新 `app/src/main/assets/privacyPolicy.md` 移除 Firebase 提及（合规性）
- [ ] 2.8 构建 release APK 验证无编译错误
- [ ] 2.9 安装模拟器验证启动无崩溃
- [ ] 2.10 对比体积，记录收益

## 3. Batch 2 — 图片 WebP 转换（预估 -931KB，零功能影响）

- [ ] 3.1 转换 `assets/bg/` 14 张图为 WebP q85，**保留 .jpg 扩展名**
  - 羊皮纸1-4.jpg、新羊皮纸.jpg、护眼漫绿.jpg、边彩画布.jpg、宁静夜色.jpg、山水画.jpg、明媚倾城.jpg、深宫魅影.jpg、清新时光.jpg、午后沙滩.jpg、山水墨影.jpg
- [ ] 3.2 转换 `res/drawable/` 6 张位图为 WebP q85，保留原文件名
  - image_cover_default.jpg、image_rss_article.jpg、image_rss.jpg、image_legado.png、image_loading_error.png、icon_read_book.png
- [ ] 3.3 转换 `assets/web/images/bg.jpg` 为 WebP
- [ ] 3.4 构建验证图片资源正常打包
- [ ] 3.5 安装模拟器，切换 14 种阅读背景验证显示无瑕疵
- [ ] 3.6 验证书架默认封面/RSS图/加载错误图显示正常
- [ ] 3.7 对比体积，记录收益

## 4. Batch 3 — 构建配置微调（预估 -40~70KB，零功能影响）

- [ ] 4.1 `app/build.gradle` packaging.resources.excludes 补 `src/**`（排除 JDT 注解 .java 源码 40KB）
- [ ] 4.2 `app/build.gradle` packaging.resources.excludes 补 `kotlin/**`（排除 kotlin_builtins 元数据 52KB）
- [ ] 4.3 删 `gradle/libs.versions.toml` 9 个未使用声明
  - splitties-activities、glide-compose、glide-ksp、glide-avif、avif、kotlin-reflect、media3-exoplayer-hls、media3-ui、media3-session
- [ ] 4.4 `.gitignore` 显式添加 `modules/web/dist/`
- [ ] 4.5 构建验证无编译错误
- [ ] 4.6 验证无 Kotlin 反射运行时异常（kotlin_builtins 排除后）
- [ ] 4.7 对比体积，记录收益

## 5. Batch 4 — okhttp3 keep 改 allowobfuscation（可选，预估 -30KB，需回归）

- [ ] 5.1 `app/proguard-rules.pro` 将 `-keep class okhttp3.*{*;}` 改为 `-keep,allowobfuscation class okhttp3.*{*;}`
- [ ] 5.2 构建 release APK
- [ ] 5.3 全量网络回归测试：
  - 书源搜索/详情/目录/正文加载
  - Cronet 网络栈切换
  - WebDAV 同步备份
  - Glide 图片加载（OkHttp 集成）
  - RSS 订阅源加载
- [ ] 5.4 检查日志无 NoSuchMethodError/ClassNotFoundException
- [ ] 5.5 通过则保留，失败则回滚
- [ ] 5.6 对比体积，记录收益

## 6. 最终验证与文档同步

- [ ] 6.1 构建最终 release APK，记录总收益
- [ ] 6.2 安装逍遥模拟器完整回归测试（书源/RSS/Web/阅读/TTS/调试工具/视频/背景切换）
- [ ] 6.3 检查 `temp/tmp` 日志无异常
- [ ] 6.4 更新 `assets/updateLog.md` 追加体积优化条目（面向用户语言）
- [ ] 6.5 更新 `docs/project-flow/quick-reference.md` 构建配置说明
- [ ] 6.6 更新 `docs/INDEX.md` 状态标记
- [ ] 6.7 更新 `app/build.gradle` 注释说明精简决策
- [ ] 6.8 更新 `docs/project-flow/architecture/overview.md` 依赖清单（若有增删）

---

## AOAdapt 日志

> 任务执行中遇问题时记录（Action / Observation / Adapt）

### 2026-07-08 深度核查阶段
- **Action**: 启动 4 路并行子代理深度核查 material-icons/Firebase/ProGuard/资源
- **Observation**:
  - material-icons-extended 原估算 -3~8MB 严重高估（R8 已 tree-shake 仅链接 17 图标，移除会丢功能）
  - ProGuard keep 几乎全部不可动（jsoup 被 JS 脚本引用、okio 被安全层字符串匹配、hutool 锁定）
  - 真实零功能影响可精简空间约 -2~3MB（远低于原估算 -8~17MB）
  - Firebase 确认可移除（源码零调用）
  - WebP 可省 ~931KB（保留原扩展名实现零引用改动）
- **Adapt**: 修正 spec/design/tasks，将方案从"依赖裁剪为主"收敛为"Firebase 移除 + WebP 为主"，移除所有会影响功能的优化项，诚实告知用户真实可精简空间

### 2026-07-08 v3 打包技术手段深度评估（用户反馈 v2 预估 -2~3MB 不满后）
- **Action**: 解压 debug APK（125.7MB）深度分析内部构成 + .so ELF strip 检测 + gradle.properties 打包配置全量核查
- **Observation**:
  - DEX 占 85.9%（108MB，debug 未混淆虚高，release 经 R8 大幅缩小）
  - native lib 4.61MB：libarchive 3.5MB(76%)/renderscript 0.84MB/rtmp 0.16MB，全部功能必需
  - **14 个 .so 文件均已 strip**（ELF 检测无 .debug 段，22-28 sections），AGP 默认自动 strip，无额外空间
  - **gradle.properties 已启用所有稳定打包优化**：enableResourceOptimizations + preciseShrinking + nonTransitiveRClass + nonFinalResIds
  - 发现 src/ 40KB JDT 注解源码（不应在 APK 中，可 packaging 排除）
  - google/ 301KB + firebase/ 16KB 是 Firebase proto，随 Firebase 移除
  - tables/ 2.95MB + tc/ 1.15MB 简繁转换数据必需；dtd/ 337KB EPUB 解析必需
  - 未启用的打包手段：R8 full mode（破坏反射，硬约束禁止）/ ABI splits（牺牲兼容）/ useEmbeddedDex（负收益）
- **Adapt**: 更新 v3 文档，新增 Approach E 打包技术手段全量评估 + AD-08 评估结论 ADR + packaging 排除 src/**；诚实告知用户"项目已用所有稳定打包技术手段，无遗漏"，要达到 5MB+ 需从 F1/F2/F3 折中选项决策
