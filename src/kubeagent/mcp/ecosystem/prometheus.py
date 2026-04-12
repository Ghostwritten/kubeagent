"""Prometheus ecosystem plugin — tools for metrics querying and alert management."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool

DEFAULT_PROMETHEUS_URL = "http://localhost:9090"


def _prom_url(base: str) -> str:
    return base.rstrip("/")


class PrometheusQueryTool(BaseTool):
    name = "prometheus_query"
    description = "Execute a PromQL instant query and return current metric values."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        query: str = "",
        prometheus_url: str = DEFAULT_PROMETHEUS_URL,
        **kwargs: Any,
    ) -> Any:
        if not query:
            return {"error": "query (PromQL expression) is required"}
        url = f"{_prom_url(prometheus_url)}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": query}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Prometheus at {prometheus_url}"}
        except Exception as e:
            return {"error": str(e)}


class PrometheusQueryRangeTool(BaseTool):
    name = "prometheus_query_range"
    description = "Execute a PromQL range query over a time window (for graphs/trends)."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        query: str = "",
        start: str = "",
        end: str = "",
        step: str = "60s",
        prometheus_url: str = DEFAULT_PROMETHEUS_URL,
        **kwargs: Any,
    ) -> Any:
        if not query:
            return {"error": "query (PromQL expression) is required"}
        url = f"{_prom_url(prometheus_url)}/api/v1/query_range"
        params: dict[str, str] = {"query": query, "step": step}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Prometheus at {prometheus_url}"}
        except Exception as e:
            return {"error": str(e)}


class PrometheusAlertsTool(BaseTool):
    name = "prometheus_alerts"
    description = "List all active alerts from Prometheus Alertmanager."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        prometheus_url: str = DEFAULT_PROMETHEUS_URL,
        **kwargs: Any,
    ) -> Any:
        url = f"{_prom_url(prometheus_url)}/api/v1/alerts"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Prometheus at {prometheus_url}"}
        except Exception as e:
            return {"error": str(e)}


class PrometheusTargetsTool(BaseTool):
    name = "prometheus_targets"
    description = "List all scrape targets and their health status."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        prometheus_url: str = DEFAULT_PROMETHEUS_URL,
        **kwargs: Any,
    ) -> Any:
        url = f"{_prom_url(prometheus_url)}/api/v1/targets"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Summarize targets
            if data.get("status") == "success":
                active = data.get("data", {}).get("activeTargets", [])
                summary = []
                for t in active:
                    summary.append({
                        "job": t.get("labels", {}).get("job", ""),
                        "instance": t.get("labels", {}).get("instance", ""),
                        "health": t.get("health", ""),
                        "last_scrape": t.get("lastScrape", ""),
                    })
                return {"targets": summary, "total": len(summary)}
            return data
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Prometheus at {prometheus_url}"}
        except Exception as e:
            return {"error": str(e)}


PROMETHEUS_TOOLS: list[type[BaseTool]] = [
    PrometheusQueryTool,
    PrometheusQueryRangeTool,
    PrometheusAlertsTool,
    PrometheusTargetsTool,
]
