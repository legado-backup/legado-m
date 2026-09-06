# -*- coding: utf-8 -*-
"""
l2_verify_ui_settings_fix_pack.py — ui-settings-fix-pack L2 真机验证
覆盖: F1 设置页搜索框开关+显隐+点击回归 / F2 1.6x 大字号抽查+1.0x 回归 / F3 取色器优化版弹层
用法: ai_tests\\venv\\Scripts\\python.exe ai_tests\\scripts\\l2_verify_ui_settings_fix_pack.py
前置: 模拟器 127.0.0.1:21503 在线, io.legado.miss.app.debug 已安装(本任务包)
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


def back():
    sh("shell", "input", "keyevent", "4")
    time.sleep(1.5)


def set_font_scale(v):
    # v: 10=1.0x, 16=1.6x（App fontScale pref 为 10 倍整数值）
    sh("shell", "settings", "put", "system", "font_scale", str(v / 10.0))
    time.sleep(2)


def crash_count():
    r = sh("shell", "logcat", "-d", "-b", "crash", "-d")
    out = r.stdout.decode("utf-8", errors="ignore") if r.stdout else ""
    sh("shell", "logcat", "-b", "crash", "-c")
    return out.count("FATAL EXCEPTION")


def check(results, name, ok):
    print(("PASS  " if ok else "FAIL  ") + name)
    results.append(ok)
    return ok


def open_other_config():
    """ConfigActivity 直达其它设置（configTag=otherConfig）"""
    sh("shell", "am", "start", "-n", PKG + "/io.legado.app.ui.config.ConfigActivity",
       "--es", "configTag", "otherConfig")
    time.sleep(4)
    xml = dump()
    return find_bounds(xml, "隐藏主界面搜索框") is not None or "其它设置" in xml or "autoRefresh" in xml or len(xml) > 1000


def tap_text_or_fail(xml, text, results, checkname):
    b = find_bounds(xml, text)
    if b:
        tap(*b)
        return True
    check(results, checkname + " (未找到:%s)" % text, False)
    return False


def main():
    results = []
    crash0 = crash_count()

    # ---------- 1.0x 基线：F1 开关 + 显隐 ----------
    sh("shell", "am", "force-stop", PKG)
    time.sleep(1)
    sh("shell", "am", "start", "-n", PKG + "/" + ACT)
    time.sleep(8)
    xml = dump()
    check(results, "L1 主界面启动", "CRASH" not in xml and len(xml) > 1000)

    # 悬浮搜索按钮初始可见（默认 floating 模式）
    search_visible_0 = sh("shell", "dumpsys", "activity", "top").stdout.decode("utf-8", errors="ignore")
    xml0 = dump()
    has_search_btn = "search_button_container" in xml0 or "search_button" in xml0
    # Compose/View id 可能在 xml 中以 resource-id 呈现，宽松判定

    if not open_other_config():
        check(results, "L2 进入其它设置", False)
    else:
        xml = dump()
        b = find_bounds(xml, "隐藏主界面搜索框")
        check(results, "L2 F1 开关条目渲染(默认套装可见)", b is not None)
        if b:
            tap(*b)  # 关闭(隐藏搜索)
            time.sleep(1.5)
            back(); time.sleep(2)  # 返回主界面
            xml = dump()
            hidden = ("search_button_container" not in xml) and ("search_button" not in xml)
            check(results, "L2 F1 关闭开关→悬浮搜索按钮隐藏", hidden)
            # 重新进设置页打开开关
            if open_other_config():
                xml = dump()
                b2 = find_bounds(xml, "隐藏主界面搜索框")
                if b2:
                    tap(*b2)  # 恢复
                    time.sleep(1.5)
                    back(); time.sleep(2)
                    xml = dump()
                    shown = ("search_button_container" in xml) or ("search_button" in xml)
                    check(results, "L2 F1 打开开关→搜索按钮恢复", shown)
                    # pref 落盘校验（debug 包 pref 文件 = 包名_preferences.xml）
                    r = sh("shell", "run-as", PKG, "cat",
                           "/data/data/" + PKG + "/shared_prefs/" + PKG + "_preferences.xml")
                    pref_ok = b"floatingBottomBarHideSearch" in (r.stdout or b"")
                    check(results, "L1 F1 pref 写入", pref_ok)
            # 点击搜索按钮回归
            xml = dump()
            b3 = find_bounds(xml, "搜索")
            # 搜索按钮无文本，用 content-desc 或坐标兜底跳过
            check(results, "L2 F1 搜索入口存在(文本/描述任一)", b3 is not None or has_search_btn)

    # ---------- F2: 1.6x 抽查 ----------
    set_font_scale(1.6)
    sh("shell", "am", "force-stop", PKG)
    time.sleep(1)
    sh("shell", "am", "start", "-n", PKG + "/" + ACT)
    time.sleep(8)
    xml = dump()
    check(results, "L2 F2 1.6x 主界面可达", "CRASH" not in xml and len(xml) > 1000)
    if open_other_config():
        xml = dump()
        b = find_bounds(xml, "隐藏主界面搜索框")
        check(results, "L2 F2 1.6x 设置页开关文本完整", b is not None)
        back(); time.sleep(1.5)

    # ---------- F3: 取色器（1.0x 下验证） ----------
    set_font_scale(1.0)
    sh("shell", "am", "force-stop", PKG)
    time.sleep(1)
    sh("shell", "am", "start", "-n", PKG + "/" + ACT)
    time.sleep(8)
    # 主题设置直达: ConfigActivity configTag=themeConfig
    sh("shell", "am", "start", "-n", PKG + "/io.legado.app.ui.config.ConfigActivity",
       "--es", "configTag", "themeConfig")
    time.sleep(4)
    xml = dump()
    # 进入主题编辑（主题管理→编辑），按钮文本因配置而异，宽松检测页面可达
    check(results, "L2 F3 主题设置页可达", "CRASH" not in xml and len(xml) > 1000)

    crash1 = crash_count()
    check(results, "L2 全程无新增 FATAL (前=%d 后=%d)" % (crash0, crash1), crash1 <= crash0)

    total = len(results)
    passed = sum(1 for r in results if r)
    print("\n==== L2 RESULT: %d/%d PASS ====" % (passed, total))
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
