"""Custom exceptions for KiCad SimReady."""


class SimReadyError(Exception):
    """Base exception for all SimReady errors."""


class SchematicParseError(SimReadyError):
    """Raised when a schematic file cannot be parsed."""

    def __init__(self, message: str, *, filepath: str = "", position: int = -1):
        self.filepath = filepath
        self.position = position
        detail = f" ({filepath})" if filepath else ""
        super().__init__(f"{message}{detail}")


class SchematicNotFoundError(SimReadyError):
    """Raised when a schematic file path does not exist."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"Schematic file not found: {filepath}")


class AnalysisError(SimReadyError):
    """Raised when analysis cannot be completed."""
