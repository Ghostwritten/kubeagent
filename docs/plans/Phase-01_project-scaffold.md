# Phase 01 — Project Scaffold

> Status: `pending`
> Depends on: None
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Create the project foundation: directory structure, build system, dev tooling, and a minimal CLI entry point that proves the package is installable and runnable.

---

## Tasks

- [ ] **T1: Initialize project with pyproject.toml**
  - Python 3.11+ requirement
  - Project metadata (name: kubeagent, version: 0.1.0, license: MIT)
  - CLI entry point: `kubeagent` command via `[project.scripts]`
  - Dependencies: (none yet — only dev dependencies)

- [ ] **T2: Create directory structure**
  ```
  src/kubeagent/
  ├── __init__.py
  ├── cli/
  │   └── __init__.py
  ├── agent/
  │   └── __init__.py
  ├── tools/
  │   ├── __init__.py
  │   └── builtin/
  │       └── __init__.py
  ├── infra/
  │   └── __init__.py
  └── config/
      └── __init__.py
  ```

- [ ] **T3: Setup dev tooling**
  - ruff (linting + formatting)
  - pytest (testing)
  - pre-commit hooks
  - Makefile or justfile for common commands (lint, test, format)

- [ ] **T4: Minimal CLI entry point**
  - `kubeagent --version` prints version
  - `kubeagent --help` prints usage
  - `kubeagent` with no args prints welcome message
  - Use `click` or `argparse` for CLI parsing

- [ ] **T5: CI basics**
  - `.gitignore` for Python project
  - Basic `README.md` with project description
  - GitHub Actions workflow for lint + test (optional, can defer)

---

## Acceptance Criteria

1. `pip install -e .` succeeds
2. `kubeagent --version` outputs `0.1.0`
3. `pytest` runs with 0 errors (even if 0 tests)
4. `ruff check .` passes
5. Directory structure matches the spec

---

## Notes

- Keep dependencies minimal at this stage — no K8s client, no LLM libraries yet
- CLI framework choice (click vs argparse) to be decided during implementation
