# Proposal: Math Similarity Solver Agent

## Problem statement
Students often have a new math problem but do not know how to begin. A direct model call can solve many problems, but it can fail to provide grounded, problem-specific context. This project builds a minimal workflow that first retrieves a similar solved problem from .edu sources, then uses that context to solve the new problem.

## Why an agentic workflow (instead of one model call)
A single LLM call does not decide whether OCR is needed, does not run targeted retrieval, and does not rank candidate examples before solving. This project uses a staged workflow where each stage has a clear responsibility:
- OCR decision: text input vs image input
- Query construction and constrained web retrieval
- Similarity ranking over candidates
- Final solving with retrieved context

The workflow is mostly deterministic and intentionally small for classroom explainability.

## Proposed design
Pipeline:
1. OCR node: extract text from image if needed
2. Normalize node: lowercase and clean whitespace
3. Search node: build a .edu query and collect candidates
4. Similarity node: rank candidates with Jaccard overlap
5. Solve node: send user problem + best match to local Ollama model

## Decision points
1. OCR routing decision
- What decision: whether to process raw text directly or run OCR
- Deterministic: yes
- Tool(s): pytesseract + Pillow
- Why: supports image-based homework inputs

2. Retrieval decision
- What decision: which external snippets to keep from search
- Deterministic: mostly deterministic filtering (.edu URLs, top-k)
- Tool(s): requests + BeautifulSoup on DuckDuckGo HTML results
- Why: keeps search constrained to educational domains

3. Similarity decision
- What decision: choose the most relevant candidate for context
- Deterministic: yes (max Jaccard score)
- Tool(s): lexical token overlap
- Why: transparent baseline easy to explain in class

4. Solve decision
- What decision: generate final solution using retrieved context
- Deterministic: partially non-deterministic (LLM generation)
- Tool(s): ChatOllama (local model)
- Why: local inference for reproducible demos and no cloud dependency

## Feasibility and scope
Feasibility:
- Uses lightweight Python packages and local Ollama
- Runs from a single CLI script
- Produces explicit JSON output for evaluation

In-scope:
- End-to-end local workflow
- .edu-focused retrieval
- Similarity ranking
- Local solve
- Basic evaluation and reflection artifacts

Out-of-scope:
- Production reliability engineering
- Large benchmark datasets
- Advanced semantic retrieval and formal grading pipeline

## Success criteria
- The workflow runs locally for text input and image input when OCR dependencies are installed
- Retrieved examples are .edu-linked whenever possible
- The final step returns useful step-by-step solutions for most test prompts
- Evaluation artifacts summarize strengths, failures, and technical limitations
