#!/usr/bin/env python3
"""写作助手测试与评测最小可运行项目。"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import dotenv

dotenv.load_dotenv()

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

    def generate(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        if self.provider == "mock":
            return self._mock_generate(prompt)
        if self.provider == "openai":
            return self._openai_generate(prompt, history or [])
        raise ValueError(f"不支持 provider: {self.provider}")

    def _mock_generate(self, prompt: str) -> str:
        return (
            "【标题】高效写作三步法\n"
            "1. 明确读者与目标：先写一句‘这篇文章帮谁解决什么问题’。\n"
            "2. 先搭结构再填内容：按‘问题-分析-建议’组织段落。\n"
            "3. 结尾给行动建议：提供可执行清单，提升转化。\n\n"
            f"参考你的需求：{prompt[:80]}"
        )

    def _openai_generate(self, prompt: str, history: List[Dict[str, str]]) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.openai-proxy.org/v1").rstrip("/")
        if not api_key:
            raise RuntimeError(
                "缺少 ANTHROPIC_API_KEY 环境变量。\n"
                "PowerShell 请先执行：\n"
                "$env:ANTHROPIC_API_KEY='你的key'\n"
                "$env:ANTHROPIC_BASE_URL='https://api.openai-proxy.org/v1'"
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            raise RuntimeError(
                f"模型服务请求失败：HTTP {e.code} {e.reason}。\n"
                f"请求地址：{base_url}/chat/completions\n"
                "排查建议：\n"
                "1) 确认 ANTHROPIC_API_KEY 是否有效、未过期、未欠费；\n"
                "2) 确认 ANTHROPIC_BASE_URL 是否正确；\n"
                f"3) 确认模型名 `{self.model}` 在该平台可用。\n"
                f"服务返回：{detail[:300]}"
            ) from e

        choices = body.get("choices") if isinstance(body, dict) else None
        if not choices:
            raise RuntimeError(f"响应中缺少 choices 字段，原始响应：{json.dumps(body, ensure_ascii=False)[:500]}")
        return choices[0]["message"]["content"].strip()


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
        "p95_latency_ms": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 2) if latencies else 0,
    }

    report = {"summary": summary, "results": results}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def interactive_chat(client: LLMClient, max_history_turns: int) -> None:
    print("写作助手已启动，输入 q 退出，输入 /clear 清空上下文。")
    history: List[Dict[str, str]] = []
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in {"q", "quit", "exit"}:
            print("再见！")
            return
        if user_input == "/clear":
            history = []
            print("上下文已清空。")
            continue
        if not user_input:
            continue
        answer = client.generate(user_input, history=history)
        print(f"\n助手：\n{answer}")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})
        max_messages = max_history_turns * 2
        if len(history) > max_messages:
            history = history[-max_messages:]


def main() -> None:
    parser = argparse.ArgumentParser(description="写作助手测试项目（可运行）")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"], help="模型提供方")
    parser.add_argument("--model", default="gpt-4.1-mini", help="模型名称（provider=openai 时生效）")
    parser.add_argument("--max-history-turns", type=int, default=6, help="chat 模式保留的历史轮数")
    sub = parser.add_subparsers(dest="cmd", required=True)

    eval_cmd = sub.add_parser("eval", help="运行批量评测")
    eval_cmd.add_argument("--cases", default="tests/writing_cases.jsonl", help="测试集路径")
    eval_cmd.add_argument("--report", default="reports/latest_report.json", help="评测报告输出路径")

    sub.add_parser("chat", help="启动交互式写作助手")

    args = parser.parse_args()
    client = LLMClient(provider=args.provider, model=args.model)

    if args.cmd == "chat":
        interactive_chat(client, max_history_turns=max(0, args.max_history_turns))
    else:
        report = run_eval(client, Path(args.cases), Path(args.report))
        print("评测完成：")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        print(f"详细结果已写入: {args.report}")


if __name__ == "__main__":
    main()
