"""
Knowledge OS API routes.
Thin APIRouter wrapping existing Knowledge OS compiler/runtime/provenance
endpoints for integration into the main NOVA API server.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Ensure the nova package is importable
_nova_root = str(Path(__file__).parent.parent)
if _nova_root not in sys.path:
    sys.path.insert(0, _nova_root)

# Eagerly import nova packages to avoid import deadlocks in FastAPI threadpool workers
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.provenance import ProvenanceGraph
from nova.packages.temporal.persistence import SQLiteTemporalIndex
from nova.packages.identity.persistence import SQLiteIdentityRegistry
from nova.packages.runtime.daily_chronicle import compute_knowledge_health, generate_daily_chronicle
from nova.packages.reasoning import compile_reasoning_context
from nova.packages.llm import get_provider, format_reasoning_prompt, REASONING_SYSTEM_PROMPT
from nova.packages.observation import build_bundle, build_multi_bundle
from nova.packages.compiler import compile as nova_compile
from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.ingestion import (
    IngestionRegistry, SlackAdapter, GitCommitAdapter, PlaintextAdapter,
    MarkdownAdapter, PDFAdapter, EmailAdapter, CalendarAdapter,
    JSONAdapter, CSVAdapter
)

router = APIRouter()

# ── Lazy singletons (reuse existing CLI helpers) ──

_store = None
_prov = None
_ingestion = None
_id = None
_temp = None


def _get_store():
    global _store
    if _store is None:
        from nova.packages.runtime.persistence import SQLiteCommitStore
        db_path = os.path.join(_nova_root, "nova", "knowledge.db")
        _store = SQLiteCommitStore(db_path)
    return _store

def _get_integrity_snapshot():
    store = _get_store()
    return getattr(store, 'integrity_snapshot', None)


def _get_prov():
    global _prov
    if _prov is None:
        from nova.packages.provenance import ProvenanceGraph
        _prov = ProvenanceGraph()
    return _prov


def _get_temp():
    global _temp
    if _temp is None:
        from nova.packages.temporal.persistence import SQLiteTemporalIndex
        db_path = os.path.join(_nova_root, "nova", "temporal.db")
        _temp = SQLiteTemporalIndex(db_path)
    return _temp


def _get_id():
    global _id
    if _id is None:
        from nova.packages.identity.persistence import SQLiteIdentityRegistry
        db_path = os.path.join(_nova_root, "nova", "identity.db")
        _id = SQLiteIdentityRegistry(db_path)
    return _id


def _format_natural_text(val: any) -> str:
    if isinstance(val, dict):
        if "title" in val and "summary" in val:
            return f"{val['title']}: {val['summary']}"
        if "topic" in val and "chosen_option" in val:
            return f"{val['topic']} (Chosen: {val['chosen_option']})"
        if "side_a" in val and "side_b" in val:
            return f"{val['side_a']} vs {val['side_b']}: {val.get('description', '')}"
        if "question" in val:
            return f"Question: {val['question']}"
        if "statement" in val:
            return f"Principle: {val['statement']}"
        
        for list_key in ["decisions", "observations", "risks", "action_items", "alternatives", "tradeoffs", "goals", "assumptions", "constraints", "questions", "principles", "notes", "items", "entities", "relationships", "market_data", "competitors", "team_members", "financial_metrics"]:
            if list_key in val and isinstance(val[list_key], list):
                lines = []
                for item in val[list_key]:
                    if isinstance(item, dict):
                        item_text = (item.get("decision") or item.get("description") or item.get("statement") or 
                                     item.get("summary") or item.get("content") or item.get("question") or 
                                     item.get("title") or item.get("name") or str(item))
                        lines.append(f"• {item_text.strip()}")
                    elif isinstance(item, str) and item.strip():
                        lines.append(f"• {item.strip()}")
                if lines:
                    return "\n".join(lines)

        for k in ["decision", "description", "content", "summary", "name", "title", "text", "statement"]:
            if k in val and isinstance(val[k], str) and val[k].strip():
                return val[k].strip()
        import json
        return json.dumps(val)
    if isinstance(val, list):
        lines = []
        for item in val:
            if isinstance(item, dict):
                item_text = (item.get("decision") or item.get("description") or item.get("statement") or 
                             item.get("summary") or item.get("content") or item.get("question") or 
                             item.get("title") or item.get("name") or str(item))
                lines.append(f"• {item_text.strip()}")
            elif isinstance(item, str) and item.strip():
                lines.append(f"• {item.strip()}")
        return "\n".join(lines) if lines else ""
    if isinstance(val, str):
        trimmed = val.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            try:
                import json
                return _format_natural_text(json.loads(trimmed))
            except Exception:
                pass
            try:
                import json, re
                repaired = re.sub(r'("")([^"]*)("")', r'"\2"', trimmed)
                return _format_natural_text(json.loads(repaired))
            except Exception:
                pass
        import re
        items = re.findall(r'\"(?:decision|goal|risk|action|principle|statement|summary|description|question)\"\s*:\s*\"([^\"]+)\"', trimmed)
        if items:
            return "\n".join(f"• {x.strip()}" for x in items if x.strip())
    return str(val if val is not None else "")


def _get_meta_fields(n):
    """Extract sender, source_path, text from a KIR node's metadata."""
    c = n.metadata.get("content")
    if isinstance(c, dict):
        target_val = c.get("content") if "content" in c and c.get("content") else c
        return c.get("sender", "unknown"), c.get("source_path", ""), _format_natural_text(target_val)
    return n.metadata.get("sender", "unknown"), n.metadata.get("source_path", ""), _format_natural_text(c if c else "")


# ── Models ──

class IngestRequest(BaseModel):
    source_type: str
    content: str


# ── Endpoints ──

@router.get("/health")
def knowledge_health():
    from nova.packages.runtime.daily_chronicle import compute_knowledge_health
    store = _get_store()
    chain = store.get_chain()
    health_data = compute_knowledge_health(store)
    return {"status": "ok", "commits": len(chain), **health_data}


@router.get("/report")
def get_chronicle_report(
    window: str = Query("today"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
):
    from nova.packages.runtime.daily_chronicle import generate_daily_chronicle
    store = _get_store()
    return generate_daily_chronicle(store, window=window, start_dt_str=start, end_dt_str=end)


@router.get("/integrity/snapshot")
def get_integrity_snapshot():
    snap = _get_integrity_snapshot()
    if not snap:
        raise HTTPException(status_code=500, detail="Integrity Snapshot not initialized")
    return snap


@router.get("/integrity/profile")
def get_integrity_profile(id: str = Query(...)):
    snap = _get_integrity_snapshot()
    if not snap:
        raise HTTPException(status_code=500, detail="Integrity Snapshot not initialized")
    profile = snap.get("profiles", {}).get(id)
    if not profile:
        raise HTTPException(status_code=404, detail="Knowledge Quality Profile not found")
    return profile


@router.get("/status")
def get_knowledge_status(filter: str = Query("")):
    snap = _get_integrity_snapshot()
    if not snap:
        raise HTTPException(status_code=500, detail="Integrity Snapshot not initialized")
    f_low = filter.lower()
    matches = []
    for pid, profile in snap.get("profiles", {}).items():
        if not f_low or profile.get("knowledge_status", "").lower() == f_low:
            matches.append(profile)
    return matches


@router.get("/entities")
def get_entities():
    store = _get_store()
    entities = set()
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, _, _ = _get_meta_fields(n)
            if sender:
                entities.add(sender)
    return [{"id": e, "name": e} for e in sorted(entities)]


@router.get("/entity/{entity_id}")
def get_entity(entity_id: str):
    store = _get_store()
    observations = []
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, _, _ = _get_meta_fields(n)
            if sender == entity_id:
                observations.append(n.output_id)
    return {"id": entity_id, "name": entity_id, "observations": observations}


@router.get("/relationships")
def get_relationships():
    store = _get_store()
    rels = []
    prev = None
    for kc in store.get_chain():
        if prev:
            rels.append({"source": prev, "target": kc.commit_hash, "relation": "follows_commit"})
        prev = kc.commit_hash
    return rels


@router.get("/artifacts")
def get_artifacts():
    store = _get_store()
    artifacts = {}
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            _, path, txt = _get_meta_fields(n)
            if path:
                artifacts[path] = {"id": path, "type": path.split("/")[0] if "/" in path else "unknown", "content": txt}
    return list(artifacts.values())


@router.get("/artifact/{artifact_id:path}")
def get_artifact(artifact_id: str):
    for a in get_artifacts():
        if a["id"] == artifact_id or artifact_id in a["id"]:
            return a
    raise HTTPException(status_code=404, detail="Artifact not found")


@router.get("/observations")
def get_observations():
    store = _get_store()
    obs = []
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            _, _, txt = _get_meta_fields(n)
            obs.append({"id": n.output_id, "op": n.op, "dialect": n.dialect.value, "content": txt})
    return obs


@router.get("/observation/{obs_id}")
def get_observation(obs_id: str):
    for o in get_observations():
        if o["id"] == obs_id:
            return o
    raise HTTPException(status_code=404, detail="Observation not found")


@router.get("/commits")
def get_commits():
    store = _get_store()
    chain = store.get_chain()
    result = []
    for kc in chain:
        node_summaries = []
        dialect = "UNKNOWN"
        op = "UNKNOWN"
        for n in kc.kir_nodes:
            _, _, txt = _get_meta_fields(n)
            if len(txt) > 40:
                txt = txt[:37] + "..."
            node_summaries.append(f"{n.dialect.value}:{n.op} '{txt}'")
            dialect = n.dialect.value
            op = n.op
        result.append({
            "hash": kc.commit_hash,
            "short_hash": kc.commit_hash[:8],
            "timestamp": kc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "dialect": dialect,
            "op": op,
            "parent": kc.parent_hash,
            "summary": " | ".join(node_summaries),
            "node_count": len(kc.kir_nodes),
        })
    return result


@router.get("/commit/{commit_id}")
def get_commit(commit_id: str):
    store = _get_store()
    for kc in store.get_chain():
        if kc.commit_hash.startswith(commit_id):
            return {
                "hash": kc.commit_hash,
                "parent": kc.parent_hash,
                "created_at": kc.created_at.isoformat(),
                "nodes": [n.output_id for n in kc.kir_nodes],
            }
    raise HTTPException(status_code=404, detail="Commit not found")


@router.get("/timeline")
def get_timeline():
    store = _get_store()
    events = []
    for kc in store.get_chain():
        events.append({
            "timestamp": kc.created_at.isoformat(),
            "type": "commit",
            "id": kc.commit_hash[:8],
            "full_id": kc.commit_hash,
            "summary": f"Compiled {len(kc.kir_nodes)} node(s)",
        })
    return sorted(events, key=lambda x: x["timestamp"])


@router.get("/search")
def search_knowledge(q: str = Query("")):
    q_low = q.lower()
    if not q_low:
        return []
    store = _get_store()
    matches = []
    for kc in store.get_chain():
        if q_low in kc.commit_hash.lower():
            matches.append({"type": "commit", "id": kc.commit_hash[:8], "full_id": kc.commit_hash, "text": kc.commit_hash})
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if q_low in n.output_id.lower() or q_low in txt.lower() or q_low in sender.lower() or q_low in path.lower():
                matches.append({"type": "observation", "id": n.output_id, "text": f"{sender}: {txt[:60]}"})
    return matches


@router.get("/lineage/{lineage_id}")
def get_decision_lineage(lineage_id: str):
    store = _get_store()
    nodes = getattr(store, "get_lineage", lambda x: [])(lineage_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Lineage not found")
        
    chain = store.get_chain()
    
    enriched = []
    for node_info in nodes:
        node_id = node_info["node_id"]
        found = None
        for kc in chain:
            for n in kc.kir_nodes:
                raw_id = n.output_id
                fact_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id
                if raw_id == node_id or fact_id == node_id:
                    found = n
                    break
            if found:
                break
        
        if found:
            enriched.append({
                "node_id": node_id,
                "occurrence_time": node_info["occurrence_time"],
                "op": found.op,
                "dialect": found.dialect.value,
                "content": found.metadata.get("content", {}),
                "metadata": found.metadata
            })
            
    return enriched


@router.get("/explore")
def explore_knowledge():
    store = _get_store()
    chain = store.get_chain()
    graph = {"artifacts": [], "observations": [], "entities": [], "commits": []}
    entities_seen = set()

    for kc in chain:
        graph["commits"].append({
            "id": kc.commit_hash,
            "short_id": kc.commit_hash[:8],
            "timestamp": kc.created_at.isoformat(),
            "adjacent_observations": [n.output_id for n in kc.kir_nodes],
        })
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            obs_id = n.output_id
            graph["observations"].append({
                "id": obs_id,
                "op": n.op,
                "dialect": n.dialect.value,
                "content": txt[:60] if len(txt) > 60 else txt,
                "adjacent_commit": kc.commit_hash[:8],
                "adjacent_artifact": path,
                "adjacent_entity": sender,
            })
            if path and path not in [a["id"] for a in graph["artifacts"]]:
                graph["artifacts"].append({"id": path, "adjacent_observation": obs_id})
            if sender not in entities_seen:
                entities_seen.add(sender)
                graph["entities"].append({"id": sender, "adjacent_observations": [obs_id]})

    return graph


@router.get("/inspect/{object_id:path}")
def inspect_object(object_id: str):
    store = _get_store()
    prov = _get_prov()
    chain = store.get_chain()

    # Check commit
    for kc in chain:
        if kc.commit_hash.startswith(object_id):
            commit_nodes = []
            for n in kc.kir_nodes:
                _, _, n_txt = _get_meta_fields(n)
                commit_nodes.append({
                    "id": n.output_id,
                    "dialect": n.dialect.value,
                    "op": n.op,
                    "summary": n_txt,
                    "evidence_span": n.metadata.get("content", {}).get("evidence_span", "") if isinstance(n.metadata.get("content"), dict) else "",
                    "confidence": n.metadata.get("content", {}).get("confidence") if isinstance(n.metadata.get("content"), dict) else None,
                    "raw_payload": n.metadata.get("content")
                })
            return {
                "object_type": "Commit",
                "id": kc.commit_hash,
                "summary": f"Knowledge Commit {kc.commit_hash[:8]}",
                "metadata": {"created_at": kc.created_at.isoformat(), "parent": kc.parent_hash},
                "relationships": [{"target": kc.parent_hash, "relation": "parent"}] if kc.parent_hash else [],
                "timeline": [{"timestamp": kc.created_at.isoformat(), "event": "commit_created"}],
                "provenance": [kc.commit_hash],
                "supporting_evidence": [n.output_id for n in kc.kir_nodes],
                "related_commits": [kc.commit_hash],
                "commit_nodes": commit_nodes,
                "sibling_nodes": []
            }

    # Check observation/fact/artifact
    for kc in chain:
        for n in kc.kir_nodes:
            sender, src_path, txt = _get_meta_fields(n)
            raw_id = n.output_id
            norm_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id

            if object_id in (raw_id, norm_id, src_path) or (src_path and object_id in src_path):
                obj_type = "Artifact" if object_id == src_path else "Observation"
                try:
                    expl = prov.explain(norm_id) if obj_type == "Observation" else [src_path]
                except Exception:
                    expl = [norm_id]
                sibling_nodes = []
                for sib in kc.kir_nodes:
                    if sib.output_id != n.output_id:
                        _, _, s_txt = _get_meta_fields(sib)
                        sibling_nodes.append({
                            "id": sib.output_id,
                            "dialect": sib.dialect.value,
                            "op": sib.op,
                            "summary": s_txt,
                            "evidence_span": sib.metadata.get("content", {}).get("evidence_span", "") if isinstance(sib.metadata.get("content"), dict) else "",
                            "confidence": sib.metadata.get("content", {}).get("confidence") if isinstance(sib.metadata.get("content"), dict) else None,
                            "raw_payload": sib.metadata.get("content")
                        })
                return {
                    "object_type": obj_type,
                    "id": raw_id,
                    "summary": f"{n.dialect.value}:{n.op} — {txt[:80]}",
                    "metadata": n.metadata,
                    "relationships": [{"target": kc.commit_hash, "relation": "compiled_into"}],
                    "timeline": [{"timestamp": kc.created_at.isoformat(), "event": "extracted"}],
                    "provenance": expl,
                    "supporting_evidence": [src_path] if src_path else [],
                    "related_commits": [kc.commit_hash],
                    "commit_nodes": [],
                    "sibling_nodes": sibling_nodes
                }

    # Fallback — Entity
    return {
        "object_type": "Entity",
        "id": object_id,
        "summary": f"Entity: {object_id}",
        "metadata": {"entity_id": object_id},
        "relationships": [],
        "timeline": [],
        "provenance": [],
        "supporting_evidence": [],
        "related_commits": [],
        "commit_nodes": [],
        "sibling_nodes": []
    }


@router.get("/reason")
def reason_knowledge(q: str = Query("")):
    if not q:
        return {"intent": "", "context": {}}
    store = _get_store()
    try:
        from nova.packages.reasoning import compile_reasoning_context
        from nova.packages.llm import get_provider, format_reasoning_prompt, REASONING_SYSTEM_PROMPT
        context = compile_reasoning_context(q, store, temporal_idx=_get_temp())
        provider = get_provider()
        prompt = format_reasoning_prompt(q, context)
        answer = provider.generate(prompt, system_prompt=REASONING_SYSTEM_PROMPT)
        return {"intent": q, "context": context, "answer": answer}
    except Exception as e:
        return {"intent": q, "context": {"notice": "No supporting facts compiled for intent.", "detail": str(e)}}


@router.get("/reason/stream")
def reason_knowledge_stream(q: str = Query("")):
    from fastapi.responses import StreamingResponse
    import json
    store = _get_store()
    try:
        from nova.packages.reasoning import compile_reasoning_context
        from nova.packages.llm import get_provider, format_reasoning_prompt, REASONING_SYSTEM_PROMPT
        context = compile_reasoning_context(q, store, temporal_idx=_get_temp())
        provider = get_provider()
        prompt = format_reasoning_prompt(q, context)
        
        def sse_generator():
            header = json.dumps({"intent": q, "context": context})
            yield f"data: {header}\n\n"
            try:
                for token in provider.stream(prompt, system_prompt=REASONING_SYSTEM_PROMPT):
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception as stream_err:
                yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(sse_generator(), media_type="text/event-stream")
    except Exception as e:
        error_msg = str(e)
        def err_gen():
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")


@router.get("/llm/health")
def get_llm_health():
    from nova.packages.llm import get_provider
    return get_provider().health()



@router.get("/explain/{fact_id}")
def explain_knowledge(fact_id: str):
    prov = _get_prov()
    original = fact_id
    if fact_id.startswith("kir_obs_"):
        fact_id = "obs_" + fact_id[len("kir_obs_"):]
    try:
        res = prov.explain(fact_id)
        chain = res if isinstance(res, list) else [res]
    except Exception:
        chain = [fact_id]
    return {"fact_id": original, "chain": chain}


class PreviewRequest(BaseModel):
    source_type: str
    content: str
    title: Optional[str] = ""


class CompileRequest(BaseModel):
    source_type: str
    content: str
    title: Optional[str] = ""
    approved_observations: Optional[list] = None
    approved_observation_ids: Optional[list] = None
class VerifyRequest(BaseModel):
    node_id: str
    new_status: str


def _parse_input(source_type: str, content: str, title: str = "") -> dict:
    import json
    import hashlib
    from nova.packages.ingestion import (
        IngestionRegistry, SlackAdapter, GitCommitAdapter, PlaintextAdapter,
        MarkdownAdapter, PDFAdapter, EmailAdapter, CalendarAdapter,
        JSONAdapter, CSVAdapter
    )
    reg = IngestionRegistry()
    reg.register(PlaintextAdapter())
    reg.register(MarkdownAdapter())
    reg.register(PDFAdapter())
    reg.register(EmailAdapter())
    reg.register(CalendarAdapter())
    reg.register(JSONAdapter())
    reg.register(CSVAdapter())
    reg.register(SlackAdapter())
    reg.register(GitCommitAdapter())

    raw_input = content
    if source_type == "json":
        try:
            raw_input = json.loads(content)
        except Exception:
            raw_input = {"sender": "json_user", "content": content, "source_path": title or "json/input"}
    elif source_type == "slack":
        try:
            raw_input = json.loads(content)
        except Exception:
            raw_input = {"channel": title or "general", "user": "slack_user", "text": content}
    elif source_type == "git":
        try:
            raw_input = json.loads(content)
        except Exception:
            raw_input = {"author": "git_author", "message": content, "sha": hashlib.sha256(content.encode()).hexdigest()[:8]}
    elif source_type == "email":
        try:
            raw_input = json.loads(content)
        except Exception:
            raw_input = {"from": "email_sender", "subject": title or "email", "body": content}

    try:
        return reg.ingest(source_type, raw_input)
    except Exception:
        return {"sender": "unknown", "content": content, "source_path": f"{source_type}/{hashlib.sha256(content.encode()).hexdigest()[:8]}"}


@router.get("/stats")
def get_home_stats():
    store = _get_store()
    chain = store.get_chain()
    entities = set()
    artifacts = set()
    obs_count = 0
    for kc in chain:
        for n in kc.kir_nodes:
            obs_count += 1
            s, p, _ = _get_meta_fields(n)
            if s: entities.add(s)
            if p: artifacts.add(p)
    return {
        "stats": {
            "commits": len(chain),
            "artifacts": len(artifacts),
            "entities": len(entities),
            "observations": obs_count,
            "compiler_status": "LOCKED (Deterministic NAS-001..011)"
        },
        "recent_commits": get_commits()[:5],
        "recent_artifacts": get_artifacts()[:5],
        "recent_entities": [{"id": e, "name": e} for e in sorted(entities)][:5],
        "recent_timeline": get_timeline()[-5:][::-1]
    }


@router.post("/preview")
def preview_artifact(req: PreviewRequest):
    import hashlib
    import json
    from nova.packages.llm import get_provider
    parsed = _parse_input(req.source_type, req.content, req.title or "")
    sender = parsed.get("sender", "unknown")
    src_path = parsed.get("source_path", f"{req.source_type}/artifact")
    txt = str(parsed.get("content", req.content))

    provider = get_provider()
    try:
        structured_ai = provider.extract_organizational_knowledge(txt, req.title or "", req.source_type)
    except Exception as e:
        structured_ai = {"entities": [], "relationships": [], "observations": [], "warnings": [str(e)], "reasoning": "Fallback extraction applied."}

    obs_list = []
    categories = {
        "observations": "OBSERVATION",
        "decisions": "DECISION",
        "assumptions": "ASSUMPTION",
        "constraints": "CONSTRAINT",
        "risks": "RISK",
        "alternatives": "ALTERNATIVE",
        "tradeoffs": "TRADEOFF",
        "goals": "GOAL",
        "action_items": "ACTION_ITEM",
        "questions": "QUESTION",
        "principles": "PRINCIPLE",
        "notes": "NOTE",
        "market_data": "MARKET_DATA",
        "competitors": "COMPETITOR",
        "team_members": "TEAM_MEMBER",
        "financial_metrics": "FINANCIAL_METRIC"
    }

    for cat_key, type_name in categories.items():
        items = structured_ai.get(cat_key, [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    item["type"] = type_name
                content_str = json.dumps(item) if isinstance(item, dict) else str(item)
                ev_span = item.get("evidence_span", "") if isinstance(item, dict) else ""
                conf = item.get("confidence") if isinstance(item, dict) else None
                obs_list.append({
                    "id": f"kir_{cat_key}_{hashlib.sha256(content_str.encode()).hexdigest()[:8]}_{i}",
                    "op": "ASSERT",
                    "dialect": "DECISION" if type_name == "DECISION" else "KNOWLEDGE",
                    "content": content_str,
                    "semantic_category": cat_key,
                    "type": type_name,
                    "evidence_span": ev_span,
                    "confidence": conf,
                    "approved": True,
                    "raw_payload": item
                })

    if not obs_list:
        obs_list.append({
            "id": f"kir_obs_{hashlib.sha256(txt.encode()).hexdigest()[:8]}",
            "op": "ASSERT",
            "dialect": "KNOWLEDGE",
            "content": txt[:300] + ("..." if len(txt) > 300 else ""),
            "semantic_category": "observations",
            "semantic_type": "OBSERVATION",
            "evidence_span": "Lines 1-5",
            "confidence": None,
            "approved": True,
            "raw_payload": {"content": txt[:300]}
        })

    ent_list = []
    for e in structured_ai.get("entities", []):
        if isinstance(e, dict):
            new_alias = e.get("name", sender)
            ent_list.append({"id": e.get("id", sender), "name": new_alias, "evidence_span": e.get("evidence_span", ""), "confidence": e.get("confidence"), "approved": True})
            
            # Log LLM suggestion to merge table if applicable
            id_reg = _get_id()
            canon = id_reg.lookup_by_alias(new_alias)
            if canon is None:
                # Need to run fuzzy check ourselves, or we can just run the full resolution
                # But resolve() will automatically log a suggestion if 0.6 <= ratio < 0.92!
                # Wait, resolve() is called when the bundle is built, but that's only for the 'sender' of the artifact right now.
                # What about the extracted entities? They aren't resolved into the registry automatically unless they are linked.
                # Let's run a manual fuzzy check here for LLM entities.
                cursor = id_reg._conn.cursor()
                cursor.execute("SELECT canonical_id, known_aliases_json FROM entities WHERE merged_into IS NULL")
                import difflib
                norm_new = id_reg._normalize(new_alias)
                for row in cursor.fetchall():
                    c_id = row["canonical_id"]
                    for known in json.loads(row["known_aliases_json"]):
                        ratio = difflib.SequenceMatcher(None, norm_new, id_reg._normalize(known)).ratio()
                        if 0.6 <= ratio < 0.92:
                            cursor.execute("SELECT 1 FROM merge_suggestions WHERE new_alias = ? AND suggested_canonical_id = ? AND status = 'dismissed'", (new_alias, c_id))
                            if not cursor.fetchone():
                                import uuid
                                from datetime import datetime
                                id_reg._conn.execute(
                                    "INSERT INTO merge_suggestions (id, new_alias, suggested_canonical_id, ratio, source, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (str(uuid.uuid4()), new_alias, c_id, ratio, "llm", "pending", datetime.now().isoformat())
                                )
                                id_reg._conn.commit()
                            break # Move to next entity

    if not ent_list:
        ent_list = [{"id": sender, "name": sender, "evidence_span": "Header", "confidence": None, "approved": True}]

    rel_list = []
    for r in structured_ai.get("relationships", []):
        if isinstance(r, dict):
            rel_list.append({"source": r.get("source", sender), "target": r.get("target", src_path), "relation": r.get("relation", "authored"), "evidence_span": r.get("evidence_span", ""), "confidence": r.get("confidence"), "approved": True})
    if not rel_list:
        rel_list = [{"source": sender, "target": src_path, "relation": "authored", "evidence_span": "Header", "confidence": None, "approved": True}]

    diagnostics = [{"level": "INFO", "message": f"Orchestrated extraction confidence: {structured_ai.get('confidence', 0.95)}"}]
    if structured_ai.get("reasoning"):
        diagnostics.append({"level": "INFO", "message": f"AI Rationale: {structured_ai['reasoning']}"})

    import re
    group_to_categories = {
        "org_struct": ["entities", "relationships", "observations", "team_members"],
        "decision_intel": ["decisions", "alternatives", "tradeoffs", "assumptions", "notes"],
        "exec_intel": ["goals", "action_items", "constraints", "risks"],
        "know_intel": ["questions", "principles", "market_data", "competitors", "financial_metrics"],
    }
    failed_groups = []
    failed_categories = []
    partial_extraction = False
    
    for w in structured_ai.get("warnings", []):
        if "[SKIPPED]" in w:
            partial_extraction = True
            m = re.search(r"Prompt (\w+) failed", w)
            if m:
                g = m.group(1)
                if g not in failed_groups:
                    failed_groups.append(g)
                    failed_categories.extend(group_to_categories.get(g, []))

    return {
        "observations": obs_list,
        "suggested_entities": ent_list,
        "suggested_relationships": rel_list,
        "diagnostics": diagnostics,
        "warnings": structured_ai.get("warnings", []),
        "partial_extraction": partial_extraction,
        "failed_groups": failed_groups,
        "failed_categories": failed_categories
    }


class RetryPreviewRequest(BaseModel):
    source_type: str
    content: str
    title: Optional[str] = ""
    retry_groups: list[str]


@router.post("/preview/retry")
def retry_preview(req: RetryPreviewRequest):
    import hashlib
    import json
    from nova.packages.llm import get_provider
    parsed = _parse_input(req.source_type, req.content, req.title or "")
    sender = parsed.get("sender", "unknown")
    src_path = parsed.get("source_path", f"{req.source_type}/artifact")
    txt = str(parsed.get("content", req.content))

    provider = get_provider()
    try:
        structured_ai = provider.extract_organizational_knowledge(
            txt[:1500], req.title or "", req.source_type, groups=req.retry_groups
        )
    except Exception as e:
        structured_ai = {"warnings": [str(e)]}

    obs_list = []
    categories = {
        "observations": "OBSERVATION",
        "decisions": "DECISION",
        "assumptions": "ASSUMPTION",
        "constraints": "CONSTRAINT",
        "risks": "RISK",
        "alternatives": "ALTERNATIVE",
        "tradeoffs": "TRADEOFF",
        "goals": "GOAL",
        "action_items": "ACTION_ITEM",
        "questions": "QUESTION",
        "principles": "PRINCIPLE",
        "notes": "NOTE",
        "market_data": "MARKET_DATA",
        "competitors": "COMPETITOR",
        "team_members": "TEAM_MEMBER",
        "financial_metrics": "FINANCIAL_METRIC"
    }

    for cat_key, type_name in categories.items():
        items = structured_ai.get(cat_key, [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    item["type"] = type_name
                content_str = json.dumps(item) if isinstance(item, dict) else str(item)
                ev_span = item.get("evidence_span", "") if isinstance(item, dict) else ""
                conf = item.get("confidence") if isinstance(item, dict) else None
                obs_list.append({
                    "id": f"kir_{cat_key}_{hashlib.sha256(content_str.encode()).hexdigest()[:8]}_{i}",
                    "op": "ASSERT",
                    "dialect": "DECISION" if type_name == "DECISION" else "KNOWLEDGE",
                    "content": content_str,
                    "semantic_category": cat_key,
                    "type": type_name,
                    "evidence_span": ev_span,
                    "confidence": conf,
                    "approved": True,
                    "raw_payload": item
                })

    ent_list = []
    for e in structured_ai.get("entities", []):
        if isinstance(e, dict):
            new_alias = e.get("name", sender)
            ent_list.append({"id": e.get("id", sender), "name": new_alias, "evidence_span": e.get("evidence_span", ""), "confidence": e.get("confidence"), "approved": True})
            
    rel_list = []
    for r in structured_ai.get("relationships", []):
        if isinstance(r, dict):
            rel_list.append({"source": r.get("source", sender), "target": r.get("target", src_path), "relation": r.get("relation", "authored"), "evidence_span": r.get("evidence_span", ""), "confidence": r.get("confidence"), "approved": True})

    return {
        "observations": obs_list,
        "suggested_entities": ent_list,
        "suggested_relationships": rel_list,
        "warnings": structured_ai.get("warnings", [])
    }


@router.post("/compile")
def compile_artifact(req: CompileRequest):

    from nova.packages.observation import build_bundle, build_multi_bundle
    from nova.packages.compiler import compile as nova_compile
    from nova.packages.identity import IdentityRegistry
    from nova.packages.temporal import TemporalIndex

    parsed = _parse_input(req.source_type, req.content, req.title or "")
    id_reg = _get_id()
    temp_idx = _get_temp()
    prov = _get_prov()
    store = _get_store()

    if hasattr(req, "approved_observations") and req.approved_observations:
        bundle = build_multi_bundle(req.approved_observations, id_reg, temp_idx, prov)
    else:
        bundle = build_bundle(parsed, id_reg, temp_idx, prov)

    commit = nova_compile(bundle)
    store.commit(commit)

    fact_id = commit.kir_nodes[0].output_id if commit.kir_nodes else None
    return {
        "status": "success",
        "commit_hash": commit.commit_hash,
        "fact_id": fact_id,
        "dialect": commit.kir_nodes[0].dialect.value if commit.kir_nodes else None,
        "op": commit.kir_nodes[0].op if commit.kir_nodes else None,
    }

@router.post("/verify")
def verify_node(req: VerifyRequest):
    if req.new_status not in ["unverified", "acknowledged", "verified"]:
        raise HTTPException(status_code=400, detail="Invalid verification status")
    
    store = _get_store()
    conn = store._conn
    
    verified_at = datetime.now(timezone.utc).isoformat() if req.new_status == "verified" else None
    
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO node_review_state (node_id, verification_status, verified_at) VALUES (?, ?, ?)",
            (req.node_id, req.new_status, verified_at)
        )
    return {"status": "success"}


@router.get("/export")
def export_knowledge():
    store = _get_store()
    chain = store.get_chain()
    res = []
    for kc in chain:
        res.append({
            "commit_hash": kc.commit_hash,
            "created_at": kc.created_at.isoformat(),
            "nodes": [{"id": n.output_id, "op": n.op, "dialect": n.dialect.value, "metadata": n.metadata} for n in kc.kir_nodes]
        })
    return res


@router.post("/reset")
def reset_knowledge():
    global _store, _prov, _id, _temp
    for db_name in ["knowledge.db", "temporal.db", "identity.db"]:
        db_path = os.path.abspath(os.path.join(_nova_root, "nova", db_name))
        
        # HARD SAFETY GUARD
        if db_path.endswith(os.path.join("nova", "knowledge.db")):
            raise RuntimeError(
                "CRITICAL SAFETY GUARD: Refusing to reset the production knowledge database. "
                "Use an isolated test database instead. This operation permanently destroys real user data."
            )
            
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
    _store = None
    _prov = None
    _id = None
    _temp = None
    return {"status": "ok", "message": "Local knowledge commit store reset to genesis."}


@router.post("/ingest")
def ingest_knowledge(req: IngestRequest):
    from nova.packages.observation import build_bundle
    from nova.packages.compiler import compile as nova_compile
    from nova.packages.identity import IdentityRegistry
    from nova.packages.temporal import TemporalIndex

    parsed = _parse_input(req.source_type, req.content)
    id_reg = _get_id()
    temp_idx = _get_temp()
    prov = _get_prov()
    store = _get_store()

    bundle = build_bundle(parsed, id_reg, temp_idx, prov)
    commit = nova_compile(bundle)
    store.commit(commit)

    fact_id = commit.kir_nodes[0].output_id if commit.kir_nodes else None
    return {
        "commit_hash": commit.commit_hash,
        "fact_id": fact_id,
        "dialect": commit.kir_nodes[0].dialect.value if commit.kir_nodes else None,
        "op": commit.kir_nodes[0].op if commit.kir_nodes else None,
    }

@router.get("/api/identity/suggestions")
def get_identity_suggestions():
    store = _get_store()
    reg = _get_id()
    cursor = reg._conn.cursor()
    cursor.execute("SELECT * FROM merge_suggestions WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(row) for row in cursor.fetchall()]

@router.post("/api/identity/suggestions/{id}/confirm")
def confirm_suggestion(id: str):
    store = _get_store()
    reg = _get_id()
    with reg._conn:
        cursor = reg._conn.cursor()
        cursor.execute("SELECT new_alias, suggested_canonical_id FROM merge_suggestions WHERE id = ?", (id,))
        row = cursor.fetchone()
        if row:
            reg.add_alias(row["suggested_canonical_id"], row["new_alias"])
            cursor.execute("UPDATE merge_suggestions SET status = 'confirmed' WHERE id = ?", (id,))
    return {"status": "success"}

@router.post("/api/identity/suggestions/{id}/dismiss")
def dismiss_suggestion(id: str):
    store = _get_store()
    reg = _get_id()
    with reg._conn:
        reg._conn.execute("UPDATE merge_suggestions SET status = 'dismissed' WHERE id = ?", (id,))
    return {"status": "success"}


@router.get("/master-report/status")
def get_master_report_status():
    from nova.packages.runtime.master_report import update_and_render_master_report
    store = _get_store()
    try:
        res = update_and_render_master_report(store)
        return {
            "report_hash": res.report_hash,
            "generated_at": res.generated_at.isoformat(),
            "sections_rerendered": res.sections_rerendered,
            "sections_from_cache": res.sections_from_cache
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/master-report")
def get_master_report_pdf():
    from fastapi.responses import Response
    from nova.packages.runtime.master_report import update_and_render_master_report, render_master_report_pdf
    store = _get_store()
    try:
        res = update_and_render_master_report(store)
        pdf_bytes = render_master_report_pdf(res)
        filename = f"master-report-{res.generated_at.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
