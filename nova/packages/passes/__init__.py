from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Iterable, Optional
from nova.packages.kir import KIRNode
from nova.packages.observation import ObservationBundle
from nova.packages.passes.diagnostics import DiagnosticsContext, Diagnostic, DiagnosticSeverity
import logging

logger = logging.getLogger(__name__)
class PassCategory(Enum):
    ANALYSIS = "ANALYSIS"
    TRANSFORMATION = "TRANSFORMATION"
    OPTIMIZATION = "OPTIMIZATION"
    VERIFICATION = "VERIFICATION"
    LOWERING = "LOWERING"
    DIAGNOSTICS = "DIAGNOSTICS"

class PassValidationError(Exception):
    pass

class PassCycleError(Exception):
    pass

class UnsatisfiedRequirementError(Exception):
    pass

class Pass(ABC):
    category: PassCategory
    name: str
    requires: List[str] = []
    provides: List[str] = []
    version: str = "1.0.0"
    preserved_analyses: List[str] = []

    @abstractmethod
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        pass

class LoweringPass(Pass):
    category = PassCategory.LOWERING
    name = "LoweringPass"
    requires = []
    provides = ["lowered"]

    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        # Placeholder for future lowering logic, currently a pure no-op
        return list(kir_nodes)

class DiagnosticsPass(Pass):
    category = PassCategory.DIAGNOSTICS
    name = "DiagnosticsPass"
    requires = ["lowered", "deduplicated"]
    provides = ["validated"]

    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        for node in kir_nodes:
            if not node.output_id:
                if diagnostics:
                    diagnostics.emit(Diagnostic(
                        code="MISSING_OUTPUT_ID",
                        message=f"KIRNode missing output_id: {node}",
                        severity=DiagnosticSeverity.FATAL
                    ))
                else:
                    raise PassValidationError(f"KIRNode missing output_id: {node}")
            if not node.metadata:
                if diagnostics:
                    diagnostics.emit(Diagnostic(
                        code="MISSING_METADATA",
                        message=f"KIRNode missing metadata: {node}",
                        severity=DiagnosticSeverity.FATAL
                    ))
                else:
                    raise PassValidationError(f"KIRNode missing metadata: {node}")
        # Does not modify nodes
        return list(kir_nodes)

class DeduplicationPass(Pass):
    category = PassCategory.OPTIMIZATION
    name = "DeduplicationPass"
    requires = ["lowered"]
    provides = ["deduplicated"]

    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        seen = set()
        result = []
        for node in kir_nodes:
            if node.output_id not in seen:
                seen.add(node.output_id)
                result.append(node)
        return result

class PassPipeline:
    def __init__(self, passes: Iterable[Pass]):
        self.passes = list(passes)

    def resolve_order(self) -> List[Pass]:
        pending = list(self.passes)
        resolved = []
        satisfied = set()
        
        all_provides = set()
        for p in self.passes:
            all_provides.update(p.provides)
            
        for p in self.passes:
            for req in p.requires:
                if req not in all_provides and req not in satisfied:
                    raise UnsatisfiedRequirementError(f"Pass {p.name} requires '{req}' which is never provided.")
                    
        while pending:
            eligible = [p for p in pending if all(req in satisfied for req in p.requires)]
            if not eligible:
                raise PassCycleError("Cycle detected among passes: " + ", ".join(p.name for p in pending))
                
            eligible.sort(key=lambda p: p.name)
            chosen = eligible[0]
            pending.remove(chosen)
            resolved.append(chosen)
            satisfied.update(chosen.provides)
            
        return resolved

    def run(self, kir_nodes: List[KIRNode], diagnostics: getattr(sys, 'modules', {}).get('typing', __import__('typing')).Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        ordered_passes = self.resolve_order()
        
        order_names = " -> ".join(p.name for p in ordered_passes)
        logger.debug(f"[PassPipeline] Resolved order: {order_names}")
        
        current_nodes = list(kir_nodes)
        for p in ordered_passes:
            in_count = len(current_nodes)
            current_nodes = p.run(current_nodes, diagnostics=diagnostics)
            out_count = len(current_nodes)
            logger.debug(f"[PassPipeline] Ran {p.name} ({p.category.value}): {in_count} in -> {out_count} out")
        return current_nodes

__all__ = [
    "PassCategory",
    "PassValidationError",
    "PassCycleError",
    "UnsatisfiedRequirementError",
    "Pass",
    "LoweringPass",
    "DiagnosticsPass",
    "DeduplicationPass",
    "PassPipeline"
]
