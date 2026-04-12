# KubeAgent Distribution & CI/CD Design

> Date: 2026-04-13
> Status: Approved
> Repository: https://github.com/Ghostwritten/kubeagent.git

---

## Goal

Add complete distribution infrastructure for KubeAgent v1.0, supporting four installation methods: PyPI, Homebrew, Docker (GHCR + Docker Hub), and GitHub Releases.

---

## Architecture

Two GitHub Actions workflows with clear separation of concerns:

### Workflow 1: `ci.yml` — Continuous Integration

- **Trigger**: push to `main`, pull requests to `main`
- **Jobs**:
  - `lint`: ruff check + format validation
  - `test`: pytest on Python 3.12 + 3.13

### Workflow 2: `release.yml` — Release Pipeline

- **Trigger**: push tag matching `v*` (e.g. `v1.0.0`)
- **Jobs** (with dependencies):

```
test (gate)
  ├── publish-pypi (build wheel/sdist → PyPI)
  ├── publish-docker (multi-arch → GHCR + Docker Hub)
  ├── github-release (changelog + artifacts)
  └── update-homebrew (update tap formula)
```

---

## Components

### 1. CI Workflow (`.github/workflows/ci.yml`)

- Matrix: Python 3.12, 3.13
- Steps: checkout → setup-python → install deps → ruff lint → pytest
- Runs on: `ubuntu-latest`

### 2. Release Workflow (`.github/workflows/release.yml`)

- Gate job: run full test suite before any publishing
- Version extraction: strip `v` prefix from tag (`v1.0.0` → `1.0.0`)

### 3. PyPI Publishing

- Action: `pypa/gh-action-pypi-publish`
- Build: `python -m build` (wheel + sdist)
- Secret: `PYPI_API_TOKEN` (repository secret)
- Trusted publishing via OIDC preferred if configured

### 4. Docker Image

- Base: `python:3.12-slim` (multi-stage build)
- Stage 1 (builder): install dependencies
- Stage 2 (runtime): copy installed packages, minimal image
- Tags: `latest`, `vX.Y.Z`, `vX.Y`, `vX`
- Push to:
  - GHCR: `ghcr.io/ghostwritten/kubeagent` (uses `GITHUB_TOKEN`)
  - Docker Hub: `ghostwritten/kubeagent` (uses `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN`)

### 5. `.dockerignore`

Exclude: `.git`, `.venv`, `__pycache__`, `tests/`, `docs/`, `.github/`, `*.pyc`

### 6. GitHub Release

- Action: `softprops/action-gh-release`
- Auto-generate changelog from commits since last tag
- Upload: wheel and sdist as release assets

### 7. Homebrew Formula

- Tap repository: `Ghostwritten/homebrew-tap` (separate repo, auto-updated)
- Formula file: `homebrew/kubeagent.rb` (template in this repo)
- Release job updates the tap repo via GitHub API
- Formula installs from PyPI source tarball with sha256 verification

---

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `PYPI_API_TOKEN` | Publish to PyPI |
| `DOCKERHUB_USERNAME` | Docker Hub login |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `HOMEBREW_TAP_TOKEN` | PAT with repo scope to push to homebrew-tap repo |

`GITHUB_TOKEN` is auto-provided for GHCR and GitHub Release.

---

## File Manifest

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | PR/push CI (lint + test) |
| `.github/workflows/release.yml` | Tag-triggered release pipeline |
| `Dockerfile` | Multi-stage Docker build |
| `.dockerignore` | Exclude files from Docker context |
| `homebrew/kubeagent.rb` | Homebrew formula template |

---

## Version Strategy

- Source of truth: git tag (`v1.0.0`)
- `pyproject.toml` and `__init__.py` use `version = "1.0.0"` statically
- Release workflow validates tag matches package version
- Developers bump version manually before tagging

---

## Release Procedure

```bash
# 1. Bump version in pyproject.toml and __init__.py
# 2. Commit: "chore: bump version to 1.0.0"
# 3. Tag and push:
git tag v1.0.0
git push origin main --tags
# 4. release.yml auto-publishes to all channels
```
