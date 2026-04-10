"""Hook Engine — event-driven automation for KubeAgent operations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class HookEvent(Enum):
    """Hook lifecycle events."""

    PRE_APPLY = "pre-apply"
    POST_APPLY = "post-apply"
    PRE_DELETE = "pre-delete"
    POST_DELETE = "post-delete"
    PRE_DEPLOY = "pre-deploy"
    POST_DEPLOY = "post-deploy"
    ON_ERROR = "on-error"
    ON_CONNECT = "on-connect"
    ON_DIAGNOSE = "on-diagnose"


@dataclass
class Hook:
    """A single hook definition."""

    name: str
    command: str
    enabled: bool = True
    timeout: int = 30  # seconds


@dataclass
class HookResult:
    """Result from a single hook execution."""

    hook_name: str
    event: HookEvent
    success: bool
    output: str
    error: str | None = None


@dataclass
class HookEngine:
    """Event-driven automation engine.

    Loads hook definitions from hooks.yaml and executes them at the
    appropriate lifecycle points. Supports:
    - pre/post hooks for all mutating operations
    - on-error hooks for failure handling
    - on-connect hooks for cluster connection events
    - on-diagnose hooks for diagnostic operations

    Execution order for an operation:
    1. Policy check
    2. pre-* hook (can abort if returns non-zero)
    3. User confirmation (if interactive)
    4. Operation executes
    5. post-* hook (always runs on success)
    6. on-error hook (runs if operation failed)
    """

    hooks_file: str | Path | None = None
    _hooks: dict[str, list[Hook]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._load_hooks()

    def _load_hooks(self) -> None:
        """Load hooks from YAML config file."""
        if self.hooks_file is None:
            default = Path.home() / ".kubeagent" / "hooks.yaml"
            if default.exists():
                self.hooks_file = str(default)
            else:
                self._hooks = {}
                return

        path = Path(self.hooks_file)
        if not path.exists():
            self._hooks = {}
            return

        try:
            data = yaml.safe_load(path.read_text()) or {}
            hooks_list: list[dict] = data.get("hooks", {})
            self._hooks = {}

            for event_name, hooks in hooks_list.items():
                if not isinstance(hooks, list):
                    continue
                event_hooks = []
                for hook_def in hooks:
                    if isinstance(hook_def, dict):
                        event_hooks.append(
                            Hook(
                                name=hook_def.get("name", "unnamed"),
                                command=hook_def.get("command", ""),
                                enabled=hook_def.get("enabled", True),
                                timeout=hook_def.get("timeout", 30),
                            )
                        )
                if event_hooks:
                    self._hooks[event_name] = event_hooks
        except Exception:
            self._hooks = {}

    def get_hooks(self, event: str) -> list[Hook]:
        """Get all hooks for a given event."""
        return self._hooks.get(event, [])

    def run_pre_apply(self, resource: str, namespace: str) -> list[HookResult]:
        """Run pre-apply hooks. Return results; first failure aborts operation."""
        return self._run_hooks(HookEvent.PRE_APPLY)

    def run_post_apply(self, resource: str, namespace: str) -> list[HookResult]:
        """Run post-apply hooks."""
        return self._run_hooks(HookEvent.POST_APPLY)

    def run_pre_delete(self, resource: str, namespace: str) -> list[HookResult]:
        """Run pre-delete hooks. Return results; first failure aborts operation."""
        return self._run_hooks(HookEvent.PRE_DELETE)

    def run_post_delete(self, resource: str, namespace: str) -> list[HookResult]:
        """Run post-delete hooks."""
        return self._run_hooks(HookEvent.POST_DELETE)

    def run_pre_deploy(self, manifest: str, namespace: str) -> list[HookResult]:
        """Run pre-deploy hooks."""
        return self._run_hooks(HookEvent.PRE_DEPLOY)

    def run_post_deploy(self, manifest: str, namespace: str) -> list[HookResult]:
        """Run post-deploy hooks."""
        return self._run_hooks(HookEvent.POST_DEPLOY)

    def run_on_error(
        self,
        operation: str,
        error: str,
        resource: str | None = None,
    ) -> list[HookResult]:
        """Run on-error hooks."""
        return self._run_hooks(HookEvent.ON_ERROR)

    def run_on_connect(self, cluster: str) -> list[HookResult]:
        """Run on-connect hooks."""
        return self._run_hooks(HookEvent.ON_CONNECT)

    def run_on_diagnose(self, query: str) -> list[HookResult]:
        """Run on-diagnose hooks."""
        return self._run_hooks(HookEvent.ON_DIAGNOSE)

    def _run_hooks(self, event: HookEvent) -> list[HookResult]:
        """Execute all hooks for an event. Returns results for all hooks."""
        results: list[HookResult] = []
        hooks = self.get_hooks(event.value)

        for hook in hooks:
            if not hook.enabled:
                continue
            result = self._execute_hook(hook, event)
            results.append(result)

        return results

    def _execute_hook(self, hook: Hook, event: HookEvent) -> HookResult:
        """Execute a single hook and return its result."""
        try:
            proc = subprocess.run(
                hook.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=hook.timeout,
            )
            success = proc.returncode == 0
            output = proc.stdout.strip() if proc.stdout else ""
            error = proc.stderr.strip() if proc.stderr else None
            if proc.returncode != 0 and not error:
                error = f"exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            success = False
            output = ""
            error = f"timeout after {hook.timeout}s"
        except Exception as e:
            success = False
            output = ""
            error = str(e)

        return HookResult(
            hook_name=hook.name,
            event=event,
            success=success,
            output=output,
            error=error,
        )

    def can_proceed(self, event: HookEvent) -> tuple[bool, str]:
        """Check if operation can proceed (all pre-hooks passed).

        Returns (can_proceed, reason).
        """
        pre_event_map = {
            HookEvent.PRE_APPLY: HookEvent.PRE_APPLY,
            HookEvent.PRE_DELETE: HookEvent.PRE_DELETE,
            HookEvent.PRE_DEPLOY: HookEvent.PRE_DEPLOY,
        }

        if event not in pre_event_map:
            return True, ""

        pre_event = pre_event_map[event]
        results = self._run_hooks(pre_event)

        for result in results:
            if not result.success:
                return False, f"Hook '{result.hook_name}' failed: {result.error}"

        return True, ""
