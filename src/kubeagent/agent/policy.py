"""Policy Engine — security enforcement and confirmation workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.registry import ToolRegistry

# Risk descriptions for each security level
_RISK_MESSAGES: dict[SecurityLevel, str] = {
    SecurityLevel.SAFE: "",
    SecurityLevel.SENSITIVE: ("This is a sensitive operation that may affect cluster state."),
    SecurityLevel.DANGEROUS: (
        "WARNING: This is a dangerous operation that can cause irreversible changes."
    ),
}


class PolicyDecision(StrEnum):
    """Result of a policy check."""

    ALLOW = "allow"  # Execute immediately
    CONFIRM = "confirm"  # Ask for confirmation
    DENY = "deny"  # Refuse to execute


def check_policy(
    tool_name: str,
    registry: ToolRegistry,
    args: dict[str, Any] | None = None,
    auto_approve: bool = False,
    dry_run: bool = False,
) -> PolicyDecision:
    """Check the policy for a tool execution.

    Args:
        tool_name: Name of the tool to execute.
        registry: Tool registry to look up security levels.
        args: Tool arguments (for impact analysis).
        auto_approve: If True, skip confirmation (--yes flag).
        dry_run: If True, dry-run mode — always allow.

    Returns:
        PolicyDecision indicating whether to allow, confirm, or deny.
    """
    # Dry-run is always safe
    if dry_run:
        return PolicyDecision.ALLOW

    tool_class = registry.get(tool_name)
    if tool_class is None:
        return PolicyDecision.DENY

    tool = tool_class()
    level = tool.security_level

    if level == SecurityLevel.SAFE:
        return PolicyDecision.ALLOW

    if auto_approve:
        return PolicyDecision.ALLOW

    if level == SecurityLevel.SENSITIVE:
        return PolicyDecision.CONFIRM

    if level == SecurityLevel.DANGEROUS:
        return PolicyDecision.CONFIRM

    return PolicyDecision.ALLOW


def get_risk_message(tool_name: str, registry: ToolRegistry) -> str:
    """Get the risk message for a tool."""
    tool_class = registry.get(tool_name)
    if tool_class is None:
        return "Unknown tool."
    tool = tool_class()
    return _RISK_MESSAGES.get(tool.security_level, "")


def build_impact_description(
    tool_name: str,
    args: dict[str, Any],
    registry: ToolRegistry,
) -> str:
    """Build a human-readable description of what an operation will do.

    Used in the confirmation prompt.
    """
    tool_class = registry.get(tool_name)
    if tool_class is None:
        return f"Unknown operation: {tool_name}"

    tool = tool_class()
    level = tool.security_level
    msg = _RISK_MESSAGES.get(level, "")

    parts: list[str] = []
    if msg:
        parts.append(msg)

    # Tool-specific impact descriptions
    kind = args.get("kind", "")
    name = args.get("name", "")
    namespace = args.get("namespace", "default")

    if tool_name == "delete_resource":
        parts.append(f"This will delete {kind}/{name} in namespace {namespace}.")
    elif tool_name == "restart_pod":
        parts.append(f"This will restart pod {name} in namespace {namespace}.")
    elif tool_name == "scale_resource":
        replicas = args.get("replicas", "?")
        parts.append(f"This will scale {kind}/{name} to {replicas} replicas.")
    elif tool_name == "cordon_node":
        parts.append(f"This will mark node {name} as unschedulable.")
    elif tool_name == "drain_node":
        parts.append(f"This will drain node {name} — all non-daemonset pods will be evicted.")
    elif tool_name == "apply_yaml":
        parts.append("This will apply the given YAML to the cluster.")
    else:
        parts.append(f"Operation: {tool_name} with args {args}")

    return " ".join(parts)


def needs_double_confirmation(tool_name: str, registry: ToolRegistry) -> bool:
    """Check if a tool requires double confirmation.

    Only the most dangerous operations require double confirmation:
    - drain_node (evicts all pods)
    - delete_resource (for namespace-level deletions)
    """
    return tool_name in ("drain_node",)


# ---------------------------------------------------------------------------
# RBAC — Role-Based Access Control
# ---------------------------------------------------------------------------



class Role(StrEnum):
    """User roles for RBAC."""

    ADMIN = "admin"      # Full access
    OPERATOR = "operator"  # Read/write, no cluster-admin
    VIEWER = "viewer"    # Read-only


@dataclass
class PolicyRule:
    """A single policy rule."""

    action: str  # get | list | apply | delete | exec | admin
    resource: str  # pod | deployment | service | node | * | ...
    namespace: str | None = None  # specific namespace or None for all
    allow: bool = True


@dataclass
class RBACPolicy:
    """Role-based access control policy.

    Attributes:
        role: User's role (admin, operator, viewer)
        protected_namespaces: Namespaces that operators/viewers cannot modify
        rules: Custom policy rules (override defaults)
    """

    role: Role = Role.OPERATOR
    protected_namespaces: list[str] = field(
        default_factory=lambda: ["kube-system", "kube-public"]
    )
    rules: list[PolicyRule] = field(default_factory=list)

    def can_get(self, resource: str, namespace: str) -> bool:
        """Check if user can get/list a resource."""
        if self.role in (Role.ADMIN, Role.OPERATOR, Role.VIEWER):
            return True
        return False

    def can_apply(self, resource: str, namespace: str) -> bool:
        """Check if user can apply (create/update) a resource."""
        if self.role == Role.ADMIN:
            return True
        if self.role == Role.VIEWER:
            return False
        # OPERATOR: allow but protect critical namespaces
        if self.role == Role.OPERATOR:
            if namespace in self.protected_namespaces:
                return False
        return True

    def can_delete(self, resource: str, namespace: str) -> bool:
        """Check if user can delete a resource."""
        if self.role == Role.ADMIN:
            return True
        if self.role == Role.VIEWER:
            return False
        # OPERATOR: no delete in protected namespaces
        if self.role == Role.OPERATOR:
            if namespace in self.protected_namespaces:
                return False
        return True

    def can_exec(self, resource: str, namespace: str) -> bool:
        """Check if user can exec into pods."""
        if self.role == Role.ADMIN:
            return True
        if self.role == Role.VIEWER:
            return False
        return True

