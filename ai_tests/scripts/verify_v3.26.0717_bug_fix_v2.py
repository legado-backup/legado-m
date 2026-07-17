"""v3.26.0717 bug fix 验证脚本 v2 - 逐步验证并保存结果"""
import sys
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uiautomator2 as u2

DEVICE = "127.0.0.1:21503"
PKG = "io.legado.app.debug"
ADB = "D:/Program Files/Microvirt/MEmu/adb.exe"
REPORT = Path("ai_tests/reports/v3.26.0717-bug-fix-verify")
REPORT.mkdir(parents=True, exist_ok=True)
LOG_FILE = REPORT / "verify_log.txt"

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def dump_analyze(d, name):
    """dump UI 并返回根元素"""
    xml = d.dump_hierarchy()
    path = REPORT / f"{name}.xml"
    path.write_text(xml, encoding="utf-8")
    return ET.fromstring(xml)

def find_texts(root, keywords):
    """查找包含关键词的 text"""
    results = []
    for elem in root.iter('node'):
        text = elem.get('text', '')
        if text:
            for kw in keywords:
                if kw in text:
                    rid = elem.get('resource-id', '')
                    results.append((text, rid))
                    break
    return results

def main():
    # 清空日志
    LOG_FILE.write_text("", encoding="utf-8")

    log("=" * 60)
    log("v3.26.0717 bug fix 验证 v2")
    log("=" * 60)

    d = u2.connect(DEVICE)
    log(f"设备连接: {d.info}")

    # 重启应用
    log("\n[步骤1] 重启应用...")
    env = {"MSYS_NO_PATHCONV": "1", "PATH": ""}
    subprocess.run([ADB, "-s", DEVICE, "shell", "am", "force-stop", PKG], env=env)
    time.sleep(1)
    subprocess.run([ADB, "-s", DEVICE, "shell", "am", "start", "-n", f"{PKG}/io.legado.app.ui.main.MainActivity"], env=env)
    time.sleep(3)

    root = dump_analyze(d, "step1_main")
    # 确认在主界面
    main_tabs = find_texts(root, ["书架", "发现", "订阅", "我的"])
    # 也检查 desc
    descs = []
    for elem in root.iter('node'):
        desc = elem.get('content-desc', '')
        if desc and desc in ["书架", "发现", "订阅", "我的"]:
            descs.append(desc)
    log(f"主界面Tab(desc): {descs}")

    # ===== Issue-4: 其他设置并发数显示 =====
    log("\n[Issue-4] 验证其他设置并发数显示")
    log("[步骤2] 点击'我的'...")
    d(description="我的").click()
    time.sleep(1.5)
    root = dump_analyze(d, "step2_my")
    titles = find_texts(root, ["设置", "配置", "主题", "其他", "阅读", "备份", "Web", "关于"])
    log(f"我的页面配置项: {titles[:10]}")

    log("[步骤3] 滚动查找'其他设置'...")
    found_other = False
    for i in range(8):
        d.swipe(360, 800, 360, 200, 0.3)
        time.sleep(0.4)
        root = dump_analyze(d, f"step3_scroll{i}")
        for elem in root.iter('node'):
            text = elem.get('text', '')
            if text and "其他设置" in text:
                log(f"  滚动{i}次找到: {text}")
                found_other = True
                # 点击
                el = d(text=text)
                if el.exists:
                    el.click()
                    time.sleep(1.5)
                break
        if found_other:
            break

    if not found_other:
        # 列出所有 preference_title
        root = dump_analyze(d, "step3_final")
        all_titles = []
        for elem in root.iter('node'):
            rid = elem.get('resource-id', '')
            text = elem.get('text', '')
            if 'preference_title' in rid and text:
                all_titles.append(text)
        log(f"所有 preference_title: {all_titles}")
        log("[FAIL] 未找到'其他设置'")
    else:
        log("[步骤4] 在其他设置页面查找 rss/图片并发...")
        root = dump_analyze(d, "step4_other_config")
        d.screenshot(str(REPORT / "step4_other_config.png"))
        # 查找并发配置项
        for elem in root.iter('node'):
            text = elem.get('text', '')
            rid = elem.get('resource-id', '')
            if text and any(kw in text for kw in ["并发", "RSS", "图片", "加载", "线程", "更新", "搜索"]):
                log(f"  配置项: text={text[:40]} rid={rid}")
        # 查找 summary
        for elem in root.iter('node'):
            rid = elem.get('resource-id', '')
            text = elem.get('text', '')
            if 'preference_summary' in rid and text:
                if any(kw in text for kw in ["并发", "当前", "RSS", "图片", "加载", "线程", "default", "current"]):
                    log(f"  SUMMARY: text={text[:60]}")
        # 滚动查找
        for i in range(5):
            d.swipe(360, 800, 360, 200, 0.3)
            time.sleep(0.4)
            root = dump_analyze(d, f"step4_scroll{i}")
            for elem in root.iter('node'):
                text = elem.get('text', '')
                rid = elem.get('resource-id', '')
                if text and any(kw in text for kw in ["并发", "RSS", "图片加载", "解析并发"]):
                    log(f"  滚动{i}配置项: text={text[:40]} rid={rid}")
                if 'preference_summary' in rid and text:
                    if any(kw in text for kw in ["并发", "当前", "RSS", "图片", "加载", "default", "current"]):
                        log(f"  滚动{i} SUMMARY: text={text[:60]}")

    # ===== Issue-5: 书源域名分组 =====
    log("\n[Issue-5] 验证书源域名分组")
    # 返回主界面
    d.press("back")
    time.sleep(0.5)
    d.press("back")
    time.sleep(0.5)
    # 确认在主界面
    root = dump_analyze(d, "step5_main")
    # 点击"更多选项"菜单
    log("[步骤5] 点击'更多选项'菜单进入书源管理...")
    el = d(description="更多选项")
    if el.exists:
        el.click()
        time.sleep(1)
        root = dump_analyze(d, "step5_menu")
        # 查找"书源管理"
        for elem in root.iter('node'):
            text = elem.get('text', '')
            if text and ("书源" in text or "书源管理" in text):
                log(f"  菜单项: {text}")
                el = d(text=text)
                if el.exists:
                    el.click()
                    time.sleep(1.5)
                    break
    else:
        log("[FAIL] 未找到'更多选项'菜单")

    root = dump_analyze(d, "step5_book_source")
    d.screenshot(str(REPORT / "step5_book_source.png"))
    # 检查是否有 http/https 作为分组标题
    for elem in root.iter('node'):
        text = elem.get('text', '')
        if text and ("http://" == text or "https://" == text or text.startswith("http://") or text.startswith("https://")):
            log(f"  [WARN] 发现URL文本: {text[:30]}")
    # 查找排序/分组相关
    for elem in root.iter('node'):
        text = elem.get('text', '')
        if text and any(kw in text for kw in ["排序", "分组", "域名", "智能", "权重", "反序", "升序", "降序"]):
            log(f"  排序/分组项: {text}")

    # ===== Issue-1: 订阅源解析并发 =====
    log("\n[Issue-1] 验证订阅源解析并发显示")
    d.press("back")
    time.sleep(0.5)
    d.press("back")
    time.sleep(0.5)
    log("[步骤6] 点击'订阅'进入订阅源管理...")
    d(description="订阅").click()
    time.sleep(1.5)
    root = dump_analyze(d, "step6_rss")
    d.screenshot(str(REPORT / "step6_rss.png"))
    # 列出订阅源列表项
    for elem in root.iter('node'):
        text = elem.get('text', '')
        rid = elem.get('resource-id', '')
        if text and 'tv_source_name' in rid:
            log(f"  订阅源: {text[:20]}")
            # 点击第一个进入编辑
            el = d(resourceId=rid)
            if el.exists:
                el.click()
                time.sleep(1)
                break
    root = dump_analyze(d, "step6_rss_edit")
    d.screenshot(str(REPORT / "step6_rss_edit.png"))
    # 查找解析并发
    for elem in root.iter('node'):
        text = elem.get('text', '')
        rid = elem.get('resource-id', '')
        if text and ("解析并发" in text or "parseConcurrency" in text or "并发" in text):
            log(f"  [PASS] 找到解析并发: text={text} rid={rid}")

    log("\n" + "=" * 60)
    log("验证完成。详细截图和XML见 reports/v3.26.0717-bug-fix-verify/")
    log("=" * 60)

if __name__ == "__main__":
    main()
