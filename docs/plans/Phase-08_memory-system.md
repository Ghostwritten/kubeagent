# Phase 08 — Memory System

> Status: `pending`
> Depends on: Phase 07
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement persistent memory that survives across sessions: user preferences, cluster profiles, fault knowledge, and audit logs.

---

## Tasks

- [ ] **T1: Storage layer**
  - SQLite database at `~/.kubeagent/memory.db`
  - Schema design: tables for preferences, cluster_profiles, fault_knowledge, audit_log
  - Migration support (for future schema changes)
  - Storage size management (max_size_mb config)

- [ ] **T2: User preferences memory**
  - Auto-detect and store: preferred output format, favorite namespaces, common operations
  - Explicit save: user says "remember that I prefer table output"
  - Load preferences into prompt context on startup
  - User can view and clear preferences

- [ ] **T3: Cluster profile memory**
  - Per-cluster storage: topology, characteristics, common issues
  - Auto-populate on first connect (node count, K8s version, installed CRDs)
  - Update incrementally as agent learns more about the cluster
  - Inject relevant cluster profile into prompt

- [ ] **T4: Fault knowledge base**
  - Store past diagnoses: symptom → root cause → solution
  - Query when similar symptoms appear
  - User can confirm or invalidate stored knowledge

- [ ] **T5: Audit log**
  - Append-only log of all mutating operations
  - Fields: timestamp, user, cluster, namespace, operation, resource, result
  - Redact sensitive values (secrets, tokens)
  - `kubeagent audit` or conversational query to review audit history
  - Configurable retention (expiration_days)

- [ ] **T6: Memory integration with agent**
  - MemoryManager class: unified interface for all memory types
  - Inject relevant memories into prompt context
  - Post-operation: store outcomes automatically
  - Privacy: never store K8s secret values

- [ ] **T7: Tests**
  - Unit tests for each memory type CRUD
  - Test expiration/cleanup
  - Test audit log redaction
  - Test memory injection into prompt

---

## Acceptance Criteria

1. User preference "I prefer YAML output" persists across sessions
2. Cluster profile auto-populated on first connection
3. Past diagnosis recalled when similar issue occurs
4. `kubeagent audit` shows recent mutating operations
5. Secrets and tokens never appear in memory database
6. Memory respects `expiration_days` config

---

## Files Created/Modified

- `src/kubeagent/agent/memory.py` — MemoryManager
- `src/kubeagent/infra/storage.py` — SQLite storage layer
- `tests/unit/test_memory.py`
- `tests/unit/test_storage.py`
