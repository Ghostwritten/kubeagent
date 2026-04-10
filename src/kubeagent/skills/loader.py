"""Skill loader — loads user-defined skills from disk."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from kubeagent.skills.base import Skill

_USER_SKILLS_DIR = Path.home() / ".kubeagent" / "skills"


def load_user_skills_dir() -> Path | None:
    """Return the user skills directory, creating it if needed."""
    if _USER_SKILLS_DIR.exists():
        return _USER_SKILLS_DIR
    return None


def load_user_skill(path: Path) -> Skill | None:
    """Load a single skill from a markdown file.

    Format:
        ---
        name: skill-name
        description: What this skill does
        trigger: /skill-name
        required_tools:
          - get_pods
          - get_events
        ---
        # Steps
        1. Step one description
        2. Step two description
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        if not validate_skill_markdown(content):
            return None

        skill = _parse_skill_content(content)
        return skill
    except Exception:
        return None


def validate_skill_markdown(content: str) -> bool:
    """Validate that a markdown skill has required frontmatter fields."""
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        return False

    try:
        data = yaml.safe_load(frontmatter_match.group(1))
        if not isinstance(data, dict):
            return False
        required = ["name", "description", "trigger"]
        return all(data.get(field) for field in required)
    except Exception:
        return False


def _parse_skill_content(content: str) -> Skill:
    """Parse skill content into a Skill object."""
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n*(.*)", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError("Missing frontmatter")

    data = yaml.safe_load(frontmatter_match.group(1))
    body = frontmatter_match.group(2).strip()

    # Extract steps from body (numbered lists)
    steps: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and (stripped[0].isdigit() or stripped.startswith("-")):
            step = stripped.lstrip("0123456789.-) ").strip()
            if step:
                steps.append(step)

    return Skill(
        name=data.get("name", "unknown"),
        description=data.get("description", ""),
        trigger=data.get("trigger", f"/{data.get('name', 'unknown')}"),
        steps=steps,
        required_tools=data.get("required_tools", []),
    )
