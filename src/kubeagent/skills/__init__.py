"""Skill system for KubeAgent."""

from kubeagent.skills.base import BuiltinSkill, Skill
from kubeagent.skills.registry import SkillRegistry

__all__ = ["Skill", "BuiltinSkill", "SkillRegistry"]
