# Phase 03 — K8s Executor + Read Tools

> Status: `completed`
> Depends on: Phase 02
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement the unified K8s Executor interface (Python Client) and the core read-only tools that query cluster state without making changes.

---

## Tasks

- [ ] **T1: KubeExecutor interface**
  - Abstract base class `KubeExecutor`
  - Methods: `get()`, `list()`, `watch()`, `logs()`, `exec()`
  - Unified return format (structured dict/JSON, not raw objects)

- [ ] **T2: PythonClientExecutor implementation**
  - Implement `KubeExecutor` using official `kubernetes` Python client
  - Handle connection from current cluster context
  - Proper error handling: connection errors, timeout, API errors

- [ ] **T3: Read tools - Core**
  - `get_pods(namespace=None, labels=None)` — list pods with status, restarts, age
  - `get_nodes()` — list nodes with conditions, allocatable resources
  - `get_namespaces()` — list all namespaces
  - `get_services(namespace=None)` — list services with type, cluster IP
  - `get_configmaps(namespace=None)` — list configmaps

- [ ] **T4: Read tools - Detailed**
  - `describe_resource(kind, name, namespace)` — get full resource details (like kubectl describe)
  - `get_events(namespace=None, kind=None)` — recent events sorted by time
  - `get_resource_quota(namespace)` — resource quota usage
  - `get_pod_logs(name, namespace, container, tail_lines)` — fetch logs

- [ ] **T5: Tool registry foundation**
  - Basic tool registration system
  - Tools auto-discovered and registered at startup
  - Tool metadata: name, description, parameters, security level

---

## Acceptance Criteria

1. Code can call `get_pods("default")` and receive structured list of pods with status
2. `get_nodes()` returns node conditions and allocatable resources
3. `describe_resource("deployment", "nginx", "default")` returns full deployment details
4. All tools handle errors gracefully (cluster unreachable → clear error message)
5. Tools can be called programmatically (not yet via natural language)

---

## Notes

- Focus on Python Client only in this Phase, kubectl wrapper comes in Phase 04
- Return types should be Pydantic models for type safety
- Keep tool logic thin — just API calls, no complex business logic
