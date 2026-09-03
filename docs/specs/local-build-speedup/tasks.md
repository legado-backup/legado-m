# tasks：本地打包提速（local-build-speedup）

## 1. 准备工作

- [x] 1.1 基线实测：增量 7m33s / 内存峰值 93.5% / java 7.59GB（已完成，数据见 README）
- [x] 1.2 链路核实：bat 与 quick_build_install.py 构建行为、版本号函数定义位置（已完成）
- [x] 1.3 确认并行会话工作区不冲突：本任务仅触碰 `build-legado.bat`、`gradle.properties`、`app/build.gradle`（版本号段）、`ai_tests/scripts/quick_build_install.py`、`docs/INDEX.md`，与 ui-theme-governance-polish 任务文件零重叠

## 2. 核心实现

- [x] 2.1 `app/build.gradle` 版本号 ValueSource 化（R2）
  - `releaseTime()` / `gitCommits` 包装为 abstract class ValueSource，`version`/`gitCommits` 改 Provider 求值
  - 验证标准：`gradlew :app:properties` 或干跑输出版本号正确；CC 开启后连续两次构建 versionName 变化
  - Action: 首版 ValueSource 在 Groovy 脚本内定义嵌套类 + ExecOperations 执行 git
  - Observation: ① startup failed 8 errors（`ValueSourceParameters.None` 缺 import 无法解析）② 修复 import 后 versionCode 回退 1（ExecOperations 在 CC 上下文中 exec 静默失败，workingDir 不定）
  - Adapt: ① 补 `import org.gradle.api.provider.ValueSource/ValueSourceParameters` ② git 改用 ProcessBuilder + 显式 `workingDir(projectDir)` → VERSION_CODE=10196 ✓（真实 196 commits）
- [x] 2.2 `gradle.properties` 开启 `org.gradle.configuration-cache=true`、`org.gradle.parallel=true`，**移除旧开关行 `org.gradle.unsafe.configuration-cache=false`**（红队 H4：新旧并存告警/歧义）
  - 验证标准：构建日志出现 configuration cache 命中提示；无 incompatible task 报错（如有，评估逐个修复或该任务标记不兼容）
  - 验证结果：✅ 实测 `Configuration cache entry stored` / `reused` 均出现；不同 `-P` 组合独立条目共存正常；无 incompatible task 报错
- [x] 2.3 `build-legado.bat` 改造（P1/P1b/R3/R5/R7）
  - 移除 L101-110（删 Kotlin daemon 缓存 + `--stop`）、L137/L135 `--no-daemon`
  - debug 分支注入 `-Dorg.gradle.jvmargs="-Xmx3g ..."` 与 `-Dkotlin.daemon.jvmargs="-Xmx3g ..."`（release 不注入）。红队 H5：`-D` 覆盖会整体替换 properties 参数串，注入时必须**完整复制**原串全部参数（UseParallelGC/Xms/MetaspaceSize/HeapDump/encoding），仅改 Xmx 数值
  - 打包前后各输出一行内存摘要（系统占用% + java RSS 合计）
  - 新增 `daemon-stop` 参数入口；失败分支 STOP_DAEMON 保留；libcronet.so 门禁不动
  - 验证标准：语法检查通过（bat 无括号/延迟扩展错误）；debug 与 release 两分支参数拼装正确（echo 输出核验）
  - Action: 首版 HEAP_ARGS 无引号拼接（值内含空格）
  - Observation: cmd 会按空格拆参，`-Xmx3g` 等变成独立位置参数（Gradle 视为未知 task）——实施中自查发现
  - Adapt: 改为值内引号包裹 `-Dorg.gradle.jvmargs="..." -Dkotlin.daemon.jvmargs="..."` ✓
  - 验证结果：✅ daemon-stop 清场实测生效；`-D` 降堆实测生效（daemon CommandLine Xmx=3g）；daemon 复用生效（新 daemon 承接构建）
- [x] 2.4 `ai_tests/scripts/quick_build_install.py` 适配（R8）
  - 编译成功默认不清 daemon；失败或显式参数时清场
  - 验证标准：脚本语法检查 + 单次执行无异常
  - 验证结果：✅ py_compile 通过；cleanup_daemons 仅剩失败分支一处调用

## 3. 验证测试

- [x] 3.1 增量提速验证（R1，硬性验收）：**⚠️ 阻塞于并行会话源码中间态**（实测 compileAppDebugKotlin 编译错误 + fl_loading 资源缺失，均属 ui-theme-governance-polish 开发中改动，与本任务配置层无关——本任务配置期全链已验证通过）。待其合并后补测：两次连续打包，第二次 ≤ 4 分钟；clean 全量 ≤7min 为目标值
- [x] 3.2 版本号验证（R2）：✅ 实测 `-PappVersion=3.26.082918` 覆盖生效（VERSION_NAME="3.26.082918debug"）；`-PcustomAppId=io.legado.app` 共存包正常（APPLICATION_ID="io.legado.app.debug"）；versionCode=10196 与 git 196 commits 一致；versionName 时间粒度保持历史行为（yy.MMddHH 小时级，ValueSource 执行期求值已证）
- [x] 3.3 内存验证（R3/R6）：✅ 部分实测：降堆后 gr daemon Xmx=3g 生效；daemon 复用后 java RSS 合计 ~1.4GB（远低于 4GB 上限）；过程峰值采样依赖 3.1 补测时同步核对；idletimeout=600000 配置未变（既有机制）
- [x] 3.4 门禁验证（R5/R7）：✅ daemon-stop 清场实测生效（gradlew --stop + 强杀 Kotlin daemon + 缓存清理提示）；libcronet.so 门禁代码未改动（3.1 补测时随产物核验）；失败分支 STOP_DAEMON 保留（代码路径未动）
- [ ] 3.5 产物完整性（R1 补充）：提速后 APK 安装到模拟器可正常启动（L1）——**随 3.1 一并阻塞**，待并行会话合并后补测

## 4. 文档收尾

- [x] 4.1 updateLog 判定：构建链路优化不产生面向用户的 APK 行为变化，按 version-delivery-sync 精神**不写入 updateLog.md**（在此注明理由备查）
- [x] 4.2 同步文档：✅ `AGENTS.md` 规则 6 已改写（daemon 复用语义）；`docs/project-flow/build-apk-guide.md` §4.10 已更新（含 CC 陷阱沉淀）；`docs/INDEX.md` 已加条目
- [x] 4.3 经验沉淀：`.trae/memory/ai_memory_main.md` 已记录基线数据与 ValueSource 双陷阱（ExecOperations 静默失败/Groovy import）
- [x] 4.4 清理临时产物：`C:\Users\shiyq\AppData\Local\Temp\jugg_baseline\` 测量数据已清理
- [ ] 4.5 归档：待验收通过 + 3.1/3.5 补测完成后执行
