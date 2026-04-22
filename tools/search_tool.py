"""Web search helper for the class demo.

This file builds a .edu-restricted query and fetches candidate snippets from
DuckDuckGo HTML results. If search fails, it falls back to static examples so
that the classroom demo still runs end-to-end.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

DUCKDUCKGO_HTML = "https://duckduckgo.com/html/"

FALLBACK_RESULTS = [
    {
        "title": "Paul's Online Math Notes - Solving Linear Equations",
        "url": "https://tutorial.math.lamar.edu/Classes/Alg/SolveEqns.aspx",
        "snippet": "Algebra notes with worked examples for solving linear equations step by step.",
        "tags": ["algebra", "linear", "equation", "solve", "system"],
    },
    {
        "title": "Paul's Online Math Notes - Factoring Polynomials",
        "url": "https://tutorial.math.lamar.edu/Classes/Alg/Factoring.aspx",
        "snippet": "Worked examples for factoring quadratics and polynomial expressions.",
        "tags": ["algebra", "factor", "quadratic", "polynomial"],
    },
    {
        "title": "Paul's Online Math Notes - Derivatives",
        "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeIntro.aspx",
        "snippet": "Calculus I derivative rules and examples including power rule and product rule.",
        "tags": ["calculus", "derivative", "differentiate", "product rule"],
    },
    {
        "title": "Paul's Online Math Notes - Integrals",
        "url": "https://tutorial.math.lamar.edu/Classes/CalcI/IntegralsIntro.aspx",
        "snippet": "Calculus I integration basics with antiderivative examples.",
        "tags": ["calculus", "integral", "integrate", "antiderivative"],
    },
    {
        "title": "University of Kentucky - Solving Systems by Elimination",
        "url": "https://www.ms.uky.edu/ma109/textbook/sec-solvesystemelim.html",
        "snippet": "Step-by-step elimination method examples for systems of linear equations.",
        "tags": ["algebra", "system", "elimination", "linear"],
    },
]


def _fallback_candidates_for_query(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return real .edu fallback candidates with simple topic matching."""
    tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored: list[tuple[int, dict[str, Any]]] = []

    for item in FALLBACK_RESULTS:
        tag_overlap = len(tokens.intersection(set(item.get("tags", []))))
        clean_item = {
            "title": item["title"],
            "url": item["url"],
            "snippet": item["snippet"],
        }
        scored.append((tag_overlap, clean_item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    ordered = [entry for _, entry in scored]
    return ordered[:max_results]


def build_edu_query(problem_text: str) -> str:
    """Build a short .edu-focused search query from normalized problem text."""
    short = " ".join(problem_text.split()[:24])
    return f"site:.edu solved example {short}".strip()


def _is_edu_url(url: str) -> bool:
    return ".edu" in url.lower()


def _unwrap_duckduckgo_link(url: str) -> str:
    """Convert DuckDuckGo redirect links to direct destination URLs."""
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url

    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    return url


def search_candidate_problems(query: str, max_results: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    """Search for candidate solved problems and return basic text fields.

    Returns:
        (results, error_message). If successful, error_message is None.
    """
    try:
        response = requests.get(
            DUCKDUCKGO_HTML,
            params={"q": query},
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (MathSimilarityAgent/0.1)"},
        )
        response.raise_for_status()
    except Exception as exc:
        # Clear fallback for offline demos or blocked network environments.
        fallback = _fallback_candidates_for_query(query=query, max_results=max_results)
        return fallback, f"Search request failed, using fallback examples: {exc}"

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, Any]] = []

    for block in soup.select("div.result"):
        link = block.select_one("a.result__a")
        snippet_node = block.select_one("a.result__snippet") or block.select_one("div.result__snippet")
        if not link:
            continue

        url = _unwrap_duckduckgo_link(link.get("href", "").strip())
        title = link.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""

        # Keep .edu targets only to match project scope.
        if not _is_edu_url(url):
            continue

        # Remove noisy whitespace and symbols for easier downstream similarity.
        snippet = re.sub(r"\s+", " ", snippet).strip()

        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break

    if not results:
        fallback = _fallback_candidates_for_query(query=query, max_results=max_results)
        return fallback, "No .edu candidates found from web search; using fallback examples"

    return results, None
