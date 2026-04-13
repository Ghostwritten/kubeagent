"""Tests for Phase 10 — Skill + Hook + Headless."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kubeagent.agent.policy import PolicyRule, RBACPolicy, Role
from kubeagent.cli.headless import HeadlessResult, run_batch, run_headless
from kubeagent.hooks.engine import HookEngine, HookEvent, HookResult
from kubeagent.skills.base import Skill
from kubeagent.skills.loader import load_user_skill, validate_skill_markdown
from kubeagent.skills.registry import SkillRegistry

# ---------------------------------------------------------------------------
# T4: Headless Mode
# ---------------------------------------------------------------------------


class TestRunHeadless:
    def test_run_headless_returns_result(self) -> None:
        """run_headless executes a query and returns a result."""
        result = run_headless("list pods", output_format="text")
        assert isinstance(result, HeadlessResult)
        assert result.exit_code in (0, 1)
        assert result.output is not None

    def test_run_headless_json_format(self) -> None:
        """run_headless with json format doesn't crash."""
        result = run_headless("list pods", output_format="json")
        assert result.format == "json"

    def test_headless_result_structure(self) -> None:
        """HeadlessResult has correct fields."""
        result = HeadlessResult(output="test output", exit_code=0, format="text")
        assert result.output == "test output"
        assert result.exit_code == 0
        assert result.format == "text"


class TestRunBatch:
    def test_run_batch_empty_file(self) -> None:
        """Batch with empty file returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "commands.txt"
            batch_file.write_text("")
            result = run_batch(batch_file)
            assert result.exit_code == 0

    def test_run_batch_single_command(self) -> None:
        """Batch with single command executes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "commands.txt"
            batch_file.write_text("list pods\n")
            result = run_batch(batch_file)
            assert result.exit_code in (0, 1)
            assert result.output is not None

    def test_run_batch_multiple_commands(self) -> None:
        """Batch with multiple commands executes all."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "commands.txt"
            batch_file.write_text("list pods\nlist namespaces\n")
            result = run_batch(batch_file)
            assert result.exit_code in (0, 1)

    def test_run_batch_nonexistent_file(self) -> None:
        """Batch with nonexistent file returns exit_code 1."""
        result = run_batch(Path("/nonexistent/commands.txt"))
        assert result.exit_code == 1
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# T3: Hook Engine
# ---------------------------------------------------------------------------


class TestHookEngine:
    def test_hook_engine_loads_hooks(self) -> None:
        """HookEngine loads hooks from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_file = Path(tmpdir) / "hooks.yaml"
            hooks_file.write_text(
                "hooks:\n  pre-apply:\n    - name: validate-yaml\n      command: echo 'pre-apply'\n"
            )
            engine = HookEngine(hooks_file=str(hooks_file))
            assert len(engine.get_hooks("pre-apply")) == 1

    def test_hook_engine_empty_config(self) -> None:
        """HookEngine handles empty/missing config."""
        engine = HookEngine(hooks_file="/nonexistent/hooks.yaml")
        assert engine.get_hooks("pre-apply") == []
        assert engine.get_hooks("post-deploy") == []

    def test_hook_event_types(self) -> None:
        """All expected hook event types exist."""
        events = [
            "pre-apply",
            "post-apply",
            "pre-delete",
            "post-delete",
            "pre-deploy",
            "post-deploy",
            "on-error",
            "on-connect",
            "on-diagnose",
        ]
        for event in events:
            assert hasattr(HookEvent, event.upper().replace("-", "_"))

    def test_hook_result_structure(self) -> None:
        """HookResult has correct fields."""
        result = HookResult(
            hook_name="test-hook",
            event=HookEvent.PRE_APPLY,
            success=True,
            output="ok",
            error=None,
        )
        assert result.success is True
        assert result.output == "ok"

    def test_can_proceed_passes(self) -> None:
        """can_proceed returns True when no hooks configured."""
        engine = HookEngine(hooks_file="/nonexistent")
        ok, reason = engine.can_proceed(HookEvent.PRE_APPLY)
        assert ok is True

    def test_can_proceed_blocks_on_failure(self) -> None:
        """can_proceed returns False when pre-hook fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_file = Path(tmpdir) / "hooks.yaml"
            hooks_file.write_text(
                "hooks:\n  pre-apply:\n    - name: fail-hook\n      command: exit 1\n"
            )
            engine = HookEngine(hooks_file=str(hooks_file))
            ok, reason = engine.can_proceed(HookEvent.PRE_APPLY)
            assert ok is False
            assert "fail-hook" in reason


# ---------------------------------------------------------------------------
# T1: Skill System Foundation
# ---------------------------------------------------------------------------


class TestSkillRegistry:
    def test_loads_builtin_skills(self) -> None:
        """SkillRegistry loads all built-in skills."""
        registry = SkillRegistry()
        skill_names = registry.list_skills()
        assert "diagnose" in skill_names
        assert "deploy" in skill_names
        assert "rollback" in skill_names
        assert "security-audit" in skill_names

    def test_get_skill(self) -> None:
        """get_skill returns correct Skill."""
        registry = SkillRegistry()
        skill = registry.get("diagnose")
        assert skill is not None
        assert skill.name == "diagnose"
        assert skill.description != ""

    def test_get_unknown_skill(self) -> None:
        """get_skill for unknown skill returns None."""
        registry = SkillRegistry()
        assert registry.get("nonexistent-skill") is None

    def test_list_skills_returns_all(self) -> None:
        """list_skills returns all skill names."""
        registry = SkillRegistry()
        names = registry.list_skills()
        assert len(names) >= 4


class TestSkill:
    def test_skill_structure(self) -> None:
        """Skill has all required fields."""
        skill = Skill(
            name="test-skill",
            description="Test skill",
            trigger="test",
            steps=["step1", "step2"],
            required_tools=["get_pods"],
        )
        assert skill.name == "test-skill"
        assert len(skill.steps) == 2
        assert "get_pods" in skill.required_tools

    def test_builtin_skill_structure(self) -> None:
        """BuiltinSkill extends Skill with execute method."""
        from kubeagent.skills.builtin.diagnose import DiagnoseSkill

        skill = DiagnoseSkill()
        assert skill.name == "diagnose"
        assert callable(skill.execute)


# ---------------------------------------------------------------------------
# T5: Policy Engine Enhancement (RBAC)
# ---------------------------------------------------------------------------


class TestRBACPolicy:
    def test_rbac_allows_admin(self) -> None:
        """Admin role can do anything."""
        policy = RBACPolicy(role=Role.ADMIN)
        assert policy.can_delete("pod", "default") is True
        assert policy.can_apply("deployment", "default") is True

    def test_rbac_blocks_viewer_delete(self) -> None:
        """Viewer role cannot delete."""
        policy = RBACPolicy(role=Role.VIEWER)
        assert policy.can_delete("pod", "default") is False
        assert policy.can_delete("deployment", "default") is False

    def test_rbac_allows_viewer_read(self) -> None:
        """Viewer role can read."""
        policy = RBACPolicy(role=Role.VIEWER)
        assert policy.can_get("pod", "default") is True
        assert policy.can_get("service", "default") is True

    def test_rbac_namespace_protection(self) -> None:
        """Protected namespaces block non-admin."""
        policy = RBACPolicy(role=Role.OPERATOR, protected_namespaces=["kube-system"])
        assert policy.can_delete("pod", "kube-system") is False
        assert policy.can_delete("pod", "default") is True

    def test_role_enum(self) -> None:
        """All expected roles exist."""
        assert Role.ADMIN is not None
        assert Role.OPERATOR is not None
        assert Role.VIEWER is not None

    def test_policy_rule_structure(self) -> None:
        """PolicyRule has correct structure."""
        rule = PolicyRule(
            action="delete",
            resource="pod",
            namespace="default",
            allow=False,
        )
        assert rule.allow is False
        assert rule.action == "delete"


# ---------------------------------------------------------------------------
# T6: User-defined Skills
# ---------------------------------------------------------------------------


class TestUserSkillLoader:
    def test_load_skill_from_markdown(self) -> None:
        """load_user_skill parses markdown skill file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "my-skill.md"
            skill_file.write_text(
                "---\n"
                "name: my-skill\n"
                "description: My custom skill\n"
                "trigger: my-skill\n"
                "---\n"
                "# Steps\n"
                "1. Step one\n"
                "2. Step two\n"
            )
            skill = load_user_skill(skill_file)
            assert skill is not None
            assert skill.name == "my-skill"

    def test_validate_skill_markdown(self) -> None:
        """validate_skill_markdown checks required frontmatter."""
        valid = "---\nname: test\ndescription: Test\ntrigger: test\n---\n# Steps\n1. Do thing\n"
        assert validate_skill_markdown(valid) is True

    def test_validate_skill_missing_name(self) -> None:
        """Missing name field fails validation."""
        invalid = "---\ndescription: Test\n---\n"
        assert validate_skill_markdown(invalid) is False
