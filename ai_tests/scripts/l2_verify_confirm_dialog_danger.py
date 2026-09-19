"""l2_verify_confirm_dialog_danger.py — A2.2.0/A2.2.1 真机验证：确认弹框 destructive 色单源

覆盖：
  T1 LogActivity 溢出菜单「一键清除」→ AppConfirmDialog(destructive=true) 弹出
  T2 确认钮文字（「清除」）像素采样 ≈ AppSemanticColors.Danger = #D44848（容差 ±40）
  T3 无 FATAL EXCEPTION

背景：A2.2.1 把 `AppConfirmDialog`/`ConfirmDialog` 的 destructive 确认钮由
`MaterialTheme.colorScheme.error`（`ThemeSpec` 主题推导：日 #E53935 / 夜 #FF5252）
收口到 `AppDialogStyle.danger`（语义色单源 #D44848，AD-14）。
本脚本用**像素采样**做客观判定，避免"看起来对"。

用法:
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_confirm_dialog_danger.py [--shot out.png]
"""
import argparse
import subprocess
import sys
import time

import uiautomator2 as u2
from PIL import Image

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
HOST = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
ACT = "io.legado.app.ui.log.LogActivity"

S_MORE_MENU = "日志管理"   # log_manage（LogManageScreen 右上角溢出菜单的 contentDescription）
S_CLEAR_ALL = "一键清除"    # log_clear_all
S_CLEAR = "清除"           # clear（确认钮文案）

# AppSemanticColors.Danger = 0xFFD44848（单源真值，A3.2 已落）
DANGER = (0xD4, 0x48, 0x48)
TOL = 40


def fatal_count() -> int:
    out = subprocess.run([ADB, "-s", HOST, "logcat", "-d", "-s", "AndroidRuntime:E"],
                         capture_output=True, text=True, timeout=60).stdout or ""
    return sum(1 for line in out.splitlines() if "FATAL EXCEPTION" in line)


def tap_desc_bottommost(d, desc):
    nodes = d(description=desc)
    if nodes.count == 0:
        return False
    best, best_bottom = None, -1
    for i in range(nodes.count):
        node = nodes[i]
        bottom = node.info.get("bounds", {}).get("bottom", -1)
        if bottom > best_bottom:
            best, best_bottom = node, bottom
    if best is not None:
        best.click()
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default=None)
    args = ap.parse_args()
    d = u2.connect(HOST)
    results = []

    subprocess.run([ADB, "-s", HOST, "logcat", "-c"], capture_output=True, timeout=30)
    subprocess.run([ADB, "-s", HOST, "shell", "am", "force-stop", PKG], capture_output=True, timeout=30)
    time.sleep(2)
    subprocess.run([ADB, "-s", HOST, "shell", "am", "start", "-n", f"{PKG}/{ACT}"],
                   capture_output=True, timeout=30)
    time.sleep(4)

    # --- T1 打开 destructive 确认弹框 ---
    if not tap_desc_bottommost(d, S_MORE_MENU):
        print("[FAIL] T1 未找到「更多菜单」入口")
        return 1
    time.sleep(1.5)
    if not d(text=S_CLEAR_ALL).exists:
        print("[FAIL] T1 溢出菜单中未找到「一键清除」")
        return 1
    d(text=S_CLEAR_ALL).click()
    time.sleep(2.0)
    ok = d(text=S_CLEAR).exists
    results.append(("T1 destructive 确认弹框弹出（确认钮「清除」可见）", ok))
    print(f"  [T1] 确认钮「清除」: {'可见' if ok else '缺失'}")
    if not ok:
        return 1

    shot = args.shot or "output/l2_confirm_dialog_danger.png"
    d.screenshot(shot)

    # --- T2 像素采样确认钮文字色 ≈ #D44848 ---
    info = d(text=S_CLEAR).info
    b = info["bounds"]
    img = Image.open(shot).convert("RGB")
    hits = 0
    total = 0
    for x in range(b["left"], b["right"]):
        for y in range(b["top"], b["bottom"]):
            px = img.getpixel((x, y))
            total += 1
            if all(abs(px[i] - DANGER[i]) <= TOL for i in range(3)):
                hits += 1
    ratio = hits / total if total else 0.0
    near = hits >= 20
    results.append((f"T2 确认钮文字色 ≈ #D44848（命中 {hits}/{total} 像素）", near))
    print(f"  [T2] #D44848 容差内像素 = {hits}/{total}（阈值 ≥20）")
    print(f"  截图: {shot}")

    # --- T3 无崩溃 ---
    fatals = fatal_count()
    results.append(("T3 无 FATAL EXCEPTION", fatals == 0))
    print(f"  [T3] FATAL EXCEPTION = {fatals}")

    print()
    all_pass = all(ok for _, ok in results)
    print(f"== L2 总结: {'ALL PASS' if all_pass else 'HAS FAIL'} ({sum(1 for _, ok in results if ok)}/{len(results)}) ==")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
