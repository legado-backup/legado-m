# 固定测试流程 SOP（禁止从头创建临时脚本）

> **用户反馈（2026-07-11）**："你的测试流程为什么老是来来回回的变动呢？难道就没有一些经验或者是固定流程的脚本可以沉淀到ai_test目录下么？！！！你需要深度分析反省呢！"
>
> 本文档定义固定的测试流程，AI 每次测试**必须遵循此流程**，禁止在 temp/ 目录创建临时脚本。

## 标准测试流水线

```
编译 → 安装 → L1验证 → 导入订阅源 → L2验证 → 日志分析
```

每步对应固定脚本（位于 `ai_tests/scripts/`）：

| 步骤 | 脚本 | 说明 | 用法 |
|------|------|------|------|
| 1. 编译+安装+L1 | `quick_build_install.py` | 编译APK+启动MEmu+安装+L1验证 | `python ai_tests/scripts/quick_build_install.py` |
| 2. 导入订阅源 | `import_rss_source.py` | 从JSON导入订阅源到legado.db（含WAL模式处理） | `python ai_tests/scripts/import_rss_source.py <json_path>` |
| 3. L2验证视频播放器 | `l2_verify_video_player.py` | 视频播放器L2功能验证（导航+错误模式分析） | `python ai_tests/scripts/l2_verify_video_player.py` |
| 4. SwipeTest日志分析 | `swipe_test_log.py` | SwipeTest日志抓取分析（仅临时日志验证时用） | `python ai_tests/scripts/swipe_test_log.py [clear\|capture\|analyze]` |
| 5. 修复点覆盖度分析 | `fix_coverage_check.py` | 检查每个修复点的正向日志是否触发（10个修复点） | `python ai_tests/scripts/fix_coverage_check.py` |
| 6. 批量源遍历 | `batch_source_test.py` | 自动遍历多个RSS源检测修复点触发（全程脱敏） | `python ai_tests/scripts/batch_source_test.py [起始编号] [结束编号]` |
| 7. 导航辅助 | `nav_helper.py` | 脱敏导航到视频播放器（只输出编号不输出名称） | `python ai_tests/scripts/nav_helper.py [源编号]` |

### ⚠️ 重要：Room WAL 模式（2026-07-13 新增）

`import_rss_source.py` 已更新支持 Room WAL 模式：
- **问题**：Room 使用 WAL 模式，如果只 pull/push 主 `.db` 文件，WAL 中的旧状态会在 App 启动时覆盖新导入的数据
- **修复**：脚本现在同时 pull `.db-wal`/`.db-shm` 文件，用 `PRAGMA wal_checkpoint(TRUNCATE)` 合并 WAL 到主 DB，push 后删除设备端 WAL/SHM
- **注意**：导入前必须 `am force-stop` App，否则 App 可能覆盖 DB

## 环境要求

```bash
# 必须使用 ai_tests venv Python（禁止公共 Python）
ai_tests\venv\Scripts\python.exe ai_tests/scripts/xxx.py

# 或激活虚拟环境后执行
ai_tests\venv\Scripts\activate
python ai_tests/scripts/xxx.py
```

## 禁止行为

- ❌ 在 `temp/` 目录创建临时测试脚本（本会话已创建4个临时脚本，这是反模式）
- ❌ 每次测试从头编写 Python 脚本
- ❌ 手动执行 ADB 命令（应通过脚本执行，路径常量在 config.py）
- ❌ 硬编码路径（必须复用 `ai_tests/config.py` 中的常量）
- ❌ 不读取本 SOP 就开始测试

## 允许行为

- ✅ 扩展现有脚本的功能（修改 `ai_tests/scripts/` 下的脚本）
- ✅ 新增脚本到 `ai_tests/scripts/` 目录（当现有脚本无法覆盖新场景时）
- ✅ 修改脚本参数适配不同测试场景
- ✅ 复用 `ai_tests/lib/` 中的模块（memu_controller/apk_deployer/ui_executor）
- ✅ 复用 `ai_tests/config.py` 中的常量（ADB_PATH/MEMUC_PATH/MEMU_ADB_HOST 等）

## L2 验证场景清单

视频播放器相关功能验证场景（每个场景对应 l2_verify_video_player.py 的一个 `--scenario` 参数）：

| 场景 | 说明 | 关键验证点 |
|------|------|-----------|
| `swipe_article` | 上下滑动切换文章 | ⚠️依赖已移除的SwipeTest临时日志，会显示"未触发" |
| `pagination` | 分页加载 | ⚠️同上 |
| `preload` | 预缓冲 | ⚠️同上 |
| `position_memory` | 位置记忆 | ⚠️同上 |
| `backward_compat` | 向后兼容 | 无SwipeTest日志触发=通过 |
| `buffer_progress` | 缓冲进度条更新 | ⚠️依赖已移除的F1临时日志 |
| `control_visibility` | 控件自动隐藏 | ⚠️依赖已移除的F2临时日志 |
| `error_patterns` | ★推荐★ 错误模式验证 | P2 Malformed URL / P1-C destroy failed / P1-A ClassCastException / P2-A IllegalBlockSize 四种错误模式0出现=通过 |
| `all` | 全部场景 | 含error_patterns |

### SwipeTest 临时日志状态说明

> **2026-07-13 更新**：SwipeTest/F1/F2 临时日志已在任务 #69/#77/#109 中移除（验证通过后清理）。
>
> 依赖这些日志的场景（swipe_article/pagination/preload/position_memory/buffer_progress/control_visibility）会显示"未触发"，这是**预期行为**，非代码问题。
>
> **验证修复点请使用 `error_patterns` 场景**：通过 logcat 直接分析 4 种错误模式（Malformed URL/destroy failed/ClassCastException/IllegalBlockSizeException）是否为 0，永久有效。

## SwipeTest 临时日志规范

> **P0 规则23（用户表扬）**：复杂功能实施必须添加临时日志验证

1. **添加日志**：在关键路径添加 `Log.d("SwipeTest", "xxx: param=value")`
2. **抓取日志**：`python ai_tests/scripts/swipe_test_log.py capture`
3. **分析日志**：`python ai_tests/scripts/swipe_test_log.py analyze`
4. **验证通过后移除**：所有 SwipeTest 日志必须在验证通过后移除

## 脚本维护规则

- 脚本修改后必须更新本 SOP 的脚本表格
- 新增脚本必须在"L2验证场景清单"或新表格中记录用法
- 脚本必须包含 `if __name__ == "__main__":` 入口和 argparse 参数解析
- 脚本必须 import config 常量，禁止硬编码路径
