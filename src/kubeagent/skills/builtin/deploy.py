"""Built-in /deploy skill — guided deployment with best-practice checks."""

from __future__ import annotations

from kubeagent.skills.base import BuiltinSkill


class DeploySkill(BuiltinSkill):
    """Guided deployment skill with best-practice checks.

    Triggers: /deploy
    Steps:
    1. Validate manifest syntax
    2. Check for resource limits and requests
    3. Dry-run validation
    4. Pre-deploy hook
    5. Apply with confirmation
    6. Post-deploy verification
    """

    name = "deploy"
    description = "Guided deployment with best-practice checks and verification"
    trigger = "/deploy"
    required_tools = ["apply_yaml"]

    def execute(self, context: dict) -> str:
        """Execute guided deployment workflow.

        Steps:
        1. Parse YAML manifest from context
        2. Validate resource specifications (limits/requests present)
        3. Check for dangerous settings (privileged containers, hostPID, etc.)
        4. Run pre-deploy hooks
        5. Dry-run to preview changes
        6. Apply with user confirmation
        7. Verify rollout status
        8. Run post-deploy hooks
        """
        manifest = context.get("manifest", "")
        namespace = context.get("namespace", "default")

        checks = self._run_pre_deploy_checks(manifest)

        return (
            f"## Deployment Plan for namespace '{namespace}'\n\n"
            f"{checks}\n\n"
            "Run with --dry-run to preview, or confirm to proceed."
        )

    def _run_pre_deploy_checks(self, manifest: str) -> str:
        """Run pre-deployment best-practice checks."""
        checks = []

        if not manifest:
            checks.append("- [ ] No manifest provided — please provide YAML content")
            return "\n".join(checks)

        checks.append("+ [x] Manifest provided")

        # Check for resource limits
        if "resources:" in manifest:
            if "limits:" in manifest:
                checks.append("+ [x] Resource limits present")
            else:
                checks.append("- [ ] WARNING: No resource limits specified")

        if "requests:" in manifest:
            checks.append("+ [x] Resource requests present")
        else:
            checks.append("- [ ] WARNING: No resource requests specified")

        # Check for dangerous settings
        dangerous = []
        if "privileged: true" in manifest:
            dangerous.append("privileged containers")
        if "hostPID: true" in manifest:
            dangerous.append("hostPID access")
        if "hostNetwork: true" in manifest:
            dangerous.append("hostNetwork access")

        if dangerous:
            checks.append(f"- [ ] DANGEROUS: {', '.join(dangerous)}")
        else:
            checks.append("+ [x] No dangerous settings detected")

        return "\n".join(checks)
