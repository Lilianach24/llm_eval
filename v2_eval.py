#!/usr/bin/env python3
"""V2 增强评测：并发调用、多模型交叉验证、不一致性/合规率/ECE统计。"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from app import LLMClient, load_cases, check_case


def confidence_proxy(answer: str, must_include: List[str], max_chars: int) -> float:
    """启发式置信度代理（0~1），用于近似 ECE。"""
    score = 0.5
    if must_include:
        hit = sum(1 for t in must_include if t in answer) / len(must_include)
        score += 0.35 * hit
    if len(answer) <= max_chars:
        score += 0.15
    else:
        overflow_ratio = min((len(answer) - max_chars) / max_chars, 1.0)
        score -= 0.2 * overflow_ratio
    return max(0.0, min(1.0, score))


def ece(rows: List[Dict[str, Any]], bins: int = 10) -> float:
    if not rows:
        return 0.0
    bucket = [[] for _ in range(bins)]
    for r in rows:
        conf = float(r["confidence"])
        idx = min(int(conf * bins), bins - 1)
        bucket[idx].append(r)

    total = len(rows)
    acc = 0.0
    for b in bucket:
        if not b:
            continue
        avg_conf = statistics.mean(float(x["confidence"]) for x in b)
        avg_acc = statistics.mean(1.0 if x["passed"] else 0.0 for x in b)
        acc += abs(avg_conf - avg_acc) * (len(b) / total)
    return round(acc, 6)


def run_one(client: LLMClient, case) -> Dict[str, Any]:
    st = time.perf_counter()
    answer = client.generate(case.prompt)
    latency = (time.perf_counter() - st) * 1000
    base = check_case(case, answer)
    base["latency_ms"] = round(latency, 2)
    base["answer"] = answer
    return base


def concurrent_eval(client: LLMClient, cases: List, workers: int) -> List[Dict[str, Any]]:
    results = [None] * len(cases)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut_map = {ex.submit(run_one, client, c): i for i, c in enumerate(cases)}
        for fut in as_completed(fut_map):
            i = fut_map[fut]
            results[i] = fut.result()
    return results


def disagreement_rate(per_model: Dict[str, List[Dict[str, Any]]]) -> float:
    names = list(per_model.keys())
    if len(names) < 2:
        return 0.0
    n = len(per_model[names[0]])
    disagree = 0
    for i in range(n):
        vals = [per_model[m][i]["passed"] for m in names]
        if any(v != vals[0] for v in vals[1:]):
            disagree += 1
    return round(disagree / n, 4) if n else 0.0


def main() -> None:
    p = argparse.ArgumentParser(description="V2增强评测")
    p.add_argument("--provider", default="mock", choices=["mock", "openai"])
    p.add_argument("--models", default="gpt-4.1-mini", help="逗号分隔模型列表，用于交叉验证")
    p.add_argument("--cases", default="tests/writing_cases.jsonl")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default="reports/v2_eval_report.json")
    args = p.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    cases = load_cases(Path(args.cases))

    per_model: Dict[str, List[Dict[str, Any]]] = {}
    for m in models:
        client = LLMClient(provider=args.provider, model=m)
        rows = concurrent_eval(client, cases, args.workers)
        for row, case in zip(rows, cases):
            row["difficulty"] = getattr(case, "difficulty", "UNKNOWN") if hasattr(case, "difficulty") else "UNKNOWN"
            row["confidence"] = confidence_proxy(row["answer"], row.get("must_include", []), case.max_chars)
            row["compliance"] = bool(row["includes_ok"] and row["length_ok"])
        per_model[m] = rows

    summary_models = {}
    for m, rows in per_model.items():
        total = len(rows)
        passed = sum(1 for r in rows if r["passed"])
        compliance = sum(1 for r in rows if r["compliance"])
        lat = [r["latency_ms"] for r in rows]
        summary_models[m] = {
            "total": total,
            "passed": passed,
            "accuracy": round(passed / total, 4) if total else 0.0,
            "compliance_rate": round(compliance / total, 4) if total else 0.0,
            "ece": ece(rows),
            "avg_latency_ms": round(statistics.mean(lat), 2) if lat else 0.0,
        }

    report = {
        "meta": {"provider": args.provider, "models": models, "workers": args.workers},
        "summary_by_model": summary_models,
        "cross_model_disagreement": disagreement_rate(per_model),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"V2 报告已写入: {args.out}")


if __name__ == "__main__":
    main()
