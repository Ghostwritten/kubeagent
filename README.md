# KubeAgent

> Natural language CLI for Kubernetes cluster management

KubeAgent is an AI-powered CLI tool that lets you manage Kubernetes clusters through natural language conversation.

## Installation

### PyPI (Recommended)

```bash
pipx install kubeagent
# or
pip install kubeagent
```

### Homebrew (macOS / Linux)

```bash
brew tap Ghostwritten/tap
brew install kubeagent
```

### Docker

```bash
# GHCR
docker pull ghcr.io/ghostwritten/kubeagent:latest

# Docker Hub
docker pull ghostwritten/kubeagent:latest

# Run
docker run --rm -v ~/.kube:/home/kubeagent/.kube:ro ghcr.io/ghostwritten/kubeagent
```

### GitHub Releases

Download the latest wheel or source tarball from
[Releases](https://github.com/Ghostwritten/kubeagent/releases).

```bash
pip install kubeagent-*.whl
```

## Quick Start

```bash
# First run triggers setup wizard
kubeagent

# Re-configure anytime
kubeagent init

# Diagnose issues
kubeagent doctor

# Start MCP server
kubeagent mcp start

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

Four-layer architecture: Interface -> Agent -> Capability -> Infrastructure

See [AGENTS.md](AGENTS.md) for full specification.

## License

MIT
