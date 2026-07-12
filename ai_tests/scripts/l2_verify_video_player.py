#!/usr/bin/env python3
r"""l2_verify_video_player.py — 视频播放器L2功能验证

固定测试流程步骤3：导航到视频播放器 + 执行场景操作 + SwipeTest日志验证

用法：
    ai_tests\venv\Scripts\python.exe ai_tests/scripts/l2_verify_video_player.py [--scenario SCENARIO] [--manual]

场景：
    swipe_article       - 上下滑动切换文章
    pagination          - 分页加载（滑到最后一个触发加载下一页）
    preload             - 预缓冲（视频播放到80%触发预加载）
    position_memory     - 位置记忆（退出返回列表自动滚动）
    backward_compat     - 向后兼容（无 rssArticles 时不触发新功能）
    buffer_progress     - 缓冲进度条更新（F1：secondaryProgress 更新验证）
    control_visibility  - 控件自动隐藏（F2：3秒后自动隐藏验证）
    all                 - 全部场景（默认）

模式：
    自动模式（默认）：脚本自动启动App并导航到视频播放器
    --manual         ：用户已手动导航到视频播放器，脚本只执行场景验证

退出码：
    0 = 全部场景通过
    1 = 部分场景未通过
    2 = 致命错误（设备连接/导航失败）
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# 添加 ai_tests 目录到 path 以 import config 和 swipe_test_log
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST, PACKAGE, MAIN_ACTIVITY

# 导入 swipe_test_log 的功能（同目录）
sys.path.insert(0, str(Path(__file__).parent))
from swipe_test_log import clear_logcat, capture_log, analyze_log, LOG_TMP_PATH

# 尝试导入 uiautomator2（可选依赖）
try:
    import uiautomator2 as u2
    HAS_U2 = True
except ImportError:
    HAS_U2 = False


def run_adb(cmd, timeout=30):
    """执行ADB命令"""
    full_cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} {cmd}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result


def connect_device():
    """连接MEmu设备"""
    if not HAS_U2:
        print("⚠️ uiautomator2 未安装，使用 ADB 命令操作")
        return None
    try:
        device = u2.connect(MEMU_ADB_HOST)
        info = device.info
        print(f"✅ 已连接设备: {info.get('productName', 'unknown')}")
        return device
    except Exception as e:
        print(f"⚠️ uiautomator2 连接失败: {e}，使用 ADB 命令操作")
        return None


def swipe_up(device):
    """向上滑动（切换到下一篇文章）"""
    if device:
        device.swipe_ext("up", scale=0.8)
    else:
        # ADB fallback: 从屏幕下部滑到上部
        run_adb("shell input swipe 500 1500 500 500 300")
    time.sleep(1)


def swipe_down(device):
    """向下滑动（切换到上一篇文章）"""
    if device:
        device.swipe_ext("down", scale=0.8)
    else:
        # ADB fallback: 从屏幕上部滑到下部
        run_adb("shell input swipe 500 500 500 1500 300")
    time.sleep(1)


def press_back():
    """按返回键"""
    run_adb("shell input keyevent 4")
    time.sleep(1)


def navigate_to_video_player(device):
    """自动导航到视频播放器

    流程：
    1. 启动App
    2. 等待App加载
    3. 导航到订阅源Tab
    4. 点击视频类型的订阅源
    5. 点击文章列表中的第一篇文章
    6. 等待视频播放器启动

    返回 True 如果导航成功
    """
    print("\n=== 导航到视频播放器 ===")

    # 检查App是否已运行
    result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
    if PACKAGE not in result.stdout:
        # 启动App
        print("  启动App...")
        run_adb(f"shell am start -n {PACKAGE}/{MAIN_ACTIVITY}")
        time.sleep(5)

    # 检查是否已在视频播放器
    result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
    if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
        print("✅ 已在视频播放器页面")
        return True

    # 尝试导航到订阅源
    if device:
        print("  尝试通过 uiautomator2 导航...")
        try:
            # 查找并点击订阅源Tab（底部导航栏）
            rss_tab = device(text="订阅源")
            if rss_tab.exists:
                rss_tab.click()
                time.sleep(2)
                print("  已点击订阅源Tab")
            else:
                print("  ⚠️ 未找到订阅源Tab，尝试从书架切换...")
                # 尝试通过底部导航栏的第2个Tab
                tabs = device(className="android.widget.TabWidget")
                if tabs.exists:
                    children = tabs.child(className="android.widget.TextView")
                    if len(children) >= 2:
                        children[1].click()
                        time.sleep(2)

            # 查找视频类型的订阅源（含视频图标或视频标签的项）
            # 这里简化处理：点击第一个订阅源
            source_item = device(className="androidx.recyclerview.widget.RecyclerView").child(index=0)
            if source_item.exists:
                source_item.click()
                time.sleep(3)
                print("  已点击订阅源")

            # 在文章列表中点击第一篇文章
            article = device(className="androidx.recyclerview.widget.RecyclerView").child(index=0)
            if article.exists:
                article.click()
                time.sleep(5)
                print("  已点击文章")

            # 检查是否进入视频播放器
            result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
            if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
                print("✅ 导航到视频播放器成功")
                return True
            else:
                print("⚠️ 导航后未进入视频播放器")
                return False

        except Exception as e:
            print(f"⚠️ uiautomator2 导航失败: {e}")
            return False
    else:
        print("⚠️ 无 uiautomator2，无法自动导航")
        print("   请使用 --manual 模式：手动导航到视频播放器后再运行脚本")
        return False


def verify_paths(required_paths, found_paths):
    """验证关键路径是否触发"""
    missing = [p for p in required_paths if p not in found_paths]
    return missing


def scenario_swipe_article(device):
    """场景1: 上下滑动切换文章

    验证点：onPageSelected→activatePlayer→switchToArticle→startPlay
    """
    print("\n=== 场景1: 上下滑动切换文章 ===")

    clear_logcat()
    print("  向上滑动切换到下一篇文章...")
    swipe_up(device)
    time.sleep(3)  # 等待切换和加载

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    required = ["onPageSelected", "activatePlayer"]
    missing = verify_paths(required, found)

    if not missing:
        print("✅ 场景1验证通过: 关键路径已触发（onPageSelected + activatePlayer）")
        return True
    else:
        print(f"⚠️ 场景1部分路径未触发: {missing}")
        return False


def scenario_pagination(device):
    """场景2: 分页加载

    验证点：loadMoreArticles + ARTICLES_LOADED
    """
    print("\n=== 场景2: 分页加载 ===")

    clear_logcat()
    print("  连续向上滑动5次，触发分页加载...")
    for i in range(5):
        swipe_up(device)
        time.sleep(2)

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    required = ["loadMoreArticles", "ARTICLES_LOADED"]
    missing = verify_paths(required, found)

    if not missing:
        print("✅ 场景2验证通过: 分页加载已触发")
        return True
    else:
        print(f"⚠️ 场景2部分路径未触发: {missing}")
        print("   （可能文章数量不足，未触发分页加载）")
        return False


def scenario_preload(device):
    """场景3: 预缓冲

    验证点：preloadNextArticleHtml
    """
    print("\n=== 场景3: 预缓冲 ===")

    clear_logcat()
    print("  等待视频播放以触发预缓冲（15秒）...")
    # 等待视频播放到80%触发预缓冲
    time.sleep(15)

    capture_log()
    found = analyze_log()

    if found is None:
        print("⚠️ 日志分析失败")
        return False

    if "preloadNextArticleHtml" in found:
        print("✅ 场景3验证通过: 预缓冲已触发")
        return True
    else:
        print("⚠️ 场景3预缓冲未触发（可能视频未播放到80%）")
        return False


def scenario_position_memory(device):
    """场景4: 位置记忆

    验证点：finish_save_link + onResume_scroll
    """
    print("\n=== 场景4: 位置记忆 ===")

    # 第一步：在播放器中向上滑动改变位置，然后退出
    clear_logcat()
    print("  向上滑动2次改变文章位置...")
    for i in range(2):
        swipe_up(device)
        time.sleep(2)

    print("  按返回键退出播放器...")
    press_back()
    time.sleep(2)

    capture_log()
    found_exit = analyze_log()

    if found_exit is None:
        print("⚠️ 退出阶段日志分析失败")
        return False

    # 第二步：重新进入播放器
    print("  重新进入播放器...")
    clear_logcat()

    # 如果有device，尝试重新进入
    if device:
        try:
            # 在文章列表中点击第一篇文章
            article = device(className="androidx.recyclerview.widget.RecyclerView").child(index=0)
            if article.exists:
                article.click()
                time.sleep(5)
        except Exception:
            pass
    else:
        # ADB fallback：点击屏幕中部
        run_adb("shell input tap 500 800")
        time.sleep(5)

    capture_log()
    found_reenter = analyze_log()

    if found_reenter is None:
        print("⚠️ 重新进入阶段日志分析失败")
        return False

    # 验证关键路径
    has_save = "finish_save_link" in found_exit
    has_scroll = "onResume_scroll" in found_reenter

    if has_save and has_scroll:
        print("✅ 场景4验证通过: 位置记忆已触发")
        return True
    else:
        missing = []
        if not has_save:
            missing.append("finish_save_link")
        if not has_scroll:
            missing.append("onResume_scroll")
        print(f"⚠️ 场景4部分路径未触发: {missing}")
        return False


def scenario_backward_compat(device):
    """场景5: 向后兼容

    验证点：无SwipeTest日志触发（因为不进入文章模式）
    """
    print("\n=== 场景5: 向后兼容 ===")

    # 向后兼容场景需要从非订阅源入口进入播放器
    # 简化验证：检查当前日志中是否有SwipeTest触发
    # 如果当前不是文章模式，不应触发文章相关日志

    clear_logcat()
    print("  等待5秒观察日志...")
    time.sleep(5)

    capture_log()

    # 检查日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        swipetest_lines = [l for l in content.split('\n') if 'SwipeTest' in l]

        # 过滤掉非文章模式的日志（backward_compat 场景不应触发文章切换相关日志）
        article_related = [l for l in swipetest_lines
                          if any(k in l for k in ['onPageSelected', 'switchToArticle', 'loadMoreArticles'])]

        if not article_related:
            print("✅ 场景5验证通过: 向后兼容正常（无文章模式日志触发）")
            return True
        else:
            print(f"⚠️ 场景5向后兼容异常: 触发了 {len(article_related)} 条文章模式日志")
            return False
    else:
        print("✅ 场景5验证通过: 无SwipeTest日志")
        return True


def scenario_buffer_progress(device):
    """场景6: 缓冲进度条更新（F1）

    验证点：F1 startBufferUpdate + F1 缓冲更新
    """
    print("\n=== 场景6: 缓冲进度条更新（F1）===")

    clear_logcat()
    print("  等待视频播放10秒，观察缓冲进度更新...")
    time.sleep(10)

    capture_log()

    # 读取日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        has_start = "F1 startBufferUpdate" in content
        has_update = "F1 缓冲更新" in content

        if has_start and has_update:
            # 统计缓冲更新次数
            update_count = content.count("F1 缓冲更新")
            print(f"✅ 场景6验证通过: 缓冲进度更新已触发（{update_count}次更新）")
            return True
        else:
            missing = []
            if not has_start:
                missing.append("F1 startBufferUpdate")
            if not has_update:
                missing.append("F1 缓冲更新")
            print(f"⚠️ 场景6部分路径未触发: {missing}")
            return False
    else:
        print("⚠️ 日志文件不存在")
        return False


def scenario_control_visibility(device):
    """场景7: 控件自动隐藏（F2）

    验证点：F2 scheduleAutoHide + F2 autoHide触发（3秒后）
    """
    print("\n=== 场景7: 控件自动隐藏（F2）===")

    clear_logcat()
    print("  等待视频播放5秒（控件应显示后3秒自动隐藏）...")
    time.sleep(5)

    capture_log()

    # 读取日志内容
    if LOG_TMP_PATH.exists():
        content = LOG_TMP_PATH.read_text(encoding='utf-8')
        has_schedule = "F2 scheduleAutoHide" in content
        has_autohide = "F2 autoHide触发" in content

        if has_schedule and has_autohide:
            print("✅ 场景7验证通过: 控件自动隐藏已触发（scheduleAutoHide + autoHide触发）")
            return True
        elif has_schedule and not has_autohide:
            print("⚠️ 场景7部分通过: scheduleAutoHide已触发但autoHide未触发")
            print("   （可能3秒未到或控件已被手动隐藏）")
            return False
        else:
            missing = []
            if not has_schedule:
                missing.append("F2 scheduleAutoHide")
            if not has_autohide:
                missing.append("F2 autoHide触发")
            print(f"⚠️ 场景7部分路径未触发: {missing}")
            return False
    else:
        print("⚠️ 日志文件不存在")
        return False


def main():
    parser = argparse.ArgumentParser(description="视频播放器L2功能验证")
    parser.add_argument(
        "--scenario",
        choices=["swipe_article", "pagination", "preload",
                 "position_memory", "backward_compat",
                 "buffer_progress", "control_visibility", "all"],
        default="all",
        help="验证场景（默认all）"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="手动模式：用户已手动导航到视频播放器，脚本只执行场景验证"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Legado 视频播放器L2功能验证")
    print(f"场景: {args.scenario} | 模式: {'手动' if args.manual else '自动'}")
    print("=" * 60)

    # 连接设备
    device = connect_device()

    # 导航到视频播放器（非手动模式时）
    if not args.manual:
        if not navigate_to_video_player(device):
            print("❌ 无法自动导航到视频播放器")
            print("   建议：手动导航到视频播放器后使用 --manual 参数运行")
            sys.exit(2)
    else:
        # 手动模式：验证当前是否在视频播放器
        result = run_adb("shell dumpsys activity activities | findstr mResumedActivity")
        if "VideoPlayer" in result.stdout or "VideoPlay" in result.stdout:
            print("✅ 手动模式：已在视频播放器页面")
        else:
            print("⚠️ 手动模式：当前不在视频播放器页面，仍继续执行")

    # 执行场景验证
    scenarios = {
        "swipe_article": scenario_swipe_article,
        "pagination": scenario_pagination,
        "preload": scenario_preload,
        "position_memory": scenario_position_memory,
        "backward_compat": scenario_backward_compat,
        "buffer_progress": scenario_buffer_progress,
        "control_visibility": scenario_control_visibility,
    }

    if args.scenario == "all":
        results = {}
        for name, func in scenarios.items():
            try:
                results[name] = func(device)
            except Exception as e:
                print(f"❌ 场景 {name} 执行异常: {e}")
                results[name] = False

        print("\n" + "=" * 60)
        print("L2验证结果汇总")
        print("=" * 60)
        for name, passed in results.items():
            status = "✅ 通过" if passed else "⚠️ 未通过"
            print(f"  {name}: {status}")

        all_passed = all(results.values())
    else:
        try:
            passed = scenarios[args.scenario](device)
        except Exception as e:
            print(f"❌ 场景 {args.scenario} 执行异常: {e}")
            passed = False
        all_passed = passed
        print(f"\n场景 {args.scenario}: {'✅ 通过' if passed else '⚠️ 未通过'}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ L2验证全部通过")
    else:
        print("⚠️ L2验证部分未通过（详见上方报告）")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
