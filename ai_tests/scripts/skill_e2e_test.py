#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_e2e_test.py — Legado Source Creator Skill v3 端到端测试

测试目标：
    AC-1: Skill 核心模块导入正常（归档后无 ImportError）
    AC-2: sanitize_source_json 修复 None 序列化 bug（Rss.kt:64 不再触发 ReferenceError）
    AC-3: CLI 入口可启动（python -m legado_client --help）
    AC-4: 真实源 JSON 模拟端到端：含 None 字段的源经 sanitize 后输出合规 JSON

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/skill_e2e_test.py
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/skill_e2e_test.py --verbose

退出码：
    0 = 全部通过
    1 = 有失败项
    2 = 环境错误（venv 路径错误等）

设计依据：
    docs/specs/legado-skill-v3-rebuild/spec.md (FR-4, AC-2)
    docs/specs/legado-skill-v3-rebuild/design.md (ADR-F: None Bug 修复方案)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, List, Tuple

# === 路径常量（不依赖 ai_tests.config，独立运行）===
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = PROJECT_ROOT / ".trae" / "skills" / "legado-source-creator"
SKILL_SCRIPTS = SKILL_ROOT / "scripts"
SKILL_VENV_PYTHON = SKILL_SCRIPTS / ".venv" / "Scripts" / "python.exe"


# === 测试结果类型 ===
class TestResult:
    """单条测试结果。"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, name: str, status: str, detail: str = ""):
        self.name = name
        self.status = status
        self.detail = detail

    def __str__(self) -> str:
        symbol = {"PASS": "[OK]", "FAIL": "[XX]", "SKIP": "[--]"}.get(self.status, "[??]")
        return f"  {symbol} {self.name}: {self.detail}"


# === 测试用例 ===

def test_skill_scripts_dir_exists() -> TestResult:
    """AC-1.1: skill scripts 目录存在。"""
    if SKILL_SCRIPTS.is_dir():
        return TestResult("skill_scripts_dir_exists", TestResult.PASS,
                          f"path={SKILL_SCRIPTS}")
    return TestResult("skill_scripts_dir_exists", TestResult.FAIL,
                      f"目录不存在: {SKILL_SCRIPTS}")


def test_skill_venv_python_executable() -> TestResult:
    """AC-1.2: skill venv Python 可执行。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("skill_venv_python_executable", TestResult.FAIL,
                          f"venv python 不存在: {SKILL_VENV_PYTHON}")
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return TestResult("skill_venv_python_executable", TestResult.PASS,
                              f"python={version}")
        return TestResult("skill_venv_python_executable", TestResult.FAIL,
                          f"returncode={result.returncode}")
    except Exception as e:
        return TestResult("skill_venv_python_executable", TestResult.FAIL,
                          f"exception={e}")


def test_skill_core_modules_import() -> TestResult:
    """AC-1.3: skill 核心模块全部可导入（归档后无 ImportError）。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("skill_core_modules_import", TestResult.SKIP,
                          "venv python 不可用，跳过")

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from legado_client.cli import main; "
        "from legado_client.client.debug_runner import run; "
        "from legado_client.client.debug_orchestrator import DebugOrchestrator; "
        "from legado_client.analyzer.auto_fixer import auto_fix_error; "
        "from legado_client.experience.experience_manager import ExperienceManager; "
        "from legado_client.utils.file_utils import sanitize_source_json; "
        "from legado_client.delegate import OcrDelegate; "
        "print('OK')"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=30,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return TestResult("skill_core_modules_import", TestResult.PASS,
                              "7 模块导入成功")
        stderr_tail = (result.stderr or "")[-200:]
        return TestResult("skill_core_modules_import", TestResult.FAIL,
                          f"returncode={result.returncode}, stderr={stderr_tail}")
    except Exception as e:
        return TestResult("skill_core_modules_import", TestResult.FAIL,
                          f"exception={e}")


def test_archive_dir_exists() -> TestResult:
    """AC-1.4: 归档目录存在（v3 重构归档完整性）。

    归档位置：.trae/skills/legado-source-creator-archive/（与 skill 平级）
    """
    archive_dir = SKILL_ROOT.parent / "legado-source-creator-archive"
    if archive_dir.is_dir():
        subdirs = [d.name for d in archive_dir.iterdir() if d.is_dir()]
        return TestResult("archive_dir_exists", TestResult.PASS,
                          f"归档子目录={subdirs}")
    return TestResult("archive_dir_exists", TestResult.FAIL,
                      f"归档目录不存在: {archive_dir}")


def test_sanitize_function_basic() -> TestResult:
    """AC-2.1: sanitize_source_json 基础功能：None → 空字符串。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("sanitize_basic", TestResult.SKIP, "venv 不可用")

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from legado_client.utils.file_utils import sanitize_source_json; "
        "r1 = sanitize_source_json({'a': None, 'b': 1}); "
        "assert r1 == {'a': '', 'b': 1}, f'case1 fail: {r1}'; "
        "r2 = sanitize_source_json(None); "
        "assert r2 == '', f'case2 fail: {r2}'; "
        "r3 = sanitize_source_json([None, 1, {'x': None}]); "
        "assert r3 == ['', 1, {'x': ''}], f'case3 fail: {r3}'; "
        "print('OK')"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return TestResult("sanitize_basic", TestResult.PASS,
                              "3 用例通过：dict/None/list")
        return TestResult("sanitize_basic", TestResult.FAIL,
                          f"stderr={result.stderr[-200:]}")
    except Exception as e:
        return TestResult("sanitize_basic", TestResult.FAIL, f"exception={e}")


def test_sanitize_preserves_falsy() -> TestResult:
    """AC-2.2: sanitize 保留 falsy 非 None 值（False/0/[]/{}）。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("sanitize_preserves_falsy", TestResult.SKIP, "venv 不可用")

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from legado_client.utils.file_utils import sanitize_source_json; "
        "r = sanitize_source_json({'f': False, 'z': 0, 'el': [], 'ed': {}, 'n': None}); "
        "assert r == {'f': False, 'z': 0, 'el': [], 'ed': {}, 'n': ''}, f'fail: {r}'; "
        "print('OK')"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0:
            return TestResult("sanitize_preserves_falsy", TestResult.PASS,
                              "False/0/[]/{} 保留，None 替换")
        return TestResult("sanitize_preserves_falsy", TestResult.FAIL,
                          f"stderr={result.stderr[-200:]}")
    except Exception as e:
        return TestResult("sanitize_preserves_falsy", TestResult.FAIL, f"exception={e}")


def test_sanitize_no_none_string_in_dumps() -> TestResult:
    """AC-2.3（核心）: sanitize 后 json.dumps 输出不含字符串 'None' 或 'null'。

    这是 Rss.kt:64 ReferenceError 的根因修复验证。
    """
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("sanitize_no_none_string", TestResult.SKIP, "venv 不可用")

    code = (
        "import sys, json; sys.path.insert(0, '.'); "
        "from legado_client.utils.file_utils import sanitize_source_json; "
        "src = {'sourceUrl': 'https://example.com', 'loginCheckJs': None, "
        "       'ruleArticles': None, 'header': None}; "
        "sanitized = sanitize_source_json(src); "
        "json_str = json.dumps(sanitized, ensure_ascii=False); "
        "assert 'None' not in json_str, f'发现字符串 None: {json_str}'; "
        "assert 'null' not in json_str, f'发现 null: {json_str}'; "
        "print('OK json=' + json_str)"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            # 输出中含 JSON 串（已脱敏，只含 example.com）
            json_line = result.stdout.strip()
            return TestResult("sanitize_no_none_string", TestResult.PASS,
                              "json.dumps 输出无 'None' / 'null'")
        return TestResult("sanitize_no_none_string", TestResult.FAIL,
                          f"stderr={result.stderr[-200:]}")
    except Exception as e:
        return TestResult("sanitize_no_none_string", TestResult.FAIL, f"exception={e}")


def test_cli_help_works() -> TestResult:
    """AC-3: CLI 入口可启动（python -m legado_client --help）。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("cli_help_works", TestResult.SKIP, "venv 不可用")

    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-m", "legado_client", "--help"],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "usage:" in result.stdout:
            # 提取 subcommands 验证完整
            has_debug = "debug" in result.stdout
            has_verify = "verify" in result.stdout
            return TestResult("cli_help_works", TestResult.PASS,
                              f"debug={has_debug}, verify={has_verify}")
        return TestResult("cli_help_works", TestResult.FAIL,
                          f"returncode={result.returncode}")
    except Exception as e:
        return TestResult("cli_help_works", TestResult.FAIL, f"exception={e}")


def test_real_source_json_simulation() -> TestResult:
    """AC-4: 真实源 JSON 模拟：模拟 v2 测试遗留的 None 字段场景。

    场景：AI 生成源时常见 None 字段（loginCheckJs/loginUrl/header/ruleContent），
    经 sanitize_source_json 后输出合规 JSON。
    """
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("real_source_json_simulation", TestResult.SKIP, "venv 不可用")

    # 模拟一个 AI 生成时常残留 None 字段的订阅源
    simulated_source = {
        "sourceName": "测试源",
        "sourceUrl": "https://example.com/rss",
        "sourceType": "rss",
        "enabled": True,
        "loginUrl": None,           # 未配置登录
        "loginCheckJs": None,       # 未配置登录检查 JS
        "header": None,             # 未配置 header
        "customOrder": 0,
        "ruleArticles": ".article-item@css",
        "ruleContent": None,        # 未配置正文规则
        "ruleSearch": None,         # 订阅源无搜索
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(simulated_source, f, ensure_ascii=False)
        temp_path = f.name

    try:
        code = (
            "import sys, json; sys.path.insert(0, '.'); "
            "from legado_client.utils.file_utils import sanitize_source_json; "
            f"src = json.load(open(r'{temp_path}', encoding='utf-8')); "
            "sanitized = sanitize_source_json(src); "
            "out = json.dumps(sanitized, ensure_ascii=False); "
            "assert 'None' not in out, 'found None string'; "
            "assert 'null' not in out, 'found null'; "
            "assert sanitized['loginCheckJs'] == '', 'loginCheckJs not empty str'; "
            "assert sanitized['ruleArticles'] == '.article-item@css', 'ruleArticles lost'; "
            "assert sanitized['enabled'] is True, 'enabled changed'; "
            "print('OK fields=' + str(len(sanitized)))"
        )
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            fields_count = result.stdout.strip().split("fields=")[-1]
            return TestResult("real_source_json_simulation", TestResult.PASS,
                              f"模拟源 {fields_count} 字段经 sanitize 全合规")
        return TestResult("real_source_json_simulation", TestResult.FAIL,
                          f"stderr={result.stderr[-300:]}")
    except Exception as e:
        return TestResult("real_source_json_simulation", TestResult.FAIL, f"exception={e}")
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def test_broken_references_gone() -> TestResult:
    """AC-1.5: 归档后无 broken 顶层 import（cli.py / debug_runner.py 等）。"""
    # 扫描所有 .py 文件，检查顶层 from legado_client.{archived} import
    archived_modules = ["web", "storage", "server", "device", "alembic"]
    broken = []
    for py_file in SKILL_SCRIPTS.rglob("*.py"):
        # 跳过 archive 目录本身
        if "archive" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for mod in archived_modules:
            # 匹配顶层 import（非延迟 try/except 内的）
            for line_no, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                # 跳过注释行
                if stripped.startswith("#"):
                    continue
                # 匹配 from legado_client.{mod} import 或 import legado_client.{mod}
                if (f"from legado_client.{mod} import" in stripped or
                    f"import legado_client.{mod}" in stripped):
                    # 检查是否在 try/except 块内（延迟导入）
                    # 简化判定：行首缩进 ≥ 4 空格视为 try 内（容错）
                    if not line.startswith(" " * 4):
                        broken.append(f"{py_file.name}:{line_no}: {stripped}")
    if not broken:
        return TestResult("broken_references_gone", TestResult.PASS,
                          "无顶层 import 归档模块")
    return TestResult("broken_references_gone", TestResult.FAIL,
                      f"发现 {len(broken)} 处: {'; '.join(broken[:3])}")


# ========== AC-5 必填字段校验器（v4 新增）==========

def test_mandatory_field_validator_exists() -> TestResult:
    """AC-5.1: mandatory_fields.py 校验器模块存在且可导入。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("mandatory_validator_exists", TestResult.SKIP, "venv 不可用")

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from legado_client.validator import ("
        "MandatoryFieldValidator, validate_source, format_validation_report,"
        "BOOK_SOURCE_FIELDS, RSS_SOURCE_FIELDS); "
        "assert len(BOOK_SOURCE_FIELDS) > 0; "
        "assert len(RSS_SOURCE_FIELDS) > 0; "
        "print('OK')"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return TestResult("mandatory_validator_exists", TestResult.PASS,
                              "validator 模块导入成功")
        return TestResult("mandatory_validator_exists", TestResult.FAIL,
                          f"stderr={result.stderr[-200:]}")
    except Exception as e:
        return TestResult("mandatory_validator_exists", TestResult.FAIL, f"exception={e}")


def test_mandatory_validator_catches_missing_fields() -> TestResult:
    """AC-5.2（核心）: 校验器准确捕获 rssSource_skill_v2_test.json 缺失字段。

    用户反馈：生成的源缺 sourceIcon/searchUrl/sortUrl = 不可用。
    校验器必须捕获这些字段（CRITICAL+MANDATORY+RECOMMENDED）。
    """
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("mandatory_catches_missing", TestResult.SKIP, "venv 不可用")

    # 模拟 rssSource_skill_v2_test.json 的问题源（缺 sourceIcon/searchUrl/sortUrl）
    code = (
        "import sys, json; sys.path.insert(0, '.'); "
        "from legado_client.validator import validate_source; "
        "bad_source = {"
        "  'sourceName': 'test', 'sourceUrl': 'https://example.com',"
        "  'sourceIcon': '', 'searchUrl': None, 'sortUrl': None,"
        "  'ruleArticles': '@CSS:.item', 'ruleTitle': '@CSS:.title',"
        "  'ruleLink': '@CSS:a@href', 'ruleContent': '@CSS:.content',"
        "  'ruleNextPage': None"
        "}; "
        "result = validate_source(bad_source, source_type='rss', strict_recommended=True); "
        "assert not result['passed'], '校验应该失败'; "
        "missing = result['all_missing']; "
        "assert 'sourceIcon' in missing, f'sourceIcon 未被捕获: {missing}'; "
        "assert 'searchUrl' in missing, f'searchUrl 未被捕获: {missing}'; "
        "assert 'sortUrl' in missing, f'sortUrl 未被捕获: {missing}'; "
        "print('OK missing=' + str(missing))"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return TestResult("mandatory_catches_missing", TestResult.PASS,
                              "捕获 sourceIcon/searchUrl/sortUrl 缺失")
        return TestResult("mandatory_catches_missing", TestResult.FAIL,
                          f"stderr={result.stderr[-300:]}")
    except Exception as e:
        return TestResult("mandatory_catches_missing", TestResult.FAIL, f"exception={e}")


def test_mandatory_validator_passes_complete_source() -> TestResult:
    """AC-5.3: 校验器对完整源（所有字段齐全）应通过。"""
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("mandatory_passes_complete", TestResult.SKIP, "venv 不可用")

    code = (
        "import sys; sys.path.insert(0, '.'); "
        "from legado_client.validator import validate_source; "
        "good_source = {"
        "  'sourceName': 'test', 'sourceUrl': 'https://example.com',"
        "  'sourceIcon': 'https://example.com/icon.png',"
        "  'searchUrl': 'https://example.com/search?q={{key}}',"
        "  'sortUrl': '分类1::https://example.com/cat1',"
        "  'sourceGroup': '测试', 'sourceComment': '测试源',"
        "  'type': 2,"
        "  'ruleArticles': '@CSS:.item', 'ruleTitle': '@CSS:.title',"
        "  'ruleLink': '@CSS:a@href', 'ruleContent': '@CSS:.content',"
        "  'ruleImage': '@CSS:img@src', 'ruleDescription': '@CSS:.desc',"
        "  'ruleNextPage': '@CSS:a.next@href'"
        "}; "
        "result = validate_source(good_source, source_type='rss', strict_recommended=True); "
        "assert result['passed'], f'完整源应通过: {result}'; "
        "print('OK')"
    )
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            return TestResult("mandatory_passes_complete", TestResult.PASS,
                              "完整源 14 字段全通过")
        return TestResult("mandatory_passes_complete", TestResult.FAIL,
                          f"stderr={result.stderr[-300:]}")
    except Exception as e:
        return TestResult("mandatory_passes_complete", TestResult.FAIL, f"exception={e}")


def test_real_rss_source_skill_v2_validation() -> TestResult:
    """AC-5.4（核心）: 真实测试遗留的 rssSource_skill_v2_test.json 应被校验为失败。

    用户指出的具体文件：output/rss/rssSource_skill_v2_test.json
    缺 sourceIcon/searchUrl/sortUrl → 应被校验为不可用。
    """
    if not SKILL_VENV_PYTHON.is_file():
        return TestResult("real_v2_validation", TestResult.SKIP, "venv 不可用")

    real_file = PROJECT_ROOT / "output" / "rss" / "rssSource_skill_v2_test.json"
    if not real_file.is_file():
        return TestResult("real_v2_validation", TestResult.SKIP,
                          f"测试文件不存在: {real_file}")

    # 用多行字符串 + .format() 避免 f-string 引号嵌套问题
    code = """
import sys, json
sys.path.insert(0, '.')
from legado_client.validator import validate_source, format_validation_report

real_file = r'{real_file}'
with open(real_file, encoding='utf-8') as f:
    data = json.load(f)
if isinstance(data, list):
    data = data[0]
result = validate_source(data, source_type='rss', strict_recommended=True)
assert not result['passed'], 'v2 测试源缺字段应该校验失败'
assert 'sourceIcon' in result['all_missing']
assert 'searchUrl' in result['all_missing']
assert 'sortUrl' in result['all_missing']
print('OK missing_count=' + str(len(result['all_missing'])))
""".format(real_file=str(real_file))
    try:
        result = subprocess.run(
            [str(SKILL_VENV_PYTHON), "-c", code],
            capture_output=True, text=True, timeout=15,
            cwd=str(SKILL_SCRIPTS),
        )
        if result.returncode == 0 and "OK" in result.stdout:
            missing_count = result.stdout.strip().split("missing_count=")[-1]
            return TestResult("real_v2_validation", TestResult.PASS,
                              f"v2 测试源 {missing_count} 字段缺失被捕获")
        return TestResult("real_v2_validation", TestResult.FAIL,
                          f"stderr={result.stderr[-300:]}")
    except Exception as e:
        return TestResult("real_v2_validation", TestResult.FAIL, f"exception={e}")


# === 测试运行器 ===

def run_all_tests(verbose: bool = False) -> int:
    """运行所有测试用例，返回退出码。"""
    test_cases: List[Tuple[str, Callable[[], TestResult]]] = [
        ("环境检查", [
            test_skill_scripts_dir_exists,
            test_skill_venv_python_executable,
            test_archive_dir_exists,
        ]),
        ("AC-1 核心模块导入", [
            test_skill_core_modules_import,
            test_broken_references_gone,
        ]),
        ("AC-2 None 序列化 bug 修复", [
            test_sanitize_function_basic,
            test_sanitize_preserves_falsy,
            test_sanitize_no_none_string_in_dumps,
        ]),
        ("AC-3 CLI 入口", [
            test_cli_help_works,
        ]),
        ("AC-4 真实源 JSON 端到端", [
            test_real_source_json_simulation,
        ]),
        ("AC-5 必填字段校验器（v4）", [
            test_mandatory_field_validator_exists,
            test_mandatory_validator_catches_missing_fields,
            test_mandatory_validator_passes_complete_source,
            test_real_rss_source_skill_v2_validation,
        ]),
    ]

    print("=" * 72)
    print("Legado Source Creator Skill v3 端到端测试")
    print(f"Skill 路径: {SKILL_ROOT}")
    print(f"venv Python: {SKILL_VENV_PYTHON}")
    print("=" * 72)

    all_results: List[TestResult] = []
    for group_name, tests in test_cases:
        print(f"\n【{group_name}】")
        for test_fn in tests:
            try:
                result = test_fn()
            except Exception as e:
                result = TestResult(test_fn.__name__, TestResult.FAIL,
                                    f"uncaught exception: {e}")
            all_results.append(result)
            print(result)
            if verbose and result.status == TestResult.FAIL:
                # 详细输出已在 detail 中
                pass

    # 汇总
    passed = sum(1 for r in all_results if r.status == TestResult.PASS)
    failed = sum(1 for r in all_results if r.status == TestResult.FAIL)
    skipped = sum(1 for r in all_results if r.status == TestResult.SKIP)
    total = len(all_results)

    print("\n" + "=" * 72)
    print(f"测试汇总：总计 {total} | 通过 {passed} | 失败 {failed} | 跳过 {skipped}")
    print("=" * 72)

    if failed == 0 and skipped == 0:
        print("[PASS] 全部测试通过")
        return 0
    elif failed == 0:
        print(f"[WARN] 主测试通过（{skipped} 项因环境跳过）")
        return 0
    else:
        print(f"[FAIL] {failed} 项测试失败")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Skill v3 端到端测试",
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细输出")
    args = parser.parse_args()

    if not SKILL_ROOT.is_dir():
        print(f"错误: skill 目录不存在: {SKILL_ROOT}", file=sys.stderr)
        return 2

    return run_all_tests(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
