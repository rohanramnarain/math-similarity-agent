"""CLI entrypoint for the Math Similarity Solver Agent demo.

Run with either a text problem or an image path. The script prints the key
outputs required by the class project.
"""

from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from graph import build_graph
from tools.solve_tool import get_startup_warning


def parse_args() -> argparse.Namespace:
	"""Parse command-line inputs for text or image modes."""
	parser = argparse.ArgumentParser(description="Math Similarity Solver Agent")
	parser.add_argument("--text", type=str, default="", help="Raw math problem as text")
	parser.add_argument("--image", type=str, default="", help="Path to image containing a math problem")
	return parser.parse_args()


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
		"final_solution": result.get("final_solution", ""),
		"errors": result.get("errors", []),
	}

	print(json.dumps(output, indent=2))


if __name__ == "__main__":
	main()
