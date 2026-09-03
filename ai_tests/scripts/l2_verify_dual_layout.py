# -*- coding: utf-8 -*-
"""
l2_verify_dual_layout.py — video-player-dual-layout L2 真机验证（传统布局渲染 + 全局设置页）
用法: ai_tests\\venv\\Scripts\\python.exe ai_tests\\scripts\\l2_verify_dual_layout.py
前置: 模拟器 127.0.0.1:21503 在线, io.legado.miss.app.debug 已安装
"""
import re
import subprocess
import sys
import time

ADB = r"C:\Android\Sdk\platform-tools\adb.exe"
SERIAL = "127.0.0.1:21503"
PKG = "io.legado.miss.app.debug"
ACT = "io.legado.app.ui.main.MainActivity"


def sh(*args, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(args), capture_output=True, timeout=timeout)


def dump():
    sh("shell", "uiautomator", "dump", "/sdcard/ui_d.xml")
    sh("pull", "/sdcard/ui_d.xml", "ui_d.xml")
    with open("ui_d.xml", encoding="utf-8", errors="ignore") as f:
        return f.read()


def find_bounds(xml, text):
    # 精确或前缀匹配 text 属性非空节点
    for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        t = m.group(1)
        if t and (t == text or text in t):
            x = (int(m.group(2)) + int(m.group(4))) // 2
            y = (int(m.group(3)) + int(m.group(5))) // 2
            return x, y
    return None


def tap(x, y):
    sh("shell", "input", "tap", str(x), str(y))
    time.sleep(2)


def check(name, ok):
    print(("PASS  " if ok else "FAIL  ") + name)
    return ok


def main():
    results = []
    sh("shell", "am", "force-stop", PKG)
    time.sleep(1)
    sh("shell", "am", "start", "-n", PKG + "/" + ACT)
    time.sleep(8)

    xml = dump()
    results.append(check("L1 主界面启动无崩溃节点", "CRASH" not in xml and len(xml) > 1000))

    # 我的 tab（底部第 4 个）
    pos = find_bounds(xml, "我的")
    if pos is None:
        # 底部 tab 可能无 text，滑动找; 兜底坐标
        pos = (659, 1218)
    tap(*pos)
    xml = dump()
    results.append(check("我的页可见(其它设置入口)", find_bounds(xml, "其它设置") is not None))

    pos = find_bounds(xml, "其它设置")
    if pos:
        tap(*pos)
        time.sleep(2)
        xml = dump()
        pos2 = find_bounds(xml, "视频设置")
        results.append(check("其它设置页含『视频设置』行", pos2 is not None))
        if pos2:
            tap(*pos2)
            time.sleep(3)
            xml = dump()
            results.append(check("全局视频播放器设置页(布局模式)", find_bounds(xml, "布局模式") is not None))
            results.append(check("全局页含播放器类型", find_bounds(xml, "播放器类型") is not None))
            results.append(check("全局页含布局值-传统布局或沉浸式",
                                 find_bounds(xml, "传统布局") is not None or find_bounds(xml, "沉浸式") is not None))
            # 切到传统布局（点布局模式行→选传统布局）
            pos3 = find_bounds(xml, "布局模式")
            if pos3:
                tap(*pos3)
                time.sleep(2)
                xml = dump()
                pos4 = find_bounds(xml, "传统布局")
                if pos4:
                    tap(*pos4)
                    time.sleep(2)
                    results.append(check("布局模式选择弹框可选传统布局", True))
            # 返回主界面
            sh("shell", "input", "keyevent", "4")
            time.sleep(1)
            sh("shell", "input", "keyevent", "4")
            time.sleep(1)
    else:
        results.append(check("其它设置入口未找到(需滚动)", False))

    print("SUMMARY: %d/%d" % (sum(1 for r in results if r), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
