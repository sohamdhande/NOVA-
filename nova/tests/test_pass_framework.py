import sys
from pathlib import Path

# Add project root to sys.path to resolve 'nova'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.kir import KIRNode
from nova.packages.passes import (
    PassPipeline, 
    LoweringPass,
    DiagnosticsPass, 
    DeduplicationPass, 
    PassValidationError
)

def test_determinism():
    nodes = [
        KIRNode(op="TEST", inputs=[], output_id="node_1", metadata={"key": "val"}),
        KIRNode(op="TEST", inputs=[], output_id="node_2", metadata={"key": "val"}),
    ]
    pipeline = PassPipeline([LoweringPass(), DeduplicationPass(), DiagnosticsPass()])
    
    res1 = pipeline.run(nodes)
    res2 = pipeline.run(nodes)
    
    assert res1 == res2, "PassPipeline is non-deterministic"
    print("PassPipeline determinism test passed.")

def test_diagnostics_pass():
    bad_node_1 = KIRNode(op="TEST", inputs=[], output_id="", metadata={"key": "val"})
    bad_node_2 = KIRNode(op="TEST", inputs=[], output_id="node_1", metadata={})
    good_node = KIRNode(op="TEST", inputs=[], output_id="node_1", metadata={"key": "val"})
    
    diag_pass = DiagnosticsPass()
    
    # Missing output_id
    try:
        diag_pass.run([bad_node_1])
        assert False, "Expected PassValidationError for missing output_id"
    except PassValidationError as e:
        print(f"Caught expected error (missing output_id): {e}")
        
    # Missing metadata
    try:
        diag_pass.run([bad_node_2])
        assert False, "Expected PassValidationError for missing metadata"
    except PassValidationError as e:
        print(f"Caught expected error (missing metadata): {e}")
        
    # Good node
    res = diag_pass.run([good_node])
    assert len(res) == 1, "DiagnosticsPass should return the nodes unchanged"
    print("DiagnosticsPass test passed.")

def test_deduplication_pass():
    nodes = [
        KIRNode(op="TEST", inputs=[], output_id="node_1", metadata={"version": 1}),
        KIRNode(op="TEST", inputs=[], output_id="node_1", metadata={"version": 2}), # duplicate
        KIRNode(op="TEST", inputs=[], output_id="node_2", metadata={"version": 1}),
    ]
    
    dedup_pass = DeduplicationPass()
    res = dedup_pass.run(nodes)
    
    assert len(res) == 2, "DeduplicationPass failed to remove duplicate"
    assert res[0].metadata["version"] == 1, "DeduplicationPass didn't keep the first occurrence"
    assert res[1].output_id == "node_2", "DeduplicationPass removed wrong node"
    
    print("DeduplicationPass test passed.")

if __name__ == "__main__":
    print("--- Testing Pass Framework ---")
    test_determinism()
    test_diagnostics_pass()
    test_deduplication_pass()
    print("All Pass Framework tests passed!\n")
