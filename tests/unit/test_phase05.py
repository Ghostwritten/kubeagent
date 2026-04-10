"""Tests for Phase 05 — LLM integration and agent core."""

from __future__ import annotations

from kubeagent.agent.model import get_agent_model, get_model_info, resolve_model_name
from kubeagent.agent.prompts import SYSTEM_PROMPT
from kubeagent.config.settings import KubeAgentConfig, ModelConfig

# ---------------------------------------------------------------------------
# Model resolution tests
# ---------------------------------------------------------------------------


class TestResolveModelName:
    def test_openai_prefix(self) -> None:
        assert resolve_model_name("gpt-4o") == "openai:gpt-4o"

    def test_anthropic_prefix(self) -> None:
        result = resolve_model_name("claude-sonnet-4-20250514")
        assert result == "anthropic:claude-sonnet-4-20250514"

    def test_ollama_explicit(self) -> None:
        assert resolve_model_name("ollama/llama3") == "ollama:llama3"

    def test_already_prefixed(self) -> None:
        assert resolve_model_name("openai:gpt-4o") == "openai:gpt-4o"

    def test_unknown_model(self) -> None:
        assert resolve_model_name("my-custom-model") == "openai:my-custom-model"


class TestGetModelInfo:
    def test_openai_info(self) -> None:
        info = get_model_info("gpt-4o")
        assert info.provider == "openai"
        assert not info.is_local

    def test_ollama_is_local(self) -> None:
        info = get_model_info("ollama/llama3")
        assert info.is_local
        assert info.provider == "ollama"

    def test_anthropic_info(self) -> None:
        info = get_model_info("claude-sonnet-4-20250514")
        assert info.provider == "anthropic"


class TestGetAgentModel:
    def test_uses_config_default(self) -> None:
        config = ModelConfig(default="gpt-4o")
        assert get_agent_model(config) == "openai:gpt-4o"


# ---------------------------------------------------------------------------
# Agent creation tests
# ---------------------------------------------------------------------------


class TestCreateAgent:
    def test_creates_agent(self) -> None:
        from pydantic_ai import Agent

        from kubeagent.agent.agent import create_agent

        config = KubeAgentConfig()
        agent = create_agent(config)
        assert isinstance(agent, Agent)

    def test_agent_model_is_set(self) -> None:
        from kubeagent.agent.agent import create_agent

        config = KubeAgentConfig()
        agent = create_agent(config)
        assert agent.model is not None


# ---------------------------------------------------------------------------
# Result formatting tests
# ---------------------------------------------------------------------------


class TestFormatResult:
    def test_string_passthrough(self) -> None:
        from kubeagent.agent.agent import _format_result

        assert _format_result("hello") == "hello"

    def test_empty_list(self) -> None:
        from kubeagent.agent.agent import _format_result

        assert _format_result([]) == "No results found."

    def test_list_of_dicts(self) -> None:
        from kubeagent.agent.agent import _format_result

        result = _format_result([{"name": "nginx", "status": "Running"}])
        assert "nginx" in result
        assert "Running" in result

    def test_dict_result(self) -> None:
        from kubeagent.agent.agent import _format_result

        result = _format_result({"deleted": True, "name": "nginx"})
        assert "deleted: True" in result
        assert "name: nginx" in result

    def test_dict_with_nested_list(self) -> None:
        from kubeagent.agent.agent import _format_result

        result = _format_result({"applied": [{"kind": "Pod", "action": "created"}]})
        assert "applied:" in result
        assert "Pod" in result

    def test_dict_with_simple_list(self) -> None:
        from kubeagent.agent.agent import _format_result

        result = _format_result({"evicted": ["default/nginx-123"]})
        assert "evicted:" in result
        assert "default/nginx-123" in result


# ---------------------------------------------------------------------------
# Input model tests
# ---------------------------------------------------------------------------


class TestInputModels:
    def test_get_pods_defaults(self) -> None:
        from kubeagent.agent.agent import GetPodsInput

        inp = GetPodsInput()
        assert inp.namespace == ""
        assert inp.label_selector is None

    def test_get_pod_logs_required(self) -> None:
        from kubeagent.agent.agent import GetPodLogsInput

        inp = GetPodLogsInput(name="nginx-123")
        assert inp.name == "nginx-123"
        assert inp.tail_lines == 100

    def test_apply_yaml_input(self) -> None:
        from kubeagent.agent.agent import ApplyYamlInput

        inp = ApplyYamlInput(yaml_content="kind: Pod")
        assert inp.dry_run is False
        assert inp.namespace == "default"

    def test_delete_resource_input(self) -> None:
        from kubeagent.agent.agent import DeleteResourceInput

        inp = DeleteResourceInput(kind="pod", name="nginx")
        assert inp.dry_run is False

    def test_drain_node_input(self) -> None:
        from kubeagent.agent.agent import DrainNodeInput

        inp = DrainNodeInput(name="node-1")
        assert inp.force is False


# ---------------------------------------------------------------------------
# Deps tests
# ---------------------------------------------------------------------------


class TestKubeAgentDeps:
    def test_holds_config(self) -> None:
        from kubeagent.agent.deps import KubeAgentDeps

        config = KubeAgentConfig()
        deps = KubeAgentDeps(config=config)
        assert deps.config.model.default == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Prompt template tests
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_contains_role(self) -> None:
        assert "KubeAgent" in SYSTEM_PROMPT

    def test_contains_guidelines(self) -> None:
        assert "Kubernetes" in SYSTEM_PROMPT
