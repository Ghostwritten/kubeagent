"""Plugin CLI commands — kubeagent plugin install/list/update/remove."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from kubeagent.plugins.manager import PluginManager


@dataclass
class CLIResult:
    """Result of a CLI command."""

    exit_code: int
    output: str


def run_plugin_command(
    args: list[str],
    plugins_dir: Path | None = None,
) -> CLIResult:
    """Run a plugin management command.

    Args:
        args: Command arguments, e.g. ["list"], ["install", "my-plugin"]
        plugins_dir: Override plugins directory

    Returns:
        CLIResult with exit_code and output.
    """
    if not args:
        return CLIResult(exit_code=1, output="Usage: kubeagent plugin <list|install|remove>")

    cmd = args[0]

    try:
        if cmd == "list":
            return _plugin_list(plugins_dir)
        elif cmd == "install":
            if len(args) < 2:
                return CLIResult(exit_code=1, output="Usage: kubeagent plugin install <package-or-url>")
            return _plugin_install(args[1], plugins_dir)
        elif cmd == "remove":
            if len(args) < 2:
                return CLIResult(exit_code=1, output="Usage: kubeagent plugin remove <name>")
            return _plugin_remove(args[1], plugins_dir)
        elif cmd == "update":
            if len(args) < 2:
                return CLIResult(exit_code=1, output="Usage: kubeagent plugin update <name>")
            return _plugin_update(args[1], plugins_dir)
        else:
            return CLIResult(exit_code=1, output=f"Unknown command: {cmd}")
    except Exception as e:
        return CLIResult(exit_code=1, output=f"[ERROR] {e}")


def _plugin_list(plugins_dir: Path | None = None) -> CLIResult:
    """List installed plugins."""
    mgr = PluginManager(plugins_dir=plugins_dir)
    plugins = mgr.list_plugins()

    if not plugins:
        return CLIResult(exit_code=0, output="No plugins installed.")

    lines = ["Installed plugins:"]
    for name in plugins:
        p = mgr.get_plugin(name)
        if p:
            lines.append(f"  {p.manifest.name} {p.manifest.version} ({p.manifest.type.value}) [{p.state.value}]")
        else:
            lines.append(f"  {name}")

    return CLIResult(exit_code=0, output="\n".join(lines))


def _plugin_install(
    package_or_url: str,
    plugins_dir: Path | None = None,
) -> CLIResult:
    """Install a plugin from PyPI package or git URL."""
    mgr = PluginManager(plugins_dir=plugins_dir)
    install_dir = mgr._plugins_dir

    try:
        # Try as PyPI package
        if package_or_url.startswith(("http://", "https://", "git+")):
            return _install_from_url(package_or_url, install_dir, mgr)
        else:
            return _install_from_pypi(package_or_url, install_dir, mgr)
    except Exception as e:
        return CLIResult(exit_code=1, output=f"[ERROR] Install failed: {e}")


def _install_from_pypi(
    package: str,
    install_dir: Path,
    mgr: PluginManager,
) -> CLIResult:
    """Install a plugin from PyPI using pip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download package
        result = subprocess.run(
            [sys.executable, "-m", "pip", "download", package, "-d", tmpdir, "--no-deps"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return CLIResult(
                exit_code=1,
                output=f"[ERROR] pip download failed: {result.stderr}",
            )

        # Extract
        try:
            import zipfile

            for f in Path(tmpdir).iterdir():
                if f.suffix == ".whl":
                    with zipfile.ZipFile(f) as zf:
                        zf.extractall(tmpdir)
        except Exception:
            pass

        # Find plugin.yaml
        candidates = list(Path(tmpdir).rglob("plugin.yaml"))
        if not candidates:
            return CLIResult(
                exit_code=1,
                output=f"[ERROR] No plugin.yaml found in package '{package}'. "
                "Is this a valid KubeAgent plugin?",
            )

        manifest = candidates[0].parent
        mgr.install_plugin(manifest)
        return CLIResult(exit_code=0, output=f"Installed plugin: {package}")


def _install_from_url(
    url: str,
    install_dir: Path,
    mgr: PluginManager,
) -> CLIResult:
    """Install a plugin from a git URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, tmpdir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return CLIResult(
                exit_code=1,
                output=f"[ERROR] git clone failed: {result.stderr}",
            )

        manifest_path = Path(tmpdir) / "plugin.yaml"
        if not manifest_path.exists():
            return CLIResult(
                exit_code=1,
                output="[ERROR] No plugin.yaml found in repository.",
            )

        mgr.install_plugin(Path(tmpdir))
        return CLIResult(exit_code=0, output=f"Installed plugin from {url}")


def _plugin_remove(name: str, plugins_dir: Path | None = None) -> CLIResult:
    """Remove an installed plugin."""
    mgr = PluginManager(plugins_dir=plugins_dir)
    try:
        mgr.remove_plugin(name)
        return CLIResult(exit_code=0, output=f"Removed plugin: {name}")
    except KeyError:
        return CLIResult(exit_code=1, output=f"[ERROR] Plugin '{name}' not found.")
    except Exception as e:
        return CLIResult(exit_code=1, output=f"[ERROR] {e}")


def _plugin_update(name: str, plugins_dir: Path | None = None) -> CLIResult:
    """Update a plugin (reinstall from PyPI)."""
    mgr = PluginManager(plugins_dir=plugins_dir)
    plugin = mgr.get_plugin(name)
    if not plugin:
        return CLIResult(exit_code=1, output=f"[ERROR] Plugin '{name}' not found.")

    try:
        mgr.remove_plugin(name)
        return _install_from_pypi(name, mgr._plugins_dir, mgr)
    except Exception as e:
        return CLIResult(exit_code=1, output=f"[ERROR] Update failed: {e}")


# ---------------------------------------------------------------------------
# Skill install command
# ---------------------------------------------------------------------------


def run_skill_install(url: str, skills_dir: Path | None = None) -> CLIResult:
    """Install a community skill from a URL."""
    skills_dir = skills_dir or Path.home() / ".kubeagent" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, tmpdir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return CLIResult(
                    exit_code=1,
                    output=f"[ERROR] git clone failed: {result.stderr}",
                )

            # Find .md files
            md_files = list(Path(tmpdir).glob("*.md"))
            if not md_files:
                return CLIResult(
                    exit_code=1,
                    output="[ERROR] No .md skill files found in repository.",
                )

            for md in md_files:
                dest = skills_dir / md.name
                shutil.copy(md, dest)

            return CLIResult(
                exit_code=0,
                output=f"Installed {len(md_files)} skill(s) from {url}",
            )
    except Exception as e:
        return CLIResult(exit_code=1, output=f"[ERROR] {e}")
