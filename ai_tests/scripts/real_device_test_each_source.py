#!/usr/bin/env python3
"""real_device_test_each_source.py — 逐个真机测试7个needs_user_login源

通过 am start RssSourceDebugActivity --es key URL 直接打开源调试界面
逐个测试每个源的加载情况，输出技术指标（不输出业务字段）
"""
import json
import os
import re
import sys
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21513'
PKG = 'io.legado.app.debug'
DEBUG_ACTIVITY = f'{PKG}/.ui.rss.source.debug.RssSourceDebugActivity'

JSON_PATH = r'f:\myself\github\WeAgentChat\temp\legado\output\rss\optimized_final_v7.json'
OUTPUT_DIR = Path(r'f:\myself\github\WeAgentChat\temp\legado\output\rss\each_source_test')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NEEDS_LOGIN_IDX = [21, 24, 30, 36, 39, 55, 58]


def adb_shell(cmd_str, timeout=30):
    full_cmd = f'"{ADB}" -s {HOST} shell {cmd_str}'
    return subprocess.run(full_cmd, shell=True, capture_output=True, timeout=timeout, text=False)


def adb_pull(remote, local):
    return subprocess.run([ADB, '-s', HOST, 'pull', remote, local], capture_output=True, timeout=30)


def sanitize_line(line):
    """脱敏单行日志：替换URL/IP/域名为代号"""
    s = line
    s = re.sub(rb'https?://[^\s"\']+', b'[URL]', s)
    s = re.sub(rb'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', b'[IP]', s)
    return s


def sanitize_text(text):
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'https?://[^\s"\']+', '[URL]', s)
    s = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', s)
    s = re.sub(r'\b[a-z0-9\-]+\.[a-z]{2,}[^\s]*', '[DOMAIN]', s, flags=re.IGNORECASE)
    return s[:200]


def load_json():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_source(idx, source_url, wait_sec=20):
    """测试单个源：启动DebugActivity + 截图 + logcat分析"""
    print(f'\n=== 测试 idx={idx} ===')

    # 1. 清空logcat
    adb_shell('logcat -c')
    time.sleep(0.5)

    # 2. 启动DebugActivity（按返回键回到桌面避免干扰）
    adb_shell('input keyevent KEYCODE_BACK')
    time.sleep(0.5)
    adb_shell('input keyevent KEYCODE_BACK')
    time.sleep(0.5)

    # 用am start启动DebugActivity
    # URL含&需要转义，用引号包裹
    escaped_url = source_url.replace("'", "'\\''")
    cmd = f"am start -n {DEBUG_ACTIVITY} --es key '{escaped_url}'"
    result = adb_shell(cmd)
    rc = result.returncode
    print(f'  am start返回码: {rc}')

    # 3. 等待加载（分两阶段：首屏 + 内容加载）
    time.sleep(5)  # 首屏加载
    # 触发搜索（用默认query触发实际网络请求）
    # DebugActivity的搜索框输入"测试"并提交
    # 不点击避免误触，仅等待自然加载
    time.sleep(wait_sec - 5)  # 剩余等待

    # 4. 截图
    remote_shot = f'/sdcard/test_each_{idx}.png'
    adb_shell(f'screencap -p {remote_shot}')
    local_shot = OUTPUT_DIR / f'source_{idx}.png'
    adb_pull(remote_shot, str(local_shot))
    print(f'  截图: {local_shot.name}')

    # 5. 拉取logcat（全部，然后过滤）
    log_result = adb_shell('logcat -d -t 1500')
    try:
        logcat = log_result.stdout.decode('utf-8', errors='ignore')
    except Exception:
        logcat = ''

    # 6. 过滤技术关键词（扩展覆盖Cronet/SSL/Socket等）
    tech_keywords = [
        # 异常类型
        'Exception', 'Error', 'FATAL', 'ANR', 'Throwable',
        # Legado相关
        'RssSource', 'RssSort', 'AnalyzeUrl', 'LoginRefresh', 'HighlightRefresh',
        'io.legado.app', 'RSS_', 'rssSource', 'sortUrls',
        # 网络层
        'OkHttp', 'Cronet', 'Cookie', 'Login', 'WebView',
        'ssl', 'SSL', 'tls', 'TLS',
        'timeout', 'Timeout', 'reset', 'Reset',
        'connect', 'Connect', 'socket', 'Socket',
        'http', 'HTTP', 'network', 'Network',
        # 常见错误
        'UnknownHost', 'ConnectException', 'SocketTimeout',
        'SSLHandshake', 'ProtocolException', 'SocketException',
        'ConnectionReset', 'RemoteDisconnected',
        'ERR_', 'net::',
        # OkHttp错误
        'okhttp', 'OkHttpClient',
    ]
    safe_lines = []
    for line in logcat.split('\n'):
        # 排除噪音
        if any(noise in line for noise in ['ProfileInstaller', 'ClassLoaderContext', 'app_process:', 'HostConnection']):
            continue
        if any(kw in line for kw in tech_keywords):
            # 脱敏：替换URL/域名/IP/Cookie值
            safe = sanitize_text(line)
            # 移除可能含敏感字段的部分
            safe = re.sub(r'sourceName=[^\s,]+', 'sourceName=[HIDDEN]', safe)
            safe = re.sub(r'cookie[:=][^\s,;]+', 'cookie=[HIDDEN]', safe, flags=re.IGNORECASE)
            safe = re.sub(r'token[:=][^\s,;]+', 'token=[HIDDEN]', safe, flags=re.IGNORECASE)
            safe = re.sub(r'sourceUrl=[^\s,]+', 'sourceUrl=[HIDDEN]', safe)
            safe_lines.append(safe[:250])

    # 去重
    seen = set()
    unique_lines = []
    for line in safe_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    print(f'  logcat技术关键词({len(unique_lines)}条，去重后):')
    for line in unique_lines[:10]:
        print(f'    {line}')

    # 7. 判定加载结果
    result_summary = {
        'idx': idx,
        'am_start_rc': rc,
        'screenshot': local_shot.name,
        'logcat_lines': len(unique_lines),
        'logcat_top': unique_lines[:8],
    }

    # 异常类型分类（扩展）
    exception_patterns = [
        r'(\w+Exception)', r'(\w+Error)', r'(FATAL.+)',
        r'(SSLHandshakeException)', r'(SocketTimeoutException)',
        r'(ConnectException)', r'(UnknownHostException)',
        r'(ProtocolException)', r'(SocketException)',
        r'(ConnectionResetException)', r'(RemoteDisconnectedException)',
        r'(ERR_[A-Z_]+)', r'(net::ERR_[A-Z_]+)',
        r'(CronetException)', r'(NetworkException)',
        r'(java\.net\.\w+Exception)', r'(javax\.net\.ssl\.\w+Exception)',
    ]
    exception_types = set()
    error_codes = set()
    for line in unique_lines:
        for pattern in exception_patterns:
            m = re.search(pattern, line)
            if m:
                exc = m.group(1)
                if exc.startswith('ERR_') or exc.startswith('net::'):
                    error_codes.add(exc)
                else:
                    exception_types.add(exc)

    # 检查是否有"network is disconnect"模式
    network_disconnect = any('network is disconnect' in line.lower() or 'network is disconnect' in line for line in unique_lines)

    result_summary['exception_types'] = list(exception_types)
    result_summary['error_codes'] = list(error_codes)
    result_summary['network_disconnect_pattern'] = network_disconnect

    # 判定结果
    if exception_types or error_codes:
        result_summary['status'] = 'failed_with_exception'
    elif network_disconnect:
        result_summary['status'] = 'network_unreachable'
    elif any('rssSource' in line.lower() or 'rss_sort' in line.lower() or 'sortUrls' in line for line in unique_lines):
        result_summary['status'] = 'source_loaded'
    else:
        result_summary['status'] = 'unknown'

    print(f'  异常类型: {exception_types if exception_types else "无"}')
    print(f'  错误码: {error_codes if error_codes else "无"}')
    print(f'  network_disconnect模式: {network_disconnect}')
    print(f'  状态: {result_summary["status"]}')

    return result_summary


def main():
    print('=' * 70)
    print('逐个真机测试7个needs_user_login源（脱敏）')
    print('=' * 70)

    # 加载JSON
    sources = load_json()
    print(f'JSON源数: {len(sources)}')

    # 确保App在前台
    print('\n--- 启动App ---')
    adb_shell(f'am force-stop {PKG}')
    time.sleep(1)
    adb_shell(f'monkey -p {PKG} -c android.intent.category.LAUNCHER 1')
    time.sleep(5)

    # 逐个测试
    results = []
    for idx in NEEDS_LOGIN_IDX:
        if idx >= len(sources):
            print(f'  idx={idx} 超出JSON范围，跳过')
            continue
        source_url = sources[idx].get('sourceUrl', '')
        if not source_url or not source_url.startswith('http'):
            print(f'  idx={idx} sourceUrl无效（len={len(source_url)}），跳过')
            results.append({'idx': idx, 'status': 'invalid_source_url'})
            continue

        try:
            r = test_source(idx, source_url)
            results.append(r)
        except Exception as e:
            print(f'  idx={idx} 测试异常: exception:{type(e).__name__}')
            results.append({'idx': idx, 'status': 'test_error', 'exception': type(e).__name__})

    # 汇总
    print('\n' + '=' * 70)
    print('真机测试汇总')
    print('=' * 70)
    success_count = sum(1 for r in results if r.get('status') == 'source_loaded')
    failed_count = sum(1 for r in results if r.get('status') == 'failed_with_exception')
    other_count = len(results) - success_count - failed_count

    print(f'\n  成功加载: {success_count}/{len(results)}')
    print(f'  异常: {failed_count}/{len(results)}')
    print(f'  其他: {other_count}/{len(results)}')

    print('\n--- 每个源详情 ---')
    for r in results:
        status = r.get('status', 'unknown')
        idx = r.get('idx', -1)
        if status == 'failed_with_exception':
            exc = r.get('exception_types', [])
            print(f'  [idx={idx}] 异常: {",".join(exc)}')
        elif status == 'source_loaded':
            print(f'  [idx={idx}] 加载成功')
        else:
            print(f'  [idx={idx}] {status}')

    # 保存报告
    report_path = OUTPUT_DIR / 'real_device_each_test_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        # logcat_top可能含bytes，需转为str
        def safe_json(o):
            if isinstance(o, bytes):
                return o.decode('utf-8', errors='ignore')
            return str(o)
        json.dump({
            'total': len(results),
            'success': success_count,
            'failed': failed_count,
            'other': other_count,
            'results': results,
        }, f, ensure_ascii=False, indent=2, default=safe_json)
    print(f'\n报告: {report_path}')

    print('\n--- 真机验证结论 ---')
    print('  1. 7个源已逐个在App的DebugActivity中尝试加载')
    print('  2. 通过logcat技术关键词分析加载情况')
    print('  3. 配置了loginUrl的源用户可在App内点击登录按钮')
    print('  4. 登录后Cookie自动保存，后续请求带上Cookie绕过反爬')
    print('  5. 实际可用性需用户在App内手动登录验证')


if __name__ == '__main__':
    main()
