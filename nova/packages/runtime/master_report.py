import hashlib
import json
from typing import Any

from datetime import datetime, timezone
from dataclasses import dataclass
from nova.packages.runtime.store import KnowledgeStore
from nova.packages.runtime.state_resolution import ResolvedNode, StateSnapshot, get_state_snapshot
from nova.packages.runtime.master_report_renderers import SECTION_RENDERERS
from tools.pdf_tool import create_pdf
import os

def hash_category_nodes(nodes: list[ResolvedNode]) -> str:
    """
    Deterministic hash of a category's current resolved nodes.
    Includes output_id, metadata, status, and superseded_by.
    Excludes temporal resolution fields (first_committed_at, last_updated_at).
    """
    canonical_list = []
    for resolved in nodes:
        canonical_list.append({
            "output_id": resolved.node.output_id,
            "metadata": resolved.node.metadata,
            "status": resolved.status,
            "superseded_by": resolved.superseded_by
        })
        
    canonical_list.sort(key=lambda x: x["output_id"])
    
    payload = json.dumps(canonical_list, sort_keys=True)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def get_changed_categories(
    store: KnowledgeStore, snapshot: StateSnapshot
) -> dict[str, bool]:
    """
    For every category in snapshot.buckets, compute hash_category_nodes()
    and compare against store.get_cached_section(category). Returns a dict
    of category -> True (needs re-render) or False (cache is valid/unchanged).
    A category with no cached entry yet always needs re-render (treat as
    changed).
    """
    changed = {}
    
    for category, nodes in snapshot.buckets.items():
        new_hash = hash_category_nodes(nodes)
        
        if hasattr(store, "get_cached_section"):
            cached = store.get_cached_section(category)
        else:
            cached = None
            
        if not cached:
            changed[category] = True
        elif cached["content_hash"] != new_hash:
            changed[category] = True
        else:
            changed[category] = False
            
    return changed

@dataclass(frozen=True)
class MasterReportResult:
    full_markdown: str
    report_hash: str
    generated_at: datetime
    sections_rerendered: list[str]
    sections_from_cache: list[str]

def update_and_render_master_report(store: KnowledgeStore) -> MasterReportResult:
    snapshot = get_state_snapshot(store)
    
    sections_order = [
        "executive_summary",
        "the_problem",
        "solution_product",
        "why_now",
        "market_opportunity",
        "business_model",
        "traction_milestones",
        "competitive_landscape",
        "go_to_market",
        "team",
        "roadmap_risks",
        "financials_ask"
    ]
    
    full_doc = []
    rerendered = []
    from_cache = []
    
    gen_time = datetime.now(timezone.utc)
    full_doc.append(f"# N.O.V.A Master Chronicle Report\nGenerated at: {gen_time.isoformat()}\n\n")
    
    for section_name in sections_order:
        renderer_func, consumed_categories = SECTION_RENDERERS[section_name]
        
        # Approach (a): Compute a composite hash of all consumed categories.
        # This is simpler and avoids mis-matches between category cache and section cache.
        cat_hashes = []
        for cat in consumed_categories:
            nodes = snapshot.buckets.get(cat, [])
            cat_hashes.append(hash_category_nodes(nodes))
            
        combined_payload = "".join(cat_hashes)
        section_hash = hashlib.sha256(combined_payload.encode('utf-8')).hexdigest()
        
        cached = store.get_cached_section(section_name) if hasattr(store, "get_cached_section") else None
        
        if cached and cached.get("content_hash") == section_hash:
            from_cache.append(section_name)
            full_doc.append(cached["rendered_markdown"])
        else:
            rerendered.append(section_name)
            rendered_markdown = renderer_func(snapshot)
            full_doc.append(rendered_markdown)
            if hasattr(store, "save_section"):
                store.save_section(section_name, section_hash, rendered_markdown)
                
        full_doc.append("\n\n---\n\n")
        
    full_markdown = "".join(full_doc)
    report_hash = hashlib.sha256(full_markdown.encode('utf-8')).hexdigest()
    
    return MasterReportResult(
        full_markdown=full_markdown,
        report_hash=report_hash,
        generated_at=gen_time,
        sections_rerendered=rerendered,
        sections_from_cache=from_cache
    )

def render_master_report_pdf(result: MasterReportResult) -> bytes:
    # create_pdf writes to a file and returns the file path as a string.
    # We generate a unique temporary-ish topic title.
    topic = f"Master Report {result.generated_at.strftime('%Y-%m-%d')}"
    filepath = create_pdf(topic=topic, content=result.full_markdown, include_takeaways=False)
    
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()
        
    # Clean up the generated file to avoid leaving artifacts
    if os.path.exists(filepath):
        os.remove(filepath)
        
    return pdf_bytes
