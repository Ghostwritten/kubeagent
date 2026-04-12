# KubeAgent Master Plan

> Last Updated: 2026-04-12
> Design Spec: [../specs/2026-04-09-kubeagent-design.md](../specs/2026-04-09-kubeagent-design.md)

---

## Rules

1. **One Phase at a time** — Do not start a new Phase until the current one passes its acceptance criteria.
2. **Design before code** — Each Phase document must be reviewed and approved before implementation begins.
3. **Test as you go** — Every Phase includes unit tests; integration tests where applicable.
4. **Update before moving on** — After completing a Phase, update its status and record any decisions or deviations in `docs/decisions/`.
5. **Keep it working** — Each Phase completion should leave the project in a runnable state. No broken builds between Phases.
6. **Commit per task** — Each task within a Phase gets its own commit with a clear message.

---

## Phase Overview

| Phase | Title | Status | Doc |
|-------|-------|--------|-----|
| 01 | Project Scaffold | `completed` | [Phase-01_project-scaffold.md](Phase-01_project-scaffold.md) |
| 02 | Cluster Context | `completed` | [Phase-02_cluster-context.md](Phase-02_cluster-context.md) |
| 03 | K8s Executor + Read Tools | `completed` | [Phase-03_k8s-executor-read-tools.md](Phase-03_k8s-executor-read-tools.md) |
| 04 | K8s Write Tools + kubectl | `completed` | [Phase-04_k8s-write-tools-kubectl.md](Phase-04_k8s-write-tools-kubectl.md) |
| 05 | LLM Integration + Agent Core | `completed` | [Phase-05_llm-integration-agent-core.md](Phase-05_llm-integration-agent-core.md) |
| 06 | Interactive CLI | `completed` | [Phase-06_interactive-cli.md](Phase-06_interactive-cli.md) |
| 07 | Prompt Engine + Policy | `completed` | [Phase-07_prompt-engine-policy.md](Phase-07_prompt-engine-policy.md) |
| 08 | Memory System | `completed` | [Phase-08_memory-system.md](Phase-08_memory-system.md) |
| 09 | SubAgent + Model Router | `completed` | [Phase-09_subagent-model-router.md](Phase-09_subagent-model-router.md) |
| 10 | Skill + Hook + Headless | `completed` | [Phase-10_skill-hook-headless.md](Phase-10_skill-hook-headless.md) |
| 11 | Plugin System | `completed` | [Phase-11_plugin-system.md](Phase-11_plugin-system.md) |
| 12 | MCP Server + Ecosystem | `completed` | [Phase-12_mcp-server-ecosystem.md](Phase-12_mcp-server-ecosystem.md) |

---

## Milestones

| Milestone | After Phase | Capability |
|-----------|-------------|------------|
| **MVP Alpha** | Phase 07 | Conversational CLI that manages K8s clusters with safety controls |
| **MVP Beta** ✅ | Phase 10 | Professional diagnostics, automation, headless mode |
| **v1.0** ✅ | Phase 12 | Full platform with plugin ecosystem and MCP support |

---

## Dependency Graph

```
Phase 01 (Scaffold)
  └─► Phase 02 (Cluster Context)
        └─► Phase 03 (Read Tools)
              └─► Phase 04 (Write Tools + kubectl)
                    └─► Phase 05 (LLM + Agent Core)
                          └─► Phase 06 (Interactive CLI)
                                └─► Phase 07 (Prompt + Policy)
                                      └─► Phase 08 (Memory)
                                            └─► Phase 09 (SubAgent + Router)
                                                  └─► Phase 10 (Skill + Hook + Headless)
                                                        └─► Phase 11 (Plugin System)
                                                              └─► Phase 12 (MCP + Ecosystem)
```

---

## Execution Order

For each Phase:

1. **Read** the Phase document — understand scope, tasks, acceptance criteria
2. **Design** — if the Phase requires design decisions not covered in the spec, document them in `docs/decisions/`
3. **Implement** — write code, one task at a time, commit per task
4. **Test** — run unit tests, integration tests, manual smoke checks
5. **Validate** — verify all acceptance criteria pass
6. **Update** — set Phase status to `completed`, record any notes or deviations
7. **Review** — review the Phase output before moving to next Phase
8. **Proceed** — start next Phase

---

## Notes

- Architecture design rationale is in [../specs/2026-04-09-kubeagent-design.md](../specs/2026-04-09-kubeagent-design.md)
- Architecture decisions are recorded in [../decisions/](../decisions/)
- Phases can be extended — after Phase 12 ("小满贯"), new Phases can be appended for additional features
