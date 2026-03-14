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
        "title": "Example algebra problem",
        "url": "https://example.edu/algebra/solved-example",
        "snippet": "Solve for x in a linear equation and show each step.",
    },
    {
        "title": "Example calculus derivative problem",
        "url": "https://example.edu/calculus/derivative-practice",
        "snippet": "Find the derivative of a polynomial using the power rule.",
    },
]


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
        return FALLBACK_RESULTS, f"Search request failed, using fallback examples: {exc}"

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
        return FALLBACK_RESULTS, "No .edu candidates found from web search; using fallback examples"

    return results, None
