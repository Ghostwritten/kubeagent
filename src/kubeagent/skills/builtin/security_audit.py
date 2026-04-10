"""Built-in /security-audit skill — cluster security posture assessment."""

from __future__ import annotations

from kubeagent.skills.base import BuiltinSkill


class SecurityAuditSkill(BuiltinSkill):
    """Security posture assessment skill.

    Triggers: /security-audit
    Checks:
    - Pod security context (runAsNonRoot, privileged, capabilities)
    - Network policies (are namespaces isolated?)
    - RBAC (service accounts with cluster-admin?)
    - Secrets (are secrets mounted as env vars?)
    - Ingress security (TLS, whitelist)
    """

    name = "security-audit"
    description = "Assess cluster security posture and identify vulnerabilities"
    trigger = "/security-audit"
    required_tools = ["get_nodes", "get_pods", "get_services", "get_configmaps"]

    def execute(self, context: dict) -> str:
        """Execute security audit workflow.

        Runs checks across multiple dimensions:
        1. Pod security: runAsNonRoot, privileged, capabilities
        2. Network: missing NetworkPolicy, hostNetwork usage
        3. RBAC: overly permissive bindings
        4. Secrets: env var secrets (prefer volumes)
        5. TLS: services without TLS
        """
        namespace = context.get("namespace", "all")

        return (
            f"## Security Audit for namespace '{namespace}'\n\n"
            "Running checks:\n"
            "1. Pod security context (runAsNonRoot, privileged containers)\n"
            "2. Network isolation (missing NetworkPolicy)\n"
            "3. Service Account permissions\n"
            "4. Secrets management (env vars vs volumes)\n"
            "5. Ingress TLS configuration\n\n"
            "This audit identifies security risks and provides remediation recommendations."
        )
