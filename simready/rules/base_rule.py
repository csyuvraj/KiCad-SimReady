"""Base class for simulation readiness rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from simready.core.models import CheckResult, Schematic


class BaseRule(ABC):
    """Abstract base class for schematic validation rules."""

    name: str = "BaseRule"
    description: str = ""

    @abstractmethod
    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Run the rule against a schematic and return results."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
