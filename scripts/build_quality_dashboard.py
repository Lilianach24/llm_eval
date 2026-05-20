#!/usr/bin/env python3
"""质量看板数据聚合脚本。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def main() -> None:
    latest = load_json(Path("reports/latest_report.json"))
    reg = load_json(Path("reports/regression_summary.json"))
    v2 = load_json(Path("reports/v2_eval_report.json"))
    fact = load_json(Path("reports/fact_check_report.json"))

    snapshot = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "base": latest.get("summary", {}),
        "regression": reg.get("base_summary", {}),
        "v2": v2.get("summary_by_model", {}),
        "cross_model_disagreement": v2.get("cross_model_disagreement", 0.0),
        "fact_check": fact.get("summary", {}),
    }
    out = Path("reports/dashboard_snapshot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"dashboard snapshot written: {out}")


if __name__ == "__main__":
    main()
