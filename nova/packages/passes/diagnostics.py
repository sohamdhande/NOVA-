from enum import Enum
from dataclasses import dataclass
from typing import Optional

class DiagnosticSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"

@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: DiagnosticSeverity
    affected_node_id: Optional[str] = None
    provenance_ref: Optional[str] = None
    suggested_fix: Optional[str] = None

class DiagnosticsContext:
    def __init__(self):
        self._diagnostics: list[Diagnostic] = []

    def emit(self, diagnostic: Diagnostic) -> None:
        self._diagnostics.append(diagnostic)

    def get_all(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    def get_by_severity(self, severity: DiagnosticSeverity) -> list[Diagnostic]:
        return [d for d in self._diagnostics if d.severity == severity]

    def has_fatal(self) -> bool:
        return any(d.severity == DiagnosticSeverity.FATAL for d in self._diagnostics)

__all__ = [
    "DiagnosticSeverity",
    "Diagnostic",
    "DiagnosticsContext"
]
