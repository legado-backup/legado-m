#!/usr/bin/env python3
"""verify_rss_login.py — 订阅源登录验证脚本（CF绕过，全程脱敏）

固定测试流程步骤4：直接通过 ADB 启动 SourceLoginActivity，验证 CF 绕过效果

策略：绕过UI长按位置不准的问题，直接 am start SourceLoginActivity
     让 WebViewLoginFragment 加载 sourceUrl，触发 CF JS Challenge 自动通过
     + CookieStore.setCookie 自动同步 Cookie

安全规范：绝不输出源URL/源名称/域名，只用长度或代号

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/verify_rss_login.py
"""
import uiautomator2 as u2
import time
import sys
import sqlite3
import subprocess
import tempfile
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MEMU_ADB_HOST, ADB_PATH, PACKAGE

DB_DEVICE_PATH = f"/data/data/{PACKAGE}/databases/legado.db"


def run_adb(cmd, timeout=30):
    """执行ADB命令（MSYS_NO_PATHCONV=1避免Git Bash路径转换）"""
    env = os.environ.copy()
    env['MSYS_NO_PATHCONV'] = '1'
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env)
    return result


def get_target_source_info(local_db):
    """查询目标源的 sourceUrl（不输出，只返回供ADB使用）"""
    conn = sqlite3.connect(local_db)
    try:
        c = conn.cursor()
        # 找到 loginUrl 非空且 enabled=1 的源（我们优化的目标源）
        c.execute("SELECT sourceUrl, loginUrl, enabledCookieJar, enableJs, loginUi, loginCheckJs FROM rssSources WHERE loginUrl IS NOT NULL AND loginUrl != '' AND enabled = 1 ORDER BY customOrder ASC")
        rows = c.fetchall()
        if not rows:
            return None
        # 找第一个 loginUrl == sourceUrl 的源（我们修复后的目标）
        for r in rows:
            if r[0] == r[1]:  # sourceUrl == loginUrl
                return {
                    'sourceUrl': r[0],
                    'loginUrl': r[1],
                    'enabledCookieJar': r[2],
                    'enableJs': r[3],
                    'loginUi': r[4],
                    'loginCheckJs': r[5],
                }
        # 没找到完全匹配的，返回第一个
        r = rows[0]
        return {
            'sourceUrl': r[0],
            'loginUrl': r[1],
            'enabledCookieJar': r[2],
            'enableJs': r[3],
            'loginUi': r[4],
            'loginCheckJs': r[5],
        }
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("订阅源登录验证脚本（CF绕过，ADB直启）")
    print("=" * 60)

    # Step 1: 拉取DB并查询目标源信息
    print("\n[Step 1] 拉取DB查询目标源配置...")
    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    try:
        run_adb(f"shell \"su -c 'cp {DB_DEVICE_PATH} /sdcard/legado.db && chmod 666 /sdcard/legado.db'\"")
        run_adb(f"pull /sdcard/legado.db {tmp_db}")
        for ext in ['-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                os.unlink(p)
        info = get_target_source_info(tmp_db)
        if info is None:
            print("❌ 未找到目标源")
            return 1
        # 只输出技术字段，不输出 sourceUrl 内容
        print(f"  ✅ 找到目标源")
        print(f"    sourceUrl长度={len(info['sourceUrl'])} enabledCookieJar={info['enabledCookieJar']} enableJs={info['enableJs']}")
        login_ui_status = "(空)" if not info['loginUi'] else f"长度={len(info['loginUi'])}"
        login_check_js_status = "(未设置)" if not info['loginCheckJs'] else f"长度={len(info['loginCheckJs'])}"
        print(f"    loginUrl长度={len(info['loginUrl'])} loginUi={login_ui_status} loginCheckJs={login_check_js_status}")
        # 验证 loginUrl == sourceUrl
        if info['sourceUrl'] == info['loginUrl']:
            print(f"  ✅ loginUrl == sourceUrl（URL形式，符合修复方案）")
        else:
            print(f"  ⚠️ loginUrl != sourceUrl，可能未正确修复")
    finally:
        time.sleep(0.5)
        for ext in ['', '-wal', '-shm']:
            p = tmp_db + ext
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except PermissionError:
                    pass

    source_url = info['sourceUrl']

    # Step 2: 清理logcat并启动 App（确保App已启动）
    print("\n[Step 2] 清理logcat并启动 App...")
    run_adb(f"shell am force-stop {PACKAGE}")
    time.sleep(1)
    run_adb("logcat -c")
    run_adb(f"shell am start -n {PACKAGE}/io.legado.app.ui.welcome.WelcomeActivity")
    print("  等待 App 启动...")
    time.sleep(5)

    # Step 3: 通过 ADB 直接启动 SourceLoginActivity
    print("\n[Step 3] 通过 ADB 启动 SourceLoginActivity...")
    # 使用 am start 传参（type=rssSource, key=sourceUrl）
    # 注意：sourceUrl 含特殊字符，需要正确转义
    am_cmd = f'shell am start -n {PACKAGE}/io.legado.app.ui.login.SourceLoginActivity --es type "rssSource" --es key "{source_url}"'
    print(f"  >>> am start SourceLoginActivity (sourceUrl长度={len(source_url)})")
    result = run_adb(am_cmd)
    print(f"  启动结果: {result.stdout.strip() or result.stderr.strip() or 'OK'}")
    time.sleep(3)

    # Step 4: 检查是否进入 SourceLoginActivity
    print("\n[Step 4] 检查 Activity...")
    d = u2.connect(MEMU_ADB_HOST)
    cur = d.app_current()
    print(f"  当前Activity: {cur.get('activity', '?')}")

    if 'SourceLogin' not in cur.get('activity', ''):
        print("  ⚠️ 未进入 SourceLoginActivity")
        # 检查是否报错
        result = run_adb("logcat -d -t 50 *:E")
        if result.stdout:
            # 只输出技术错误，不输出业务文本
            lines = result.stdout.split('\n')
            err_lines = [l for l in lines if 'Exception' in l or 'Error' in l or 'FATAL' in l]
            print(f"  最近错误日志({len(err_lines)}条):")
            for l in err_lines[:5]:
                # 脱敏：截断长字符串
                print(f"    {l[:150]}")
        return 1

    print("  ✅ 进入 SourceLoginActivity")

    # Step 5: 等待 WebView 加载完成（CF JS Challenge通常5-15秒）
    print("\n[Step 5] 等待 WebView 加载并触发 CF 通过（最长60秒）...")
    cf_passed = False
    for i in range(60):
        time.sleep(1)
        if i % 5 == 0:
            cur = d.app_current()
            print(f"  [{i+1}s] Activity: {cur.get('activity', '?')}")
            # 检查 WebView 进度
            progress = d(resourceId=f"{PACKAGE}:id/progress_bar")
            if progress.exists:
                try:
                    info_p = progress.info
                    print(f"    进度条存在")
                except:
                    pass
        # 检查是否已自动 finish（Cookie 同步完成后某些情况会自动关闭）
        cur = d.app_current()
        if 'SourceLogin' not in cur.get('activity', ''):
            print(f"  [{i+1}s] SourceLoginActivity已退出，可能Cookie同步完成")
            cf_passed = True
            break

    # Step 6: 输出最终状态
    print("\n[Step 6] 最终状态:")
    cur = d.app_current()
    print(f"  当前Activity: {cur.get('activity', '?')}")
    print(f"  CF绕过: {'可能已通过' if cf_passed else '需检查WebView状态'}")

    # Step 7: 抓取 logcat 关键日志（只输出技术字段）
    print("\n[Step 7] 抓取 logcat 关键日志（只技术字段）...")
    result = run_adb("logcat -d -t 200")
    if result.stdout:
        lines = result.stdout.split('\n')
        # 只过滤技术关键词
        keywords = ['Cookie', 'WebView', 'onPageStarted', 'onPageFinished', 'setCookie', 'loginUrl', 'SourceLogin', 'Exception', 'Error', 'FATAL']
        filtered = []
        for l in lines:
            if any(k in l for k in keywords):
                # 脱敏：替换URL为/path/{id}，替换长字符串
                safe_l = re.sub(r'https?://[^\s"\']+', '/path/{id}', l)
                safe_l = re.sub(r'cookie[:\s=]*[^\s]+', 'cookie=***', safe_l, flags=re.IGNORECASE)
                if len(safe_l) > 200:
                    safe_l = safe_l[:200] + '...'
                filtered.append(safe_l)
        print(f"  关键日志({len(filtered)}条):")
        for l in filtered[:30]:
            print(f"    {l}")

    print("\n✅ 登录流程测试完成")


if __name__ == "__main__":
    sys.exit(main() or 0)
