# Phase 05 — LLM Integration + Agent Core

> Status: `pending`
> Depends on: Phase 04
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Integrate LiteLLM and Pydantic AI to create the core agent that can understand natural language, select appropriate tools, and execute single-turn requests.

---

## Tasks

- [ ] **T1: LiteLLM integration**
  - Configure LiteLLM with model providers: OpenAI, Anthropic, Ollama
  - Support model selection via config
  - Handle API errors, timeouts, fallback logic
  - Streaming response support

- [ ] **T2: Pydantic AI agent setup**
  - Create main agent using Pydantic AI
  - Bind all registered tools to agent
  - Tool schema auto-generation via `@agent.tool`

- [ ] **T3: Basic conversation loop (single-turn)**
  - Input → Intent recognition → Tool selection → Execution → Output
  - Simple: user asks, agent calls tool, returns result
  - No multi-turn context yet (Phase 06)

- [ ] **T4: Tool result processing**
  - Parse tool return values
  - Format results for LLM consumption
  - Handle tool execution errors gracefully

- [ ] **T5: Basic prompt template**
  - System prompt: "You are KubeAgent, a Kubernetes expert..."
  - Include available tools in system prompt
  - Simple prompt, no complex context yet

---

## Acceptance Criteria

1. Agent can process "list all pods in default namespace" and call `get_pods` tool
2. Agent returns structured output from tool execution
3. Model can be switched (via config): OpenAI ↔ Anthropic ↔ Ollama
4. Streaming output works for long responses
5. "What pods are running?" → calls tool → returns pod list

---

## Notes

- Use Pydantic AI's built-in tool calling — don't over-engineer
- Start with simple single-turn: no memory, no SubAgent
- Keep prompt minimal for now — full Prompt Engine in Phase 07
