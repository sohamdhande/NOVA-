import json
import string
from dataclasses import dataclass
from typing import Any
from nova.packages.runtime import KnowledgeStore, project_current_state, Projection
import logging

logger = logging.getLogger(__name__)
class ReasoningVerificationError(Exception):
    pass

@dataclass(frozen=True)
class ReasoningPlan:
    intent: str
    keywords: list[str]

def build_plan(intent: str) -> ReasoningPlan:
    stopwords = {"a", "an", "the", "is", "of", "what", "mentioned", "in", "to", "for", "on", "with", "did", "does", "do", "it", "that", "this", "and", "or"}
    
    clean_intent = intent.lower()
    for p in string.punctuation:
        clean_intent = clean_intent.replace(p, " ")
        
    words = clean_intent.split()
    keywords = [w for w in words if w not in stopwords]
    
    return ReasoningPlan(intent=intent, keywords=keywords)

@dataclass(frozen=True)
class DependencyAnalysis:
    relevant_fact_indices: list[int]
    fallback_applied: bool = False

def analyze_dependencies(plan: ReasoningPlan, projection: Projection) -> DependencyAnalysis:
    indices = []
    for i, fact in enumerate(projection.facts):
        fact_str = json.dumps(fact).lower()
        if any(kw in fact_str for kw in plan.keywords) or any(kw in fact.get("matched_keywords", []) for kw in plan.keywords):
            indices.append(i)
            
    fallback_applied = False
    if not indices:
        fallback_applied = True
        indices = list(range(len(projection.facts)))
        
    return DependencyAnalysis(relevant_fact_indices=indices, fallback_applied=fallback_applied)

@dataclass(frozen=True)
class ReasoningIR:
    selected_facts: list[dict[str, Any]]
    plan: ReasoningPlan

def lower_to_reasoning_ir(analysis: DependencyAnalysis, projection: Projection, plan: ReasoningPlan) -> ReasoningIR:
    selected = [projection.facts[i] for i in analysis.relevant_fact_indices]
    return ReasoningIR(selected_facts=selected, plan=plan)

def optimize_reasoning_ir(rir: ReasoningIR, integrity_snapshot: dict = None) -> ReasoningIR:
    seen = set()
    deduped = []
    for fact in rir.selected_facts:
        fact_str = json.dumps(fact, sort_keys=True)
        if fact_str not in seen:
            seen.add(fact_str)
            deduped.append(fact)
            
    def _priority(f: dict) -> int:
        typ = str(f.get("type", "")).upper()
        content = f.get("content", {})
        if isinstance(content, str):
            try: content = json.loads(content)
            except Exception: content = {}
        if isinstance(content, dict) and content.get("semantic_type"):
            typ = str(content.get("semantic_type")).upper()
        ranks = {
            "DAILY_CHRONICLE_REPORT": 0,
            "DECISION": 1,
            "TRADEOFF": 2,
            "ALTERNATIVE": 3,
            "ASSUMPTION": 4,
            "RISK": 5,
            "CONSTRAINT": 6,
            "GOAL": 7,
            "QUESTION": 8,
            "PRINCIPLE": 9,
            "ACTION_ITEM": 10
        }
        base_rank = ranks.get(typ, 50)
        
        # Apply integrity status modifiers
        if integrity_snapshot:
            profiles = integrity_snapshot.get("profiles", {})
            ident = str(f.get("identity", ""))
            profile = profiles.get(ident)
            if profile:
                status = profile.get("knowledge_status", "")
                if status == "Verified":
                    base_rank -= 10  # Heavily boost human verified
                elif status == "EvidenceStrong":
                    base_rank -= 5  # Boost strong evidence
                elif status in ["Stale", "Conflicted", "Deprecated"]:
                    base_rank += 20  # Demote weak/stale
                    f["_integrity_warning"] = status
                    
                v_status = profile.get("verification_status", "unverified")
                if v_status == "unverified":
                    base_rank += 30  # Heavily demote unverified
                    f["_verification_warning"] = "[UNVERIFIED — never reviewed by user]"
                    
        return base_rank

    deduped.sort(key=_priority)
    return ReasoningIR(selected_facts=deduped, plan=rir.plan)

def verify_reasoning_ir(rir: ReasoningIR) -> ReasoningIR:
    if not rir.selected_facts:
        raise ReasoningVerificationError("ReasoningIR selected_facts is empty after optimization.")
    return rir

def compile_executable_context(rir_opt: ReasoningIR, max_context_chars: int = 16000) -> str:
    """
    Compile verified facts into a context string for the LLM.
    
    max_context_chars: Approximate character budget for the compiled context.
    ~4 chars per token, so 16000 chars ≈ 4000 tokens, leaving room for
    system prompt + question within Groq's 6000 TPM free tier limit.
    """
    context_lines = [f"Intent: {rir_opt.plan.intent}", "\nCompiled Context:"]
    current_chars = sum(len(l) for l in context_lines)
    facts_included = 0
    facts_truncated = 0
    
    for fact in rir_opt.selected_facts:
        ident = fact.get("identity", "unknown")
        typ = fact.get("type", "UNKNOWN")
        warn = ""
        if getattr(rir_opt, "has_warnings", False):
            warn = " [WARNING: Fact failed cryptographic integrity validation]"
        
        conf_str = ""
        if fact.get("confidence") is None:
            conf_str = " (Confidence: unspecified)"
        else:
            conf_str = f" (Confidence: {fact.get('confidence')})"
            
        fact_payload = dict(fact)
        formatted_txt = None
        if isinstance(fact_payload.get("content"), dict) and "content" in fact_payload["content"]:
            try:
                from api.knowledge_routes import _format_natural_text
                formatted_txt = _format_natural_text(fact_payload["content"]["content"])
            except Exception:
                pass
        elif "content" in fact_payload:
            try:
                from api.knowledge_routes import _format_natural_text
                formatted_txt = _format_natural_text(fact_payload["content"])
            except Exception:
                pass

        if formatted_txt and not formatted_txt.strip().startswith("{"):
            line = f"- Fact [{ident}] ({typ}){warn}{conf_str}:\n{formatted_txt}"
        else:
            line = f"- Fact [{ident}] ({typ}){warn}{conf_str}: {json.dumps(fact_payload, sort_keys=True)}"
        
        # Truncate individual facts that are extremely long (>3000 chars ≈ 750 tokens)
        max_fact_chars = 3000
        if len(line) > max_fact_chars:
            line = line[:max_fact_chars] + "\n[... truncated for token budget ...]"
            facts_truncated += 1
        
        # Check if adding this fact would blow the budget
        if current_chars + len(line) + 4 > max_context_chars and facts_included > 0:
            remaining = len(rir_opt.selected_facts) - facts_included
            context_lines.append(f"\n[{remaining} additional fact(s) omitted for token budget — query more specifically to narrow results]")
            break
        
        context_lines.append(line)
        current_chars += len(line) + 4  # +4 for the "\n\n" join separator
        facts_included += 1
    
    if facts_truncated:
        logger.info(f"[ReasoningCompiler] Truncated {facts_truncated} oversized facts to fit token budget.")
        
    return "\n\n".join(context_lines)

def compile_reasoning_context(intent: str, store: KnowledgeStore, temporal_idx=None) -> str:
    logger.info(f"[ReasoningCompiler] Executing pipeline for intent: '{intent}'")
    
    plan = build_plan(intent)
    logger.debug(f"[ReasoningCompiler] 1. build_plan: Extracted {len(plan.keywords)} keywords -> {plan.keywords}")
    
    projection = project_current_state(store, temporal_idx=temporal_idx)
    logger.debug(f"[ReasoningCompiler] 2. project_current_state: Flattened {len(projection.facts)} total facts from chain.")

    chronicle_kws = {"change", "changed", "new", "week", "today", "yesterday", "evolved", "growth", "chronicle", "health", "happened", "summary", "snapshot"}
    if any(kw in intent.lower() for kw in chronicle_kws):
        try:
            from nova.packages.runtime.daily_chronicle import generate_daily_chronicle, compute_knowledge_health
            rep = generate_daily_chronicle(store, window="7d" if "week" in intent.lower() else "today")
            hlth = compute_knowledge_health(store)
            report_fact = {
                "identity": rep["snapshot"]["snapshot_id"],
                "type": "DAILY_CHRONICLE_REPORT",
                "matched_keywords": plan.keywords,
                "content": {"report": rep, "health": hlth}
            }
            projection = Projection(facts=[report_fact] + list(projection.facts), as_of=projection.as_of)
            logger.debug("[ReasoningCompiler] Injected DAILY_CHRONICLE_REPORT fact at priority 0.")
        except Exception as e:
            logger.warning(f"[ReasoningCompiler] Could not generate daily chronicle fact: {e}")
    
    analysis = analyze_dependencies(plan, projection)
    total_facts = len(projection.facts)
    if analysis.fallback_applied:
        logger.debug(f"[ReasoningCompiler] 3. analyze_dependencies: 0/{total_facts} facts matched naturally — fallback applied, {total_facts}/{total_facts} included.")
    else:
        logger.debug(f"[ReasoningCompiler] 3. analyze_dependencies: {len(analysis.relevant_fact_indices)}/{total_facts} facts matched keywords.")
    
    rir = lower_to_reasoning_ir(analysis, projection, plan)
    logger.debug(f"[ReasoningCompiler] 4. lower_to_reasoning_ir: Constructed IR with {len(rir.selected_facts)} facts.")
    
    rir_opt = optimize_reasoning_ir(rir, getattr(store, "integrity_snapshot", None))
    logger.debug(f"[ReasoningCompiler] 5. optimize_reasoning_ir: Deduped down to {len(rir_opt.selected_facts)} facts.")
    
    rir_ver = verify_reasoning_ir(rir_opt)
    logger.debug(f"[ReasoningCompiler] 6. verify_reasoning_ir: Context passed verification.")
    
    context_str = compile_executable_context(rir_ver)
    logger.debug(f"[ReasoningCompiler] 7. compile_executable_context: Rendered final string.\n")
    
    return context_str

__all__ = [
    "ReasoningVerificationError",
    "ReasoningPlan",
    "DependencyAnalysis",
    "ReasoningIR",
    "build_plan",
    "analyze_dependencies",
    "lower_to_reasoning_ir",
    "optimize_reasoning_ir",
    "verify_reasoning_ir",
    "compile_executable_context",
    "compile_reasoning_context"
]
