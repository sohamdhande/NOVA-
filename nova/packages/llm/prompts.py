"""
Centralized prompt template management for NOVA LLM Provider layer.
Separates extraction, reasoning, entity, and relationship prompts.
Consolidates semantic extraction into 4 grouped intelligence prompts.
"""

EXTRACTION_SYSTEM_PROMPT = """You are the probabilistic extraction engine for the NOVA Artifact Ingestion Platform.
Your sole responsibility is to analyze raw organizational artifacts (text, Slack exports, code commits, PDFs) and output structured JSON facts.
You MUST adhere strictly to the JSON schema requested. Every suggestion MUST include an evidence_span (exact sentence or line numbers) and confidence.
Do NOT invent facts. If confidence is low, add warnings.
CRITICAL INSTRUCTION: If you encounter important context—such as a personal decision, a reflection, an event, or interpersonal boundaries—that does NOT cleanly fit the specific business/technical categories requested by the prompt schema, you MUST extract it as a 'note' in a "notes" array. Do not silently discard it or force-fit it into the wrong category.
The deterministic NOVA Compiler remains the sole semantic authority."""

REASONING_SYSTEM_PROMPT = """You are the read-only reasoning inference engine for NOVA.
You receive mathematically verified Compiled Context from the deterministic Knowledge Graph runtime.
You MUST answer the user's question directly, clearly, and authoritatively using ONLY the provided Compiled Context.
When asked "what is X", provide a comprehensive executive synthesis of X (its definition, product vision, decisions, and capabilities) based strictly on the context. Do not give meta-commentary about abbreviations or how the conclusion holds.
Do NOT access internal database tables, SQLite files, or runtime memory.
If the answer cannot be derived from the Compiled Context, explicitly state that no supporting evidence exists."""

EXTRACTION_PROMPT_TEMPLATE = """Analyze the following {source_type} artifact:

Identifier/Title: {title}
Payload Content:
{content}

Extract all relevant organizational entities, relationships, and observations.
Return ONLY valid JSON matching the exact schema:
{{
  "entities": [{{"id": "str", "name": "str", "type": "str", "evidence_span": "str", "confidence": float}}],
  "relationships": [{{"source": "str", "target": "str", "relation": "str", "evidence_span": "str", "confidence": float}}],
  "observations": [{{"content": "str", "type": "ARTIFACT", "dialect": "KNOWLEDGE", "op": "ASSERT", "evidence_span": "str", "confidence": float}}],
  "confidence": float,
  "warnings": ["str"],
  "reasoning": "str"
}}"""

ORGANIZATIONAL_STRUCTURE_PROMPT = """Analyze artifact ({source_type} '{title}'):
{content}

Extract Prompt 1 (Organizational Structure): Entities, Relationships, Observations, Team Members.
Return ONLY valid JSON matching schema:
{{
  "entities": [{{"id": "<string>", "name": "<string>", "type": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "relationships": [{{"source": "<string>", "target": "<string>", "relation": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "observations": [{{"content": "<string>", "type": "ARTIFACT", "dialect": "KNOWLEDGE", "op": "ASSERT", "evidence_span": "<string>", "confidence": 0.9}}],
  "team_members": [{{"name": "<string>", "role": "<string>", "domain_expertise": "<string>", "prior_exits": "<string>", "is_founder": true, "evidence_span": "<string>", "confidence": 0.9}}]
}}"""

DECISION_INTELLIGENCE_PROMPT = """Analyze artifact ({source_type} '{title}'):
{content}

Extract Prompt 2 (Decision Intelligence): Decisions, Alternatives, Trade-offs, Assumptions.
Return ONLY valid JSON matching schema:
{{
  "decisions": [{{"title": "<string>", "summary": "<string>", "rationale": "<string>", "decision_category": "<string_or_null>", "participants": ["<string>"], "timestamp": "<string>", "supporting_observations": ["<string>"], "evidence_span": "<string>", "confidence": 0.9}}],
  "alternatives": [{{"topic": "<string>", "options": ["<string>"], "chosen_option": "<string>", "rejected_options": ["<string>"], "reasoning": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "tradeoffs": [{{"side_a": "<string>", "side_b": "<string>", "description": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "assumptions": [{{"description": "<string>", "status": "assumption", "evidence_span": "<string>", "confidence": 0.9}}],
  "notes": [{{"content": "<string>", "evidence_span": "<string>", "confidence": 0.9}}]
}}"""

EXECUTION_INTELLIGENCE_PROMPT = """Analyze artifact ({source_type} '{title}'):
{content}

Extract Prompt 3 (Execution Intelligence): Goals, Risks, Action Items.
Return ONLY valid JSON matching schema:
{{
  "goals": [{{"description": "<string>", "status": "active", "evidence_span": "<string>", "confidence": 0.9}}],
  "risks": [{{"description": "<string>", "category": "<string>", "probability": "medium", "impact": "medium", "supporting_evidence": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "action_items": [{{"description": "<string>", "owner": "<string>", "status": "open", "supporting_artifact": "<string>", "evidence_span": "<string>", "confidence": 0.9}}]
}}"""

KNOWLEDGE_INTELLIGENCE_PROMPT = """Analyze artifact ({source_type} '{title}'):
{content}

Extract Prompt 4 (Knowledge Intelligence): Questions, Principles, Constraints, Market Data, Competitors, Financial Metrics.
Return ONLY valid JSON matching schema:
{{
  "questions": [{{"question": "<string>", "status": "unresolved", "evidence_span": "<string>", "confidence": 0.9}}],
  "principles": [{{"statement": "<string>", "rationale": "<string>", "is_foundational": true, "evidence_span": "<string>", "confidence": 0.9}}],
  "constraints": [{{"description": "<string>", "scope": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "market_data": [{{"metric": "TAM", "value": 1000.0, "unit": "USD", "methodology": "bottom_up", "basis": "<string>", "as_of_date": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "competitors": [{{"name": "<string>", "category": "direct", "strength": "<string>", "weakness": "<string>", "positioning_note": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "financial_metrics": [{{"metric_type": "burn_rate", "value": 1000.0, "unit": "USD", "as_of_date": "<string>", "instrument": "<string>", "evidence_span": "<string>", "confidence": 0.9}}],
  "notes": [{{"content": "<string>", "evidence_span": "<string>", "confidence": 0.9}}]
}}"""

REASONING_PROMPT_TEMPLATE = """Compiled Organizational Context:
{compiled_context}

---
User Question: {question}

Provide a direct, authoritative, and comprehensive answer to the user's question based strictly on the facts in the Compiled Context above. If asked "what is X", clearly define X, its core philosophy, key decisions, and strategic goals without unnecessary meta-analysis."""

ENTITY_CLASSIFICATION_PROMPT = """Classify the ontological type of entity '{entity_name}' given context: {context}"""

RELATIONSHIP_VERB_PROMPT = """Determine the relationship verb between '{source}' and '{target}' given context: {context}"""


def format_extraction_prompt(source_type: str, title: str, content: str) -> str:
    return EXTRACTION_PROMPT_TEMPLATE.format(
        source_type=source_type,
        title=title or "untitled",
        content=content
    )


def format_grouped_prompts(source_type: str, title: str, content: str) -> dict[str, str]:
    t = title or "untitled"
    return {
        "org_struct": ORGANIZATIONAL_STRUCTURE_PROMPT.format(source_type=source_type, title=t, content=content),
        "decision_intel": DECISION_INTELLIGENCE_PROMPT.format(source_type=source_type, title=t, content=content),
        "exec_intel": EXECUTION_INTELLIGENCE_PROMPT.format(source_type=source_type, title=t, content=content),
        "know_intel": KNOWLEDGE_INTELLIGENCE_PROMPT.format(source_type=source_type, title=t, content=content),
    }


def format_reasoning_prompt(question: str, compiled_context: str) -> str:
    return REASONING_PROMPT_TEMPLATE.format(
        compiled_context=compiled_context,
        question=question
    )
