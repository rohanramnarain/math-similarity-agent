"""LangGraph workflow for the Math Similarity Solver Agent.

The graph is intentionally small and mostly deterministic for classroom demos.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from tools.ocr_tool import extract_text_from_image
from tools.search_tool import build_edu_query, search_candidate_problems
from tools.similarity_tool import select_best_match
from tools.solve_tool import solve_with_llm


class AgentState(TypedDict, total=False):
	"""Shared state that flows through all graph nodes."""

	raw_text: str
	image_path: str
	extracted_text: str
	normalized_problem: str
	query: str
	candidates: list[dict[str, Any]]
	best_match: dict[str, Any]
	similarity_score: float
	final_solution: str
	errors: list[str]


def _add_error(state: AgentState, message: str) -> None:
	"""Append an error message to state without breaking the run."""
	state.setdefault("errors", [])
	state["errors"].append(message)


def ocr_node(state: AgentState) -> AgentState:
	"""Extract text from image input, or pass through raw text input."""
	raw_text = (state.get("raw_text") or "").strip()
	image_path = (state.get("image_path") or "").strip()

	if raw_text:
		state["extracted_text"] = raw_text
		return state

	if image_path:
		text, error = extract_text_from_image(image_path)
		state["extracted_text"] = text
		if error:
			_add_error(state, error)
		return state

	state["extracted_text"] = ""
	_add_error(state, "No input provided. Supply --text or --image.")
	return state


def normalize_node(state: AgentState) -> AgentState:
	"""Normalize extracted text for cleaner search and similarity comparisons."""
	text = (state.get("extracted_text") or "").strip().lower()
	text = re.sub(r"\s+", " ", text)
	state["normalized_problem"] = text
	if not text:
		_add_error(state, "Normalized problem text is empty")
	return state


def search_node(state: AgentState) -> AgentState:
	"""Build .edu query and collect candidate solved problems from the web."""
	normalized = state.get("normalized_problem", "")
	query = build_edu_query(normalized)
	state["query"] = query

	candidates, error = search_candidate_problems(query)
	state["candidates"] = candidates
	if error:
		_add_error(state, error)
	return state


def similarity_node(state: AgentState) -> AgentState:
	"""Pick the best matching candidate using simple vector similarity."""
	normalized = state.get("normalized_problem", "")
	candidates = state.get("candidates", [])

	best_match, score = select_best_match(normalized, candidates)
	state["best_match"] = best_match or {}
	state["similarity_score"] = round(float(score), 4)

	if not best_match:
		_add_error(state, "No best match candidate selected")
	return state


def solve_node(state: AgentState) -> AgentState:
	"""Send user problem + best match context to LLM solver."""
	user_problem = state.get("normalized_problem", "")
	best = state.get("best_match", {})
	similar_problem = f"{best.get('title', '')} {best.get('snippet', '')}".strip()

	solution, error = solve_with_llm(user_problem=user_problem, similar_problem=similar_problem)
	state["final_solution"] = solution
	if error:
		_add_error(state, error)
	return state


def build_graph():
	"""Compile and return the minimal runnable LangGraph app."""
	workflow = StateGraph(AgentState)

	workflow.add_node("ocr", ocr_node)
	workflow.add_node("normalize", normalize_node)
	workflow.add_node("search", search_node)
	workflow.add_node("similarity", similarity_node)
	workflow.add_node("solve", solve_node)

	workflow.set_entry_point("ocr")
	workflow.add_edge("ocr", "normalize")
	workflow.add_edge("normalize", "search")
	workflow.add_edge("search", "similarity")
	workflow.add_edge("similarity", "solve")
	workflow.add_edge("solve", END)

	return workflow.compile()
