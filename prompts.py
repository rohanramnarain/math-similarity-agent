"""Prompt helpers for the class demo.

This file keeps prompt text in one place so the graph and tools stay simple.
"""


def build_solver_prompt(user_problem: str, similar_problem: str) -> str:
	"""Create a concise prompt for solving a new problem using a similar one."""
	return (
		"You are a math tutor. Solve the user's new problem step-by-step.\n"
		"Use the similar solved problem only as supporting context.\n"
		"If context seems mismatched, say so and still solve the new problem.\n\n"
		"User problem:\n"
		f"{user_problem}\n\n"
		"Retrieved similar problem:\n"
		f"{similar_problem}\n\n"
		"Return a clear, concise final solution."
	)
