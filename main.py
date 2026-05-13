"""CLI entrypoint for the Math Similarity Solver Agent demo.

Run with either a text problem or an image path. The script prints the key
outputs required by the class project.
"""

from __future__ import annotations

import argparse
import json
import re
import textwrap

from dotenv import load_dotenv

from graph import build_graph
from tools.solve_tool import get_startup_warning


def _clean_math_output(text: str) -> str:
	"""Convert common LaTeX math notation into terminal-friendly plain text."""
	if not text:
		return ""

	cleaned = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.DOTALL)
	cleaned = re.sub(r"\$(.*?)\$", r"\1", cleaned, flags=re.DOTALL)

	# Convert nested \frac{a}{b} forms one level at a time.
	while True:
		updated = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"(\1)/(\2)", cleaned)
		if updated == cleaned:
			break
		cleaned = updated

	cleaned = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"sqrt(\1)", cleaned)
	cleaned = cleaned.replace("\\times", "*")
	cleaned = cleaned.replace("\\cdot", "*")
	cleaned = cleaned.replace("\\leq", "<=")
	cleaned = cleaned.replace("\\geq", ">=")
	cleaned = cleaned.replace("\\neq", "!=")
	cleaned = cleaned.replace("\\left", "")
	cleaned = cleaned.replace("\\right", "")

	# Strip any remaining simple LaTeX commands while preserving their text payload.
	cleaned = re.sub(r"\\[a-zA-Z]+", "", cleaned)
	cleaned = cleaned.replace("{", "")
	cleaned = cleaned.replace("}", "")
	cleaned = re.sub(r"[ \t]+", " ", cleaned)
	cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
	return cleaned


def parse_args() -> argparse.Namespace:
	"""Parse command-line inputs for text or image modes."""
	parser = argparse.ArgumentParser(description="Math Similarity Solver Agent")
	parser.add_argument("--text", type=str, default="", help="Raw math problem as text")
	parser.add_argument("--image", type=str, default="", help="Path to image containing a math problem")
	parser.add_argument(
		"--format",
		choices=["pretty", "json"],
		default="pretty",
		help="Output format for terminal display",
	)
	return parser.parse_args()


def _pretty_print_output(output: dict) -> None:
	"""Print a demo-friendly terminal report."""
	line = "=" * 72
	print(line)
	print("MATH SIMILARITY SOLVER REPORT")
	print(line)

	print(f"Problem      : {output.get('normalized_user_problem', '')}")
	print(f"Search Query : {output.get('search_query', '')}")
	print(
		"Search       : "
		f"{output.get('search_provider', '')} | "
		f"candidates={output.get('search_candidate_count', 0)} | "
		f"fallback={output.get('search_used_fallback', False)}"
	)

	match = output.get("retrieved_similar_problem", {})
	print("\nBest Retrieved Match")
	print("-" * 72)
	print(f"Title        : {match.get('title', '')}")
	print(f"URL          : {match.get('url', '')}")
	print("Snippet      :")
	print(textwrap.fill(match.get("snippet", ""), width=72, initial_indent="  ", subsequent_indent="  "))

	print("\nSimilarity")
	print("-" * 72)
	print(f"Score        : {output.get('similarity_score', 0.0):.3f}")

	print("\nFinal Solution")
	print("-" * 72)
	print(output.get("final_solution", ""))

	errors = output.get("errors", [])
	if errors:
		print("\nWarnings / Notes")
		print("-" * 72)
		for err in errors:
			print(f"- {err}")

	print(line)


def main() -> None:
	"""Run graph and print normalized problem, match, score, and final solution."""
	load_dotenv()
	args = parse_args()
	startup_warning = get_startup_warning()

	app = build_graph()
	state = {
		"raw_text": args.text,
		"image_path": args.image,
		"errors": [f"Startup check: {startup_warning}"] if startup_warning else [],
	}

	result = app.invoke(state)

	output = {
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
		"final_solution": _clean_math_output(result.get("final_solution", "")),
		"errors": result.get("errors", []),
	}

	if args.format == "json":
		print(json.dumps(output, indent=2))
	else:
		_pretty_print_output(output)


if __name__ == "__main__":
	main()
