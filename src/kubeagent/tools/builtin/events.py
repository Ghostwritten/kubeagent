"""Tool: get events."""

from __future__ import annotations

from kubeagent.infra.executor import PythonClientExecutor, SecurityLevel
from kubeagent.tools.base import BaseTool


class GetEventsTool(BaseTool):
    name = "get_events"
    description = "Get recent events in a namespace or across the cluster. Sorted by time."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        executor: PythonClientExecutor,
        namespace: str = "",
        field_selector: str = "",
    ) -> list[dict]:
        events = executor.get_events(namespace=namespace, field_selector=field_selector)
        return [
            {
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "source": e.source,
                "count": e.count,
                "age": e.age,
                "involved_object": e.involved_object,
            }
            for e in events
        ]
