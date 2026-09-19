"""l2_verify_theme_section.py — A3.6 真机验证：主题设置页三分区标题可见

用法:
    python ai_tests/scripts/l2_verify_theme_section.py [--shot 输出png]
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import uiautomator2 as u2

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
HOST = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default=None)
    args = ap.parse_args()
    d = u2.connect(HOST)
    subprocess.run([ADB, "-s", HOST, "shell", "am", "force-stop", PKG], capture_output=True, timeout=30)
    time.sleep(2)
    # 直接启动主题设置页（ConfigActivity + configTag=themeConfig，全限定类名）
    subprocess.run([ADB, "-s", HOST, "shell", "am", "start", "-n",
                    f"{PKG}/io.legado.app.ui.config.ConfigActivity",
                    "--es", "configTag", "themeConfig"], capture_output=True, timeout=30)
    time.sleep(4)

    xml = d.dump_hierarchy()
    # 页面较长，第三分区在首屏外（dump_hierarchy 只返回可见节点）→ 滚动后合并采集
    # 注意：swipe 绝对坐标依赖分辨率，用 swipe_ext("up") 更稳
    for _ in range(3):
        d.swipe_ext("up", scale=0.6)
        time.sleep(0.8)
    xml += d.dump_hierarchy()
    sections = ["外观与沉浸", "主题与系统界面", "模板与封面"]
    found = {s: (s in xml) for s in sections}
    for s, ok in found.items():
        print(f"  [分区] {s}: {'可见' if ok else '缺失'}")
    # 恢复图标等关键项仍在
    # 关键项（文案取自 values-zh/strings.xml 实际值）
    for item in ["切换图标", "主题列表", "底栏管理", "封面设置"]:
        print(f"  [项] {item}: {'可见' if item in xml else '缺失'}")

    if args.shot:
        d.screenshot(args.shot)
        print(f"  截图: {args.shot}")

    print()
    if all(found.values()):
        print("[PASS] A3.6 主题设置三分区标题全部可见")
        return 0
    print("[FAIL] 存在缺失分区")
    return 1


if __name__ == "__main__":
    sys.exit(main())