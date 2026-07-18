from abc import ABC, abstractmethod
from typing import List, Dict, Any
from nova.packages.passes.diagnostics import Diagnostic, DiagnosticSeverity
from nova.packages.kir import KIRNode

class VerificationAnalyzer(ABC):
    name: str

    @abstractmethod
    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        pass

class OntologyAnalyzer(VerificationAnalyzer):
    name = "OntologyAnalyzer"
    
    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        diagnostics = []
        for node in kir_nodes:
            if not node.metadata or "type" not in node.metadata:
                diagnostics.append(Diagnostic(
                    code="ONTOLOGY_MISSING_TYPE",
                    message="KIRNode metadata is missing 'type'.",
                    severity=DiagnosticSeverity.ERROR,
                    affected_node_id=node.output_id,
                    suggested_fix="Ensure lower_to_kir extracts type correctly."
                ))
        return diagnostics

class IdentityAnalyzer(VerificationAnalyzer):
    name = "IdentityAnalyzer"

    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        diagnostics = []
        for node in kir_nodes:
            if not node.metadata or "identity" not in node.metadata:
                diagnostics.append(Diagnostic(
                    code="IDENTITY_MISSING",
                    message="KIRNode metadata is missing 'identity'.",
                    severity=DiagnosticSeverity.ERROR,
                    affected_node_id=node.output_id,
                    suggested_fix="Ensure observation contains a valid identity hash."
                ))
        return diagnostics

class TemporalAnalyzer(VerificationAnalyzer):
    name = "TemporalAnalyzer"

    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        diagnostics = []
        # Complex temporal rules could go here
        return diagnostics

class ProvenanceAnalyzer(VerificationAnalyzer):
    name = "ProvenanceAnalyzer"

    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        diagnostics = []
        return diagnostics

class RelationshipAnalyzer(VerificationAnalyzer):
    name = "RelationshipAnalyzer"

    def analyze(self, kir_nodes: List[KIRNode]) -> List[Diagnostic]:
        diagnostics = []
        return diagnostics

class VerificationReport:
    def __init__(self, diagnostics: List[Diagnostic]):
        self.diagnostics = list(diagnostics)
        
    def has_fatal(self) -> bool:
        return any(d.severity == DiagnosticSeverity.FATAL for d in self.diagnostics)
        
    def has_error(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_diagnostics": len(self.diagnostics),
            "fatal_count": sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.FATAL),
            "error_count": sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR),
            "diagnostics": [
                {
                    "code": d.code,
                    "message": d.message,
                    "severity": d.severity.value,
                    "node": d.affected_node_id
                } for d in self.diagnostics
            ]
        }

def run_verification(kir_nodes: List[KIRNode]) -> VerificationReport:
    analyzers: List[VerificationAnalyzer] = [
        OntologyAnalyzer(),
        IdentityAnalyzer(),
        TemporalAnalyzer(),
        ProvenanceAnalyzer(),
        RelationshipAnalyzer()
    ]
    
    all_diagnostics = []
    for analyzer in analyzers:
        all_diagnostics.extend(analyzer.analyze(kir_nodes))
        
    return VerificationReport(all_diagnostics)

__all__ = [
    "VerificationAnalyzer",
    "OntologyAnalyzer",
    "IdentityAnalyzer",
    "TemporalAnalyzer",
    "ProvenanceAnalyzer",
    "RelationshipAnalyzer",
    "VerificationReport",
    "run_verification"
]
