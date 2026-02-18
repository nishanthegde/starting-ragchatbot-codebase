# Repository Guidelines

## Project Structure & Module Organization
This repository is a small full-stack RAG app.

- `backend/`: FastAPI server and RAG pipeline.
- `backend/app.py`: API routes (`/api/query`, `/api/courses`) and static hosting.
- `backend/rag_system.py`, `vector_store.py`, `ai_generator.py`: retrieval + generation core.
- `frontend/`: static UI (`index.html`, `script.js`, `style.css`).
- `docs/`: source course content ingested into ChromaDB at startup.
- `run.sh`: local launcher.
- `pyproject.toml`: Python dependencies and version constraints.

## Build, Test, and Development Commands
- Use `uv` for all environment, dependency, and runtime commands. Do not use `pip` directly.
- `uv sync`: install project dependencies from `pyproject.toml`/`uv.lock`.
- `./run.sh`: start the app (runs `uvicorn` from `backend/` on port `8000`).
- `cd backend && uv run uvicorn app:app --reload --port 8000`: manual backend start.
- `uv run python main.py`: basic sanity run for the root entry script.

App URLs:
- UI: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, snake_case for functions/variables, PascalCase for classes.
- Prefer type hints (already used across backend modules).
- Keep modules focused by concern (API, retrieval, vector store, tools, session state).
- Frontend JavaScript uses camelCase (`sendMessage`, `createLoadingMessage`) and clear DOM IDs.
- Use descriptive filenames (example: `document_processor.py`, `search_tools.py`).

## Testing Guidelines
There is currently no committed automated test suite.

- Add new tests under `tests/` using `pytest`.
- Name files `test_<module>.py` and test functions `test_<behavior>()`.
- Prioritize coverage for parsing/chunking, vector search filters, and API route behavior.
- Run tests with `uv run pytest` once tests are added.

## Commit & Pull Request Guidelines
Current history uses short, lowercase summaries (e.g., `added lab files`).

- Keep commit messages concise and imperative (`add session history trimming`).
- One logical change per commit.
- PRs should include: purpose, key files changed, manual verification steps, and screenshots for UI changes.
- Link related issues/tasks when available and note any `.env` or data assumptions.
