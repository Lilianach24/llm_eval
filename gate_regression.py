#!/usr/bin/env python3
"""第三阶段：回归门禁检查（阈值 + 基线对比）。"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run_regression(provider: str, model: str, cases: str, out: str, failed_out: str) -> None:
    cmd = [
        "python",
        "run_regression.py",
        "--provider",
        provider,
        "--model",
        model,
        "--cases",
        cases,
        "--out",
        out,
        "--failed-out",
        failed_out,
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="回归门禁：阈值检查 + 基线对比")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--cases", default="tests/writing_cases.jsonl")
    parser.add_argument("--out", default="reports/regression_summary.json")
    parser.add_argument("--failed-out", default="reports/failed_cases.json")
    parser.add_argument("--baseline", default="reports/baseline_regression_summary.json")
    parser.add_argument("--min-pass-rate", type=float, default=0.80)
    parser.add_argument("--max-regression", type=float, default=0.03, help="允许相对基线下降幅度")
    args = parser.parse_args()

    run_regression(args.provider, args.model, args.cases, args.out, args.failed_out)

    cur = json.loads(Path(args.out).read_text(encoding="utf-8"))
    cur_rate = float(cur.get("base_summary", {}).get("pass_rate", 0.0))

    errors = []
    if cur_rate < args.min_pass_rate:
        errors.append(f"当前 pass_rate={cur_rate:.4f} 低于阈值 {args.min_pass_rate:.4f}")

    baseline_path = Path(args.baseline)
    if baseline_path.exists():
        base = json.loads(baseline_path.read_text(encoding="utf-8"))
        base_rate = float(base.get("base_summary", {}).get("pass_rate", 0.0))
        drop = base_rate - cur_rate
        if drop > args.max_regression:
            errors.append(f"相对基线退化 {drop:.4f} 超过允许值 {args.max_regression:.4f}（baseline={base_rate:.4f}, current={cur_rate:.4f}）")
    else:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"未检测到基线，已初始化: {baseline_path}")

    if errors:
        print("门禁失败：")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("门禁通过。")


if __name__ == "__main__":
    main()
