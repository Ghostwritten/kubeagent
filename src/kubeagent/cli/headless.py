"""Headless mode — non-interactive CLI for CI/CD."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kubeagent.agent.agent import run_single_turn
from kubeagent.config.settings import KubeAgentConfig, load_config


@dataclass
class HeadlessResult:
    """Result from a headless run."""

    output: str
    exit_code: int
    format: str  # text | json | yaml


def run_headless(
    query: str,
    output_format: str = "text",
    config: KubeAgentConfig | None = None,
) -> HeadlessResult:
    """Execute a single query in headless mode and return the result.

    Args:
        query: Natural language query to execute.
        output_format: Output format - text, json, or yaml.
        config: Optional config override.

    Returns:
        HeadlessResult with output and exit code.
    """
    cfg = config or load_config()
    exit_code = 0
    output = ""

    try:
        import asyncio

        result = asyncio.run(run_single_turn(query, config=cfg))

        if output_format == "json":
            output = _format_json(result)
        elif output_format == "yaml":
            output = _format_yaml(result)
        else:
            output = result

    except Exception as e:
        exit_code = 1
        output = f"[ERROR] {e}"

    return HeadlessResult(output=output, exit_code=exit_code, format=output_format)


def run_batch(
    batch_file: Path,
    output_format: str = "text",
) -> HeadlessResult:
    """Execute multiple queries from a batch file.

    Args:
        batch_file: Path to file with one query per line.
        output_format: Output format for each result.

    Returns:
        HeadlessResult with combined output and exit_code.
    """
    if not batch_file.exists():
        return HeadlessResult(
            output=f"Batch file not found: {batch_file}",
            exit_code=1,
            format=output_format,
        )

    lines = batch_file.read_text().splitlines()
    # Strip comments and empty lines
    queries = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]

    if not queries:
        return HeadlessResult(output="", exit_code=0, format=output_format)

    results: list[str] = []
    exit_code = 0

    for i, query in enumerate(queries):
        if len(queries) > 1:
            results.append(f"--- Command {i + 1}: {query} ---")
        result = run_headless(query, output_format=output_format)
        results.append(result.output)
        if result.exit_code != 0:
            exit_code = 1

    return HeadlessResult(
        output="\n".join(results),
        exit_code=exit_code,
        format=output_format,
    )


def _format_json(text: str) -> str:
    """Wrap text output as JSON."""
    import json

    # Try to parse as structured output first
    try:
        return json.dumps({"result": text}, indent=2, ensure_ascii=False)
    except Exception:
        return json.dumps({"result": text}, ensure_ascii=False)


def _format_yaml(text: str) -> str:
    """Wrap text output as YAML."""
    try:
        import yaml

        return yaml.dump({"result": text}, default_flow_style=False, allow_unicode=True)
    except ImportError:
        return f"result: |\n  {text}"
