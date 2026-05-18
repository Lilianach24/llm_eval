#!/usr/bin/env python3
"""写作助手测试与评测最小可运行项目。

功能：
1) 交互式写作助手（mock 或 OpenAI 兼容接口）
2) 批量评测（从 tests/writing_cases.jsonl 读取样本）
3) 输出 JSON 报告（通过率、格式合规率、平均延迟）
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "你是一个专业中文写作助手。请严格按用户要求输出，"
    "语言清晰、结构完整，必要时使用分点。"
)


@dataclass
class EvalCase:
    case_id: str
    prompt: str
    must_include: List[str]
    max_chars: int


class LLMClient:
    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model

    def generate(self, prompt: str) -> str:
        if self.provider == "mock":
            return self._mock_generate(prompt)
        if self.provider == "openai":
            return self._openai_generate(prompt)
        raise ValueError(f"不支持 provider: {self.provider}")

    def _mock_generate(self, prompt: str) -> str:
        # 保证在离线环境可运行。
        return (
            "【标题】高效写作三步法\n"
            "1. 明确读者与目标：先写一句‘这篇文章帮谁解决什么问题’。\n"
            "2. 先搭结构再填内容：按‘问题-分析-建议’组织段落。\n"
            "3. 结尾给行动建议：提供可执行清单，提升转化。\n\n"
            f"参考你的需求：{prompt[:80]}"
        )

    def _openai_generate(self, prompt: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("缺少 OPENAI_API_KEY 环境变量")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()


def load_cases(path: Path) -> List[EvalCase]:
    cases: List[EvalCase] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            cases.append(
                EvalCase(
                    case_id=raw["case_id"],
                    prompt=raw["prompt"],
                    must_include=raw.get("must_include", []),
                    max_chars=int(raw.get("max_chars", 1200)),
                )
            )
    return cases


def check_case(case: EvalCase, answer: str) -> Dict[str, Any]:
    includes_ok = all(token in answer for token in case.must_include)
    length_ok = len(answer) <= case.max_chars
    passed = includes_ok and length_ok
    return {
        "case_id": case.case_id,
        "passed": passed,
        "includes_ok": includes_ok,
        "length_ok": length_ok,
        "answer_chars": len(answer),
        "must_include": case.must_include,
    }


def run_eval(client: LLMClient, case_path: Path, report_path: Path) -> Dict[str, Any]:
    cases = load_cases(case_path)
    results = []
    latencies = []

    for case in cases:
        start = time.perf_counter()
        answer = client.generate(case.prompt)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

        res = check_case(case, answer)
        res["latency_ms"] = round(latency, 2)
        results.append(res)

    pass_rate = sum(1 for r in results if r["passed"]) / max(len(results), 1)
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "pass_rate": round(pass_rate, 4),
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0,
        "p95_latency_ms": round(sorted(latencies)[int(0.95 * (len(latencies)-1))], 2) if latencies else 0,
    }

    report = {"summary": summary, "results": results}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def interactive_chat(client: LLMClient) -> None:
    print("写作助手已启动，输入 q 退出。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in {"q", "quit", "exit"}:
            print("再见！")
            return
        if not user_input:
            continue
        answer = client.generate(user_input)
        print(f"\n助手：\n{answer}")


def main() -> None:
    parser = argparse.ArgumentParser(description="写作助手测试项目（可运行）")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"], help="模型提供方")
    parser.add_argument("--model", default="gpt-4.1-mini", help="模型名称（provider=openai 时生效）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    eval_cmd = sub.add_parser("eval", help="运行批量评测")
    eval_cmd.add_argument("--cases", default="tests/writing_cases.jsonl", help="测试集路径")
    eval_cmd.add_argument("--report", default="reports/latest_report.json", help="评测报告输出路径")

    sub.add_parser("chat", help="启动交互式写作助手")

    args = parser.parse_args()
    client = LLMClient(provider=args.provider, model=args.model)

    if args.cmd == "chat":
        interactive_chat(client)
    else:
        report = run_eval(client, Path(args.cases), Path(args.report))
        print("评测完成：")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        print(f"详细结果已写入: {args.report}")


if __name__ == "__main__":
    main()
