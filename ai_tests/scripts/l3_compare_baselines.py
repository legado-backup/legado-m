#!/usr/bin/env python3
"""l3_compare_baselines.py — A5.8 L3 渲染基线对比（pre-a3 vs after-a3，ui-subpage-optimization）

目的：A3 主题链（danger 色 / token 门面 / 撞色阈值）改动后，用重采样基线（after-a3）
与 A3 前原基线（baseline-pre-a3）逐帧比对，确认组件/主题收敛未改坏观感。

⚠️ 判读边界：模拟器渲染管线故障（AD-25）会产出黑帧/陈旧帧，本脚本**不自动判定通过**，
只产出客观逐帧差异报告（平均像素差 + 显著变化像素占比），最终由人工判读。

用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/l3_compare_baselines.py [--root output/ui-baseline]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops

# 已知故障特征：黑帧/陈旧帧字节极小 → 判定为渲染管线故障（AD-25），不参与差异计算
MIN_BYTES = 2000
# 单通道差 > 该阈值视为「显著变化像素」
SIG_THR = 12


def compare(a: Path, b: Path) -> tuple[float, float] | None:
    """返回 (平均像素差, 显著变化像素占比)。任一帧异常/尺寸不符 → None。"""
    try:
        if a.stat().st_size < MIN_BYTES or b.stat().st_size < MIN_BYTES:
            return None
        ia = Image.open(a).convert("RGB")
        ib = Image.open(b).convert("RGB")
        if ia.size != ib.size:
            return None
        diff = ImageChops.difference(ia, ib)
        px = list(diff.getdata())
        total = len(px)
        if total == 0:
            return None
        mean = sum(sum(p) / 3 for p in px) / total
        sig = sum(1 for p in px if max(p) > SIG_THR) / total
        return mean, sig
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="output/ui-baseline")
    args = ap.parse_args()
    root = Path(args.root)
    pre, after = root / "baseline-pre-a3", root / "after-a3"
    if not pre.is_dir() or not after.is_dir():
        print(f"[FAIL] 基线目录缺失: pre={pre.exists()} after={after.exists()}")
        return 1

    pre_rel = sorted(p.relative_to(pre).as_posix() for p in pre.rglob("*.png"))
    after_rel = sorted(p.relative_to(after).as_posix() for p in after.rglob("*.png"))
    print(f"pre-a3 帧数 = {len(pre_rel)}   after-a3 帧数 = {len(after_rel)}")
    print("=" * 78)
    print(f"{'cell':44s} {'平均像素差':>10s} {'显著变化占比':>12s}")
    print("-" * 78)
    for rel in after_rel:
        if rel not in pre_rel:
            print(f"{rel:44s} {'仅 after 存在':>10s}")
            continue
        r = compare(after / rel, pre / rel)
        if r is None:
            print(f"{rel:44s} {'故障帧已跳过':>10s}")
        else:
            mean, sig = r
            print(f"{rel:44s} {mean:10.2f} {sig * 100:11.2f}%")

    missing = [c for c in pre_rel if c not in after_rel]
    print("=" * 78)
    if missing:
        print(f"after 缺失 {len(missing)} 帧（重采样被模拟器渲染故障阻断，AD-25 待设备恢复重跑）：")
        for m in missing:
            print(f"  - {m}")
    else:
        print("after 帧覆盖完整，无缺失")
    return 0


if __name__ == "__main__":
    sys.exit(main())
