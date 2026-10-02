"""
LocalQuery Evaluation Benchmark
=================================
Measures accuracy, latency, and memory footprint of the full pipeline
across a set of representative NL → SQL test cases.

Usage::

    python eval/run_benchmark.py
    python eval/run_benchmark.py --model qwen2.5-coder:7b
    python eval/run_benchmark.py --db data/hr.db --model llama3.2:3b

The benchmark uses *exact-match* SQL comparison (case-insensitive, no trailing
semicolon) for non-ambiguous queries, and checks the clarification question
for ambiguous queries.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List

# Allow running from the project root without pip install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import psutil

from localquery.db.schema import setup_db
from localquery.orchestration.pipeline import LocalQueryPipeline

# ---------------------------------------------------------------------------
# Default test suite against the finance.db demo database
# ---------------------------------------------------------------------------

FINANCE_TEST_CASES: List[Dict[str, Any]] = [
    {
        "query": "Show me all active users",
        "type": "simple_filter",
        "expected_sql": "SELECT * FROM users WHERE status = 'active'",
        "expected_clarification": None,
    },
    {
        "query": "What is the total balance of all checking accounts?",
        "type": "aggregation",
        "expected_sql": "SELECT SUM(balance) FROM accounts WHERE account_type = 'checking'",
        "expected_clarification": None,
    },
    {
        "query": "How much revenue did we make?",
        "type": "ambiguous_money",
        "expected_sql": None,
        "expected_clarification": (
            "When you say 'revenue/income', are you looking for the "
            "gross total, or the net after expenses?"
        ),
    },
    {
        "query": "List transactions for Charlie Brown",
        "type": "join",
        "expected_sql": (
            "SELECT t.* FROM transactions t "
            "JOIN accounts a ON t.account_id = a.account_id "
            "JOIN users u ON a.user_id = u.user_id "
            "WHERE u.first_name = 'Charlie' AND u.last_name = 'Brown'"
        ),
        "expected_clarification": None,
    },
    {
        "query": "Show recent transactions",
        "type": "ambiguous_time",
        "expected_sql": None,
        "expected_clarification": (
            "By 'recent', do you mean the last 30 days, "
            "or a different time period?"
        ),
    },
    {
        "query": "How many users signed up in 2023?",
        "type": "aggregation_with_filter",
        "expected_sql": (
            "SELECT COUNT(*) FROM users "
            "WHERE signup_date >= '2023-01-01' AND signup_date < '2024-01-01'"
        ),
        "expected_clarification": None,
    },
]


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def _normalise_sql(sql: str) -> str:
    """Lowercase, strip trailing semicolons and extra whitespace."""
    return " ".join(sql.lower().replace(";", "").split())


def run_benchmark(model_name: str, db_path: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Run the full benchmark suite against *db_path* with *model_name*.

    Returns a summary dict.
    """
    print(f"\n{'='*60}")
    print(f"  LocalQuery Benchmark")
    print(f"  Model : {model_name}")
    print(f"  DB    : {db_path}")
    print(f"{'='*60}\n")

    pipeline = LocalQueryPipeline(db_path=db_path, model_name=model_name)
    results = []

    for i, test in enumerate(FINANCE_TEST_CASES, 1):
        print(f"[{i}/{len(FINANCE_TEST_CASES)}] {test['type']}: {test['query']}")

        mem_before = psutil.virtual_memory().used
        t0 = time.perf_counter()

        result = pipeline.process_query(test["query"])

        latency = time.perf_counter() - t0
        mem_delta_mb = max(0, psutil.virtual_memory().used - mem_before) / (1024 ** 2)

        # Evaluate correctness
        correct = False
        if test["expected_clarification"]:
            correct = (
                result["status"] == "needs_clarification"
                and result["clarification_question"] == test["expected_clarification"]
            )
        elif result["status"] == "success" and result["sql"]:
            gen = _normalise_sql(result["sql"])
            exp = _normalise_sql(test["expected_sql"])
            correct = gen == exp

        status_icon = "✓" if correct else "✗"
        if verbose:
            print(f"  {status_icon} Latency: {latency:.2f}s | Mem Δ: {mem_delta_mb:.1f} MB")
            if not correct and result.get("sql"):
                print(f"    Expected: {test['expected_sql']}")
                print(f"    Got     : {result['sql']}")
            elif not correct and result.get("clarification_question"):
                print(f"    Expected clarification: {test['expected_clarification']}")
                print(f"    Got                   : {result['clarification_question']}")
            print()

        results.append({"latency": latency, "correct": correct, "mem_mb": mem_delta_mb})

    # Summary
    n = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    avg_latency = sum(r["latency"] for r in results) / n
    avg_mem = sum(r["mem_mb"] for r in results) / n

    print(f"\n{'─'*60}")
    print(f"  Accuracy      : {n_correct}/{n}  ({n_correct / n * 100:.1f}%)")
    print(f"  Avg Latency   : {avg_latency:.2f}s")
    print(f"  Avg Mem Delta : {avg_mem:.1f} MB")
    print(f"{'─'*60}\n")

    return {
        "model": model_name,
        "db": db_path,
        "accuracy": n_correct / n,
        "avg_latency": avg_latency,
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LocalQuery benchmark — evaluate NL→SQL accuracy and latency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LOCALQUERY_MODEL", "qwen2.5-coder:3b"),
        help="Ollama model name (default: qwen2.5-coder:3b)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database (default: finance.db in project root)",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()

    # Resolve default DB path relative to the project root
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if args.db:
        db_path = args.db
    else:
        db_path = os.path.join(_project_root, "finance.db")
        setup_db(db_path)

    if not os.path.exists(db_path):
        print(f"[Error] Database not found: {db_path}")
        sys.exit(1)

    run_benchmark(model_name=args.model, db_path=db_path)
