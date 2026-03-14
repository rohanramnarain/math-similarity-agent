This repo is a student class project.

Build a minimal Python LangChain/LangGraph workflow for a Math Similarity Solver Agent.

Project goal:
Take a math problem as text or image, search for similar solved math problems on .edu sites, choose the most similar one, and send both the original problem and the retrieved similar problem to an LLM to solve the new problem.

Priorities:
1. Keep the code simple and easy to explain
2. Use small modular files
3. Prefer readable code over abstractions
4. Add comments
5. Avoid production-scale complexity
6. Keep external dependencies minimal
7. Use placeholders only when clearly labeled
8. Restrict search to .edu domains where possible
9. Focus on these stages: OCR, search, similarity, solve
10. Every change should preserve a working demo path

Architecture preference:
- Use LangGraph for the overall workflow
- Use nodes for OCR, normalization, search, similarity ranking, and solve
- Keep the workflow mostly deterministic
- Do not build a giant autonomous agent
- Optimize for a class demo, not production

Coding preference:
- Python only
- Clear function names
- Explain each file in comments
- Include setup steps in README
