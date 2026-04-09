# Phase 01 — Project Scaffold + First-Run Experience

> Status: `completed` (2026-04-10)
> Depends on: None
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Create the project foundation: installable package, directory structure, dev tooling, minimal CLI, and the first-run configuration experience that embodies KubeAgent's professional UX.

---

## Installation Design

| Method | Command | Note |
|--------|---------|------|
| **pipx (recommended)** | `pipx install kubeagent` | Isolated environment, no system pollution |
| **pip** | `pip install kubeagent` | Traditional |
| **Homebrew** | `brew install kubeagent` | macOS, defer to later phase |

---

## First-Run Experience Design

**Hybrid mode: auto-detect + guided setup (like Claude Code)**

```
用户运行 kubeagent
    │
    ▼
① Pre-flight Check（静默检测）
   - ~/.kube/config 是否存在
   - 环境变量: ANTHROPIC_API_KEY / OPENAI_API_KEY / KUBEAGENT_API_KEY
   - ~/.kubeagent/config.yaml 是否已存在
    │
    ▼
② 可视化概览
   🚀 Welcome to kubeagent!
   [K8s]  ✅ Found kubeconfig at ~/.kube/config
          Current context: gke-production-cluster
   [LLM]   ❌ No API Key found.
    │
    ▼
③ 缺失项引导（只引导检测不到的项）
   选择模型: 1. Anthropic  2. OpenAI  3. Ollama  4. 稍后配置
    │
    ▼
④ 连通性校验
   Testing API Key... ✅ Valid.
   Testing cluster connection... ✅ Reachable.
    │
    ▼
⑤ 保存配置
   Configuration saved to ~/.kubeagent/config.yaml
```

**Three core commands:**

| Command | Purpose | Trigger |
|---------|---------|---------|
| Auto-trigger | First-run setup wizard | No config found |
| `kubeagent init` | Full re-configuration | User manual |
| `kubeagent doctor` | Diagnose + fix issues | User manual |

**Configuration storage:**
- Path: `~/.kubeagent/`
- Config file: `~/.kubeagent/config.yaml`
- Env var overrides: `KUBEAGENT_API_KEY`, `KUBEAGENT_MODEL_ENDPOINT`, `KUBEAGENT_MODEL`
- API Key: recommend env vars (no plaintext), optional keyring support later

**Progressive behavior:**

| Scenario | Behavior |
|----------|----------|
| No kubeconfig | Prompt for path, graceful exit |
| No API Key | Guide model selection + key input |
| Incomplete config | Step-by-step, never ask everything at once |
| Expired/broken config | `kubeagent doctor` detects and guides fix |

---

## Tasks

- [ ] **T1: Initialize project with pyproject.toml**
  - Python 3.12+ requirement
  - Project metadata (name: kubeagent, version: 0.1.0, license: MIT)
  - CLI entry point: `kubeagent` command via `[project.scripts]`
  - click for CLI framework
  - Dev dependencies only: ruff, pytest, pre-commit

- [ ] **T2: Create directory structure**
  ```
  src/kubeagent/
  ├── __init__.py          # __version__
  ├── __main__.py          # python -m kubeagent
  ├── cli/
  │   ├── __init__.py
  │   ├── main.py          # click root: --version, --help, init, doctor
  │   └── setup_wizard.py  # first-run setup wizard
  ├── agent/
  │   └── __init__.py
  ├── tools/
  │   ├── __init__.py
  │   └── builtin/
  │       └── __init__.py
  ├── infra/
  │   └── __init__.py
  └── config/
      ├── __init__.py
      └── settings.py      # Pydantic config models
  ```

- [ ] **T3: Setup dev tooling**
  - ruff (linting + formatting)
  - pytest (testing)
  - pre-commit hooks
  - justfile for common commands (lint, test, format, clean)

- [ ] **T4: CLI entry point with click**
  - `kubeagent --version` prints version
  - `kubeagent --help` prints usage
  - `kubeagent` with no args triggers first-run check
  - `kubeagent init` triggers setup wizard
  - `kubeagent doctor` runs diagnostics

- [ ] **T5: First-run setup wizard**
  - Pre-flight check: detect kubeconfig, API keys, existing config
  - Visual status: show detected / missing items
  - Guided input for missing items only
  - Connectivity validation: test API key + cluster connection
  - Save to ~/.kubeagent/config.yaml
  - Skip if config already exists (unless `init`)

- [ ] **T6: `kubeagent doctor` command**
  - Re-run pre-flight checks
  - Validate existing config (API key still valid, cluster still reachable)
  - Report status with ✅/❌ indicators
  - Suggest fixes for issues

- [ ] **T7: CI basics**
  - `.gitignore` for Python project
  - `README.md` with installation + quick start
  - `LICENSE` (MIT)

---

## Acceptance Criteria

1. `pip install -e .` succeeds
2. `kubeagent --version` outputs `0.1.0`
3. `kubeagent` first run triggers setup wizard (no config exists)
4. Setup wizard detects kubeconfig and guides API key input
5. `kubeagent init` re-runs setup wizard
6. `kubeagent doctor` runs diagnostics with ✅/❌ output
7. `pytest` runs with 0 errors
8. `ruff check .` passes
9. Directory structure matches the spec

---

## Notes

- Keep dependencies minimal: click, pydantic, pyyaml (for config)
- No K8s client, no LLM libraries yet — doctor validates connectivity with minimal HTTP calls
- Homebrew formula deferred to later phase
- API key stored in config.yaml for now, keyring integration in later phase
