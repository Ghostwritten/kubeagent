# Phase 10 — Skill + Hook + Headless

> Status: `pending`
> Depends on: Phase 09
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement the Skill system (reusable workflows), Hook Engine (event-driven automation), and Headless mode (non-interactive operation for CI/CD).

---

## Tasks

- [ ] **T1: Skill system foundation**
  - Skill definition format: Markdown-based (similar to Claude Code skills)
  - Skill metadata: name, description, trigger conditions, required tools
  - Skill loading from `skills/` directory
  - Skill registry and invocation via `/skill-name`

- [ ] **T2: Built-in skills**
  - `/diagnose` — multi-dimensional cluster/workload diagnosis
  - `/deploy` — guided deployment with best-practice checks
  - `/rollback` — safe rollback with verification
  - `/security-audit` — security posture assessment
  - Each skill orchestrates multiple tools + SubAgents

- [ ] **T3: Hook Engine**
  - Hook lifecycle events: `pre-apply`, `post-apply`, `pre-delete`, `post-delete`, `pre-deploy`, `post-deploy`, `on-error`, `on-connect`, `on-diagnose`
  - Hook definition in `~/.kubeagent/hooks.yaml` or KUBEAGENT.md
  - Hook execution order: Policy check → pre-hook → user confirmation → operation → post-hook → on-error (if failed)
  - Hooks can abort operations (pre-hook returns error → operation cancelled)

- [ ] **T4: Headless mode**
  - `kubeagent --headless "query"` — single query, exit after response
  - `--json` / `--yaml` / `--text` output format flags
  - `--batch <file>` — execute multiple queries from file
  - `--exit-code` — return 0 for success, 1 for failure (CI/CD friendly)
  - Pipe-friendly: `kubeagent --headless --json "list unhealthy pods" | jq`

- [ ] **T5: Policy Engine enhancement**
  - Role-based access: admin / operator / viewer
  - Operation whitelist/blacklist per cluster
  - Resource whitelist/blacklist (protect namespaces)
  - Custom policy rules via config

- [ ] **T6: User-defined skills**
  - User can create custom skills in `~/.kubeagent/skills/`
  - Skill validation on load
  - Community skill installation: `kubeagent skill install <url>`

---

## Acceptance Criteria

1. `/diagnose` skill runs multi-step diagnosis workflow
2. `pre-deploy` hook triggers before deployment and can abort
3. `kubeagent --headless "list pods" --json` outputs JSON and exits
4. `kubeagent --batch commands.txt` executes all queries
5. Role-based access blocks dangerous operations for `viewer` role
6. User-defined skill loads and executes correctly

---

## Milestone: MVP Beta

Phase 10 completion marks **MVP Beta** — professional diagnostics, automation, and headless mode ready for production use.

---

## Notes

- Skill format should be simple enough for community contribution
- Hook execution must be fast — avoid blocking operations
- Headless mode is critical for CI/CD integration
