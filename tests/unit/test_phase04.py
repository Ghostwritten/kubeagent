"""Tests for Phase 04 — write tools, kubectl wrapper, and registry integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kubeagent.infra.executor import SecurityLevel
from kubeagent.infra.kubectl import (
    KubectlResult,
    _validate_params,
    run_kubectl,
)
from kubeagent.tools.registry import get_registry

# ---------------------------------------------------------------------------
# Kubectl wrapper tests
# ---------------------------------------------------------------------------


class TestKubectlResult:
    def test_ok_property(self) -> None:
        r = KubectlResult(command="kubectl exec pod", exit_code=0, stdout="ok", stderr="")
        assert r.ok is True

    def test_ok_property_fail(self) -> None:
        r = KubectlResult(command="kubectl exec pod", exit_code=1, stdout="", stderr="error")
        assert r.ok is False


class TestValidateParams:
    def test_allowed_flags(self) -> None:
        _validate_params(["exec", "pod", "-n", "default", "-c", "sidecar"])

    def test_disallowed_flag(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Disallowed"):
            _validate_params(["--dangerous-flag"])

    def test_no_flags(self) -> None:
        _validate_params(["exec", "pod"])


class TestRunKubectl:
    def test_kubectl_not_installed(self) -> None:
        import pytest

        with patch("kubeagent.infra.kubectl._kubectl_available", return_value=False):
            with pytest.raises(FileNotFoundError, match="not installed"):
                run_kubectl(["exec", "pod"])

    def test_empty_args(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="No arguments"):
            run_kubectl([])

    def test_disallowed_command(self) -> None:
        import pytest

        with patch("kubeagent.infra.kubectl._kubectl_available", return_value=True):
            with pytest.raises(ValueError, match="not allowed"):
                run_kubectl(["delete", "pod", "x"])

    def test_successful_exec(self) -> None:
        with patch("kubeagent.infra.kubectl._kubectl_available", return_value=True):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "hello\n"
            mock_proc.stderr = ""
            with patch("subprocess.run", return_value=mock_proc):
                result = run_kubectl(["exec", "pod", "--", "echo", "hello"])
                assert result.ok is True
                assert result.stdout == "hello\n"

    def test_timeout(self) -> None:
        import subprocess

        with patch("kubeagent.infra.kubectl._kubectl_available", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kubectl", 30)):
                result = run_kubectl(["exec", "pod", "--", "sleep", "999"])
                assert result.ok is False
                assert "timed out" in result.stderr


# ---------------------------------------------------------------------------
# Write tool tests (mocked executor)
# ---------------------------------------------------------------------------


def _mock_executor() -> MagicMock:
    return MagicMock()


class TestApplyYamlTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.apply import ApplyYamlTool

        executor = _mock_executor()
        executor.apply_yaml.return_value = {
            "applied": [
                {
                    "kind": "Deployment",
                    "name": "nginx",
                    "namespace": "default",
                    "action": "created",
                }
            ],
            "dry_run": False,
        }

        tool = ApplyYamlTool()
        yaml_content = "kind: Deployment\nmetadata:\n  name: nginx"
        result = tool.execute(executor, yaml_content=yaml_content)
        assert result["applied"][0]["action"] == "created"
        executor.apply_yaml.assert_called_once_with(
            yaml_content=yaml_content, namespace="default", dry_run=False
        )

    def test_execute_dry_run(self) -> None:
        from kubeagent.tools.builtin.apply import ApplyYamlTool

        executor = _mock_executor()
        executor.apply_yaml.return_value = {
            "applied": [
                {"kind": "Pod", "name": "test", "namespace": "default", "action": "dry-run"}
            ],
            "dry_run": True,
        }

        tool = ApplyYamlTool()
        result = tool.execute(executor, yaml_content="x", dry_run=True)
        assert result["dry_run"] is True


class TestDeleteResourceTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.delete import DeleteResourceTool

        executor = _mock_executor()
        executor.delete_resource.return_value = {
            "deleted": True,
            "kind": "Pod",
            "name": "nginx-123",
            "action": "deleted",
        }

        tool = DeleteResourceTool()
        result = tool.execute(executor, kind="pod", name="nginx-123")
        assert result["deleted"] is True
        assert tool.security_level == SecurityLevel.DANGEROUS


class TestScaleResourceTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.scale import ScaleResourceTool

        executor = _mock_executor()
        executor.scale_resource.return_value = {
            "scaled": True,
            "kind": "deployment",
            "name": "nginx",
            "replicas": 3,
            "action": "scaled",
        }

        tool = ScaleResourceTool()
        result = tool.execute(executor, kind="deployment", name="nginx", replicas=3)
        assert result["scaled"] is True
        assert result["replicas"] == 3
        assert tool.security_level == SecurityLevel.SENSITIVE


class TestRestartPodTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.restart import RestartPodTool

        executor = _mock_executor()
        executor.restart_pod.return_value = {
            "restarted": True,
            "name": "nginx-123",
            "namespace": "default",
            "previous_status": "Running",
        }

        tool = RestartPodTool()
        result = tool.execute(executor, name="nginx-123")
        assert result["restarted"] is True
        assert tool.security_level == SecurityLevel.DANGEROUS


class TestCordonNodeTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.nodes_ops import CordonNodeTool

        executor = _mock_executor()
        executor.cordon_node.return_value = {"cordoned": True, "name": "node-1"}

        tool = CordonNodeTool()
        result = tool.execute(executor, name="node-1")
        assert result["cordoned"] is True
        assert tool.security_level == SecurityLevel.DANGEROUS


class TestUncordonNodeTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.nodes_ops import UncordonNodeTool

        executor = _mock_executor()
        executor.uncordon_node.return_value = {"uncordoned": True, "name": "node-1"}

        tool = UncordonNodeTool()
        result = tool.execute(executor, name="node-1")
        assert result["uncordoned"] is True
        assert tool.security_level == SecurityLevel.SENSITIVE


class TestDrainNodeTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.nodes_ops import DrainNodeTool

        executor = _mock_executor()
        executor.drain_node.return_value = {
            "drained": True,
            "name": "node-1",
            "evicted": ["default/nginx-123"],
            "skipped": [],
        }

        tool = DrainNodeTool()
        result = tool.execute(executor, name="node-1")
        assert result["drained"] is True
        assert tool.security_level == SecurityLevel.DANGEROUS


# ---------------------------------------------------------------------------
# kubectl tool tests
# ---------------------------------------------------------------------------


class TestKubectlExecTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.kubectl import KubectlExecTool

        with patch("kubeagent.tools.builtin.kubectl.kubectl_exec") as mock_exec:
            mock_exec.return_value = KubectlResult(
                command="kubectl exec pod -n default -- ls",
                exit_code=0,
                stdout="file.txt\n",
                stderr="",
            )
            tool = KubectlExecTool()
            result = tool.execute(pod="my-pod", command=["ls"])
            assert result["ok"] is True
            assert "file.txt" in result["stdout"]


class TestKubectlTopTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.kubectl import KubectlTopTool

        with patch("kubeagent.tools.builtin.kubectl.kubectl_top") as mock_top:
            mock_top.return_value = KubectlResult(
                command="kubectl top pods", exit_code=0, stdout="NAME  CPU  MEMORY\n", stderr=""
            )
            tool = KubectlTopTool()
            result = tool.execute()
            assert result["ok"] is True


class TestKubectlApplyFileTool:
    def test_execute(self) -> None:
        from kubeagent.tools.builtin.kubectl import KubectlApplyFileTool

        with patch("kubeagent.tools.builtin.kubectl.kubectl_apply_file") as mock_apply:
            mock_apply.return_value = KubectlResult(
                command="kubectl apply -f deploy.yaml",
                exit_code=0,
                stdout="deployment.apps/nginx created\n",
                stderr="",
            )
            tool = KubectlApplyFileTool()
            result = tool.execute(file_path="deploy.yaml")
            assert result["ok"] is True


# ---------------------------------------------------------------------------
# Registry integration — verify all Phase 04 tools are discovered
# ---------------------------------------------------------------------------


class TestRegistryPhase04:
    def test_all_write_tools_registered(self) -> None:
        registry = get_registry()
        assert registry.get("apply_yaml") is not None
        assert registry.get("delete_resource") is not None
        assert registry.get("scale_resource") is not None
        assert registry.get("restart_pod") is not None
        assert registry.get("cordon_node") is not None
        assert registry.get("uncordon_node") is not None
        assert registry.get("drain_node") is not None
        assert registry.get("kubectl_exec") is not None
        assert registry.get("kubectl_top") is not None
        assert registry.get("kubectl_apply_file") is not None

    def test_tool_count(self) -> None:
        registry = get_registry()
        # 8 read tools + 9 write tools = 17
        assert len(registry) >= 17

    def test_security_levels_correct(self) -> None:
        registry = get_registry()
        safe = registry.filter_by_security(SecurityLevel.SAFE)
        sensitive = registry.filter_by_security(SecurityLevel.SENSITIVE)
        dangerous = registry.filter_by_security(SecurityLevel.DANGEROUS)

        safe_names = {t().name for t in safe}
        sensitive_names = {t().name for t in sensitive}
        dangerous_names = {t().name for t in dangerous}

        # Write tools should NOT be in safe
        assert "delete_resource" not in safe_names
        assert "apply_yaml" not in safe_names

        # Dangerous tools
        assert "delete_resource" in dangerous_names
        assert "restart_pod" in dangerous_names
        assert "cordon_node" in dangerous_names
        assert "drain_node" in dangerous_names

        # Sensitive tools
        assert "apply_yaml" in sensitive_names
        assert "scale_resource" in sensitive_names
        assert "uncordon_node" in sensitive_names
