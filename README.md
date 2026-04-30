# Math Similarity Solver Agent

Minimal class-project prototype using Python + LangGraph.

## What it does
Given a math problem as text or image:
1. Runs OCR (if image input)
2. Normalizes the problem text
3. Builds a .edu-restricted search query
4. Pulls candidate solved problems from web results
5. Computes lexical similarity and picks the best match
6. Sends user problem + similar problem to a local Hugging Face Gemma model
7. Returns normalized problem, best match, score, and final solution

## Project structure
- main.py: CLI entrypoint that runs the graph and prints JSON output
- graph.py: LangGraph state and node wiring
- prompts.py: Prompt text helper for solver
- tools/ocr_tool.py: OCR helper using pytesseract
- tools/search_tool.py: .edu-focused web search helper
- tools/similarity_tool.py: Lexical similarity helper
- tools/solve_tool.py: Hugging Face Gemma local solve helper (with Ollama fallback)

## Setup
1. Create and activate a virtual environment:
	- python3 -m venv .venv
	- source .venv/bin/activate
2. Install dependencies:
	- pip install -r requirements.txt
3. Install Tesseract OCR (required for image mode):
	- macOS (Homebrew): brew install tesseract
	- Ubuntu/Debian: sudo apt-get install tesseract-ocr
	- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
4. Configure environment variables:
	- cp .env.example .env
	- Default backend is Hugging Face with HF_MODEL_ID=google/gemma-4-E2B-it
	- Set HF_TOKEN if model access requires authentication
	- Optional fallback: set LLM_BACKEND=ollama and configure OLLAMA_MODEL/OLLAMA_BASE_URL

## Run
Text mode:
- python main.py --text "Solve 2x + 3 = 11"

Image mode:
- python main.py --image path/to/problem.png

## Notes
- This is intentionally simple and classroom-demo friendly.
- Search node tries DuckDuckGo HTML and falls back to static .edu examples if needed.
- Similarity uses simple lexical overlap as a baseline.
- Solver uses Hugging Face local inference with default model google/gemma-4-E2B-it.

## Local evaluation
Run the 10-query local evaluation and generate a summary report:
- python evaluation/run_evaluation.py

Artifacts written by the evaluation script:
- evaluation/results.json
- evaluation/reflection.md

Class deliverables:
- deliverables/proposal.md
- deliverables/final_reflection.md
