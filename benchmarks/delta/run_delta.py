#!/usr/bin/env python3
"""DELTA benchmark harness — multi-provider with model-agnostic search.

Runs tasks through an agentic loop with web search (Exa), producing
answers.jsonl in the DELTA harness protocol format.

Supports Gemini, Anthropic (Claude), and OpenAI (GPT/Astra) models via --model flag.
Provider auto-detected from model name: claude-* -> Anthropic, gpt-*/o3*/o4* -> OpenAI,
everything else -> Gemini.

Usage:
  python run_delta.py --run 1 --output results/answers_run1.jsonl
  python run_delta.py --run 1 --model gpt-6-astra --output results/answers_astra.jsonl
  python run_delta.py --run 1 --no-search --output results/answers_nosearch.jsonl
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

from exa_py import Exa

ROOT = Path(__file__).resolve().parent
TASKS_JSONL = ROOT / "data" / "tasks.jsonl"
DATASET_VERSION = "1.1.0"

SYSTEM_PROMPT = (
    "You are a senior expert producing the deliverable named in the user's "
    "instructions. Return the deliverable as the body of your reply in plain "
    "text or markdown (do NOT base64-encode or attach a file). Aim for the "
    "quality and detail expected of a domain specialist."
)

SYSTEM_PROMPT_WITH_SEARCH = (
    "You are a senior expert producing the deliverable named in the user's "
    "instructions. Return the deliverable as the body of your reply in plain "
    "text or markdown (do NOT base64-encode or attach a file). Aim for the "
    "quality and detail expected of a domain specialist.\n\n"
    "You have access to a search tool. Use it to research the question "
    "before answering. Search multiple times if needed — once for the "
    "general framework and again for specific authorities, references, or "
    "sources you want to cite. Verify any citation you are unsure of rather "
    "than guessing. Be precise: exact reference numbers, identifiers, and "
    "dates."
)

MODEL = os.environ.get("DELTA_MODEL", "gemini-3.7-flash")
SYSTEM_NAME = os.environ.get("DELTA_SYSTEM", "irys-swarm")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")

PRICE_SEARCH = float(os.environ.get("DELTA_PRICE_SEARCH", "0.001"))
MAX_TOOL_ROUNDS = 8

PRICING = {
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "claude-fable-5-1": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "gpt-5.5": (2.00, 8.00),
    "gpt-6-astra": (5.00, 20.00),
}


def detect_provider(model: str) -> str:
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith(("gpt-", "o3", "o4")):
        return "openai"
    return "gemini"


def get_pricing(model: str) -> tuple[float, float]:
    if model in PRICING:
        return PRICING[model]
    provider = detect_provider(model)
    if provider == "anthropic":
        return (3.00, 15.00)
    if provider == "openai":
        return (5.00, 20.00)
    return (0.75, 3.75)


def load_tasks() -> list[dict]:
    tasks = []
    with open(TASKS_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def do_search(exa: Exa, query: str) -> str:
    try:
        results = exa.search(
            query,
            num_results=5,
            text={"max_characters": 1500},
            type="neural",
        )
        parts = []
        for r in results.results:
            parts.append(f"### {r.title}\n**URL:** {r.url}\n\n{r.text}\n")
        return "\n---\n".join(parts) if parts else "No results found."
    except Exception as e:
        return f"Search error: {e}"


# --------------- Gemini provider ---------------

def _make_gemini_client():
    from google import genai
    from google.genai import types as genai_types
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    http_options = genai_types.HttpOptions(timeout=180_000)
    if key:
        return genai.Client(api_key=key, http_options=http_options)
    return genai.Client(http_options=http_options)


def run_gemini_with_search(task: dict, exa: Exa, *, model: str) -> dict:
    from google import genai
    from google.genai import types as genai_types

    search_decl = genai_types.FunctionDeclaration(
        name="search",
        description="Search the web for authoritative sources, references, and academic materials. Returns titles, URLs, and text snippets.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in the language most likely to yield relevant results.",
                },
            },
            "required": ["query"],
        },
    )

    client = _make_gemini_client()
    tools = [genai_types.Tool(function_declarations=[search_decl])]
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT_WITH_SEARCH,
        max_output_tokens=16384,
        temperature=0.1,
        tools=tools,
    )

    contents = [genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=task["prompt"]["nl"])],
    )]

    total_in = total_out = search_calls = 0
    candidate = None
    t0 = time.perf_counter()

    for _round in range(MAX_TOOL_ROUNDS + 1):
        response = client.models.generate_content(
            model=model, contents=contents, config=config,
        )
        usage = response.usage_metadata
        total_in += getattr(usage, "prompt_token_count", 0)
        total_out += getattr(usage, "candidates_token_count", 0)

        candidate = response.candidates[0] if response.candidates else None
        if not candidate:
            break

        has_fc = False
        assistant_parts = []
        tool_parts = []

        for part in candidate.content.parts:
            assistant_parts.append(part)
            if part.function_call and part.function_call.name == "search":
                has_fc = True
                search_calls += 1
                result_text = do_search(exa, part.function_call.args.get("query", ""))
                tool_parts.append(genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name="search", response={"results": result_text},
                    )
                ))

        contents.append(genai_types.Content(role="model", parts=assistant_parts))
        if not has_fc:
            break
        contents.append(genai_types.Content(role="user", parts=tool_parts))

    latency = time.perf_counter() - t0
    final_text = ""
    if candidate:
        for part in candidate.content.parts:
            if part.text:
                final_text += part.text

    return _make_record(task, model, final_text, total_in, total_out,
                        search_calls, _round + 1, latency,
                        str(candidate.finish_reason) if candidate else "unknown")


def run_gemini_no_search(task: dict, *, model: str) -> dict:
    from google.genai import types as genai_types

    client = _make_gemini_client()
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=16384,
        temperature=0.1,
    )

    t0 = time.perf_counter()
    response = client.models.generate_content(
        model=model, contents=task["prompt"]["nl"], config=config,
    )
    latency = time.perf_counter() - t0

    usage = response.usage_metadata
    total_in = getattr(usage, "prompt_token_count", 0)
    total_out = getattr(usage, "candidates_token_count", 0)

    return _make_record(task, model, response.text or "", total_in, total_out,
                        0, 1, latency,
                        str(response.candidates[0].finish_reason) if response.candidates else "unknown")


# --------------- Anthropic provider ---------------

def _make_anthropic_client():
    import anthropic
    return anthropic.Anthropic()


ANTHROPIC_SEARCH_TOOL = {
    "name": "search",
    "description": "Search the web for authoritative sources, references, and academic materials. Returns titles, URLs, and text snippets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query in the language most likely to yield relevant results.",
            },
        },
        "required": ["query"],
    },
}


def run_anthropic_with_search(task: dict, exa: Exa, *, model: str) -> dict:
    client = _make_anthropic_client()
    messages = [{"role": "user", "content": task["prompt"]["nl"]}]

    total_in = total_out = search_calls = 0
    t0 = time.perf_counter()
    final_text = ""
    finish_reason = "unknown"

    for _round in range(MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model=model,
            max_tokens=16384,
            temperature=0.1,
            system=SYSTEM_PROMPT_WITH_SEARCH,
            tools=[ANTHROPIC_SEARCH_TOOL],
            messages=messages,
        )

        total_in += response.usage.input_tokens
        total_out += response.usage.output_tokens
        finish_reason = response.stop_reason or "unknown"

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in assistant_content:
            if block.type == "text":
                final_text = block.text
            elif block.type == "tool_use" and block.name == "search":
                search_calls += 1
                result_text = do_search(exa, block.input.get("query", ""))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        if not tool_results:
            break

        messages.append({"role": "user", "content": tool_results})

    latency = time.perf_counter() - t0
    return _make_record(task, model, final_text, total_in, total_out,
                        search_calls, _round + 1, latency, finish_reason)


def run_anthropic_no_search(task: dict, *, model: str) -> dict:
    client = _make_anthropic_client()

    t0 = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=16384,
        temperature=0.1,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": task["prompt"]["nl"]}],
    )
    latency = time.perf_counter() - t0

    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text

    return _make_record(task, model, text, response.usage.input_tokens,
                        response.usage.output_tokens, 0, 1, latency,
                        response.stop_reason or "unknown")


# --------------- OpenAI provider ---------------

def _make_openai_client():
    import openai
    return openai.OpenAI()


OPENAI_SEARCH_TOOL = {
    "type": "function",
    "name": "search",
    "description": "Search the web for authoritative sources, references, and academic materials. Returns titles, URLs, and text snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query in the language most likely to yield relevant results.",
            },
        },
        "required": ["query"],
    },
}


def run_openai_with_search(task: dict, exa: Exa, *, model: str) -> dict:
    client = _make_openai_client()
    input_items = [
        {"type": "message", "role": "developer", "content": SYSTEM_PROMPT_WITH_SEARCH},
        {"type": "message", "role": "user", "content": task["prompt"]["nl"]},
    ]

    total_in = total_out = search_calls = 0
    t0 = time.perf_counter()
    final_text = ""
    finish_reason = "unknown"

    prev_response_id = None
    for _round in range(MAX_TOOL_ROUNDS + 1):
        create_kwargs = {
            "model": model,
            "max_output_tokens": 16384,
            "tools": [OPENAI_SEARCH_TOOL],
        }
        if prev_response_id:
            create_kwargs["previous_response_id"] = prev_response_id
            create_kwargs["input"] = tool_outputs
        else:
            create_kwargs["input"] = input_items

        response = client.responses.create(**create_kwargs)
        prev_response_id = response.id

        total_in += response.usage.input_tokens
        total_out += response.usage.output_tokens
        finish_reason = response.status or "unknown"

        has_tool_call = False
        tool_outputs = []
        for item in response.output:
            if item.type == "message":
                for part in item.content:
                    if part.type == "output_text":
                        final_text = part.text
            elif item.type == "function_call" and item.name == "search":
                has_tool_call = True
                search_calls += 1
                args = json.loads(item.arguments)
                result_text = do_search(exa, args.get("query", ""))
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result_text,
                })

        if not has_tool_call:
            break

    latency = time.perf_counter() - t0
    return _make_record(task, model, final_text, total_in, total_out,
                        search_calls, _round + 1, latency, finish_reason)


def run_openai_no_search(task: dict, *, model: str) -> dict:
    client = _make_openai_client()

    t0 = time.perf_counter()
    response = client.responses.create(
        model=model,
        max_output_tokens=16384,
        input=[
            {"type": "message", "role": "developer", "content": SYSTEM_PROMPT},
            {"type": "message", "role": "user", "content": task["prompt"]["nl"]},
        ],
    )
    latency = time.perf_counter() - t0

    text = ""
    for item in response.output:
        if item.type == "message":
            for part in item.content:
                if part.type == "output_text":
                    text = part.text

    return _make_record(task, model, text, response.usage.input_tokens,
                        response.usage.output_tokens, 0, 1, latency,
                        response.status or "unknown")


# --------------- Shared ---------------

def _make_record(task, model, text, total_in, total_out, search_calls,
                 tool_rounds, latency, finish_reason) -> dict:
    price_in, price_out = get_pricing(model)
    cost_model = (total_in * price_in + total_out * price_out) / 1_000_000
    cost_search = search_calls * PRICE_SEARCH
    cost_total = cost_model + cost_search

    return {
        "task_id": task["task_id"],
        "dataset_version": DATASET_VERSION,
        "system": SYSTEM_NAME,
        "run": None,
        "answer": text.strip(),
        "metadata": {
            "model": model,
            "tokens_input": total_in,
            "tokens_output": total_out,
            "search_calls": search_calls,
            "tool_rounds": tool_rounds,
            "latency_seconds": round(latency, 2),
            "cost_model_usd": round(cost_model, 6),
            "cost_search_usd": round(cost_search, 6),
            "cost_total_usd": round(cost_total, 6),
            "finish_reason": finish_reason,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run DELTA benchmark")
    parser.add_argument("--run", type=int, required=True, choices=[1, 2],
                        help="Run number (protocol requires two independent runs)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSONL path (default: results/answers_run{N}.jsonl)")
    parser.add_argument("--model", type=str, default=None,
                        help=f"Model override (default: {MODEL})")
    parser.add_argument("--system-name", type=str, default=None,
                        help=f"System name (default: {SYSTEM_NAME})")
    parser.add_argument("--task", type=str, default=None,
                        help="Run a single task by ID (for debugging)")
    parser.add_argument("--no-search", action="store_true",
                        help="Disable search tool (raw model only)")
    args = parser.parse_args()

    model = args.model or MODEL
    system_name = args.system_name or SYSTEM_NAME
    use_search = not args.no_search
    output = args.output or f"results/answers_run{args.run}.jsonl"
    provider = detect_provider(model)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    tasks = load_tasks()
    if args.task:
        tasks = [t for t in tasks if t["task_id"] == args.task]
        if not tasks:
            print(f"Task {args.task!r} not found", file=sys.stderr)
            sys.exit(1)

    existing = set()
    if os.path.exists(output):
        with open(output, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.add(json.loads(line)["task_id"])
        print(f"Resuming: {len(existing)}/{len(tasks)} already completed")

    exa = Exa(api_key=EXA_API_KEY) if use_search else None

    mode = "search" if use_search else "no-search"
    print(f"DELTA benchmark -- run {args.run}, model={model}, provider={provider}, mode={mode}")
    print(f"{len(tasks)} tasks, output -> {output}\n")

    total_cost = 0.0
    for i, task in enumerate(tasks):
        tid = task["task_id"]
        if tid in existing:
            print(f"  [{i+1}/{len(tasks)}] {tid} -- skipped (already done)")
            continue

        print(f"  [{i+1}/{len(tasks)}] {tid}...", end=" ", flush=True)
        try:
            if provider == "anthropic":
                if use_search:
                    record = run_anthropic_with_search(task, exa, model=model)
                else:
                    record = run_anthropic_no_search(task, model=model)
            elif provider == "openai":
                if use_search:
                    record = run_openai_with_search(task, exa, model=model)
                else:
                    record = run_openai_no_search(task, model=model)
            else:
                if use_search:
                    record = run_gemini_with_search(task, exa, model=model)
                else:
                    record = run_gemini_no_search(task, model=model)

            record["run"] = args.run
            record["system"] = system_name

            with open(output, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            meta = record["metadata"]
            total_cost += meta["cost_total_usd"]
            searches = f", {meta['search_calls']} searches" if meta["search_calls"] else ""
            print(f"done ({meta['tokens_output']} tok, {meta['latency_seconds']}s, "
                  f"${meta['cost_total_usd']:.4f}{searches})")
        except Exception as e:
            error_record = {
                "task_id": tid,
                "dataset_version": DATASET_VERSION,
                "system": system_name,
                "run": args.run,
                "answer": "",
                "error": str(e),
            }
            with open(output, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_record, ensure_ascii=False) + "\n")
            print(f"ERROR: {e}")

    print(f"\nDone. Answers written to {output}")
    print(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
