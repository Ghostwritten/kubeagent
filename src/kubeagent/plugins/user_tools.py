"""User-defined tool registration — Python functions, shell scripts, kubectl plugins."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from kubeagent.infra.executor import SecurityLevel
from kubeagent.plugins.interface import PluginPermissions
from kubeagent.plugins.sandbox import PluginSandbox
from kubeagent.tools.base import BaseTool


@dataclass
class ToolArg:
    """A tool argument definition."""

    name: str
    type: str = "str"  # str | int | bool | list
    description: str = ""
    required: bool = True
    default: str | None = None


@dataclass
class ShellToolConfig:
    """Configuration for a shell-based tool."""

    command: str  # Shell command, with {arg} placeholders
    args_schema: list[ToolArg] = field(default_factory=list)
    timeout: int = 30


class ShellTool(BaseTool):
    """A tool backed by a shell script or command.

    Created by users via config or plugin manifest.
    """

    name: str = ""
    description: str = ""
    security_level: SecurityLevel = SecurityLevel.SENSITIVE

    def __init__(
        self,
        name: str,
        command: str,
        args_schema: list[ToolArg] | None = None,
        timeout: int = 30,
        description: str = "",
        security_level: SecurityLevel = SecurityLevel.SENSITIVE,
    ) -> None:
        self.name = name
        self.description = description or f"Shell tool: {command[:50]}"
        self.command = command
        self.args_schema = args_schema or []
        self.timeout = timeout
        self.security_level = security_level

    def execute(self, **kwargs: object) -> object:
        """Execute the shell command with provided arguments."""
        cmd = self.command
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            if placeholder in cmd:
                cmd = cmd.replace(placeholder, str(value))

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            return f"[ERROR] {result.stderr.strip()}"
        return result.stdout.strip()

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "security_level": str(self.security_level.value),
            "type": "shell",
        }


class PythonFunctionTool(BaseTool):
    """A tool backed by a Python callable.

    The callable is wrapped and sandboxed with PluginSandbox.
    """

    name: str = ""
    description: str = ""
    security_level: SecurityLevel = SecurityLevel.SENSITIVE

    def __init__(
        self,
        name: str,
        func: object,
        args_schema: list[ToolArg] | None = None,
        description: str = "",
        security_level: SecurityLevel = SecurityLevel.SENSITIVE,
        permissions: PluginPermissions | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.func = func
        self.args_schema = args_schema or []
        self.security_level = security_level
        self._sandbox = PluginSandbox(permissions) if permissions else None

    def execute(self, **kwargs: object) -> object:
        """Execute the wrapped Python function."""
        if self._sandbox:
            # Use sandbox for execution
            code = f"result = {self.func.__name__}(**kwargs)"
            return self._sandbox.execute_python(code, **kwargs)

        try:
            return self.func(**kwargs)
        except TypeError as e:
            return f"[ERROR] Invalid arguments: {e}"
        except Exception as e:
            return f"[ERROR] {type(e).__name__}: {e}"

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "security_level": str(self.security_level.value),
            "type": "python",
        }


# Global list of user-registered tools
_USER_TOOLS: list[BaseTool] = []


def register_user_tool(tool: BaseTool) -> None:
    """Register a user-defined tool.

    The tool will be added to the global tool registry.
    """
    from kubeagent.tools.registry import get_registry

    _USER_TOOLS.append(tool)
    get_registry().register(tool)


def unregister_user_tool(name: str) -> bool:
    """Unregister a user-defined tool by name."""
    global _USER_TOOLS
    for i, tool in enumerate(_USER_TOOLS):
        if tool.name == name:
            del _USER_TOOLS[i]
            return True
    return False


def list_user_tools() -> list[BaseTool]:
    """Return all registered user tools."""
    return list(_USER_TOOLS)
