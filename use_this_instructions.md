# use_this_instructions.md

Type these commands in Terminal from the project root.

## 1) One-time setup

```bash
cd /Users/rohanramnarain/math-similarity-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install OCR dependency (macOS):

```bash
brew install tesseract
```

## 2) Start Ollama (required for real LLM answers)

Open a separate terminal tab/window and run:

```bash
ollama serve
```

In another terminal tab/window (still in project folder):

```bash
ollama pull qwen2.5-coder:1.5b
curl -sS http://localhost:11434/api/tags
```

If `qwen2.5-coder:1.5b` is listed in the tags response, Ollama is ready.

## 3) Run one demo problem (text mode)

```bash
cd /Users/rohanramnarain/math-similarity-agent
source .venv/bin/activate
python main.py --text "Solve 2x + 3 = 11"
```

You should see JSON with:
- `normalized_user_problem`
- `retrieved_similar_problem`
- `similarity_score`
- `final_solution`
- `errors`

## 4) Run image mode (optional)

```bash
cd /Users/rohanramnarain/math-similarity-agent
source .venv/bin/activate
python main.py --image path/to/problem.png
```

## 5) Run full evaluation (10 fixed problems)

```bash
cd /Users/rohanramnarain/math-similarity-agent
source .venv/bin/activate
python evaluation/run_evaluation.py
```

This command writes:
- `evaluation/results.json`
- `evaluation/reflection.md`

## 6) View the generated results in terminal

```bash
cat evaluation/reflection.md
```

```bash
python -m json.tool evaluation/results.json
```

## 7) Quick repeat workflow (after setup is done)

```bash
cd /Users/rohanramnarain/math-similarity-agent
source .venv/bin/activate
python main.py --text "Factor x^2 + 5x + 6"
python evaluation/run_evaluation.py
cat evaluation/reflection.md
```

## Notes
- If Ollama is not running, the app still runs but returns a clearly labeled placeholder solution.
- Search is restricted to `.edu` candidates when possible, with fallback examples for demo reliability.
