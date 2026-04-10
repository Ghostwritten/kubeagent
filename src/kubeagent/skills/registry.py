"""Skill registry — loads and manages all available skills."""

from __future__ import annotations

from dataclasses import dataclass, field

from kubeagent.skills.base import BuiltinSkill, Skill
from kubeagent.skills.builtin.deploy import DeploySkill
from kubeagent.skills.builtin.diagnose import DiagnoseSkill
from kubeagent.skills.builtin.rollback import RollbackSkill
from kubeagent.skills.builtin.security_audit import SecurityAuditSkill
from kubeagent.skills.loader import load_user_skill, load_user_skills_dir


@dataclass
class SkillRegistry:
    """Registry of all available skills (built-in + user-defined)."""

    _skills: dict[str, Skill] = field(default_factory=dict)
    _user_skills_loaded: bool = False

    def __post_init__(self) -> None:
        self._load_builtin_skills()
        self._load_user_skills()

    def _load_builtin_skills(self) -> None:
        """Load all built-in skills."""
        builtins: list[BuiltinSkill] = [
            DiagnoseSkill(),
            DeploySkill(),
            RollbackSkill(),
            SecurityAuditSkill(),
        ]
        for skill in builtins:
            self._skills[skill.name] = skill

    def _load_user_skills(self) -> None:
        """Load skills from ~/.kubeagent/skills/."""
        if self._user_skills_loaded:
            return
        self._user_skills_loaded = True


        skills_dir = load_user_skills_dir()
        if skills_dir is None:
            return

        try:
            for skill_file in skills_dir.glob("*.md"):
                skill = load_user_skill(skill_file)
                if skill is not None:
                    self._skills[skill.name] = skill
        except Exception:
            pass  # Silently skip invalid user skills

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """List all available skill names."""
        return sorted(self._skills.keys())

    def reload_user_skills(self) -> None:
        """Force reload of user skills (e.g., after installing new skill)."""
        self._user_skills_loaded = False
        self._load_user_skills()
