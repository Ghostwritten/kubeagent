# Phase 02 — Cluster Context

> Status: `completed` (2026-04-10)
> Depends on: Phase 01
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement cluster connectivity management: kubeconfig parsing, multi-cluster switching, connection validation, and current context display in CLI prompt.

---

## Tasks

- [ ] **T1: kubeconfig parsing**
  - Load `~/.kube/config` (or custom path via `--kubeconfig`)
  - Parse contexts, users, clusters
  - Handle multiple kubeconfig files (KUBECONFIG env var)

- [ ] **T2: Multi-cluster listing**
  - `kubeagent clusters` command: list all available clusters
  - Show cluster name, server URL, auth type, current context marker

- [ ] **T3: Cluster switching**
  - `kubeagent switch <cluster-name>` command
  - Natural language: "switch to production"
  - Validate cluster connectivity after switch

- [ ] **T4: Connection validation**
  - Verify cluster is reachable (test API server connection)
  - Display cluster info: version, nodes count, API groups

- [ ] **T5: CLI prompt integration**
  - Show current cluster context in prompt (e.g., `kubeagent:prod $`)
  - Update prompt when context changes

---

## Acceptance Criteria

1. `kubeagent clusters` lists all available clusters from kubeconfig
2. `kubeagent switch prod-cluster` switches to target cluster
3. `kubeagent cluster info` shows cluster version and node count
4. CLI prompt displays current cluster name
5. Invalid cluster name shows error with suggestion

---

## Notes

- Use `kubernetes` Python client `config` module for kubeconfig loading
- Store current context in `~/.kubeagent/state.json` for persistence
- Defer advanced auth (exec-based, OIDC) to later Phase if complex
