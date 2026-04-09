# KubeAgent — AGENTS.md

> This document defines the identity, capabilities, behavior rules, and constraints for the KubeAgent project.
> It serves as the foundational context for all development and contribution activities.

---

## Project Identity

**Name**: KubeAgent
**Type**: Open-source CLI intelligent agent
**Purpose**: Manage Kubernetes clusters through natural language conversation
**Repository**: github.com/user/kubeagent
**License**: MIT

---

## Core Architecture

KubeAgent is built on a **four-layer architecture**:

```
Interface Layer  →  Agent Layer  →  Capability Layer  →  Infrastructure Layer
```

| Layer | Components |
|-------|-----------|
| **Interface** | CLI REPL, Headless mode, Shell passthrough (`!`), Skill dispatch (`/`), Prompt Engine |
| **Agent** | Main Agent (Pydantic AI), SubAgent Dispatcher, Memory Manager, Hook Engine, Policy Engine |
| **Capability** | Tool Registry, Skill Registry — Built-in / User-defined / Plugin tools |
| **Infrastructure** | Model Router (LiteLLM), Cluster Context, K8s Executor (Python Client + kubectl), Storage (SQLite) |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Agent Framework | Pydantic AI |
| Model Interface | LiteLLM (100+ models: Ollama / Claude / GPT / Gemini) |
| K8s SDK | kubernetes (official Python client) |
| K8s CLI | kubectl (subprocess, supplementary) |
| CLI UI | Rich + prompt_toolkit |
| Config | Pydantic + YAML |
| Storage | SQLite + local files |
| Packaging | pip / pipx |

---

## Design Principles

1. **Natural Language First** — Conversation-driven interaction, like Claude Code
2. **Professional Output** — Rich tables for data, Markdown for analysis, mixed rendering
3. **Safety by Design** — Three-tier operation classification, RBAC, dry-run, confirmation flows
4. **Model Agnostic** — Local (Ollama) and cloud (Claude/GPT/Gemini) with intelligent routing
5. **Open & Extensible** — Plugin system, community Skills, user-defined Tools
6. **Incremental Delivery** — 12 lightweight phases, each producing a usable increment

---

## Installation

| Method | Command | Note |
|--------|---------|------|
| **pipx (recommended)** | `pipx install kubeagent` | Isolated environment, no system pollution |
| **pip** | `pip install kubeagent` | Traditional |
| **Homebrew** | `brew install kubeagent` | macOS (later phase) |

## First-Run Experience

**Hybrid mode: auto-detect + guided setup (like Claude Code)**

- **Auto-trigger**: First run detects environment, guides only missing items
- **`kubeagent init`**: Full re-configuration
- **`kubeagent doctor`**: Diagnose + fix issues

**Pre-flight check on every run:**
- Detect `~/.kube/config` and current context
- Detect API keys via env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `KUBEAGENT_API_KEY`)
- Detect `~/.kubeagent/config.yaml`

**Configuration storage:**
- Path: `~/.kubeagent/`
- Config: `~/.kubeagent/config.yaml`
- Env var overrides: `KUBEAGENT_API_KEY`, `KUBEAGENT_MODEL_ENDPOINT`, `KUBEAGENT_MODEL`

## Interaction Model

- **Primary**: Conversational dialogue (natural language)
- **Shell passthrough**: `!command` executes shell commands directly
- **Skill invocation**: `/skill-name` triggers predefined workflows (e.g., `/diagnose`, `/deploy`)
- **Headless**: `kubeagent --headless "query"` for CI/CD and scripting

---

## Component Overview

### Prompt Engine
Composes system prompts from: base template + KUBEAGENT.md rules + cluster context + user preferences.
Priority: KUBEAGENT.md > config.yaml > defaults.

### Main Agent
Central reasoning engine using Pydantic AI. Workflow: intent recognition → memory query → policy check → task planning → tool selection → result synthesis.

### SubAgent System
Dynamic creation at runtime. Independent tool sets and model selection. Parallel execution via asyncio. Ephemeral lifecycle.

### Tool System
- **Built-in**: get_pods, describe_resource, read_logs, apply_yaml, delete_resource, scale, exec, etc.
- **User-defined**: custom scripts, kubectl plugins
- **Plugin**: Helm, Istio, ArgoCD ecosystem tools
- Each tool declares security level: `safe` / `sensitive` / `dangerous`

### Skill System
Reusable workflows: `/diagnose`, `/deploy`, `/rollback`, `/security-audit`, `/migrate`, etc.
Markdown-based definitions, community-contributable.

### Hook Engine
Event-driven automation: `pre-apply`, `post-deploy`, `on-error`, `on-connect`, etc.
Can abort operations on failure.

### Memory Manager
Five types: session context, user preferences, cluster profiles, fault knowledge, audit log.
SQLite storage with expiration and privacy controls.

### Policy Engine
- Three-tier: safe (immediate) → sensitive (confirm) → dangerous (double-confirm + warning)
- RBAC: admin / operator / viewer
- Whitelist/blacklist per operation and resource
- Dry-run mode for all mutations

### Model Router
Four strategies (user-selectable): complexity-based, cost-based, availability-fallback, manual.
SubAgents can use lighter models than Main Agent.

### K8s Executor
Unified interface: Python Client (primary) + kubectl (supplementary).
Auto-detect kubectl, graceful degradation if absent.
All outputs normalized to structured data models.

---

## Security Rules

1. **Operation classification**: Every K8s operation is tagged safe/sensitive/dangerous
2. **Confirmation flow**: Sensitive → "Proceed? [y/N]", Dangerous → type resource name to confirm
3. **Dry-run**: `--dry-run` shows preview without executing any mutations
4. **No secret storage**: Memory system never stores K8s secrets, tokens, or credentials
5. **Injection prevention**: kubectl calls use argument lists, never shell string interpolation
6. **Audit trail**: All mutating operations logged with timestamp, user, cluster, resource, result

---

## Model Configuration

```yaml
model:
  default: claude-sonnet-4-20250514
  fallback: [gpt-4o, ollama/qwen2.5]
  strategy: complexity  # complexity | cost | availability | manual
  subagent_model: claude-haiku-4-5-20251001
  cost:
    monthly_budget: 50
    currency: USD
```

---

## Configuration Hierarchy

| File | Purpose | Format |
|------|---------|--------|
| `KUBEAGENT.md` | Project-level behavioral rules | Natural language (Markdown) |
| `~/.kubeagent/config.yaml` | Global technical settings | Structured YAML |
| `~/.kubeagent/hooks.yaml` | Hook definitions | Structured YAML |

**Priority**: KUBEAGENT.md > config.yaml > defaults

---

## Implementation Roadmap

12 phases with three milestones:

| Milestone | After Phase | Status |
|-----------|-------------|--------|
| **MVP Alpha** | Phase 07 — Prompt Engine + Policy | `pending` |
| **MVP Beta** | Phase 10 — Skill + Hook + Headless | `pending` |
| **v1.0 小满贯** | Phase 12 — MCP Server + Ecosystem | `pending` |

**Full plan**: `docs/plans/00-master-plan.md`

---

## File Structure

```
kubeagent/
├── src/kubeagent/
│   ├── cli/           # Interface Layer
│   ├── agent/         # Agent Layer
│   ├── tools/         # Capability Layer (builtin/, kubectl.py)
│   ├── infra/         # Infrastructure Layer
│   └── config/        # Configuration
├── skills/            # Built-in skills
├── plugins/           # Plugin directory
├── tests/             # unit/, integration/, fixtures/
└── docs/
    ├── specs/         # Architecture design (WHY & WHAT)
    ├── plans/         # Phase plans (HOW & WHEN)
    └── decisions/     # Architecture Decision Records
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/specs/2026-04-09-kubeagent-design.md` | Architecture design: WHY and WHAT |
| `docs/plans/00-master-plan.md` | Roadmap: phase overview, dependency graph, execution rules |
| `docs/plans/Phase-XX_*.md` | Phase details: tasks, acceptance criteria, status |
| `docs/decisions/` | ADR: architecture decisions and rationale |
