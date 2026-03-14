"""Similarity helper for the class demo.

This file uses a tiny bag-of-words vector approach with cosine similarity.
TODO: replace with Math2Vec or another math-aware embedding model later.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Convert text into lowercase word tokens."""
    return re.findall(r"[a-zA-Z0-9^+-/*=().]+", text.lower())


def _vectorize(text: str) -> Counter[str]:
    """Build a sparse token-frequency vector."""
    return Counter(_tokenize(text))


def _cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
    """Compute cosine similarity for two sparse token vectors."""
    if not a or not b:
        return 0.0

    dot = sum(a[token] * b.get(token, 0) for token in a)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def select_best_match(problem_text: str, candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    """Return the best candidate and similarity score."""
    if not candidates:
        return None, 0.0

    base_vec = _vectorize(problem_text)
    best_candidate = None
    best_score = -1.0

    for candidate in candidates:
        candidate_text = f"{candidate.get('title', '')} {candidate.get('snippet', '')}".strip()
        candidate_vec = _vectorize(candidate_text)
        score = _cosine_similarity(base_vec, candidate_vec)
        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate, max(best_score, 0.0)
