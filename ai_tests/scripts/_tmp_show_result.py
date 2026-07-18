#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(__file__).parent.parent.parent / "output" / "rss" / "subagent_manual_analysis.json"
d = json.load(open(p, "r", encoding="utf-8"))
print("=== summary ===")
for k, v in d.items():
    if k != "results":
        print(f"  {k}: {v}")
print(f"\n=== results ({len(d['results'])} items) ===")
for r in d["results"]:
    print(f"  idx={r['idx']:3d} method={r['recovered_method']:14s} acc={str(r['accessible']):5s} type={r['type']} conf={r['confidence']:.2f} err={r['error_type']:25s} notes={r['analysis_notes'][:50]}")
