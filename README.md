<div align="center">

# WhatYouSaid

[![codecov](https://codecov.io/github/ericksonlopes/WhatYouSaid/branch/main/graph/badge.svg?token=8CZJARVJUE)](https://codecov.io/github/ericksonlopes/WhatYouSaid)

[![Tests](https://github.com/ericksonlopes/what-you-said/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/python-tests.yml)
[![Code Quality](https://github.com/ericksonlopes/what-you-said/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/code-quality.yml)
[![Security](https://github.com/ericksonlopes/what-you-said/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/security.ymll)

![Python](https://img.shields.io/badge/-Python-3776AB?&logo=Python&logoColor=FFFFFF)
![LangChain](https://img.shields.io/badge/-LangChain-1C3C3C?&logo=LangChain&logoColor=FFFFFF)
![Pytest|63](https://img.shields.io/badge/-Pytest-0A9EDC?&logo=Pytest&logoColor=FFFFFF)
![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?&logo=GitHub%20Actions&logoColor=FFFFFF)

</div>

WhatYouSaid is a person-centric vectorized data hub designed to extract, process, and index information about
people from any source of content — video, audio, and text — and enable powerful semantic search and Retrieval-Augmented
Generation (RAG) workflows.

This repository provides modular extractors, splitting utilities, embedding integration, and vector-store-friendly
artifacts so you can build scalable, searchable profiles and knowledge bases about individuals.

Features

- Multi-source extraction: ingest data from video (YouTube), audio transcripts, and plain text sources.
- Transcript processing and temporal splitting: break long transcripts into semantically coherent chunks suitable for
  embeddings and dense retrieval.
- Embeddings and model loader: abstracted model loading so you can swap embedding providers easily.
- Vector-store agnostic: produce embeddings and documents ready to index into your vector database of choice (FAISS,
  Pinecone, Weaviate, etc.).
- Built for RAG: designed to support retrieval-augmented generation workflows and semantic search over people-centric
  data.

Quickstart

Prerequisites:

- Python 3.12+
- A Python virtual environment (recommended)

Install the package (editable mode):

```bash
python -m pip install -e .

# Install project dependencies with uv
uv sync

# Install development dependencies (testing, linting, etc.)
uv sync --group dev
```

Dependencies are declared in `pyproject.toml`. Core dependencies are in the main list, while development tools like `pytest`, `ruff`, `mypy`, and `bandit` are managed in the `dev` group.

Run tests:

```bash
pytest -v
```

Architecture

- src/infrastructure/extractors: code to fetch raw content (e.g., YouTube transcripts, audio-to-text pipelines).
- src/infrastructure/services: processing and orchestration (splitting, model loading, embedding preparation).
- src/config: environment and settings management.
- tests/: unit and integration tests with coverage settings in pytest.ini.

Contributing

Contributions are welcome. Please:

- Open an issue to discuss major changes.
- Create a branch for your feature or fix, add tests, and submit a pull request.
- Keep code style consistent and run tests locally before submitting.

License

This project includes a LICENSE file; see it for licensing details.

Acknowledgements

Built to be an extensible foundation for building searchable, vectorized person profiles and RAG-enabled applications.

<div align="center">
    <p>Made with ❤️ by Erickson Lopes </p>

[![LinkedIn|150](https://img.shields.io/badge/LinkedIn-Erickson_Lopes-blue)](https://www.linkedin.com/in/ericksonlopes/)

</div>

