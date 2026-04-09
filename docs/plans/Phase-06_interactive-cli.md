# Phase 06 — Interactive CLI

> Status: `pending`
> Depends on: Phase 05
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Build the full interactive CLI experience: REPL for multi-turn conversation, shell passthrough, Rich/Markdown mixed output, and streaming responses.

---

## Tasks

- [ ] **T1: REPL multi-turn conversation**
  - Persistent conversation loop (Ctrl+C to exit)
  - Conversation history within session
  - Input prompt shows current cluster/context
  - Auto-complete for common commands

- [ ] **T2: Shell passthrough**
  - `!` prefix executes shell command directly
  - Example: `!kubectl get pods` passes through to shell
  - Support chaining: `!kubectl get pods | grep nginx`

- [ ] **T3: Output rendering**
  - Rich tables for structured data (pods, nodes, services)
  - Markdown for analysis and explanations
  - Mixed mode: tables for data, markdown for narrative
  - Terminal width awareness, scrolling support

- [ ] **T4: Streaming output**
  - Stream LLM response token-by-token
  - Show spinner while tool executes
  - Progressive rendering for long outputs

- [ ] **T5: CLI polish**
  - Welcome message with quick start guide
  - Help command with all available commands
  - Error messages that guide user to resolution
  - Color scheme consistent with terminal theme

---

## Acceptance Criteria

1. Run `kubeagent` → REPL starts, shows prompt with cluster name
2. Multi-turn: "list pods" → "now list services" → context maintained
3. `!kubectl get pods` executes shell command
4. Pod listing renders as Rich table with proper columns
5. Streaming response shows tokens as they arrive

---

## Notes

- Use `prompt_toolkit` for REPL, `rich` for output
- Handle edge cases: empty input, Ctrl+C, terminal resize
- Keep backward compatible with headless mode (Phase 10)
