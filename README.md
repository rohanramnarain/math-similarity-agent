# Math Similarity Solver Agent

Minimal class-project prototype using Python + LangGraph.

## What it does
Given a math problem as text or image:
1. Runs OCR (if image input)
2. Normalizes the problem text
3. Builds a .edu-restricted search query
4. Pulls candidate solved problems from web results
5. Computes simple vector similarity and picks the best match
6. Sends user problem + similar problem to a local Ollama model
7. Returns normalized problem, best match, score, and final solution

## Project structure
- main.py: CLI entrypoint that runs the graph and prints JSON output
- graph.py: LangGraph state and node wiring
- prompts.py: Prompt text helper for solver
- tools/ocr_tool.py: OCR helper using pytesseract
- tools/search_tool.py: .edu-focused web search helper
- tools/similarity_tool.py: Simple bag-of-words cosine similarity
- tools/solve_tool.py: ChatOllama-based local solve helper with placeholder fallback

## Setup
1. Create and activate a virtual environment:
	- python3 -m venv .venv
	- source .venv/bin/activate
2. Install dependencies:
	- pip install -r requirements.txt
3. Install and start Ollama (local):
	- Install from https://ollama.com/download
	- ollama serve
	- ollama pull qwen3.5:4b
4. Configure environment variables:
	- cp .env.example .env
	- Optional: change OLLAMA_MODEL or OLLAMA_BASE_URL in .env

## Run
Text mode:
- python main.py --text "Solve 2x + 3 = 11"

Image mode:
- python main.py --image path/to/problem.png

## Notes
- This is intentionally simple and classroom-demo friendly.
- Search node tries DuckDuckGo HTML and falls back to static .edu examples if needed.
- Similarity currently uses basic token vectors.
- Solver uses ChatOllama with default local model qwen3.5:4b.
- TODO: Replace similarity with Math2Vec or other math-aware embeddings.
