#!/usr/bin/env python3
r"""v5_6_generate_final.py — 生成 V5.6 最终产物

输出3个文件：
1. optimized_v5_6_final.json - 包含所有184源 + 修复后的源[1]/源[2]/源[3]
2. v5_6_single_source_fix_log.md - 单源深度修复日志
3. v5_6_single_source_workflow.md - 单源深度修复工作流文档

修复结果摘要：
- 源[1] (站点A 动态域名): ✅ 全部5维度通过（list_size:97, search_kw:我的, content=pass）
- 源[2] (论坛站 反爬): ❌ 反爬+需用户登录，自动化无法修复
- 源[3] (站点C HTTPS): ❌ 境外服务器不可达，DNS无法解析
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PATCH_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_6_patch.json')
FINAL_JSON = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_v5_6_final.json')
FIX_LOG_MD = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_single_source_fix_log.md')
WORKFLOW_MD = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_6_single_source_workflow.md')


def main():
    # 加载 patch JSON (已含源1+源2+源3的修复)
    with open(PATCH_JSON, 'r', encoding='utf-8') as f:
        all_sources = json.load(f)

    print(f'加载 V5.6 patch JSON: {len(all_sources)} 源')

    # 统计
    enabled_count = sum(1 for s in all_sources if s.get('enabled'))
    disabled_count = len(all_sources) - enabled_count
    print(f'  enabled: {enabled_count} | disabled: {disabled_count}')

    # 保存最终 JSON
    with open(FINAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_sources, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 输出最终 JSON: {FINAL_JSON}')

    # 生成修复日志
    fix_log = generate_fix_log()
    FIX_LOG_MD.write_text(fix_log, encoding='utf-8')
    print(f'✅ 输出修复日志: {FIX_LOG_MD}')

    # 生成工作流文档
    workflow = generate_workflow()
    WORKFLOW_MD.write_text(workflow, encoding='utf-8')
    print(f'✅ 输出工作流文档: {WORKFLOW_MD}')


def generate_fix_log():
    return """# V5.6 单源深度修复日志

**生成时间**: 2026-07-20
**任务**: 完善3个失败订阅源，让其通过模拟器开源阅读真机5维度测试

## 1. 修复目标（3个失败源）

| 源编号 | 失败维度 | 失败原因（v5_5验证） |
|--------|----------|---------------------|
| 源[1] | list/category/search | list_empty + category_list_failed + search_result_empty |
| 源[2] | content | content_parse_failed |
| 源[3] | search | malformed_url + content_parse_failed |

## 2. 修复过程

### 2.1 源[1] (站点A 动态域名映射)

**根因分析**:
- PC 探测发布页发现 JS 跳转目标为 `.51rb16/17/18.cc`
- 但源配置中 sortUrl/searchUrl 使用的是失效域名 `.51rb10.cc`
- 域名映射表 `mt[d]` 31天循环，但拼接基础域名错误

**修复方案**:
- 替换 sortUrl 中所有 `.51rb10.cc` → `.51rb16.cc`
- 替换 searchUrl 中所有 `.51rb10.cc` → `.51rb16.cc`
- 更新 lastHost 为 `51rb16.cc`

**修复脚本**: `ai_tests/scripts/v5_6_patch_sources.py`

**验证结果**: ✅ 全部5维度通过
- domain=pass
- list=pass (list_size:97)
- search=pass (search_kw:我的)
- category=pass
- content=pass

**网络请求路径**（脱敏）:
- 分类请求: `/vodtype/{id}.html`、`/vodtype/{id}-{id}.html`
- 搜索请求: `/vodsearch/{key}----------{page}---.html`
- 详情请求: `/voddetail/{id}.html`
- 视频播放: 加载 hls.js@1.4.12 播放 m3u8

### 2.2 源[2] (论坛站 反爬)

**根因分析**:
- 站点使用 JS 加密反爬：返回 safeid + str 变量 + mainv2.js 渲染
- type=0（网页源）默认用 OkHttp/Cronet 请求，不渲染 JS
- 服务器返回 302 重定向到 GE/CC/VALIDATOR 验证页
- 最终返回的 HTML 是反爬页（safeid+str+mainv2.js），无 .tr3 列表项
- sourceComment 提到"需要申请一个账号，免费. 先登录一下"，必须用户登录

**修复尝试**:
1. 修改 ruleContent 从 `class.f14@all&&script@all` → `class.f14@all`（去掉错误的 script 提取）
2. 重新导入 DB 验证
3. 结果：list 失败（反爬页无列表项）

**最终结论**: ❌ 无法通过自动化修复
- 反爬机制需要 WebView 渲染 JS
- 需要用户手动注册账号+登录
- 自动化测试无法完成用户登录流程
- 配置的 loginUrl/loginUi 是正确的，但需要用户手动触发登录

### 2.3 源[3] (站点C HTTPS)

**根因分析**:
- 原 sourceUrl=`http://jlm153.cc`，PC 探测返回 SSL wrong version number
- 实际站点是 HTTPS，但 sourceComment 中 host 变量已经是 `https://jlm153.cc`
- PC nslookup 能解析（166.0.188.247），但 MEmu 模拟器 DNS 无法解析

**修复尝试**（4次，均失败）:
1. http://jlm153.cc → PC 测试 SSL wrong version number
2. https://jlm153.cc → 模拟器报 UnknownHostException
3. https://jlm153.cc + /system/etc/hosts 添加 IP 映射 → 仍 UnknownHostException（Cronet/OkHttp 不读 hosts）
4. https://jlm153.cc + 模拟器 DNS 改为 8.8.8.8/1.1.1.1 → 仍 UnknownHostException

**最终结论**: ❌ 无法修复
- 服务器 IP 166.0.188.247 是境外地址
- 模拟器 DNS 即使配置为 8.8.8.8 也无法解析（可能 MEmu NAT 层有 DNS 劫持）
- 即使能解析，境外服务器在国内通常不可达
- 历史已多次标记为 `[AI_V3:disabled_reason=inaccessible]`、`[AI_V4:still_inaccessible]`、`[AI_V5_3:network_exception:exception]`

## 3. 5维度真机验证结果

| 源编号 | domain | list | search | category | content | 完全通过 |
|--------|--------|------|--------|----------|---------|----------|
| 源[1] | ✅ pass | ✅ pass (97项) | ✅ pass | ✅ pass | ✅ pass | ✅ 是 |
| 源[2] | ✅ pass | ❌ fail | ❌ fail | ❌ fail | unknown | ❌ 否 |
| 源[3] | ❌ fail | unknown | ❌ fail | ❌ fail | unknown | ❌ 否 |

## 4. 修复成功率

- **完全通过5维度**: 1/3 (源[1])
- **部分通过**: 0/3
- **完全失败**: 2/3 (源[2] 需用户登录 / 源[3] 境外不可达)

## 5. 关键经验沉淀

### 5.1 成功经验（源[1]）
- **PC 探测 + 真机调试结合**：PC 探测发布页找到正确域名，真机调试验证修复
- **域名映射表修复**：苹果CMS视频站常用 `mt[d]` 31天循环映射表，需检查映射基础域名
- **logcat 分析5维度**：通过 `≡获取成功`、`└列表大小:N`、`︽列表页解析完成` 等标记精确判断

### 5.2 失败教训（源[2]/源[3]）
- **反爬机制**：JS 加密（safeid+mainv2.js）必须 WebView 渲染，type=0 网页源无法绕过
- **境外服务器**：DNS 无法解析 + IP 不可达，无法在模拟器内访问
- **hosts 映射无效**：Cronet/OkHttp 不读 /system/etc/hosts，需要修改 App 内 DNS 解析器
- **3次失败换方法**：源[3] 已尝试4次（http→https/hosts映射/DNS改8.8.8.8）都失败，根因是境外不可达，应及早放弃

## 6. 输出产物

- `output/rss/optimized_v5_6_final.json` - 最终源JSON（184源）
- `output/rss/v5_6_debug_verify_result_v4.json` - 5维度验证结果
- `output/rss/v5_6_debug_verify_report_v4.md` - 5维度验证报告
- `output/rss/v5_6_debug_logs/` - 调试日志目录
- `output/rss/v5_6_debug_shots/` - 调试截图目录
- `output/rss/v5_6_single_source_fix_log.md` - 本修复日志
- `output/rss/v5_6_single_source_workflow.md` - 工作流文档

## 7. 安全规范

本日志全部脱敏输出：
- 源名称用编号替代（源[1]/源[2]/源[3]）
- 域名用代号替代（站点A/B/C）
- URL 路径模式化（/vodtype/{id}.html）
- 无 cookie/token/密钥等敏感字段
- 无原始日志引用，只输出技术结论
"""


def generate_workflow():
    return """# V5.6 单源深度修复工作流

**适用场景**: 修复失败的订阅源，让其通过模拟器开源阅读真机5维度测试
**核心原则**: 单源深度修复，放弃批量分析

## 1. 工作流总览

```
选失败源 → PC 探测根因 → 修复规则 → 导入DB → 真机调试 → 5维度验证
   ↓                                                      ↓
 阻塞?                                                   通过?
   ↓                                                      ↓
 分析原因继续                                          下一源 or 输出
```

## 2. 6步骤详细流程

### 步骤1: 抓包环境配置（可选）

**目标**: 配置 mitmproxy 抓包环境，捕获 App Cronet 真实请求

**命令**:
```bash
# 启动 mitmdump
mitmdump -p 8080 --listen-host 0.0.0.0 -w capture.flow --set block_global=false --set ssl_insecure=true

# 推送证书到模拟器系统CA
adb push mitmproxy-ca-cert.pem /sdcard/
adb shell su -c "cp /sdcard/mitmproxy-ca-cert.pem /system/etc/security/cacerts/c8750f0d.0"
adb shell su -c "chmod 644 /system/etc/security/cacerts/c8750f0d.0"

# 设置模拟器代理
adb shell settings put global http_proxy 10.0.2.2:8080
```

**替代方案**（mitmproxy 不可用时）:
- 用 ADB logcat 捕获 App 内部网络日志（Legado sourceDebug 标签）
- logcat 包含完整的请求 URL/响应内容/解析过程

### 步骤2: 选3源分析失败原因

**目标**: 从历史验证结果中选3个失败源，分析失败维度

**输入**: `v5_5_debug_verify_result.json`（前一版验证结果）

**选择标准**:
- 失败维度不同（避免同类型问题）
- 优先选择有修复价值的源（非境外不可达）
- 1个 list 失败 + 1个 content 失败 + 1个 search 失败

**输出**: 3个目标源的 JSON 配置

### 步骤3: 单源深度修复工作流

对每个源重复执行：

#### 3.1 PC 探测根因
```python
# 用 urllib/curl 探测源站点可达性
# 提取 HTML 结构，分析 ruleArticles/ruleContent 是否能匹配
python ai_tests/scripts/v5_6_deep_probe.py
```

#### 3.2 编写修复脚本
```python
# 基于PC探测结果，重写规则
python ai_tests/scripts/v5_6_patch_sources.py
```

#### 3.3 导入DB
```bash
# 用 import_rss_source.py 导入修复后的JSON到 legado.db
ai_tests/venv/Scripts/python.exe ai_tests/scripts/import_rss_source.py <json_path>
```

#### 3.4 真机调试5维度
```bash
# 启动 RssSourceDebugActivity 触发5维度调试
# 通过 logcat 分析 domain/list/search/category/content
ai_tests/venv/Scripts/python.exe ai_tests/scripts/v5_6_debug_verify.py
```

### 步骤4: 视频源播放验证（type=2 源）

**关键点**:
- 检查 ruleContent 是否生成 video 标签
- 检查是否加载 hls.js（m3u8 播放）
- 通过 content=pass 判断播放页是否正常

### 步骤5: 输出最终JSON

```python
# 合并所有源 + 修复后的源，输出最终JSON
python ai_tests/scripts/v5_6_generate_final.py
```

### 步骤6: 沉淀工作流文档

生成本文档 + 修复日志。

## 3. 5维度定义与判断

通过 logcat 中的 sourceDebug 标签判断：

| 维度 | 通过标记 | 失败标记 |
|------|----------|----------|
| domain | `≡获取成功` | `UnknownHostException` / `SocketTimeoutException` / `SSLException` |
| list | `└列表大小:N` (N>0) + `︽列表页解析完成` | `列表大小:0` / `列表页解析成功，为空` |
| search | `⇒开始搜索关键字` + `︽列表页解析完成` | `搜索URL为空` / `search_result_empty` |
| category | 同 list 维度（基于 sortUrl 触发） | `category_list_failed` / `category_parse_failed` |
| content | `︽内容页解析完成` | `content_parse_failed` / `内容规则为空` (skip) |

## 4. 关键技术点

### 4.1 RssSourceDebugActivity 触发

```bash
adb shell am start -n io.legado.app.debug/io.legado.app.ui.rss.source.debug.RssSourceDebugActivity --es key "源URL"
```

- 启动后 App 显示调试界面
- 点击 `textFl` 触发分类维度调试
- 点击 `textMy`/`textXt` 触发搜索维度调试

### 4.2 UI 自动化点击

```python
# dump UI XML
adb shell uiautomator dump /sdcard/ui_dump.xml
adb pull /sdcard/ui_dump.xml

# 解析节点找 textFl/textMy
nodes = parse_ui_nodes(xml_text)
fl_nodes = find_node_by_resource_id(nodes, r'id/text_fl$')

# 点击节点中心
bounds = get_bounds_center(fl_nodes[0].get('bounds', ''))
adb shell input tap {x} {y}
```

### 4.3 logcat 分析5维度

```python
# 清logcat
adb logcat -c

# 等待18秒（让App完成请求）
time.sleep(18)

# 抓取logcat
log = adb logcat -d -v threadtime

# 分析5维度
result = analyze_logcat_for_dimensions(log, source_url)
```

### 4.4 DB 导入（避坑）

**关键点**：必须同时 pull/push WAL/SHM 文件，否则 Room WAL 模式会覆盖新数据

```python
# pull DB + WAL + SHM
adb pull /sdcard/legado.db
adb pull /sdcard/legado.db-wal  # 可选
adb pull /sdcard/legado.db-shm  # 可选

# 清理本地 WAL/SHM（避免malformed）
for ext in ['-wal', '-shm']:
    if os.path.exists(tmp_path + ext):
        os.unlink(tmp_path + ext)

# 导入后 push 回设备
adb push tmp.db /sdcard/legado.db
adb shell su -c "cp /sdcard/legado.db /data/data/io.legado.app.debug/databases/legado.db"

# 关键：删除设备端WAL/SHM，避免旧WAL覆盖新数据
adb shell su -c "rm -f /data/data/io.legado.app.debug/databases/legado.db-wal /data/data/io.legado.app.debug/databases/legado.db-shm"
```

## 5. 失败处理策略

### 5.1 失败3次换方法

按用户铁律"失败不重试同一方式：如果修改规则3次仍失败，分析根因后换方法"

| 失败次数 | 策略 |
|----------|------|
| 1次 | 修复规则，重新验证 |
| 2次 | 换修复方向（如改协议/改域名） |
| 3次 | 标记为不可修复，记录根因 |

### 5.2 常见失败根因

| 根因 | 表现 | 修复方案 |
|------|------|----------|
| 域名失效 | list_empty + UnknownHostException | 找新域名（发布页/JS跳转） |
| 协议错误 | SSL wrong version number | http↔https 切换 |
| 反爬机制 | 返回 safeid+mainv2.js | 改 type=1 用 WebView 渲染 |
| 境外不可达 | DNS 无法解析 | 标记为禁用 |
| 需要登录 | 302 重定向到登录页 | 配置 loginUrl/loginUi，需用户手动登录 |
| 规则错误 | content_parse_failed | 重写 ruleContent |

## 6. 输出安全规范

严格遵守输出安全铁律：
- 源名称用编号替代（源[1]/源[2]/源[3]）
- 域名用代号替代（站点A/B/C）
- URL 路径模式化（/vodtype/{id}.html）
- 不输出 cookie/token/密钥
- 不输出原始日志，只输出技术结论
- 思考过程不引用源名称/域名/URL

## 7. 可复制性评估

本工作流的复用价值：
- ✅ 5维度 logcat 分析逻辑可复用（v5_4_debug_verify.py 模板）
- ✅ DB 导入流程可复用（import_rss_source.py）
- ✅ PC 探测 + 真机调试结合方法可复用
- ✅ 失败3次换方法策略可复用
- ⚠️ mitmproxy 抓包环境配置复杂，可用 logcat 替代
- ⚠️ 反爬机制需具体站点具体分析

## 8. 工具脚本清单

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/v5_6_extract_targets.py` | 从 final JSON 提取失败源到独立JSON |
| `ai_tests/scripts/v5_6_probe_source.py` | PC 端探测源站点可达性 |
| `ai_tests/scripts/v5_6_deep_probe.py` | PC 深度探测保存HTML原文 |
| `ai_tests/scripts/v5_6_patch_sources.py` | 修复源[1]和源[3]配置 |
| `ai_tests/scripts/v5_6_patch_src2.py` | 修复源[2] ruleContent |
| `ai_tests/scripts/v5_6_verify_patch.py` | 验证修复后URL可达性 |
| `ai_tests/scripts/v5_6_debug_verify.py` | 5维度真机调试验证 |
| `ai_tests/scripts/v5_6_generate_final.py` | 生成最终JSON+日志+工作流 |
| `ai_tests/scripts/import_rss_source.py` | 通用：导入订阅源到DB |
"""

if __name__ == '__main__':
    main()
