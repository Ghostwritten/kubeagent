"""Base tool class and security levels for the tool registry."""

from __future__ import annotations

from kubeagent.infra.executor import SecurityLevel


class BaseTool:
    """Base class for all KubeAgent tools.

    Each tool must define:
    - name: unique identifier (e.g., "get_pods")
    - description: what the tool does (shown to LLM)
    - security_level: safe / sensitive / dangerous
    """

    name: str = ""
    description: str = ""
    security_level: SecurityLevel = SecurityLevel.SAFE

    def execute(self, **kwargs: object) -> object:
        """Execute the tool. Subclasses must implement."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, str]:
        """Serialize tool metadata for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "security_level": str(self.security_level),
        }
