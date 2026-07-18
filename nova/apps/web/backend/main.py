from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from nova.packages.observation import build_bundle
from nova.packages.compiler import compile
from nova.packages.cli.main import get_store, get_identity, get_temporal, get_provenance, get_dependency, setup_ingestion
from nova.packages.reasoning import compile_reasoning_context

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    source_type: str
    content: str

class AskRequest(BaseModel):
    intent: str

def _get_meta_fields(n):
    c = n.metadata.get("content")
    if isinstance(c, dict):
        return c.get("sender", "unknown"), c.get("source_path", ""), str(c.get("content", ""))
    return n.metadata.get("sender", "unknown"), n.metadata.get("source_path", ""), str(c if c else "")

@app.post("/ingest")
def ingest_endpoint(req: IngestRequest):
    registry = setup_ingestion()
    try:
        parsed = registry.ingest(req.source_type, req.content)
        if req.source_type == "plaintext" and parsed.get("sender") == "unknown":
            parsed["sender"] = f"unknown_{parsed.get('source_path', 'unknown').split('/')[-1]}"
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    id_reg = get_identity()
    temp_idx = get_temporal()
    prov_graph = get_provenance()
    
    store = get_store(None)
    latest = store.get_latest()
    derived_from_ids = None
    if latest and latest.kir_nodes:
        raw_output_id = latest.kir_nodes[0].output_id
        if raw_output_id.startswith("kir_obs_"):
            prev_fact_id = "obs_" + raw_output_id[len("kir_obs_"):]
        else:
            prev_fact_id = raw_output_id
        derived_from_ids = [(prev_fact_id, "follows")]
        
    bundle = build_bundle(parsed, id_reg, temp_idx, prov_graph, derived_from_ids=derived_from_ids)
    commit = compile(bundle)
    store.commit(commit)
    
    fact_id = commit.kir_nodes[0].output_id if commit.kir_nodes else None
    op = commit.kir_nodes[0].op if commit.kir_nodes else None
    dialect = commit.kir_nodes[0].dialect.value if commit.kir_nodes else None
    
    return {
        "commit_hash": commit.commit_hash,
        "dialect": dialect,
        "op": op,
        "fact_id": fact_id
    }

@app.get("/log")
@app.get("/commits")
def commits_endpoint():
    store = get_store(None)
    chain = store.get_chain()
    
    result = []
    for kc in chain:
        short_hash = kc.commit_hash[:8]
        ts = kc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        node_summaries = []
        dialect = "UNKNOWN"
        op = "UNKNOWN"
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if len(txt) > 40:
                txt = txt[:37] + "..."
            node_summaries.append(f"{n.dialect.value}:{n.op} '{txt}'")
            dialect = n.dialect.value
            op = n.op
            
        summary = " | ".join(node_summaries)
        result.append({
            "hash": kc.commit_hash,
            "short_hash": short_hash,
            "timestamp": ts,
            "dialect": dialect,
            "op": op,
            "summary": summary
        })
    return result

@app.get("/commit/{id}")
def commit_endpoint(id: str):
    store = get_store(None)
    for kc in store.get_chain():
        if kc.commit_hash.startswith(id):
            return {"hash": kc.commit_hash, "parent": kc.parent_hash, "created_at": kc.created_at.isoformat(), "nodes": [n.output_id for n in kc.kir_nodes]}
    raise HTTPException(status_code=404, detail="Commit not found")

@app.get("/entities")
def entities_endpoint():
    store = get_store(None)
    entities = set()
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if sender:
                entities.add(sender)
    return [{"id": e, "name": e} for e in sorted(entities)]

@app.get("/entity/{id}")
def entity_endpoint(id: str):
    store = get_store(None)
    observations = []
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if sender == id:
                observations.append(n.output_id)
    return {"id": id, "name": id, "observations": observations}

@app.get("/relationships")
def relationships_endpoint():
    store = get_store(None)
    rels = []
    prev = None
    for kc in store.get_chain():
        if prev:
            rels.append({"source": prev, "target": kc.commit_hash, "relation": "follows_commit"})
        prev = kc.commit_hash
    return rels

@app.get("/artifacts")
def artifacts_endpoint():
    store = get_store(None)
    artifacts = {}
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if path:
                artifacts[path] = {"id": path, "type": path.split("/")[0], "content": txt}
    return list(artifacts.values())

@app.get("/artifact/{id:path}")
def artifact_endpoint(id: str):
    for a in artifacts_endpoint():
        if a["id"] == id or id in a["id"]:
            return a
    raise HTTPException(status_code=404, detail="Artifact not found")

@app.get("/observations")
def observations_endpoint():
    store = get_store(None)
    obs = []
    for kc in store.get_chain():
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            obs.append({"id": n.output_id, "op": n.op, "dialect": n.dialect.value, "content": txt})
    return obs

@app.get("/observation/{id}")
def observation_endpoint(id: str):
    for o in observations_endpoint():
        if o["id"] == id:
            return o
    raise HTTPException(status_code=404, detail="Observation not found")

@app.get("/timeline")
def timeline_endpoint():
    store = get_store(None)
    events = []
    for kc in store.get_chain():
        events.append({
            "timestamp": kc.created_at.isoformat(),
            "type": "commit",
            "id": kc.commit_hash[:8],
            "summary": f"Compiled {len(kc.kir_nodes)} nodes"
        })
    return sorted(events, key=lambda x: x["timestamp"])

@app.get("/search")
def search_endpoint(q: str = ""):
    q_low = q.lower()
    store = get_store(None)
    matches = []
    for kc in store.get_chain():
        if q_low in kc.commit_hash.lower():
            matches.append({"type": "commit", "id": kc.commit_hash[:8], "text": kc.commit_hash})
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            if q_low in n.output_id.lower() or q_low in txt.lower() or q_low in sender.lower() or q_low in path.lower():
                matches.append({"type": "observation", "id": n.output_id, "text": f"{sender}: {txt[:40]}"})
    return matches

@app.get("/explore")
def explore_endpoint():
    store = get_store(None)
    chain = store.get_chain()
    
    graph = {"artifacts": [], "observations": [], "entities": [], "commits": []}
    entities_seen = set()
    
    for kc in chain:
        graph["commits"].append({
            "id": kc.commit_hash,
            "short_id": kc.commit_hash[:8],
            "adjacent_observations": [n.output_id for n in kc.kir_nodes]
        })
        for n in kc.kir_nodes:
            sender, path, txt = _get_meta_fields(n)
            obs_id = n.output_id
            
            graph["observations"].append({
                "id": obs_id,
                "op": n.op,
                "adjacent_commit": kc.commit_hash,
                "adjacent_artifact": path,
                "adjacent_entity": sender
            })
            if path:
                graph["artifacts"].append({"id": path, "adjacent_observation": obs_id})
            if sender not in entities_seen:
                entities_seen.add(sender)
                graph["entities"].append({"id": sender, "adjacent_observations": [obs_id]})
    return graph

@app.get("/inspect/{id:path}")
def inspect_endpoint(id: str):
    store = get_store(None)
    prov = get_provenance()
    chain = store.get_chain()
    
    # Check commit
    for kc in chain:
        if kc.commit_hash.startswith(id):
            return {
                "object_type": "Commit",
                "summary": f"Knowledge Commit {kc.commit_hash[:8]}",
                "metadata": {"created_at": kc.created_at.isoformat(), "parent": kc.parent_hash},
                "relationships": [{"target": kc.parent_hash, "relation": "parent"}] if kc.parent_hash else [],
                "timeline": [{"timestamp": kc.created_at.isoformat(), "event": "commit_created"}],
                "provenance": [kc.commit_hash],
                "supporting_evidence": [n.output_id for n in kc.kir_nodes],
                "related_commits": [kc.commit_hash]
            }
            
    # Check observation/fact/artifact
    for kc in chain:
        for n in kc.kir_nodes:
            sender, src_path, txt = _get_meta_fields(n)
            raw_id = n.output_id
            norm_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id
            
            if id in (raw_id, norm_id, src_path) or (src_path and id in src_path):
                obj_type = "Artifact" if id == src_path else "Observation"
                expl = prov.explain(norm_id) if obj_type == "Observation" else [src_path]
                return {
                    "object_type": obj_type,
                    "summary": f"{n.dialect.value}:{n.op} - {txt[:50]}",
                    "metadata": n.metadata,
                    "relationships": [{"target": kc.commit_hash, "relation": "compiled_into"}],
                    "timeline": [{"timestamp": kc.created_at.isoformat(), "event": "extracted"}],
                    "provenance": expl,
                    "supporting_evidence": [src_path],
                    "related_commits": [kc.commit_hash]
                }
                
    # Fallback to Entity
    return {
        "object_type": "Entity",
        "summary": f"Entity {id}",
        "metadata": {"entity_id": id},
        "relationships": [],
        "timeline": [],
        "provenance": [],
        "supporting_evidence": [],
        "related_commits": []
    }

@app.post("/ask")
@app.get("/reason")
def ask_endpoint(req: AskRequest = None, q: str = ""):
    intent = req.intent if req else q
    store = get_store(None)
    try:
        context = compile_reasoning_context(intent, store)
        return {"intent": intent, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain/{fact_id}")
def explain_endpoint(fact_id: str):
    prov_graph = get_provenance()
    original_fact_id = fact_id
    if fact_id.startswith("kir_obs_"):
        fact_id = "obs_" + fact_id[len("kir_obs_"):]
    explanation = prov_graph.explain(fact_id)
    return {"fact_id": original_fact_id, "chain": explanation}

@app.get("/health")
def health_endpoint():
    return {"status": "ok"}
