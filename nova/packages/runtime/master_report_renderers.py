from typing import Callable, Any
from nova.packages.runtime.state_resolution import StateSnapshot, ResolvedNode

import json

def extract_fields(node: ResolvedNode) -> dict:
    """
    Safely unwraps a ResolvedNode's actual semantic fields from the nested
    metadata structure. Handles flat (for tests), nested dict, and nested JSON string
    (metadata["content"]["content"]). Returns an empty dict if malformed.
    """
    meta = node.node.metadata
    
    # 1. Check if fields are right at the root (mostly for older tests)
    if any(k in meta for k in ["title", "description", "question", "statement", "metric", "name"]):
        return meta
        
    content_val = meta.get("content")
    if not content_val:
        return {}
        
    # 2. If it's a dictionary
    if isinstance(content_val, dict):
        # Handle the exact nesting described by the user: metadata["content"]["content"] as JSON string
        if "content" in content_val and isinstance(content_val["content"], str):
            try:
                parsed = json.loads(content_val["content"])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        # Otherwise, the dictionary itself contains the fields (e.g. from raw_payload)
        return content_val
        
    # 3. If content itself is a JSON string
    if isinstance(content_val, str):
        try:
            parsed = json.loads(content_val)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
            
    return {}

def _render_node_list(nodes: list[ResolvedNode], formatter: Callable[[dict], str]) -> str:
    """Helper to render a list of nodes using a formatting function."""
    if not nodes:
        return "* None\n"
    return "".join(f"* {formatter(extract_fields(n))}\n" for n in nodes if n.status == "ACTIVE")

# --- IMPLEMENTED SECTIONS ---

def render_executive_summary_section(snapshot: StateSnapshot) -> str:
    out = ["## Executive Summary\n"]
    
    foundational_principles = [
        n for n in snapshot.buckets.get("PRINCIPLE", [])
        if n.status == "ACTIVE" and extract_fields(n).get("is_foundational") is True
    ]
    
    if not foundational_principles:
        out.append("\n[No foundational principle has been marked yet. Mark a PRINCIPLE as foundational to populate this section.]\n")
    else:
        out.append("### Foundational Principles\n")
        out.append(_render_node_list(
            foundational_principles,
            lambda m: f"**{m.get('statement', '')}**: {m.get('rationale', '')}"
        ))
        
    out.append("\n### Top-Level Goals\n")
    out.append(_render_node_list(
        snapshot.buckets.get("GOAL", []),
        lambda m: f"{m.get('description', '')}"
    ))
    
    return "".join(out)

def render_business_model_section(snapshot: StateSnapshot) -> str:
    out = ["## Business Model\n"]
    
    pricing_decisions = [
        n for n in snapshot.buckets.get("DECISION", [])
        if n.status == "ACTIVE" and extract_fields(n).get("decision_category") == "pricing"
    ]
    
    if not pricing_decisions:
        out.append("\n[No pricing-related decision has been marked yet. Extract a DECISION with decision_category='pricing' to populate this section.]\n")
    else:
        out.append("### Pricing Decisions\n")
        out.append(_render_node_list(
            pricing_decisions,
            lambda m: f"**{m.get('title', 'Untitled')}**: {m.get('summary', '')}"
        ))
        
    out.append("\n### Assumptions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ASSUMPTION", []),
        lambda m: f"{m.get('description', '')}"
    ))
    
    return "".join(out)

def render_solution_product_section(snapshot: StateSnapshot) -> str:
    out = ["## Solution & Product\n"]
    out.append("### Decisions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("DECISION", []),
        lambda m: f"**{m.get('title', 'Untitled')}**: {m.get('summary', '')}"
    ))
    out.append("\n### Tradeoffs\n")
    out.append(_render_node_list(
        snapshot.buckets.get("TRADEOFF", []),
        lambda m: f"**{m.get('side_a', '')} vs {m.get('side_b', '')}**: {m.get('description', '')}"
    ))
    out.append("\n### Alternatives Considered\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ALTERNATIVE", []),
        lambda m: f"**{m.get('topic', '')}** -> Chose: {m.get('chosen_option', '')}"
    ))
    return "".join(out)


def render_traction_milestones_section(snapshot: StateSnapshot) -> str:
    out = ["## Traction & Milestones\n"]
    out.append("### Goals\n")
    out.append(_render_node_list(
        snapshot.buckets.get("GOAL", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Action Items\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ACTION_ITEM", []),
        lambda m: f"{m.get('description', '')}"
    ))
    return "".join(out)


def render_go_to_market_section(snapshot: StateSnapshot) -> str:
    out = ["## Go-to-Market\n"]
    out.append("### Decisions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("DECISION", []),
        lambda m: f"**{m.get('title', 'Untitled')}**: {m.get('summary', '')}"
    ))
    out.append("\n### Action Items\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ACTION_ITEM", []),
        lambda m: f"{m.get('description', '')}"
    ))
    return "".join(out)


def render_roadmap_risks_section(snapshot: StateSnapshot) -> str:
    out = ["## Roadmap & Risks\n"]
    out.append("### Goals\n")
    out.append(_render_node_list(
        snapshot.buckets.get("GOAL", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Action Items\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ACTION_ITEM", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Risks\n")
    out.append(_render_node_list(
        snapshot.buckets.get("RISK", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Open Questions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("QUESTION", []),
        lambda m: f"{m.get('question', '')}"
    ))
    return "".join(out)


def render_the_problem_section(snapshot: StateSnapshot) -> str:
    out = ["## The Problem\n"]
    out.append("### Assumptions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ASSUMPTION", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Questions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("QUESTION", []),
        lambda m: f"{m.get('question', '')}"
    ))
    return "".join(out)


def render_why_now_section(snapshot: StateSnapshot) -> str:
    out = ["## Why Now\n"]
    out.append("### Assumptions\n")
    out.append(_render_node_list(
        snapshot.buckets.get("ASSUMPTION", []),
        lambda m: f"{m.get('description', '')}"
    ))
    out.append("\n### Principles\n")
    out.append(_render_node_list(
        snapshot.buckets.get("PRINCIPLE", []),
        lambda m: f"{m.get('statement', '')}"
    ))
    return "".join(out)


def render_market_opportunity_section(snapshot: StateSnapshot) -> str:
    out = ["## Market Opportunity\n"]
    
    market_nodes = snapshot.buckets.get("MARKET_DATA", [])
    if market_nodes:
        out.append(_render_node_list(
            market_nodes,
            lambda m: f"**{m.get('metric', '')}**: {m.get('value', 0)} {m.get('unit', '')} (Methodology: {m.get('methodology', 'unspecified')}, Basis: {m.get('basis', 'unspecified')}, As of: {m.get('as_of_date', 'unspecified')})"
        ))
    else:
        # Heuristic search for tracking signal - signal-finding only, not a substitute for real data
        keywords = ["market size", "tam", "sam", "som", "total addressable"]
        tracking_q = None
        for q in snapshot.buckets.get("QUESTION", []):
            if q.status == "ACTIVE":
                desc = extract_fields(q).get("question", "").lower()
                if any(kw in desc for kw in keywords):
                    tracking_q = q
                    break
                    
        if tracking_q:
            out.append(f"\n[Market sizing has not yet been quantified. Open Question {tracking_q.node.output_id}: '{extract_fields(tracking_q).get('question', '')}' is tracking this gap.]\n")
        else:
            out.append("\n[Market sizing (TAM/SAM/SOM) has not yet been recorded in Chronicle. Add this data via a Chronicle conversation covering market sizing calculations.]\n")
            
    return "".join(out)


def render_competitive_landscape_section(snapshot: StateSnapshot) -> str:
    out = ["## Competitive Landscape\n"]
    
    comp_nodes = snapshot.buckets.get("COMPETITOR", [])
    if comp_nodes:
        out.append(_render_node_list(
            comp_nodes,
            lambda m: f"**{m.get('name', '')}** ({m.get('category', '')}) - Strength: {m.get('strength', '')}, Weakness: {m.get('weakness', '')}. Note: {m.get('positioning_note', '')}"
        ))
    else:
        # Heuristic search for tracking signal - signal-finding only, not a substitute for real data
        keywords = ["competitor", "competition", "rival", "vs"]
        tracking_risk = None
        for r in snapshot.buckets.get("RISK", []):
            if r.status == "ACTIVE":
                desc = extract_fields(r).get("description", "").lower()
                if any(kw in desc for kw in keywords):
                    tracking_risk = r
                    break
                    
        if tracking_risk:
            out.append(f"\n[No formal competitor analysis exists yet. Risk {tracking_risk.node.output_id} references competitive pressure: '{extract_fields(tracking_risk).get('description', '')[:50]}...']\n")
        else:
            out.append("\n[Competitive landscape has not yet been recorded in Chronicle. Add competitor analysis via a Chronicle conversation.]\n")
            
    return "".join(out)


def render_team_section(snapshot: StateSnapshot) -> str:
    out = ["## Team\n"]
    
    team_nodes = [n for n in snapshot.buckets.get("TEAM_MEMBER", []) if n.status == "ACTIVE"]
    if team_nodes:
        # Sort founders first
        team_nodes.sort(key=lambda n: not extract_fields(n).get("is_founder", False))
        
        out.append(_render_node_list(
            team_nodes,
            lambda m: f"**{m.get('name', '')}** ({m.get('role', '')}) - Founder: {m.get('is_founder', False)}. Expertise: {m.get('domain_expertise', '')}. Exits: {m.get('prior_exits', 'None')}"
        ))
    else:
        out.append("\n[Team composition and founder backgrounds have not yet been recorded in Chronicle. Add this via a Chronicle conversation describing the founding team.]\n")
        
    return "".join(out)


def render_financials_ask_section(snapshot: StateSnapshot) -> str:
    out = ["## Financials & The Ask\n"]
    
    fin_nodes = snapshot.buckets.get("FINANCIAL_METRIC", [])
    if fin_nodes:
        out.append(_render_node_list(
            fin_nodes,
            lambda m: f"**{m.get('metric_type', '')}**: {m.get('value', 0)} {m.get('unit', '')} (Instrument: {m.get('instrument', 'None')}, As of: {m.get('as_of_date', 'unspecified')})"
        ))
    else:
        # Heuristic search for tracking signal - signal-finding only, not a substitute for real data
        keywords = ["funding", "runway", "raise", "burn rate"]
        tracking_goal = None
        for g in snapshot.buckets.get("GOAL", []):
            if g.status == "ACTIVE":
                desc = extract_fields(g).get("description", "").lower()
                if any(kw in desc for kw in keywords):
                    tracking_goal = g
                    break
                    
        if tracking_goal:
            out.append(f"\n[No formal financial metrics exist yet. Goal {tracking_goal.node.output_id} references funding: '{extract_fields(tracking_goal).get('description', '')[:50]}...']\n")
        else:
            out.append("\n[Financial metrics and funding ask have not yet been recorded in Chronicle. Add this via a Chronicle conversation covering burn rate, runway, and the ask.]\n")
            
    return "".join(out)


# Registry mapping section name -> (renderer_func, list_of_consumed_categories)
SECTION_RENDERERS = {
    "solution_product": (render_solution_product_section, ["DECISION", "TRADEOFF", "ALTERNATIVE"]),
    "business_model": (render_business_model_section, ["DECISION", "ASSUMPTION"]),
    "traction_milestones": (render_traction_milestones_section, ["GOAL", "ACTION_ITEM"]),
    "go_to_market": (render_go_to_market_section, ["DECISION", "ACTION_ITEM"]),
    "roadmap_risks": (render_roadmap_risks_section, ["GOAL", "ACTION_ITEM", "RISK", "QUESTION"]),
    "the_problem": (render_the_problem_section, ["ASSUMPTION", "QUESTION"]),
    "why_now": (render_why_now_section, ["ASSUMPTION", "PRINCIPLE"]),
    "executive_summary": (render_executive_summary_section, ["PRINCIPLE", "GOAL"]),
    "market_opportunity": (render_market_opportunity_section, ["MARKET_DATA", "QUESTION"]),
    "competitive_landscape": (render_competitive_landscape_section, ["COMPETITOR", "RISK"]),
    "team": (render_team_section, ["TEAM_MEMBER"]),
    "financials_ask": (render_financials_ask_section, ["FINANCIAL_METRIC", "GOAL"]),
}
