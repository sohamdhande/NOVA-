import pytest
import os
import fitz
from tools.pdf_tool import _extract_takeaways, create_pdf

def test_extract_takeaways_prose_working_case():
    """Confirm the original intended use case (prose) works correctly and extracts sentences."""
    prose = (
        "This is a standard document intended for reading. It contains multiple sentences describing how a system works! "
        "The system connects various components together. It is extremely important that this document is summarized correctly. "
        "We want the takeaways to highlight the key points. Therefore, sentence splitting is the right approach here."
    )
    takeaways = _extract_takeaways(prose, count=3)
    
    assert len(takeaways) > 0, "Should extract takeaways from normal prose"
    assert "This is a standard document intended for reading" in takeaways[0]
    
    # Ensure none are excessively long
    for t in takeaways:
        assert len(t) < 300, "Takeaways should be individual sentences, not the whole block"

def test_extract_takeaways_markdown_fallback():
    """Confirm heavily structured markdown gracefully falls back to empty takeaways instead of verbatim dumping."""
    markdown = """
# N.O.V.A Master Chronicle Report
Generated at: 2026-07-17T09:14:45.680682+00:00

## Executive Summary
* Goal Description

## The Problem
### Assumptions
* None

## Solution & Product
### Decisions
* **Test Decision**: Decision Summary
"""
    takeaways = _extract_takeaways(markdown)
    assert takeaways == [], "Structured markdown with many headers should return empty takeaways to avoid garbage duplication"

def test_pdf_generation_skips_takeaways(tmp_path):
    """Confirm the create_pdf function correctly respects include_takeaways=False."""
    markdown = "## Section 1\nContent here.\n## Section 2\nMore content."
    
    # Override DOCS_DIR temporarily by patching it, or just generate and clean up
    # create_pdf writes to DOCS_DIR. We'll let it write and read it back.
    pdf_path = create_pdf("Test Report", markdown, include_takeaways=False)
    
    try:
        assert os.path.exists(pdf_path)
        
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        
        assert "Key Takeaways" not in full_text, "Takeaways section should be skipped"
        assert "Section 1" in full_text
        
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
