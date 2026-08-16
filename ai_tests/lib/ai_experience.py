"""ai_tests/lib/ai_experience.py — AiExperience（AI-LLM-Testing 经验层，AD-05）

职责：跨运行复用已验证的元素定位与判定样本，避免重复花 token/时间：
- elements: {screen_signature: {desc: [x1,y1,x2,y2]}} 已验证可点击元素（设备坐标）
- verdicts: [{tc_id, prompt_hash, verdict, confidence, note}] 判定样本（few-shot 参考）
- 签名失效控制：元素经验按 screen_signature（Activity + 首个关键文本）隔离，
  UI 改版后签名不匹配自动失效

持久化：ai_tests/experience/ai_experience.json（load/save 原子写）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_tests.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

EXPERIENCE_PATH = PROJECT_ROOT / "ai_tests" / "experience" / "ai_experience.json"


class AiExperience:
    """经验库（JSON 持久化）"""

    def __init__(self, path: Path = EXPERIENCE_PATH):
        self.path = path
        self._data: Dict[str, Any] = {
            "version": 1,
            "elements": {},
            "verdicts": [],
            "updated_at": None,
        }
        self._load()

    # === 加载/保存 ===

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("经验库加载失败（重建空库）: %s", e)
            self._data = {"version": 1, "elements": {}, "verdicts": []}

    def save(self) -> None:
        self._data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(self.path)

    # === 元素经验 ===

    def lookup(self, desc: str, screen_signature: str) -> Optional[List[int]]:
        """查已验证元素（命中返回设备坐标 [x1,y1,x2,y2]）"""
        return self._data.get("elements", {}).get(screen_signature, {}).get(desc)

    def record_element(self, desc: str, screen_signature: str, box: List[int]) -> None:
        """记录验证成功的元素定位（覆盖旧样本）"""
        screen = self._data.setdefault("elements", {}).setdefault(screen_signature, {})
        screen[desc] = box
        logger.debug("经验记录元素 %s@%s: %s", desc, screen_signature, box)

    # === 判定样本 ===

    def add_verdict(self, tc_id: str, prompt_hash: str, verdict: str,
                    confidence: int, note: str = "") -> None:
        """记录判定样本（供 few-shot 参考）"""
        self._data.setdefault("verdicts", []).append({
            "tc_id": tc_id,
            "prompt_hash": prompt_hash,
            "verdict": verdict,
            "confidence": confidence,
            "note": note,
            "at": datetime.now().isoformat(timespec="seconds"),
        })
        # 仅保留最近 200 条，防无限膨胀
        self._data["verdicts"] = self._data["verdicts"][-200:]

    def recent_verdicts(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self._data.get("verdicts", [])[-limit:]

    # === 元信息 ===

    def stats(self) -> Dict[str, Any]:
        return {
            "screens": len(self._data.get("elements", {})),
            "elements": sum(len(v) for v in self._data.get("elements", {}).values()),
            "verdicts": len(self._data.get("verdicts", [])),
            "updated_at": self._data.get("updated_at"),
        }


# === 自检 ===
if __name__ == "__main__":
    import tempfile
    exp = AiExperience(Path(tempfile.mkdtemp()) / "exp.json")
    exp.record_element("开关", "BookshelfScreen:番茄小说", [100, 200, 300, 400])
    exp.add_verdict("TC-1", "abc", "pass", 90, "演示")
    assert exp.lookup("开关", "BookshelfScreen:番茄小说") == [100, 200, 300, 400]
    exp.save()
    exp2 = AiExperience(exp.path)
    assert exp2.lookup("开关", "BookshelfScreen:番茄小说") == [100, 200, 300, 400]
    assert exp2.stats()["elements"] == 1
    print("[PASS] ai_experience 持久化读写")
