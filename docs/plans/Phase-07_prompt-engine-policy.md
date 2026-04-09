# Phase 07 — Prompt Engine + Policy

> Status: `pending`
> Depends on: Phase 06
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement the Prompt Engine for dynamic system prompt construction and the Policy Engine for security enforcement (operation classification, confirmation, dry-run).

---

## Tasks

- [ ] **T1: Prompt Engine**
  - Compose system prompt from multiple sources:
    - Base: "You are KubeAgent, a Kubernetes expert..."
    - Cluster context: current cluster, namespace, resource summary
    - KUBEAGENT.md rules: user-defined behaviors
    - User preferences: output format, language
  - KUBEAGENT.md loading and parsing (Markdown-based)
  - Dynamic prompt update on context change

- [ ] **T2: KUBEAGENT.md support**
  - Define format: Markdown with sections for rules, conventions, preferences
  - Project-level config: namespace defaults, naming conventions, deployment rules
  - Global config: `~/.kubeagent/config.yaml`
  - Priority: KUBEAGENT.md > global config > defaults

- [ ] **T3: Policy Engine - operation classification**
  - Three levels:
    - `safe`: get, list, describe, logs, events, top → execute immediately
    - `sensitive`: scale, restart, edit configmap → prompt confirmation
    - `dangerous`: delete namespace, delete pvc, modify rbac → force confirmation + warning
  - Map every tool to a security level

- [ ] **T4: Confirmation workflow**
  - Prompt user before sensitive/dangerous operations
  - Show what will happen: "This will delete 3 pods in namespace default"
  - Danger operations: show impact analysis, require second confirmation
  - `--yes` flag to bypass confirmations (for headless/scripting)

- [ ] **T5: Dry-run mode**
  - `--dry-run` flag or in-session toggle
  - All write operations show preview without executing
  - Diff-style output: "Would create: Deployment nginx..."

---

## Acceptance Criteria

1. KUBEAGENT.md with rules is loaded and respected
2. Deleting namespace triggers two-stage confirmation
3. `--dry-run` on "apply deployment" shows YAML without creating
4. Safe operations execute immediately without prompting
5. Prompt engine includes current cluster info in system prompt

---

## Notes

- This Phase creates the "safety by design" foundation
- KUBEAGENT.md format should be simple and intuitive
- More complex policies (RBAC, whitelist/blacklist) in Phase 10
