# Phase 04 — K8s Write Tools + kubectl

> Status: `completed`
> Depends on: Phase 03
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Implement write operations (apply, delete, scale, restart) and the kubectl wrapper for operations that Python Client handles poorly (exec, top, apply -f).

---

## Tasks

- [ ] **T1: Write tools - Core**
  - `apply_yaml(yaml_content, namespace)` — create or update resources from YAML
  - `delete_resource(kind, name, namespace)` — delete a resource
  - `scale_resource(kind, name, namespace, replicas)` — scale deployment/statefulset

- [ ] **T2: Write tools - Operations**
  - `restart_pod(name, namespace)` — delete pod to trigger restart
  - `cordon_node(name)` — mark node as unschedulable
  - `uncordon_node(name)` — mark node as schedulable
  - `drain_node(name, force=False)` — drain node (delete pods, cordon)

- [ ] **T3: kubectl wrapper**
  - Detect if kubectl is installed (graceful fail if not)
  - Wrapper for: `kubectl exec`, `kubectl top`, `kubectl apply -f`
  - Use argument lists, NOT shell string拼接 (security)
  - Parameter whitelist validation before execution

- [ ] **T4: Tool registry enhancement**
  - Each tool declares security level: `safe`, `sensitive`, `dangerous`
  - Tool documentation: name, description, parameters, examples

- [ ] **T5: Execute validation**
  - Apply operation returns what was created/updated
  - Delete operation confirms resource was removed
  - All operations support dry-run preview

---

## Acceptance Criteria

1. `apply_yaml()` creates deployment from YAML string
2. `delete_resource("pod", "nginx-xxx", "default")` deletes the pod
3. `scale_resource("deployment", "nginx", "default", 3)` scales to 3 replicas
4. kubectl wrapper executes `kubectl exec` for pod shell access
5. All write operations have security level classification

---

## Notes

- kubectl wrapper is supplementary — prefer Python Client for everything except exec/top/apply-file
- Implement proper error handling for kubectl not found case
- Security: validate all parameters before passing to kubectl subprocess
