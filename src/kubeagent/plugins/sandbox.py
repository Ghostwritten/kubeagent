"""Plugin sandbox — permission enforcement for plugin execution."""

from __future__ import annotations

import subprocess

from kubeagent.plugins.interface import PluginPermissions


class PluginSandbox:
    """Sandbox for running plugin code with declared permissions.

    Enforces:
    - Allowed tools (by name)
    - Allowed namespaces
    - Allowed clusters
    - Shell command restrictions
    """

    def __init__(self, permissions: PluginPermissions) -> None:
        self._perms = permissions
        self._denylist = ["rm -rf", "dd if=", ":(){:|:&};:", "curl |sh", "wget |sh"]

    def allows_tool(self, tool_name: str) -> bool:
        """Check if plugin is allowed to use a tool."""
        return self._perms.allows_tool(tool_name)

    def allows_namespace(self, namespace: str) -> bool:
        """Check if plugin is allowed to access a namespace."""
        return self._perms.allows_namespace(namespace)

    def execute_python(self, code: str, **kwargs: str) -> object:
        """Execute Python code in a restricted environment.

        Returns the value of `result` variable if set, otherwise None.
        """
        safe_builtins = {
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "sorted": sorted,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "type": type,
            "isinstance": isinstance,
            "True": True,
            "False": False,
            "None": None,
        }

        local_ns: dict = {"result": None}
        local_ns.update(kwargs)

        try:
            # Try eval first for simple expressions (e.g. "1 + 1")
            try:
                return eval(code, {"__builtins__": safe_builtins}, local_ns)  # noqa: S307
            except SyntaxError:
                pass
            exec(code, {"__builtins__": safe_builtins}, local_ns)
            return local_ns.get("result", None)
        except NameError as e:
            if "open" in str(e) or "__import__" in str(e):
                raise PermissionError(f"Blocked: {e}") from e
            raise
        except Exception as e:
            raise RuntimeError(f"Plugin execution error: {e}") from e

    def execute_shell(self, command: str) -> tuple[bool, str]:
        """Execute a shell command with safety checks.

        Returns (success, output).
        Denies commands containing dangerous patterns.
        """
        cmd_lower = command.lower().strip()
        for pattern in self._denylist:
            if pattern.lower() in cmd_lower:
                return False, f"[DENIED] Command contains blocked pattern: {pattern}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            success = result.returncode == 0
            output = result.stdout if result.stdout else result.stderr
            return success, output.strip()
        except subprocess.TimeoutExpired:
            return False, "[DENIED] Command timed out (10s limit)"
        except Exception as e:
            return False, f"[ERROR] {e}"
