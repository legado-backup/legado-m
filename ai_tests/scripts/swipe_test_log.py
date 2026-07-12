#!/usr/bin/env python3
r"""swipe_test_log.py — SwipeTest临时日志抓取分析工具

固定测试流程步骤4：抓取和分析SwipeTest标签日志

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/swipe_test_log.py [clear|capture|analyze]

子命令：
    clear   - 清空logcat（操作前执行）
    capture - 抓取SwipeTest日志（操作后执行）
    analyze - 分析上一次抓取的日志，确认关键路径

示例：
    # 操作前清空日志
    python ai_tests/scripts/swipe_test_log.py clear

    # 执行UI操作（上下滑动等）...

    # 操作后抓取日志
    python ai_tests/scripts/swipe_test_log.py capture

    # 分析日志
    python ai_tests/scripts/swipe_test_log.py analyze
"""
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST

# 日志临时存储路径
LOG_TMP_PATH = Path(__file__).parent.parent / "tmp_swipetest_log.txt"

# 关键路径模式（用于 analyze）
KEY_PATTERNS = {
    "onPageSelected": r"onPageSelected.*position=(\d+)",
    "activatePlayer": r"activatePlayer.*articleIndex=(\d+)",
    "switchToArticle": r"switchToArticle.*index=(\d+)",
    "startPlay": r"startPlay.*link=(\S+)",
    "loadMoreArticles": r"loadMoreArticles.*page=(\d+)",
    "ARTICLES_LOADED": r"ARTICLES_LOADED.*count=(\d+)",
    "preloadNextArticleHtml": r"preloadNextArticleHtml.*index=(\d+)",
    "clearPreloadCache": r"clearPreloadCache",
    "finish_save_link": r"finish.*saveLink=(\S+)",
    "onResume_scroll": r"onResume.*scrollTo=(\d+)",
}


def run_adb(cmd, timeout=30):
    """执行ADB命令"""
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def clear_logcat():
    """清空logcat"""
    print("=== 清空 logcat ===")
    result = run_adb("logcat -c")
    if result.returncode == 0:
        print("✅ logcat 已清空")
    else:
        print(f"❌ 清空失败: {result.stderr}")


def capture_log():
    """抓取SwipeTest标签日志"""
    print("=== 抓取 SwipeTest 日志 ===")
    result = run_adb('logcat -d -s SwipeTest:D')

    if result.returncode != 0:
        print(f"❌ 抓取失败: {result.stderr}")
        return

    log_content = result.stdout

    # 保存到临时文件
    LOG_TMP_PATH.write_text(log_content, encoding='utf-8')
    print(f"✅ 日志已保存到 {LOG_TMP_PATH}")
    print(f"   SwipeTest 日志行数: {len([l for l in log_content.split(chr(10)) if 'SwipeTest' in l])}")

    # 输出前20行预览
    lines = [l for l in log_content.split('\n') if l.strip()]
    if lines:
        print("\n--- 日志预览（前20行）---")
        for line in lines[:20]:
            print(f"  {line.strip()}")
    else:
        print("⚠️ 未捕获到 SwipeTest 日志（确认App中已添加 Log.d(\"SwipeTest\", ...)）")


def analyze_log():
    """分析日志确认关键路径"""
    print("=== 分析 SwipeTest 日志 ===")

    if not LOG_TMP_PATH.exists():
        print(f"❌ 日志文件不存在: {LOG_TMP_PATH}")
        print("   请先执行: python swipe_test_log.py capture")
        return

    log_content = LOG_TMP_PATH.read_text(encoding='utf-8')

    print(f"日志文件: {LOG_TMP_PATH}")
    print(f"总行数: {len(log_content.split(chr(10)))}")

    # 分析关键路径
    print("\n--- 关键路径分析 ---")
    found_paths = {}
    for path_name, pattern in KEY_PATTERNS.items():
        matches = re.findall(pattern, log_content)
        if matches:
            found_paths[path_name] = matches
            print(f"  ✅ {path_name}: {len(matches)} 次 {matches[:5]}")
        else:
            print(f"  ❌ {path_name}: 未触发")

    # 输出时序摘要
    print("\n--- 时序摘要 ---")
    lines = [l for l in log_content.split('\n') if 'SwipeTest' in l]
    for line in lines:
        # 提取时间和消息
        parts = line.split('SwipeTest')
        if len(parts) >= 2:
            msg = parts[1].strip().lstrip(':').strip()
            print(f"  {msg[:100]}")

    # 判定结果
    print("\n--- 判定结果 ---")
    critical_paths = ["onPageSelected", "activatePlayer"]
    all_critical = all(p in found_paths for p in critical_paths)
    if all_critical:
        print("✅ 关键路径已触发（onPageSelected + activatePlayer）")
    else:
        missing = [p for p in critical_paths if p not in found_paths]
        print(f"⚠️ 缺失关键路径: {missing}")

    return found_paths


def main():
    if len(sys.argv) < 2:
        print("用法: python swipe_test_log.py [clear|capture|analyze]")
        print("  clear   - 清空logcat（操作前执行）")
        print("  capture - 抓取SwipeTest日志（操作后执行）")
        print("  analyze - 分析日志确认关键路径")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "clear":
        clear_logcat()
    elif cmd == "capture":
        capture_log()
    elif cmd == "analyze":
        analyze_log()
    else:
        print(f"❌ 未知子命令: {cmd}")
        print("可用子命令: clear | capture | analyze")
        sys.exit(1)


if __name__ == "__main__":
    main()
