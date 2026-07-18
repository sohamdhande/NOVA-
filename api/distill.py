import os
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DistillRequest(BaseModel):
    project: str
    thread: str

class DistillChatRequest(BaseModel):
    project: str
    message: str
    history: list[dict] = []


# Uses __PROJECT_CONTEXT__, __USER_THREAD__, __PROJECT_NAME__ as placeholders
# instead of {curly_braces} to avoid KeyError when context contains braces like {variable_name}
DISTILL_SYSTEM_PROMPT = """You are a decision analyst for a specific project.

PROJECT CONTEXT (what is already known):
__PROJECT_CONTEXT__

CURRENT THREAD (new information to analyze):
__USER_THREAD__

Extract decisions, assumptions, uncertainties, next actions, and core background context/facts ONLY from the current thread.
Flag any contradictions with the project context.
Be specific — extract concrete decisions and factual system knowledge, not vague goals.

Return ONLY valid JSON:
{
  "project": "__PROJECT_NAME__",
  "decided": [
    {
      "decision": "concrete decision statement",
      "reasoning": "why this decision was made",
      "contradicts_prior": false,
      "confidence": "high/medium/low"
    }
  ],
  "assumed": [
    {
      "assumption": "what is being assumed",
      "why": "why this assumption matters",
      "could_break_if": "what would invalidate this"
    }
  ],
  "uncertain": [
    {
      "question": "what is still unclear",
      "why_it_matters": "impact if unresolved",
      "blocker": true
    }
  ],
  "next_actions": [
    {
      "action": "specific next step",
      "depends_on": "what must happen first (or null)",
      "owner": "who does this (or null if unclear)",
      "timeline": "when (or null if unclear)"
    }
  ],
  "contradictions": [
    "any decision that conflicts with prior decisions in this project"
  ],
  "context": [
    {
      "fact": "a concrete piece of background information or system knowledge",
      "relevance": "why this information is important"
    }
  ]
}"""


def _build_project_context(project: str) -> str:
    """Build project context string from memory store."""
    try:
        from core.api_server import nova_app
        if not nova_app or not hasattr(nova_app, 'memory_store') or not nova_app.memory_store:
            return "No prior context available (new project)."

        summary = nova_app.memory_store.get_project_summary(project)
        if summary["entry_count"] == 0:
            return "No prior context available (new project)."

        parts = [f"Project: {project}"]
        parts.append(f"Total entries: {summary['entry_count']}")
        if summary["source_types"]:
            parts.append(f"Source types: {', '.join(summary['source_types'])}")
        if summary["tags"]:
            parts.append(f"Tags: {', '.join(summary['tags'])}")

        if summary["recent_entries"]:
            parts.append("\nRecent entries:")
            for entry in summary["recent_entries"][:5]:
                parts.append(f"  - [{entry['source_type']}] {entry['title']}: {entry['summary'][:150]}")

        return "\n".join(parts)
    except Exception as e:
        return f"Context unavailable: {str(e)}"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


@router.post("/distill")
async def distill_thread(request: DistillRequest):
    """Distill a chat thread into structured decisions via Groq with SSE streaming."""
    project = request.project.strip()
    thread = request.thread.strip()

    if not project:
        raise HTTPException(status_code=400, detail="Project name is required.")
    if not thread:
        raise HTTPException(status_code=400, detail="Empty thread provided.")

    estimated_tokens = _estimate_tokens(thread)
    if estimated_tokens > 100_000:
        raise HTTPException(
            status_code=413,
            detail=f"Thread too large (~{estimated_tokens:,} tokens). Maximum is ~100,000 tokens. Please trim your thread."
        )

    import groq
    api_key = os.getenv("GROQ_API_KEY_PRIMARY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY_PRIMARY not configured.")

    client = groq.AsyncGroq(api_key=api_key)

    # Build project context from memory
    project_context = _build_project_context(project)

    thread_preview = (thread[:500] + "...") if len(thread) > 500 else thread
    system_prompt = (DISTILL_SYSTEM_PROMPT
        .replace("__PROJECT_CONTEXT__", project_context)
        .replace("__USER_THREAD__", thread_preview)
        .replace("__PROJECT_NAME__", project)
    )

    async def sse_generator():
        """Stream Groq response as Server-Sent Events."""
        accumulated = ""
        try:
            stream = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": thread}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                stream=True
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    accumulated += delta.content
                    yield f"data: {json.dumps({'type': 'chunk', 'content': delta.content})}\n\n"

            # Parse the complete JSON and send final structured result
            try:
                parsed = json.loads(accumulated)
                # Ensure project field is set
                parsed["project"] = project
                yield f"data: {json.dumps({'type': 'complete', 'result': parsed})}\n\n"
            except json.JSONDecodeError:
                yield f"data: {json.dumps({'type': 'error', 'detail': 'Failed to parse Groq response as JSON. Raw output sent as chunks.'})}\n\n"

        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg or "413" in error_msg:
                masked_key = f"{api_key[:4]}***{api_key[-4:]}" if api_key and len(api_key) > 8 else "***"
                yield f"data: {json.dumps({'type': 'error', 'detail': f'Rate limited by Groq [env: GROQ_API_KEY_PRIMARY, key: {masked_key}]: {error_msg}. Try trimming your thread or upgrading your Groq tier.'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'detail': f'Distillation failed: {error_msg}'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/distill/export/{project}")
async def export_project_context(project: str):
    """Exports a markdown narrative summarizing the project context."""
    try:
        from core.api_server import nova_app
        if not nova_app or not hasattr(nova_app, 'memory_store') or not nova_app.memory_store:
            raise HTTPException(status_code=500, detail="Memory subsystem offline")

        markdown_narrative = nova_app.memory_store.export_narrative(project)
        summary = nova_app.memory_store.get_project_summary(project)

        from datetime import datetime
        return {
            "project": project,
            "markdown": markdown_narrative,
            "metadata": {
                "entry_count": summary.get("entry_count", 0),
                "last_updated": datetime.now().isoformat(),
                "source_types": summary.get("source_types", []),
                "tags": summary.get("tags", [])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/distill/chat")
async def project_chat(request: DistillChatRequest):
    """Chat with the expert project manager powered by the consolidated narrative context."""
    project = request.project.strip()
    if not project:
        raise HTTPException(status_code=400, detail="Project name is required.")
        
    try:
        from core.api_server import nova_app
        if not nova_app or not hasattr(nova_app, 'memory_store') or not nova_app.memory_store:
            raise HTTPException(status_code=500, detail="Memory subsystem offline")

        # Get compacted context
        project_context = nova_app.memory_store.export_narrative(project)

        system_prompt = f"""You are the Principal Architect and Expert Project Manager for '{project}'.
Below is the factual Project Context distilled from memory.

Your role:
1. Provide deep, critical analysis and intelligent opinions on the project.
2. Ground your facts in the Project Context, but DO NOT artificially restrict your responses.
3. If the user asks for your Point of View (POV), critiques, advice, or evaluation, you MUST use your own vast external knowledge to analyze the decisions and state what is good, bad, or risky.
4. Never say "the context doesn't contain an evaluation." You ARE the evaluator.

PROJECT CONTEXT:
================
{project_context}
================
"""
        import groq
        import os
        api_key = os.getenv("GROQ_API_KEY_PRIMARY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY_PRIMARY not configured.")
            
        client = groq.AsyncGroq(api_key=api_key)

        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": request.message})

        async def sse_generator():
            try:
                stream = await client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    messages=messages,
                    temperature=0.2,
                    stream=True
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': delta.content})}\n\n"
                
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
