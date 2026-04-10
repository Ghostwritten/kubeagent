"""Base classes for skill definitions."""

from __future__ import annotations


class Skill:
    """A skill definition."""

    name: str
    description: str
    trigger: str  # slash command that invokes this skill
    steps: list[str]
    required_tools: list[str]

    def __init__(
        self,
        name: str = "",
        description: str = "",
        trigger: str = "",
        steps: list[str] | None = None,
        required_tools: list[str] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.trigger = trigger
        self.steps = steps or []
        self.required_tools = required_tools or []


class BuiltinSkill(Skill):
    """Base class for built-in skills that can execute logic.

    Subclasses must set class-level attributes:
        name, description, trigger, required_tools
    """

    def __init__(self) -> None:
        # Use class-level attributes as instance values
        self.name = self.name
        self.description = self.description
        self.trigger = self.trigger
        self.steps = getattr(self, "steps", [])
        self.required_tools = getattr(self, "required_tools", [])

    def execute(self, context: dict) -> str:
        """Execute the skill and return result."""
        raise NotImplementedError
