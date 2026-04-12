"""Grafana ecosystem plugin — tools for dashboard and annotation management."""

from __future__ import annotations

from typing import Any

import requests

from kubeagent.infra.executor import SecurityLevel
from kubeagent.tools.base import BaseTool

DEFAULT_GRAFANA_URL = "http://localhost:3000"


def _grafana_headers(api_key: str = "") -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class GrafanaDashboardListTool(BaseTool):
    name = "grafana_dashboard_list"
    description = "List all Grafana dashboards with titles and URLs."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        grafana_url: str = DEFAULT_GRAFANA_URL,
        api_key: str = "",
        **kwargs: Any,
    ) -> Any:
        url = f"{grafana_url.rstrip('/')}/api/search?type=dash-db"
        try:
            resp = requests.get(url, headers=_grafana_headers(api_key), timeout=10)
            resp.raise_for_status()
            dashboards = resp.json()
            return [
                {
                    "title": d.get("title", ""),
                    "uid": d.get("uid", ""),
                    "url": f"{grafana_url.rstrip('/')}{d.get('url', '')}",
                    "tags": d.get("tags", []),
                }
                for d in dashboards
            ]
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Grafana at {grafana_url}"}
        except Exception as e:
            return {"error": str(e)}


class GrafanaDashboardGetTool(BaseTool):
    name = "grafana_dashboard_get"
    description = "Get a Grafana dashboard by UID, including all panels."
    security_level = SecurityLevel.SAFE

    def execute(
        self,
        uid: str = "",
        grafana_url: str = DEFAULT_GRAFANA_URL,
        api_key: str = "",
        **kwargs: Any,
    ) -> Any:
        if not uid:
            return {"error": "uid is required"}
        url = f"{grafana_url.rstrip('/')}/api/dashboards/uid/{uid}"
        try:
            resp = requests.get(url, headers=_grafana_headers(api_key), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            dashboard = data.get("dashboard", {})
            panels = dashboard.get("panels", [])
            return {
                "title": dashboard.get("title", ""),
                "uid": uid,
                "panels": [
                    {
                        "title": p.get("title", ""),
                        "type": p.get("type", ""),
                        "id": p.get("id", ""),
                    }
                    for p in panels
                ],
                "panel_count": len(panels),
            }
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Grafana at {grafana_url}"}
        except Exception as e:
            return {"error": str(e)}


class GrafanaAnnotationCreateTool(BaseTool):
    name = "grafana_annotation_create"
    description = "Create a Grafana annotation (e.g., to mark a deployment event)."
    security_level = SecurityLevel.SENSITIVE

    def execute(
        self,
        text: str = "",
        tags: list[str] | None = None,
        dashboard_uid: str = "",
        grafana_url: str = DEFAULT_GRAFANA_URL,
        api_key: str = "",
        **kwargs: Any,
    ) -> Any:
        if not text:
            return {"error": "text is required"}
        url = f"{grafana_url.rstrip('/')}/api/annotations"
        payload: dict[str, Any] = {"text": text, "tags": tags or ["kubeagent"]}
        if dashboard_uid:
            payload["dashboardUID"] = dashboard_uid
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=_grafana_headers(api_key),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"error": f"Cannot connect to Grafana at {grafana_url}"}
        except Exception as e:
            return {"error": str(e)}


GRAFANA_TOOLS: list[type[BaseTool]] = [
    GrafanaDashboardListTool,
    GrafanaDashboardGetTool,
    GrafanaAnnotationCreateTool,
]
