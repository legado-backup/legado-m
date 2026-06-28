#!/usr/bin/env python3
"""
degradation_chain.py - 8.4 统一降级链架构

当 debug-source.py 检测到障碍（登录/CF/验证码）时，按统一降级链顺序尝试：
    auto_solve → cookie_import → manual_guide → mark_unverifiable

每一步成功则返回，全部失败则标记 unverifiable。支持配置自定义顺序与启用开关。
辅助模块（obstacle_resolver/cookie_manager/interactive_guide）以 try-import 方式加载，
缺失时该步骤自动跳过，不报错。

用法:
    from degradation_chain import degrade
    result = degrade(url, "cf", context={"html": html})
    if result["success"]:
        cookie_store = result["cookie_store"]
"""

import copy
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TOOLS_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _TOOLS_DIR / "degradation_config.json"

# 添加 scripts/ 目录到 sys.path 以导入 legado_client 包（obstacle_resolver/interactive_guide 已迁移）
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# try-import 辅助模块（obstacle_resolver/interactive_guide 已迁移至 legado_client/，cookie_manager 仍在 tools/）
try:
    from legado_client.client.obstacle_resolver import resolve_obstacle
    _HAS_OBSTACLE_RESOLVER = True
except ImportError:
    _HAS_OBSTACLE_RESOLVER = False
    resolve_obstacle = None

try:
    from cookie_manager import PersistentCookieStore
    _HAS_COOKIE_MANAGER = True
except ImportError:
    _HAS_COOKIE_MANAGER = False
    PersistentCookieStore = None

try:
    from legado_client.client.interactive_guide import guide_login, guide_cf_bypass, guide_captcha
    _HAS_INTERACTIVE_GUIDE = True
except ImportError:
    _HAS_INTERACTIVE_GUIDE = False
    guide_login = guide_cf_bypass = guide_captcha = None


# ---------------------------------------------------------------------------
# 常量与默认配置
# ---------------------------------------------------------------------------

# 默认降级步骤顺序
DEGRADATION_STEPS = ["auto_solve", "cookie_import", "manual_guide", "mark_unverifiable"]

_DEFAULT_CONFIG = {
    "steps": list(DEGRADATION_STEPS),
    "enabled": {
        "auto_solve": True,
        "cookie_import": True,
        "manual_guide": True,
        "mark_unverifiable": True,
    },
    "timeout_seconds": {
        "auto_solve": 30,
        "cookie_import": 15,
        "manual_guide": 120,
    },
}

# 降级追踪记录：{(url, obstacle_type): [{step, success, duration, message}]}
_track_log = {}


# ---------------------------------------------------------------------------
# 配置加载/保存
# ---------------------------------------------------------------------------

def load_config():
    """从 tools/degradation_config.json 加载降级链配置。

    文件不存在时自动生成默认配置。缺失字段用默认值补全。

    Returns:
        dict: 配置字典
    """
    if not _CONFIG_FILE.exists():
        save_config(copy.deepcopy(_DEFAULT_CONFIG))
        return copy.deepcopy(_DEFAULT_CONFIG)
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return copy.deepcopy(_DEFAULT_CONFIG)
    # 补全缺失字段
    for k, v in _DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = copy.deepcopy(v)
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                cfg[k].setdefault(sub_k, sub_v)
    return cfg


def save_config(config):
    """保存降级链配置到 tools/degradation_config.json。

    Returns:
        bool: 是否保存成功
    """
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 结果构造
# ---------------------------------------------------------------------------

def _make_result(success=False, step=None, cookie_store=None, message="", log=None):
    """构造统一的降级结果 dict（不依赖 ResolveResult，保证模块独立可用）"""
    return {
        "success": success,
        "step": step,
        "cookie_store": cookie_store or {},
        "message": message,
        "log": log or [],
    }


# ---------------------------------------------------------------------------
# 各步骤实现
# ---------------------------------------------------------------------------

def _step_auto_solve(url, obstacle_type, html, cookie_store):
    """步骤1：自动求解（cloudscraper/OCR/加密分析）"""
    if not _HAS_OBSTACLE_RESOLVER:
        return _make_result(False, "auto_solve", cookie_store,
                            "obstacle_resolver 未安装，跳过自动求解")
    try:
        result = resolve_obstacle(url, html, obstacle_type, cookie_store)
        return _make_result(result.success, "auto_solve", result.cookie_store,
                            result.message, result.log)
    except Exception as e:
        return _make_result(False, "auto_solve", cookie_store,
                            f"自动求解异常: {e}")


def _step_cookie_import(url, obstacle_type, html, cookie_store):
    """步骤2：从持久化存储加载 Cookie"""
    if not _HAS_COOKIE_MANAGER:
        return _make_result(False, "cookie_import", cookie_store,
                            "cookie_manager 未安装，跳过Cookie导入")
    try:
        store = PersistentCookieStore()
        cookie_str = store.get_cookie_for_url(url)
        if not cookie_str:
            return _make_result(False, "cookie_import", cookie_store,
                                "无可用Cookie缓存")
        domain = urlparse(url).netloc
        cookie_store[domain] = cookie_str
        return _make_result(True, "cookie_import", cookie_store,
                            f"从缓存加载Cookie成功: {domain}")
    except Exception as e:
        return _make_result(False, "cookie_import", cookie_store,
                            f"Cookie导入异常: {e}")


def _step_manual_guide(url, obstacle_type, html, cookie_store, context):
    """步骤3：交互式引导用户操作"""
    if not _HAS_INTERACTIVE_GUIDE:
        return _make_result(False, "manual_guide", cookie_store,
                            "interactive_guide 未安装，跳过交互引导")
    try:
        domain = urlparse(url).netloc
        if obstacle_type == "login":
            cookie_str = guide_login(url)
        elif obstacle_type == "cf":
            cookie_str = guide_cf_bypass(url)
        elif obstacle_type == "captcha":
            img_path = (context or {}).get("captcha_img_path", "")
            cookie_str = guide_captcha(img_path) if img_path else ""
        else:
            return _make_result(False, "manual_guide", cookie_store,
                                f"不支持的障碍类型: {obstacle_type}")
        if not cookie_str:
            return _make_result(False, "manual_guide", cookie_store,
                                "用户未提供Cookie")
        cookie_store[domain] = cookie_str
        # 持久化用户导入的 Cookie
        if _HAS_COOKIE_MANAGER:
            try:
                PersistentCookieStore().save(domain, cookie_str)
            except Exception:
                pass
        return _make_result(True, "manual_guide", cookie_store,
                            f"用户手动导入Cookie成功: {domain}")
    except Exception as e:
        return _make_result(False, "manual_guide", cookie_store,
                            f"交互引导异常: {e}")


def _step_mark_unverifiable(url, obstacle_type, cookie_store):
    """步骤4：标记为不可验证并记录"""
    return _make_result(False, "mark_unverifiable", cookie_store,
                        f"所有降级策略均失败，标记为不可验证: {url} ({obstacle_type})")


# ---------------------------------------------------------------------------
# 步骤执行入口
# ---------------------------------------------------------------------------

def execute_step(step_name, url, obstacle_type, context=None):
    """执行单个降级步骤。

    Args:
        step_name: 步骤名 auto_solve/cookie_import/manual_guide/mark_unverifiable
        url: 目标URL
        obstacle_type: 障碍类型 login/cf/captcha
        context: 上下文 dict，可含 html/cookie_store/captcha_img_path

    Returns:
        dict: 降级结果 {success, step, cookie_store, message, log}
    """
    ctx = context or {}
    html = ctx.get("html", "")
    cookie_store = dict(ctx.get("cookie_store") or {})

    if step_name == "auto_solve":
        return _step_auto_solve(url, obstacle_type, html, cookie_store)
    if step_name == "cookie_import":
        return _step_cookie_import(url, obstacle_type, html, cookie_store)
    if step_name == "manual_guide":
        return _step_manual_guide(url, obstacle_type, html, cookie_store, ctx)
    if step_name == "mark_unverifiable":
        return _step_mark_unverifiable(url, obstacle_type, cookie_store)
    return _make_result(False, step_name, cookie_store, f"未知步骤: {step_name}")


# ---------------------------------------------------------------------------
# 降级追踪
# ---------------------------------------------------------------------------

def _record_track(url, obstacle_type, step, success, duration, message):
    """内部：记录单步追踪信息"""
    key = (url, obstacle_type)
    _track_log.setdefault(key, []).append({
        "step": step,
        "success": success,
        "duration_seconds": round(duration, 3),
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


def track_degradation(url, obstacle_type):
    """查询指定障碍场景的降级追踪记录。

    Args:
        url: 目标URL
        obstacle_type: 障碍类型 login/cf/captcha

    Returns:
        list[dict]: 该场景尝试过的所有步骤记录；无记录返回空列表
    """
    return list(_track_log.get((url, obstacle_type), []))


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def degrade(url, obstacle_type, context=None):
    """按降级链顺序尝试每种策略，成功则返回，全部失败则标记 unverifiable。

    Args:
        url: 目标URL
        obstacle_type: 障碍类型 login/cf/captcha
        context: 上下文 dict，可含 html/cookie_store/captcha_img_path

    Returns:
        dict: 降级结果 {success, step, cookie_store, message, log}
    """
    cfg = load_config()
    steps = cfg.get("steps") or DEGRADATION_STEPS
    enabled = cfg.get("enabled", {})
    ctx = dict(context or {})
    # 上下文中的 cookie_store 在各步骤间传递
    cookie_store = dict(ctx.get("cookie_store") or {})

    for step_name in steps:
        if not enabled.get(step_name, True):
            continue
        start = time.time()
        result = execute_step(step_name, url, obstacle_type,
                              {**ctx, "cookie_store": cookie_store})
        duration = time.time() - start
        # 同步 cookie_store 到上下文（步骤间传递）
        cookie_store = dict(result.get("cookie_store") or cookie_store)
        _record_track(url, obstacle_type, step_name, result["success"],
                      duration, result["message"])
        if result["success"]:
            return result
    # 全部失败，执行标记步骤（若启用）
    if enabled.get("mark_unverifiable", True) and "mark_unverifiable" not in steps:
        result = execute_step("mark_unverifiable", url, obstacle_type,
                              {"cookie_store": cookie_store})
        _record_track(url, obstacle_type, "mark_unverifiable",
                      False, 0.0, result["message"])
        return result
    # 返回最后一步结果
    return result


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def _self_test():
    """最小自检：覆盖纯逻辑函数的正常+边界用例"""
    # 1. load_config - 正常用例（文件已存在）
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert "steps" in cfg and len(cfg["steps"]) == 4
    assert cfg["steps"] == DEGRADATION_STEPS
    # 边界用例：enabled 字段补全
    assert cfg["enabled"]["auto_solve"] is True

    # 2. execute_step - 未知步骤
    r = execute_step("unknown_step", "http://x.com", "login")
    assert r["success"] is False
    assert "未知步骤" in r["message"]

    # 3. execute_step - mark_unverifiable
    r = execute_step("mark_unverifiable", "http://x.com", "cf",
                     {"cookie_store": {"x.com": "k=v"}})
    assert r["success"] is False
    assert r["step"] == "mark_unverifiable"
    assert r["cookie_store"] == {"x.com": "k=v"}

    # 4. track_degradation - 无记录返回空列表
    tracks = track_degradation("http://no-record.test", "login")
    assert tracks == []

    # 5. degrade - 全部辅助模块可能缺失，应走完降级链到 mark_unverifiable
    r = degrade("http://test-degrade.test", "login", context={"html": ""})
    assert r["success"] is False
    # 应有追踪记录
    tracks = track_degradation("http://test-degrade.test", "login")
    assert len(tracks) >= 1
    # 清理追踪记录
    _track_log.clear()

    print("[self_test] degradation_chain 全部通过 (5 组用例)")


if __name__ == "__main__":
    _self_test()
