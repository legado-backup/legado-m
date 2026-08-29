"""ai_tests/tests/conftest.py — pytest 公共夹具

自动把项目根加入 sys.path，保证 `from ai_tests.xxx import ...` 可直接导入，
无需手动设置 PYTHONPATH。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
