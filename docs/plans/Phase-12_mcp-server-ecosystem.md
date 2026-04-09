# Phase 12 — MCP Server + Ecosystem

> Status: `pending`
> Depends on: Phase 11
> Master Plan: [00-master-plan.md](00-master-plan.md)

---

## Goal

Expose KubeAgent as an MCP (Model Context Protocol) server and integrate with major K8s ecosystem tools (Helm, Istio, ArgoCD, Prometheus, Grafana).

---

## Tasks

- [ ] **T1: MCP Server implementation**
  - Implement MCP protocol server
  - Expose all KubeAgent tools as MCP tools
  - Expose skills as MCP resources
  - Authentication and authorization for MCP clients

- [ ] **T2: MCP Server lifecycle**
  - `kubeagent mcp start` — start MCP server
  - `kubeagent mcp stop` — stop MCP server
  - `kubeagent mcp status` — show server status
  - Server runs as background daemon

- [ ] **T3: Helm plugin**
  - Tools: `helm_list`, `helm_install`, `helm_upgrade`, `helm_rollback`, `helm_uninstall`
  - Skills: `/helm-deploy`, `/helm-diagnose`
  - Integration with existing Helm CLI

- [ ] **T4: Istio plugin**
  - Tools: `istio_analyze`, `istio_proxy_status`, `istio_config`
  - Skills: `/istio-diagnose`, `/istio-security-audit`
  - Service mesh topology visualization

- [ ] **T5: ArgoCD plugin**
  - Tools: `argocd_app_list`, `argocd_app_sync`, `argocd_app_status`
  - Skills: `/argocd-deploy`, `/argocd-rollback`
  - GitOps workflow integration

- [ ] **T6: Observability plugins**
  - Prometheus: query metrics, alert status
  - Grafana: dashboard links, snapshot creation
  - Integration with cluster monitoring

- [ ] **T7: Documentation and examples**
  - MCP client examples (Claude Code, Cursor)
  - Plugin development guide
  - Ecosystem integration tutorials

---

## Acceptance Criteria

1. MCP server starts and accepts connections
2. Claude Code can connect to KubeAgent via MCP and call tools
3. Helm plugin can list and install charts
4. Istio plugin can diagnose service mesh issues
5. ArgoCD plugin can sync applications
6. At least 5 community-contributed plugins/skills exist

---

## Milestone: v1.0 "小满贯"

Phase 12 completion marks **v1.0** — full platform with plugin ecosystem and MCP support. The project has achieved its initial vision and is ready for community growth.

---

## Notes

- MCP protocol spec: https://modelcontextprotocol.io/
- Ecosystem plugins can be separate packages
- Document how other AI tools can use KubeAgent as K8s capability provider
