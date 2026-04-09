"""First-run setup wizard with progressive configuration."""

from __future__ import annotations

from pathlib import Path

import click
import requests

from kubeagent.config.settings import (
    CONFIG_FILE,
    ClusterConfig,
    KubeAgentConfig,
    ModelConfig,
    detect_kubeconfig,
    get_env_api_key,
    save_config,
)


def check_kubeconfig(path: str) -> tuple[bool, str | None]:
    """Check if kubeconfig exists and get current context."""
    import os

    if not os.path.exists(path):
        return False, None

    # Simple parse of kubeconfig to get current context
    # No kubernetes library yet, so minimal check
    try:
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        current_context = data.get("current-context", "")
        return True, current_context
    except Exception:
        return True, "unknown"


def check_api_key(api_key: str, provider: str) -> tuple[bool, str]:
    """Test API key validity."""
    if not api_key:
        return False, "No API key provided"

    if provider == "anthropic":
        try:
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "API key is valid"
            return False, f"Invalid API key (status {resp.status_code})"
        except requests.RequestException as e:
            return False, f"Connection failed: {e}"

    if provider == "openai":
        try:
            resp = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "API key is valid"
            return False, f"Invalid API key (status {resp.status_code})"
        except requests.RequestException as e:
            return False, f"Connection failed: {e}"

    return False, "Unknown provider"


def detect_provider(api_key: str) -> str:
    """Detect provider from API key format."""
    if api_key.startswith("sk-ant-"):
        return "anthropic"
    if api_key.startswith("sk-"):
        return "openai"
    return "unknown"


def run_wizard() -> bool:
    """Run the interactive setup wizard. Returns True if setup succeeded."""
    click.echo("\n🚀 Welcome to kubeagent!\n")

    # Step 1: Detect environment
    detected_kubeconfig = detect_kubeconfig()
    detected_api_key = get_env_api_key()
    detected_provider = detect_provider(detected_api_key) if detected_api_key else None

    # Step 2: Show status
    click.echo("Checking environment...")
    if detected_kubeconfig:
        _, ctx = check_kubeconfig(detected_kubeconfig)
        click.echo(f"[K8s]  ✅ Found kubeconfig at {detected_kubeconfig}")
        click.echo(f"        Current context: {ctx or 'none'}")
    else:
        click.echo("[K8s]  ❌ No kubeconfig found")

    if detected_api_key:
        click.echo(f"[LLM]   ✅ Found API key ({detected_provider})")
    else:
        click.echo("[LLM]   ❌ No API key found")

    click.echo()

    # Step 3: API Key configuration
    if detected_api_key:
        click.echo("✅ API key detected from environment. Using it.")
        api_key = detected_api_key
        provider = detected_provider
    else:
        click.echo("LLM configuration:")
        click.echo("  1. Anthropic (Claude) - Recommended")
        click.echo("  2. OpenAI (GPT)")
        click.echo("  3. Ollama (Local)")
        click.echo("  4. Skip for now (manual configuration)")

        choice = click.prompt("Select an option", default="4", type=int)

        if choice == 4:
            click.echo("Skipping LLM configuration. Run 'kubeagent init' to configure later.")
            click.echo()
            return False

        provider_map = {1: "anthropic", 2: "openai", 3: "ollama"}
        provider = provider_map.get(choice, "ollama")

        if provider in ("anthropic", "openai"):
            api_key = click.prompt(
                f"Enter your {provider.capitalize()} API Key",
                hide_input=True,
            )
        else:
            api_key = click.prompt(
                "Enter Ollama base URL",
                default="http://localhost:11434",
                show_default=True,
            )
            # No validation needed for Ollama in wizard

    click.echo()

    # Step 4: Validate API key (for cloud providers)
    if provider in ("anthropic", "openai"):
        click.echo("Testing API key...")
        valid, msg = check_api_key(api_key, provider)
        if valid:
            click.echo(f"[LLM]   ✅ {msg}")
        else:
            click.echo(f"[LLM]   ❌ {msg}")
            click.echo("Please check your API key and run 'kubeagent init' to retry.")
            return False
    else:
        click.echo("[LLM]   ✅ Ollama endpoint configured")

    # Step 5: Validate cluster connection (minimal)
    if detected_kubeconfig:
        click.echo("Testing cluster connection...")
        exists, _ = check_kubeconfig(detected_kubeconfig)
        if exists:
            click.echo("[K8s]   ✅ Cluster config found")
        else:
            click.echo("[K8s]   ❌ Cluster config not found")
    click.echo()

    # Step 6: Save configuration
    model_config = ModelConfig(
        default="claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o",
        api_key=api_key if provider in ("anthropic", "openai") else None,
        api_base="http://localhost:11434" if provider == "ollama" else None,
    )
    default_kubeconfig = str(Path.home() / ".kube" / "config")
    cluster_config = ClusterConfig(
        kubeconfig=detected_kubeconfig or default_kubeconfig,
    )
    config = KubeAgentConfig(model=model_config, cluster=cluster_config, initialized=True)

    save_config(config)
    click.echo(f"Configuration saved to {CONFIG_FILE}")

    click.echo()
    click.echo("✅ Setup complete! Run 'kubeagent' to get started.")

    return True


def run_doctor() -> None:
    """Run diagnostics and report status."""
    click.echo("\n🔍 KubeAgent Doctor\n")

    all_ok = True

    # Check API key
    api_key = get_env_api_key()
    if api_key:
        provider = detect_provider(api_key)
        click.echo(f"[LLM]   ✅ API key found ({provider})")

        if provider in ("anthropic", "openai"):
            valid, msg = check_api_key(api_key, provider)
            if valid:
                click.echo("[LLM]   ✅ API key is valid")
            else:
                click.echo(f"[LLM]   ❌ {msg}")
                all_ok = False
    else:
        click.echo("[LLM]   ❌ No API key found")
        click.echo("         Set KUBEAGENT_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY")
        all_ok = False

    # Check kubeconfig
    kubeconfig = detect_kubeconfig()
    if kubeconfig:
        exists, ctx = check_kubeconfig(kubeconfig)
        if exists:
            click.echo(f"[K8s]   ✅ kubeconfig found at {kubeconfig}")
            click.echo(f"[K8s]   ✅ Current context: {ctx or 'none'}")
        else:
            click.echo(f"[K8s]   ❌ kubeconfig not found at {kubeconfig}")
            all_ok = False
    else:
        click.echo("[K8s]   ❌ No kubeconfig found")
        click.echo("         Set KUBECONFIG or ensure ~/.kube/config exists")
        all_ok = False

    # Check config file
    if CONFIG_FILE.exists():
        click.echo(f"[Config] ✅ Config file at {CONFIG_FILE}")
    else:
        click.echo(f"[Config] ❌ No config file at {CONFIG_FILE}")
        click.echo("         Run 'kubeagent init' to create one")

    click.echo()
    if all_ok:
        click.echo("✅ All checks passed!")
    else:
        click.echo("⚠️  Some checks failed. Run 'kubeagent init' to fix.")
