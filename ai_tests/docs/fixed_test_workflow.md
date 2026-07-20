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
| 3b. L2验证订阅源搜索 | `l2_verify_rss_search.py` | 订阅源统一搜索L2功能验证（rss-unified-search新增） | `python ai_tests/scripts/l2_verify_rss_search.py [--keyword 关键词] [--scenario all]` |
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

## Cronet 库预下载检查（2026-07-18 v5 反哺新增）

> **背景**：真机测试发现部分 HTTPS 源加载失败，logcat 显示 `libcronet.so FileNotFoundException`。
> legado 使用 Cronet 库（基于 Chromium 网络栈）处理 HTTPS 请求，Cronet 库需要从网络下载或随App打包。
> 模拟器首次安装 App 时未自动下载 Cronet 库，导致 HTTPS 源全部加载失败（HTTP 源不受影响）。

### 触发条件

真机测试前必须执行 Cronet 库预下载检查，特别是：
- 首次安装 App 后的第一次测试
- 模拟器重置/重装后的第一次测试
- HTTPS 源加载失败时（优先检查 Cronet 库可用性）

### 诊断方法

**症状识别（logcat 关键词）**：
- `libcronet.so FileNotFoundException` - Cronet 库文件缺失
- `UnsatisfiedLinkError` + `cronet` - Cronet 库链接失败
- `Failed to load native library` + `cronet` - Cronet 库加载失败

**诊断脚本**（用 venv Python 执行）：

```python
# 检查 Cronet 库可用性
import subprocess
ADB = "adb"  # 从 config.py 导入
HOST = "127.0.0.1:21503"  # 从 config.py 导入
PKG = "io.legado.app"  # 从 config.py 导入

# 1. 检查 Cronet 库文件是否存在
r = subprocess.run([ADB, '-s', HOST, 'shell', 'su', '-c',
                    f'ls /data/data/{PKG}/files/cronet/ 2>/dev/null'],
                   capture_output=True, timeout=10)
files = r.stdout.decode('utf-8', errors='ignore').strip()
has_cronet_so = 'libcronet' in files
print(f'Cronet 库文件存在: {has_cronet_so}')

# 2. 检查 logcat 是否有 Cronet 相关错误
r = subprocess.run([ADB, '-s', HOST, 'logcat', '-d', '-t', '500'],
                   capture_output=True, timeout=15)
log = r.stdout.decode('utf-8', errors='ignore')
has_cronet_error = ('FileNotFoundException' in log and 'cronet' in log.lower()) or \
                   ('UnsatisfiedLinkError' in log and 'cronet' in log.lower())
print(f'Cronet 库错误: {has_cronet_error}')
```

### 修复流程

| 步骤 | 操作 | 命令/说明 |
|------|------|---------|
| 1. 诊断 | 检查文件存在性 + logcat错误 | 见上方诊断脚本 |
| 2. 触发下载 | 启动 App 等待60秒自动下载 | `adb shell am start -n {PKG}/.ui.MainActivity` 后 sleep 60 |
| 3. 复检 | 再次检查文件存在性 | 确认 `libcronet.so` 已下载 |
| 4. 重测 | 重新跑 scenario 验证 | HTTPS 源应能正常加载 |

### 集成到标准测试流水线

**更新后的标准测试流水线**：

```
编译 → 安装 → 启动App等待Cronet下载(60秒) → L1验证 → 导入订阅源 → L2验证 → 日志分析
                              ↑ 新增步骤
```

**新增检查清单**（L1验证前必做）：

```python
# 在 quick_build_install.py 后增加 Cronet 检查
def ensure_cronet_ready():
    """确保 Cronet 库可用（首次安装后必须执行）"""
    # 1. 启动 App 触发自动下载
    subprocess.run([ADB, '-s', HOST, 'shell', 'am', 'start',
                    f'-n {PKG}/.ui.MainActivity'], timeout=10)
    print('等待60秒让 App 自动下载 Cronet 库...')
    time.sleep(60)

    # 2. 检查是否下载成功
    r = subprocess.run([ADB, '-s', HOST, 'shell', 'su', '-c',
                        f'ls /data/data/{PKG}/files/cronet/'],
                       capture_output=True, timeout=10)
    if 'libcronet' in r.stdout.decode('utf-8', errors='ignore'):
        print('✅ Cronet 库下载成功')
        return True
    else:
        print('❌ Cronet 库下载失败，HTTPS 源将无法加载')
        return False
```

### 实战数据（2026-07-18）

| 指标 | 数据 |
|------|------|
| HTTPS 源加载失败数 | 7个 |
| 诊断结果 | 全部命中 `libcronet.so FileNotFoundException` |
| 触发下载后 | Cronet 库成功下载 |
| 重测结果 | 7个 HTTPS 源全部加载成功 |
| HTTP 源影响 | 无（只有 HTTPS 依赖 Cronet） |

### 教训

1. **真机测试前必须预下载 Cronet 库**（首次安装App后等待60秒）
2. HTTPS 源加载失败时，优先检查 Cronet 库可用性（而非 DNS 或网络问题）
3. logcat 关键词：`libcronet.so FileNotFoundException` / `UnsatisfiedLinkError` / `Failed to load native library`
4. Cronet 库位置：`/data/data/{PKG}/files/cronet/libcronet.so`
5. HTTP 源不受影响（只有 HTTPS 依赖 Cronet），可用于区分诊断
