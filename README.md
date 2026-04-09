# KubeAgent

> Natural language CLI for Kubernetes cluster management

KubeAgent is an AI-powered CLI tool that lets you manage Kubernetes clusters through natural language conversation.

## Installation

```bash
# Recommended
pipx install kubeagent

# Alternative
pip install kubeagent
```

## Quick Start

```bash
# First run triggers setup wizard
kubeagent

# Re-configure anytime
kubeagent init

# Diagnose issues
kubeagent doctor

# Check version
kubeagent --version
```

## Development

```bash
# Install with dev dependencies
just install

# Format, lint, test
just check
```

## Architecture

Four-layer architecture: Interface → Agent → Capability → Infrastructure

See [AGENTS.md](AGENTS.md) for full specification.

## License

MIT
