"""Similarity helper for the class demo.

This file uses a simple lexical overlap score (Jaccard similarity) between
the user problem and each candidate result.
"""

from __future__ import annotations

import re
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Convert text into lowercase word tokens."""
    return re.findall(r"[a-zA-Z0-9^+-/*=().]+", text.lower())


def _jaccard_similarity(a_text: str, b_text: str) -> float:
    """Compute Jaccard similarity of token sets."""
    a = set(_tokenize(a_text))
    b = set(_tokenize(b_text))
    if not a or not b:
        return 0.0

    intersection = len(a.intersection(b))
    union = len(a.union(b))
    if union == 0:
        return 0.0
    return intersection / union


def select_best_match(problem_text: str, candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    """Return the best candidate and similarity score."""
    if not candidates:
        return None, 0.0

    best_candidate = None
    best_score = -1.0

    for candidate in candidates:
        candidate_text = f"{candidate.get('title', '')} {candidate.get('snippet', '')}".strip()
        score = _jaccard_similarity(problem_text, candidate_text)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate, max(best_score, 0.0)
