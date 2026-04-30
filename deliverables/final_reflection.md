# Final Reflection: Math Similarity Solver Agent

Math assistance is already here; math assistance has always been here. The question in this project was never whether students needed another large autonomous system, but whether a small, explainable workflow could retrieve a related solved problem and then use that context to solve a new one in a reliable way. 

In that spirit, I built a minimal LangGraph pipeline with five explicit stages: OCR, normalization, search, similarity ranking, and solve. Each stage has one clear role, each transition is visible, and each decision can be explained in plain language during a class demo.

The system is deterministic where determinism adds trust and debuggability, and generative where generation is actually needed. If a user provides raw text, the workflow proceeds directly; if a user provides an image, OCR extracts text first. The search stage constructs a query with a .edu preference so retrieved material tends to come from educational domains. 

The similarity stage ranks candidates with Jaccard overlap and picks one best match. The solve stage then passes both the original prompt and the retrieved similar problem to the local LLM, which produces the final steps. Instead of a giant autonomous agent pretending to reason over everything, it is a constrained and legible pipeline that performs one bounded task end to end.

Evaluation already exists in this project as a reproducible local harness that judges outputs across ten fixed prompts and writes JSON plus a technical report. The current harness evaluates three dimensions: retrieval relevance (0-2), solution utility (0-2), and prompt-specific answer correctness (0-2). It also runs an ablation that compares solving with retrieved similar context versus solving without that context. 

In the latest run, average retrieval relevance was 0.2 out of 2, average solution utility was 2.0 out of 2 for both variants, and average lexical similarity was 0.043. The stricter correctness metric showed a meaningful difference: 1.8 out of 2 with context versus 2.0 out of 2 without context, with one prompt where context correlated with a worse final answer (derivative of x^3 + 2x). All runs still produced .edu retrieval URLs, no critical solve/input failures, and no placeholder outputs. 

In practice, this means the system is stable as a demo pipeline, but context quality and ranking quality still need to improve before retrieved examples consistently help final correctness.

These outcomes follow directly from the project’s deliberate tradeoffs. I chose lexical Jaccard matching because it is easy to inspect and explain, even though embedding-based methods would likely improve semantic recall. I enforced .edu filtering because source quality and trust signaling matter for a student-facing demo, even though stricter filtering can reduce coverage. 

I also kept fallback candidates so the system still demonstrates a complete path when network search is weak or unavailable. For a class project, these tradeoffs are not flaws in execution; they are explicit design choices that prioritize transparency, reproducibility, and instructional clarity over maximal benchmark performance.

The limitations are equally clear and should be named without euphemism. Lexical similarity misses conceptually similar problems when wording diverges. Web snippets are often shallow, noisy, or incomplete, so the context sent to the solver can be uneven. 

The current scoring rubric is lightweight and partially heuristic, which makes it useful for rapid iteration but less authoritative for formal comparison. These are not hidden edge cases but structural constraints of the present implementation, and they define exactly where future effort should go.

The project also sits within a broader social and cultural reality about educational technology. At the individual level, the workflow lowers activation energy by turning a blank problem into a guided path, but that same convenience can encourage imitation without understanding if used passively. 

At the societal level, retrieval-based tutoring systems can silently define what counts as a legitimate method by elevating what is indexed, searchable, and domain-filtered. A .edu constraint can improve perceived credibility, yet it also narrows the range of knowledge that appears. In other words, technical constraints are not neutral; they shape what learners see, trust, and repeat.

What this project demonstrates most clearly is that outcomes in agentic systems are governed as much by orchestration as by model choice. Routing logic, retrieval policy, similarity criteria, and fallback behavior all materially determine whether the final answer is useful. 

The significance of this work, then, is not that it solves every math problem perfectly, but that it offers a working, explainable, modular example of how deterministic scaffolding can make LLM behavior more dependable in practice while still exposing measurable limits.

The next version should strengthen retrieval first, then evaluation depth, then multimodal reliability. Replacing purely lexical ranking with semantic retrieval would improve match quality for paraphrased or structurally similar problems. 

Adding a small hand-labeled benchmark with a stricter rubric would make progress claims more credible and comparable over time. Expanding routine OCR image tests in the evaluation harness would reveal extraction failures earlier and protect the end-to-end demo path.
