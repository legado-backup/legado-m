# issues-found — app-update-variant-fix（2026-09-12 真机/环境问题登记）

## IF-1 quick_build_install.py 编译超时误报（已修复）
- **现象**：`quick_build_install.py` 步骤 1 硬编码 `timeout=600`，daemon 清场后冷编译实测 15-18 分钟，必然 `TimeoutExpired` 杀进程并误报"编译失败"；且异常路径直接 raise，未走失败清场分支。
- **修复**：timeout 600→1800（脚本内注释留痕）。**后续建议**：该脚本的编译超时应进 config.py 常量并支持环境变量覆盖（未本次实施）。
- **关联陷阱**：gradle daemon VFS 损坏（`BuildSessionActionExecutor` 初始化失败）→ `stop-daemons.bat` 清场后重试即过（既有陷阱复现，处置有效）。

## IF-2 PowerShell 向 gradlew.bat 传 `-Pkey=value` 被拆散
- **现象**：`.\gradlew.bat assembleAppDebug -PappVersion=3.26.090520` 经 PowerShell→bat 链路后，gradle 收到 `-PappVersion=3` 与任务名 `.26.090520`（报 Task not found）。
- **处置**：参数整体加引号 `"-PappVersion=3.26.090520"` 即可。低版本验证包构建成功。

## IF-3 AGP 清理输出目录旧 APK（流程提醒）
- **现象**：`app/build/outputs/apk/app/debug/` 下换 versionName 重新打包后，旧版本 APK 被 AGP 清除（仅剩新包）。
- **影响**：需要"正常包+低版本包"并存的验证流程，必须在重建前把已构建 APK 拷贝到 `output/apk/test/` 归档目录（AGP 不清该目录）。

## IF-4 检查更新自身无 L2 脚本（已补齐）
- **现象**：更新链路（Gitee/GitHub 双源+资产解析）此前无固化验证脚本，回归只能靠发版后用户反馈。
- **修复**：新增 `ai_tests/scripts/l2_verify_update_check.py`（SOP 16v），T1 静默判定/T2 低版本弹框对号，本批 T1/T2 真机 PASS（证据 `ai_tests/reports/update_check_20260912_161932|162046/`）。

## IF-5 会话沙箱发布死结（环境级，2026-09-12）
- **现象**：后台沙箱运行 publish_release.py 时，正式包 kotlin 编译随机 AccessDenied（class 文件/F:\gh daemon registry 锁被拒）；沙箱留下的两个 gradle daemon（PID 43192/61040）宿主侧 taskkill/Stop-Process 均"拒绝访问"杀不掉，长期存活且拖慢后续构建（冷构建 17min 恶化为 50min+，期间 kapt/KSP 阶段反复停滞）。
- **本次结局**：4 次发布尝试（沙箱 1 次 + 提权 3 次），测试包 49 分钟构建成功但正式包阶段反复受阻，最终人工中止。
- **教训**：**发布这类需要完整文件系统/网络/进程控制的重流程，应在用户原生终端跑 `publish.bat`**，不进会话沙箱；沙箱内跑过一次重型 gradle 后，同会话后续构建都受僵尸 daemon 拖累。
