# Math Similarity Agent Flow

This document shows the end-to-end workflow at a high level.

## Visual Flow

```mermaid
flowchart TD
    A[Input]
    A1[Text Problem]
    A2[Image Problem]
    B[OCR Node]
    C[Normalize Node]
    D[Search Node (.edu-focused query)]
    E[Similarity Node (best match)]
    F[Solve Node (LLM)]
    G[Output JSON]

    A --> A1 --> C
    A --> A2 --> B --> C
    C --> D --> E --> F --> G
```

## Step-by-Step

1. Input
- User provides either a text math problem or an image containing a problem.

2. OCR
- If input is an image, OCR extracts text from that image.

3. Normalize
- The problem text is cleaned (lowercased and whitespace-normalized).

4. Search
- The app builds a .edu-focused query and fetches candidate solved problems.
- Provider order is: Bing HTML -> Bing RSS -> DuckDuckGo HTML -> static fallback.
- If live providers fail, fallback candidates are used so the demo still runs.
- Recent live pulls included .edu pages like Paul's Online Math Notes (tutorial.math.lamar.edu) and MIT OpenCourseWare (ocw.mit.edu).

5. Similarity
- Candidates are ranked by lexical Jaccard overlap.
- The highest-scoring candidate is selected as the best match.

6. Solve
- The normalized user problem and selected similar problem are sent to the LLM.
- The model generates a step-by-step solution.

7. Output
- The CLI returns structured JSON including:
  - normalized problem
  - search metadata (query/provider/fallback/candidate count)
  - retrieved similar problem
  - similarity score
  - final solution
  - errors/warnings

## Browser / Headless Usage

- This project does not currently use a headless browser framework (no Playwright, Selenium, or Puppeteer in the runtime flow).
- Search is done with direct HTTP requests using `requests`:
  - Bing HTML endpoint
  - Bing RSS endpoint
  - DuckDuckGo HTML endpoint
- If those providers do not return usable `.edu` results, the workflow uses static `.edu` fallback examples.
