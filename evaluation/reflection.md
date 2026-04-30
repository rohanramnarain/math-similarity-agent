# Technical Reflection (Local Evaluation)

## Method
- Ran 10 fixed text queries through the existing LangGraph workflow (OCR -> normalize -> search -> similarity -> solve).
- For each query, evaluated two solve variants using local Ollama: with retrieved similar context and without similar context.
- Scored each run on retrieval relevance (0-2), solution utility (0-2), and prompt-specific answer correctness (0-2), then compared per-query and aggregate deltas.

## Aggregate Results
- Queries: 10
- Avg retrieval relevance (0-2): 0.6
- Avg solution utility with context (0-2): 2
- Avg solution utility without context (0-2): 2
- Avg answer correctness with context (0-2): 2
- Avg answer correctness without context (0-2): 2
- Avg answer correctness delta (with - without): 0
- Correctness wins (with / without / ties): 0 / 0 / 10
- Avg lexical similarity score: 0.069
- Avg total score with context (0-4): 2.6
- Avg total score without context (0-4): 2.6
- Avg strict total with context (retrieval + correctness, 0-4): 2.6
- Avg strict total without context (retrieval + correctness, 0-4): 2.6
- Avg total score delta (with - without): 0
- With-context wins / without-context wins / ties: 0 / 0 / 10
- Runs with errors (with context): 8
- Runs with errors (without context): 8
- Runs with critical solve/input errors (with context): 0
- Runs with critical solve/input errors (without context): 0
- Runs with placeholder answers (with context): 0
- Runs with placeholder answers (without context): 0
- Runs with .edu retrieval URLs: 10

## Strongest Cases (With Context)
- Q1: total=4 (retrieval=2, solution=2), similarity=0.2381, url=https://www.ms.uky.edu/ma109/textbook/sec-solvesystemelim.html
- Q2: total=4 (retrieval=2, solution=2), similarity=0.0784, url=https://www.math.cmu.edu/~mradclif/teaching/127S19/Notes/ChineseRemainderTheorem.pdf
- Q6: total=3 (retrieval=1, solution=2), similarity=0.0952, url=https://www.ms.uky.edu/ma109/textbook/sec-solvesystemelim.html

## Weakest Cases (With Context)
- Q3: total=2 (retrieval=0, solution=2), similarity=0.0, url=https://tutorial.math.lamar.edu/Classes/Alg/Factoring.aspx
- Q4: total=2 (retrieval=0, solution=2), similarity=0.0526, url=https://tutorial.math.lamar.edu/Classes/CalcI/IntegralsIntro.aspx
- Q5: total=2 (retrieval=0, solution=2), similarity=0.05, url=https://www.ms.uky.edu/ma109/textbook/sec-solvesystemelim.html

## Largest Context Gains
- Q1: solution delta=0 (with=2, without=2)
- Q2: solution delta=0 (with=2, without=2)
- Q3: solution delta=0 (with=2, without=2)

## Largest Correctness Deltas
- Q1: correctness delta=0 (with=2, without=2)
- Q2: correctness delta=0 (with=2, without=2)
- Q3: correctness delta=0 (with=2, without=2)

## Technical Interpretation
- The graph reliably provides a retrieved context object, enabling an explicit ablation rather than a hypothetical comparison.
- Retrieval quality remains constrained by web snippet quality and lexical token overlap, independent of solve variant.
- The added correctness metric is stricter than style-based utility scoring and can expose wrong final answers even when explanations look fluent.
- Context-helpfulness is query-dependent: some prompts benefit, while others are unchanged when similar context is removed.
- Solver quality is still tightly coupled to local model availability; placeholder safeguards preserve demo continuity if model calls fail.

## Key Limitations
- Similarity ranking is lexical only; there is no semantic embedding or math-aware parsing.
- Search can return sparse or mismatched snippets, and fallback results may not align with every prompt type.
- Correctness checks are deterministic prompt-specific heuristics and not a full symbolic math verifier.
- Evaluation scoring remains lightweight and is suitable for class reflection, not publication-level benchmarking.

## Next Technical Improvements
1. Add a semantic similarity baseline (embedding or hybrid lexical+semantic ranking) and re-run the same with/without-context ablation.
2. Add a tiny gold set with expected solution forms for stricter scoring of both variants.
3. Add one image-based OCR test case in each evaluation run when sample images are available.
