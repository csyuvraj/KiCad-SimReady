"""Base class for simulation readiness rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from simready.core.models import CheckResult, Schematic


class BaseRule(ABC):
    """Abstract base class for schematic validation rules.
    
    All simulation readiness rules must inherit from this class and implement
    the check() method. Rules operate independently and report their findings
    as CheckResult objects.
    
    Attributes:
        name: Human-readable rule name (e.g., "SpiceModelRule").
        description: Detailed description of what the rule checks.
        
    Example:
        >>> class MyRule(BaseRule):
        ...     name = "MyRule"
        ...     description = "Checks for something specific"
        ...     
        ...     def check(self, schematic: Schematic) -> list[CheckResult]:
        ...         results = []
        ...         for component in schematic.components:
        ...             # Perform check logic
        ...             pass
        ...         return results
    """

    name: str = "BaseRule"
    description: str = ""

    @abstractmethod
    def check(self, schematic: Schematic) -> list[CheckResult]:
        """Run the rule against a schematic and return results.
        
        This method must be implemented by all rule subclasses.
        
        Args:
            schematic: Schematic object to analyze.
            
        Returns:
            List of CheckResult objects, one or more per check performed.
            The list may be empty if no issues are found and the rule
            doesn't report per-item results.
        """
        ...

    def __repr__(self) -> str:
        """Return string representation of the rule.
        
        Returns:
            String like "SpiceModelRule(name='SpiceModelRule')".
        """
        return f"{self.__class__.__name__}(name={self.name!r})"
