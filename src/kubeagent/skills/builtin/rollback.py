"""Built-in /rollback skill — safe rollback with verification."""

from __future__ import annotations

from kubeagent.skills.base import BuiltinSkill


class RollbackSkill(BuiltinSkill):
    """Safe rollback skill with history and verification.

    Triggers: /rollback
    Steps:
    1. List available revisions (deployment revision history)
    2. Show diff between current and target revision
    3. Pre-rollback hook
    4. Execute rollback (kubectl rollout undo)
    5. Post-rollback verification
    """

    name = "rollback"
    description = "Safe rollback to previous deployment revision with verification"
    trigger = "/rollback"
    required_tools = ["describe_resource", "get_events"]

    def execute(self, context: dict) -> str:
        """Execute safe rollback workflow.

        Args:
            kind: Resource kind (deployment, statefulset)
            name: Resource name
            namespace: Target namespace
            revision: Target revision (optional, defaults to previous)

        Steps:
        1. Get current revision history
        2. Show what will change
        3. Pre-rollback hook (if configured)
        4. Execute rollback
        5. Verify new revision is running
        6. Report status
        """
        kind = context.get("kind", "deployment")
        name = context.get("name", "")
        namespace = context.get("namespace", "default")

        if not name:
            return (
                "Usage: /rollback <kind> <name> [namespace]\n"
                "Example: /rollback deployment my-app production\n\n"
                "This will show available revisions and guide you through safe rollback."
            )

        return (
            f"## Rollback Plan for {kind}/{name} in {namespace}\n\n"
            "1. Fetch revision history via kubectl rollout history\n"
            "2. Show diff between current and target revision\n"
            "3. Execute: kubectl rollout undo\n"
            "4. Wait for rollout to complete\n"
            "5. Verify new pods are running\n\n"
            "Run with --confirm to execute, or preview first."
        )
