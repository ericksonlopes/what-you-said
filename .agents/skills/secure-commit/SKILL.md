---
name: secure-commit
description: Orchestrates a safe git commit process by running linters (ruff), type checks (mypy), security scans (bandit), and tests (pytest) before committing. Use this when the user wants to commit changes or "wrap up" a task safely.
---

# Secure Commit

This skill enforces a rigorous validation pipeline before any code is committed to the repository. It ensures that only high-quality, safe, and tested code reaches the version control system.

## Workflow

When triggered, follow these steps in order. If any step fails, stop immediately, report the error, and do NOT proceed with the commit.

### 1. Preparation
- Ensure all relevant files are staged.
- Validate that the repository is in a clean state for committing.

### 2. Linting & Formatting (Ruff)
- Run `ruff check . --fix` to identify and automatically fix common linting issues.
- Run `ruff format .` to ensure consistent code styling.

### 3. Static Type Checking (Mypy)
- Run `mypy .` to verify type safety across the project.
- Address any type errors before proceeding.

### 4. Security Scan (Bandit)
- Run `bandit -r src/` to scan for common security vulnerabilities in the source code.
- Ensure no high-severity issues are present.

### 5. Test Presence Validation (New)
- Identify all staged files in `src/` using `git diff --cached --name-only`.
- For each file in `src/application/`, `src/infrastructure/`, or `src/presentation/`, verify if a corresponding test file exists in `tests/` (e.g., `src/path/file.py` -> `tests/path/test_file.py`).
- **Exemptions**: `__init__.py`, and files inside `domain/entities/`, `dtos/`, `schemas/`, `mappers/` are exempt from this mandatory check.
- If a required test file is missing, inform the user and ask for confirmation or a test creation before proceeding.

### 6. Automated Testing (Pytest)
- Run `pytest` to execute the full test suite.
- Ensure all tests pass.

## Final Commit
- **USER PERMISSION REQUIRED**: NEVER perform the git commit automatically. Even if all checks pass, you MUST ask the user for explicit permission to commit.
- **ZERO TOLERANCE**: Only if ALL previous steps passed with **zero remaining issues** (0 ruff errors, 0 mypy errors, 100% pytest success), and after receiving user approval, perform the git commit.
- Use a clear, concise, and descriptive commit message that follows the project's established style.
- Confirm the successful commit with `git status`.

## Guardrails
- **NEVER** use `--no-verify` or bypass hooks if they exist.
- **NEVER** commit if tests fail.
- **NEVER** commit if high-severity security issues are detected by Bandit.
- Provide a summary of the checks performed (e.g., "Ruff: Passed, Mypy: Passed, Bandit: Passed, Tests: Passed").
