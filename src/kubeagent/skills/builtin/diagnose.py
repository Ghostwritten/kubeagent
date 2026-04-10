"""Built-in /diagnose skill — multi-dimensional cluster/workload diagnosis."""

from __future__ import annotations

from kubeagent.skills.base import BuiltinSkill


class DiagnoseSkill(BuiltinSkill):
    """Multi-dimensional cluster diagnostic skill.

    Triggers: /diagnose
    Orchestrates: pod status, events, resource usage, node conditions
    """

    name = "diagnose"
    description = "Run comprehensive multi-dimensional cluster diagnosis"
    trigger = "/diagnose"
    required_tools = ["get_pods", "get_events", "get_nodes", "get_services"]

    def execute(self, context: dict) -> str:
        """Execute the diagnosis workflow.

        Returns a formatted diagnostic report covering:
        - Unhealthy pods (CrashLoopBackOff, ImagePullBackOff, etc.)
        - Recent error events
        - Node conditions (MemoryPressure, DiskPressure, PIDPressure)
        - Pending/Evicted pods
        - Service endpoint status
        """
        # This is called by the REPL skill dispatcher
        # The actual diagnostic logic is performed by SubAgents via diagnose_issue tool
        return self._build_diagnostic_prompt(context)

    def _build_diagnostic_prompt(self, context: dict) -> str:
        """Build the diagnostic prompt from context."""
        namespace = context.get("namespace", "default")
        return (
            f"Run a comprehensive diagnostic of namespace '{namespace}' covering:\n"
            "1. Pod health: CrashLoopBackOff, ImagePullBackOff, Pending, Evicted\n"
            "2. Recent error events in the namespace\n"
            "3. Node conditions affecting pods in this namespace\n"
            "4. Service endpoint readiness\n"
            "5. Resource requests vs actual usage\n"
            "Provide a structured diagnosis with root cause analysis."
        )
