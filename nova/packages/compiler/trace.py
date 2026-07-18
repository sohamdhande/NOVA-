from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any

@dataclass
class CompilerTrace:
    compilation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    compiler_version: str = "1.0.0"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = None
    passes_executed: List[str] = field(default_factory=list)
    verification_summary: Dict[str, Any] = field(default_factory=dict)
    diagnostics_summary: Dict[str, Any] = field(default_factory=dict)

    def finish(self, passes: List[str], verification_report: Any, diagnostics_ctx: Any) -> None:
        self.finished_at = datetime.now(timezone.utc)
        self.passes_executed = list(passes)
        
        if verification_report:
            self.verification_summary = verification_report.to_dict()
            
        if diagnostics_ctx:
            diags = diagnostics_ctx.get_all()
            self.diagnostics_summary = {
                "total": len(diags),
                "fatals": sum(1 for d in diags if d.severity.value == "FATAL"),
                "errors": sum(1 for d in diags if d.severity.value == "ERROR"),
                "warnings": sum(1 for d in diags if d.severity.value == "WARNING"),
                "infos": sum(1 for d in diags if d.severity.value == "INFO")
            }

__all__ = [
    "CompilerTrace"
]
