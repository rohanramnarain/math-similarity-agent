"""LLM solve helper for the class demo.

This file sends the user problem and matched similar problem to a local
Ollama model via ChatOllama.
"""

from __future__ import annotations

import os

from langchain_ollama import ChatOllama

from prompts import build_solver_prompt


def solve_with_llm(user_problem: str, similar_problem: str) -> tuple[str, str | None]:
    """Solve the user problem with context from a similar retrieved problem.

    Returns:
        (solution_text, error_message). error_message is None when successful.
    """
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b").strip() or "qwen2.5-coder:1.5b"
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"

    try:
        llm = ChatOllama(model=model_name, base_url=base_url, temperature=0)
        prompt = build_solver_prompt(user_problem=user_problem, similar_problem=similar_problem)
        response = llm.invoke(prompt)
        return response.content, None
    except Exception as exc:
        placeholder = (
            "Placeholder solution (local Ollama model unavailable).\n"
            f"Expected model: {model_name}\n"
            f"Expected Ollama URL: {base_url}\n"
            "Detected problem: "
            f"{user_problem[:180]}\n"
            "Retrieved similar example: "
            f"{similar_problem[:180]}\n"
            "TODO: Start Ollama and ensure your configured model is available"
        )
        return placeholder, f"Local Ollama solve failed; returned placeholder solution: {exc}"
