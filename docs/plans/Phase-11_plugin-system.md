# Phase 11 — Plugin System

> Status: `pending`
> Depends on: Phase 10
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Create the plugin system that allows third-party extensions: tool plugins, skill plugins, and policy plugins.

---

## Tasks

- [ ] **T1: Plugin interface specification**
  - Plugin manifest format: `plugin.yaml` with metadata
  - Plugin types: tool, skill, policy
  - Plugin entry points via Python package structure
  - Version compatibility declaration

- [ ] **T2: Plugin lifecycle management**
  - `kubeagent plugin install <name>` — install from PyPI or URL
  - `kubeagent plugin list` — show installed plugins
  - `kubeagent plugin update <name>` — update plugin
  - `kubeagent plugin remove <name>` — uninstall plugin
  - Plugin directory: `~/.kubeagent/plugins/`

- [ ] **T3: Plugin sandboxing**
  - Declared permissions: which tools, which clusters, which namespaces
  - Plugin cannot access more than declared
  - Audit log for plugin operations

- [ ] **T4: User-defined tool registration**
  - User can register custom tools via config
  - Tool can be: Python function, shell script, kubectl plugin
  - Tool metadata: name, description, parameters, security level

- [ ] **T5: Community skill contribution**
  - Skill contribution workflow documentation
  - Skill review guidelines
  - Skill versioning and compatibility

- [ ] **T6: Plugin marketplace (optional)**
  - Central registry of community plugins
  - Search and discovery
  - Rating and reviews

---

## Acceptance Criteria

1. Third-party plugin can be installed and loaded
2. Plugin adds new tools that appear in tool registry
3. Plugin permissions are enforced
4. User-defined tool (shell script) can be registered and called
5. Community skill can be installed via `kubeagent skill install`

---

## Notes

- Plugin system should be secure by default
- Start with simple plugins, defer complex sandboxing if needed
- Document plugin development guide
