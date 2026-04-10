"""Prompt Engine — dynamic system prompt construction."""

from __future__ import annotations

from pathlib import Path

from kubeagent.config.settings import KubeAgentConfig

# KUBEAGENT.md file names to search for (in order of priority)
_KUBEAGENT_FILENAMES = ["KUBEAGENT.md", ".kubeagent.md"]

# Default base prompt
_BASE_PROMPT = """\
You are KubeAgent, an intelligent Kubernetes cluster management assistant.

Your role:
- Help users manage and diagnose Kubernetes clusters using natural language
- Translate user requests into appropriate kubectl/tool operations
- Present results clearly with actionable insights

Guidelines:
- Always confirm before executing destructive operations (delete, drain, etc.)
- Explain what you're doing and why
- When showing resources, highlight important information (status, warnings, errors)
- Suggest follow-up actions when relevant
- If a resource is not found, suggest checking the namespace and resource name

You have access to tools for querying and managing Kubernetes resources.
Use the appropriate tool for each request. Do not guess — if unsure, ask the user.
"""


def load_kubeagent_md(path: Path | None = None) -> str | None:
    """Load KUBEAGENT.md rules file.

    Searches in order:
    1. Given path (explicit)
    2. Current working directory
    3. ~/.kubeagent/KUBEAGENT.md (global)

    Returns:
        Content of the file, or None if not found.
    """
    if path is not None:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    # Search in CWD
    cwd = Path.cwd()
    for filename in _KUBEAGENT_FILENAMES:
        candidate = cwd / filename
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    # Search in global config
    global_path = Path.home() / ".kubeagent" / "KUBEAGENT.md"
    if global_path.exists():
        return global_path.read_text(encoding="utf-8")

    return None


def build_cluster_context(
    cluster_name: str | None = None,
    namespace: str | None = None,
    server: str | None = None,
) -> str:
    """Build the cluster context section of the system prompt."""
    if not cluster_name:
        return ""

    lines = [
        "## Current Cluster",
        f"- Cluster: {cluster_name}",
    ]
    if namespace:
        lines.append(f"- Default namespace: {namespace}")
    if server:
        lines.append(f"- Server: {server}")
    return "\n".join(lines)


def build_preferences_section(config: KubeAgentConfig) -> str:
    """Build the user preferences section."""
    lines = ["## Preferences"]
    lines.append(f"- Output style: {config.output.style}")
    if config.output.language != "auto":
        lines.append(f"- Language: {config.output.language}")
    if config.output.verbose:
        lines.append("- Verbose output: enabled")
    lines.append(f"- Default model: {config.model.default}")
    return "\n".join(lines)


def build_system_prompt(
    config: KubeAgentConfig,
    cluster_name: str | None = None,
    namespace: str | None = None,
    server: str | None = None,
    kubeagent_md_path: Path | None = None,
    memory_preferences: str | None = None,
) -> str:
    """Compose the full system prompt from all sources.

    Order (later sections override earlier ones):
    1. Base prompt (hardcoded)
    2. Cluster context (dynamic)
    3. User preferences (from config)
    4. Memory preferences (from SQLite)
    5. KUBEAGENT.md rules (user-defined)
    """
    sections: list[str] = [_BASE_PROMPT]

    # Cluster context
    cluster_ctx = build_cluster_context(cluster_name, namespace, server)
    if cluster_ctx:
        sections.append(cluster_ctx)

    # User preferences
    sections.append(build_preferences_section(config))

    # Memory preferences
    if memory_preferences:
        sections.append(memory_preferences)

    # KUBEAGENT.md rules
    kubeagent_md = load_kubeagent_md(kubeagent_md_path)
    if kubeagent_md:
        sections.append("## Project Rules (from KUBEAGENT.md)\n")
        sections.append(kubeagent_md)

    return "\n\n".join(sections)
