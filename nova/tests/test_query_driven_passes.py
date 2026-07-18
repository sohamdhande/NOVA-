import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.passes import (
    Pass, PassPipeline, PassCategory, LoweringPass, DeduplicationPass, DiagnosticsPass,
    PassCycleError, UnsatisfiedRequirementError
)
from nova.packages.kir import KIRNode
from nova.packages.passes.diagnostics import DiagnosticsContext

class FakePassA(Pass):
    category = PassCategory.ANALYSIS
    name = "FakePassA"
    requires = ["cap_B"]
    provides = ["cap_A"]
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        return kir_nodes

class FakePassB(Pass):
    category = PassCategory.ANALYSIS
    name = "FakePassB"
    requires = ["cap_A"]
    provides = ["cap_B"]
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        return kir_nodes

class FakePassUnsatisfied(Pass):
    category = PassCategory.ANALYSIS
    name = "FakePassUnsatisfied"
    requires = ["impossible_cap"]
    provides = []
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        return kir_nodes

class ZPass(Pass):
    category = PassCategory.ANALYSIS
    name = "ZPass"
    requires = []
    provides = ["cap_Z"]
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        return kir_nodes

class APass(Pass):
    category = PassCategory.ANALYSIS
    name = "APass"
    requires = []
    provides = ["cap_A"]
    def run(self, kir_nodes: List[KIRNode], diagnostics: Optional[DiagnosticsContext] = None) -> List[KIRNode]:
        return kir_nodes

def test_query_driven_passes():
    # a. Scrambled input order
    orders = [
        [LoweringPass(), DeduplicationPass(), DiagnosticsPass()],
        [DiagnosticsPass(), LoweringPass(), DeduplicationPass()],
        [DeduplicationPass(), DiagnosticsPass(), LoweringPass()]
    ]
    
    for passes in orders:
        pipeline = PassPipeline(passes)
        resolved = pipeline.resolve_order()
        names = [p.name for p in resolved]
        assert names == ["LoweringPass", "DeduplicationPass", "DiagnosticsPass"]

    # b. Determinism
    pipeline = PassPipeline([DiagnosticsPass(), LoweringPass(), DeduplicationPass()])
    first_res = [p.name for p in pipeline.resolve_order()]
    for _ in range(4):
        res = [p.name for p in pipeline.resolve_order()]
        assert res == first_res

    # c. Cycle detection
    try:
        pipeline = PassPipeline([FakePassA(), FakePassB()])
        pipeline.resolve_order()
        assert False, "Should have raised PassCycleError"
    except PassCycleError:
        pass

    # d. Unsatisfied requirement
    try:
        pipeline = PassPipeline([LoweringPass(), FakePassUnsatisfied()])
        pipeline.resolve_order()
        assert False, "Should have raised UnsatisfiedRequirementError"
    except UnsatisfiedRequirementError:
        pass

    # e. Tie-breaking stability
    # No dependencies, APass and ZPass both eligible. Alphabetical means APass then ZPass.
    pipeline1 = PassPipeline([ZPass(), APass()])
    assert [p.name for p in pipeline1.resolve_order()] == ["APass", "ZPass"]
    
    pipeline2 = PassPipeline([APass(), ZPass()])
    assert [p.name for p in pipeline2.resolve_order()] == ["APass", "ZPass"]

if __name__ == "__main__":
    print("--- Testing Query-Driven Passes ---")
    test_query_driven_passes()
    print("All Query-Driven Passes tests passed!\n")
