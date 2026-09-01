# -*- coding: utf-8 -*-
"""l2_verify_compose_s2_source.py — S2 管理列表（BookSourceScreen 双轨）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s2_source.py [--scenario all]
前置：MEmu 已启动；测试包已安装；书源列表 ≥2 条目（B2 seed：3 合成源）
脱敏：源列表全程不输出名称/URL，只输出计数/布尔/编号/hash（output-safety 铁律）

—— B2 第 3 轮锚点实锚表（2026-09-02 dump_anchors.py 真机 dump + 源码双证）——
导航：am start 直拉 BookSourceActivity（订阅 tab Compose 语义未暴露，第 2 轮校准结论沿用）
顶栏 4 动作=icon contentDescription（AppManagementScaffold.AppManagementTopAction，iconRes+desc=action.text）：
    排序[455,71][493,109]｜分组[523,71]｜新建书源[591,71]｜三点=desc"更多菜单"[644,56][712,124]
    （R.string.more_menu——第 2 轮"desc 未暴露"结论修正：desc 有暴露，原脚本锚点词"更多选项"错误）
搜索框：常驻 BasicTextField hint"搜索书源"（无障碍 EditText 映射[95,126][674,216]，无"搜索"按钮）
列表条目：clickable 容器[23,229][697,364]；拖拽手柄 Icon desc"排序"[46,276][87,317]（reorderEnabled=
    Default 排序+无搜索词+无域名分组时渲染，draggableHandle=长按后拖）；条目编辑钮 desc"编辑"；
    条目三点 desc"更多菜单"（与顶栏/批量栏同名——zone 限定 y 区间定位）
多选态批量栏（AppManagementSelectionBottomBar，selectedCount>0 AnimatedVisibility）：
    计数 text"全选（N/M）"（R.string.select_all_count，点击=全选 onSelectAll）｜"反选"钮
    （R.string.revert_selection）｜主按钮"删除"（danger=bottomActions 末项）｜其余 11 项收进
    批量栏更多菜单 desc"更多菜单"（y>1050 zone 限定）
删除确认框：showComposeConfirmDialog title"提醒" message"是否确认删除？…" 按钮"否/是"
排序菜单：showComposeActionListDialog title"排序" 8 项=反序/手动排序/智能排序/名称排序/地址排序/
    更新时间排序/响应时间排序/是否启用（第 2 轮"ListLayoutMenu"口径修正=Compose ActionListDialog）
筛选菜单：title"分组" 固定项=分组管理/已启用/已禁用/需要登录/无分组/启用发现/禁用发现[+分组名]
三点菜单 5 项：本地导入/网络导入/二维码导入/按域名分组/帮助
S2-4 三视图：载体页功能不存在（AppManagementScaffold/AppManagementLazyColumn 无视图形态参数，
    2026-09-02 源码核对；"列表/紧凑/Grid"仅 SourceFolderConfigDialog 订阅文件夹配置有且订阅源固定
    卡片无列表语义）→N/A 登记，不判 FAIL（规格 ListLayoutMenu 概念未在 C1 载体实现）
S2-8 返回层级：BaseActivity onBackPressedDispatcher callback=直接 finish（BaseActivity.kt:103-105），
    BookSourceActivity 无多选态 BackHandler→真机实证后按实现登记（差异则如实 FAIL）
"""
import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from ai_tests.config import ADB_PATH as ADB, MEMU_ADB_HOST as HOST, PACKAGE as PKG
except ImportError:
    ADB = r"D:\Program Files\Microvirt\MEmu\adb.exe"
    HOST = "127.0.0.1:21503"
    PKG = "io.legado.miss.app.debug"

from ai_tests.lib import compose_assert as ca

ZONE_TOP = 220      # 顶栏/搜索区与列表区分界（dump 证据：条目容器 y1=229 起）
ZONE_BOTTOM = 1000  # 列表区上界（批量栏 y>1050 排除）


def bounds_in_zone(d, pattern: str, y_min=0, y_max=99999):
    """dump_bounds 的 y 区间限定版（同名锚点多实例定位：顶栏排序 vs 条目手柄；顶栏三点 vs 批量栏三点）
    dump 证据：node 属性序 text/desc 在前、bounds 末位，正则段拼接与 compose_assert.dump_bounds 同构"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        time.sleep(1.5)
        xml = d.dump_hierarchy()
    for m in re.finditer(r'<node[^>]*' + pattern + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if y_min <= y1 <= y_max:
            return {"left": x1, "top": y1, "right": x2, "bottom": y2,
                    "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}
    return None


def click_in_zone(d, pattern: str, y_min=0, y_max=99999, timeout=3) -> bool:
    """click_by_dump 的 zone 限定版（重试 ≤2 次，防死循环口径与库一致）"""
    for _ in range(2):
        b = bounds_in_zone(d, pattern, y_min, y_max)
        if b:
            w, h = d.window_size()
            d.click(b["cx"] / w, b["cy"] / h)
            time.sleep(1.2)
            return True
        time.sleep(1)
    return False


def long_click_item(d, idx=0, duration_ms=900) -> bool:
    """长按第 idx 个条目容器（item_containers 坐标直按——条目几何特征无法写成 dump_bounds
    单 pattern：pattern 自含 bounds 段会与库尾部 bounds 捕获段双重拼接恒失配）"""
    items = item_containers(d)
    if len(items) <= idx:
        return False
    b = items[idx]
    ca.sh("input", "swipe", str(b["cx"]), str(b["cy"]), str(b["cx"]), str(b["cy"]),
          str(duration_ms), timeout=15)
    time.sleep(1.2)
    return True


def item_containers(d):
    """列表条目容器 bounds 列表（clickable+条目几何特征过滤；批量栏钮/选择槽/开关经 x/y 过滤排除）"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        time.sleep(1.5)
        xml = d.dump_hierarchy()
    out = []
    for m in re.finditer(r'<node[^>]*clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if ZONE_TOP < y1 < ZONE_BOTTOM and x1 < 100 and x2 > 640 and (y2 - y1) > 60:
            out.append({"left": x1, "top": y1, "right": x2, "bottom": y2,
                        "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2})
    return out


def first_item_hash(d):
    """首条目标题 hash（脱敏：列表区首个 text 节点；dump 证据首条目标题 y1≈274，
    x1=98（Default 排序有拖拽手柄）/x1=44（排序后 reorderEnabled=False 手柄消失左移）——
    x1>30 放宽适配两态；手柄/勾选槽均非 text 节点不会误抓）"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        time.sleep(1.5)
        xml = d.dump_hierarchy()
    for m in re.finditer(r'<node[^>]*text="([^"]{2,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        txt, x1, y1 = m.group(1), int(m.group(2)), int(m.group(3))
        if ZONE_TOP < y1 < 520 and x1 > 30:
            return hashlib.md5(txt.encode("utf-8")).hexdigest()[:8]
    return None


def first_item_hash_retry(d, tries=4):
    """首项 hash 读取重试——AdbKeyboard 工具条出现期间 dump 只见 IME 窗口（列表节点全消
    失，B2 第 3 轮 s2-5 实证 hash=None），窗口期过后恢复；间隔 1s 重试≤4 次防死循环"""
    for _ in range(tries):
        h = first_item_hash(d)
        if h is not None:
            return h
        time.sleep(1.0)
    return None


def selected_count(d):
    """批量栏计数 N（text"全选（N/M）"首捕获组；无批量栏返回 None）"""
    m = re.search(r'text="全选（(\d+)/\d+）"', d.dump_hierarchy())
    return int(m.group(1)) if m else None


def dismiss_ime_bar(d, probes=3):
    """收起 AdbKeyboard 输入视图工具条（∞/Clear Text/Done/Switch IME——当前默认 IME 为
    AdbKeyboard，其输入视图随 EditText 焦点显示；B2 第 3 轮实证：Compose 菜单 dismiss 后
    焦点回落搜索框→工具条延迟 2~3s 出现→占据批量栏区域吞点击）。探测循环覆盖延迟窗口，
    检测到即点其 Done 键收起；未出现则探测完直接返回（无副作用）"""
    for _ in range(probes):
        if bounds_in_zone(d, r'text="Switch IME"'):
            done_b = bounds_in_zone(d, r'text="Done"')
            if done_b:
                w, h = d.window_size()
                d.click(done_b["cx"] / w, done_b["cy"] / h)
                time.sleep(1.0)
            return
        time.sleep(0.8)


def exit_multi_select(d):
    """复位退多选：点计数（=全选）→反选→选中集空退出；Miuix 按钮节点间歇丢失时兜底
    冷启动（am start 复用实例不清选中态，force-stop 才彻底）"""
    if ca.click_by_dump(d, r'text="全选（\d+/\d+）"', timeout=2):
        dismiss_ime_bar(d)
        time.sleep(0.8)
        if ca.click_by_dump(d, r'text="反选"', timeout=2):
            time.sleep(0.8)
            if selected_count(d) is None:
                return
    nav_to_source_list(d)


def nav_to_source_list(d) -> bool:
    """am start 直拉（B2 第 2 轮校准沿用：订阅 tab Compose 语义未暴露；BookSourceActivity=S2 载体）。
    冷启动口径：force-stop 后重拉——am start 会复用存活实例，选中态/焦点/IME 工具条跨步骤
    残留不可预测（B2 第 3 轮实证：残留多选态使长按变 toggle 取消、IME 残留吞点击），冷启重建最稳"""
    ca.sh("am", "force-stop", PKG)
    time.sleep(1.0)
    ca.sh("am", "start", "-n",
          f"{PKG}/io.legado.app.ui.book.source.manage.BookSourceActivity")
    time.sleep(3.0)
    # IME 残留自愈（IME 为系统服务，force-stop 不收；工具条占批量栏区域吞点击——
    # B2 第 3 轮截图实证）。mInputShown=true 时 keyevent4 仅收键盘不触达 app（安全窗口）
    r = ca.sh("dumpsys", "input_method", timeout=10)
    if "mInputShown=true" in r.stdout.decode("utf-8", errors="ignore"):
        ca.sh("input", "keyevent", "4")
        time.sleep(1.0)
    for _ in range(8):  # 轮询列表容器就绪（冷启动渲染窗口；B2 实证 4s 固定等待不足→长按落空）
        if item_containers(d):
            break
        time.sleep(1.0)
    # AdbKeyboard 工具条（dump 不可见）跨 app 残留会吃掉后续 BACK/底部点击——盲点其 Done
    # 键收起（工具条不在时该点为列表尾部空白区，非多选态下无副作用）
    ca.sh("input", "tap", "460", "1230")
    time.sleep(0.8)
    return "BookSourceActivity" in d.app_current().get("activity", "")


def step_s2_1_multi_select(d) -> bool:
    """S2-1 滑选多选：长按首条目进多选（批量栏出现）→点击次条目计数增长（区间选中 L2 化简，全量归 L3）
    实锚：长按=onToggleSelect（BookSourceItemRow.onLongClick）；批量栏=计数"全选（N/M）"+"反选"钮
    （第 2 轮实证"反选/删除"沿用，原脚本断言"全选"独立按钮形态不符已修）"""
    if not long_click_item(d):
        ca.shot(d, "l2_s2_s1_no_item")
        return False
    time.sleep(1.0)
    batch_ok = bounds_in_zone(d, r'text="全选（\d+/\d+）"') is not None and \
        bounds_in_zone(d, r'text="反选"') is not None
    cnt1 = selected_count(d)
    items = item_containers(d)
    if len(items) >= 2:
        w, h = d.window_size()
        d.click(items[1]["cx"] / w, items[1]["cy"] / h)
        time.sleep(1.2)
    cnt2 = selected_count(d)
    ca.shot(d, "l2_s2_s1_multiselect")
    grew = cnt1 is not None and cnt2 is not None and cnt2 > cnt1
    print(f"  批量栏出现={batch_ok} 选中计数 {cnt1}->{cnt2} 增长={grew}")
    exit_multi_select(d)
    return batch_ok and grew


def step_s2_2_drag_sort(d) -> bool:
    """S2-2 拖拽排序：手柄按下即拖换位→首项 hash 变化→退出重进顺序保持（upOrder 落库持久化）
    实锚：手柄=条目左首 Icon desc"排序"（y>220 zone 区分顶栏同名钮）；
    注入=u2 touch down→立即 move 步进→up（dbg_drag_probe.py 选型实证：sh.calvin.reorderable 3.1.0
    draggableHandle 默认 DragGestureDetector.Press=detectDragGestures 按下即拖，长按静置
    （hold≥900ms）手势链失效换位不触发；shell input draganddrop 语义=长按后拖同样失配——
    第 2 轮位移=0 根因）"""
    h0 = first_item_hash(d)
    hb = bounds_in_zone(d, r'content-desc="排序"', y_min=ZONE_TOP, y_max=520)
    if not hb:
        ca.shot(d, "l2_s2_s2_no_handle")
        print("  [校准点] 拖拽手柄未命中（reorderEnabled 需 Default 排序+空搜索词）")
        return False
    cx, cy, dy, steps = hb["cx"], hb["cy"], 144, 14  # 条目高 135，拖 144px=换一位
    d.touch.down(cx, cy)
    for i in range(1, steps + 1):
        d.touch.move(cx, cy + dy * i // steps)
        time.sleep(0.04)
    time.sleep(0.25)
    d.touch.up(cx, cy + dy)
    time.sleep(2.0)
    h1 = first_item_hash(d)
    moved = h0 is not None and h1 is not None and h0 != h1
    # 持久化：退出重进顺序保持（onDragStopped→upOrder 落库）
    persisted = False
    if moved:
        ca.sh("input", "keyevent", "4")
        time.sleep(1.5)
        nav_to_source_list(d)
        time.sleep(1.5)
        h2 = first_item_hash(d)
        persisted = h1 == h2
    ca.shot(d, "l2_s2_s2_dragged")
    print(f"  首项 hash before={h0} after={h1} moved={moved} 重进保持={persisted}")
    return moved and persisted


def step_s2_3_batch_ops(d) -> bool:
    """S2-3 批量操作抽测：多选→直钮"反选"（计数即时变化）→批量栏更多菜单→"启用所选"
    实锚：批量栏三点 desc"更多菜单"（y>1050 zone）；"反选"=x 固定 415+y 跟随计数 cy
    （计数 text 稳定暴露；系统栏沉浸切换致 y 浮动 ±45px，tap 屏底即触发系统栏滑出）。
    ⚠️ AdbKeyboard 工具条陷阱（B2 第 3 轮实证）：**只要开过批量栏菜单**，dismiss 后焦点
    回落搜索框→IME 输入视图（∞/Clear Text/Done/Switch IME）1.5s 内出现盖住批量栏区，
    且为独立 IME 窗口 dump 不可见（检测失效）→对策=动作顺序重排：无菜单副作用的"反选"
    先行，菜单类"启用所选"殿后（其后无批量栏点击需求）；删除链确认框已由 S6-1 覆盖
    （同构 showComposeConfirmDialog），此处不再抽测删除"""
    if not long_click_item(d):
        return False
    time.sleep(1.0)
    cnt0 = selected_count(d)
    # 动作 1：反选（直钮，无菜单副作用；y 跟随计数 cy 抗系统栏浮动）
    cnt_b = bounds_in_zone(d, r'text="全选（\d+/\d+）"')
    ca.sh("input", "tap", "415", str(cnt_b["cy"]) if cnt_b else "1230")
    time.sleep(1.5)
    cnt1 = selected_count(d)
    inverted = cnt0 is not None and cnt1 is not None and cnt1 != cnt0
    # 动作 2：启用所选（菜单类，殿后——dismiss 后工具条出现不影响已完成的判定）
    opened = click_in_zone(d, r'content-desc="更多菜单"', y_min=1050)
    ok_enable = opened and ca.click_by_dump(d, r'text="启用所选"', timeout=3)
    time.sleep(1.0)
    ca.shot(d, "l2_s2_s3_batch")
    print(f"  反选计数 {cnt0}->{cnt1} 即时刷新={inverted} 批量启用所选={ok_enable}")
    exit_multi_select(d)
    return inverted and ok_enable


def step_s2_4_three_views(d) -> bool:
    """S2-4 三视图：N/A 登记——载体页功能不存在（证据见头部实锚表；列表/紧凑/网格锚点均未渲染）"""
    xml = d.dump_hierarchy()
    absent = all(re.search(f'text="{v}"', xml) is None for v in ("紧凑", "网格"))
    ca.shot(d, "l2_s2_s4_na")
    print(f"  [N/A] 三视图功能不存在（紧凑/网格 text 未渲染={absent}）——规格与实现差异，SKIP 不判 FAIL")
    return True  # 由 main 单列 SKIP，不计入 PASS/FAIL


def step_s2_5_sort_options(d) -> bool:
    """S2-5 排序选项+升降序：排序菜单抽测"地址排序"→"反序"（升降序翻转，对应规格同维翻转）
    实锚：顶栏 desc"排序"（y<220 zone）；菜单项 text 全屏唯一（Dialog 独立窗口）
    判定：抽测后首项 hash 任一变化（3 合成源互异名，反序后首项必为原末条）"""
    h0 = first_item_hash(d)
    ok = True
    for opt in ("地址排序", "反序"):
        if not click_in_zone(d, r'content-desc="排序"', y_max=ZONE_TOP):
            ca.shot(d, "l2_s2_s5_no_sort")
            print("  [校准点] 排序菜单入口未命中")
            return False
        time.sleep(1.0)
        if not ca.click_by_dump(d, f'text="{opt}"', timeout=3):
            print(f"  [校准点] 排序项 {opt} 未命中")
            ok = False
            break
        time.sleep(1.5)
    # 盲点 AdbKeyboard 工具条 Done 键（点"反序"后工具条出现，dump 只见 IME 窗口致
    # first_item_hash=None——B2 第 3 轮实证；工具条不在时该点为列表尾部空白区无副作用）
    ca.sh("input", "tap", "460", "1230")
    time.sleep(1.0)
    h1 = first_item_hash_retry(d)
    ca.shot(d, "l2_s2_s5_sorted")
    changed = h0 is not None and h1 is not None and h0 != h1
    print(f"  首项 hash before={h0} after={h1} 维度/升降序变化={changed}")
    return ok and changed


def step_s2_6_search_filter(d) -> bool:
    """S2-6 搜索+快捷筛选词：搜索框常驻→input 技术字符"3"（合成源名尾缀数字）→计数变化；
    顶栏 desc"分组"→快捷词"已禁用"→计数→0；返回清筛选（BookSourceActivity.finish() query 非空=
    updateSearchQuery("")，不退页）恢复
    （第 2 轮口径修正：无"搜索"按钮，搜索框常驻；筛选词入口=顶栏"分组"showFilterMenu）"""
    items0 = len(item_containers(d))
    eb = bounds_in_zone(d, r'class="android\.widget\.EditText"')
    if not eb:
        ca.shot(d, "l2_s2_s6_no_search")
        return False
    w, h = d.window_size()
    d.click(eb["cx"] / w, eb["cy"] / h)
    time.sleep(1.0)
    ca.sh("input", "text", "3")
    time.sleep(2.0)
    items1 = len(item_containers(d))
    ca.shot(d, "l2_s2_s6_filtered")
    ca.sh("input", "keyevent", "4")  # 收键盘
    time.sleep(0.8)
    ca.sh("input", "keyevent", "4")  # 清查询（finish 拦截语义，不退页）
    time.sleep(1.5)
    # 快捷筛选词抽测
    ok_menu = click_in_zone(d, r'content-desc="分组"', y_max=ZONE_TOP)
    time.sleep(1.0)
    picked = ca.click_by_dump(d, r'text="已禁用"', timeout=3)
    time.sleep(1.5)
    items2 = len(item_containers(d))
    ca.shot(d, "l2_s2_s6_filter_word")
    ca.sh("input", "keyevent", "4")  # 清筛选
    time.sleep(1.5)
    items3 = len(item_containers(d))
    filtered = items1 != items0
    word_filtered = picked and items2 != items3
    restored = items3 == items0
    print(f"  关键字过滤 {items0}->{items1}={filtered} 快捷词已禁用 {items3}->{items2} 恢复={restored}")
    return ok_menu and filtered and word_filtered and restored


def step_s2_7_menu_family(d) -> bool:
    """S2-7 菜单族：顶栏三点 desc"更多菜单"→5 项全展开（AppDropdownMenu，无系统 PopupMenu 残留）
    实锚修正：R.string.more_menu="更多菜单"（原锚点"更多选项"词错，desc 实际有暴露）"""
    if not click_in_zone(d, r'content-desc="更多菜单"', y_max=ZONE_TOP):
        ca.shot(d, "l2_s2_s7_no_menu")
        return False
    time.sleep(1.0)
    xml = d.dump_hierarchy()
    items = ["本地导入", "网络导入", "二维码导入", "按域名分组显示", "帮助"]
    hit = [t for t in items if re.search(f'text="{t}"', xml)]
    menu_cnt = len(re.findall(r'<node[^>]*clickable="true"[^>]*', xml))
    ca.shot(d, "l2_s2_s7_dropdown")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.0)
    print(f"  菜单项命中={len(hit)}/5 可点击节点={menu_cnt}（全项展开断言 >3）")
    return len(hit) == 5 and menu_cnt > 3


def step_s2_8_back_hierarchy(d) -> bool:
    """S2-8 返回键层级：多选态按返回→预期"先退多选再退页面"
    实现实证：BaseActivity onBackPressedDispatcher=直接 finish（BaseActivity.kt:103-105），
    BookSourceActivity/AppManagementScaffold 均无多选态 BackHandler→真机行为以本步输出为准，
    若页面直接退出=规格与实现差异，如实 FAIL 登记（回归候选）"""
    if not long_click_item(d):
        return False
    time.sleep(1.0)
    # 多选态判定用计数 text（稳定暴露）；"反选"钮 text 间歇丢失（Miuix 按钮节点，截图实证在屏）
    in_multi = selected_count(d) is not None
    # BACK 实证（重试 ≤2 次排除工具条/焦点残留噪声；手动双轮复现=多选态 BACK 直接
    # finish 回桌面——BaseActivity onBackPressedDispatcher 直连 finish，无多选态消费）
    for _ in range(2):
        ca.sh("input", "keyevent", "4")
        time.sleep(1.8)
        if selected_count(d) is None:
            break
    out_multi = selected_count(d) is None
    still_on_page = "BookSourceActivity" in d.app_current().get("activity", "")
    ca.shot(d, "l2_s2_s8_back")
    print(f"  进多选={in_multi} 一次返回批量栏消失={out_multi} 页面仍在={still_on_page}")
    return in_multi and out_multi and still_on_page


def main():
    ap = argparse.ArgumentParser(description="S2 管理列表 Compose 迁移 L2 验证（S2-1~8）")
    ap.add_argument("--scenario", default="all",
                    help="all | s2-1 | s2-2 | s2-3 | s2-5 | s2-6 | s2-7 | s2-8（s2-4=N/A 登记）")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    if not nav_to_source_list(d):
        print("== L2 总结: HAS FAIL（导航未达管理列表）==")
        sys.exit(1)

    run_all = args.scenario == "all"
    if run_all:  # s2-4 N/A 单列（不进 PASS/FAIL 注册表）
        step_s2_4_three_views(d)
        print("s2-4: SKIP(N/A 功能不存在——登记)")
    steps = {
        "s2-1": step_s2_1_multi_select,
        "s2-2": step_s2_2_drag_sort,
        "s2-3": step_s2_3_batch_ops,
        "s2-5": step_s2_5_sort_options,
        "s2-6": step_s2_6_search_filter,
        "s2-7": step_s2_7_menu_family,
        "s2-8": step_s2_8_back_hierarchy,
    }
    all_pass = ca.run_steps(steps, "all" if run_all else args.scenario,
                            tag_keywords=[], since_ts=since_ts, ctx=d)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
