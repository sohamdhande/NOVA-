import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from nova.packages.kir import KIRNode
from nova.packages.observation import ObservationBundle
from nova.packages.passes import PassPipeline, LoweringPass, DeduplicationPass, DiagnosticsPass
import logging

from nova.packages.passes.diagnostics import DiagnosticsContext, Diagnostic
from nova.packages.compiler.trace import CompilerTrace
from nova.packages.compiler.verification import run_verification, VerificationReport

logger = logging.getLogger(__name__)

class CompilationError(Exception):
    pass

@dataclass(frozen=True)
class KnowledgeCommit:
    commit_hash: str
    kir_nodes: list[KIRNode]
    parent_hash: Optional[str]
    created_at: datetime
    trace: Optional[CompilerTrace] = None
    verification_report: Optional[VerificationReport] = None
    diagnostics: list[Diagnostic] = None

def compute_commit_hash(kir_nodes: list[KIRNode]) -> str:
    """
    SHA-256 over a deterministic serialization of the KIR nodes.
    Sort keys, no randomness, no timestamps inside the hash input.
    """
    serialized_nodes = []
    for node in kir_nodes:
        node_dict = {
            "op": node.op,
            "inputs": node.inputs,
            "output_id": node.output_id,
            "metadata": node.metadata,
            "dialect": node.dialect.value
            # Explicitly EXCLUDED: verification_status and verified_at
            # These are mutable review-states, not immutable assertion content.
            # They must never affect the commit_hash or parent_hash chain.
        }
        serialized_nodes.append(node_dict)
    
    serialized_nodes.sort(key=lambda x: x["output_id"])
    
    json_bytes = json.dumps(serialized_nodes, sort_keys=True).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()

from nova.packages.kir import lower_to_kir

def bundle_to_kir(bundle: ObservationBundle) -> list[KIRNode]:
    """
    Standalone pure function that converts a bundle to initial KIRNodes 
    BEFORE the pipeline starts.
    """
    nodes = []
    for obs in bundle.observations:
        node = lower_to_kir(obs)
        nodes.append(node)
    return nodes

def compile(bundle: ObservationBundle, parent_hash: Optional[str] = None, ignore_fatal: bool = False) -> KnowledgeCommit:
    """
    Builds a PassPipeline, runs it to generate KIRNodes, computes hash, 
    and returns an immutable KnowledgeCommit.
    """
    trace = CompilerTrace()
    diagnostics_ctx = DiagnosticsContext()
    
    kir_nodes_initial = bundle_to_kir(bundle)
    
    scrambled_passes = [
        DiagnosticsPass(),
        LoweringPass(),
        DeduplicationPass()
    ]
    logger.debug(f"[Compiler] Constructed pipeline with SCRAMBLED order: " + " -> ".join(p.name for p in scrambled_passes))
    
    pipeline = PassPipeline(scrambled_passes)
    
    kir_nodes = pipeline.run(kir_nodes_initial, diagnostics=diagnostics_ctx)
    
    # Verification Phase
    verification_report = run_verification(kir_nodes)
    
    trace.finish([p.name for p in pipeline.resolve_order()], verification_report, diagnostics_ctx)
    
    if (verification_report.has_fatal() or diagnostics_ctx.has_fatal()) and not ignore_fatal:
        raise CompilationError("Compilation failed due to FATAL errors.")
    
    commit_hash = compute_commit_hash(kir_nodes)
    
    return KnowledgeCommit(
        commit_hash=commit_hash,
        kir_nodes=kir_nodes,
        parent_hash=parent_hash,
        created_at=datetime.now(timezone.utc),
        trace=trace,
        verification_report=verification_report,
        diagnostics=diagnostics_ctx.get_all() if diagnostics_ctx else []
    )

__all__ = [
    "KnowledgeCommit",
    "compute_commit_hash",
    "bundle_to_kir",
    "compile"
]
