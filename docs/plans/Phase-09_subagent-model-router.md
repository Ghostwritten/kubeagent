# Phase 09 — SubAgent + Model Router

> Status: `pending`
> Depends on: Phase 08
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Enable the Main Agent to dynamically create specialized SubAgents for complex tasks, and implement intelligent model routing strategies.

---

## Tasks

- [ ] **T1: SubAgent factory**
  - `SubAgentFactory`: create agent instances at runtime
  - Each SubAgent receives: task description, tool subset, model selection, context
  - SubAgent is a Pydantic AI Agent instance (not a predefined class)
  - Ephemeral lifecycle: created → executed → result returned → destroyed

- [ ] **T2: SubAgent dispatcher**
  - Main Agent decides when to dispatch SubAgents (via LLM reasoning)
  - Parallel execution via asyncio.gather
  - Timeout handling per SubAgent
  - Error isolation: one SubAgent failure doesn't crash others

- [ ] **T3: Result aggregation**
  - Collect structured results from all SubAgents
  - Main Agent synthesizes into unified analysis
  - Source attribution: which SubAgent produced which finding

- [ ] **T4: Model Router — routing strategies**
  - `complexity`: classify query complexity → route to appropriate model
    - Simple (list, get) → light model (Haiku, GPT-4o-mini, local)
    - Complex (diagnose, plan) → strong model (Opus, GPT-4o, Sonnet)
  - `cost`: track token usage, respect monthly_budget
  - `availability`: fallback chain on API failure
  - `manual`: user specifies model via --model or in-session command
  - Strategy selectable via config

- [ ] **T5: SubAgent model selection**
  - SubAgents can use different (lighter) models than Main Agent
  - Configurable via `subagent_model` in config
  - Main Agent can override per-SubAgent if needed

- [ ] **T6: Tests**
  - Test SubAgent creation with dynamic tool sets
  - Test parallel execution and result aggregation
  - Test timeout and error isolation
  - Test each routing strategy
  - Test cost tracking

---

## Acceptance Criteria

1. "Why is payment-service crashing?" → Main Agent creates 2-3 SubAgents in parallel → aggregated diagnosis
2. SubAgents use configured `subagent_model` (lighter model)
3. Model routing respects configured strategy
4. One SubAgent timeout doesn't crash the entire diagnosis
5. Token usage tracked and reported

---

## Files Created/Modified

- `src/kubeagent/agent/subagent.py` — SubAgentFactory, SubAgentDispatcher
- `src/kubeagent/infra/model_router.py` — full routing strategies (upgrade from Phase 05)
- `src/kubeagent/agent/main_agent.py` — add SubAgent dispatch capability
- `tests/unit/test_subagent.py`
- `tests/unit/test_model_router.py` — extended tests
