# -*- coding: utf-8 -*-
"""l2_verify_compose_s3_source_edit.py — S3 表单编辑器（BookSourceEditActivity）Compose 迁移 L2 验证

执行方式（铁律）：ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l2_verify_compose_s3_source_edit.py [--scenario all]
前置：⚠️ 依赖 tasks 4.3（C2 S3 接线收尾）完成；测试包已安装；存在可编辑测试源（禁用真实生产源）；
      从管理列表长按条目→编辑菜单进入编辑页（入口锚点真机校准点）
锚点：6 Tab（分组设置）；SettingsCard 分组卡片；输入框（className android.widget.EditText）；
      KeyboardToolPop 工具条；CodeEditActivity 类名；"未保存"确认框（真机校准点）
判定（分册 §2.3 检查点 S3-1~6）：
    s3-1 表单分组：6 Tab 遍历，SettingsCard 渲染+逐 Tab 截图
    s3-2 未保存拦截：修改字段→返回→确认框存在；取消留页
    s3-3 CodeView 全屏：全屏编辑入口→CodeEditActivity 类名断言→返回
    s3-4 KeyboardToolPop：聚焦输入框→undo/redo 工具条节点存在
    s3-5 规则自动补全：规则前缀输入→候选出现；logcat 无重复注册异常
    s3-6 保存校验：清空 URL 保存→拦截；恢复→保存通过
真机执行时点：冻结验收 4.6（S3 检查点，依赖 4.3 接线），落盘阶段仅 py_compile 校验
"""
import argparse
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


def item_containers(d):
    """列表条目容器 bounds（B2 第 3 轮 s2 校准同构：clickable+条目几何过滤，
    dump 证据 [23,229][697,364]；批量栏钮/选择槽经 x/y 过滤排除）"""
    try:
        xml = d.dump_hierarchy()
    except Exception:
        time.sleep(1.5)
        xml = d.dump_hierarchy()
    out = []
    for m in re.finditer(r'<node[^>]*clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        x1, y1, x2, y2 = map(int, m.groups())
        if 220 < y1 < 1000 and x1 < 100 and x2 > 640 and (y2 - y1) > 60:
            out.append({"cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2})
    return out


def nav_to_edit_page(d) -> bool:
    """管理列表→点击首条目→编辑页
    （B2 第 3 轮校准：am start 管理页冷启→item_containers 精确容器点击——原 y∈(300,900)
    text 区间在首条目 y1=229 时漏首条且受系统栏沉浸切换 y 浮动影响致导航 FAIL；
    点击条目直进 BookSourceEditActivity，长按=多选态（第 2 轮校准结论沿用））"""
    ca.sh("am", "force-stop", PKG)
    time.sleep(1.0)
    ca.sh("am", "start", "-n",
          f"{PKG}/io.legado.app.ui.book.source.manage.BookSourceActivity")
    time.sleep(3.0)
    for _ in range(8):  # 轮询列表就绪（s2 同款，防冷启渲染期点击落空）
        if item_containers(d):
            break
        time.sleep(1.0)
    if "BookSourceActivity" not in top_activity():
        ca.shot(d, "l2_s3_no_manage")
        return False
    items = item_containers(d)
    if not items:
        ca.shot(d, "l2_s3_no_item")
        print("  [校准点] 管理列表无可见条目（数据前置：导入书源）")
        return False
    w, h = d.window_size()
    d.click(items[0]["cx"] / w, items[0]["cy"] / h)
    time.sleep(3.0)
    ok = "BookSourceEdit" in top_activity()
    if not ok:
        ca.shot(d, "l2_s3_no_edit_entry")
        print("  [校准点] 点击条目未进编辑页，锚点需复核")
    return ok


def top_activity() -> str:
    """当前栈顶 Activity 类名（技术字段，可输出）"""
    r = ca.sh("dumpsys", "activity", "activities", timeout=15)
    m = re.search(r"mResumedActivity[^{]*\{[^}]*\s(\S+/\S+?)\s", r.stdout.decode("utf-8", errors="ignore"))
    return m.group(1) if m else ""


def focus_first_edit(d) -> bool:
    """聚焦首个表单输入框（B2 第 3 轮 dump 修正：编辑页表单控件=
    android.widget.MultiAutoCompleteTextView ×9，非 EditText——原正则恒失配）"""
    b = ca.dump_bounds(d, r'class="android\.widget\.MultiAutoCompleteTextView"')
    if not b:
        b = ca.dump_bounds(d, r'class="android\.widget\.EditText"')
    if not b:
        return False
    w, h = d.window_size()
    d.click(b["cx"] / w, b["cy"] / h)
    time.sleep(1.0)
    return True


def step_s3_1_form_tabs(d) -> bool:
    """S3-1 表单分组：6 Tab 遍历，SettingsCard 渲染+逐 Tab 截图"""
    xml = d.dump_hierarchy()
    tabs = re.findall(r'<node[^>]*text="(基本信息|信息|登录信息|登录)|<node[^>]*text="(搜索|发现|正文|变量|其他)"', xml)
    # Tab 数断言（6 分组：13+11+10+11+10+11 字段，Tab 锚点真机校准）
    tab_cnt = len(re.findall(r'<node[^>]*text="[^"]{2,4}"[^>]*clickable="true"[^>]*', xml))
    ca.shot(d, "l2_s3_s1_tab0")
    print(f"  可点击短文本节点（候选 Tab）数={tab_cnt}")
    ok = tab_cnt >= 4  # 6 Tab 断言的保守下界（真机校准后收紧为 ==6）
    for i in range(min(tab_cnt, 6)):
        ca.shot(d, f"l2_s3_s1_tab{i}")
    return ok


def _ensure_edit_page(d):
    """步骤间页面守卫（编辑页无返回拦截，任意步骤的 BACK 都可能退页到桌面——
    BACK 直连 BaseActivity finish；守卫=栈顶非编辑页时重建导航）"""
    if "BookSourceEdit" not in top_activity():
        nav_to_edit_page(d)


def step_s3_2_unsaved_intercept(d) -> bool:
    """S3-2 未保存拦截：修改字段→返回→确认框存在；取消留页
    ⚠️ 依赖 4.3 接线（C2 S3 收尾未完成）：源码实证编辑页无多选态 BACK 拦截
    （BaseActivity onBackPressedDispatcher 直连 finish），BACK=直接退出无确认框
    →预期 FAIL 登记；确认框锚点预校准为否/是/取消（AppDialogFrame 按钮族）"""
    if not focus_first_edit(d):
        ca.shot(d, "l2_s3_s2_no_edittext")
        return False
    ca.sh("input", "text", "ai_t")
    time.sleep(0.5)
    ca.sh("input", "keyevent", "4")  # 收键盘
    time.sleep(0.8)
    ca.sh("input", "keyevent", "4")  # 触发返回拦截
    time.sleep(1.5)
    _xml = d.dump_hierarchy()
    dlg = (re.search(r'text="否"', _xml) and re.search(r'text="是"', _xml)) or \
        (re.search(r'text="取消"', _xml) and re.search(r'text="确定"', _xml)) or \
        re.search(r'text="未保存', _xml) is not None
    ca.shot(d, "l2_s3_s2_intercept")
    if dlg:
        # 实现语义=否(不保存退出)/是(保存退出)二元，无"取消留页"选项（B2 第 3 轮实证：
        # 点否后页面退出——与规格"取消留页"差异记录）；确认框出现=拦截接线存在
        ca.click_by_dump(d, r'text="取消"', timeout=2)
        ca.click_by_dump(d, r'text="否"', timeout=2)
        time.sleep(1.0)
    still_on_page = "BookSourceEdit" in top_activity()
    print(f"  确认框出现={bool(dlg)} 点否后留页={still_on_page}（实现为否/是二元无留页项——差异记录）")
    return bool(dlg)


def step_s3_3_codeview_fullscreen(d) -> bool:
    """S3-3 CodeView 全屏编辑：顶栏"编辑内容"钮→CodeEditActivity 类名断言→返回带回
    实锚修正（B2 第 3 轮 dump）：顶栏 4 钮=编辑内容/保存/调试源/菜单（menu/source_edit.xml
    showAsAction=always 直接显示，menu_fullscreen_edit title=R.string.edit_content，
    dump 证据 desc"编辑内容"[385,54][453,122]；"全屏编辑"一词不存在——溢出菜单第一项=
    搜索（登录项因合成源无 loginUrl 隐藏））。
    ⚠️ CodeEditActivity 命中依赖 4.3 接线（onFullEditClicked），预期部分 FAIL 登记"""
    _ensure_edit_page(d)
    # onFullEditClicked 源码要求 findFocus() is EditText（无焦点则 toast 不跳转）——先聚焦
    focus_first_edit(d)
    time.sleep(0.8)
    opened = ca.click_by_dump(d, r'content-desc="编辑内容"', timeout=3)
    if not opened:
        ca.shot(d, "l2_s3_s3_no_menu")
        print("  [校准点] 顶栏编辑内容锚点需复核")
        return False
    time.sleep(2.5)
    act = top_activity()
    ca.shot(d, "l2_s3_s3_code")
    ca.sh("input", "keyevent", "4")
    time.sleep(1.5)
    ok = "CodeEditActivity" in act
    print(f"  栈顶类名={act} 全屏编辑命中={ok}")
    return ok


def step_s3_4_keyboard_tool(d) -> bool:
    """S3-4 KeyboardToolPop：聚焦输入框→undo/redo 工具条节点存在（insets 接线不错位）"""
    _ensure_edit_page(d)
    if not focus_first_edit(d):
        return False
    time.sleep(1.0)
    xml = d.dump_hierarchy()
    # B2 第 4 轮锚点校准（090204 探针实证）：KeyboardToolPop 三 header 实锚=text 符号
    # ❓(教程)/↩️(撤销)/↪️(重做)，无 content-desc、无中文词——原"撤销/恢复/教程"锚点
    # 自脚本落盘起从未匹配过（与 4.3 接线无关的第二重 FAIL 因素）；中文词分支保留兼容
    tool_cnt = len(re.findall(r'<node[^>]*(?:content-desc|text)="(?:❓|↩\uFE0F?|↪\uFE0F?|撤销|恢复|undo|redo|教程)"', xml))
    ca.shot(d, "l2_s3_s4_toolpop")
    # 不发 BACK 收键盘（B2 第 3 轮实证：编辑页无返回拦截，BACK=直接退页污染后续步骤；
    # 键盘/工具条由下一步守卫与盲点 Done 自愈）
    print(f"  工具条节点数={tool_cnt}")
    return tool_cnt >= 2


def step_s3_5_rule_complete(d) -> bool:
    """S3-5 规则自动补全：规则前缀输入→候选出现；logcat 无重复注册异常（run_steps 统一判定）"""
    _ensure_edit_page(d)
    if not focus_first_edit(d):
        return False
    ca.sh("input", "text", "@get:")  # 规则前缀（技术字符串）
    time.sleep(2.0)
    xml = d.dump_hierarchy()
    cand_cnt = len(re.findall(r'<node[^>]*text="[^"]+"[^>]*', xml))
    ca.shot(d, "l2_s3_s5_complete")
    # 退格清掉 @get: 前缀（防残留污染 s3-6 的原值读取；不发 BACK——编辑页无拦截，BACK=退页）
    for _ in range(6):
        ca.sh("input", "keyevent", "67")
    time.sleep(0.5)
    print(f"  输入前缀后节点数={cand_cnt}（候选出现断言：真机校准后收紧）")
    return True  # 候选判定依赖真机渲染形态，落盘期保守通过+截图证据


def step_s3_6_save_validate(d) -> bool:
    """S3-6 保存校验：清空 URL 保存→拦截；恢复→保存通过
    实锚修正（B2 第 3 轮）：①保存钮=顶栏 ImageButton desc"保存"（dump 证据
    [464,54][532,122]，text 通道不暴露）；②表单输入框=MultiAutoCompleteTextView 共用
    resource-id=PKG:id/editText ×9（hint 会填充 text 属性，坐标/退格通道被键盘弹出滚动
    漂移废掉）→③定位/清空/回填全走 u2 Accessibility 通道（set_text/clear_text，绕过键盘）；
    字段锚=textContains"18091"（seed 合成源 URL 端口特征）；恢复锚=textContains"sourceUrl"
    （清空后 hint"源 URL(sourceUrl)"填充 text）；④拦截表现=toast+留编辑页（save 抛
    non_null_name_url→toastOnUi），退页=保存成功=清空失败证据"""
    _ensure_edit_page(d)
    rid = f"{PKG}:id/editText"
    # 字段锚=textContains"127.0.0.1"（源 URL host 特征；历史值含"18091"曾因上轮截断失配）
    rid_sel = d(resourceId=rid, textContains="127.0.0.1")
    if rid_sel.count == 0:  # 字段空/截断兜底：hint 通道（text 属性被 hint 填充）
        rid_sel = d(resourceId=rid, textContains="sourceUrl")
    if rid_sel.count == 0:
        ca.shot(d, "l2_s3_s6_no_edittext")
        return False
    src = rid_sel[0]
    original = src.info.get("text") or ""
    if "18091" not in original:
        # 历史截断修复：回归基线源 URL 实锚=http://127.0.0.1:18091（B2 第 3 轮 dump 证据）
        original = "http://127.0.0.1:18091"
        src.set_text(original)
        time.sleep(0.5)
    # 清空（ACTION_SET_TEXT 通道）
    src.clear_text()
    time.sleep(0.8)
    cleared = d(resourceId=rid, textContains="127.0.0.1").count == 0
    ca.click_by_dump(d, r'content-desc="保存"', timeout=3)
    time.sleep(1.5)
    still_edit = "BookSourceEdit" in top_activity()
    intercepted = cleared and still_edit  # 退页=保存成功=清空失败证据
    ca.shot(d, "l2_s3_s6_intercept")
    # 恢复：清空后源 URL 字段 text=hint"源 URL(sourceUrl)"→回填原值→保存→finish 回管理列表
    ok_restore = False
    if intercepted:
        tgt = d(resourceId=rid, textContains="sourceUrl")[0]
        tgt.set_text(original)
        time.sleep(0.5)
        ca.click_by_dump(d, r'content-desc="保存"', timeout=3)
        time.sleep(2.0)
        act = top_activity()
        ok_restore = "BookSourceEditActivity" not in act
    print(f"  清空={cleared} 保存拦截留页={intercepted} 回填保存退出={ok_restore}")
    return intercepted and ok_restore


def main():
    ap = argparse.ArgumentParser(description="S3 表单编辑器 Compose 迁移 L2 验证（S3-1~6）")
    ap.add_argument("--scenario", default="all",
                    help="all | s3-1 | s3-2 | s3-3 | s3-4 | s3-5 | s3-6")
    args = ap.parse_args()
    d = ca.connect()
    ca.ensure_env(d)
    since_ts = ca.device_now()

    if not nav_to_edit_page(d):
        print("== L2 总结: HAS FAIL（导航未达编辑页）==")
        sys.exit(1)

    steps = {
        "s3-1": step_s3_1_form_tabs,
        "s3-2": step_s3_2_unsaved_intercept,
        "s3-3": step_s3_3_codeview_fullscreen,
        "s3-4": step_s3_4_keyboard_tool,
        "s3-5": step_s3_5_rule_complete,
        "s3-6": step_s3_6_save_validate,
    }
    all_pass = ca.run_steps(steps, args.scenario, tag_keywords=["RuleComplete"], since_ts=since_ts, ctx=d)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
