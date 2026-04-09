# KubeAgent Design Specification

> Version: 1.0.0  
> Date: 2026-04-09  
> Status: Draft  
> Implementation Plan: [../plans/00-master-plan.md](../plans/00-master-plan.md)

---

## Purpose of This Document

This document answers **WHY** and **WHAT** — the architectural rationale, design principles, and component responsibilities. For **HOW** and **WHEN** (implementation tasks, phases, status), see the [Master Plan](../plans/00-master-plan.md).

---

## 1. Project Overview

### 1.1 Vision

KubeAgent is an open-source CLI intelligent agent that enables users to manage Kubernetes clusters through natural language conversation. It aims to completely replace the command-line mindset of kubectl/kubeadm with an AI-driven, conversational approach that provides professional-grade cluster management with built-in safety awareness, logical analysis, and best-practice enforcement.

### 1.2 Core Principles

- **Natural Language First**: Conversation-driven interaction, similar to Claude Code's UX
- **Professional Output**: Context-aware formatting that adapts to the scenario (structured tables for overviews, reasoning chains for diagnostics, change previews for deployments)
- **Safety by Design**: Three-tier operation classification, role-based access, dry-run support
- **Open & Extensible**: Plugin system, community-contributed Skills, user-defined Tools
- **Model Agnostic**: Support local models (Ollama) and paid APIs (Claude/GPT/Gemini) with intelligent routing

### 1.3 Target Users

- SRE / DevOps Engineers
- Developers
- Cluster Administrators
- Any Kubernetes operator who prefers natural language over CLI commands

### 1.4 Interaction Model

- **Primary**: Conversational dialogue (like Claude Code)
- **Shell passthrough**: `!` prefix executes shell commands directly
- **Skill invocation**: `/skill-name` triggers predefined workflows
- **Stateful sessions**: Remembers user context, habits, and preferences across sessions

---

## 2. Architecture

### 2.1 Four-Layer Architecture

```
┌─────────────────────────────────────────────┐
│         Interface Layer (交互层)              │
│  CLI REPL | Headless | ! Shell | /Skill      │
│  Prompt Engine + KUBEAGENT.md                │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│          Agent Layer (智能层)                 │
│  Main Agent | SubAgent Dispatcher            │
│  Memory Manager | Hook Engine | Policy Engine│
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│        Capability Layer (能力层)              │
│  Tool Registry | Skill Registry              │
│  Built-in Tools | User Tools | Plugin Tools  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Infrastructure Layer (基础层)            │
│  Model Router | Cluster Context | Storage    │
│  K8s Executor (Python Client + kubectl)      │
└─────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Key Components |
|-------|---------------|----------------|
| **Interface** | User interaction, input parsing, output rendering | CLI REPL, Headless mode, Shell passthrough, Skill dispatch, Prompt Engine |
| **Agent** | Intent recognition, task planning, tool orchestration, decision-making | Main Agent, SubAgent Dispatcher, Memory Manager, Hook Engine, Policy Engine |
| **Capability** | Extensible tool and skill registration, execution | Tool Registry, Skill Registry, Built-in/User/Plugin tools |
| **Infrastructure** | Model access, cluster connectivity, storage, K8s operations | Model Router (LiteLLM), Cluster Context, SQLite/file storage, K8s Executor |

---

## 3. Component Design

### 3.1 Prompt Engine

**Purpose**: Constructs the system prompt for each agent interaction by composing multiple sources.

**Prompt Sources (priority high to low)**:
1. User message (current input)
2. `KUBEAGENT.md` project-level configuration (user-defined rules, naming conventions, deployment preferences)
3. Active cluster context (cluster name, namespace, resource summary)
4. Memory context (user preferences, recent operations, cluster profile)
5. System prompt template (K8s expert role definition, safety rules, output guidelines)

**User Customization**:
- `KUBEAGENT.md` in project root: project-specific rules in natural language (e.g., "always use namespace production for deployments", "never delete PVCs without backup"). This file defines **what the agent should know and follow** for this project — behavioral rules, naming conventions, deployment preferences.
- `~/.kubeagent/config.yaml`: global **technical settings** — model selection, security role, output format, memory limits. Structured YAML, not natural language.
- Prompt templates are overridable
- **Precedence**: KUBEAGENT.md (project) overrides config.yaml (global) for overlapping concerns

### 3.2 Main Agent

**Purpose**: The central reasoning engine that processes user requests.

**Workflow**:
1. **Intent Recognition**: Classify user input (query, operation, diagnosis, deployment, etc.)
2. **Memory Query**: Check relevant history, user preferences, cluster profile
3. **Policy Check**: Validate operation against security policies and user role
4. **Task Planning**: Determine whether to handle directly or dispatch SubAgents
5. **Tool Selection**: Choose appropriate tools for execution
6. **Result Synthesis**: Aggregate results and generate output
7. **Memory Update**: Store relevant outcomes for future reference

**Framework**: Pydantic AI for agent orchestration, tool binding, and structured output.

### 3.3 SubAgent System

**Purpose**: Dynamically created specialized agents for complex, multi-dimensional tasks.

**Design**:
- **Dynamic instantiation**: Main Agent creates SubAgents at runtime based on task requirements
- **Independent tool sets**: Each SubAgent receives only the tools it needs
- **Independent model selection**: SubAgents can use lighter/cheaper models than Main Agent
- **Parallel execution**: Multiple SubAgents can run concurrently via asyncio
- **Result aggregation**: Main Agent collects and synthesizes SubAgent outputs
- **Lifecycle**: SubAgents are ephemeral; created for a task, destroyed after completion

**Example SubAgent types** (created dynamically, not predefined classes):
- Diagnostic Agent: Collects pod status, events, descriptions
- Log Analysis Agent: Reads and analyzes log patterns
- Resource Check Agent: Inspects node status, resource quotas, limits
- Security Audit Agent: Checks RBAC, network policies, secrets exposure

### 3.4 Tool System

**Purpose**: Extensible registry of atomic operations the agent can perform.

**Tool Categories**:

| Category | Examples | Source |
|----------|---------|--------|
| **Built-in** | get_pods, describe_resource, read_logs, apply_yaml, delete_resource, exec_pod, scale, get_events, get_metrics | Core package |
| **User-defined** | Custom scripts, kubectl plugins, operational runbooks | User registration |
| **Plugin** | Helm operations, Istio management, ArgoCD sync | Plugin system |

**Tool Registration**:
- Built-in tools are auto-registered at startup
- User tools registered via config file or CLI command
- Plugin tools registered by plugin installation
- Each tool declares its security level (safe/sensitive/dangerous)
- Tools are bound to Pydantic AI's `@agent.tool` decorator with auto-schema generation

**Security Binding**:
- Each tool is tagged with an operation security level
- Policy Engine checks the tag before execution
- Tools can declare required roles

### 3.5 Skill System

**Purpose**: Reusable, composable workflows that combine multiple tools with reasoning logic.

**Built-in Skills**:
- `/diagnose` — Multi-dimensional cluster/workload diagnosis
- `/deploy` — Guided deployment with best-practice checks
- `/rollback` — Safe rollback with verification
- `/security-audit` — Security posture assessment
- `/migrate` — Migration checklist and validation
- `/backup` — Backup verification and status
- `/scale-plan` — Scaling strategy analysis
- `/cost-analysis` — Resource cost optimization

**Skill Definition Format**:
- Markdown-based definition files (similar to Claude Code skills)
- Declarative: name, description, trigger conditions, steps, required tools
- Community-contributable with version management

**Skill Loading**:
- Built-in skills loaded from `skills/` directory
- User skills from `~/.kubeagent/skills/`
- Community skills installed via `kubeagent skill install <name>`

### 3.6 Hook Engine

**Purpose**: Event-driven automation that executes user-defined actions before/after operations.

**Hook Lifecycle Events**:

| Event | Trigger Point | Example Use Case |
|-------|--------------|-----------------|
| `pre-apply` | Before applying YAML | Auto lint + dry-run validation |
| `post-apply` | After applying YAML | Verify rollout status |
| `pre-delete` | Before deleting resources | Check dependent resources |
| `post-delete` | After deleting resources | Verify cleanup completion |
| `pre-deploy` | Before deployment | Check image vulnerability, resource quota |
| `post-deploy` | After deployment | Health check, smoke test |
| `on-error` | When any operation fails | Auto-collect diagnostic info |
| `pre-scale` | Before scaling | Check node capacity |
| `on-connect` | When connecting to cluster | Cluster health snapshot |
| `on-diagnose` | When diagnosis workflow starts | Trigger additional data collection |

**Execution Order** (for mutating operations):
1. Policy Engine check (role + whitelist/blacklist) → abort if denied
2. `pre-*` hooks execute → abort if hook fails
3. User confirmation (if sensitive/dangerous)
4. Operation execution
5. `post-*` hooks execute
6. `on-error` hooks (if operation failed)

**Hook Definition**:
- Configured in `~/.kubeagent/hooks.yaml` or `KUBEAGENT.md`
- Each hook specifies: event, action (shell command / tool call / skill invocation), conditions
- Hooks can abort the parent operation (e.g., pre-deploy check fails → deployment aborted)

### 3.7 Memory Manager

**Purpose**: Persistent, categorized memory across sessions.

**Memory Types**:

| Type | Content | Persistence | Example |
|------|---------|------------|---------|
| **Session Context** | Current conversation state, referenced resources | Session lifetime | "We've been discussing nginx-deployment" |
| **User Preferences** | Output format, favorite namespaces, default cluster | Permanent | "User prefers table output, works mostly in namespace production" |
| **Cluster Profile** | Cluster characteristics, topology, common issues | Per-cluster, long-lived | "prod-cluster has 50 nodes, runs Istio, frequently has memory pressure" |
| **Fault Knowledge** | Past diagnoses, solutions, patterns | Permanent | "payment-service OOM was caused by memory leak in v2.3.1, fixed by increasing limits" |
| **Audit Log** | All mutating operations performed | Permanent, append-only | "2026-04-09 14:30 — deleted pod nginx-xxx in namespace default" |

**Storage**: SQLite for structured data, local files for large content.

**Privacy Controls**:
- User can view, export, and delete any memory
- Sensitive data (secrets, tokens) never stored in memory
- Memory expiration policies configurable

### 3.8 Policy Engine

**Purpose**: Centralized security policy enforcement.

**Three-Tier Operation Classification**:

| Level | Operations | Agent Behavior |
|-------|-----------|---------------|
| **Safe** | get, list, describe, logs, events, top | Execute immediately |
| **Sensitive** | restart pod, scale replicas, edit configmap, cordon node | Prompt for user confirmation |
| **Dangerous** | delete namespace, delete PVC, modify RBAC, drain node, delete CRD | Force confirmation + secondary warning with impact analysis |

**Role-Based Access**:
- **Admin**: All operations permitted (still requires confirmation for dangerous)
- **Operator**: Safe + Sensitive operations, dangerous operations blocked
- **Viewer**: Safe operations only (read-only mode)
- Role configured in `~/.kubeagent/config.yaml`

**Whitelist / Blacklist**:
- Operation whitelist: only listed operations are allowed
- Operation blacklist: listed operations are always blocked
- Resource whitelist/blacklist: protect specific namespaces or resources
- Configured per-cluster in `KUBEAGENT.md` or global config

**Dry-Run Mode**:
- `--dry-run` flag or in-session toggle
- All mutating operations show preview without execution
- Diff-style output showing what would change

### 3.9 Headless Mode

**Purpose**: Non-interactive operation for scripting, CI/CD, and automation.

**Invocation**:
```bash
# Single query
kubeagent --headless "check if all pods in production are healthy"

# Structured output
kubeagent --headless --json "list all pods with restart count > 5"
kubeagent --headless --yaml "show deployment config for payment-service"

# Batch processing
kubeagent --headless --batch commands.txt

# Pipe-friendly
kubeagent --headless --json "list unhealthy pods" | jq '.pods[] | .name'

# CI/CD integration
kubeagent --headless --exit-code "verify deployment rollout is complete"
```

**Output Formats**: JSON, YAML, plain text, Markdown (selectable via flags).

**Exit Codes**: Configurable exit codes for CI/CD (0=success, 1=failure, 2=warning).

### 3.10 Cluster Context

**Purpose**: Multi-cluster connection management.

**Features**:
- Parse and manage kubeconfig files
- Switch clusters via natural language ("switch to production cluster")
- Maintain connection pool for active clusters
- Cluster health snapshot on connect (via `on-connect` hook)
- Support multiple kubeconfig file paths
- Display current cluster context in CLI prompt

### 3.11 Model Router

**Purpose**: Unified LLM access with intelligent routing.

**Framework**: LiteLLM for 100+ model unified interface.

**Supported Model Types**:
- Local: Ollama (Llama, Qwen, DeepSeek, etc.)
- Cloud: Claude (Anthropic), GPT (OpenAI), Gemini (Google)
- Self-hosted: vLLM, llama.cpp compatible endpoints

**Routing Strategies** (user-selectable):

| Strategy | Logic | Example |
|----------|-------|---------|
| **Complexity-based** | Simple queries → light model, complex reasoning → strong model | "list pods" → Haiku; "why is this pod crashing" → Opus |
| **Cost-based** | Respect user budget, optimize cost per query | Monthly budget $50, auto-select cheapest capable model |
| **Availability-based** | Fallback chain when primary model unavailable | Claude → GPT → Ollama local |
| **Manual** | User specifies model directly | `kubeagent --model ollama/qwen2.5` |

**Configuration**:
```yaml
# ~/.kubeagent/config.yaml
model:
  default: claude-sonnet-4-20250514
  fallback: [gpt-4o, ollama/qwen2.5]
  strategy: complexity  # complexity | cost | availability | manual
  subagent_model: claude-haiku-4-5-20251001  # lighter model for SubAgents
  cost:
    monthly_budget: 50
    currency: USD
```

### 3.12 K8s Executor

**Purpose**: Unified execution layer that abstracts Python Client and kubectl differences.

**Design**:
- `KubeExecutor` interface with two implementations:
  - `PythonClientExecutor`: Primary, for structured operations (CRUD, watch, metrics)
  - `KubectlExecutor`: Supplementary, for apply, exec, top, plugin ecosystem
- Auto-detection: If kubectl is not installed, gracefully degrade to Python Client only
- K8s server version detection at startup for SDK compatibility
- All outputs normalized to unified data models before returning to agent layer

**Security**:
- kubectl calls use argument list (not shell string) to prevent command injection
- Parameter whitelist validation before kubectl execution
- Execution audit logging

### 3.13 Plugin System (Phase 3)

**Purpose**: Third-party extensibility for ecosystem integration.

**Plugin Types**:
- **Tool plugins**: Add new tools (e.g., Helm operations, Istio configuration)
- **Skill plugins**: Add new skills (e.g., `/helm-deploy`, `/istio-diagnose`)
- **Policy plugins**: Add custom policy rules (e.g., compliance checks)

**Plugin Lifecycle**:
```bash
kubeagent plugin install helm-plugin
kubeagent plugin list
kubeagent plugin update helm-plugin
kubeagent plugin remove helm-plugin
```

**Plugin Development**:
- Standardized plugin interface (Python package with entry points)
- Plugin manifest declares: name, version, tools, skills, dependencies
- Sandboxed execution with declared permissions

### 3.14 MCP Server (Phase 3)

**Purpose**: Expose KubeAgent as an MCP (Model Context Protocol) server, enabling other AI tools (Claude Code, Cursor, etc.) to use KubeAgent's K8s capabilities.

**Design**:
- KubeAgent's tools and skills exposed as MCP tools
- Other AI agents can connect to KubeAgent as an MCP server
- Same security policies and role-based access apply
- KubeAgent becomes a K8s capability provider for the broader AI ecosystem

---

## 4. Data Flow

### 4.1 Request Lifecycle

```
User Input: "payment-service 为什么一直重启？"
  │
  ▼
① Prompt Engine
   → Compose system prompt (role + KUBEAGENT.md rules + cluster context)
   → Load relevant memory (cluster profile, user preferences)
  │
  ▼
② Main Agent (Pydantic AI)
   → Intent: Fault Diagnosis
   → Memory: Any history for payment-service?
   → Policy: User has permission for read operations?
   → Plan: Multi-dimensional investigation needed → dispatch SubAgents
  │
  ▼
③ SubAgent Dispatcher
   → Create DiagnosticAgent (tools: get_pods, describe, get_events)
   → Create LogAnalysisAgent (tools: read_logs)
   → Create ResourceCheckAgent (tools: get_node_status, get_resource_quota)
   → Hook: on-diagnose triggers additional checks
   → Execute all SubAgents in parallel (asyncio)
  │
  ▼
④ Tool Execution
   → K8s Executor → Python Client API calls
   → Results normalized to structured data
  │
  ▼
⑤ Result Aggregation
   → Main Agent synthesizes SubAgent results
   → Root cause analysis + repair recommendations
   → Memory: Store diagnosis for future reference
   → Audit: Log the diagnostic operation
  │
  ▼
⑥ Output Rendering
   → Rich tables: Pod status, resource metrics
   → Markdown: Analysis reasoning, root cause, recommendations
   → Mixed output adapted to terminal width
```

---

## 5. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Ecosystem, K8s client support, async |
| Agent Framework | Pydantic AI | Type-safe, lightweight, multi-model, dependency injection |
| Model Interface | LiteLLM | 100+ models unified API, cost tracking |
| K8s SDK | `kubernetes` (official) | Structured API, type-safe, watch support |
| K8s CLI | kubectl (subprocess) | Apply, exec, top, plugin ecosystem |
| CLI Framework | Rich + prompt_toolkit | Terminal UI, tables, syntax highlighting, auto-complete |
| Output | Rich (structured data) + Markdown (analysis) | Mixed rendering for professional output |
| Configuration | Pydantic + YAML | Type-safe config with validation |
| Storage | SQLite + local files | Memory, audit logs, session state |
| Packaging | pip / pipx | Standard Python distribution |

---

## 6. Security Design

### 6.1 Principles

- **Least privilege**: Agent only performs operations the user's kubeconfig allows
- **Defense in depth**: Policy Engine + K8s RBAC + operation classification
- **Audit trail**: All mutating operations logged with timestamp, user, cluster, details
- **No secret storage**: Memory system never stores K8s secrets, tokens, or credentials
- **Injection prevention**: kubectl calls use argument lists, never shell interpolation

### 6.2 Threat Model

| Threat | Mitigation |
|--------|-----------|
| Prompt injection via K8s resource names | Sanitize all K8s data before including in prompts |
| Accidental destructive operations | Three-tier classification + confirmation + dry-run |
| Credential leakage through memory | Memory system excludes secrets; audit log redacts sensitive values |
| kubectl command injection | Argument list execution, parameter whitelist |
| Unauthorized multi-cluster access | Respect kubeconfig permissions, no privilege escalation |

---

## 7. Implementation Roadmap

Implementation is organized into 12 lightweight phases. See [Master Plan](../plans/00-master-plan.md) for detailed task breakdown, dependencies, and status tracking.

**Milestones:**
- **MVP Alpha** (after Phase 07): Conversational CLI with safety controls
- **MVP Beta** (after Phase 10): Professional diagnostics, automation, headless mode
- **v1.0 小满贯** (after Phase 12): Full platform with plugin ecosystem and MCP support

---

## 8. Project Structure

```
kubeagent/
├── pyproject.toml
├── KUBEAGENT.md                    # Project-level configuration example
├── src/kubeagent/
│   ├── cli/                        # Interface Layer
│   │   ├── repl.py                 # REPL main loop
│   │   ├── renderer.py             # Rich/Markdown output
│   │   ├── shell.py                # ! shell passthrough
│   │   └── history.py              # Persistent command history
│   ├── agent/                      # Agent Layer
│   │   ├── main_agent.py           # Main Agent (Pydantic AI)
│   │   ├── prompt.py               # Prompt Engine
│   │   ├── memory.py               # Memory Manager
│   │   ├── policy.py               # Policy Engine
│   │   └── subagent.py             # SubAgent Factory & Dispatcher
│   ├── tools/                      # Capability Layer
│   │   ├── base.py                 # BaseTool class
│   │   ├── registry.py             # Tool Registry
│   │   ├── builtin/                # Built-in K8s tools
│   │   │   ├── pods.py, deployments.py, services.py
│   │   │   ├── logs.py, events.py, resources.py
│   │   │   ├── yaml_ops.py, mutations.py
│   │   │   └── nodes.py, namespaces.py
│   │   └── kubectl.py              # kubectl wrapper
│   ├── infra/                      # Infrastructure Layer
│   │   ├── model_router.py         # LiteLLM model routing
│   │   ├── cluster.py              # Cluster connection
│   │   ├── executor.py             # K8s Executor interface
│   │   └── storage.py             # SQLite persistence
│   └── config/
│       ├── settings.py             # Pydantic config models
│       ├── defaults.yaml          # Default values
│       └── kubeagent_md.py        # KUBEAGENT.md loader
├── skills/                         # Built-in skills (Phase 10)
├── plugins/                        # Plugin directory (Phase 11)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── docs/
    ├── specs/                      # This document (WHY & WHAT)
    ├── plans/                      # Phase plans (HOW & WHEN)
    ├── decisions/                  # Architecture Decision Records
    └── user-guide/
```

---

## 9. Configuration Reference

### 9.1 Global Configuration (`~/.kubeagent/config.yaml`)

```yaml
# Model configuration
model:
  default: claude-sonnet-4-20250514
  fallback: [gpt-4o, ollama/qwen2.5]
  strategy: complexity
  subagent_model: claude-haiku-4-5-20251001
  cost:
    monthly_budget: 50
    currency: USD

# Security
security:
  role: admin  # admin | operator | viewer
  dry_run: false
  blacklist:
    operations: []
    namespaces: [kube-system]
  whitelist:
    operations: []
    namespaces: []

# Output
output:
  style: mixed  # rich | markdown | mixed
  language: auto  # auto | en | zh
  verbose: false

# Memory
memory:
  enabled: true
  audit_log: true
  expiration_days: 90
  max_size_mb: 100

# Cluster
cluster:
  kubeconfig: ~/.kube/config
  default_namespace: default
```

### 9.2 Project Configuration (`KUBEAGENT.md`)

```markdown
# KubeAgent Project Configuration

## Cluster Rules
- Default namespace: production
- Never delete PVCs without explicit backup confirmation
- Always use rolling update strategy for deployments

## Naming Conventions
- Deployments: {service-name}-{env}
- ConfigMaps: {service-name}-config

## Deployment Preferences
- Always set resource requests and limits
- Minimum replicas: 2 for production workloads
- Required labels: app, env, team, version
```

---

## 10. Open Questions

These questions are deferred to Phase planning or later:

1. **Skill definition format**: Markdown (like Claude Code) for declaration + optional Python handlers for complex logic. Decision deferred to Phase 10.

2. **Plugin sandboxing**: Full process isolation vs. Python-level restriction. Decision deferred to Phase 11.

3. **Offline mode**: Fully offline with Ollama local models is supported in principle, but UX with smaller models may be degraded. LiteLLM handles this already.

4. **Multi-language output**: Auto-detect from input language, configurable override. Decision deferred to Phase planning.

5. **CLI framework choice**: click vs argparse for CLI parsing. Decision deferred to Phase 01.
