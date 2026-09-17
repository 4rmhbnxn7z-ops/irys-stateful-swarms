#!/usr/bin/env python3
"""DELTA benchmark judge -- scores answers against binary criteria.

Implements the judge protocol: multiple independent judges from different
model families, each grading blind. Disagreements on task pass/fail are
flagged for review.

Usage:
  python judge_delta.py --answers results/answers_run1.jsonl --output results/scores_run1.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from google import genai
from google.genai import types as genai_types

ROOT = Path(__file__).resolve().parent
TASKS_JSONL = ROOT / "data" / "tasks.jsonl"

JUDGE_SYSTEM = (
    "You are a legal evaluation judge. You will be given a legal answer "
    "and a single binary pass/fail criterion. Determine whether the answer "
    "meets the criterion.\n\n"
    "Rules:\n"
    "- Apply the criterion exactly as written; do not introduce unstated preferences.\n"
    "- Grade blind to the system that produced the answer.\n"
    "- Dutch text (pass_criteria.nl) is normative; use the English translation "
    "only as a reference.\n"
    "- Accommodate defensible legal approaches -- do not auto-fail novel but "
    "correct reasoning.\n"
    "- Respond with ONLY a JSON object: {\"verdict\": \"PASS\" or \"FAIL\", "
    "\"reasoning\": \"one sentence\"}"
)

JUDGE_MODEL = os.environ.get("DELTA_JUDGE_MODEL", "gemini-3.5-flash-lite")


def make_client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    http_options = genai_types.HttpOptions(timeout=180_000)
    if key:
        return genai.Client(api_key=key, http_options=http_options)
    return genai.Client(http_options=http_options)


def load_tasks_index() -> dict[str, dict]:
    index = {}
    with open(TASKS_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                task = json.loads(line)
                index[task["task_id"]] = task
    return index


def load_answers(path: str) -> list[dict]:
    answers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                answers.append(json.loads(line))
    return answers


def judge_criterion(client: genai.Client, answer_text: str,
                    criterion: dict, model: str) -> dict:
    cid = criterion["id"]
    ctype = criterion["type"]
    pass_nl = criterion["pass_criteria"]["nl"]
    pass_en = criterion["pass_criteria"]["en"]

    user_msg = (
        f"## Answer to evaluate\n\n{answer_text}\n\n"
        f"## Criterion {cid} ({ctype})\n\n"
        f"**Dutch (normative):** {pass_nl}\n\n"
        f"**English (reference):** {pass_en}\n\n"
        f"Does the answer meet this criterion? Respond with JSON only."
    )

    config = genai_types.GenerateContentConfig(
        system_instruction=JUDGE_SYSTEM,
        max_output_tokens=256,
        temperature=0.0,
        response_mime_type="application/json",
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_msg,
                config=config,
            )
            text = (response.text or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(text)
            return {
                "criterion_id": cid,
                "type": ctype,
                "verdict": result.get("verdict", "FAIL"),
                "reasoning": result.get("reasoning", ""),
                "judge_model": model,
            }
        except (json.JSONDecodeError, Exception) as e:
            if attempt < 2:
                time.sleep(5 * (2 ** attempt))
                continue
            return {
                "criterion_id": cid,
                "type": ctype,
                "verdict": "ERROR",
                "reasoning": str(e),
                "judge_model": model,
            }
    return {
        "criterion_id": cid,
        "type": ctype,
        "verdict": "ERROR",
        "reasoning": "max retries exceeded",
        "judge_model": model,
    }


def score_answer(client: genai.Client, answer: dict, task: dict,
                 judge_model: str) -> dict:
    criteria = task.get("criteria", [])
    answer_text = answer.get("answer", "")
    if not answer_text:
        return {
            "task_id": answer["task_id"],
            "run": answer.get("run"),
            "system": answer.get("system"),
            "judge_model": judge_model,
            "criteria_results": [
                {"criterion_id": c["id"], "type": c["type"],
                 "verdict": "FAIL", "reasoning": "empty answer"}
                for c in criteria
            ],
            "criteria_met": 0,
            "criteria_total": len(criteria),
            "criteria_pct": 0.0,
            "task_pass": False,
        }

    results = []
    for criterion in criteria:
        r = judge_criterion(client, answer_text, criterion, judge_model)
        results.append(r)

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    total = len(criteria)

    by_type: dict[str, dict] = {}
    for r in results:
        ct = r["type"]
        if ct not in by_type:
            by_type[ct] = {"passed": 0, "total": 0}
        by_type[ct]["total"] += 1
        if r["verdict"] == "PASS":
            by_type[ct]["passed"] += 1

    return {
        "task_id": answer["task_id"],
        "run": answer.get("run"),
        "system": answer.get("system"),
        "judge_model": judge_model,
        "criteria_results": results,
        "criteria_met": passed,
        "criteria_total": total,
        "criteria_pct": round(100.0 * passed / total, 1) if total else 0.0,
        "task_pass": passed == total,
        "by_type": {
            k: {**v, "pct": round(100.0 * v["passed"] / v["total"], 1) if v["total"] else 0.0}
            for k, v in by_type.items()
        },
    }


def summarize(scores: list[dict]) -> None:
    total_criteria_met = sum(s["criteria_met"] for s in scores)
    total_criteria = sum(s["criteria_total"] for s in scores)
    tasks_passed = sum(1 for s in scores if s["task_pass"])

    print("\n" + "=" * 60)
    print("DELTA BENCHMARK RESULTS")
    print("=" * 60)
    print(f"  Tasks:        {len(scores)}")
    print(f"  Criteria met: {total_criteria_met}/{total_criteria} "
          f"({100.0 * total_criteria_met / total_criteria:.1f}%)")
    print(f"  Task pass:    {tasks_passed}/{len(scores)} "
          f"({100.0 * tasks_passed / len(scores):.1f}%)")

    type_agg: dict[str, dict] = {}
    for s in scores:
        for ct, vals in s.get("by_type", {}).items():
            if ct not in type_agg:
                type_agg[ct] = {"passed": 0, "total": 0}
            type_agg[ct]["passed"] += vals["passed"]
            type_agg[ct]["total"] += vals["total"]

    print("\n  By criterion type:")
    for ct in ("substance", "citation", "form"):
        if ct in type_agg:
            v = type_agg[ct]
            pct = 100.0 * v["passed"] / v["total"] if v["total"] else 0.0
            print(f"    {ct:12s}: {v['passed']:3d}/{v['total']:3d} ({pct:.1f}%)")

    print("\n  Per task:")
    for s in scores:
        status = "PASS" if s["task_pass"] else "FAIL"
        print(f"    {s['task_id']:60s} {s['criteria_met']:2d}/{s['criteria_total']:2d} "
              f"({s['criteria_pct']:5.1f}%) [{status}]")
    print()


def main():
    parser = argparse.ArgumentParser(description="Judge DELTA answers")
    parser.add_argument("--answers", type=str, required=True,
                        help="Path to answers JSONL from run_delta.py")
    parser.add_argument("--output", type=str, default=None,
                        help="Output scores JSONL (default: results/scores_run{N}.jsonl)")
    parser.add_argument("--judge-model", type=str, default=None,
                        help=f"Judge model override (default: {JUDGE_MODEL})")
    parser.add_argument("--task", type=str, default=None,
                        help="Score a single task only")
    args = parser.parse_args()

    judge_model = args.judge_model or JUDGE_MODEL

    tasks_index = load_tasks_index()
    answers = load_answers(args.answers)

    if args.task:
        answers = [a for a in answers if a["task_id"] == args.task]

    run_num = answers[0].get("run", 1) if answers else 1
    output = args.output or f"results/scores_run{run_num}.jsonl"
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    existing = set()
    if os.path.exists(output):
        with open(output, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    existing.add(rec["task_id"])

    client = make_client()
    print(f"DELTA judge -- model={judge_model}, {len(answers)} answers\n")

    all_scores = []
    for i, answer in enumerate(answers):
        tid = answer["task_id"]
        if tid in existing:
            print(f"  [{i+1}/{len(answers)}] {tid} -- skipped (already scored)")
            continue
        if tid not in tasks_index:
            print(f"  [{i+1}/{len(answers)}] {tid} -- task not found, skipping")
            continue

        task = tasks_index[tid]
        n_criteria = len(task.get("criteria", []))
        print(f"  [{i+1}/{len(answers)}] {tid} ({n_criteria} criteria)...",
              end=" ", flush=True)

        score = score_answer(client, answer, task, judge_model)
        all_scores.append(score)

        with open(output, "a", encoding="utf-8") as f:
            f.write(json.dumps(score, ensure_ascii=False) + "\n")

        print(f"{score['criteria_met']}/{score['criteria_total']} "
              f"({'PASS' if score['task_pass'] else 'FAIL'})")

    if not all_scores and existing:
        with open(output, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_scores.append(json.loads(line))

    if all_scores:
        summarize(all_scores)


if __name__ == "__main__":
    main()
