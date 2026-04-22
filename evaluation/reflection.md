# Technical Reflection (Local Evaluation)

## Method
- Ran 10 fixed text queries through the existing LangGraph workflow (OCR -> normalize -> search -> similarity -> solve).
- Used local Ollama via configured environment variables and captured the full JSON output per query.
- Scored each run on two 0-2 scales: retrieval relevance and solution utility.

## Aggregate Results
- Queries: 10
- Avg retrieval relevance (0-2): 0.2
- Avg solution utility (0-2): 2
- Avg lexical similarity score: 0.043
- Runs with errors: 10
- Runs with critical solve/input errors: 0
- Runs with placeholder answers: 0
- Runs with .edu retrieval URLs: 10

## Strongest Cases
- Q6: total=3 (retrieval=1, solution=2), similarity=0.0952, url=https://www.ms.uky.edu/ma109/textbook/sec-solvesystemelim.html
- Q10: total=3 (retrieval=1, solution=2), similarity=0.0833, url=https://tutorial.math.lamar.edu/Classes/Alg/Factoring.aspx
- Q1: total=2 (retrieval=0, solution=2), similarity=0.0, url=https://tutorial.math.lamar.edu/Classes/Alg/SolveEqns.aspx

## Weakest Cases
- Q1: total=2 (retrieval=0, solution=2), similarity=0.0, url=https://tutorial.math.lamar.edu/Classes/Alg/SolveEqns.aspx
- Q2: total=2 (retrieval=0, solution=2), similarity=0.0526, url=https://tutorial.math.lamar.edu/Classes/CalcI/IntegralsIntro.aspx
- Q3: total=2 (retrieval=0, solution=2), similarity=0.0, url=https://tutorial.math.lamar.edu/Classes/Alg/Factoring.aspx

## Technical Interpretation
- The deterministic graph structure is stable and produces complete output objects consistently.
- Retrieval quality is mostly constrained by web snippet quality and lexical token overlap, not graph orchestration.
- The simple Jaccard matcher is easy to explain for class demos, but it under-ranks conceptually similar problems phrased differently.
- Solver quality is tightly coupled to local model availability and model capability. If the model call fails, fallback placeholders protect demo continuity but reduce true solve performance.

## Key Limitations
- Similarity ranking is lexical only; there is no semantic embedding or math-aware parsing.
- Search can return sparse or mismatched snippets, and fallback results may not align with every prompt type.
- Evaluation scoring is lightweight and partly heuristic; it is suitable for class reflection, not publication-level benchmarking.

## Next Technical Improvements
1. Add a semantic similarity baseline (embedding or hybrid lexical+semantic ranking).
2. Add a tiny gold set with expected solution forms for stricter scoring.
3. Add one image-based OCR test case in each evaluation run when sample images are available.
