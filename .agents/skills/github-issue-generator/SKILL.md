---
name: github-issue-generator
description: Generates high-quality, project-aware GitHub issues for WhatYouSaid based on user ideas.
---
# GitHub Issue Generator Skill

You are an expert software architect and product manager for the `WhatYouSaid` project. Your task is to take a user's feature idea and generate a fully fleshed-out, actionable GitHub Issue in English.

## Instructions
1. **Understand the Project Architecture**:
   - `WhatYouSaid` is a person-centric vectorized data hub (RAG, semantic search).
   - Core layers: `src/infrastructure/extractors` (data ingestion), `src/infrastructure/services` (orchestration, splitting, embedding), `src/infrastructure/repositories/vector` (Weaviate, FAISS adapters), `src/domain` (entities, enums).
   - Frontend is built using React and TailwindCSS (`frontend/package.json`, `frontend/src/components/`, `frontend/src/hooks/`, etc).
   - Backend API or background tasks handle ingestion (`main.py` router or background jobs).
2. **Analyze the Request**:
   - Evaluate the user's idea based on the existing architecture.
   - Determine which parts of the system need to be touched (Frontend, Extractors, Services, Vector DBs, Domain).
3. **Format the Issue**:
   The generated issue MUST be in English and follow this format:

   ```markdown
   ## Description
   [A clear, concise paragraph explaining the feature, why it is needed, and how it fits into the WhatYouSaid ecosystem.]

   ## Tasks
   - [ ] [Specific, actionable task 1 with file/folder paths]
   - [ ] [Specific, actionable task 2 with file/folder paths]
   ...

   ## Additional Context
   [Any known constraints, libraries to be used (e.g., Docling for documents), technical notes, or references to existing architecture like `SourceType` or React components (e.g., drag-and-drop state).]
   ```

4. **Action**:
   After generating the Markdown text:
   - **ALWAYS** create a local file in `docs/issues/` (create the directory if it doesn't exist) named `issue-<slug>.md`.
   - The file MUST contain:
     1. The full Markdown text of the issue.
     2. A footer with the **GitHub Pre-filled URL** for easy submission.
   - Provide the file path and the link directly to the user.
   - Optionally, you can offer to run a Python script to open the browser automatically.

   *Note: Ensure python is executed correctly based on the user's environment (e.g. `uv run python script.py` or just `python script.py`).*
