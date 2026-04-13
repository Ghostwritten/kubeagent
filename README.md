# KubeAgent

> Natural language CLI for Kubernetes cluster management

KubeAgent is an AI-powered CLI tool that lets you manage Kubernetes clusters through natural language conversation.

## Installation

### macOS

**Homebrew (recommended):**

```bash
brew tap Ghostwritten/tap
brew install kubeagent
```

**pip / pipx:**

```bash
pipx install kubeagent-cli
# or
pip install kubeagent-cli
```

**Standalone binary:**

```bash
# Apple Silicon (M1/M2/M3/M4)
curl -L -o kubeagent https://github.com/Ghostwritten/kubeagent/releases/latest/download/kubeagent-darwin-arm64
chmod +x kubeagent
sudo mv kubeagent /usr/local/bin/

# Intel
curl -L -o kubeagent https://github.com/Ghostwritten/kubeagent/releases/latest/download/kubeagent-darwin-x86_64
chmod +x kubeagent
sudo mv kubeagent /usr/local/bin/
```

**Docker:**

```bash
docker pull ghcr.io/ghostwritten/kubeagent:latest
docker run --rm -v ~/.kube:/home/kubeagent/.kube:ro ghcr.io/ghostwritten/kubeagent
```

### Linux

**pip / pipx (requires Python 3.12+):**

```bash
pipx install kubeagent-cli
# or
pip install kubeagent-cli
```

**Standalone binary:**

```bash
# x86_64
curl -L -o kubeagent https://github.com/Ghostwritten/kubeagent/releases/latest/download/kubeagent-linux-x86_64
chmod +x kubeagent
sudo mv kubeagent /usr/local/bin/

# ARM64 (aarch64)
curl -L -o kubeagent https://github.com/Ghostwritten/kubeagent/releases/latest/download/kubeagent-linux-arm64
chmod +x kubeagent
sudo mv kubeagent /usr/local/bin/
```

**Docker:**

```bash
# GHCR
docker pull ghcr.io/ghostwritten/kubeagent:latest
# Docker Hub
docker pull ghostwritten/kubeagent:latest

docker run --rm -v ~/.kube:/home/kubeagent/.kube:ro ghcr.io/ghostwritten/kubeagent
```

### Windows

**pip / pipx (requires Python 3.12+):**

```powershell
pipx install kubeagent-cli
# or
pip install kubeagent-cli
```

**Standalone binary:**

```powershell
# Download from GitHub Releases
Invoke-WebRequest -Uri https://github.com/Ghostwritten/kubeagent/releases/latest/download/kubeagent-windows-x86_64.exe -OutFile kubeagent.exe
# Move to a directory in PATH
Move-Item kubeagent.exe C:\Windows\System32\
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
