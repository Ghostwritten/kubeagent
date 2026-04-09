"""kubectl wrapper for operations that Python Client handles poorly."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class KubectlResult:
    """Result from a kubectl command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


# Commands allowed to be executed through the wrapper
_ALLOWED_COMMANDS = {"exec", "top", "apply", "port-forward"}

# Parameters that are whitelisted for security
_ALLOWED_FLAGS = {
    "-n",
    "--namespace",
    "-c",
    "--container",
    "-l",
    "--selector",
    "--all-namespaces",
    "-f",
    "--filename",
    "--tail",
    "--since",
    "-p",
    "--previous",
    "-i",
    "--stdin",
    "-t",
    "--tty",
    "--no-headers",
    "--context",
}


def _kubectl_available() -> bool:
    """Check if kubectl is installed."""
    return shutil.which("kubectl") is not None


def _validate_params(args: list[str]) -> None:
    """Validate kubectl parameters against whitelist."""
    for arg in args:
        # Skip positional args and the -- separator
        if arg == "--" or not arg.startswith("-"):
            continue
        if arg.startswith("---"):
            continue
        flag = arg.split("=")[0]
        if flag not in _ALLOWED_FLAGS:
            raise ValueError(f"Disallowed kubectl flag: {flag}")


def run_kubectl(args: list[str], timeout: int = 30) -> KubectlResult:
    """Execute a kubectl command with argument list (NOT shell string).

    Args:
        args: Arguments to pass to kubectl (e.g., ["exec", "pod-name", "--", "ls"])
        timeout: Command timeout in seconds.

    Returns:
        KubectlResult with exit code, stdout, and stderr.

    Raises:
        FileNotFoundError: If kubectl is not installed.
        ValueError: If disallowed flags are used.
    """
    if not _kubectl_available():
        raise FileNotFoundError("kubectl is not installed or not in PATH")

    if not args:
        raise ValueError("No arguments provided")

    command = args[0]
    if command not in _ALLOWED_COMMANDS:
        allowed = ", ".join(sorted(_ALLOWED_COMMANDS))
        raise ValueError(f"kubectl {command} is not allowed. Allowed: {allowed}")

    _validate_params(args)

    cmd = ["kubectl", *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return KubectlResult(
            command=" ".join(cmd),
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
        )

    return KubectlResult(
        command=" ".join(cmd),
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def kubectl_exec(
    pod: str,
    namespace: str = "default",
    container: str | None = None,
    command: list[str] | None = None,
) -> KubectlResult:
    """Execute a command in a pod via kubectl exec."""
    args = ["exec", pod, "-n", namespace]
    if container:
        args.extend(["-c", container])
    args.append("--")
    args.extend(command or ["/bin/sh"])
    return run_kubectl(args)


def kubectl_top(
    resource: str = "pods",
    namespace: str = "",
    selector: str = "",
) -> KubectlResult:
    """Show resource usage via kubectl top."""
    args = ["top", resource]
    if namespace:
        args.extend(["-n", namespace])
    if selector:
        args.extend(["-l", selector])
    return run_kubectl(args, timeout=10)


def kubectl_apply_file(file_path: str, namespace: str = "default") -> KubectlResult:
    """Apply a YAML file via kubectl apply -f."""
    args = ["apply", "-f", file_path, "-n", namespace]
    return run_kubectl(args)
