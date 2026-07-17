#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SSL 握手诊断脚本（模拟器端实验B+C 综合诊断）

用途：
1. 从JSON读取sourceUrl（不输出）
2. 清空logcat
3. 启动SourceLoginActivity触发WebView加载
4. 抓取logcat中ssl/chromium/ERROR关键字
5. 输出技术分析（不输出域名/URL/源名称）

实验设计（控制变量）：
- 实验 A（PC Python ssl）：已证明源站TLS正常（TLSv1.3+TLSv1.2均OK）
- 实验 B（模拟器 curl）：模拟器通常无curl，跳过
- 实验 C（模拟器 OkHttp/WebView）：本脚本，触发WebView加载并抓logcat

输出：仅技术结论，符合output-safety.md
"""
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
DEVICE = "127.0.0.1:21503"
PACKAGE = "io.legado.app.debug"
ACTIVITY = f"{PACKAGE}/io.legado.app.ui.login.SourceLoginActivity"


def run_adb(args, timeout=30):
    """执行ADB命令，返回stdout"""
    cmd = [ADB, "-s", DEVICE] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout + r.stderr
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


def load_source_url(json_path: str) -> str:
    """从JSON读取sourceUrl（不输出）"""
    p = Path(json_path)
    if not p.exists():
        print(f"[ERROR] 文件不存在: {p}")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        src = data[0] if data else {}
    else:
        src = data
    url = src.get("sourceUrl")
    if not url:
        print("[ERROR] 未找到sourceUrl字段")
        sys.exit(1)
    return url


def main():
    if len(sys.argv) < 2:
        print("用法: python diag_ssl_emulator.py <json路径>")
        sys.exit(1)

    json_path = sys.argv[1]
    source_url = load_source_url(json_path)

    # 脱敏输出
    parsed = urllib.parse.urlparse(source_url)
    host = parsed.hostname or ""
    print(f"[TARGET] host=({host[:2]}***, len={len(host)}), port={parsed.port or 443}")

    # Step 1: 检查设备
    devices = run_adb(["devices"])
    if DEVICE not in devices:
        print(f"[ERROR] 设备 {DEVICE} 未连接")
        sys.exit(1)
    print(f"[OK] 设备已连接: {DEVICE}")

    # Step 2: 检查App是否已安装
    check_app = run_adb(["shell", "pm", "list", "packages", PACKAGE])
    if PACKAGE not in check_app:
        print(f"[ERROR] App未安装: {PACKAGE}")
        sys.exit(1)
    print(f"[OK] App已安装: {PACKAGE}")

    # Step 3: 清空logcat
    run_adb(["logcat", "-c"])
    print("[OK] logcat已清空")

    # Step 4: 启动SourceLoginActivity（绕过UI长按，直接ADB启动）
    # 注意：source_url 作为参数传入，不显示
    start_cmd = [
        "shell",
        "am",
        "start",
        "-n",
        ACTIVITY,
        "--es",
        "type",
        "rssSource",
        "--es",
        "key",
        source_url,
    ]
    start_result = run_adb(start_cmd)
    if "Error" in start_result or "error" in start_result:
        print(f"[ERROR] 启动Activity失败: {start_result[:200]}")
        sys.exit(1)
    print("[OK] SourceLoginActivity已启动，WebView开始加载")

    # Step 5: 等待WebView加载和SSL握手（10秒足够）
    print("[WAIT] 等待10秒让SSL握手完成...")
    time.sleep(10)

    # Step 6: 抓取logcat（过滤SSL/chromium/ERROR相关，但不输出业务字段）
    # 过滤技术关键字：ssl/tls/chromium/net_error/ERROR/handshake/certificate
    logcat = run_adb(["logcat", "-d"], timeout=60)

    # 关键字过滤
    keywords = [
        "ssl", "tls", "chromium", "net_error", "handshake",
        "certificate", "ssl_client_socket", "ERR_SSL", "ERR_CONNECTION",
        "ERR_CERT", "OnReceivedSslError", "WebViewClient",
        "cronet", "Cronet", "okhttp", "OkHttp",
    ]
    filtered_lines = []
    for line in logcat.splitlines():
        line_lower = line.lower()
        if any(kw.lower() in line_lower for kw in keywords):
            filtered_lines.append(line)

    print()
    print("=" * 60)
    print(f"[LOGCAT] SSL/网络相关日志（共{len(filtered_lines)}行）")
    print("=" * 60)

    # 脱敏处理：替换域名/IP/URL/源名称
    import re

    def sanitize(text):
        # 替换URL
        text = re.sub(r"https?://[^\s\"'<>]+", "[URL]", text)
        # 替换IP
        text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]", text)
        # 替换host（如果有）
        if host:
            text = text.replace(host, "[HOST]")
        # 替换cookie/token关键字
        text = re.sub(r"(?i)(cookie|token|password|secret|auth)\s*[=:]\s*\S+", "[SENSITIVE]", text)
        return text

    for line in filtered_lines[:80]:  # 最多输出80行
        print(sanitize(line)[:200])

    print()
    print("=" * 60)
    print("[ANALYSIS] 技术分析：")
    print("=" * 60)

    # 分析
    has_ssl_error = any("ssl" in l.lower() or "ERR_SSL" in l for l in filtered_lines)
    has_net_reset = any("ERR_CONNECTION_RESET" in l or "-101" in l for l in filtered_lines)
    has_cert_error = any("ERR_CERT" in l for l in filtered_lines)
    has_handshake = any("handshake" in l.lower() for l in filtered_lines)
    has_net_error = any("net_error" in l.lower() for l in filtered_lines)
    has_cronet_log = any("cronet" in l.lower() for l in filtered_lines)

    print(f"  - SSL相关日志存在: {has_ssl_error}")
    print(f"  - ERR_CONNECTION_RESET(-101): {has_net_reset}")
    print(f"  - ERR_CERT_*证书错误: {has_cert_error}")
    print(f"  - handshake关键字: {has_handshake}")
    print(f"  - net_error关键字: {has_net_error}")
    print(f"  - Cronet相关日志: {has_cronet_log}")

    print()
    print("[CONCLUSION] 综合PC+模拟器证据：")
    print("  - PC端Python ssl：源站TLS握手正常（TLSv1.3+TLSv1.2均OK）")
    print(f"  - 模拟器WebView：{'SSL握手失败' if has_net_reset or has_ssl_error else '未见明显SSL错误'}")
    if has_net_reset:
        print("  - 排除'源站问题'（PC能访问）")
        print("  - 排除'OkHttp升级'（WebView不走OkHttp）")
        print("  → 真正根因：模拟器WebView版本(Chrome 68)或模拟器网络环境")


if __name__ == "__main__":
    main()
