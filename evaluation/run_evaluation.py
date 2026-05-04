"""Run a reproducible local evaluation for the Math Similarity Solver Agent.

This script runs 10 fixed text queries through the LangGraph workflow,
stores detailed outputs, computes lightweight quality scores, and writes a
technical reflection grounded in observed results.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import build_graph
from tools.solve_tool import solve_with_llm


TEST_PROBLEMS = [
    "Solve 2x + 3 = 11",
    "Solve 3x - 7 = 11",
    "Factor x^2 + 5x + 6",
    "Solve x^2 - 9 = 0",
    "Find the derivative of x^3 + 2x",
    "Find the derivative of (x^2 + 1)(x - 4)",
    "Integrate 2x + 5",
    "Compute the integral of x^2",
    "If a rectangle has length 8 and width 3, what is its area?",
    "Solve the system: x + y = 6 and x - y = 2",
]


def retrieval_score(result: dict) -> int:
    """Score retrieval relevance from 0-2 using simple deterministic rules."""
    match = result.get("retrieved_similar_problem", {})
    normalized = result.get("normalized_user_problem", "")

    url = (match.get("url") or "").lower()
    title = (match.get("title") or "").lower()
    snippet = (match.get("snippet") or "").lower()

    if not url or ".edu" not in url:
        return 0

    q_tokens = set(normalized.split())
    c_tokens = set((title + " " + snippet).split())
    overlap = len(q_tokens.intersection(c_tokens))

    if overlap >= 4:
        return 2
    if overlap >= 2:
        return 1
    return 0


def _has_critical_error(errors: list[str]) -> bool:
    """Return True if errors contain solve/input failures."""
    return any(
        "Local Ollama solve failed" in err
        or "No input provided" in err
        or "Normalized problem text is empty" in err
        for err in errors
    )


def _non_solve_errors(errors: list[str]) -> list[str]:
    """Keep upstream errors while removing solve-stage model-call failures."""
    return [err for err in errors if "Local Ollama solve failed" not in err]


def solution_score(result: dict) -> int:
    """Score solution utility from 0-2 for classroom-quality output."""
    final_solution = (result.get("final_solution") or "").strip().lower()
    errors = result.get("errors", [])

    if final_solution.startswith("placeholder solution"):
        return 0

    # Penalize only critical solve-stage errors, not search fallback warnings.
    if _has_critical_error(errors):
        return 1

    # A lightweight proxy for explanation quality.
    if "step" in final_solution or "therefore" in final_solution or "answer" in final_solution:
        return 2

    return 1


def _normalize_for_match(text: str) -> str:
    """Normalize text for lightweight answer matching."""
    cleaned = text.lower().replace("\\", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def _contains_any(text: str, options: list[str]) -> bool:
    return any(option in text for option in options)


def correctness_score(problem_id: int, result: dict) -> int:
    """Score mathematical correctness from 0-2 using prompt-specific checks."""
    final_solution = (result.get("final_solution") or "").strip()
    errors = result.get("errors", [])

    if final_solution.lower().startswith("placeholder solution"):
        return 0
    if _has_critical_error(errors):
        return 0

    text = _normalize_for_match(final_solution)

    # Score legend:
    # 2 = expected final answer pattern clearly present
    # 1 = partially correct evidence present
    # 0 = missing or contradictory answer pattern
    if problem_id == 1:
        return 2 if _contains_any(text, ["x=4", "x4"]) else 0

    if problem_id == 2:
        return 2 if _contains_any(text, ["x=6", "x6"]) else 0

    if problem_id == 3:
        full = ("-2" in text and "-3" in text) or ("(x+2)(x+3)" in text)
        partial = ("-2" in text) or ("-3" in text) or ("x+2" in text and "x+3" in text)
        if full:
            return 2
        if partial:
            return 1
        return 0

    if problem_id == 4:
        has_pos = _contains_any(text, ["x=3", "or3", "and3"])
        has_neg = _contains_any(text, ["x=-3", "-3"])
        if has_pos and has_neg:
            return 2
        if has_pos or has_neg:
            return 1
        return 0

    if problem_id == 5:
        if _contains_any(text, ["3x^2+2", "3x2+2"]):
            return 2
        if _contains_any(text, ["3x^2+4", "3x2+4"]):
            return 0
        if "3x" in text:
            return 1
        return 0

    if problem_id == 6:
        if _contains_any(text, ["3x^2-8x+1", "3x2-8x+1"]):
            return 2
        if _contains_any(text, ["3x^2", "-8x", "+1"]):
            return 1
        return 0

    if problem_id == 7:
        has_poly = _contains_any(text, ["x^2+5x", "x2+5x"])
        has_constant = "c" in text
        if has_poly and has_constant:
            return 2
        if has_poly:
            return 1
        return 0

    if problem_id == 8:
        has_integral = _contains_any(
            text,
            ["x^3/3", "x3/3", "x^{3}/3", "frac{x^3}{3}", "frac{x3}{3}"],
        )
        has_constant = "c" in text
        if has_integral and has_constant:
            return 2
        if has_integral:
            return 1
        return 0

    if problem_id == 9:
        if _contains_any(text, ["24", "24squareunits"]):
            return 2
        return 0

    if problem_id == 10:
        has_x = _contains_any(text, ["x=4", "x4"])
        has_y = _contains_any(text, ["y=2", "y2"])
        if has_x and has_y:
            return 2
        if has_x or has_y:
            return 1
        return 0

    return 0


def parse_args() -> argparse.Namespace:
    """Parse optional controls for safer local evaluation runs."""
    parser = argparse.ArgumentParser(description="Run local evaluation for the Math Similarity Solver Agent")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Run only the first N test problems. Use 0 to run the full set.",
    )
    parser.add_argument(
        "--results-file",
        type=str,
        default="results.json",
        help="Filename for the JSON evaluation output.",
    )
    parser.add_argument(
        "--reflection-file",
        type=str,
        default="reflection.md",
        help="Filename for the markdown evaluation reflection.",
    )
    return parser.parse_args()


def run_queries(limit: int = 0) -> dict:
    """Run all fixed queries and compare solve with-vs-without similar context."""
    app = build_graph()
    runs = []
    prompts = TEST_PROBLEMS if limit <= 0 else TEST_PROBLEMS[:limit]

    for idx, prompt in enumerate(prompts, start=1):
        state = {"raw_text": prompt, "image_path": "", "errors": []}
        result = app.invoke(state)

        base_output = {
            "normalized_user_problem": result.get("normalized_problem", ""),
            "search_query": result.get("query", ""),
            "search_provider": result.get("search_provider", ""),
            "search_used_fallback": result.get("search_used_fallback", False),
            "search_candidate_count": result.get("search_candidate_count", 0),
            "retrieved_similar_problem": {
                "title": result.get("best_match", {}).get("title", ""),
                "url": result.get("best_match", {}).get("url", ""),
                "snippet": result.get("best_match", {}).get("snippet", ""),
            },
            "similarity_score": result.get("similarity_score", 0.0),
        }

        best = result.get("best_match", {})
        similar_problem = f"{best.get('title', '')} {best.get('snippet', '')}".strip()

        with_context_output = {
            **base_output,
            "used_similar_context": True,
            "final_solution": result.get("final_solution", ""),
            "errors": result.get("errors", []),
        }

        without_context_solution, without_context_error = solve_with_llm(
            user_problem=base_output["normalized_user_problem"],
            similar_problem="",
        )
        without_context_errors = _non_solve_errors(result.get("errors", []))
        if without_context_error:
            without_context_errors.append(without_context_error)

        without_context_output = {
            **base_output,
            "used_similar_context": False,
            "final_solution": without_context_solution,
            "errors": without_context_errors,
        }

        r_score = retrieval_score(base_output)
        with_context_solution_score = solution_score(with_context_output)
        without_context_solution_score = solution_score(without_context_output)
        with_context_correctness_score = correctness_score(idx, with_context_output)
        without_context_correctness_score = correctness_score(idx, without_context_output)

        runs.append(
            {
                "id": idx,
                "prompt": prompt,
                "retrieved_similar_text_used": similar_problem,
                "output_with_context": with_context_output,
                "output_without_context": without_context_output,
                "retrieval_relevance_score": r_score,
                "solution_utility_with_context": with_context_solution_score,
                "solution_utility_without_context": without_context_solution_score,
                "answer_correctness_with_context": with_context_correctness_score,
                "answer_correctness_without_context": without_context_correctness_score,
                "total_with_context": r_score + with_context_solution_score,
                "total_without_context": r_score + without_context_solution_score,
                "total_strict_with_context": r_score + with_context_correctness_score,
                "total_strict_without_context": r_score + without_context_correctness_score,
                "solution_score_delta_with_minus_without": (
                    with_context_solution_score - without_context_solution_score
                ),
                "correctness_score_delta_with_minus_without": (
                    with_context_correctness_score - without_context_correctness_score
                ),
            }
        )

    retrieval_scores = [r["retrieval_relevance_score"] for r in runs]
    with_context_solution_scores = [r["solution_utility_with_context"] for r in runs]
    without_context_solution_scores = [r["solution_utility_without_context"] for r in runs]
    similarity_scores = [float(r["output_with_context"].get("similarity_score", 0.0)) for r in runs]
    with_context_total_scores = [r["total_with_context"] for r in runs]
    without_context_total_scores = [r["total_without_context"] for r in runs]
    with_context_correctness_scores = [r["answer_correctness_with_context"] for r in runs]
    without_context_correctness_scores = [r["answer_correctness_without_context"] for r in runs]
    with_context_total_strict_scores = [r["total_strict_with_context"] for r in runs]
    without_context_total_strict_scores = [r["total_strict_without_context"] for r in runs]

    with_context_critical_error_count = sum(
        1
        for r in runs
        if _has_critical_error(r["output_with_context"].get("errors", []))
    )
    without_context_critical_error_count = sum(
        1
        for r in runs
        if _has_critical_error(r["output_without_context"].get("errors", []))
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "query_count": len(runs),
        "comparison_mode": "with_context_vs_without_context",
        "summary": {
            "avg_retrieval_relevance": round(statistics.mean(retrieval_scores), 3),
            "avg_solution_utility_with_context": round(statistics.mean(with_context_solution_scores), 3),
            "avg_solution_utility_without_context": round(statistics.mean(without_context_solution_scores), 3),
            "avg_similarity_score": round(statistics.mean(similarity_scores), 3),
            "avg_total_with_context": round(statistics.mean(with_context_total_scores), 3),
            "avg_total_without_context": round(statistics.mean(without_context_total_scores), 3),
            "avg_total_delta_with_minus_without": round(
                statistics.mean(
                    [r["total_with_context"] - r["total_without_context"] for r in runs]
                ),
                3,
            ),
            "avg_answer_correctness_with_context": round(
                statistics.mean(with_context_correctness_scores),
                3,
            ),
            "avg_answer_correctness_without_context": round(
                statistics.mean(without_context_correctness_scores),
                3,
            ),
            "avg_answer_correctness_delta_with_minus_without": round(
                statistics.mean(
                    [
                        r["answer_correctness_with_context"]
                        - r["answer_correctness_without_context"]
                        for r in runs
                    ]
                ),
                3,
            ),
            "correctness_with_context_better_count": sum(
                1
                for r in runs
                if r["answer_correctness_with_context"] > r["answer_correctness_without_context"]
            ),
            "correctness_without_context_better_count": sum(
                1
                for r in runs
                if r["answer_correctness_without_context"] > r["answer_correctness_with_context"]
            ),
            "correctness_tie_count": sum(
                1
                for r in runs
                if r["answer_correctness_with_context"] == r["answer_correctness_without_context"]
            ),
            "avg_total_strict_with_context": round(statistics.mean(with_context_total_strict_scores), 3),
            "avg_total_strict_without_context": round(statistics.mean(without_context_total_strict_scores), 3),
            "with_context_better_count": sum(
                1 for r in runs if r["total_with_context"] > r["total_without_context"]
            ),
            "without_context_better_count": sum(
                1 for r in runs if r["total_without_context"] > r["total_with_context"]
            ),
            "tie_count": sum(1 for r in runs if r["total_with_context"] == r["total_without_context"]),
            "error_run_count_with_context": sum(
                1 for r in runs if r["output_with_context"].get("errors")
            ),
            "error_run_count_without_context": sum(
                1 for r in runs if r["output_without_context"].get("errors")
            ),
            "critical_error_run_count_with_context": with_context_critical_error_count,
            "critical_error_run_count_without_context": without_context_critical_error_count,
            "placeholder_run_count_with_context": sum(
                1
                for r in runs
                if (
                    r["output_with_context"].get("final_solution", "").strip().lower().startswith(
                        "placeholder solution"
                    )
                )
            ),
            "placeholder_run_count_without_context": sum(
                1
                for r in runs
                if (
                    r["output_without_context"].get("final_solution", "").strip().lower().startswith(
                        "placeholder solution"
                    )
                )
            ),
            "edu_result_count": sum(
                1
                for r in runs
                if ".edu" in (r["output_with_context"].get("retrieved_similar_problem", {}).get("url", "").lower())
            ),
        },
        "runs": runs,
    }


def build_reflection(results: dict) -> str:
    """Create a technical reflection grounded in measured local outputs."""
    summary = results["summary"]
    runs = results["runs"]

    strongest_with_context = sorted(runs, key=lambda r: r["total_with_context"], reverse=True)[:3]
    weakest_with_context = sorted(runs, key=lambda r: r["total_with_context"])[:3]
    biggest_gain_with_context = sorted(
        runs,
        key=lambda r: r["solution_score_delta_with_minus_without"],
        reverse=True,
    )[:3]
    biggest_correctness_delta = sorted(
        runs,
        key=lambda r: abs(r["correctness_score_delta_with_minus_without"]),
        reverse=True,
    )[:3]

    def fmt_run(run: dict, total_key: str, solution_key: str) -> str:
        url = run["output_with_context"]["retrieved_similar_problem"].get("url", "")
        sim = run["output_with_context"].get("similarity_score", 0.0)
        return (
            f"- Q{run['id']}: total={run[total_key]} "
            f"(retrieval={run['retrieval_relevance_score']}, solution={run[solution_key]}), "
            f"similarity={sim}, url={url}"
        )

    lines = [
        "# Technical Reflection (Local Evaluation)",
        "",
        "## Method",
        f"- Ran {results['query_count']} fixed text queries through the existing LangGraph workflow (OCR -> normalize -> search -> similarity -> solve).",
        f"- For each query, evaluated two solve variants using the configured local LLM backend ({os.getenv('LLM_BACKEND', 'huggingface')}): with retrieved similar context and without similar context.",
        "- Scored each run on retrieval relevance (0-2), solution utility (0-2), and prompt-specific answer correctness (0-2), then compared per-query and aggregate deltas.",
        "",
        "## Aggregate Results",
        f"- Queries: {results['query_count']}",
        f"- Avg retrieval relevance (0-2): {summary['avg_retrieval_relevance']}",
        f"- Avg solution utility with context (0-2): {summary['avg_solution_utility_with_context']}",
        f"- Avg solution utility without context (0-2): {summary['avg_solution_utility_without_context']}",
        f"- Avg answer correctness with context (0-2): {summary['avg_answer_correctness_with_context']}",
        f"- Avg answer correctness without context (0-2): {summary['avg_answer_correctness_without_context']}",
        f"- Avg answer correctness delta (with - without): {summary['avg_answer_correctness_delta_with_minus_without']}",
        f"- Correctness wins (with / without / ties): {summary['correctness_with_context_better_count']} / {summary['correctness_without_context_better_count']} / {summary['correctness_tie_count']}",
        f"- Avg lexical similarity score: {summary['avg_similarity_score']}",
        f"- Avg total score with context (0-4): {summary['avg_total_with_context']}",
        f"- Avg total score without context (0-4): {summary['avg_total_without_context']}",
        f"- Avg strict total with context (retrieval + correctness, 0-4): {summary['avg_total_strict_with_context']}",
        f"- Avg strict total without context (retrieval + correctness, 0-4): {summary['avg_total_strict_without_context']}",
        f"- Avg total score delta (with - without): {summary['avg_total_delta_with_minus_without']}",
        f"- With-context wins / without-context wins / ties: {summary['with_context_better_count']} / {summary['without_context_better_count']} / {summary['tie_count']}",
        f"- Runs with errors (with context): {summary['error_run_count_with_context']}",
        f"- Runs with errors (without context): {summary['error_run_count_without_context']}",
        f"- Runs with critical solve/input errors (with context): {summary['critical_error_run_count_with_context']}",
        f"- Runs with critical solve/input errors (without context): {summary['critical_error_run_count_without_context']}",
        f"- Runs with placeholder answers (with context): {summary['placeholder_run_count_with_context']}",
        f"- Runs with placeholder answers (without context): {summary['placeholder_run_count_without_context']}",
        f"- Runs with .edu retrieval URLs: {summary['edu_result_count']}",
        "",
        "## Strongest Cases (With Context)",
    ]
    lines.extend(
        fmt_run(r, total_key="total_with_context", solution_key="solution_utility_with_context")
        for r in strongest_with_context
    )
    lines.extend(["", "## Weakest Cases (With Context)"])
    lines.extend(
        fmt_run(r, total_key="total_with_context", solution_key="solution_utility_with_context")
        for r in weakest_with_context
    )
    lines.extend(["", "## Largest Context Gains"])
    lines.extend(
        (
            f"- Q{r['id']}: solution delta={r['solution_score_delta_with_minus_without']} "
            f"(with={r['solution_utility_with_context']}, without={r['solution_utility_without_context']})"
        )
        for r in biggest_gain_with_context
    )
    lines.extend(["", "## Largest Correctness Deltas"])
    lines.extend(
        (
            f"- Q{r['id']}: correctness delta={r['correctness_score_delta_with_minus_without']} "
            f"(with={r['answer_correctness_with_context']}, without={r['answer_correctness_without_context']})"
        )
        for r in biggest_correctness_delta
    )

    lines.extend(
        [
            "",
            "## Technical Interpretation",
            "- The graph reliably provides a retrieved context object, enabling an explicit ablation rather than a hypothetical comparison.",
            "- Retrieval quality remains constrained by web snippet quality and lexical token overlap, independent of solve variant.",
            "- The added correctness metric is stricter than style-based utility scoring and can expose wrong final answers even when explanations look fluent.",
            "- Context-helpfulness is query-dependent: some prompts benefit, while others are unchanged when similar context is removed.",
            "- Solver quality is still tightly coupled to local model availability; placeholder safeguards preserve demo continuity if model calls fail.",
            "",
            "## Key Limitations",
            "- Similarity ranking is lexical only; there is no semantic embedding or math-aware parsing.",
            "- Search can return sparse or mismatched snippets, and fallback results may not align with every prompt type.",
            "- Correctness checks are deterministic prompt-specific heuristics and not a full symbolic math verifier.",
            "- Evaluation scoring remains lightweight and is suitable for class reflection, not publication-level benchmarking.",
            "",
            "## Next Technical Improvements",
            "1. Add a semantic similarity baseline (embedding or hybrid lexical+semantic ranking) and re-run the same with/without-context ablation.",
            "2. Add a tiny gold set with expected solution forms for stricter scoring of both variants.",
            "3. Add one image-based OCR test case in each evaluation run when sample images are available.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    load_dotenv()
    args = parse_args()

    evaluation_dir = Path(__file__).resolve().parent
    results_path = evaluation_dir / args.results_file
    reflection_path = evaluation_dir / args.reflection_file

    results = run_queries(limit=args.limit)
    reflection = build_reflection(results)

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    reflection_path.write_text(reflection, encoding="utf-8")

    print(f"Wrote {results_path}")
    print(f"Wrote {reflection_path}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
