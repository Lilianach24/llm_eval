#!/usr/bin/env python3
"""自动化回归脚本：执行评测并输出分层统计。"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def run_eval(provider: str, model: str, cases: str, report: str) -> None:
    cmd = [
        "python3",
        "app.py",
        "--provider",
        provider,
        "--model",
        model,
        "eval",
        "--cases",
        cases,
        "--report",
        report,
    ]
    subprocess.run(cmd, check=True)


def load_cases(case_path: Path) -> Dict[str, dict]:
    mapping: Dict[str, dict] = {}
    for line in case_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        mapping[obj["case_id"]] = obj
    return mapping


def summarize(report: dict, case_meta: Dict[str, dict]) -> Tuple[dict, dict]:
    by_diff = defaultdict(lambda: Counter(total=0, passed=0))
    by_tag = defaultdict(lambda: Counter(total=0, passed=0))

    for r in report.get("results", []):
        cid = r["case_id"]
        passed = bool(r["passed"])
        meta = case_meta.get(cid, {})
        diff = meta.get("difficulty", "UNKNOWN")
        tags = meta.get("tags", ["untagged"])

        by_diff[diff]["total"] += 1
        by_diff[diff]["passed"] += int(passed)

        for t in tags:
            by_tag[t]["total"] += 1
            by_tag[t]["passed"] += int(passed)

    def with_rate(cntr_map):
        out = {}
        for k, v in sorted(cntr_map.items()):
            total = v["total"]
            passed = v["passed"]
            out[k] = {
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / total, 4) if total else 0.0,
            }
        return out

    return with_rate(by_diff), with_rate(by_tag)


def main() -> None:
    parser = argparse.ArgumentParser(description="自动化回归：评测 + 分层统计")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--cases", default="tests/writing_cases.jsonl")
    parser.add_argument("--report", default="reports/latest_report.json")
    parser.add_argument("--out", default="reports/regression_summary.json")
    args = parser.parse_args()

    run_eval(args.provider, args.model, args.cases, args.report)

    case_meta = load_cases(Path(args.cases))
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    by_diff, by_tag = summarize(report, case_meta)

    summary = {
        "base_summary": report.get("summary", {}),
        "by_difficulty": by_diff,
        "by_tag": by_tag,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("回归完成：")
    print(json.dumps(summary["base_summary"], ensure_ascii=False, indent=2))
    print(f"分层统计已写入: {args.out}")


if __name__ == "__main__":
    main()
