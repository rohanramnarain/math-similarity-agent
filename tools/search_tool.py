"""Web search helper for the class demo.

This file builds a .edu-restricted query and fetches candidate snippets from
DuckDuckGo HTML results. If search fails, it falls back to static examples so
that the classroom demo still runs end-to-end.
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

DUCKDUCKGO_HTML = "https://duckduckgo.com/html/"
BING_SEARCH = "https://www.bing.com/search"

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


def _topic_terms(problem_text: str) -> list[str]:
    """Add lightweight math-topic hints to improve search relevance."""
    text = problem_text.lower()
    terms: list[str] = []

    if "derivative" in text or "differentiate" in text:
        terms.extend(["calculus", "derivative"])
    elif "integral" in text or "integrate" in text:
        terms.extend(["calculus", "integral"])
    elif "factor" in text:
        terms.extend(["algebra", "factoring"])
    elif "system" in text or ("x + y" in text and "x - y" in text):
        terms.extend(["algebra", "system of equations"])
    elif "rectangle" in text or "area" in text:
        terms.extend(["geometry", "area"])
    else:
        terms.extend(["algebra", "linear equation"])

    return terms


def build_edu_query(problem_text: str) -> str:
    """Build a short .edu-focused search query from normalized problem text."""
    short = " ".join(problem_text.split()[:18])
    topic = " ".join(_topic_terms(problem_text))
    return f'site:.edu {topic} worked example "{short}"'.strip()


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


def _clean_snippet(text: str) -> str:
    """Normalize snippet text from search providers."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _search_duckduckgo_html(query: str, max_results: int) -> tuple[list[dict[str, Any]], str | None]:
    """Try DuckDuckGo HTML results first."""
    response = requests.get(
        DUCKDUCKGO_HTML,
        params={"q": query},
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0 (MathSimilarityAgent/0.1)"},
    )
    response.raise_for_status()

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

        if not _is_edu_url(url):
            continue

        results.append({"title": title, "url": url, "snippet": _clean_snippet(snippet)})
        if len(results) >= max_results:
            break

    if not results:
        return [], "DuckDuckGo returned no .edu candidates"

    return results, None


def _search_bing_rss(query: str, max_results: int) -> tuple[list[dict[str, Any]], str | None]:
    """Fallback to Bing RSS because it is lighter-weight than HTML scraping."""
    response = requests.get(
        BING_SEARCH,
        params={"q": query, "format": "rss"},
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0 (MathSimilarityAgent/0.1)"},
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results: list[dict[str, Any]] = []

    for item in root.findall("./channel/item"):
        url = (item.findtext("link") or "").strip()
        if not _is_edu_url(url):
            continue

        title = (item.findtext("title") or "").strip()
        snippet = _clean_snippet(item.findtext("description") or "")
        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break

    if not results:
        return [], "Bing RSS returned no .edu candidates"

    return results, None


def _search_bing_html(query: str, max_results: int) -> tuple[list[dict[str, Any]], str | None]:
    """Use Bing HTML results as a stronger fallback than RSS for .edu pages."""
    response = requests.get(
        BING_SEARCH,
        params={"q": query},
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0 (MathSimilarityAgent/0.1)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, Any]] = []

    for block in soup.select("li.b_algo"):
        link = block.select_one("h2 a")
        snippet_node = block.select_one("p")
        if not link:
            continue

        url = (link.get("href") or "").strip()
        title = link.get_text(" ", strip=True)
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""

        if not _is_edu_url(url):
            continue

        results.append({"title": title, "url": url, "snippet": _clean_snippet(snippet)})
        if len(results) >= max_results:
            break

    if not results:
        return [], "Bing HTML returned no .edu candidates"

    return results, None


def search_candidate_problems(
    query: str,
    max_results: int = 5,
) -> tuple[list[dict[str, Any]], str | None, dict[str, Any]]:
    """Search for candidate solved problems and return basic text fields.

    Returns:
        (results, error_message, metadata). If successful, error_message is None.
    """
    attempt_errors: list[str] = []

    for provider_name, search_fn in [
        ("Bing HTML", _search_bing_html),
        ("Bing RSS", _search_bing_rss),
        ("DuckDuckGo HTML", _search_duckduckgo_html),
    ]:
        try:
            results, error = search_fn(query, max_results)
        except Exception as exc:
            attempt_errors.append(f"{provider_name} failed: {exc}")
            continue

        if results:
            if error:
                attempt_errors.append(error)
            warning = "; ".join(attempt_errors) if attempt_errors else None
            metadata = {
                "provider": provider_name,
                "used_fallback": False,
                "candidate_count": len(results),
            }
            return results, warning, metadata

        if error:
            attempt_errors.append(error)

    fallback = _fallback_candidates_for_query(query=query, max_results=max_results)
    error_message = "; ".join(attempt_errors) if attempt_errors else "No .edu candidates found from live search"
    metadata = {
        "provider": "Static Fallback",
        "used_fallback": True,
        "candidate_count": len(fallback),
    }
    return fallback, f"{error_message}; using fallback examples", metadata
