# -*- coding: utf-8 -*-
"""
AI 调试通道「一键初始化」（design AD-05 / tasks 2.3、2.4）

一条命令完成：设备校验 → 拉起 App（触发内腿自启）→ 端口转发 → 凭据落本机临时文件 →
MCP `initialize` 探活 → 输出 PASS/FAIL 与失败原因。

用法：
    ai_tests\\venv\\Scripts\\python.exe scripts/ai_debug_init.py
    ai_tests\\venv\\Scripts\\python.exe scripts/ai_debug_init.py --device 127.0.0.1:21503
    ai_tests\\venv\\Scripts\\python.exe scripts/ai_debug_init.py --no-launch     # 假定 App 已在运行

输出安全（tasks 2.3 安全标准）：**stdout 永不出现凭据原文**，只给长度与掩码；
凭据只写入项目 `.temp/`（已 gitignore）下的单文件，不入库、不进日志。

失败原因（tasks 2.4）：未找到 adb / 设备离线 / App 未安装 / 服务未起（端口不通）/
端口转发失败 / 探活超时 / 鉴权失败（401）。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADB_CANDIDATES = [r"C:\Android\Sdk\platform-tools\adb.exe", "adb"]
DEFAULT_DEVICE = "127.0.0.1:21503"
DEFAULT_PKG = "io.legado.miss.app.debug"
PORT = 8765
TOKEN_FILE = ROOT / ".temp" / "dev_token.txt"
DEBUG_BRANCH_SRC = ROOT / "app/src/debug/java/io/legado/app/web/WebAuthDebugBranch.kt"

PASS, FAIL = "PASS", "FAIL"


class Fail(Exception):
    """可读失败：直接作为 FAIL 原因输出。"""


def find_adb(cli: str | None) -> str:
    for c in ([cli] if cli else []) + ADB_CANDIDATES:
        if not c:
            continue
        if "\\" in c or "/" in c:
            if Path(c).exists():
                return c
        else:
            p = shutil.which(c)
            if p:
                return p
    raise Fail("未找到 adb（请用 --adb 指定，或把 platform-tools 加入 PATH）")


def run(cmd: list[str], timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise Fail(f"命令失败({proc.returncode})：{' '.join(cmd[:3])} … {proc.stderr.strip()[:160]}")
    return proc


def read_fixed_token() -> str:
    """凭据单一真源 = debug 变体源码常量（避免脚本内再抄一份 ⇒ 仓库不新增凭据副本）。"""
    if not DEBUG_BRANCH_SRC.exists():
        raise Fail(f"未找到 debug 支路源码：{DEBUG_BRANCH_SRC}")
    text = DEBUG_BRANCH_SRC.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'FIXED_TOKEN\s*=\s*"([^"]{16,})"', text)
    if not m:
        raise Fail("debug 支路源码中未找到 FIXED_TOKEN 常量")
    return m.group(1)


def mask(token: str) -> str:
    return f"{token[:2]}***<len={len(token)}>"


def check_device(adb: str, device: str) -> None:
    out = run([adb, "devices"], check=False).stdout
    line = next((l for l in out.splitlines() if l.startswith(device)), None)
    if line is None:
        raise Fail(f"设备 {device} 不在 adb devices 列表中（先启动模拟器或 adb connect）")
    if "device" not in line.split("\t")[-1].strip():
        raise Fail(f"设备 {device} 状态异常（offline/unauthorized）")


def check_pkg(adb: str, device: str, pkg: str) -> None:
    out = run([adb, "-s", device, "shell", "pm list packages " + pkg], check=False).stdout
    if pkg not in out:
        raise Fail(f"设备上未安装 {pkg}（请先安装 debug 测试包）")


def launch_app(adb: str, device: str, pkg: str) -> None:
    run([adb, "-s", device, "shell",
         f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"], check=False, timeout=60)


def port_open(adb: str, device: str) -> bool:
    """用设备侧 netstat 判断内腿端口是否在监听（避免依赖 forward 后再探）。"""
    out = run([adb, "-s", device, "shell", f"netstat -ltn 2>/dev/null | grep {PORT}"],
              check=False).stdout
    return str(PORT) in out


def wait_service(adb: str, device: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if port_open(adb, device):
            return
        time.sleep(2)
    raise Fail(f"内腿服务未就绪：{timeout_s:.0f}s 内未见端口 {PORT} 监听（App 未启动或服务启动失败，看 logcat 关键词 McpDebugService）")


def forward(adb: str, device: str) -> None:
    run([adb, "-s", device, "forward", "--remove", f"tcp:{PORT}"], check=False)
    out = run([adb, "-s", device, "forward", f"tcp:{PORT}", f"tcp:{PORT}"], check=False)
    if str(PORT) not in out.stdout:
        raise Fail(f"端口转发失败：{out.stdout.strip() or out.stderr.strip()}")


def mcp_initialize(token: str, timeout_s: float = 20.0) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "ai-debug-init", "version": "1.0"}},
    }).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/mcp", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/json, text/event-stream")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Fail("鉴权失败（401）：支路未生效或凭据不匹配（可检查 PreferKey.webAuthDebugBranch 是否为 false）")
        raise Fail(f"探活返回 HTTP {e.code}")
    except urllib.error.URLError as e:
        raise Fail(f"探活超时/连接失败：{type(e.reason).__name__ if hasattr(e, 'reason') else type(e).__name__}")
    except TimeoutError:
        raise Fail("探活超时")
    if raw.startswith("data:") or "data:" in raw:
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
    try:
        return json.loads(raw)
    except Exception as exc:  # noqa
        raise Fail(f"探活响应非 JSON：{type(exc).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=DEFAULT_DEVICE)
    ap.add_argument("--pkg", default=DEFAULT_PKG)
    ap.add_argument("--adb", default=None)
    ap.add_argument("--no-launch", action="store_true", help="假定 App 已在运行，不主动拉起")
    args = ap.parse_args()

    steps: list[str] = []
    try:
        adb = find_adb(args.adb)
        steps.append(f"adb        : {adb}")

        token = read_fixed_token()
        steps.append(f"支路凭据   : {mask(token)}（来源：debug 变体源码常量）")

        check_device(adb, args.device)
        steps.append(f"设备       : {args.device} 在线")

        check_pkg(adb, args.device, args.pkg)
        steps.append(f"应用       : {args.pkg} 已安装")

        if args.no_launch:
            steps.append("拉起       : 跳过（--no-launch）")
        else:
            launch_app(adb, args.device, args.pkg)
            steps.append("拉起       : 已触发 Launcher（debug 变体 onCreate 自启内腿，幂等）")

        wait_service(adb, args.device)
        steps.append(f"内腿服务   : 端口 {PORT} 已监听")

        forward(adb, args.device)
        steps.append(f"端口转发   : tcp:{PORT} → tcp:{PORT}")

        resp = mcp_initialize(token)
        server = (resp.get("result") or {}).get("serverInfo") or {}
        steps.append(f"探活       : initialize OK（server={server.get('name', '?')} v{server.get('version', '?')}）")

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token, encoding="utf-8")
        steps.append(f"凭据落盘   : {TOKEN_FILE.relative_to(ROOT)}（已 gitignore，未打印原文）")

        print("\n".join(steps))
        print(f"结果       : {PASS}")
        print("后续可直接用：MCP 客户端 POST http://127.0.0.1:8765/mcp（Bearer 见 .temp/dev_token.txt）")
        return 0

    except Fail as e:
        steps.append(f"原因       : {e}")
        print("\n".join(steps))
        print(f"结果       : {FAIL}")
        return 1
    except subprocess.TimeoutExpired as e:
        steps.append(f"原因       : 命令超时（{e.cmd[:2]}）")
        print("\n".join(steps))
        print(f"结果       : {FAIL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())