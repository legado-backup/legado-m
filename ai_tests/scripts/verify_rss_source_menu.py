"""验证订阅源管理菜单项是否含"校验选中"
进入选择模式后点击菜单，检查菜单项"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uiautomator2 as u2

DEVICE_SERIAL = "127.0.0.1:21503"
PKG = "io.legado.app.debug"

def main():
    print("=" * 60)
    print("验证订阅源管理菜单项")
    print("=" * 60)
    d = u2.connect(DEVICE_SERIAL)
    print(f"[1] 设备连接成功: {d.info.get('productName', 'unknown')}")

    # 启动订阅源管理
    print("\n[2] 启动订阅源管理")
    d.shell(f"am start -n {PKG}/io.legado.app.ui.rss.source.manage.RssSourceActivity")
    time.sleep(3)
    current = d.app_current()
    print(f"  当前 Activity: {current.get('activity', 'unknown')}")

    # 检查是否有订阅源列表
    print("\n[3] 检查订阅源列表")
    # 找到 RecyclerView 中的第一项，长按进入选择模式
    recycler = d(resourceId="io.legado.app.debug:id/recyclerView")
    if recycler.exists:
        print("  [PASS] 找到订阅源列表 RecyclerView")
        # 获取第一项
        first_item = recycler.child(index=0)
        if first_item.exists:
            print("  [INFO] 找到第一项，尝试长按进入选择模式")
            first_item.long_click(duration=2)
            time.sleep(2)
            # 检查是否进入选择模式（SelectActionBar 可见）
            select_bar = d(resourceId="io.legado.app.debug:id/action_bar")
            if select_bar.exists:
                print("  [PASS] 进入选择模式成功")
            else:
                print("  [WARN] SelectActionBar 未出现，尝试其他方式")
        else:
            print("  [WARN] 列表为空，无法进入选择模式")
    else:
        print("  [WARN] RecyclerView 未找到")

    # 点击右上角菜单（三点）
    print("\n[4] 点击菜单按钮")
    # 尝试多种菜单按钮定位方式
    menu_clicked = False
    # 方式1: contentDescription
    for desc in ["更多选项", "More options", "菜单"]:
        menu_btn = d(description=desc)
        if menu_btn.exists:
            print(f"  [INFO] 找到菜单按钮（desc={desc}），点击")
            menu_btn.click()
            time.sleep(1)
            menu_clicked = True
            break
    if not menu_clicked:
        # 方式2: 通过 className 定位 overflow
        overflow = d(className="android.widget.ImageView", descriptionMatches=".*更多.*|.*More.*")
        if overflow.exists:
            print("  [INFO] 找到 overflow 按钮，点击")
            overflow.click()
            time.sleep(1)
            menu_clicked = True

    if menu_clicked:
        # 检查菜单项是否含"校验选中"或"校验"
        print("\n[5] 检查菜单项")
        # 搜索所有 TextView
        menu_items = d(className="android.widget.TextView")
        if menu_items.exists:
            count = menu_items.count
            print(f"  [INFO] 找到 {count} 个菜单项")
            found_check = False
            for i in range(count):
                try:
                    text = menu_items[i].get_text()
                    if text and ("校验" in text or "RSS" in text.upper() or "rss" in text):
                        print(f"  [INFO] 菜单项[{i}]: {text}")
                        if "校验" in text:
                            found_check = True
                except Exception as e:
                    print(f"  [WARN] 读取菜单项[{i}]失败: {e}")
            if found_check:
                print("  [PASS] 找到'校验'菜单项！订阅源校验入口已集成")
            else:
                print("  [FAIL] 未找到'校验'菜单项")
        else:
            print("  [WARN] 菜单未展开或无 TextView")
    else:
        print("  [WARN] 未找到菜单按钮")

    # 截图保存
    print("\n[6] 截图保存")
    d.screenshot("ai_tests/reports/rss_source_menu.png")
    print("  [PASS] 截图已保存: ai_tests/reports/rss_source_menu.png")

    # 检查 PopupMenu 是否含校验项（通过 dump XML）
    print("\n[7] Dump UI XML")
    xml = d.dump_hierarchy()
    with open("ai_tests/reports/rss_source_menu_ui.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    print("  [PASS] UI XML 已保存: ai_tests/reports/rss_source_menu_ui.xml")
    # 检查 XML 是否含"校验"
    if "校验" in xml:
        print("  [PASS] UI XML 含'校验'关键字，订阅源校验菜单项已集成")
    else:
        print("  [WARN] UI XML 不含'校验'关键字")

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
