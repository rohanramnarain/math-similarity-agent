"""Run a reproducible local evaluation for the Math Similarity Solver Agent.

This script runs 10 fixed text queries through the LangGraph workflow,
stores detailed outputs, computes lightweight quality scores, and writes a
technical reflection grounded in observed results.
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph import build_graph


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


def solution_score(result: dict) -> int:
    """Score solution utility from 0-2 for classroom-quality output."""
    final_solution = (result.get("final_solution") or "").strip().lower()
    errors = result.get("errors", [])

    if final_solution.startswith("placeholder solution"):
        return 0

    # Penalize only critical solve-stage errors, not search fallback warnings.
    has_critical_error = any(
        "Local Ollama solve failed" in err
        or "No input provided" in err
        or "Normalized problem text is empty" in err
        for err in errors
    )
    if has_critical_error:
        return 1

    # A lightweight proxy for explanation quality.
    if "step" in final_solution or "therefore" in final_solution or "answer" in final_solution:
        return 2

    return 1


def run_queries() -> dict:
    """Run all fixed queries through the graph and compute score summaries."""
    app = build_graph()
    runs = []

    for idx, prompt in enumerate(TEST_PROBLEMS, start=1):
        state = {"raw_text": prompt, "image_path": "", "errors": []}
        result = app.invoke(state)

        output = {
            "normalized_user_problem": result.get("normalized_problem", ""),
            "retrieved_similar_problem": {
                "title": result.get("best_match", {}).get("title", ""),
                "url": result.get("best_match", {}).get("url", ""),
                "snippet": result.get("best_match", {}).get("snippet", ""),
            },
            "similarity_score": result.get("similarity_score", 0.0),
            "final_solution": result.get("final_solution", ""),
            "errors": result.get("errors", []),
        }

        r_score = retrieval_score(output)
        s_score = solution_score(output)

        runs.append(
            {
                "id": idx,
                "prompt": prompt,
                "output": output,
                "retrieval_relevance_score": r_score,
                "solution_utility_score": s_score,
                "total_score": r_score + s_score,
            }
        )

    retrieval_scores = [r["retrieval_relevance_score"] for r in runs]
    solution_scores = [r["solution_utility_score"] for r in runs]
    similarity_scores = [float(r["output"].get("similarity_score", 0.0)) for r in runs]
    critical_error_count = sum(
        1
        for r in runs
        if any(
            "Local Ollama solve failed" in err
            or "No input provided" in err
            or "Normalized problem text is empty" in err
            for err in r["output"].get("errors", [])
        )
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "query_count": len(runs),
        "summary": {
            "avg_retrieval_relevance": round(statistics.mean(retrieval_scores), 3),
            "avg_solution_utility": round(statistics.mean(solution_scores), 3),
            "avg_similarity_score": round(statistics.mean(similarity_scores), 3),
            "error_run_count": sum(1 for r in runs if r["output"].get("errors")),
            "critical_error_run_count": critical_error_count,
            "placeholder_run_count": sum(
                1
                for r in runs
                if (r["output"].get("final_solution", "").strip().lower().startswith("placeholder solution"))
            ),
            "edu_result_count": sum(
                1
                for r in runs
                if ".edu" in (r["output"].get("retrieved_similar_problem", {}).get("url", "").lower())
            ),
        },
        "runs": runs,
    }


def build_reflection(results: dict) -> str:
    """Create a technical reflection grounded in measured local outputs."""
    summary = results["summary"]
    runs = results["runs"]

    strongest = sorted(runs, key=lambda r: r["total_score"], reverse=True)[:3]
    weakest = sorted(runs, key=lambda r: r["total_score"])[:3]

    def fmt_run(run: dict) -> str:
        url = run["output"]["retrieved_similar_problem"].get("url", "")
        sim = run["output"].get("similarity_score", 0.0)
        return (
            f"- Q{run['id']}: total={run['total_score']} "
            f"(retrieval={run['retrieval_relevance_score']}, solution={run['solution_utility_score']}), "
            f"similarity={sim}, url={url}"
        )

    lines = [
        "# Technical Reflection (Local Evaluation)",
        "",
        "## Method",
        "- Ran 10 fixed text queries through the existing LangGraph workflow (OCR -> normalize -> search -> similarity -> solve).",
        "- Used local Ollama via configured environment variables and captured the full JSON output per query.",
        "- Scored each run on two 0-2 scales: retrieval relevance and solution utility.",
        "",
        "## Aggregate Results",
        f"- Queries: {results['query_count']}",
        f"- Avg retrieval relevance (0-2): {summary['avg_retrieval_relevance']}",
        f"- Avg solution utility (0-2): {summary['avg_solution_utility']}",
        f"- Avg lexical similarity score: {summary['avg_similarity_score']}",
        f"- Runs with errors: {summary['error_run_count']}",
        f"- Runs with critical solve/input errors: {summary['critical_error_run_count']}",
        f"- Runs with placeholder answers: {summary['placeholder_run_count']}",
        f"- Runs with .edu retrieval URLs: {summary['edu_result_count']}",
        "",
        "## Strongest Cases",
    ]
    lines.extend(fmt_run(r) for r in strongest)
    lines.extend(["", "## Weakest Cases"])
    lines.extend(fmt_run(r) for r in weakest)

    lines.extend(
        [
            "",
            "## Technical Interpretation",
            "- The deterministic graph structure is stable and produces complete output objects consistently.",
            "- Retrieval quality is mostly constrained by web snippet quality and lexical token overlap, not graph orchestration.",
            "- The simple Jaccard matcher is easy to explain for class demos, but it under-ranks conceptually similar problems phrased differently.",
            "- Solver quality is tightly coupled to local model availability and model capability. If the model call fails, fallback placeholders protect demo continuity but reduce true solve performance.",
            "",
            "## Key Limitations",
            "- Similarity ranking is lexical only; there is no semantic embedding or math-aware parsing.",
            "- Search can return sparse or mismatched snippets, and fallback results may not align with every prompt type.",
            "- Evaluation scoring is lightweight and partly heuristic; it is suitable for class reflection, not publication-level benchmarking.",
            "",
            "## Next Technical Improvements",
            "1. Add a semantic similarity baseline (embedding or hybrid lexical+semantic ranking).",
            "2. Add a tiny gold set with expected solution forms for stricter scoring.",
            "3. Add one image-based OCR test case in each evaluation run when sample images are available.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    load_dotenv()

    evaluation_dir = Path(__file__).resolve().parent
    results_path = evaluation_dir / "results.json"
    reflection_path = evaluation_dir / "reflection.md"

    results = run_queries()
    reflection = build_reflection(results)

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    reflection_path.write_text(reflection, encoding="utf-8")

    print(f"Wrote {results_path}")
    print(f"Wrote {reflection_path}")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
